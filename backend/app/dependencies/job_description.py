from functools import lru_cache

from app.dependencies.interfaces.job_description_embedding_interface import (
    JobDescriptionEmbeddingInterface,
)
from app.services.job_description_embedding_service import (
    JobDescriptionEmbeddingService,
)
from app.services.job_description_service import JobDescriptionService


@lru_cache
def get_job_description_embedding_service(
) -> JobDescriptionEmbeddingInterface:
    return JobDescriptionEmbeddingService()


@lru_cache
def get_job_description_service() -> JobDescriptionService:
    return JobDescriptionService()