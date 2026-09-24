"""
Unit tests for the Role-Based Question Generation feature.

No real LLM calls are made — a fake ILLMClient implementation is used
throughout.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError

from app.dependencies.interfaces.llm_client_interface import ILLMClient
from app.modules.question_generation.pipeline import run_question_generation_pipeline
from app.modules.question_generation.router import (
    generate_questions as generate_questions_endpoint,
)
from app.prompts.question_generation_prompt import (
    NUMBER_OF_QUESTIONS,
    build_question_prompt,
)
from app.schemas.question_generation import QuestionGenerationInput
from app.services.question_generation_service import (
    EmptyLLMResponseError,
    InvalidResponseSchemaError,
    LLMProviderError,
    MalformedLLMResponseError,
    QuestionCountMismatchError,
    QuestionGenerationService,
)


SAMPLE_PROMPT = (
    "Generate interview questions for a mid-level Backend Developer role."
)


class _FakeMessage:
    def __init__(self, content: Optional[str]):
        self.content = content


class _FakeChoice:
    def __init__(self, content: Optional[str]):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: Optional[str]):
        self.choices = [] if content is None else [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, owner: "FakeLLMClient"):
        self._owner = owner

    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ):
        self._owner.call_count += 1
        self._owner.last_model = model
        self._owner.last_prompt = messages[0]["content"] if messages else None

        if self._owner.error:
            raise self._owner.error

        return _FakeResponse(self._owner.response)


class _FakeChat:
    def __init__(self, owner: "FakeLLMClient"):
        self.completions = _FakeCompletions(owner)


class FakeLLMClient(ILLMClient):
    """Configurable fake matching the repo's AzureOpenAI client shape."""

    def __init__(
        self,
        response: Optional[str] = None,
        error: Optional[Exception] = None,
    ):
        self.response = response
        self.error = error
        self.last_prompt: Optional[str] = None
        self.last_model: Optional[str] = None
        self.call_count = 0
        self.chat = _FakeChat(self)


def make_llm_payload(questions: list[dict]) -> str:
    return json.dumps({"questions": questions})


VALID_QUESTIONS = [
    {
        "question": (
            "Explain dependency injection in FastAPI and when you would use it."
        ),
        "category": "skills",
        "skill": "FastAPI",
    },
    {
        "question": (
            "Describe a backend project where you had to solve "
            "an unexpected technical problem."
        ),
        "category": "projects",
        "skill": None,
    },
]


VALID_LLM_JSON = make_llm_payload(VALID_QUESTIONS)


VALID_PIPELINE_QUESTIONS = [
    {
        "question": (
            "Explain dependency injection in FastAPI and when you would use it."
        ),
        "category": "skills",
        "skill": "FastAPI",
    },
    {
        "question": (
            "How would you investigate and improve a slow PostgreSQL query?"
        ),
        "category": "skills",
        "skill": "PostgreSQL",
    },
    {
        "question": (
            "Describe a backend project where you solved "
            "an unexpected technical problem."
        ),
        "category": "projects",
        "skill": None,
    },
    {
        "question": (
            "Tell me about relevant experience you have working "
            "on backend applications."
        ),
        "category": "experience",
        "skill": None,
    },
    {
        "question": (
            "Describe how you communicate a technical problem "
            "to other members of your team."
        ),
        "category": "soft_skills",
        "skill": None,
    },
]


# Sliced rather than trimmed by hand: the pipeline rejects a response whose
# question count does not match what was asked for, so a fixture pinned to a
# fixed length turns any future change to NUMBER_OF_QUESTIONS into a failure
# in here rather than a real finding.
VALID_PIPELINE_JSON = make_llm_payload(
    VALID_PIPELINE_QUESTIONS[:NUMBER_OF_QUESTIONS]
)


def valid_input() -> dict:
    return {
        "job_description": {
            "job_id": "job-123",
            "role": {
                "title": "Backend Engineer",
                "department": "Engineering",
                "employment_type": "Full-time",
                "location": "Remote",
            },
            "job_summary": "Build backend services.",
            "responsibilities": ["Develop APIs"],
            "requirements": {
                "skills": {
                    "required": ["Python"],
                    "preferred": [],
                },
                "experience": {
                    "minimum_years": 2,
                    "level": "Mid-level",
                },
                "education": [],
                "certifications": [],
                "languages": [],
            },
            "technical_stack": ["Python"],
            "soft_skills": [],
            "screening_settings": {
                "passing_score": 70,
            },
        },
        "screening_criteria": {
            "job_id": "job-123",
            "screening_criteria": {
                "skills": {
                    "weight": 50,
                    "required": [
                        {"name": "Python", "weight": 50},
                    ],
                    "preferred": [],
                },
                "experience": {
                    "weight": 25,
                    "minimum_years": 2,
                    "level": "Mid-level",
                },
                "education": {
                    "weight": 10,
                    "preferred_fields": [],
                },
                "projects": {
                    "weight": 5,
                    "required": False,
                    "relevant_domains": [],
                },
                "certifications": {
                    "weight": 3,
                    "criteria": [],
                },
                "languages": {
                    "weight": 2,
                    "criteria": [],
                },
                "soft_skills": {
                    "weight": 5,
                    "criteria": [],
                },
            },
            "passing_score": 70,
        },
    }


def make_structured_request() -> QuestionGenerationInput:
    return QuestionGenerationInput.model_validate(valid_input())


class TestQuestionGenerationService:
    async def test_successful_structured_question_generation(self):
        fake_client = FakeLLMClient(response=VALID_LLM_JSON)
        service = QuestionGenerationService(llm_client=fake_client)

        response = await service.generate_questions(
            SAMPLE_PROMPT,
            number_of_questions=2,
        )

        assert len(response.questions) == 2
        assert response.questions[0].question == VALID_QUESTIONS[0]["question"]
        assert response.questions[0].category.value == "skills"
        assert response.questions[0].skill == "FastAPI"
        assert response.questions[1].category.value == "projects"
        assert response.questions[1].skill is None

    async def test_llm_client_receives_exactly_the_given_prompt(self):
        fake_client = FakeLLMClient(response=VALID_LLM_JSON)
        service = QuestionGenerationService(llm_client=fake_client)

        await service.generate_questions(
            SAMPLE_PROMPT,
            number_of_questions=2,
        )

        assert fake_client.last_prompt == SAMPLE_PROMPT

    async def test_handles_json_wrapped_in_code_fences(self):
        fenced = f"```json\n{VALID_LLM_JSON}\n```"
        fake_client = FakeLLMClient(response=fenced)
        service = QuestionGenerationService(llm_client=fake_client)

        response = await service.generate_questions(
            SAMPLE_PROMPT,
            number_of_questions=2,
        )

        assert len(response.questions) == 2

    async def test_empty_llm_response_raises(self):
        fake_client = FakeLLMClient(response="")
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(EmptyLLMResponseError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=2,
            )

    async def test_malformed_json_raises(self):
        fake_client = FakeLLMClient(response="{not valid json")
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(MalformedLLMResponseError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=2,
            )

    async def test_missing_questions_field_raises(self):
        fake_client = FakeLLMClient(response=json.dumps({"foo": "bar"}))
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=2,
            )

    async def test_questions_not_a_list_raises(self):
        fake_client = FakeLLMClient(
            response=json.dumps({"questions": "not a list"})
        )
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=2,
            )

    async def test_empty_questions_list_raises(self):
        fake_client = FakeLLMClient(response=json.dumps({"questions": []}))
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=2,
            )

    async def test_missing_question_field_raises(self):
        payload = make_llm_payload(
            [{"category": "skills", "skill": "FastAPI"}]
        )
        fake_client = FakeLLMClient(response=payload)
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=1,
            )

    async def test_blank_question_raises(self):
        payload = make_llm_payload(
            [{"question": "   ", "category": "skills", "skill": "FastAPI"}]
        )
        fake_client = FakeLLMClient(response=payload)
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=1,
            )

    async def test_invalid_category_raises(self):
        payload = make_llm_payload(
            [
                {
                    "question": "How do you scale a database?",
                    "category": "not_a_real_category",
                    "skill": None,
                }
            ]
        )
        fake_client = FakeLLMClient(response=payload)
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=1,
            )

    async def test_invalid_skill_type_raises(self):
        payload = make_llm_payload(
            [
                {
                    "question": "How do you scale a database?",
                    "category": "skills",
                    "skill": 123,
                }
            ]
        )
        fake_client = FakeLLMClient(response=payload)
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=1,
            )

    async def test_blank_skill_string_raises(self):
        payload = make_llm_payload(
            [
                {
                    "question": "How do you scale a database?",
                    "category": "skills",
                    "skill": "   ",
                }
            ]
        )
        fake_client = FakeLLMClient(response=payload)
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=1,
            )

    async def test_null_skill_is_accepted(self):
        payload = make_llm_payload(
            [
                {
                    "question": "How do you scale a database?",
                    "category": "skills",
                    "skill": None,
                }
            ]
        )
        fake_client = FakeLLMClient(response=payload)
        service = QuestionGenerationService(llm_client=fake_client)

        response = await service.generate_questions(
            SAMPLE_PROMPT,
            number_of_questions=1,
        )

        assert response.questions[0].skill is None

    async def test_fewer_questions_than_requested_raises(self):
        fake_client = FakeLLMClient(response=VALID_LLM_JSON)
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(QuestionCountMismatchError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=5,
            )

    async def test_more_questions_than_requested_raises(self):
        fake_client = FakeLLMClient(response=VALID_LLM_JSON)
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(QuestionCountMismatchError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=1,
            )

    async def test_llm_client_exception_becomes_provider_error(self):
        fake_client = FakeLLMClient(error=RuntimeError("connection failed"))
        service = QuestionGenerationService(llm_client=fake_client)

        with pytest.raises(LLMProviderError):
            await service.generate_questions(
                SAMPLE_PROMPT,
                number_of_questions=2,
            )


class TestQuestionGenerationInput:
    def test_accepts_matching_job_ids(self):
        data = QuestionGenerationInput.model_validate(valid_input())

        assert data.job_description.job_id == "job-123"
        assert data.screening_criteria.job_id == "job-123"

    def test_rejects_different_job_ids(self):
        data = valid_input()
        data["screening_criteria"]["job_id"] = "job-456"

        with pytest.raises(
            ValidationError,
            match="must belong to the same job",
        ):
            QuestionGenerationInput.model_validate(data)

    def test_rejects_missing_job_description(self):
        data = valid_input()
        data.pop("job_description")

        with pytest.raises(ValidationError):
            QuestionGenerationInput.model_validate(data)

    def test_rejects_missing_screening_criteria(self):
        data = valid_input()
        data.pop("screening_criteria")

        with pytest.raises(ValidationError):
            QuestionGenerationInput.model_validate(data)

    def test_build_question_prompt_contains_required_information(self):
        validated = QuestionGenerationInput.model_validate(valid_input())

        prompt = build_question_prompt(
            validated.job_description,
            validated.screening_criteria,
        )

        assert "Backend Engineer" in prompt
        assert "Python" in prompt
        assert '"job_id": "job-123"' in prompt
        assert "## Job Description" in prompt
        assert "## Screening Criteria" in prompt
        assert "## Number of Questions" in prompt
        assert str(NUMBER_OF_QUESTIONS) in prompt
        assert '"questions"' in prompt


class TestQuestionGenerationPipeline:
    async def test_pipeline_builds_prompt_and_generates_five_questions(self):
        fake_client = FakeLLMClient(response=VALID_PIPELINE_JSON)
        service = QuestionGenerationService(llm_client=fake_client)
        request = make_structured_request()

        response = await run_question_generation_pipeline(request, service)

        assert len(response.questions) == NUMBER_OF_QUESTIONS
        assert fake_client.call_count == 1
        assert fake_client.last_prompt is not None

    async def test_pipeline_prompt_contains_job_description_section(self):
        fake_client = FakeLLMClient(response=VALID_PIPELINE_JSON)
        service = QuestionGenerationService(llm_client=fake_client)
        request = make_structured_request()

        await run_question_generation_pipeline(request, service)

        assert "Job Description" in fake_client.last_prompt

    async def test_pipeline_prompt_contains_screening_criteria_section(self):
        fake_client = FakeLLMClient(response=VALID_PIPELINE_JSON)
        service = QuestionGenerationService(llm_client=fake_client)
        request = make_structured_request()

        await run_question_generation_pipeline(request, service)

        assert "Screening Criteria" in fake_client.last_prompt

    async def test_pipeline_uses_configured_number_of_questions(self):
        fake_client = FakeLLMClient(response=VALID_PIPELINE_JSON)
        service = QuestionGenerationService(llm_client=fake_client)
        request = make_structured_request()

        response = await run_question_generation_pipeline(request, service)

        assert len(response.questions) == NUMBER_OF_QUESTIONS


class TestQuestionGenerationRouter:
    async def test_successful_generation_returns_structured_response(self):
        fake_client = FakeLLMClient(response=VALID_PIPELINE_JSON)
        service = QuestionGenerationService(llm_client=fake_client)
        request = make_structured_request()

        response = await generate_questions_endpoint(
            request=request,
            service=service,
        )

        assert len(response.questions) == NUMBER_OF_QUESTIONS
        assert response.questions[0].category.value == "skills"
        assert response.questions[0].skill == "FastAPI"

    async def test_llm_connection_error_maps_to_503(self):
        fake_client = FakeLLMClient(error=RuntimeError("boom"))
        service = QuestionGenerationService(llm_client=fake_client)
        request = make_structured_request()

        with pytest.raises(HTTPException) as exc_info:
            await generate_questions_endpoint(
                request=request,
                service=service,
            )

        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    async def test_malformed_llm_output_maps_to_502(self):
        fake_client = FakeLLMClient(response="not json")
        service = QuestionGenerationService(llm_client=fake_client)
        request = make_structured_request()

        with pytest.raises(HTTPException) as exc_info:
            await generate_questions_endpoint(
                request=request,
                service=service,
            )

        assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY

    async def test_invalid_category_maps_to_502(self):
        questions = list(VALID_PIPELINE_QUESTIONS)
        questions[0] = {
            "question": "Valid question?",
            "category": "bogus",
            "skill": None,
        }

        fake_client = FakeLLMClient(response=make_llm_payload(questions))
        service = QuestionGenerationService(llm_client=fake_client)
        request = make_structured_request()

        with pytest.raises(HTTPException) as exc_info:
            await generate_questions_endpoint(
                request=request,
                service=service,
            )

        assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY

    async def test_question_count_mismatch_maps_to_502(self):
        fake_client = FakeLLMClient(response=VALID_LLM_JSON)
        service = QuestionGenerationService(llm_client=fake_client)
        request = make_structured_request()

        with pytest.raises(HTTPException) as exc_info:
            await generate_questions_endpoint(
                request=request,
                service=service,
            )

        assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY