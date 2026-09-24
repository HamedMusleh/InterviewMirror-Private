from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.interview_context import (
    get_application_repository,
    get_interview_repository,
)
from app.dependencies.job_opportunity import (
    get_job_opportunity_repository,
)
from app.repositories.application_repository import ApplicationRepository
from app.repositories.candidate_ranking_repository import (
    CandidateRankingRepository,
)
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.services.candidate_ranking_service import CandidateRankingService


def get_candidate_ranking_repository(
    db: Annotated[Session, Depends(get_db)],
) -> CandidateRankingRepository:
    return CandidateRankingRepository(db)


def get_candidate_ranking_service(
    ranking_repository: Annotated[
        CandidateRankingRepository,
        Depends(get_candidate_ranking_repository),
    ],
    application_repository: Annotated[
        ApplicationRepository, Depends(get_application_repository)
    ],
    interview_repository: Annotated[
        InterviewRepository, Depends(get_interview_repository)
    ],
    job_opportunity_repository: Annotated[
        JobOpportunityRepository, Depends(get_job_opportunity_repository)
    ],
) -> CandidateRankingService:
    return CandidateRankingService(
        ranking_repository=ranking_repository,
        application_repository=application_repository,
        interview_repository=interview_repository,
        job_opportunity_repository=job_opportunity_repository,
    )
