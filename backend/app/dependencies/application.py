from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.candidate import (
    get_candidate_repository,
    get_user_repository,
)
from app.dependencies.db import get_db
from app.dependencies.interfaces.llm_client_interface import (
    StructuredLLMClientInterface,
)
from app.dependencies.interview import get_interview_creation_service
from app.dependencies.interview_context import (
    get_application_repository,
)
from app.dependencies.job_opportunity import (
    get_job_opportunity_repository,
)
from app.dependencies.resume_matching import ResumeMatchingDependencies
from app.dependencies.screening import get_screening_pipeline
from app.dependencies.screening_criteria import (
    get_screening_criteria_repository,
)
from app.modules.resume_matching.pipeline import ResumeMatchingPipeline
from app.modules.resume_parser.pipeline import CVParserPipeline
from app.modules.resume_parser.router import get_cv_parser_pipeline
from app.modules.screening.pipeline import ScreeningPipeline
from app.repositories.application_repository import ApplicationRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.repositories.resume_matching_repository import (
    ResumeMatchingRepository,
)
from app.repositories.resume_repository import SQLAlchemyResumeRepository
from app.repositories.screening_criteria_repository import (
    ScreeningCriteriaRepository,
)
from app.repositories.user_repository import UserRepository
from app.services.application_service import ApplicationService
from app.services.interview_creation_service import (
    InterviewCreationService,
)
from app.services.resume_matching_service import ResumeMatchingService


def get_resume_repository(
    db: Annotated[Session, Depends(get_db)],
) -> SQLAlchemyResumeRepository:
    return SQLAlchemyResumeRepository(db)


def get_application_resume_matching_pipeline(
    db: Annotated[Session, Depends(get_db)],
    llm_client: Annotated[
        StructuredLLMClientInterface,
        Depends(ResumeMatchingDependencies.get_llm_client),
    ],
) -> ResumeMatchingPipeline:
    """Resume matching pipeline for the application-submission flow.

    Built directly on this request's shared `db` session instead of
    ResumeMatchingDependencies.get_database_resume_matching_pipeline,
    which opens its own independent session (see
    ResumeMatchingDependencies._get_database_session). That's fine for
    the standalone POST /api/resume-matching/applications/{id}
    endpoint, which only matches applications/resumes that an earlier,
    already-committed request created -- but here, the application and
    resume this flow just created are only flushed, not committed, so
    a separate session would not see them yet and matching would fail
    with ResumeMatchingNotFoundError. Reusing the shared session lets
    matching read this request's own uncommitted writes, which is what
    keeps the whole flow atomic without needing an early commit.

    """
    repository = ResumeMatchingRepository(db)

    return ResumeMatchingPipeline(
        llm_client=llm_client,
        matching_service=ResumeMatchingService(),
        repository=repository,
    )


def get_application_service(
    application_repository: Annotated[
        ApplicationRepository, Depends(get_application_repository)
    ],
    resume_repository: Annotated[
        SQLAlchemyResumeRepository, Depends(get_resume_repository)
    ],
    job_opportunity_repository: Annotated[
        JobOpportunityRepository, Depends(get_job_opportunity_repository)
    ],
    user_repository: Annotated[
        UserRepository, Depends(get_user_repository)
    ],
    candidate_repository: Annotated[
        CandidateRepository, Depends(get_candidate_repository)
    ],
    screening_criteria_repository: Annotated[
        ScreeningCriteriaRepository,
        Depends(get_screening_criteria_repository),
    ],
    cv_parser_pipeline: Annotated[
        CVParserPipeline, Depends(get_cv_parser_pipeline)
    ],
    resume_matching_pipeline: Annotated[
        ResumeMatchingPipeline,
        Depends(get_application_resume_matching_pipeline),
    ],
    screening_pipeline: Annotated[
        ScreeningPipeline, Depends(get_screening_pipeline)
    ],
    interview_creation_service: Annotated[
        InterviewCreationService, Depends(get_interview_creation_service)
    ],
) -> ApplicationService:
    return ApplicationService(
        application_repository=application_repository,
        resume_repository=resume_repository,
        job_opportunity_repository=job_opportunity_repository,
        user_repository=user_repository,
        candidate_repository=candidate_repository,
        screening_criteria_repository=screening_criteria_repository,
        cv_parser_pipeline=cv_parser_pipeline,
        resume_matching_pipeline=resume_matching_pipeline,
        screening_pipeline=screening_pipeline,
        interview_creation_service=interview_creation_service,
    )
