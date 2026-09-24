import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.interfaces.question_generation_service_interface import (
    IQuestionGenerationService,
)
from app.dependencies.interview import get_interview_creation_service
from app.dependencies.question_generation import get_question_generation_service
from app.modules.interviews.preparation import ensure_interview_questions
from app.schemas.interview import (
    InterviewCreateRequest,
    InterviewCreationResponse,
    InterviewResponse,
)
from app.services.interview_creation_service import (
    ApplicationNotFoundError,
    ApplicationNotRecommendedError,
    InterviewCreationService,
    ScreeningResultNotFoundError,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/interviews",
    tags=["Interviews"],
)


@router.post(
    "",
    response_model=InterviewCreationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "model": InterviewCreationResponse,
            "description": "The application already has an interview.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "The application does not exist.",
        },
        status.HTTP_409_CONFLICT: {
            "description": (
                "The application has not been screened or was not "
                "recommended."
            ),
        },
    },
)
async def create_interview(
    request: InterviewCreateRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[
        InterviewCreationService,
        Depends(get_interview_creation_service),
    ],
    generation_service: Annotated[
        IQuestionGenerationService,
        Depends(get_question_generation_service),
    ],
) -> InterviewCreationResponse:
    try:
        result = service.create_for_application(
            application_id=request.application_id,
            scheduled_at=request.scheduled_at,
        )

        db.commit()

        if not result.created:
            response.status_code = status.HTTP_200_OK

        interview = InterviewResponse.model_validate(result.interview)

        # Committed above, so a failure here leaves the interview intact.
        questions_generated = await ensure_interview_questions(
            interview_id=interview.id,
            db=db,
            generation_service=generation_service,
        )

        return InterviewCreationResponse(
            interview=interview,
            created=result.created,
            questions_generated=questions_generated,
        )

    except ApplicationNotFoundError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except (
        ScreeningResultNotFoundError,
        ApplicationNotRecommendedError,
    ) as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create an interview")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create the interview.",
        ) from exc
