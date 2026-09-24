from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dependencies.candidate_report_storage import (
    get_candidate_report_handler,
)
from app.handlers.candidate_report_handler import (
    CandidateEvaluationNotFoundError,
    CandidateNotFoundError,
    CandidateReportAlreadyExistsError,
    CandidateReportNotFoundError,
    CandidateReportRelationshipError,
    InterviewNotFoundError,
)
from app.modules.candidate_report.router import router
from app.schemas.candidate_report import CandidateReportResponse


def _response() -> CandidateReportResponse:
    return CandidateReportResponse(
        report_id=7,
        candidate_evaluation_id=1,
        candidate_id=12,
        interview_id=4,
        job_title="Backend Developer",
        candidate_name="Ahmad Khalil",
        overall_score=78,
        skill_scores={"Python": 85, "FastAPI": 75},
        summary=(
            "The candidate demonstrated good backend development "
            "knowledge and relevant practical experience."
        ),
        strengths=[
            "Strong Python knowledge",
            "Relevant backend experience",
        ],
        areas_for_improvement=[
            "Needs greater technical depth in FastAPI"
        ],
        recommendation=(
            "The candidate demonstrates good potential for the role."
        ),
    )


def _request_body() -> dict:
    return {
        "candidate_evaluation_id": 1,
        "interview_id": 4,
        "overall_score": 78,
        "skill_scores": {"Python": 85, "FastAPI": 75},
        "summary": "The candidate demonstrated good backend knowledge.",
        "strengths": ["Strong Python knowledge"],
        "areas_for_improvement": [
            "Needs greater technical depth in FastAPI"
        ],
        "recommendation": (
            "The candidate demonstrates good potential for the role."
        ),
    }


def _client_with_handler(handler) -> TestClient:
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_candidate_report_handler] = (
        lambda: handler
    )
    return TestClient(test_app)


# --------------------------------------------------------------------------
# POST /api/interviews/{interview_id}/report
# --------------------------------------------------------------------------


def test_post_stores_report_and_returns_full_contract():
    class FakeHandler:
        def store_report(self, interview_id, report):
            assert interview_id == 4
            assert report.candidate_evaluation_id == 1
            return _response()

    client = _client_with_handler(FakeHandler())

    response = client.post(
        "/api/interviews/4/report",
        json=_request_body(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "report_id": 7,
        "candidate_evaluation_id": 1,
        "candidate_id": 12,
        "interview_id": 4,
        "job_title": "Backend Developer",
        "candidate_name": "Ahmad Khalil",
        "overall_score": 78,
        "skill_scores": {"Python": 85, "FastAPI": 75},
        "summary": (
            "The candidate demonstrated good backend development "
            "knowledge and relevant practical experience."
        ),
        "strengths": [
            "Strong Python knowledge",
            "Relevant backend experience",
        ],
        "areas_for_improvement": [
            "Needs greater technical depth in FastAPI"
        ],
        "recommendation": (
            "The candidate demonstrates good potential for the role."
        ),
    }


def test_post_returns_404_for_invalid_interview():
    class FakeHandler:
        def store_report(self, interview_id, report):
            raise InterviewNotFoundError("Interview 4 was not found.")

    client = _client_with_handler(FakeHandler())

    response = client.post(
        "/api/interviews/4/report",
        json=_request_body(),
    )

    assert response.status_code == 404


def test_post_returns_404_for_invalid_candidate():
    class FakeHandler:
        def store_report(self, interview_id, report):
            raise CandidateNotFoundError("Candidate was not found.")

    client = _client_with_handler(FakeHandler())

    response = client.post(
        "/api/interviews/4/report",
        json=_request_body(),
    )

    assert response.status_code == 404


def test_post_returns_404_for_invalid_candidate_evaluation():
    class FakeHandler:
        def store_report(self, interview_id, report):
            raise CandidateEvaluationNotFoundError(
                "Candidate evaluation 1 was not found."
            )

    client = _client_with_handler(FakeHandler())

    response = client.post(
        "/api/interviews/4/report",
        json=_request_body(),
    )

    assert response.status_code == 404


def test_post_returns_409_for_relationship_mismatch():
    class FakeHandler:
        def store_report(self, interview_id, report):
            raise CandidateReportRelationshipError(
                "Candidate evaluation does not belong to this interview."
            )

    client = _client_with_handler(FakeHandler())

    response = client.post(
        "/api/interviews/4/report",
        json=_request_body(),
    )

    assert response.status_code == 409


def test_post_returns_409_when_report_already_exists():
    class FakeHandler:
        def store_report(self, interview_id, report):
            raise CandidateReportAlreadyExistsError(
                "A candidate report already exists for this evaluation."
            )

    client = _client_with_handler(FakeHandler())

    response = client.post(
        "/api/interviews/4/report",
        json=_request_body(),
    )

    assert response.status_code == 409


# --------------------------------------------------------------------------
# GET /api/interviews/{interview_id}/report
# --------------------------------------------------------------------------


def test_get_returns_full_contract():
    class FakeHandler:
        def get_report(self, interview_id):
            assert interview_id == 4
            return _response()

    client = _client_with_handler(FakeHandler())

    response = client.get("/api/interviews/4/report")

    assert response.status_code == 200
    body = response.json()
    assert body["report_id"] == 7
    assert body["candidate_evaluation_id"] == 1
    assert body["candidate_id"] == 12
    assert body["candidate_name"] == "Ahmad Khalil"
    assert body["job_title"] == "Backend Developer"
    assert body["overall_score"] == 78
    assert body["skill_scores"] == {"Python": 85, "FastAPI": 75}


def test_get_returns_404_when_report_not_found():
    class FakeHandler:
        def get_report(self, interview_id):
            raise CandidateReportNotFoundError(
                "Candidate report for interview 4 was not found."
            )

    client = _client_with_handler(FakeHandler())

    response = client.get("/api/interviews/4/report")

    assert response.status_code == 404


def test_get_returns_404_when_evaluation_not_ready():
    class FakeHandler:
        def get_report(self, interview_id):
            raise CandidateEvaluationNotFoundError(
                "No candidate evaluation exists yet for interview 4."
            )

    client = _client_with_handler(FakeHandler())

    response = client.get("/api/interviews/4/report")

    assert response.status_code == 404
