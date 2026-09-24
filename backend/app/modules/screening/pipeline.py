from app.modules.screening.repository import ScreeningResultRepository
from app.schemas.screening_score import (
    ScreeningResultDetail,
    ScreeningResultSummary,
    ScreeningScoreRequest,
    ScreeningScoreResponse,
)
from app.services.screening_score_service import calculate_screening_score


class ScreeningPipeline:
    def __init__(self, repository: ScreeningResultRepository):
        self.repository = repository

    def score_candidate(
        self,
        request: ScreeningScoreRequest,
    ) -> ScreeningScoreResponse:
        result = calculate_screening_score(request)
        self.repository.save(result)

        return result

    def list_results_for_job(self, job_id: str) -> list[ScreeningResultSummary]:
        return self.repository.list_by_job_id(job_id)

    def get_result_detail(
        self, application_id: int
    ) -> ScreeningResultDetail | None:
        return self.repository.get_by_application_id(application_id)