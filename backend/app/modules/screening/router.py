from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.screening import get_screening_pipeline
from app.modules.screening.pipeline import ScreeningPipeline
from app.schemas.screening_score import (
    ScreeningResultDetail,
    ScreeningResultSummary,
    ScreeningScoreRequest,
    ScreeningScoreResponse,
)


router = APIRouter(
    prefix="/api/screening",
    tags=["Screening"],
)


@router.post("/score", response_model=ScreeningScoreResponse)
def score_candidate(
    request: ScreeningScoreRequest,
    pipeline: Annotated[
        ScreeningPipeline,
        Depends(get_screening_pipeline),
    ],
) -> ScreeningScoreResponse:
    return pipeline.score_candidate(request)


@router.get("/results/{job_id}", response_model=list[ScreeningResultSummary])
def list_screening_results(
    job_id: str,
    pipeline: Annotated[
        ScreeningPipeline,
        Depends(get_screening_pipeline),
    ],
) -> list[ScreeningResultSummary]:
    return pipeline.list_results_for_job(job_id)


@router.get(
    "/results/application/{application_id}",
    response_model=ScreeningResultDetail,
)
def get_screening_result(
    application_id: int,
    pipeline: Annotated[
        ScreeningPipeline,
        Depends(get_screening_pipeline),
    ],
) -> ScreeningResultDetail:
    result = pipeline.get_result_detail(application_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Screening result not found",
        )

    return result