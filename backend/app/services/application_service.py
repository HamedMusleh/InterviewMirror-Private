import re

from app.core.resume_validation import (
    ALLOWED_RESUME_CONTENT_TYPES,
    MAX_RESUME_FILE_SIZE_BYTES,
)
from app.database.models.candidate import Candidate
from app.database.models.job_opportunity import JOB_STATUS_ARCHIVED
from app.database.models.user import User
from app.modules.resume_matching.pipeline import ResumeMatchingPipeline
from app.modules.resume_parser.pipeline import CVParserPipeline
from app.modules.screening.pipeline import ScreeningPipeline
from app.repositories.application_repository import ApplicationRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.repositories.resume_repository import SQLAlchemyResumeRepository
from app.repositories.screening_criteria_repository import (
    ScreeningCriteriaRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.application import ApplicationSubmitResponse
from app.schemas.screening_score import ScreeningScoreRequest
from app.services.interview_creation_service import (
    RECOMMENDED_SCREENING_STATUS,
    InterviewCreationService,
)

APPLICATION_STATUS_APPLIED = "applied"

# Role assigned to a User created from a candidate-facing application
# submission. There is no login/registration flow yet (see module
# docstring), so this is the only role that flow can ever produce.
CANDIDATE_USER_ROLE = "candidate"

# Authentication is intentionally out of scope for this flow (see
# module docstring). User.password_hash has a NOT NULL constraint at
# the database level with no default, so a placeholder is written
# here to satisfy the schema until real authentication exists. This
# value is never used to authenticate anyone.
NO_AUTH_PASSWORD_PLACEHOLDER = "no-authentication-configured"

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ApplicationServiceError(Exception):
    """Base class for failures raised by ApplicationService."""


class JobOpportunityNotFoundError(ApplicationServiceError):
    """Raised when job_opportunity_id does not refer to an existing job."""


class JobNotReadyForApplicationsError(ApplicationServiceError):
    """Raised when the job has no ScreeningCriteria configured yet.

    Resume Matching and Screening both depend on ScreeningCriteria, so
    candidates must not be allowed to apply -- and no User/Candidate/
    Application/Resume should be created -- until a recruiter has
    configured it for this job.
    """


class DuplicateApplicationError(ApplicationServiceError):
    """Raised when the candidate has already applied to this job."""


class InvalidResumeFileError(ApplicationServiceError):
    """Raised when the uploaded resume file fails validation."""


class InvalidApplicantDataError(ApplicationServiceError):
    """Raised when the submitted applicant name/email fails validation."""


class ApplicationService:
    """Resolve the applicant's User/Candidate identity from the
    submitted form data, then create a job application together with
    its resume, atomically, then run it through resume matching and
    candidate screening.

    There is no login/registration flow yet, so the candidate-facing
    application form is also where a User/Candidate pair first gets
    created: the submitted email is used to find an existing User
    (reused as-is) or create a new one, the same way for the Candidate
    linked to that User. candidate_id is never accepted from the
    frontend -- it is always resolved here, from the submitted email,
    using the database's own autoincrement primary key.

    User/Candidate lookups and creation, application creation, and
    resume persistence/parsing only add and flush rows through their
    repositories and never commit by themselves; the caller (router)
    commits once everything below has succeeded, and rolls back on
    any exception so a failed step never leaves a partially-created
    User/Candidate/application/resume behind.

    Note on where the commit actually happens: ScreeningResultRepository
    .save() (reused as-is from the existing screening module) commits
    internally once it saves the screening result. In practice that
    means the real commit point for this whole flow is inside that
    call, and the router's own db.commit() afterwards is a no-op by
    then. This mirrors the same pattern already used by the existing
    /api/cv-parser/parse flow -- it isn't something introduced here.

    Interview creation on a recommended screening result reuses
    InterviewCreationService.create_for_application() exactly as the
    /api/cv-parser/parse flow does: it is idempotent (a second call
    for the same application just returns the existing Interview), it
    only flushes (never commits) so it stays part of this same
    transaction, and it never fabricates an interview id -- the
    candidate-facing status endpoint (ApplicationStatusService) is
    what later surfaces this real id to the "Join Interview" button.
    """

    def __init__(
        self,
        application_repository: ApplicationRepository,
        resume_repository: SQLAlchemyResumeRepository,
        job_opportunity_repository: JobOpportunityRepository,
        user_repository: UserRepository,
        candidate_repository: CandidateRepository,
        screening_criteria_repository: ScreeningCriteriaRepository,
        cv_parser_pipeline: CVParserPipeline,
        resume_matching_pipeline: ResumeMatchingPipeline,
        screening_pipeline: ScreeningPipeline,
        interview_creation_service: InterviewCreationService,
    ):
        self.application_repository = application_repository
        self.resume_repository = resume_repository
        self.job_opportunity_repository = job_opportunity_repository
        self.user_repository = user_repository
        self.candidate_repository = candidate_repository
        self.screening_criteria_repository = screening_criteria_repository
        self.cv_parser_pipeline = cv_parser_pipeline
        self.resume_matching_pipeline = resume_matching_pipeline
        self.screening_pipeline = screening_pipeline
        self.interview_creation_service = interview_creation_service

    async def submit_application(
        self,
        job_opportunity_id: int,
        first_name: str,
        last_name: str,
        email: str,
        phone: str | None,
        file_name: str,
        content_type: str | None,
        file_bytes: bytes,
    ) -> ApplicationSubmitResponse:
        self._validate_resume_file(content_type, file_bytes)
        self._validate_applicant_data(first_name, last_name, email)

        job_opportunity = self.job_opportunity_repository.get_by_id(
            job_opportunity_id
        )

        if job_opportunity is None:
            raise JobOpportunityNotFoundError(
                f"Job opportunity {job_opportunity_id} does not exist."
            )

        # Resume Matching and Screening both depend on ScreeningCriteria,
        # so this must be checked before any User/Candidate/Application/
        # Resume gets created -- not discovered afterwards when matching
        # runs. Reuses the same ScreeningCriteriaRepository the
        # screening-criteria module already writes through.
        screening_criteria = (
            self.screening_criteria_repository.get_by_job_opportunity_id(
                job_opportunity_id
            )
        )

        if screening_criteria is None:
            raise JobNotReadyForApplicationsError(
                "Job is not ready to accept applications yet."
            )

        # Checked here, next to the criteria check and for the same reason:
        # a closed posting must be refused before any User, Candidate,
        # Application or Resume is created, not after. The recruiter has
        # said this job is finished, and the candidate is entitled to hear
        # that rather than to have an application quietly accepted into
        # something nobody is reviewing.
        if job_opportunity.status == JOB_STATUS_ARCHIVED:
            raise JobNotReadyForApplicationsError(
                "This job is closed and is no longer accepting "
                "applications."
            )

        user = self._find_or_create_user(
            email=email.strip(),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
        )

        candidate = self._find_or_create_candidate(
            user_id=user.id,
            phone=phone.strip() if phone else None,
        )

        existing_application = (
            self.application_repository.get_by_candidate_and_job(
                candidate_id=candidate.id,
                job_opportunity_id=job_opportunity_id,
            )
        )

        if existing_application is not None:
            raise DuplicateApplicationError(
                "You have already applied to this job."
            )

        application = self.application_repository.create(
            candidate_id=candidate.id,
            job_opportunity_id=job_opportunity_id,
            status=APPLICATION_STATUS_APPLIED,
        )

        parsed = self.cv_parser_pipeline.parse(file_bytes)

        resume = self.resume_repository.save(
            application_id=application.id,
            file_name=file_name,
            file_url="",
            file_type=content_type or "",
            file_data=file_bytes,
            file_size=len(file_bytes),
            resume_data=parsed.resume_data,
        )

        # Resume Matching: reuses ResumeMatchingPipeline.match_application(),
        # which reads the application/resume/job/screening-criteria rows
        # back from the database through its own repository. The pipeline
        # injected here (see dependencies/application.py) is built on this
        # same request's db session rather than an independent one, so it
        # can see the application and resume this call just flushed but
        # hasn't committed yet.
        matching_result = (
            await self.resume_matching_pipeline.match_application(
                application.id
            )
        )

        # Candidate Screening: reuses ScreeningPipeline.score_candidate()
        # with the existing ScreeningScoreRequest contract, fed directly
        # from the matching result. No matching or scoring math is
        # duplicated here.
        screening_request = ScreeningScoreRequest(
            candidate_id=matching_result.candidate_id,
            job_id=matching_result.job_id,
            application_id=matching_result.application_id,
            criteria_id=matching_result.criteria_id,
            category_scores=matching_result.category_scores,
            category_weights=matching_result.category_weights,
            matching_details=matching_result.matching_results.model_dump(),
            passing_score=matching_result.passing_score,
        )

        screening_result = self.screening_pipeline.score_candidate(
            screening_request
        )

        # Create an interview only for candidates who passed screening,
        # mirroring the existing /api/cv-parser/parse flow exactly.
        # InterviewCreationService.create_for_application() re-reads the
        # screening result it needs from the database, which is already
        # committed by ScreeningResultRepository.save() above, and it
        # only flushes the new Interview row -- the router still commits
        # once this whole method returns. Without this step an approved
        # application would never have a real interview to join.
        interview_id: int | None = None

        if screening_result.final_status == RECOMMENDED_SCREENING_STATUS:
            creation_result = (
                self.interview_creation_service.create_for_application(
                    application_id=application.id,
                )
            )
            interview_id = creation_result.interview.id

        return ApplicationSubmitResponse(
            application_id=application.id,
            job_opportunity_id=application.job_opportunity_id,
            resume_id=resume.id,
            status=application.status,
            applied_at=application.applied_at,
            interview_id=interview_id,
        )

    def _validate_resume_file(
        self,
        content_type: str | None,
        file_bytes: bytes,
    ) -> None:
        if content_type not in ALLOWED_RESUME_CONTENT_TYPES:
            raise InvalidResumeFileError(
                "Only PDF and DOCX files are supported."
            )

        if not file_bytes:
            raise InvalidResumeFileError("The uploaded file is empty.")

        if len(file_bytes) > MAX_RESUME_FILE_SIZE_BYTES:
            raise InvalidResumeFileError(
                "File size must not exceed 10 MB."
            )

    def _validate_applicant_data(
        self,
        first_name: str,
        last_name: str,
        email: str,
    ) -> None:
        if not first_name.strip():
            raise InvalidApplicantDataError("First name is required.")

        if not last_name.strip():
            raise InvalidApplicantDataError("Last name is required.")

        if not _EMAIL_PATTERN.match(email.strip()):
            raise InvalidApplicantDataError(
                "A valid email address is required."
            )

    def _find_or_create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
    ) -> User:
        """Find the User for this email, or create one.

        Email is the only identity signal available while there is no
        login/registration flow, so an existing User is always reused
        as-is (its stored name is not overwritten by whatever this
        particular application submission typed in).
        """

        user = self.user_repository.get_by_email(email)

        if user is not None:
            return user

        return self.user_repository.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password_hash=NO_AUTH_PASSWORD_PLACEHOLDER,
            role=CANDIDATE_USER_ROLE,
        )

    def _find_or_create_candidate(
        self,
        user_id: int,
        phone: str | None,
    ) -> Candidate:
        """Find the Candidate linked to this User, or create one.

        Candidate.user_id is unique, so each User has at most one
        Candidate; an existing Candidate is always reused as-is.
        """

        candidate = self.candidate_repository.get_by_user_id(user_id)

        if candidate is not None:
            return candidate

        return self.candidate_repository.create(
            user_id=user_id,
            phone=phone,
        )
