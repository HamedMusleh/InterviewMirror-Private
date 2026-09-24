from app.schemas.evaluation import (
    EvaluationInput,
    FinalEvaluationResult,
)
from app.services.evaluation_scoring_service import (
    EvaluationScoringService,
)
from app.services.evaluation_service import EvaluationService


async def run_evaluation_pipeline(
    context: EvaluationInput,
    evaluation_service: EvaluationService,
    scoring_service: EvaluationScoringService,
) -> FinalEvaluationResult:
    """
    Run the complete evaluation pipeline.

    1. Ask the LLM to evaluate the candidate answer.
    2. Calculate the deterministic weighted score.
    3. Return the final evaluation result.
    """
    evaluation_result = await evaluation_service.evaluate_answer(
        context
    )

    return scoring_service.build_final_result(
        evaluation_result
    )