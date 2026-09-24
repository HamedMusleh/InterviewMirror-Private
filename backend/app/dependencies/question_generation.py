"""FastAPI dependency-injection providers for the question-generation feature."""

from __future__ import annotations

from fastapi import Depends

from app.dependencies.interfaces.llm_client_interface import ILLMClient
from app.dependencies.interfaces.question_generation_service_interface import (
    IQuestionGenerationService,
)
from app.services.llm_client import get_openai_client
from app.services.question_generation_service import QuestionGenerationService


def get_question_generation_service(
    llm_client: ILLMClient = Depends(get_openai_client),
) -> IQuestionGenerationService:
    """Build the question-generation service using the shared LLM client."""
    return QuestionGenerationService(llm_client=llm_client)
