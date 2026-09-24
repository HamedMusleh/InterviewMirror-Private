import pytest

from app.schemas.candidate_report import GeneratedReportContent
from app.services.candidate_report_service import (
    CandidateReportError,
    CandidateReportService,
)


class FakeLLMClient:
    def __init__(
        self,
        response: GeneratedReportContent | None = None,
        error: Exception | None = None,
    ):
        self.response = response
        self.error = error
        self.system_prompt = None
        self.user_prompt = None
        self.response_model = None

    async def complete_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model,
    ):
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.response_model = response_model

        if self.error:
            raise self.error

        return self.response


@pytest.mark.anyio
async def test_generate_report_returns_generated_content():
    expected = GeneratedReportContent(
        summary="The candidate demonstrated good backend knowledge.",
        strengths=["Strong Python knowledge"],
        areas_for_improvement=[
            "Needs greater technical depth in FastAPI"
        ],
        recommendation=(
            "The candidate demonstrates good potential for the role."
        ),
    )

    llm_client = FakeLLMClient(response=expected)
    service = CandidateReportService(llm_client=llm_client)

    result = await service.generate_report(
        system_prompt="system instructions",
        user_prompt="evaluation data",
    )

    assert result == expected
    assert llm_client.system_prompt == "system instructions"
    assert llm_client.user_prompt == "evaluation data"
    assert llm_client.response_model is GeneratedReportContent


@pytest.mark.anyio
async def test_generate_report_converts_llm_error():
    llm_client = FakeLLMClient(
        error=RuntimeError("LLM failed")
    )
    service = CandidateReportService(llm_client=llm_client)

    with pytest.raises(CandidateReportError):
        await service.generate_report(
            system_prompt="system instructions",
            user_prompt="evaluation data",
        )
