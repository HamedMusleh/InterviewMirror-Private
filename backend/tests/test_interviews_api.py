from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dependencies.db import get_db
from app.dependencies.interview import get_interview_creation_service
from app.dependencies.question_generation import (
    get_question_generation_service,
)
from app.modules.interviews import router as router_module
from app.modules.interviews.router import router
from app.services.interview_creation_service import (
    ApplicationNotFoundError,
    ApplicationNotRecommendedError,
    InterviewCreationResult,
    ScreeningResultNotFoundError,
)


CREATED_AT = datetime(2026, 9, 2, 8, 0, tzinfo=timezone.utc)
SCHEDULED_AT = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class FakeInterviewCreationService:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.application_id = None
        self.scheduled_at = None

    def create_for_application(self, application_id, scheduled_at=None):
        self.application_id = application_id
        self.scheduled_at = scheduled_at

        if self.error is not None:
            raise self.error

        return self.result


def _interview():
    return SimpleNamespace(
        id=31,
        application_id=7,
        scheduled_at=SCHEDULED_AT,
        started_at=None,
        ended_at=None,
        status="scheduled",
        created_at=CREATED_AT,
    )


@pytest.fixture
def api():
    """
    The API under test with question generation stubbed out.

    Generation is an LLM call with its own tests in
    test_interview_preparation.py; stubbing it here keeps these tests about
    status codes, transactions and error mapping.
    """

    app = FastAPI()
    app.include_router(router)
    session = FakeSession()
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_question_generation_service] = (
        lambda: object()
    )

    generate = AsyncMock(return_value=5)

    with patch.object(router_module, "ensure_interview_questions", generate):
        yield app, session, generate

    app.dependency_overrides.clear()


def _client(api, service):
    app, _, _generate = api
    app.dependency_overrides[get_interview_creation_service] = (
        lambda: service
    )
    return TestClient(app, raise_server_exceptions=False)


def test_create_interview_returns_201_and_commits(api):
    _app, _session, generate = api

    service = FakeInterviewCreationService(
        result=InterviewCreationResult(
            interview=_interview(),
            created=True,
        )
    )
    client = _client(api, service)

    response = client.post(
        "/api/interviews",
        json={
            "application_id": 7,
            "scheduled_at": "2026-09-03T10:00:00Z",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "interview": {
            "id": 31,
            "application_id": 7,
            "scheduled_at": "2026-09-03T10:00:00Z",
            "started_at": None,
            "ended_at": None,
            "status": "scheduled",
            "created_at": "2026-09-02T08:00:00Z",
        },
        "questions_generated": 5,
        "created": True,
    }
    assert service.application_id == 7
    assert service.scheduled_at == SCHEDULED_AT
    assert api[1].committed is True
    assert api[1].rolled_back is False

    # Questions are prepared for the interview that was just created.
    generate.assert_awaited_once()
    assert generate.await_args.kwargs["interview_id"] == 31


def test_retry_returns_200_and_does_not_report_a_new_row(api):
    service = FakeInterviewCreationService(
        result=InterviewCreationResult(
            interview=_interview(),
            created=False,
        )
    )
    client = _client(api, service)

    response = client.post(
        "/api/interviews",
        json={"application_id": 7},
    )

    assert response.status_code == 200
    assert response.json()["created"] is False
    assert response.json()["interview"]["id"] == 31
    assert api[1].committed is True


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (ApplicationNotFoundError("missing"), 404),
        (ScreeningResultNotFoundError("not screened"), 409),
        (ApplicationNotRecommendedError("not recommended"), 409),
    ],
)
def test_expected_creation_errors_are_mapped_and_rolled_back(
    api,
    error,
    expected_status,
):
    client = _client(
        api,
        FakeInterviewCreationService(error=error),
    )

    response = client.post(
        "/api/interviews",
        json={"application_id": 7},
    )

    assert response.status_code == expected_status
    assert response.json()["detail"] == str(error)
    assert api[1].rolled_back is True
    assert api[1].committed is False


def test_request_rejects_non_positive_application_id(api):
    client = _client(api, FakeInterviewCreationService())

    response = client.post(
        "/api/interviews",
        json={"application_id": 0},
    )

    assert response.status_code == 422


def test_request_rejects_a_schedule_without_timezone(api):
    client = _client(api, FakeInterviewCreationService())

    response = client.post(
        "/api/interviews",
        json={
            "application_id": 7,
            "scheduled_at": "2026-09-03T10:00:00",
        },
    )

    assert response.status_code == 422
