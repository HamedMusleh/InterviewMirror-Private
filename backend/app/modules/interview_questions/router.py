import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.interfaces.question_generation_service_interface import (
    IQuestionGenerationService,
)
from app.dependencies.question_generation import (
    get_question_generation_service,
)
from app.modules.interview_questions.pipeline import (
    ApplicationNotFoundForInterviewError,
    InterviewNotFoundForGenerationError,
    JobOpportunityNotFoundForApplicationError,
    ScreeningCriteriaNotFoundForJobError,
    run_interview_question_generation_pipeline,
)
from app.repositories.interview_question_repository import (
    InterviewQuestionRepository,
)
from app.schemas.adaptive_follow_up import FollowUpQuestionResponse
from app.schemas.interview_question_storage import (
    GeneratedQuestions,
    InterviewQuestionResponse,
    InterviewQuestionsResponse,
)
from app.services.interview_question_service import (
    DuplicateInitialQuestionsError,
    InterviewNotFoundError,
    InterviewQuestionService,
)
from app.services.question_generation_service import (
    LLMProviderError,
    QuestionGenerationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/interview-questions",
    tags=["Interview Questions"],
)


@router.post(
    "/{interview_id}",
    response_model=InterviewQuestionsResponse,
    status_code=status.HTTP_201_CREATED,
)
def store_interview_questions(
    interview_id: int,
    generated_questions: GeneratedQuestions,
    db: Session = Depends(get_db),
):
    try:
        service = InterviewQuestionService(db)

        questions = service.store_questions(
            interview_id=interview_id,
            generated_questions=generated_questions,
        )

        db.commit()

        return InterviewQuestionsResponse(
            questions=questions,
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        logger.error(
            "Failed to store interview questions: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "An unexpected error occurred while storing "
                "interview questions."
            ),
        ) from exc


@router.post(
    "/{interview_id}/follow-up",
    response_model=InterviewQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def store_follow_up_question(
    interview_id: int,
    follow_up: FollowUpQuestionResponse,
    db: Session = Depends(get_db),
):
    try:
        service = InterviewQuestionService(db)

        question = service.store_follow_up_question(
            interview_id=interview_id,
            follow_up=follow_up,
        )

        db.commit()

        return question

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        logger.error(
            "Failed to store follow-up question: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "An unexpected error occurred while storing "
                "the follow-up question."
            ),
        ) from exc


@router.get(
    "/{interview_id}",
    response_model=InterviewQuestionsResponse,
    status_code=status.HTTP_200_OK,
)
def get_interview_questions(
    interview_id: int,
    db: Session = Depends(get_db),
):
    repository = InterviewQuestionRepository(db)

    questions = repository.get_by_interview_id(
        interview_id
    )

    return InterviewQuestionsResponse(
        questions=questions,
    )


@router.post(
    "/{interview_id}/generate",
    response_model=InterviewQuestionsResponse,
    status_code=status.HTTP_201_CREATED,
    summary=(
        "Generate role-based questions from the interview context "
        "and store them"
    ),
)
async def generate_and_store_interview_questions(
    interview_id: int,
    generation_service: IQuestionGenerationService = Depends(
        get_question_generation_service
    ),
    db: Session = Depends(get_db),
):
    try:
        storage_service = InterviewQuestionService(db)

        questions = await run_interview_question_generation_pipeline(
            interview_id=interview_id,
            db=db,
            generation_service=generation_service,
            storage_service=storage_service,
        )

        db.commit()

        return InterviewQuestionsResponse(
            questions=questions,
        )

    except InterviewNotFoundForGenerationError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ApplicationNotFoundForInterviewError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except JobOpportunityNotFoundForApplicationError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ScreeningCriteriaNotFoundForJobError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except InterviewNotFoundError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DuplicateInitialQuestionsError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except LLMProviderError as exc:
        logger.error(
            "LLM provider call failed: %s",
            exc,
        )

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Question generation is temporarily unavailable. "
                "Please try again."
            ),
        ) from exc

    except QuestionGenerationError as exc:
        logger.error(
            "LLM response failed validation: %s",
            exc,
        )

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Received an invalid response while generating "
                "questions."
            ),
        ) from exc

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Unexpected error during interview question generation"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc