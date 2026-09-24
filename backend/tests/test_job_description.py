from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.database.models.job_opportunity import JobOpportunity
from app.dependencies.job_description import (
    get_job_description_embedding_service,
    get_job_description_service,
)
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.schemas.job_description import JobDescriptionRequest
from app.services.job_description_service import JobDescriptionService


def create_valid_request() -> JobDescriptionRequest:
    return JobDescriptionRequest(
        role={
            "title": "Backend Developer",
            "department": "Engineering",
            "employment_type": "Full-time",
            "location": "Ramallah",
        },
        job_summary="Develop backend services.",
        responsibilities=[
            "Build APIs",
            " build APIs ",
            "Optimize databases",
        ],
        requirements={
            "skills": {
                "required": ["Python", " python ", "SQL"],
                "preferred": ["FastAPI", "Docker"],
            },
            "experience": {
                "minimum_years": 2,
                "level": "Mid",
            },
            "education": ["Computer Science"],
            "certifications": ["Azure"],
            "languages": ["English", "Arabic"],
        },
        technical_stack=["Python", " python ", "FastAPI"],
        soft_skills=["Communication", "Teamwork"],
    )


def test_valid_job_description_request():
    request = create_valid_request()

    assert request.role.title == "Backend Developer"
    assert request.requirements.experience.minimum_years == 2
    assert request.screening_settings.passing_score == 70


def test_rejects_empty_required_text():
    with pytest.raises(ValidationError):
        JobDescriptionRequest(
            role={
                "title": "   ",
                "department": "Engineering",
                "employment_type": "Full-time",
                "location": "Ramallah",
            },
            job_summary="Develop backend services.",
            requirements={
                "skills": {
                    "required": ["Python"],
                    "preferred": [],
                },
                "experience": {
                    "minimum_years": 2,
                    "level": "Mid",
                },
                "education": [],
                "certifications": [],
                "languages": [],
            },
        )


def test_rejects_negative_experience():
    with pytest.raises(ValidationError):
        JobDescriptionRequest(
            role={
                "title": "Backend Developer",
                "department": "Engineering",
                "employment_type": "Full-time",
                "location": "Ramallah",
            },
            job_summary="Develop backend services.",
            requirements={
                "skills": {
                    "required": ["Python"],
                    "preferred": [],
                },
                "experience": {
                    "minimum_years": -1,
                    "level": "Mid",
                },
                "education": [],
                "certifications": [],
                "languages": [],
            },
        )


def test_rejects_invalid_passing_score():
    with pytest.raises(ValidationError):
        JobDescriptionRequest(
            role={
                "title": "Backend Developer",
                "department": "Engineering",
                "employment_type": "Full-time",
                "location": "Ramallah",
            },
            job_summary="Develop backend services.",
            requirements={
                "skills": {
                    "required": ["Python"],
                    "preferred": [],
                },
                "experience": {
                    "minimum_years": 2,
                    "level": "Mid",
                },
                "education": [],
                "certifications": [],
                "languages": [],
            },
            screening_settings={
                "passing_score": 120,
            },
        )


def test_process_job_description_cleans_duplicates():
    request = create_valid_request()
    service = JobDescriptionService()

    job = service.process_job_description(request)

    assert job.responsibilities == [
        "Build APIs",
        "Optimize databases",
    ]

    assert job.requirements.skills.required == [
        "Python",
        "SQL",
    ]

    assert job.technical_stack == [
        "Python",
        "FastAPI",
    ]


def test_process_job_description_generates_job_id():
    request = create_valid_request()
    service = JobDescriptionService()

    job = service.process_job_description(request)

    assert job.job_id.startswith("JD-")
    assert len(job.job_id) == 11


def test_job_description_service_is_singleton():
    service1 = get_job_description_service()
    service2 = get_job_description_service()

    assert service1 is service2


def test_embedding_service_is_singleton():
    service1 = get_job_description_embedding_service()
    service2 = get_job_description_embedding_service()

    assert service1 is service2


def test_generate_job_description_embeddings():
    request = create_valid_request()

    processing_service = get_job_description_service()
    embedding_service = get_job_description_embedding_service()

    job = processing_service.process_job_description(request)

    embeddings = (
        embedding_service.generate_job_description_embeddings(job)
    )

    assert embeddings
    assert "role" in embeddings
    assert "job_summary" in embeddings
    assert "responsibilities" in embeddings
    assert "preferred_skills" in embeddings
    assert "soft_skills" in embeddings

    for embedding in embeddings.values():
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(value, float) for value in embedding)
def test_job_description_is_mapped_and_saved_to_database():
    request = create_valid_request()
    service = JobDescriptionService()
    processed_job = service.process_job_description(request)

    db = MagicMock()
    repository = JobOpportunityRepository(db)

    saved_job = repository.save(
        processed_job,
        recruiter_id=1,
    )

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(saved_job)

    assert isinstance(saved_job, JobOpportunity)
    assert saved_job.job_id == processed_job.job_id
    assert saved_job.recruiter_id == 1
    assert saved_job.title == "Backend Developer"
    assert saved_job.department == "Engineering"
    assert saved_job.required_skills == ["Python", "SQL"]
    assert saved_job.preferred_skills == ["FastAPI", "Docker"]
    assert saved_job.minimum_years == 2
    assert saved_job.experience_level == "Mid"
    assert saved_job.passing_score == 70