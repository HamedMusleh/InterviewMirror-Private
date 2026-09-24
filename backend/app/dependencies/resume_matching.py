from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from openai import AzureOpenAI
from sqlalchemy.orm import Session

from app.core.logging import ILogger, get_logger
from app.dependencies.interfaces.llm_client_interface import (
    StructuredLLMClientInterface,
)
from app.modules.resume_matching.pipeline import ResumeMatchingPipeline
from app.repositories.resume_matching_repository import (
    ResumeMatchingRepository,
)
from app.services.llm_client import (
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AzureOpenAIClient,
    get_openai_client,
)
from app.services.resume_matching_service import ResumeMatchingService


class ResumeMatchingDependencies:
    """FastAPI dependency providers for the resume-matching feature."""

    @staticmethod
    def get_llm_client(
        client: Annotated[AzureOpenAI, Depends(get_openai_client)],
    ) -> StructuredLLMClientInterface:
        return AzureOpenAIClient(
            client=client,
            deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
        )

    @staticmethod
    def get_resume_matching_logger() -> ILogger:
        return get_logger()

    @staticmethod
    def _get_database_session() -> Generator[Session, None, None]:
        """Resolve the database only when a stored match is requested."""
        from app.dependencies.db import get_db

        yield from get_db()

    @staticmethod
    def get_resume_matching_repository(
        db: Annotated[
            Session,
            Depends(_get_database_session),
        ],
    ) -> ResumeMatchingRepository:
        return ResumeMatchingRepository(db)

    @staticmethod
    def get_resume_matching_pipeline(
        llm_client: Annotated[
            StructuredLLMClientInterface,
            Depends(get_llm_client),
        ],
    ) -> ResumeMatchingPipeline:
        return ResumeMatchingPipeline(
            llm_client=llm_client,
            matching_service=ResumeMatchingService(),
        )

    @staticmethod
    def get_database_resume_matching_pipeline(
        llm_client: Annotated[
            StructuredLLMClientInterface,
            Depends(get_llm_client),
        ],
        repository: Annotated[
            ResumeMatchingRepository,
            Depends(get_resume_matching_repository),
        ],
    ) -> ResumeMatchingPipeline:
        return ResumeMatchingPipeline(
            llm_client=llm_client,
            matching_service=ResumeMatchingService(),
            repository=repository,
        )
