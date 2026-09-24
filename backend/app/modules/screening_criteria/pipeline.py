from openai import AzureOpenAI

from app.core.logging import ILogger
from app.schemas.job_description import JobDescriptionResponse
from app.schemas.screening_criteria import ScreeningCriteria
from app.services.screening_criteria_service import generate_screening_criteria


class ScreeningCriteriaPipeline:
    """
    Full pipeline: takes a raw Job Description JSON, validates it,
    generates the Screening Criteria via the Foundry-hosted model, and returns
    a validated ScreeningCriteria object ready for the
    Resume Matching & Scoring module.
    """

    def __init__(self, logger: ILogger, client: AzureOpenAI) -> None:
        """
        Args:
            logger: ILogger instance injected by the caller (the handler),
                forwarded down to the service.
            client: AzureOpenAI client injected by the caller (the handler),
                forwarded down to the service.
        """
        self.logger = logger
        self.client = client

    def run(self, job_description_json: dict) -> ScreeningCriteria:
        """
        Args:
            job_description_json: Raw dict, typically received from the
                job description parsing stage (Lara).

        Returns:
            ScreeningCriteria: Validated screening criteria object.
        """
        job_description = JobDescriptionResponse(**job_description_json)

        self.logger.info(
            f"Generating screening criteria for role: {job_description.role.title}"
        )

        screening_criteria = generate_screening_criteria(
            job_description,
            self.logger,
            self.client,
        )

        return screening_criteria