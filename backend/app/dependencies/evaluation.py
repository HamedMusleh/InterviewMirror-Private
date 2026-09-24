from fastapi import Depends

from app.dependencies.interfaces.llm_client_interface import (
    StructuredLLMClientInterface,
)
from app.services.evaluation_service import EvaluationService
from app.services.evaluation_scoring_service import (
    EvaluationScoringService,
)
from app.services.llm_client import AzureOpenAIClient
from app.services.llm_client import get_openai_client


def get_evaluation_llm_client() -> StructuredLLMClientInterface:
    """Return the shared Azure OpenAI client adapter."""

    return AzureOpenAIClient(
        client=get_openai_client(),
    )


def get_evaluation_service(
    llm_client: StructuredLLMClientInterface = Depends(
        get_evaluation_llm_client
    ),
) -> EvaluationService:
    """Build the evaluation service."""

    return EvaluationService(
        llm_client=llm_client,
    )


def get_evaluation_scoring_service() -> EvaluationScoringService:
    """Build the deterministic evaluation scoring service."""

    return EvaluationScoringService()