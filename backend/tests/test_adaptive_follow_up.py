import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies.adaptive_follow_up import get_adaptive_follow_up_service
from app.schemas.adaptive_follow_up import (
    FollowUpQuestionRequest,
    FollowUpQuestionResponse,
)


ENDPOINT = "/api/interviews/follow-up"


class FakeFollowUpService:
    def generate_follow_up_question(
        self, request: FollowUpQuestionRequest
    ) -> FollowUpQuestionResponse | None:
        if not request.follow_up_needed:
            return None
        return FollowUpQuestionResponse(
            parent_question_id=request.question_id,
            question="Which FastAPI features did you use?",
            category=request.question_type,
            skill=request.skill,
        )


class FailingFollowUpService:
    def generate_follow_up_question(
        self, request: FollowUpQuestionRequest
    ) -> FollowUpQuestionResponse | None:
        raise ValueError("Failed to generate a follow-up question.")


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _valid_payload():
    return {
        "question_id": 25,
        "question": "Explain your experience with FastAPI.",
        "answer": "I used FastAPI to build REST APIs for a university project.",
        "question_type": "skills",
        "skill": "FastAPI",
        "missing_areas": ["No explanation of specific FastAPI features"],
        "follow_up_needed": True,
        "follow_up_reason": "The answer lacks technical depth.",
    }


def test_generate_follow_up_success(client):
    app.dependency_overrides[get_adaptive_follow_up_service] = (
        lambda: FakeFollowUpService()
    )

    response = client.post(ENDPOINT, json=_valid_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["question"]
    assert body["parent_question_id"] == 25
    assert body["category"] == "skills"
    assert body["skill"] == "FastAPI"


def test_no_follow_up_when_not_needed(client):
    app.dependency_overrides[get_adaptive_follow_up_service] = (
        lambda: FakeFollowUpService()
    )

    payload = _valid_payload()
    payload["follow_up_needed"] = False
    payload["follow_up_reason"] = None

    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 200
    assert response.json() is None


def test_reason_required_when_follow_up_needed(client):
    payload = _valid_payload()
    payload["follow_up_reason"] = None

    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 422


def test_empty_field_is_rejected(client):
    payload = _valid_payload()
    payload["question"] = "   "

    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 422


def test_missing_required_field_is_rejected(client):
    payload = _valid_payload()
    payload.pop("answer")

    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 422


def test_service_failure_bubbles_up(client):
    app.dependency_overrides[get_adaptive_follow_up_service] = (
        lambda: FailingFollowUpService()
    )

    with pytest.raises(ValueError):
        client.post(ENDPOINT, json=_valid_payload())