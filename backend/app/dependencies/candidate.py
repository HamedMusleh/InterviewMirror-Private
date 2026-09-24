from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.user_repository import UserRepository
from app.services.candidate_service import CandidateService


def get_candidate_repository(
    db: Annotated[Session, Depends(get_db)],
) -> CandidateRepository:
    return CandidateRepository(db)


def get_user_repository(
    db: Annotated[Session, Depends(get_db)],
) -> UserRepository:
    return UserRepository(db)


def get_candidate_service(
    candidate_repository: Annotated[
        CandidateRepository, Depends(get_candidate_repository)
    ],
    user_repository: Annotated[
        UserRepository, Depends(get_user_repository)
    ],
) -> CandidateService:
    return CandidateService(
        candidate_repository=candidate_repository,
        user_repository=user_repository,
    )
