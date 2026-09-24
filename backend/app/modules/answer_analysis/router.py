"""
Router for the Answer Analysis feature.

Endpoint responsibility only: request/response wiring and HTTP-level error
mapping. All actual logic lives in the pipeline/service.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.answer_analysis import get_answer_analysis_service
from app.dependencies.interfaces.answer_analysis_service_interface import (
    IAnswerAnalysisService,
)
from app.modules.answer_analysis.pipeline import run_answer_analysis_pipeline
from app.schemas.answer_analysis import AnswerAnalysis, AnswerAnalysisInput
from app.services.answer_analysis_service import (
    AnswerAnalysisError,
    LLMProviderError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/answers",
    tags=["answer-analysis"],
)


@router.post(
    "/analyze",
    response_model=AnswerAnalysis,
    status_code=status.HTTP_200_OK,
    summary="Analyze a candidate's interview answer",
)
async def analyze_answer(
    request: AnswerAnalysisInput,
    service: IAnswerAnalysisService = Depends(
        get_answer_analysis_service
    ),
) -> AnswerAnalysis:
    try:
        return await run_answer_analysis_pipeline(
            request,
            service,
        )

    except LLMProviderError as exc:
        logger.error("LLM provider call failed: %s", exc)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Answer analysis is temporarily unavailable. "
                "Please try again."
            ),
        ) from exc

    except AnswerAnalysisError as exc:
        logger.error("LLM response failed validation: %s", exc)

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Received an invalid response while analyzing the answer."
            ),
        ) from exc
