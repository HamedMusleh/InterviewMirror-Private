"""FastAPI dependency-injection providers for the answer-analysis feature."""

from __future__ import annotations

from fastapi import Depends

from app.dependencies.interfaces.answer_analysis_service_interface import (
    IAnswerAnalysisService,
)
from app.dependencies.interfaces.llm_client_interface import ILLMClient
from app.services.answer_analysis_service import AnswerAnalysisService
from app.services.llm_client import get_openai_client


def get_answer_analysis_service(
    llm_client: ILLMClient = Depends(get_openai_client),
) -> IAnswerAnalysisService:
    """Build the answer-analysis service using the shared LLM client."""
    return AnswerAnalysisService(llm_client=llm_client)
