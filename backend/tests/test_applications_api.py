import io
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.dependencies.application import get_application_service
from app.dependencies.application_status import get_application_status_service
from app.dependencies.db import get_db
from app.dependencies.question_generation import (
    get_question_generation_service,
)
from app.main import app
from app.repositories.resume_matching_repository import (
    ResumeMatchingDataError,
    ResumeMatchingNotFoundError,
)
from app.schemas.application import ApplicationSubmitResponse
from app.schemas.application_status import ApplicationStatusResponse
from app.services.application_service import (
    DuplicateApplicationError,
    InvalidApplicantDataError,
    InvalidResumeFileError,
    JobNotReadyForApplicationsError,
    JobOpportunityNotFoundError,
)
from app.services.llm_client import (
    LLMConfigurationError,
    LLMRequestError,
    LLMResponseError,
)

ENDPOINT = "/api/applications"
STATUS_ENDPOINT = "/api/applications/status"

APPLIED_AT = datetime(2026, 8, 31, 9, 0, tzinfo=timezone.utc)


def _response(interview_id: int | None = None) -> ApplicationSubmitResponse:
    return ApplicationSubmitResponse(
        application_id=100,
        job_opportunity_id=10,
        resume_id=200,
        status="applied",
        applied_at=APPLIED_AT,
        interview_id=interview_id,
    )


class FakeApplicationService:
    """Stands in for ApplicationService, which is unit tested separately."""

    def __init__(
        self,
        error: Exception | None = None,
        interview_id: int | None = None,
    ):
        self._error = error
        self._interview_id = interview_id
        self.received_kwargs: dict | None = None

    async def submit_application(self, **kwargs):
        self.received_kwargs = kwargs

        if self._error is not None:
            raise self._error

        return _response(interview_id=self._interview_id)


class FakeSession:
    """Records the transaction calls the router makes."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


@pytest.fixture
def client():
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def session():
    fake_session = FakeSession()
    app.dependency_overrides[get_db] = lambda: fake_session

    return fake_session


def _override_service(service: FakeApplicationService) -> None:
    app.dependency_overrides[get_application_service] = lambda: service


def _post(
    client,
    *,
    job_opportunity_id=10,
    first_name="Lara",
    last_name="Haddad",
    email="lara@email.com",
    phone="0599123456",
    filename="resume.pdf",
    content_type="application/pdf",
    content=b"%PDF-1.4 fake",
):
    return client.post(
        ENDPOINT,
        data={
            "job_opportunity_id": str(job_opportunity_id),
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
        },
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


def test_submit_application_returns_201_and_commits(client, session):
    service = FakeApplicationService()
    _override_service(service)

    response = _post(client)

    assert response.status_code == 201
    body = response.json()
    assert body["application_id"] == 100
    assert body["resume_id"] == 200
    assert body["status"] == "applied"

    assert session.committed is True
    assert session.rolled_back is False

    assert service.received_kwargs["job_opportunity_id"] == 10
    assert service.received_kwargs["first_name"] == "Lara"
    assert service.received_kwargs["last_name"] == "Haddad"
    assert service.received_kwargs["email"] == "lara@email.com"
    assert service.received_kwargs["phone"] == "0599123456"
    assert service.received_kwargs["file_name"] == "resume.pdf"
    assert service.received_kwargs["content_type"] == "application/pdf"
    assert service.received_kwargs["file_bytes"] == b"%PDF-1.4 fake"


def test_submit_application_never_accepts_a_candidate_id_field(
    client, session
):
    """candidate_id is never part of the request contract: the backend
    resolves the candidate from email/name instead (see
    ApplicationService), matching the intent of the removed
    recruiter_id-style demo field."""
    service = FakeApplicationService()
    _override_service(service)

    response = _post(client)

    assert "candidate_id" not in response.json()
    assert "candidate_id" not in service.received_kwargs


def test_submit_application_returns_404_for_missing_job_and_rolls_back(
    client, session
):
    service = FakeApplicationService(
        error=JobOpportunityNotFoundError("Job opportunity 10 does not exist.")
    )
    _override_service(service)

    response = _post(client)

    assert response.status_code == 404
    assert session.rolled_back is True
    assert session.committed is False


def test_submit_application_returns_409_for_duplicate_and_rolls_back(
    client, session
):
    service = FakeApplicationService(
        error=DuplicateApplicationError("You have already applied to this job.")
    )
    _override_service(service)

    response = _post(client)

    assert response.status_code == 409
    assert session.rolled_back is True
    assert session.committed is False


def test_submit_application_returns_400_for_invalid_resume_and_rolls_back(
    client, session
):
    service = FakeApplicationService(
        error=InvalidResumeFileError("Only PDF and DOCX files are supported.")
    )
    _override_service(service)

    response = _post(client, content_type="image/png")

    assert response.status_code == 400
    assert session.rolled_back is True
    assert session.committed is False


def test_submit_application_returns_400_for_invalid_applicant_data_and_rolls_back(
    client, session
):
    service = FakeApplicationService(
        error=InvalidApplicantDataError("A valid email address is required.")
    )
    _override_service(service)

    response = _post(client, email="not-an-email")

    assert response.status_code == 400
    assert session.rolled_back is True
    assert session.committed is False


def test_submit_application_returns_500_for_unexpected_error_and_rolls_back(
    client, session
):
    service = FakeApplicationService(error=RuntimeError("boom"))
    _override_service(service)

    response = _post(client)

    assert response.status_code == 500
    assert session.rolled_back is True
    assert session.committed is False


def test_submit_application_returns_404_when_matching_data_is_missing(
    client, session
):
    """Covers a missing application/resume/job, and also a job with no
    screening criteria configured yet -- ResumeMatchingRepository raises
    the same error for all of them."""
    service = FakeApplicationService(
        error=ResumeMatchingNotFoundError(
            "Screening criteria for job opportunity 10 was not found"
        )
    )
    _override_service(service)

    response = _post(client)

    assert response.status_code == 404
    assert session.rolled_back is True
    assert session.committed is False


def test_submit_application_returns_500_for_invalid_stored_matching_data(
    client, session
):
    service = FakeApplicationService(
        error=ResumeMatchingDataError("Stored resume matching data is invalid")
    )
    _override_service(service)

    response = _post(client)

    assert response.status_code == 500
    assert session.rolled_back is True
    assert session.committed is False


def test_submit_application_returns_503_when_matching_ai_not_configured(
    client, session
):
    service = FakeApplicationService(error=LLMConfigurationError("no config"))
    _override_service(service)

    response = _post(client)

    assert response.status_code == 503
    assert session.rolled_back is True
    assert session.committed is False


def test_submit_application_returns_502_for_matching_ai_request_failure(
    client, session
):
    service = FakeApplicationService(error=LLMRequestError("timed out"))
    _override_service(service)

    response = _post(client)

    assert response.status_code == 502
    assert session.rolled_back is True
    assert session.committed is False


def test_submit_application_returns_502_for_matching_ai_response_failure(
    client, session
):
    service = FakeApplicationService(error=LLMResponseError("bad response"))
    _override_service(service)

    response = _post(client)

    assert response.status_code == 502
    assert session.rolled_back is True
    assert session.committed is False


def test_submit_application_requires_a_file(client, session):
    _override_service(FakeApplicationService())

    response = client.post(
        ENDPOINT,
        data={
            "job_opportunity_id": "10",
            "first_name": "Lara",
            "last_name": "Haddad",
            "email": "lara@email.com",
            "phone": "0599123456",
        },
    )

    assert response.status_code == 422


def test_submit_application_returns_422_for_missing_email(client, session):
    _override_service(FakeApplicationService())

    response = client.post(
        ENDPOINT,
        data={
            "job_opportunity_id": "10",
            "first_name": "Lara",
            "last_name": "Haddad",
            "phone": "0599123456",
        },
        files={"file": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )

    assert response.status_code == 422


def test_submit_application_returns_409_for_job_not_ready_and_rolls_back(
    client, session
):
    """Task 1: a job with no ScreeningCriteria yet must surface as a
    clear, distinct error -- not a generic 500 or a silent success."""
    service = FakeApplicationService(
        error=JobNotReadyForApplicationsError(
            "Job is not ready to accept applications yet."
        )
    )
    _override_service(service)

    response = _post(client)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Job is not ready to accept applications yet."
    )
    assert session.rolled_back is True
    assert session.committed is False


def test_submit_application_generates_interview_questions_when_approved(
    client, session, monkeypatch
):
    """Task 3, end to end at the router: once submit_application
    reports a real interview_id, the router triggers question
    generation for it (same best-effort pattern as
    /api/cv-parser/parse) after -- not before -- the commit."""
    calls: list[dict] = []

    async def fake_ensure_interview_questions(
        *, interview_id, db, generation_service
    ):
        calls.append({"interview_id": interview_id, "db": db})

    monkeypatch.setattr(
        "app.modules.applications.router.ensure_interview_questions",
        fake_ensure_interview_questions,
    )
    app.dependency_overrides[get_question_generation_service] = (
        lambda: object()
    )

    service = FakeApplicationService(interview_id=777)
    _override_service(service)

    response = _post(client)

    assert response.status_code == 201
    assert response.json()["interview_id"] == 777
    assert calls == [{"interview_id": 777, "db": session}]
    # Question generation only ran after the application/interview
    # were already committed.
    assert session.committed is True


def test_submit_application_skips_question_generation_when_not_approved(
    client, session, monkeypatch
):
    calls: list[dict] = []

    async def fake_ensure_interview_questions(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(
        "app.modules.applications.router.ensure_interview_questions",
        fake_ensure_interview_questions,
    )
    app.dependency_overrides[get_question_generation_service] = (
        lambda: object()
    )

    service = FakeApplicationService(interview_id=None)
    _override_service(service)

    response = _post(client)

    assert response.status_code == 201
    assert response.json()["interview_id"] is None
    assert calls == []


def test_submit_application_still_succeeds_if_question_generation_blows_up(
    client, session, monkeypatch
):
    """A failure while generating interview questions must never be
    reported back as a failed submission -- the application and
    interview are already committed by that point. ensure_interview_
    questions itself is documented to never raise, but this is the
    router's own safety net in case that ever changes."""

    async def blowing_up_ensure_interview_questions(**kwargs):
        raise RuntimeError("LLM is down")

    monkeypatch.setattr(
        "app.modules.applications.router.ensure_interview_questions",
        blowing_up_ensure_interview_questions,
    )
    app.dependency_overrides[get_question_generation_service] = (
        lambda: object()
    )

    service = FakeApplicationService(interview_id=777)
    _override_service(service)

    response = _post(client)

    assert response.status_code == 201
    assert response.json()["interview_id"] == 777
    assert session.committed is True
    assert session.rolled_back is False


class FakeApplicationStatusService:
    def __init__(
        self,
        error: Exception | None = None,
        response: ApplicationStatusResponse | None = None,
    ):
        self._error = error
        self._response = response or ApplicationStatusResponse(
            state="can_apply"
        )
        self.received_kwargs: dict | None = None

    def get_status(self, **kwargs):
        self.received_kwargs = kwargs

        if self._error is not None:
            raise self._error

        return self._response


def _override_status_service(service: FakeApplicationStatusService) -> None:
    app.dependency_overrides[get_application_status_service] = (
        lambda: service
    )


def test_get_application_status_returns_state_and_passes_through_params(
    client,
):
    service = FakeApplicationStatusService(
        response=ApplicationStatusResponse(
            state="approved_for_interview",
            application_id=100,
            interview_id=777,
        )
    )
    _override_status_service(service)

    response = client.get(
        STATUS_ENDPOINT,
        params={"job_id": "JD-TEST", "email": "lara@email.com"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "approved_for_interview"
    assert body["application_id"] == 100
    assert body["interview_id"] == 777
    assert service.received_kwargs == {
        "job_id": "JD-TEST",
        "email": "lara@email.com",
    }


def test_get_application_status_works_without_an_email(client):
    """A first-time visitor with nothing in browser storage yet still
    gets a state -- job readiness alone answers can_apply/job_not_ready."""
    service = FakeApplicationStatusService(
        response=ApplicationStatusResponse(state="job_not_ready")
    )
    _override_status_service(service)

    response = client.get(STATUS_ENDPOINT, params={"job_id": "JD-TEST"})

    assert response.status_code == 200
    assert response.json()["state"] == "job_not_ready"
    assert service.received_kwargs == {"job_id": "JD-TEST", "email": None}


def test_get_application_status_returns_404_for_missing_job(client):
    service = FakeApplicationStatusService(
        error=JobOpportunityNotFoundError("Job opportunity 'x' does not exist.")
    )
    _override_status_service(service)

    response = client.get(STATUS_ENDPOINT, params={"job_id": "x"})

    assert response.status_code == 404


def test_get_application_status_requires_job_id(client):
    service = FakeApplicationStatusService()
    _override_status_service(service)

    response = client.get(STATUS_ENDPOINT)

    assert response.status_code == 422
