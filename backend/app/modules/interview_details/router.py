from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.dependencies.interview_details import get_interview_details_handler
from app.handlers.interview_details_handler import (
    InterviewDetailsHandler,
    InterviewNotFoundError,
)
from app.schemas.interview_details import InterviewDetailsResponse


router = APIRouter(
    prefix="/api/interviews",
    tags=["Interview Details"],
)


@router.get(
    "/{interview_id}/details",
    response_model=InterviewDetailsResponse,
    summary="Retrieve per-question interview details (questions, answers, evaluation breakdown)",
)
def get_interview_details(
    interview_id: Annotated[int, Path(gt=0)],
    handler: Annotated[
        InterviewDetailsHandler,
        Depends(get_interview_details_handler),
    ],
) -> InterviewDetailsResponse:
    try:
        return handler.get_details(interview_id)
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc