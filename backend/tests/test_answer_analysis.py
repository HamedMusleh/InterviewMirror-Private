"""
Unit tests for the Answer Analysis feature.

No real LLM calls are made — a fake ILLMClient implementation is used
throughout.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import pytest
from fastapi import HTTPException, status

from app.dependencies.interfaces.llm_client_interface import ILLMClient
from app.modules.answer_analysis.pipeline import run_answer_analysis_pipeline
from app.modules.answer_analysis.router import (
    analyze_answer as analyze_answer_endpoint,
)
from app.prompts.answer_analysis_prompt import build_answer_analysis_prompt
from app.schemas.answer_analysis import AnswerAnalysisInput
from app.services.answer_analysis_service import (
    AnswerAnalysisService,
    EmptyLLMResponseError,
    InvalidResponseSchemaError,
    LLMProviderError,
    MalformedLLMResponseError,
)


SAMPLE_PROMPT = (
    "Analyze the candidate's answer to the FastAPI question below."
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


def make_llm_payload(**overrides: Any) -> str:
    payload = {
        "answer_quality": "medium",
        "relevant_points": [
            "Candidate used FastAPI to build REST APIs",
        ],
        "missing_areas": [
            "Limited technical detail",
        ],
        "evidence": [
            "I used FastAPI to build REST APIs for a university project.",
        ],
        "follow_up_needed": True,
        "follow_up_reason": "The answer lacks sufficient technical depth.",
    }
    payload.update(overrides)
    return json.dumps(payload)


VALID_LLM_JSON = make_llm_payload()


def make_request() -> AnswerAnalysisInput:
    return AnswerAnalysisInput(
        interview_id=1,
        question_id=1,
        role="Backend Developer",
        question="Explain your experience with FastAPI.",
        question_type="skills",
        skill="FastAPI",
        answer=(
            "I used FastAPI to build REST APIs for a university project."
        ),
        previous_interactions=[],
    )


class TestAnswerAnalysisService:
    async def test_successful_answer_analysis(self):
        fake_client = FakeLLMClient(response=VALID_LLM_JSON)
        service = AnswerAnalysisService(llm_client=fake_client)

        result = await service.analyze_answer(SAMPLE_PROMPT)

        assert result.answer_quality == "medium"
        assert result.relevant_points == [
            "Candidate used FastAPI to build REST APIs"
        ]
        assert result.missing_areas == ["Limited technical detail"]
        assert result.evidence == [
            "I used FastAPI to build REST APIs for a university project."
        ]
        assert result.follow_up_needed is True
        assert (
            result.follow_up_reason
            == "The answer lacks sufficient technical depth."
        )

    async def test_follow_up_reason_must_be_null_when_not_needed(self):
        payload = make_llm_payload(
            follow_up_needed=False,
            follow_up_reason="A reason should not be present",
        )
        fake_client = FakeLLMClient(response=payload)
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.analyze_answer(SAMPLE_PROMPT)

    async def test_llm_client_receives_exactly_the_given_prompt(self):
        fake_client = FakeLLMClient(response=VALID_LLM_JSON)
        service = AnswerAnalysisService(llm_client=fake_client)

        await service.analyze_answer(SAMPLE_PROMPT)

        assert fake_client.last_prompt == SAMPLE_PROMPT

    async def test_handles_json_wrapped_in_code_fences(self):
        fenced = f"```json\n{VALID_LLM_JSON}\n```"
        fake_client = FakeLLMClient(response=fenced)
        service = AnswerAnalysisService(llm_client=fake_client)

        result = await service.analyze_answer(SAMPLE_PROMPT)

        assert result.answer_quality == "medium"

    async def test_no_follow_up_needed_allows_null_reason(self):
        payload = make_llm_payload(
            follow_up_needed=False,
            follow_up_reason=None,
        )
        fake_client = FakeLLMClient(response=payload)
        service = AnswerAnalysisService(llm_client=fake_client)

        result = await service.analyze_answer(SAMPLE_PROMPT)

        assert result.follow_up_needed is False
        assert result.follow_up_reason is None

    async def test_empty_llm_response_raises(self):
        fake_client = FakeLLMClient(response="")
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(EmptyLLMResponseError):
            await service.analyze_answer(SAMPLE_PROMPT)

    async def test_malformed_json_raises(self):
        fake_client = FakeLLMClient(response="{not valid json")
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(MalformedLLMResponseError):
            await service.analyze_answer(SAMPLE_PROMPT)

    async def test_missing_required_field_raises(self):
        payload = json.loads(VALID_LLM_JSON)
        payload.pop("answer_quality")
        fake_client = FakeLLMClient(response=json.dumps(payload))
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.analyze_answer(SAMPLE_PROMPT)

    async def test_invalid_answer_quality_value_raises(self):
        payload = make_llm_payload(answer_quality="excellent")
        fake_client = FakeLLMClient(response=payload)
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.analyze_answer(SAMPLE_PROMPT)

    async def test_relevant_points_not_a_list_raises(self):
        payload = make_llm_payload(relevant_points="not a list")
        fake_client = FakeLLMClient(response=payload)
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.analyze_answer(SAMPLE_PROMPT)

    async def test_blank_item_in_relevant_points_raises(self):
        payload = make_llm_payload(relevant_points=["   "])
        fake_client = FakeLLMClient(response=payload)
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.analyze_answer(SAMPLE_PROMPT)

    async def test_blank_item_in_missing_areas_raises(self):
        payload = make_llm_payload(missing_areas=["   "])
        fake_client = FakeLLMClient(response=payload)
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.analyze_answer(SAMPLE_PROMPT)

    async def test_blank_item_in_evidence_raises(self):
        payload = make_llm_payload(evidence=["   "])
        fake_client = FakeLLMClient(response=payload)
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.analyze_answer(SAMPLE_PROMPT)

    async def test_empty_relevant_points_list_is_accepted(self):
        payload = make_llm_payload(relevant_points=[])
        fake_client = FakeLLMClient(response=payload)
        service = AnswerAnalysisService(llm_client=fake_client)

        result = await service.analyze_answer(SAMPLE_PROMPT)

        assert result.relevant_points == []

    async def test_follow_up_needed_true_without_reason_raises(self):
        payload = make_llm_payload(
            follow_up_needed=True,
            follow_up_reason=None,
        )
        fake_client = FakeLLMClient(response=payload)
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.analyze_answer(SAMPLE_PROMPT)

    async def test_follow_up_needed_true_with_blank_reason_raises(self):
        payload = make_llm_payload(
            follow_up_needed=True,
            follow_up_reason="   ",
        )
        fake_client = FakeLLMClient(response=payload)
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.analyze_answer(SAMPLE_PROMPT)

    async def test_blank_follow_up_reason_raises_even_when_not_needed(self):
        payload = make_llm_payload(
            follow_up_needed=False,
            follow_up_reason="   ",
        )
        fake_client = FakeLLMClient(response=payload)
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(InvalidResponseSchemaError):
            await service.analyze_answer(SAMPLE_PROMPT)

    async def test_llm_client_exception_becomes_provider_error(self):
        fake_client = FakeLLMClient(error=RuntimeError("connection failed"))
        service = AnswerAnalysisService(llm_client=fake_client)

        with pytest.raises(LLMProviderError):
            await service.analyze_answer(SAMPLE_PROMPT)


class TestAnswerAnalysisPipeline:
    async def test_pipeline_forwards_prompt_and_returns_result(self):
        fake_client = FakeLLMClient(response=VALID_LLM_JSON)
        service = AnswerAnalysisService(llm_client=fake_client)
        request = make_request()

        result = await run_answer_analysis_pipeline(request, service)

        expected_prompt = build_answer_analysis_prompt(request)

        assert result.answer_quality == "medium"
        assert fake_client.call_count == 1
        assert fake_client.last_prompt == expected_prompt


class TestAnswerAnalysisRouter:
    async def test_successful_analysis_returns_structured_response(self):
        fake_client = FakeLLMClient(response=VALID_LLM_JSON)
        service = AnswerAnalysisService(llm_client=fake_client)
        request = make_request()

        response = await analyze_answer_endpoint(
            request=request,
            service=service,
        )

        assert response.answer_quality == "medium"
        assert response.follow_up_needed is True

    async def test_llm_connection_error_maps_to_503(self):
        fake_client = FakeLLMClient(error=RuntimeError("boom"))
        service = AnswerAnalysisService(llm_client=fake_client)
        request = make_request()

        with pytest.raises(HTTPException) as exc_info:
            await analyze_answer_endpoint(
                request=request,
                service=service,
            )

        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    async def test_malformed_llm_output_maps_to_502(self):
        fake_client = FakeLLMClient(response="not json")
        service = AnswerAnalysisService(llm_client=fake_client)
        request = make_request()

        with pytest.raises(HTTPException) as exc_info:
            await analyze_answer_endpoint(
                request=request,
                service=service,
            )

        assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY

    async def test_invalid_schema_maps_to_502(self):
        payload = make_llm_payload(answer_quality="bogus")
        fake_client = FakeLLMClient(response=payload)
        service = AnswerAnalysisService(llm_client=fake_client)
        request = make_request()

        with pytest.raises(HTTPException) as exc_info:
            await analyze_answer_endpoint(
                request=request,
                service=service,
            )

        assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY