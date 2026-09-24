from typing import Protocol
from app.schemas.screening_score import (
    ScreeningScoreResponse,
    ScreeningResultDetail,
    ScreeningResultSummary,
)


class ScreeningResultRepository(Protocol):
    def save(self, result: ScreeningScoreResponse) -> ScreeningScoreResponse:
        ...

    def list_by_job_id(self, job_id: str) -> list[ScreeningResultSummary]:
        ...

    def get_by_application_id(
        self, application_id: int
    ) -> ScreeningResultDetail | None:
        ...