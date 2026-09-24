"""
Integration test wiring the real ApplicationService to the real
ApplicationRepository over an in-memory SQLite database.

The unit tests around this feature mock every collaborator
(tests/test_application_service.py). This file covers what that
can't: that creating an application really lands a row in the
database, and that a second attempt for the same candidate/job pair
is rejected by the real ``uq_applications_candidate_job_opportunity``
constraint, not just by the pre-check.

``job_opportunities``, ``user``, and ``resumes`` are not created here:
``job_opportunities``/``resumes`` use Postgres-only JSONB columns that
SQLite cannot compile (see tests/test_application_repository.py and
tests/test_candidate_ranking_integration.py for the same reasoning),
and User/Candidate resolution is already covered against a real
in-memory database in tests/test_user_repository.py and
tests/test_candidate_repository.py. JobOpportunityRepository,
UserRepository, CandidateRepository, SQLAlchemyResumeRepository, the CV
parser pipeline, the resume matching pipeline, and the screening
pipeline are therefore stubbed -- the matching/screening handoff itself
is covered by tests/test_application_service.py.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models.application import Application
from app.repositories.application_repository import ApplicationRepository
from app.schemas.screening_score import CategoryScore
from app.services.application_service import (
    ApplicationService,
    DuplicateApplicationError,
)

JOB_OPPORTUNITY_ID = 10
USER_ID = 5
CANDIDATE_ID = 1

APPLICANT_FIRST_NAME = "Lara"
APPLICANT_LAST_NAME = "Haddad"
APPLICANT_EMAIL = "lara@email.com"
APPLICANT_PHONE = "0599123456"

CATEGORY_NAMES = (
    "skills",
    "experience",
    "education",
    "projects",
    "certifications",
    "languages",
    "soft_skills",
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    Application.__table__.create(engine)

    session = sessionmaker(bind=engine)()

    try:
        yield session
    finally:
        session.close()


def _build_service(db_session):
    resume_repository = MagicMock()
    resume_repository.save.return_value = SimpleNamespace(id=200)

    job_opportunity_repository = MagicMock()
    job_opportunity_repository.get_by_id.return_value = SimpleNamespace(
        id=JOB_OPPORTUNITY_ID, status="published"
    )

    # User/Candidate resolution is unit tested in isolation in
    # tests/test_application_service.py; here they're stubbed to always
    # resolve to the same candidate_id, so this file can stay focused
    # on what it actually covers: the real ApplicationRepository and
    # its unique constraint.
    user_repository = MagicMock()
    user_repository.get_by_email.return_value = None
    user_repository.create.return_value = SimpleNamespace(id=USER_ID)

    candidate_repository = MagicMock()
    candidate_repository.get_by_user_id.return_value = None
    candidate_repository.create.return_value = SimpleNamespace(
        id=CANDIDATE_ID, user_id=USER_ID
    )

    cv_parser_pipeline = MagicMock()
    cv_parser_pipeline.parse.return_value = SimpleNamespace(
        resume_data=MagicMock()
    )

    resume_matching_pipeline = MagicMock()

    async def _fake_match_application(application_id: int):
        return SimpleNamespace(
            candidate_id=str(CANDIDATE_ID),
            job_id="JD-TEST",
            application_id=application_id,
            criteria_id=55,
            category_scores={
                name: CategoryScore(score=80, status="evaluated")
                for name in CATEGORY_NAMES
            },
            category_weights={
                name: 100 / 7 for name in CATEGORY_NAMES
            },
            matching_results=MagicMock(model_dump=lambda: {}),
            passing_score=70,
        )

    resume_matching_pipeline.match_application = AsyncMock(
        side_effect=_fake_match_application
    )

    screening_pipeline = MagicMock()

    screening_criteria_repository = MagicMock()
    screening_criteria_repository.get_by_job_opportunity_id.return_value = (
        SimpleNamespace(id=55)
    )

    # final_status is left as an unconfigured MagicMock attribute here,
    # which never equals "recommended" -- so this integration test's
    # candidates are never auto-approved and interview_creation_service
    # is never invoked. Interview auto-creation on a "recommended"
    # result is covered against mocks in test_application_service.py.
    interview_creation_service = MagicMock()

    service = ApplicationService(
        application_repository=ApplicationRepository(db_session),
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

    return service, resume_repository, resume_matching_pipeline, screening_pipeline


async def _submit(service):
    return await service.submit_application(
        job_opportunity_id=JOB_OPPORTUNITY_ID,
        first_name=APPLICANT_FIRST_NAME,
        last_name=APPLICANT_LAST_NAME,
        email=APPLICANT_EMAIL,
        phone=APPLICANT_PHONE,
        file_name="resume.pdf",
        content_type="application/pdf",
        file_bytes=b"%PDF-1.4 fake resume bytes",
    )


@pytest.mark.asyncio
async def test_submitting_an_application_creates_a_real_row(db_session):
    (
        service,
        resume_repository,
        resume_matching_pipeline,
        screening_pipeline,
    ) = _build_service(db_session)

    response = await _submit(service)
    db_session.commit()

    application = ApplicationRepository(db_session).get_by_id(
        response.application_id
    )

    assert application is not None
    assert application.candidate_id == CANDIDATE_ID
    assert application.job_opportunity_id == JOB_OPPORTUNITY_ID
    assert application.status == "applied"

    resume_repository.save.assert_called_once()
    assert (
        resume_repository.save.call_args.kwargs["application_id"]
        == application.id
    )

    # The real, flushed-but-not-yet-committed application id was what
    # got passed through to matching -- proof that this flow's matching
    # pipeline sees this transaction's own writes.
    resume_matching_pipeline.match_application.assert_awaited_once_with(
        application.id
    )
    screening_pipeline.score_candidate.assert_called_once()


@pytest.mark.asyncio
async def test_second_application_for_same_candidate_and_job_is_rejected(
    db_session,
):
    service, *_ = _build_service(db_session)

    await _submit(service)
    db_session.commit()

    with pytest.raises(DuplicateApplicationError):
        await _submit(service)


@pytest.mark.asyncio
async def test_different_candidates_can_both_apply_to_the_same_job(
    db_session,
):
    """Task 6/7, against the real ApplicationRepository and its
    uniqueness constraint: two different candidates -- each resolved
    from their own email, the way two different browsers (or one
    browser used by two different people, now that there is no
    candidateEmail localStorage dependency -- see Task 4) would --
    must both be able to apply to the same job. The constraint is on
    (candidate_id, job_opportunity_id), not on job_opportunity_id
    alone.
    """

    resume_repository = MagicMock()
    resume_repository.save.return_value = SimpleNamespace(id=200)

    job_opportunity_repository = MagicMock()
    job_opportunity_repository.get_by_id.return_value = SimpleNamespace(
        id=JOB_OPPORTUNITY_ID, status="published"
    )

    # Each distinct email resolves to its own User/Candidate id, the
    # same way the real UserRepository/CandidateRepository would --
    # this is what actually exercises "different candidates" rather
    # than every submission silently reusing one fixed candidate_id
    # (see _build_service above, which is deliberately simpler for
    # the same-candidate tests).
    next_id = {"value": 100}

    def _create_user(email, **_kwargs):
        next_id["value"] += 1
        return SimpleNamespace(id=next_id["value"], email=email)

    user_repository = MagicMock()
    user_repository.get_by_email.return_value = None
    user_repository.create.side_effect = _create_user

    def _create_candidate(user_id, **_kwargs):
        next_id["value"] += 1
        return SimpleNamespace(id=next_id["value"], user_id=user_id)

    candidate_repository = MagicMock()
    candidate_repository.get_by_user_id.return_value = None
    candidate_repository.create.side_effect = _create_candidate

    cv_parser_pipeline = MagicMock()
    cv_parser_pipeline.parse.return_value = SimpleNamespace(
        resume_data=MagicMock()
    )

    resume_matching_pipeline = MagicMock()

    async def _fake_match_application(application_id: int):
        return SimpleNamespace(
            candidate_id="ignored",
            job_id="JD-TEST",
            application_id=application_id,
            criteria_id=55,
            category_scores={
                name: CategoryScore(score=80, status="evaluated")
                for name in CATEGORY_NAMES
            },
            category_weights={
                name: 100 / 7 for name in CATEGORY_NAMES
            },
            matching_results=MagicMock(model_dump=lambda: {}),
            passing_score=70,
        )

    resume_matching_pipeline.match_application = AsyncMock(
        side_effect=_fake_match_application
    )

    screening_pipeline = MagicMock()

    screening_criteria_repository = MagicMock()
    screening_criteria_repository.get_by_job_opportunity_id.return_value = (
        SimpleNamespace(id=55)
    )

    interview_creation_service = MagicMock()

    service = ApplicationService(
        application_repository=ApplicationRepository(db_session),
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

    sara_response = await service.submit_application(
        job_opportunity_id=JOB_OPPORTUNITY_ID,
        first_name="Sara",
        last_name="Ahmad",
        email="sara.backend.test@example.com",
        phone="0599111111",
        file_name="resume.pdf",
        content_type="application/pdf",
        file_bytes=b"%PDF-1.4 sara resume",
    )
    db_session.commit()

    lina_response = await service.submit_application(
        job_opportunity_id=JOB_OPPORTUNITY_ID,
        first_name="Lina",
        last_name="Youssef",
        email="lina.backend.test@example.com",
        phone="0599222222",
        file_name="resume.pdf",
        content_type="application/pdf",
        file_bytes=b"%PDF-1.4 lina resume",
    )
    db_session.commit()

    repository = ApplicationRepository(db_session)

    assert sara_response.application_id != lina_response.application_id

    sara_application = repository.get_by_id(sara_response.application_id)
    lina_application = repository.get_by_id(lina_response.application_id)

    assert sara_application is not None
    assert lina_application is not None
    assert sara_application.job_opportunity_id == JOB_OPPORTUNITY_ID
    assert lina_application.job_opportunity_id == JOB_OPPORTUNITY_ID
    assert sara_application.candidate_id != lina_application.candidate_id


def test_the_real_unique_constraint_backs_up_the_pre_check(db_session):
    """Bypass the service's own pre-check to prove the DB constraint
    itself would catch a race between two concurrent submissions."""
    repository = ApplicationRepository(db_session)

    repository.create(
        candidate_id=CANDIDATE_ID,
        job_opportunity_id=JOB_OPPORTUNITY_ID,
        status="applied",
    )
    db_session.commit()

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        repository.create(
            candidate_id=CANDIDATE_ID,
            job_opportunity_id=JOB_OPPORTUNITY_ID,
            status="applied",
        )


@pytest.mark.asyncio
async def test_missing_screening_criteria_creates_no_row(db_session):
    """Task 1, against a real ApplicationRepository: when the job has
    no ScreeningCriteria, submitting must not leave a row behind."""
    from app.services.application_service import (
        JobNotReadyForApplicationsError,
    )

    service, *_ = _build_service(db_session)
    service.screening_criteria_repository.get_by_job_opportunity_id.return_value = (
        None
    )

    with pytest.raises(JobNotReadyForApplicationsError):
        await _submit(service)

    assert ApplicationRepository(db_session).get_by_candidate_and_job(
        candidate_id=CANDIDATE_ID,
        job_opportunity_id=JOB_OPPORTUNITY_ID,
    ) is None
