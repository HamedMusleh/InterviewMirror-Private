from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.screening import get_screening_repository
from app.modules.screening.repository import ScreeningResultRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.interview_repository import InterviewRepository
from app.services.interview_creation_service import InterviewCreationService


def get_interview_creation_service(
    db: Annotated[Session, Depends(get_db)],
    screening_repository: Annotated[
        ScreeningResultRepository,
        Depends(get_screening_repository),
    ],
) -> InterviewCreationService:
    return InterviewCreationService(
        application_repository=ApplicationRepository(db),
        screening_repository=screening_repository,
        interview_repository=InterviewRepository(db),
    )
