"""
Router for the Role-Based Question Generation feature.

Endpoint responsibility only: request/response wiring and HTTP-level error
mapping. All actual logic lives in the pipeline/service.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.interfaces.question_generation_service_interface import (
    IQuestionGenerationService,
)
from app.dependencies.question_generation import get_question_generation_service
from app.modules.question_generation.pipeline import run_question_generation_pipeline
from app.schemas.interview_question import QuestionGenerationResponse
from app.schemas.question_generation import QuestionGenerationInput
from app.services.question_generation_service import (
    LLMProviderError,
    QuestionGenerationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/questions",
    tags=["question-generation"],
)


@router.post(
    "/generate",
    response_model=QuestionGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate role-based interview questions",
)
async def generate_questions(
    request: QuestionGenerationInput,
    service: IQuestionGenerationService = Depends(
        get_question_generation_service
    ),
) -> QuestionGenerationResponse:
    try:
        return await run_question_generation_pipeline(
            request,
            service,
        )

    except LLMProviderError as exc:
        logger.error("LLM provider call failed: %s", exc)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Question generation is temporarily unavailable. "
                "Please try again."
            ),
        ) from exc

    except QuestionGenerationError as exc:
        logger.error("LLM response failed validation: %s", exc)

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Received an invalid response while generating questions."
            ),
        ) from exc
