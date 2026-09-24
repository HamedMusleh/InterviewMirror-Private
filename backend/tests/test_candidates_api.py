import pytest
from fastapi.testclient import TestClient

from app.dependencies.candidate import get_candidate_service
from app.main import app
from app.schemas.candidate import CandidateInfoResponse
from app.services.candidate_service import CandidateNotFoundError

ENDPOINT = "/api/candidates/1"


class FakeCandidateService:
    def __init__(self, response=None, error: Exception | None = None):
        self._response = response
        self._error = error

    def get_candidate_info(self, candidate_id: int) -> CandidateInfoResponse:
        if self._error is not None:
            raise self._error

        return self._response


@pytest.fixture
def client():
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _override_service(service) -> None:
    app.dependency_overrides[get_candidate_service] = lambda: service


def test_get_candidate_returns_name_and_phone(client):
    _override_service(
        FakeCandidateService(
            response=CandidateInfoResponse(
                first_name="Lina",
                last_name="Odeh",
                phone="+970-59-000-0000",
            )
        )
    )

    response = client.get(ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "first_name": "Lina",
        "last_name": "Odeh",
        "phone": "+970-59-000-0000",
    }


def test_get_candidate_never_exposes_a_candidate_id_field(client):
    _override_service(
        FakeCandidateService(
            response=CandidateInfoResponse(
                first_name="Lina",
                last_name="Odeh",
                phone="+970-59-000-0000",
            )
        )
    )

    response = client.get(ENDPOINT)

    assert "id" not in response.json()
    assert "candidate_id" not in response.json()


def test_get_candidate_returns_404_when_missing(client):
    _override_service(
        FakeCandidateService(
            error=CandidateNotFoundError("Candidate 1 does not exist.")
        )
    )

    response = client.get(ENDPOINT)

    assert response.status_code == 404
