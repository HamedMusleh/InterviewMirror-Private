from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.job_opportunity import get_job_opportunity_repository
from app.handlers.candidate_report_handler import CandidateReportHandler
from app.repositories.application_repository import ApplicationRepository
from app.repositories.candidate_evaluation_repository import (
    CandidateEvaluationRepository,
)
from app.repositories.candidate_report_repository import (
    CandidateReportRepository,
)
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.repositories.user_repository import UserRepository


def get_candidate_report_repository(
    db: Annotated[Session, Depends(get_db)],
) -> CandidateReportRepository:
    return CandidateReportRepository(db)


def get_candidate_evaluation_repository(
    db: Annotated[Session, Depends(get_db)],
) -> CandidateEvaluationRepository:
    return CandidateEvaluationRepository(db)


def get_interview_repository(
    db: Annotated[Session, Depends(get_db)],
) -> InterviewRepository:
    return InterviewRepository(db)


def get_application_repository(
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationRepository:
    return ApplicationRepository(db)


def get_candidate_repository(
    db: Annotated[Session, Depends(get_db)],
) -> CandidateRepository:
    return CandidateRepository(db)


def get_user_repository(
    db: Annotated[Session, Depends(get_db)],
) -> UserRepository:
    return UserRepository(db)


def get_candidate_report_handler(
    candidate_report_repository: Annotated[
        CandidateReportRepository,
        Depends(get_candidate_report_repository),
    ],
    candidate_evaluation_repository: Annotated[
        CandidateEvaluationRepository,
        Depends(get_candidate_evaluation_repository),
    ],
    interview_repository: Annotated[
        InterviewRepository,
        Depends(get_interview_repository),
    ],
    application_repository: Annotated[
        ApplicationRepository,
        Depends(get_application_repository),
    ],
    candidate_repository: Annotated[
        CandidateRepository,
        Depends(get_candidate_repository),
    ],
    user_repository: Annotated[
        UserRepository,
        Depends(get_user_repository),
    ],
    job_opportunity_repository: Annotated[
        JobOpportunityRepository,
        Depends(get_job_opportunity_repository),
    ],
) -> CandidateReportHandler:
    return CandidateReportHandler(
        candidate_report_repository=candidate_report_repository,
        candidate_evaluation_repository=candidate_evaluation_repository,
        interview_repository=interview_repository,
        application_repository=application_repository,
        candidate_repository=candidate_repository,
        user_repository=user_repository,
        job_opportunity_repository=job_opportunity_repository,
    )
