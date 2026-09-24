from typing import Annotated

from fastapi import Depends

from app.dependencies.candidate import (
    get_candidate_repository,
    get_user_repository,
)
from app.dependencies.interview_context import (
    get_application_repository,
    get_interview_repository,
)
from app.dependencies.job_opportunity import (
    get_job_opportunity_repository,
)
from app.dependencies.screening import get_screening_repository
from app.dependencies.screening_criteria import (
    get_screening_criteria_repository,
)
from app.modules.screening.repository import ScreeningResultRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.repositories.screening_criteria_repository import (
    ScreeningCriteriaRepository,
)
from app.repositories.user_repository import UserRepository
from app.services.application_status_service import ApplicationStatusService


def get_application_status_service(
    job_opportunity_repository: Annotated[
        JobOpportunityRepository, Depends(get_job_opportunity_repository)
    ],
    screening_criteria_repository: Annotated[
        ScreeningCriteriaRepository,
        Depends(get_screening_criteria_repository),
    ],
    user_repository: Annotated[
        UserRepository, Depends(get_user_repository)
    ],
    candidate_repository: Annotated[
        CandidateRepository, Depends(get_candidate_repository)
    ],
    application_repository: Annotated[
        ApplicationRepository, Depends(get_application_repository)
    ],
    screening_repository: Annotated[
        ScreeningResultRepository, Depends(get_screening_repository)
    ],
    interview_repository: Annotated[
        InterviewRepository, Depends(get_interview_repository)
    ],
) -> ApplicationStatusService:
    return ApplicationStatusService(
        job_opportunity_repository=job_opportunity_repository,
        screening_criteria_repository=screening_criteria_repository,
        user_repository=user_repository,
        candidate_repository=candidate_repository,
        application_repository=application_repository,
        screening_repository=screening_repository,
        interview_repository=interview_repository,
    )
