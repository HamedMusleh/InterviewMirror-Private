from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.interview_context import (
    get_interview_context_service,
)
from app.schemas.interview_context import (
    InterviewContext,
    InterviewContextRequest,
)
from app.services.interview_context_service import InterviewContextService


router = APIRouter(
    prefix="/api/interview-context",
    tags=["Interview Context"],
)


@router.post(
    "",
    response_model=InterviewContext,
    status_code=status.HTTP_200_OK,
)
def build_interview_context(
    request: InterviewContextRequest,
    service: Annotated[
        InterviewContextService, Depends(get_interview_context_service)
    ],
) -> InterviewContext:
    try:
        return service.build_context(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
