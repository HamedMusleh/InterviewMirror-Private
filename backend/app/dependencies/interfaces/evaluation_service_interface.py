from typing import Protocol, runtime_checkable

from app.schemas.evaluation import EvaluationInput, EvaluationResult


@runtime_checkable
class IEvaluationService(Protocol):
    """Contract for services that evaluate a candidate's interview answer."""

    async def evaluate_answer(
        self,
        context: EvaluationInput,
    ) -> EvaluationResult:
        ...