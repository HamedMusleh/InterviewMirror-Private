from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.handlers.screening_result_handler import ScreeningResultHandler
from app.repositories.SQLAlchemyScreeningResultRepository import (
    SQLAlchemyScreeningResultRepository,
)
from app.modules.screening.pipeline import ScreeningPipeline
from app.modules.screening.repository import ScreeningResultRepository


def get_screening_result_handler() -> ScreeningResultHandler:
    return ScreeningResultHandler()


def get_screening_repository(
    db: Annotated[Session, Depends(get_db)],
    handler: Annotated[ScreeningResultHandler, Depends(get_screening_result_handler)],
) -> ScreeningResultRepository:
    return SQLAlchemyScreeningResultRepository(db, handler)


def get_screening_pipeline(
    repository: Annotated[ScreeningResultRepository, Depends(get_screening_repository)],
) -> ScreeningPipeline:
    return ScreeningPipeline(repository)