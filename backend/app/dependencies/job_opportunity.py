from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)


def get_job_opportunity_repository(
    db: Annotated[Session, Depends(get_db)],
) -> JobOpportunityRepository:
    return JobOpportunityRepository(db)