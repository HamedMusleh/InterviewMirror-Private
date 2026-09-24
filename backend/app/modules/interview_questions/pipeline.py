"""
Orchestration for the Interview Question Generation integration.

Connects:
Interview
    -> Application
    -> Job Opportunity
    -> Screening Criteria
    -> Question Generation
    -> Interview Question Storage
"""

from sqlalchemy.orm import Session

from app.database.models.interview_question import InterviewQuestion
from app.dependencies.interfaces.question_generation_service_interface import (
    IQuestionGenerationService,
)
from app.modules.question_generation.pipeline import (
    run_question_generation_pipeline,
)
from app.repositories.application_repository import ApplicationRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_opportunity_repository import JobOpportunityRepository
from app.repositories.screening_criteria_repository import (
    ScreeningCriteriaRepository,
)
from app.schemas.interview_question_storage import GeneratedQuestions
from app.schemas.job_description import (
    Experience,
    JobDescriptionResponse,
    Requirements,
    Role,
    ScreeningSettings,
    Skills,
)
from app.schemas.question_generation import QuestionGenerationInput
from app.schemas.screening_criteria import ScreeningCriteria
from app.services.interview_question_service import InterviewQuestionService


class InterviewQuestionGenerationIntegrationError(Exception):
    """Base error for interview question generation integration."""


class InterviewNotFoundForGenerationError(
    InterviewQuestionGenerationIntegrationError
):
    """Raised when the requested interview does not exist."""


class ApplicationNotFoundForInterviewError(
    InterviewQuestionGenerationIntegrationError
):
    """Raised when an interview has no valid application."""


class JobOpportunityNotFoundForApplicationError(
    InterviewQuestionGenerationIntegrationError
):
    """Raised when an application's job opportunity does not exist."""


class ScreeningCriteriaNotFoundForJobError(
    InterviewQuestionGenerationIntegrationError
):
    """Raised when no screening criteria exist for the job opportunity."""


def _build_job_description(
    job_opportunity,
) -> JobDescriptionResponse:
    """
    Reconstruct JobDescriptionResponse from the persisted
    JobOpportunity model.
    """

    return JobDescriptionResponse(
        job_id=job_opportunity.job_id,
        role=Role(
            title=job_opportunity.title,
            department=job_opportunity.department,
            employment_type=job_opportunity.employment_type,
            location=job_opportunity.location,
        ),
        job_summary=job_opportunity.job_summary,
        responsibilities=job_opportunity.responsibilities,
        requirements=Requirements(
            skills=Skills(
                required=job_opportunity.required_skills,
                preferred=job_opportunity.preferred_skills,
            ),
            experience=Experience(
                minimum_years=job_opportunity.minimum_years,
                level=job_opportunity.experience_level,
            ),
            education=job_opportunity.education,
            certifications=job_opportunity.certifications,
            languages=job_opportunity.languages,
        ),
        technical_stack=job_opportunity.technical_stack,
        soft_skills=job_opportunity.soft_skills,
        screening_settings=ScreeningSettings(
            passing_score=job_opportunity.passing_score,
        ),
    )


def _build_screening_criteria(
    job_opportunity,
    screening_criteria_model,
) -> ScreeningCriteria:
    """
    Reconstruct the Pydantic ScreeningCriteria schema from the
    persisted ScreeningCriteria model.

    The database stores the generated criteria inside JSONB.
    """

    criteria_data = dict(screening_criteria_model.criteria)

    return ScreeningCriteria(
        job_id=job_opportunity.job_id,
        screening_criteria=criteria_data["screening_criteria"],
        passing_score=criteria_data.get(
            "passing_score",
            job_opportunity.passing_score,
        ),
    )


async def run_interview_question_generation_pipeline(
    interview_id: int,
    db: Session,
    generation_service: IQuestionGenerationService,
    storage_service: InterviewQuestionService,
) -> list[InterviewQuestion]:
    """
    Generate and store interview questions using only interview_id.

    Flow:
        interview_id
            -> Interview
            -> Application
            -> JobOpportunity
            -> ScreeningCriteria
            -> QuestionGeneration
            -> InterviewQuestionStorage
    """

    interview_repository = InterviewRepository(db)
    application_repository = ApplicationRepository(db)
    job_opportunity_repository = JobOpportunityRepository(db)
    screening_criteria_repository = ScreeningCriteriaRepository(db)

    # ---------------------------------------------------------
    # 1. Get Interview
    # ---------------------------------------------------------

    interview = interview_repository.get_by_id(interview_id)

    if interview is None:
        raise InterviewNotFoundForGenerationError(
            f"Interview {interview_id} does not exist."
        )

    # ---------------------------------------------------------
    # 2. Get Application
    # ---------------------------------------------------------

    application = application_repository.get_by_id(
        interview.application_id
    )

    if application is None:
        raise ApplicationNotFoundForInterviewError(
            f"Application {interview.application_id} for interview "
            f"{interview_id} does not exist."
        )

    # ---------------------------------------------------------
    # 3. Get Job Opportunity
    # ---------------------------------------------------------

    job_opportunity = job_opportunity_repository.get_by_id(
        application.job_opportunity_id
    )

    if job_opportunity is None:
        raise JobOpportunityNotFoundForApplicationError(
            f"Job opportunity {application.job_opportunity_id} "
            f"for application {application.id} does not exist."
        )

    # ---------------------------------------------------------
    # 4. Get Screening Criteria
    # ---------------------------------------------------------

    screening_criteria_model = (
        screening_criteria_repository.get_by_job_opportunity_id(
            job_opportunity.id
        )
    )

    if screening_criteria_model is None:
        raise ScreeningCriteriaNotFoundForJobError(
            f"Screening criteria for job opportunity "
            f"{job_opportunity.id} do not exist."
        )

    # ---------------------------------------------------------
    # 5. Reconstruct generation input
    # ---------------------------------------------------------

    job_description = _build_job_description(
        job_opportunity
    )

    screening_criteria = _build_screening_criteria(
        job_opportunity,
        screening_criteria_model,
    )

    generation_input = QuestionGenerationInput(
        job_description=job_description,
        screening_criteria=screening_criteria,
    )

    # ---------------------------------------------------------
    # 6. Generate questions using existing generation pipeline
    # ---------------------------------------------------------

    generated_response = await run_question_generation_pipeline(
        generation_input,
        generation_service,
    )

    # ---------------------------------------------------------
    # 7. Convert generation response to storage schema
    # ---------------------------------------------------------

    storage_input = GeneratedQuestions.model_validate(
        generated_response.model_dump(mode="json")
    )

    # ---------------------------------------------------------
    # 8. Store questions under the interview
    # ---------------------------------------------------------

    return storage_service.store_questions(
        interview_id=interview_id,
        generated_questions=storage_input,
    )