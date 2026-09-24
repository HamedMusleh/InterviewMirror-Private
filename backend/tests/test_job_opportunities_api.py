from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.dependencies.job_opportunity import get_job_opportunity_repository
from app.main import app

ENDPOINT = "/api/job-opportunities/JD-9F1C49FB"


def _job_opportunity():
    return SimpleNamespace(
        id=10,
        job_id="JD-9F1C49FB",
        title="Senior Backend Engineer",
        department="Engineering",
        employment_type="Full-time",
        location="Remote",
        job_summary="Build and scale our core platform.",
        responsibilities=["Design APIs", "Review code", "Mentor engineers"],
        required_skills=["Python", "SQL", "Distributed systems"],
        preferred_skills=["Kubernetes", "Terraform"],
        minimum_years=5,
        experience_level="Senior",
        education=["Bachelor's in Computer Science"],
        certifications=["AWS Certified Solutions Architect"],
        languages=["English"],
        technical_stack=["Python", "PostgreSQL", "Docker"],
        soft_skills=["Communication", "Leadership"],
        # Derived on the model from status; the candidate-facing
        # response carries this rather than the status itself.
        accepting_applications=True,
        # Recruiter-only fields the response must not expose.
        recruiter_id=1,
        status="open",
        passing_score=70,
    )


class FakeJobOpportunityRepository:
    def __init__(self, job_opportunity=None):
        self._job_opportunity = job_opportunity

    def get_by_job_id(self, job_id: str):
        return self._job_opportunity


@pytest.fixture
def client():
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _override_repository(repository) -> None:
    app.dependency_overrides[get_job_opportunity_repository] = (
        lambda: repository
    )


def test_get_job_opportunity_returns_candidate_facing_fields(client):
    _override_repository(FakeJobOpportunityRepository(_job_opportunity()))

    response = client.get(ENDPOINT)

    assert response.status_code == 200
    body = response.json()

    assert body["id"] == 10
    assert body["job_id"] == "JD-9F1C49FB"
    assert body["title"] == "Senior Backend Engineer"
    assert body["department"] == "Engineering"
    assert body["employment_type"] == "Full-time"
    assert body["location"] == "Remote"
    assert body["job_summary"] == "Build and scale our core platform."
    assert body["responsibilities"] == [
        "Design APIs",
        "Review code",
        "Mentor engineers",
    ]
    assert body["required_skills"] == [
        "Python",
        "SQL",
        "Distributed systems",
    ]

    # Task 1: the full candidate-visible job description must be
    # returned, not just the small subset the old schema exposed.
    assert body["preferred_skills"] == ["Kubernetes", "Terraform"]
    assert body["minimum_years"] == 5
    assert body["experience_level"] == "Senior"
    assert body["education"] == ["Bachelor's in Computer Science"]
    assert body["certifications"] == [
        "AWS Certified Solutions Architect",
    ]
    assert body["languages"] == ["English"]
    assert body["technical_stack"] == [
        "Python",
        "PostgreSQL",
        "Docker",
    ]
    assert body["soft_skills"] == ["Communication", "Leadership"]


def test_get_job_opportunity_never_exposes_recruiter_only_fields(client):
    _override_repository(FakeJobOpportunityRepository(_job_opportunity()))

    response = client.get(ENDPOINT)

    body = response.json()
    assert "recruiter_id" not in body
    assert "status" not in body
    assert "passing_score" not in body


def test_get_job_opportunity_returns_404_when_missing(client):
    _override_repository(FakeJobOpportunityRepository(None))

    response = client.get(ENDPOINT)

    assert response.status_code == 404
