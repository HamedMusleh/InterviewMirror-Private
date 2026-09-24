from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from app.schemas.resume_matching import (
    DatabaseMatchingResponse,
    EducationMatchingResult,
    ExperienceMatchingResult,
    ListMatchingResult,
    MatchingResults,
    ProjectsMatchingResult,
    SkillsMatchingResult,
)
from app.schemas.screening_score import CategoryScore
from app.services.application_service import (
    ApplicationService,
    DuplicateApplicationError,
    InvalidApplicantDataError,
    InvalidResumeFileError,
    JobNotReadyForApplicationsError,
    JobOpportunityNotFoundError,
)

JOB_OPPORTUNITY_ID = 10
OTHER_JOB_OPPORTUNITY_ID = 20
USER_ID = 5
CANDIDATE_ID = 1

APPLICANT_FIRST_NAME = "Lara"
APPLICANT_LAST_NAME = "Haddad"
APPLICANT_EMAIL = "lara@email.com"
APPLICANT_PHONE = "0599123456"

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument"
    ".wordprocessingml.document"
)

CATEGORY_NAMES = (
    "skills",
    "experience",
    "education",
    "projects",
    "certifications",
    "languages",
    "soft_skills",
)


def _matching_results() -> MatchingResults:
    return MatchingResults(
        skills=SkillsMatchingResult(
            score=80, status="evaluated", required=[], preferred=[]
        ),
        experience=ExperienceMatchingResult(
            score=80,
            status="evaluated",
            candidate_years=3,
            required_years=2,
            level_match=True,
            evidence=[],
        ),
        projects=ProjectsMatchingResult(
            score=80, status="evaluated", matches=[]
        ),
        education=EducationMatchingResult(
            score=80,
            status="evaluated",
            matched_field="Computer Science",
            evidence=None,
        ),
        certifications=ListMatchingResult(
            score=80, status="evaluated", matched=[], missing=[]
        ),
        languages=ListMatchingResult(
            score=80, status="evaluated", matched=[], missing=[]
        ),
        soft_skills=ListMatchingResult(
            score=80, status="evaluated", matched=[], missing=[]
        ),
    )


def _matching_result(
    application_id: int = 100,
    job_opportunity_id: int = JOB_OPPORTUNITY_ID,
    candidate_id: int = CANDIDATE_ID,
) -> DatabaseMatchingResponse:
    return DatabaseMatchingResponse(
        candidate_id=str(candidate_id),
        job_id="JD-TEST",
        matching_results=_matching_results(),
        application_id=application_id,
        job_opportunity_id=job_opportunity_id,
        criteria_id=55,
        category_scores={
            name: CategoryScore(score=80, status="evaluated")
            for name in CATEGORY_NAMES
        },
        category_weights={name: 100 / 7 for name in CATEGORY_NAMES},
        passing_score=70,
    )


def _build_service(
    *,
    job_opportunity=SimpleNamespace(
        id=JOB_OPPORTUNITY_ID, status="published"
    ),
    existing_application=None,
    existing_user=None,
    existing_candidate=None,
    screening_criteria=SimpleNamespace(id=55),
    screening_final_status="not_recommended",
    interview_id=999,
):
    resolved_user_id = existing_user.id if existing_user is not None else USER_ID
    resolved_candidate_id = (
        existing_candidate.id if existing_candidate is not None else CANDIDATE_ID
    )

    application_repository = MagicMock()
    application_repository.get_by_candidate_and_job.return_value = (
        existing_application
    )
    application_repository.create.return_value = SimpleNamespace(
        id=100,
        candidate_id=resolved_candidate_id,
        job_opportunity_id=JOB_OPPORTUNITY_ID,
        status="applied",
        applied_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    resume_repository = MagicMock()
    resume_repository.save.return_value = SimpleNamespace(id=200)

    job_opportunity_repository = MagicMock()
    job_opportunity_repository.get_by_id.return_value = job_opportunity

    user_repository = MagicMock()
    user_repository.get_by_email.return_value = existing_user
    user_repository.create.return_value = SimpleNamespace(
        id=resolved_user_id, email=APPLICANT_EMAIL
    )

    candidate_repository = MagicMock()
    candidate_repository.get_by_user_id.return_value = existing_candidate
    candidate_repository.create.return_value = SimpleNamespace(
        id=resolved_candidate_id, user_id=resolved_user_id
    )

    cv_parser_pipeline = MagicMock()
    cv_parser_pipeline.parse.return_value = SimpleNamespace(
        resume_data=MagicMock()
    )

    resume_matching_pipeline = MagicMock()
    resume_matching_pipeline.match_application = AsyncMock(
        return_value=_matching_result(candidate_id=resolved_candidate_id)
    )

    screening_pipeline = MagicMock()
    screening_pipeline.score_candidate.return_value = SimpleNamespace(
        final_status=screening_final_status
    )

    screening_criteria_repository = MagicMock()
    screening_criteria_repository.get_by_job_opportunity_id.return_value = (
        screening_criteria
    )

    interview_creation_service = MagicMock()
    interview_creation_service.create_for_application.return_value = (
        SimpleNamespace(
            interview=SimpleNamespace(id=interview_id),
            created=True,
        )
    )

    service = ApplicationService(
        application_repository=application_repository,
        resume_repository=resume_repository,
        job_opportunity_repository=job_opportunity_repository,
        user_repository=user_repository,
        candidate_repository=candidate_repository,
        screening_criteria_repository=screening_criteria_repository,
        cv_parser_pipeline=cv_parser_pipeline,
        resume_matching_pipeline=resume_matching_pipeline,
        screening_pipeline=screening_pipeline,
        interview_creation_service=interview_creation_service,
    )

    return (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    )


async def _submit(service, **overrides):
    kwargs = {
        "job_opportunity_id": JOB_OPPORTUNITY_ID,
        "first_name": APPLICANT_FIRST_NAME,
        "last_name": APPLICANT_LAST_NAME,
        "email": APPLICANT_EMAIL,
        "phone": APPLICANT_PHONE,
        "file_name": "resume.pdf",
        "content_type": PDF_CONTENT_TYPE,
        "file_bytes": b"%PDF-1.4 fake resume bytes",
    }
    kwargs.update(overrides)

    return await service.submit_application(**kwargs)


@pytest.mark.asyncio
async def test_submit_application_success_creates_application_then_resume():
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service()

    response = await _submit(service)

    job_opportunity_repository.get_by_id.assert_called_once_with(
        JOB_OPPORTUNITY_ID
    )
    application_repository.get_by_candidate_and_job.assert_called_once_with(
        candidate_id=CANDIDATE_ID,
        job_opportunity_id=JOB_OPPORTUNITY_ID,
    )
    application_repository.create.assert_called_once_with(
        candidate_id=CANDIDATE_ID,
        job_opportunity_id=JOB_OPPORTUNITY_ID,
        status="applied",
    )
    cv_parser_pipeline.parse.assert_called_once_with(
        b"%PDF-1.4 fake resume bytes"
    )

    save_kwargs = resume_repository.save.call_args.kwargs
    assert save_kwargs["application_id"] == 100
    assert save_kwargs["file_name"] == "resume.pdf"
    assert save_kwargs["file_type"] == PDF_CONTENT_TYPE
    assert save_kwargs["file_data"] == b"%PDF-1.4 fake resume bytes"
    assert save_kwargs["file_size"] == len(b"%PDF-1.4 fake resume bytes")

    assert response.application_id == 100
    assert response.job_opportunity_id == JOB_OPPORTUNITY_ID
    assert response.resume_id == 200
    assert response.status == "applied"


@pytest.mark.asyncio
async def test_submit_application_accepts_docx():
    service, *_ = _build_service()

    response = await _submit(service, content_type=DOCX_CONTENT_TYPE)

    assert response.application_id == 100


@pytest.mark.asyncio
async def test_submit_application_creates_new_user_and_candidate_for_new_email():
    """New email: no matching User/Candidate exists yet, so both are
    created and the database-generated candidate.id is what the
    application is created with."""
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service()

    await _submit(service)

    user_repository.get_by_email.assert_called_once_with(APPLICANT_EMAIL)
    user_repository.create.assert_called_once_with(
        email=APPLICANT_EMAIL,
        first_name=APPLICANT_FIRST_NAME,
        last_name=APPLICANT_LAST_NAME,
        password_hash=ANY,
        role="candidate",
    )

    candidate_repository.get_by_user_id.assert_called_once_with(USER_ID)
    candidate_repository.create.assert_called_once_with(
        user_id=USER_ID,
        phone=APPLICANT_PHONE,
    )

    application_repository.create.assert_called_once_with(
        candidate_id=CANDIDATE_ID,
        job_opportunity_id=JOB_OPPORTUNITY_ID,
        status="applied",
    )


@pytest.mark.asyncio
async def test_submit_application_reuses_existing_user_and_candidate_for_known_email():
    """Existing email: both the User and Candidate it already resolves
    to are reused as-is -- no duplicate User/Candidate is created."""
    existing_user = SimpleNamespace(id=USER_ID, email=APPLICANT_EMAIL)
    existing_candidate = SimpleNamespace(id=CANDIDATE_ID, user_id=USER_ID)

    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service(
        existing_user=existing_user,
        existing_candidate=existing_candidate,
    )

    await _submit(service)

    user_repository.get_by_email.assert_called_once_with(APPLICANT_EMAIL)
    user_repository.create.assert_not_called()

    candidate_repository.get_by_user_id.assert_called_once_with(USER_ID)
    candidate_repository.create.assert_not_called()

    application_repository.create.assert_called_once_with(
        candidate_id=CANDIDATE_ID,
        job_opportunity_id=JOB_OPPORTUNITY_ID,
        status="applied",
    )


@pytest.mark.asyncio
async def test_submit_application_creates_candidate_for_existing_user_without_one():
    """A User can exist without a linked Candidate yet (e.g. created
    through some other flow); the Candidate is created and linked to
    that existing User rather than creating a second User."""
    existing_user = SimpleNamespace(id=USER_ID, email=APPLICANT_EMAIL)

    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service(existing_user=existing_user)

    await _submit(service)

    user_repository.create.assert_not_called()

    candidate_repository.get_by_user_id.assert_called_once_with(USER_ID)
    candidate_repository.create.assert_called_once_with(
        user_id=USER_ID,
        phone=APPLICANT_PHONE,
    )


@pytest.mark.asyncio
async def test_submit_application_reuses_candidate_id_for_second_job_application():
    """Same candidate applying to a different job: the same
    candidate_id is reused and the new application succeeds."""
    existing_user = SimpleNamespace(id=USER_ID, email=APPLICANT_EMAIL)
    existing_candidate = SimpleNamespace(id=CANDIDATE_ID, user_id=USER_ID)

    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service(
        job_opportunity=SimpleNamespace(
            id=OTHER_JOB_OPPORTUNITY_ID, status="published"
        ),
        existing_user=existing_user,
        existing_candidate=existing_candidate,
    )

    await _submit(service, job_opportunity_id=OTHER_JOB_OPPORTUNITY_ID)

    application_repository.get_by_candidate_and_job.assert_called_once_with(
        candidate_id=CANDIDATE_ID,
        job_opportunity_id=OTHER_JOB_OPPORTUNITY_ID,
    )
    application_repository.create.assert_called_once_with(
        candidate_id=CANDIDATE_ID,
        job_opportunity_id=OTHER_JOB_OPPORTUNITY_ID,
        status="applied",
    )


@pytest.mark.asyncio
async def test_submit_application_raises_when_job_does_not_exist():
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service(job_opportunity=None)

    with pytest.raises(JobOpportunityNotFoundError):
        await _submit(service)

    # The candidate identity is never touched for a job that doesn't
    # exist -- no stray User/Candidate rows get created.
    user_repository.get_by_email.assert_not_called()
    user_repository.create.assert_not_called()
    candidate_repository.get_by_user_id.assert_not_called()
    candidate_repository.create.assert_not_called()
    application_repository.create.assert_not_called()
    resume_repository.save.assert_not_called()
    resume_matching_pipeline.match_application.assert_not_called()
    screening_pipeline.score_candidate.assert_not_called()


@pytest.mark.asyncio
async def test_submit_application_raises_on_duplicate_application():
    existing_user = SimpleNamespace(id=USER_ID, email=APPLICANT_EMAIL)
    existing_candidate = SimpleNamespace(id=CANDIDATE_ID, user_id=USER_ID)

    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service(
        existing_user=existing_user,
        existing_candidate=existing_candidate,
        existing_application=SimpleNamespace(id=1),
    )

    with pytest.raises(DuplicateApplicationError):
        await _submit(service)

    application_repository.create.assert_not_called()
    resume_repository.save.assert_not_called()
    resume_matching_pipeline.match_application.assert_not_called()
    screening_pipeline.score_candidate.assert_not_called()


@pytest.mark.asyncio
async def test_submit_application_rejects_unsupported_file_type():
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service()

    with pytest.raises(InvalidResumeFileError):
        await _submit(service, content_type="image/png")

    job_opportunity_repository.get_by_id.assert_not_called()
    user_repository.get_by_email.assert_not_called()
    application_repository.create.assert_not_called()


@pytest.mark.asyncio
async def test_submit_application_rejects_empty_file():
    service, application_repository, *_ = _build_service()

    with pytest.raises(InvalidResumeFileError):
        await _submit(service, file_bytes=b"")

    application_repository.create.assert_not_called()


@pytest.mark.asyncio
async def test_submit_application_rejects_oversized_file():
    service, application_repository, *_ = _build_service()

    oversized = b"x" * (10 * 1024 * 1024 + 1)

    with pytest.raises(InvalidResumeFileError):
        await _submit(service, file_bytes=oversized)

    application_repository.create.assert_not_called()


@pytest.mark.asyncio
async def test_submit_application_rejects_missing_first_name():
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service()

    with pytest.raises(InvalidApplicantDataError):
        await _submit(service, first_name="   ")

    job_opportunity_repository.get_by_id.assert_not_called()
    user_repository.get_by_email.assert_not_called()
    application_repository.create.assert_not_called()


@pytest.mark.asyncio
async def test_submit_application_rejects_missing_last_name():
    service, application_repository, *_ = _build_service()

    with pytest.raises(InvalidApplicantDataError):
        await _submit(service, last_name="")

    application_repository.create.assert_not_called()


@pytest.mark.asyncio
async def test_submit_application_rejects_invalid_email():
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service()

    with pytest.raises(InvalidApplicantDataError):
        await _submit(service, email="not-an-email")

    user_repository.get_by_email.assert_not_called()
    application_repository.create.assert_not_called()


@pytest.mark.asyncio
async def test_submit_application_does_not_save_resume_when_parsing_fails():
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service()
    cv_parser_pipeline.parse.side_effect = RuntimeError("parsing blew up")

    with pytest.raises(RuntimeError):
        await _submit(service)

    # The application row was created (it's the caller/router's job to
    # roll the whole transaction back), but the resume never got saved,
    # and matching/screening never ran.
    application_repository.create.assert_called_once()
    resume_repository.save.assert_not_called()
    resume_matching_pipeline.match_application.assert_not_called()
    screening_pipeline.score_candidate.assert_not_called()


@pytest.mark.asyncio
async def test_submit_application_runs_matching_then_screening_in_order():
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service()

    await _submit(service)

    resume_matching_pipeline.match_application.assert_awaited_once_with(100)
    screening_pipeline.score_candidate.assert_called_once()

    screening_request = screening_pipeline.score_candidate.call_args.args[0]
    assert screening_request.candidate_id == str(CANDIDATE_ID)
    assert screening_request.job_id == "JD-TEST"
    assert screening_request.application_id == 100
    assert screening_request.criteria_id == 55
    assert screening_request.passing_score == 70
    assert set(screening_request.category_scores) == set(CATEGORY_NAMES)
    assert set(screening_request.category_weights) == set(CATEGORY_NAMES)


@pytest.mark.asyncio
async def test_submit_application_matching_failure_skips_screening():
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service()
    resume_matching_pipeline.match_application.side_effect = RuntimeError(
        "matching blew up"
    )

    with pytest.raises(RuntimeError):
        await _submit(service)

    # Application + resume were created/saved (it's the caller/router's
    # job to roll the whole transaction back on failure), but screening
    # never ran without a matching result to score.
    application_repository.create.assert_called_once()
    resume_repository.save.assert_called_once()
    screening_pipeline.score_candidate.assert_not_called()


@pytest.mark.asyncio
async def test_submit_application_screening_failure_propagates():
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service()
    screening_pipeline.score_candidate.side_effect = RuntimeError(
        "screening blew up"
    )

    with pytest.raises(RuntimeError):
        await _submit(service)

    resume_matching_pipeline.match_application.assert_awaited_once()
    screening_pipeline.score_candidate.assert_called_once()


@pytest.mark.asyncio
async def test_submit_application_rejects_job_with_no_screening_criteria():
    """Task 1: a job with no ScreeningCriteria must reject the
    submission before any User/Candidate/Application/Resume is
    created, and before matching/screening ever run."""
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service(screening_criteria=None)

    with pytest.raises(JobNotReadyForApplicationsError):
        await _submit(service)

    service.screening_criteria_repository.get_by_job_opportunity_id.assert_called_once_with(
        JOB_OPPORTUNITY_ID
    )
    user_repository.get_by_email.assert_not_called()
    user_repository.create.assert_not_called()
    candidate_repository.get_by_user_id.assert_not_called()
    candidate_repository.create.assert_not_called()
    application_repository.create.assert_not_called()
    resume_repository.save.assert_not_called()
    resume_matching_pipeline.match_application.assert_not_called()
    screening_pipeline.score_candidate.assert_not_called()


@pytest.mark.asyncio
async def test_submit_application_checks_screening_criteria_before_job_opportunity_lookup_order():
    """The screening-criteria check happens only once a job is known
    to exist -- a missing job still surfaces as
    JobOpportunityNotFoundError, not JobNotReadyForApplicationsError."""
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service(job_opportunity=None, screening_criteria=None)

    with pytest.raises(JobOpportunityNotFoundError):
        await _submit(service)

    service.screening_criteria_repository.get_by_job_opportunity_id.assert_not_called()


@pytest.mark.asyncio
async def test_submit_application_creates_interview_when_screening_recommends():
    """Task 3: a recommended screening result must produce a real
    Interview via the existing InterviewCreationService, and its id
    is surfaced on the response so the frontend never fabricates
    one."""
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service(
        screening_final_status="recommended",
        interview_id=777,
    )

    response = await _submit(service)

    service.interview_creation_service.create_for_application.assert_called_once_with(
        application_id=100,
    )
    assert response.interview_id == 777


@pytest.mark.asyncio
async def test_submit_application_does_not_create_interview_when_not_recommended():
    (
        service,
        application_repository,
        resume_repository,
        job_opportunity_repository,
        user_repository,
        candidate_repository,
        cv_parser_pipeline,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service(screening_final_status="not_recommended")

    response = await _submit(service)

    service.interview_creation_service.create_for_application.assert_not_called()
    assert response.interview_id is None
