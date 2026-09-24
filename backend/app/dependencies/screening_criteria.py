from typing import Annotated

from fastapi import Depends
from openai import AzureOpenAI
from sqlalchemy.orm import Session

from app.core.logging import ILogger, get_logger
from app.dependencies.db import get_db
from app.dependencies.job_opportunity import (
    get_job_opportunity_repository,
)
from app.handlers.screening_criteria_handler import (
    ScreeningCriteriaHandler,
)
from app.modules.screening_criteria.pipeline import (
    ScreeningCriteriaPipeline,
)
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.repositories.screening_criteria_repository import (
    ScreeningCriteriaRepository,
)
from app.services.llm_client import get_openai_client


def get_screening_criteria_repository(
    db: Annotated[Session, Depends(get_db)],
) -> ScreeningCriteriaRepository:
    return ScreeningCriteriaRepository(db)


def get_screening_criteria_pipeline(
    logger: Annotated[ILogger, Depends(get_logger)],
    client: Annotated[AzureOpenAI, Depends(get_openai_client)],
) -> ScreeningCriteriaPipeline:
    return ScreeningCriteriaPipeline(logger, client)


def get_screening_criteria_handler(
    logger: Annotated[ILogger, Depends(get_logger)],
    pipeline: Annotated[
        ScreeningCriteriaPipeline,
        Depends(get_screening_criteria_pipeline),
    ],
    screening_criteria_repository: Annotated[
        ScreeningCriteriaRepository,
        Depends(get_screening_criteria_repository),
    ],
    job_opportunity_repository: Annotated[
        JobOpportunityRepository,
        Depends(get_job_opportunity_repository),
    ],
) -> ScreeningCriteriaHandler:
    return ScreeningCriteriaHandler(
        logger=logger,
        pipeline=pipeline,
        screening_criteria_repository=screening_criteria_repository,
        job_opportunity_repository=job_opportunity_repository,
    )