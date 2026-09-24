import logging
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.dependencies.blob_storage import get_blob_storage_service
from app.dependencies.db import get_db
from app.dependencies.speech_to_text import get_speech_to_text_service
from app.repositories.interview_question_repository import (
    InterviewQuestionRepository,
)
from app.schemas.interview_answer import InterviewAnswerResponse
from app.services.blob_storage_service import BlobStorageService
from app.services.interview_answer_service import InterviewAnswerService
from app.services.speech_to_text_service import SpeechToTextService


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/interview-answers",
    tags=["Interview Answers"],
)


@router.post(
    "/audio",
    response_model=InterviewAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_audio_answer(
    question_id: int = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    blob_storage_service: BlobStorageService = Depends(
        get_blob_storage_service
    ),
    speech_to_text_service: SpeechToTextService = Depends(
        get_speech_to_text_service
    ),
):
    try:
        question_repository = InterviewQuestionRepository(db)

        if question_repository.get_by_id(question_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview question not found.",
            )

        audio_data = await audio.read()

        if not audio_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file is empty.",
            )

        content_type = audio.content_type or "audio/webm"

        extension = "webm"

        if content_type == "audio/wav":
            extension = "wav"
        elif content_type == "audio/mpeg":
            extension = "mp3"

        blob_name = (
            f"interview-answers/"
            f"question-{question_id}-{uuid4()}.{extension}"
        )

        audio_url = await run_in_threadpool(
            blob_storage_service.upload_audio,
            audio_data=audio_data,
            blob_name=blob_name,
            content_type=content_type,
        )

        transcript = await run_in_threadpool(
            speech_to_text_service.transcribe,
            audio_url,
        )

        answer_service = InterviewAnswerService(db)

        return answer_service.create_audio_answer(
            question_id=question_id,
            audio_url=audio_url,
            transcript=transcript,
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        logger.exception("Failed to process interview answer.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process interview answer.",
        ) from exc