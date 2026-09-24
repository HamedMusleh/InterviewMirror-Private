from app.core.logging import ILogger
from app.modules.screening_criteria.pipeline import ScreeningCriteriaPipeline
from app.repositories.job_opportunity_repository import JobOpportunityRepository
from app.repositories.screening_criteria_repository_interface import (
    IScreeningCriteriaRepository,
)
from app.schemas.screening_criteria import ScreeningCriteria


class JobOpportunityNotFoundError(Exception):
    """
    Raised when the ScreeningCriteria generated for a job cannot be
    saved because no JobOpportunity exists for that job_id.
    """

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(
            f"JobOpportunity with job_id='{job_id}' was not found; "
            "cannot save screening criteria."
        )


class ScreeningCriteriaHandler:
    """
    Handler for the "generate screening criteria" use case.

    Generates the ScreeningCriteria via the injected pipeline and then
    persists it through the injected repository.
    """

    def __init__(
        self,
        logger: ILogger,
        pipeline: ScreeningCriteriaPipeline,
        screening_criteria_repository: IScreeningCriteriaRepository,
        job_opportunity_repository: JobOpportunityRepository,
    ) -> None:
        self.logger = logger
        self.pipeline = pipeline
        self.screening_criteria_repository = screening_criteria_repository
        self.job_opportunity_repository = job_opportunity_repository

    def handle_generate_screening_criteria(
        self,
        job_description_json: dict,
    ) -> ScreeningCriteria:
        screening_criteria = self.pipeline.run(job_description_json)

        job_opportunity = self.job_opportunity_repository.get_by_job_id(
            screening_criteria.job_id
        )

        if job_opportunity is None:
            self.logger.warning(
                "No JobOpportunity found for job_id="
                f"{screening_criteria.job_id}; skipping save."
            )
            raise JobOpportunityNotFoundError(screening_criteria.job_id)

        self.screening_criteria_repository.save(
            screening_criteria,
            job_opportunity.id,
        )

        return screening_criteria