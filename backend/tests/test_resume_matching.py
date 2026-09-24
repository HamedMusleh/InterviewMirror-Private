import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.dependencies.resume_matching import ResumeMatchingDependencies
from app.modules.resume_matching.pipeline import ResumeMatchingPipeline
from app.modules.resume_matching.router import router
from app.repositories.resume_matching_repository import (
    ResumeMatchingRepository,
    StoredMatchingInput,
)
from app.schemas.resume_matching import (
    EducationMatchingResult,
    ExperienceMatchingResult,
    ListMatchingResult,
    MatchingRequest,
    MatchingResults,
    PreferredSkillMatch,
    ProjectMatch,
    ProjectsMatchingResult,
    SkillMatch,
    SkillsMatchingResult,
)
from app.services.resume_matching_service import ResumeMatchingService
from app.services.llm_client import (
    AzureOpenAIClient,
    LLMResponseError,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_request(filename: str) -> MatchingRequest:
    with (FIXTURE_DIR / filename).open(encoding="utf-8") as fixture:
        return MatchingRequest.model_validate(json.load(fixture))


def build_model_result(
    request: MatchingRequest,
    *,
    partial: bool = False,
) -> MatchingResults:
    skill_score = 35 if partial else 95
    criteria = request.screening_criteria["screening_criteria"]
    required_skills = [
        SkillMatch(
            required_skill=item["name"],
            matched_skill=item["name"],
            similarity_score=skill_score,
            evidence="Resume technical skills list",
        )
        for item in criteria["skills"]["required"]
    ]
    preferred_skills = [
        PreferredSkillMatch(
            preferred_skill=item["name"],
            matched_skill=item["name"],
            similarity_score=skill_score,
            evidence="Resume tools and technologies list",
        )
        for item in criteria["skills"]["preferred"]
    ]

    if partial:
        experience = ExperienceMatchingResult(
            score=40,
            status="evaluated",
            candidate_years=1,
            required_years=2,
            level_match=False,
            evidence=["Junior Developer at Example Web Co for 1 year"],
        )
        education = EducationMatchingResult(
            score=20,
            status="evaluated",
            matched_field="Business Administration",
            evidence="Bachelor's Degree in Business Administration",
        )
        projects = ProjectsMatchingResult(
            score=30,
            status="evaluated",
            matches=[
                ProjectMatch(
                    project_name="Inventory Dashboard",
                    matched_domain=None,
                    similarity_score=30,
                    evidence="Resume project description",
                )
            ],
        )
        soft_skills = ["Problem Solving"]
    else:
        experience = ExperienceMatchingResult(
            score=90,
            status="evaluated",
            candidate_years=3,
            required_years=2,
            level_match=True,
            evidence=["Machine Learning Engineer at Example AI Co for 3 years"],
        )
        education = EducationMatchingResult(
            score=100,
            status="evaluated",
            matched_field="Computer Science",
            evidence="Bachelor's Degree in Computer Science",
        )
        projects = ProjectsMatchingResult(
            score=90,
            status="evaluated",
            matches=[
                ProjectMatch(
                    project_name="AI Recommendation System",
                    matched_domain="Machine Learning",
                    similarity_score=90,
                    evidence="Used Python and machine learning",
                )
            ],
        )
        soft_skills = ["Problem Solving", "Communication"]

    return MatchingResults(
        skills=SkillsMatchingResult(
            score=skill_score,
            status="evaluated",
            required=required_skills,
            preferred=preferred_skills,
        ),
        experience=experience,
        projects=projects,
        education=education,
        certifications=ListMatchingResult(
            score=0 if partial else 100,
            status="evaluated",
            matched=[] if partial else ["Azure AI Fundamentals"],
            missing=[] if not partial else ["Azure AI Fundamentals"],
        ),
        languages=ListMatchingResult(
            score=0 if partial else 100,
            status="evaluated",
            matched=[] if partial else ["English"],
            missing=[] if not partial else ["English"],
        ),
        soft_skills=ListMatchingResult(
            score=50 if partial else 100,
            status="evaluated",
            matched=soft_skills,
            missing=[] if not partial else ["Communication"],
        ),
    )


class FakeLLMClient:
    def __init__(self, result: MatchingResults):
        self.result = result

    async def complete_structured(self, **kwargs):
        assert kwargs["response_model"] is MatchingResults
        return self.result


class FakeMatchingRepository:
    def __init__(self, stored_input: StoredMatchingInput):
        self.stored_input = stored_input

    def load_for_application(self, application_id: int) -> StoredMatchingInput:
        assert application_id == self.stored_input.application_id
        return self.stored_input


def build_pipeline(request: MatchingRequest, *, partial: bool = False):
    return ResumeMatchingPipeline(
        llm_client=FakeLLMClient(build_model_result(request, partial=partial)),
        matching_service=ResumeMatchingService(),
    )


def test_database_repository_loads_the_three_matching_inputs():
    request = load_request("strong_match_request.json")
    application = SimpleNamespace(
        id=11,
        candidate_id=42,
        job_opportunity_id=22,
    )
    resume = SimpleNamespace(
        application_id=11,
        personal_information=request.resume.personal_information.model_dump(),
        professional_summary=request.resume.professional_summary,
        skills=request.resume.skills.model_dump(),
        experience=[item.model_dump() for item in request.resume.experience],
        education=[item.model_dump() for item in request.resume.education],
        projects=[item.model_dump() for item in request.resume.projects],
        certifications=request.resume.certifications,
        languages=request.resume.languages,
    )
    job = SimpleNamespace(
        id=22,
        job_id=request.job_description.job_id,
        title=request.job_description.role.title,
        department=request.job_description.role.department,
        employment_type=request.job_description.role.employment_type,
        location=request.job_description.role.location,
        job_summary=request.job_description.job_summary,
        responsibilities=request.job_description.responsibilities,
        required_skills=request.job_description.requirements.skills.required,
        preferred_skills=request.job_description.requirements.skills.preferred,
        minimum_years=request.job_description.requirements.experience.minimum_years,
        experience_level=request.job_description.requirements.experience.level,
        education=request.job_description.requirements.education,
        certifications=request.job_description.requirements.certifications,
        languages=request.job_description.requirements.languages,
        technical_stack=request.job_description.technical_stack,
        soft_skills=request.job_description.soft_skills,
        passing_score=request.job_description.screening_settings.passing_score,
    )
    criteria = SimpleNamespace(
        id=33,
        job_id=22,
        criteria=request.screening_criteria,
    )

    class FakeSession:
        def get(self, model, identifier):
            if model.__name__ == "Application":
                return application
            if model.__name__ == "JobOpportunity":
                return job
            raise AssertionError(f"Unexpected model: {model.__name__}")

        def scalar(self, statement):
            if "resumes" in str(statement):
                return resume
            return criteria

    stored = ResumeMatchingRepository(FakeSession()).load_for_application(11)

    assert stored.request.resume.candidate_id == "42"
    assert stored.request.job_description.job_id == "123"
    assert stored.application_id == 11
    assert stored.job_opportunity_id == 22
    assert stored.criteria_id == 33
    assert stored.category_weights["skills"] == 50
    assert stored.passing_score == 70


def test_database_matching_response_contains_scoring_handoff_data():
    request = load_request("strong_match_request.json")
    stored = StoredMatchingInput(
        request=request,
        application_id=11,
        job_opportunity_id=22,
        criteria_id=33,
        category_weights={
            "skills": 50,
            "experience": 25,
            "education": 10,
            "projects": 5,
            "certifications": 3,
            "languages": 2,
            "soft_skills": 5,
        },
        passing_score=70,
    )
    pipeline = ResumeMatchingPipeline(
        llm_client=FakeLLMClient(build_model_result(request)),
        matching_service=ResumeMatchingService(),
        repository=FakeMatchingRepository(stored),
    )

    response = asyncio.run(pipeline.match_application(11))

    assert response.application_id == 11
    assert response.job_opportunity_id == 22
    assert response.criteria_id == 33
    assert response.category_scores["skills"].score == 95
    assert response.category_scores["skills"].status == "evaluated"
    assert response.category_weights["skills"] == 50
    assert response.passing_score == 70
    assert not hasattr(response, "overall_score")
    assert not hasattr(response, "final_status")


def test_strong_fixture_has_the_expected_input_shape():
    request = load_request("strong_match_request.json")

    assert request.resume.candidate_id == "C12345"
    assert request.job_description.job_id == "123"
    assert [
        item["name"]
        for item in request.screening_criteria["screening_criteria"]["skills"][
            "required"
        ]
    ] == ["Python", "Machine Learning"]


def test_mismatched_job_ids_are_rejected():
    with (FIXTURE_DIR / "strong_match_request.json").open(
        encoding="utf-8"
    ) as fixture:
        payload = json.load(fixture)

    payload["screening_criteria"]["job_id"] = "different-job"

    with pytest.raises(ValidationError, match="job_description.job_id"):
        MatchingRequest.model_validate(payload)


def test_invalid_scores_are_rejected():
    with pytest.raises(ValidationError):
        SkillMatch(
            required_skill="Python",
            matched_skill="Python",
            similarity_score=101,
            evidence="Resume skills",
        )


def test_malformed_azure_structured_response_is_rejected():
    async def parse(**kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(parsed={"skills": {}})
                )
            ]
        )

    client = SimpleNamespace(
        beta=SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(parse=parse)
            )
        )
    )
    azure_client = AzureOpenAIClient(
        client=client,
        deployment_name="test-deployment",
    )

    with pytest.raises(LLMResponseError):
        asyncio.run(
            azure_client.complete_structured(
                system_prompt="system",
                user_prompt="user",
                response_model=MatchingResults,
            )
        )


def test_strong_match_returns_matches_and_resume_evidence():
    request = load_request("strong_match_request.json")
    response = asyncio.run(build_pipeline(request).match(request))

    assert response.candidate_id == "C12345"
    assert response.job_id == "123"
    assert response.matching_results.skills.required[0].matched_skill == "Python"
    assert response.matching_results.skills.required[0].similarity_score >= 70
    assert response.matching_results.skills.required[0].evidence is not None
    assert response.matching_results.projects.matches[0].matched_domain == (
        "Machine Learning"
    )
    assert response.matching_results.education.matched_field == "Computer Science"


def test_partial_match_marks_below_threshold_requirements_missing():
    request = load_request("partial_match_request.json")
    response = asyncio.run(build_pipeline(request, partial=True).match(request))
    results = response.matching_results

    assert all(item.matched_skill is None for item in results.skills.required)
    assert all(item.similarity_score < 70 for item in results.skills.required)
    assert results.experience.candidate_years == 1
    assert results.experience.required_years == 2
    assert results.experience.level_match is False
    assert results.certifications.missing == ["Azure AI Fundamentals"]
    assert results.languages.missing == ["English"]
    assert results.soft_skills.missing == ["Communication"]


def test_empty_optional_categories_are_not_applicable():
    request = load_request("empty_optional_requirements_request.json")
    response = asyncio.run(build_pipeline(request).match(request))
    results = response.matching_results

    for category in (
        results.projects,
        results.education,
        results.certifications,
        results.languages,
        results.soft_skills,
    ):
        assert category.status == "not_applicable"
        assert category.score is None


def test_http_endpoint_uses_the_matching_contract():
    request = load_request("strong_match_request.json")
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[
        ResumeMatchingDependencies.get_resume_matching_pipeline
    ] = lambda: build_pipeline(request)

    try:
        response = TestClient(test_app).post(
            "/api/resume-matching",
            json=request.model_dump(mode="json"),
        )
    finally:
        test_app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["candidate_id"] == "C12345"
    assert body["job_id"] == "123"
    assert set(body["matching_results"]) == {
        "skills",
        "experience",
        "projects",
        "education",
        "certifications",
        "languages",
        "soft_skills",
    }
    assert "overall_score" not in body
    assert "final_status" not in body


def test_database_http_endpoint_exposes_scoring_handoff():
    request = load_request("strong_match_request.json")
    stored = StoredMatchingInput(
        request=request,
        application_id=11,
        job_opportunity_id=22,
        criteria_id=33,
        category_weights={
            "skills": 50,
            "experience": 25,
            "education": 10,
            "projects": 5,
            "certifications": 3,
            "languages": 2,
            "soft_skills": 5,
        },
        passing_score=70,
    )
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[
        ResumeMatchingDependencies.get_database_resume_matching_pipeline
    ] = lambda: ResumeMatchingPipeline(
        llm_client=FakeLLMClient(build_model_result(request)),
        matching_service=ResumeMatchingService(),
        repository=FakeMatchingRepository(stored),
    )

    try:
        response = TestClient(test_app).post(
            "/api/resume-matching/applications/11"
        )
    finally:
        test_app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["application_id"] == 11
    assert body["criteria_id"] == 33
    assert body["category_scores"]["skills"] == {
        "score": 95,
        "status": "evaluated",
    }
