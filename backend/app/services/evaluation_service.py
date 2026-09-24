from app.dependencies.interfaces.llm_client_interface import (
    StructuredLLMClientInterface,
)
from app.prompts.evaluation_prompt import (
    EVALUATION_SYSTEM_PROMPT,
    build_evaluation_prompt,
)
from app.schemas.evaluation import (
    EvaluationInput,
    EvaluationResult,
)


class EvaluationService:
    """Evaluate a candidate's interview answer using the configured LLM."""

    def __init__(
        self,
        llm_client: StructuredLLMClientInterface,
    ) -> None:
        self._llm_client = llm_client

    async def evaluate_answer(
        self,
        context: EvaluationInput,
    ) -> EvaluationResult:
        prompt = build_evaluation_prompt(context)

        return await self._llm_client.complete_structured(
            system_prompt=EVALUATION_SYSTEM_PROMPT,
            user_prompt=prompt,
            response_model=EvaluationResult,
        )