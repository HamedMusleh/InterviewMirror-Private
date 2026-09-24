"""
Editing and deleting a job posting.

The delete guard is the part worth testing hardest. An application is the
root of a candidate's resume, screening result, interview and recorded
answers, so a posting with applications must not be removable on one click
-- and the refusal has to say why, because a button that silently does
nothing reads as a bug rather than as a rule.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.dependencies.interview_context import get_application_repository
from app.dependencies.job_description import get_job_description_service
from app.dependencies.job_opportunity import get_job_opportunity_repository
from app.dependencies.screening_criteria import (
    get_screening_criteria_handler,
    get_screening_criteria_repository,
)
from app.main import app
from app.services.job_description_service import JobDescriptionService

JOB_ID = "JD-9F1C49FB"
ENDPOINT = f"/api/job-description/{JOB_ID}"


def _job_opportunity():
    return SimpleNamespace(
        id=10,
        job_id=JOB_ID,
        recruiter_id=1,
        title="Senior Backend Engineer",
        department="Engineering",
        employment_type="Full-time",
        location="Remote",
        job_summary="Build and scale our core platform.",
        responsibilities=["Design APIs"],
        required_skills=["Python"],
        preferred_skills=["Kubernetes"],
        minimum_years=5,
        experience_level="Senior",
        education=["Bachelor's in Computer Science"],
        certifications=["AWS"],
        languages=["English"],
        technical_stack=["Python"],
        soft_skills=["Communication"],
        passing_score=70,
        status="draft",
    )


def _edit_request():
    return {
        "role": {
            "title": "Staff Backend Engineer",
            "department": "Engineering",
            "employment_type": "Full-time",
            "location": "Hybrid",
        },
        "job_summary": "Lead the platform team.",
        "responsibilities": ["Set technical direction"],
        "requirements": {
            "skills": {
                "required": ["Python", "Go"],
                "preferred": ["Rust"],
            },
            "experience": {"minimum_years": 8, "level": "Staff"},
            "education": ["Bachelor's in Computer Science"],
            "certifications": [],
            "languages": ["English"],
        },
        "technical_stack": ["Python"],
        "soft_skills": ["Mentoring"],
        "screening_settings": {"passing_score": 80},
    }


class FakeJobRepository:
    def __init__(self, job_opportunity=None):
        self._job = job_opportunity
        self.updated_with = None
        self.deleted = None
        self.status_calls = []

    def get_by_job_id(self, job_id: str):
        return self._job

    def set_status(self, job_opportunity, status):
        self.status_calls.append(status)
        job_opportunity.status = status

        return job_opportunity

    def update(self, job_opportunity, job):
        self.updated_with = job

        return job_opportunity

    def delete(self, job_opportunity):
        self.deleted = job_opportunity


class FakeApplicationRepository:
    def __init__(self, count=0):
        self._count = count

    def count_for_job_opportunity(self, job_opportunity_id: int) -> int:
        return self._count


class FakeCriteriaRepository:
    def __init__(self):
        self.deleted_for = []

    def delete_for_job_opportunity(self, job_opportunity_id: int) -> bool:
        self.deleted_for.append(job_opportunity_id)

        return True


class FakeCriteriaHandler:
    def __init__(self, explode=False):
        self.calls = []
        self._explode = explode

    def handle_generate_screening_criteria(self, job_description_json):
        self.calls.append(job_description_json)

        if self._explode:
            raise RuntimeError("model unavailable")


@pytest.fixture
def client():
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _wire(
    job_repository,
    application_repository=None,
    criteria_repository=None,
    criteria_handler=None,
):
    app.dependency_overrides[get_job_opportunity_repository] = (
        lambda: job_repository
    )
    app.dependency_overrides[get_application_repository] = (
        lambda: application_repository or FakeApplicationRepository()
    )
    app.dependency_overrides[get_screening_criteria_repository] = (
        lambda: criteria_repository or FakeCriteriaRepository()
    )
    app.dependency_overrides[get_screening_criteria_handler] = (
        lambda: criteria_handler or FakeCriteriaHandler()
    )
    app.dependency_overrides[get_job_description_service] = (
        lambda: JobDescriptionService()
    )


# --- editing -----------------------------------------------------------


def test_editing_keeps_the_job_id(client):
    """
    The identity of a posting is what every application, screening
    criteria row and candidate link already points at. Editing changes
    what it says, never which posting it is.
    """

    repository = FakeJobRepository(_job_opportunity())
    _wire(repository)

    response = client.put(ENDPOINT, json=_edit_request())

    assert response.status_code == 200
    assert response.json()["job_id"] == JOB_ID
    assert repository.updated_with.job_id == JOB_ID


def test_editing_saves_the_new_values(client):
    repository = FakeJobRepository(_job_opportunity())
    _wire(repository)

    response = client.put(ENDPOINT, json=_edit_request())

    assert response.status_code == 200

    saved = repository.updated_with

    assert saved.role.title == "Staff Backend Engineer"
    assert saved.requirements.skills.required == ["Python", "Go"]
    assert saved.screening_settings.passing_score == 80


def test_editing_regenerates_the_screening_criteria(client):
    """
    Criteria are derived from the job's skills and weights. Leaving the old
    ones after an edit would screen future candidates against requirements
    the posting no longer states, and nothing on screen would show it.
    """

    criteria_repository = FakeCriteriaRepository()
    handler = FakeCriteriaHandler()

    _wire(
        FakeJobRepository(_job_opportunity()),
        criteria_repository=criteria_repository,
        criteria_handler=handler,
    )

    response = client.put(ENDPOINT, json=_edit_request())

    assert response.status_code == 200
    # Old row removed first: the criteria table is unique per job.
    assert criteria_repository.deleted_for == [10]
    assert len(handler.calls) == 1


def test_a_failed_regeneration_does_not_lose_the_edit(client):
    """
    Regeneration reaches the model, so it can fail on its own. The
    recruiter's typing is already saved and correct by then; discarding it
    for a reason that has nothing to do with what they wrote would be the
    worse outcome.
    """

    repository = FakeJobRepository(_job_opportunity())

    _wire(repository, criteria_handler=FakeCriteriaHandler(explode=True))

    response = client.put(ENDPOINT, json=_edit_request())

    assert response.status_code == 200
    assert repository.updated_with is not None


def test_editing_a_missing_job_is_a_404(client):
    _wire(FakeJobRepository(None))

    response = client.put(ENDPOINT, json=_edit_request())

    assert response.status_code == 404


# --- deleting ----------------------------------------------------------


def test_deleting_an_unused_job_removes_it(client):
    repository = FakeJobRepository(_job_opportunity())
    criteria_repository = FakeCriteriaRepository()

    _wire(
        repository,
        application_repository=FakeApplicationRepository(count=0),
        criteria_repository=criteria_repository,
    )

    response = client.delete(ENDPOINT)

    assert response.status_code == 204
    assert repository.deleted is not None
    # Criteria belong to the posting; nothing else refers to them.
    assert criteria_repository.deleted_for == [10]


def test_deleting_a_job_with_applications_is_refused(client):
    repository = FakeJobRepository(_job_opportunity())

    _wire(
        repository,
        application_repository=FakeApplicationRepository(count=3),
    )

    response = client.delete(ENDPOINT)

    assert response.status_code == 409
    assert repository.deleted is None


def test_the_refusal_says_how_many_applications_are_in_the_way(client):
    """
    A button that appears to do nothing reads as broken. The count is what
    turns the refusal into something the recruiter can act on.
    """

    _wire(
        FakeJobRepository(_job_opportunity()),
        application_repository=FakeApplicationRepository(count=3),
    )

    detail = client.delete(ENDPOINT).json()["detail"]

    assert "3 applications" in detail


def test_the_refusal_is_worded_for_a_single_application(client):
    _wire(
        FakeJobRepository(_job_opportunity()),
        application_repository=FakeApplicationRepository(count=1),
    )

    detail = client.delete(ENDPOINT).json()["detail"]

    assert "1 application" in detail
    assert "1 applications" not in detail


def test_a_refused_delete_leaves_the_criteria_alone(client):
    """The posting survives, so its criteria have to survive with it."""

    criteria_repository = FakeCriteriaRepository()

    _wire(
        FakeJobRepository(_job_opportunity()),
        application_repository=FakeApplicationRepository(count=2),
        criteria_repository=criteria_repository,
    )

    client.delete(ENDPOINT)

    assert criteria_repository.deleted_for == []


def test_deleting_a_missing_job_is_a_404(client):
    _wire(FakeJobRepository(None))

    response = client.delete(ENDPOINT)

    assert response.status_code == 404


# --- reading it back for the form --------------------------------------


def test_the_edit_view_includes_the_passing_score(client):
    """
    The candidate-facing endpoint withholds it. A form that could not read
    it would reset the recruiter's threshold to the default on every save.
    """

    _wire(FakeJobRepository(_job_opportunity()))

    body = client.get(ENDPOINT).json()

    assert body["passing_score"] == 70
    assert body["preferred_skills"] == ["Kubernetes"]


def test_reading_a_missing_job_for_edit_is_a_404(client):
    _wire(FakeJobRepository(None))

    assert client.get(ENDPOINT).status_code == 404


# --- closing a posting -------------------------------------------------
#
# Archiving is what a finished job needs and deleting cannot give it. A
# posting candidates have applied to cannot be deleted precisely because
# their resumes, screening results and interviews hang off it; closing ends
# the posting while leaving all of that where it is.

STATUS_ENDPOINT = f"{ENDPOINT}/status"


def test_closing_a_job_archives_it(client):
    repository = FakeJobRepository(_job_opportunity())
    _wire(repository)

    response = client.patch(STATUS_ENDPOINT, json={"status": "archived"})

    assert response.status_code == 200
    assert response.json()["status"] == "archived"
    assert repository.status_calls == ["archived"]


def test_closing_destroys_nothing(client):
    """
    The whole point of closing rather than deleting. Nothing that hangs off
    the posting is touched, and the posting itself survives.
    """

    repository = FakeJobRepository(_job_opportunity())
    criteria_repository = FakeCriteriaRepository()

    _wire(repository, criteria_repository=criteria_repository)

    client.patch(STATUS_ENDPOINT, json={"status": "archived"})

    assert repository.deleted is None
    assert criteria_repository.deleted_for == []


def test_a_closed_job_can_be_reopened(client):
    """
    Closing the wrong posting should be one click to undo, not a rebuild,
    so the states are not a one-way lifecycle.
    """

    job = _job_opportunity()
    job.status = "archived"

    repository = FakeJobRepository(job)
    _wire(repository)

    response = client.patch(STATUS_ENDPOINT, json={"status": "published"})

    assert response.status_code == 200
    assert response.json()["status"] == "published"


def test_an_unknown_status_is_rejected(client):
    _wire(FakeJobRepository(_job_opportunity()))

    response = client.patch(STATUS_ENDPOINT, json={"status": "banana"})

    assert response.status_code == 422


def test_changing_the_status_of_a_missing_job_is_a_404(client):
    _wire(FakeJobRepository(None))

    response = client.patch(STATUS_ENDPOINT, json={"status": "archived"})

    assert response.status_code == 404

