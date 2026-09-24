from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.job_opportunity import (
    get_job_opportunity_repository,
)
from app.dependencies.speech_to_text import get_speech_to_text_service
from app.repositories.application_repository import ApplicationRepository
from app.repositories.interview_answer_repository import (
    InterviewAnswerRepository,
)
from app.repositories.interview_question_repository import (
    InterviewQuestionRepository,
)
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.services.interview_context_service import InterviewContextService
from app.services.speech_to_text_service import SpeechToTextService


def get_interview_question_repository(
    db: Annotated[Session, Depends(get_db)],
) -> InterviewQuestionRepository:
    return InterviewQuestionRepository(db)


def get_interview_answer_repository(
    db: Annotated[Session, Depends(get_db)],
) -> InterviewAnswerRepository:
    return InterviewAnswerRepository(db)


def get_interview_repository(
    db: Annotated[Session, Depends(get_db)],
) -> InterviewRepository:
    return InterviewRepository(db)


def get_application_repository(
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationRepository:
    return ApplicationRepository(db)


def get_interview_context_service(
    question_repository: Annotated[
        InterviewQuestionRepository,
        Depends(get_interview_question_repository),
    ],
    answer_repository: Annotated[
        InterviewAnswerRepository, Depends(get_interview_answer_repository)
    ],
    interview_repository: Annotated[
        InterviewRepository, Depends(get_interview_repository)
    ],
    application_repository: Annotated[
        ApplicationRepository, Depends(get_application_repository)
    ],
    job_opportunity_repository: Annotated[
        JobOpportunityRepository, Depends(get_job_opportunity_repository)
    ],
    speech_to_text_service: Annotated[
        SpeechToTextService, Depends(get_speech_to_text_service)
    ],
) -> InterviewContextService:
    return InterviewContextService(
        question_repository=question_repository,
        answer_repository=answer_repository,
        interview_repository=interview_repository,
        application_repository=application_repository,
        job_opportunity_repository=job_opportunity_repository,
        speech_to_text_service=speech_to_text_service,
    )
