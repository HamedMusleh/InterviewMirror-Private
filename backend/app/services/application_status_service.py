from app.repositories.application_repository import ApplicationRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.repositories.screening_criteria_repository import (
    ScreeningCriteriaRepository,
)
from app.repositories.user_repository import UserRepository
from app.modules.screening.repository import ScreeningResultRepository
from app.schemas.application_status import ApplicationStatusResponse
from app.services.application_service import JobOpportunityNotFoundError
from app.services.interview_creation_service import (
    RECOMMENDED_SCREENING_STATUS,
)
from app.services.interview_flow_service import INTERVIEW_STATUS_COMPLETED


class ApplicationStatusService:
    """Derives which section the candidate-facing JobApplicationPage
    should render, entirely from existing database records -- no new
    status columns or booleans are introduced.

    There is no login/registration flow (see ApplicationService), so
    "this candidate" can only be resolved from an email the frontend
    already has (e.g. remembered in browser storage after a previous
    submission -- see JobApplicationPage.tsx). No email, or an email
    that does not resolve to an existing Candidate, simply means the
    candidate has no known application yet: "can_apply" (once the job
    itself is ready).

    State resolution, in order:
      1. ScreeningCriteria missing for the job -> job_not_ready
      2. No resolvable Candidate, or no Application for that
         Candidate/job pair -> can_apply
      3. No ScreeningResult yet for the Application -> screening_in_progress
      4. ScreeningResult not "recommended" -> rejected
      5. No Interview yet, or Interview not "completed" ->
         approved_for_interview (interview_id is only ever populated
         once a real Interview row exists)
      6. Interview "completed" -> evaluation_in_progress
    """

    def __init__(
        self,
        job_opportunity_repository: JobOpportunityRepository,
        screening_criteria_repository: ScreeningCriteriaRepository,
        user_repository: UserRepository,
        candidate_repository: CandidateRepository,
        application_repository: ApplicationRepository,
        screening_repository: ScreeningResultRepository,
        interview_repository: InterviewRepository,
    ):
        self.job_opportunity_repository = job_opportunity_repository
        self.screening_criteria_repository = screening_criteria_repository
        self.user_repository = user_repository
        self.candidate_repository = candidate_repository
        self.application_repository = application_repository
        self.screening_repository = screening_repository
        self.interview_repository = interview_repository

    def get_status(
        self,
        job_id: str,
        email: str | None,
    ) -> ApplicationStatusResponse:
        job_opportunity = self.job_opportunity_repository.get_by_job_id(
            job_id
        )

        if job_opportunity is None:
            raise JobOpportunityNotFoundError(
                f"Job opportunity '{job_id}' does not exist."
            )

        screening_criteria = (
            self.screening_criteria_repository.get_by_job_opportunity_id(
                job_opportunity.id
            )
        )

        if screening_criteria is None:
            return ApplicationStatusResponse(state="job_not_ready")

        candidate = self._resolve_candidate(email)

        if candidate is None:
            return ApplicationStatusResponse(state="can_apply")

        application = self.application_repository.get_by_candidate_and_job(
            candidate_id=candidate.id,
            job_opportunity_id=job_opportunity.id,
        )

        if application is None:
            return ApplicationStatusResponse(state="can_apply")

        screening_result = self.screening_repository.get_by_application_id(
            application.id
        )

        if screening_result is None:
            return ApplicationStatusResponse(
                state="screening_in_progress",
                application_id=application.id,
            )

        if screening_result.final_status != RECOMMENDED_SCREENING_STATUS:
            return ApplicationStatusResponse(
                state="rejected",
                application_id=application.id,
            )

        interview = self.interview_repository.get_by_application_id(
            application.id
        )

        if interview is None or interview.status != INTERVIEW_STATUS_COMPLETED:
            return ApplicationStatusResponse(
                state="approved_for_interview",
                application_id=application.id,
                interview_id=(
                    interview.id if interview is not None else None
                ),
            )

        return ApplicationStatusResponse(
            state="evaluation_in_progress",
            application_id=application.id,
            interview_id=interview.id,
        )

    def _resolve_candidate(self, email: str | None):
        if not email or not email.strip():
            return None

        user = self.user_repository.get_by_email(email.strip())

        if user is None:
            return None

        return self.candidate_repository.get_by_user_id(user.id)
