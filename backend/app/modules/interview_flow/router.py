from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.interview_flow import (
    get_interview_flow_service,
)
from app.schemas.interview_context import InterviewContextRequest
from app.schemas.interview_flow import (
    InterviewFlowResult,
    InterviewStatusResponse,
)
from app.services.interview_flow_service import (
    InterviewFlowService,
)


router = APIRouter(
    prefix="/api/interview-flow",
    tags=["Interview Flow"],
)


@router.get(
    "/{interview_id}/status",
    response_model=InterviewStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_interview_status(
    interview_id: int,
    service: Annotated[
        InterviewFlowService,
        Depends(get_interview_flow_service),
    ],
) -> InterviewStatusResponse:
    try:
        return await service.get_status(interview_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{interview_id}/start",
    response_model=InterviewStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def start_interview(
    interview_id: int,
    service: Annotated[
        InterviewFlowService,
        Depends(get_interview_flow_service),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
) -> InterviewStatusResponse:
    """
    Mark the interview as begun and report where the candidate is.

    Safe to call on every visit to the room: the start stamp is written only
    the first time, so a reload resumes the existing clock instead of
    restarting it.
    """

    try:
        result = await service.start(interview_id)

        db.commit()

        return result

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/answers",
    response_model=InterviewFlowResult,
    status_code=status.HTTP_200_OK,
)
async def submit_answer(
    request: InterviewContextRequest,
    service: Annotated[
        InterviewFlowService,
        Depends(get_interview_flow_service),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
) -> InterviewFlowResult:
    try:
        result = await service.submit_answer(request)

        db.commit()

        return result

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc