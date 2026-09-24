from pydantic import BaseModel, model_validator

from app.schemas.job_description import JobDescriptionResponse
from app.schemas.screening_criteria import ScreeningCriteria


class QuestionGenerationInput(BaseModel):
    job_description: JobDescriptionResponse
    screening_criteria: ScreeningCriteria

    @model_validator(mode="after")
    def validate_job_id_match(self):
        if self.job_description.job_id != self.screening_criteria.job_id:
            raise ValueError(
                "Job description and screening criteria must belong to the same job"
            )

        return self