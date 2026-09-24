from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.dependencies.candidate_ranking import get_candidate_ranking_service
from app.dependencies.db import get_db
from app.main import app
from app.schemas.candidate_ranking import (
    CandidateRankingListResponse,
    CandidateRankingRequest,
    RankedCandidate,
)
from app.services.candidate_ranking_service import (
    InvalidRankingEntryError,
    JobOpportunityNotFoundError,
)


ENDPOINT = "/api/candidate-rankings/10"

CREATED_AT = datetime(2026, 8, 27, 9, 0, tzinfo=timezone.utc)

VALID_REQUEST = {
    "rankings": [
        {"application_id": 1, "interview_id": 1, "overall_score": 91.0},
        {"application_id": 2, "interview_id": 2, "overall_score": 74.5},
    ]
}


def _response(job_opportunity_id: int = 10) -> CandidateRankingListResponse:
    return CandidateRankingListResponse(
        job_opportunity_id=job_opportunity_id,
        rankings=[
            RankedCandidate(
                rank=1,
                candidate_id=1,
                candidate_name="Dana Khoury",
                candidate_email="dana@example.com",
                application_id=1,
                interview_id=1,
                overall_score=91.0,
                created_at=CREATED_AT,
            ),
            RankedCandidate(
                rank=2,
                candidate_id=2,
                candidate_name="Omar Nasser",
                candidate_email="omar@example.com",
                application_id=2,
                interview_id=2,
                overall_score=74.5,
                created_at=CREATED_AT,
            ),
        ],
    )


class FakeRankingService:
    """Stands in for CandidateRankingService, which is unit tested separately."""

    def __init__(self, error: Exception | None = None):
        self._error = error
        self.stored_request: CandidateRankingRequest | None = None

    def get_ranked_candidates(
        self,
        job_opportunity_id: int,
    ) -> CandidateRankingListResponse:
        if self._error is not None:
            raise self._error

        return _response(job_opportunity_id)

    def replace_rankings(
        self,
        job_opportunity_id: int,
        request: CandidateRankingRequest,
    ) -> CandidateRankingListResponse:
        if self._error is not None:
            raise self._error

        self.stored_request = request

        if not request.rankings:
            return CandidateRankingListResponse(
                job_opportunity_id=job_opportunity_id,
                rankings=[],
            )

        return _response(job_opportunity_id)


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


def _override_service(service: FakeRankingService) -> None:
    app.dependency_overrides[get_candidate_ranking_service] = lambda: service


def test_get_returns_the_ranked_candidate_list(client):
    _override_service(FakeRankingService())

    response = client.get(ENDPOINT)

    assert response.status_code == 200

    body = response.json()

    assert body["job_opportunity_id"] == 10
    assert [entry["rank"] for entry in body["rankings"]] == [1, 2]
    assert [entry["candidate_name"] for entry in body["rankings"]] == [
        "Dana Khoury",
        "Omar Nasser",
    ]


def test_get_returns_404_for_an_unknown_job_opportunity(client):
    _override_service(
        FakeRankingService(
            JobOpportunityNotFoundError("Job opportunity 10 does not exist.")
        )
    )

    response = client.get(ENDPOINT)

    assert response.status_code == 404
    assert response.json()["detail"] == "Job opportunity 10 does not exist."


def test_get_returns_500_without_leaking_internal_details(client):
    _override_service(FakeRankingService(RuntimeError("connection refused")))

    response = client.get(ENDPOINT)

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Failed to retrieve the ranked candidate list."
    )
    assert "connection refused" not in response.text


def test_get_rejects_a_non_positive_job_opportunity_id(client):
    _override_service(FakeRankingService())

    response = client.get("/api/candidate-rankings/0")

    assert response.status_code == 422


def test_post_stores_the_rankings_and_commits(client, session):
    service = FakeRankingService()
    _override_service(service)

    response = client.post(ENDPOINT, json=VALID_REQUEST)

    assert response.status_code == 201
    assert session.committed is True
    assert session.rolled_back is False

    assert service.stored_request is not None
    assert [
        entry.application_id for entry in service.stored_request.rankings
    ] == [1, 2]

    assert [entry["rank"] for entry in response.json()["rankings"]] == [1, 2]


def test_post_returns_404_for_an_unknown_job_opportunity(client, session):
    _override_service(
        FakeRankingService(
            JobOpportunityNotFoundError("Job opportunity 10 does not exist.")
        )
    )

    response = client.post(ENDPOINT, json=VALID_REQUEST)

    assert response.status_code == 404
    assert session.rolled_back is True
    assert session.committed is False


def test_post_returns_422_for_entries_that_do_not_fit_the_job(client, session):
    _override_service(
        FakeRankingService(
            InvalidRankingEntryError(
                "Applications [2] do not belong to job opportunity 10."
            )
        )
    )

    response = client.post(ENDPOINT, json=VALID_REQUEST)

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Applications [2] do not belong to job opportunity 10."
    )
    assert session.rolled_back is True


def test_post_rolls_back_and_returns_500_on_an_unexpected_failure(
    client,
    session,
):
    _override_service(FakeRankingService(RuntimeError("connection refused")))

    response = client.post(ENDPOINT, json=VALID_REQUEST)

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Failed to store the ranked candidate list."
    )
    assert "connection refused" not in response.text
    assert session.rolled_back is True
    assert session.committed is False


def test_post_accepts_an_empty_list_to_clear_stored_rankings(client, session):
    service = FakeRankingService()
    _override_service(service)

    response = client.post(ENDPOINT, json={"rankings": []})

    assert response.status_code == 201
    assert response.json()["rankings"] == []
    assert session.committed is True
    assert service.stored_request is not None
    assert service.stored_request.rankings == []


def test_post_rejects_a_score_outside_the_zero_to_hundred_scale(
    client,
    session,
):
    _override_service(FakeRankingService())

    response = client.post(
        ENDPOINT,
        json={
            "rankings": [
                {
                    "application_id": 1,
                    "interview_id": 1,
                    "overall_score": 101,
                }
            ]
        },
    )

    assert response.status_code == 422
