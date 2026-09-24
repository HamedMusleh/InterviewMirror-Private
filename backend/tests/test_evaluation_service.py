import pytest

from app.prompts.evaluation_prompt import EVALUATION_SYSTEM_PROMPT
from app.schemas.evaluation import EvaluationInput, EvaluationResult
from app.services.evaluation_service import EvaluationService


class MockStructuredLLMClient:
    def __init__(self, response: EvaluationResult):
        self.response = response
        self.received_system_prompt = None
        self.received_user_prompt = None
        self.received_response_model = None

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type,
    ):
        self.received_system_prompt = system_prompt
        self.received_user_prompt = user_prompt
        self.received_response_model = response_model

        return self.response


def valid_input() -> EvaluationInput:
    return EvaluationInput.model_validate(
        {
            "answer_id": 1,
            "question_id": 25,
            "question": "Explain your experience with FastAPI.",
            "skill": "FastAPI",
            "answer": (
                "I used FastAPI to build REST APIs "
                "for a university project."
            ),
            "answer_quality": "medium",
            "relevant_points": [
                "Candidate used FastAPI to build REST APIs."
            ],
            "missing_areas": [
                "Limited technical depth."
            ],
            "evidence": [
                "I used FastAPI to build REST APIs for a university project."
            ],
        }
    )


def valid_result() -> EvaluationResult:
    return EvaluationResult.model_validate(
        {
            "criteria_scores": {
                "relevance": 9,
                "correctness": 8,
                "depth": 6,
                "practicality": 7,
            },
            "strengths": [
                "Relevant FastAPI experience."
            ],
            "weaknesses": [
                "Limited technical depth."
            ],
        }
    )


@pytest.mark.anyio
async def test_evaluation_service_returns_llm_result():
    expected_result = valid_result()

    mock_client = MockStructuredLLMClient(
        response=expected_result
    )

    service = EvaluationService(
        llm_client=mock_client
    )

    result = await service.evaluate_answer(
        valid_input()
    )

    assert result == expected_result
    assert result.criteria_scores.relevance == 9
    assert result.criteria_scores.correctness == 8
    assert result.criteria_scores.depth == 6
    assert result.criteria_scores.practicality == 7


@pytest.mark.anyio
async def test_evaluation_service_uses_evaluation_system_prompt():
    mock_client = MockStructuredLLMClient(
        response=valid_result()
    )

    service = EvaluationService(
        llm_client=mock_client
    )

    await service.evaluate_answer(
        valid_input()
    )

    assert (
        mock_client.received_system_prompt
        == EVALUATION_SYSTEM_PROMPT
    )


@pytest.mark.anyio
async def test_evaluation_service_builds_user_prompt():
    mock_client = MockStructuredLLMClient(
        response=valid_result()
    )

    service = EvaluationService(
        llm_client=mock_client
    )

    await service.evaluate_answer(
        valid_input()
    )

    assert (
        "Explain your experience with FastAPI."
        in mock_client.received_user_prompt
    )

    assert (
        "I used FastAPI to build REST APIs"
        in mock_client.received_user_prompt
    )

    assert "Limited technical depth." in (
        mock_client.received_user_prompt
    )


@pytest.mark.anyio
async def test_evaluation_service_requests_evaluation_result_schema():
    mock_client = MockStructuredLLMClient(
        response=valid_result()
    )

    service = EvaluationService(
        llm_client=mock_client
    )

    await service.evaluate_answer(
        valid_input()
    )

    assert (
        mock_client.received_response_model
        is EvaluationResult
    )