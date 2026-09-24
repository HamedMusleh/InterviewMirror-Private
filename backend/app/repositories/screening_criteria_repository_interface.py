from typing import Protocol

from app.database.models.screening_criteria import (
    ScreeningCriteria as ScreeningCriteriaModel,
)
from app.schemas.screening_criteria import ScreeningCriteria


class IScreeningCriteriaRepository(Protocol):
    def save(
        self,
        criteria: ScreeningCriteria,
        job_opportunity_id: int,
    ) -> ScreeningCriteriaModel:
        ...