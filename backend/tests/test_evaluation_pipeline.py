import pytest

from app.modules.evaluation.pipeline import run_evaluation_pipeline
from app.schemas.evaluation import (
    CriteriaScores,
    EvaluationInput,
    EvaluationResult,
)
from app.services.evaluation_scoring_service import (
    EvaluationScoringService,
)


class MockEvaluationService:
    async def evaluate_answer(
        self,
        context: EvaluationInput,
    ) -> EvaluationResult:
        return EvaluationResult(
            criteria_scores=CriteriaScores(
                relevance=9,
                correctness=8,
                depth=6,
                practicality=7,
            ),
            strengths=[
                "Relevant FastAPI experience",
            ],
            weaknesses=[
                "Limited technical depth",
            ],
        )


def valid_input() -> EvaluationInput:
    return EvaluationInput(
        answer_id=1,
        question_id=25,
        question="Explain your experience with FastAPI.",
        skill="FastAPI",
        answer=(
            "I used FastAPI to build REST APIs "
            "for a university project."
        ),
        answer_quality="medium",
        relevant_points=[
            "Candidate used FastAPI to build REST APIs",
        ],
        missing_areas=[
            "Limited technical depth",
        ],
        evidence=[
            "I used FastAPI to build REST APIs "
            "for a university project.",
        ],
    )


@pytest.mark.anyio
async def test_evaluation_pipeline_returns_final_result():
    evaluation_service = MockEvaluationService()
    scoring_service = EvaluationScoringService()

    result = await run_evaluation_pipeline(
        context=valid_input(),
        evaluation_service=evaluation_service,
        scoring_service=scoring_service,
    )

    assert result.score == 7.65

    assert result.criteria_scores.relevance == 9
    assert result.criteria_scores.correctness == 8
    assert result.criteria_scores.depth == 6
    assert result.criteria_scores.practicality == 7

    assert result.strengths == [
        "Relevant FastAPI experience",
    ]

    assert result.weaknesses == [
        "Limited technical depth",
    ]