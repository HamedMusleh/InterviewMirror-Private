from app.database.models.screening_result import ScreeningResult
from app.schemas.screening_score import ScreeningScoreResponse


class ScreeningResultHandler:
    def to_db_model(self, result: ScreeningScoreResponse) -> ScreeningResult:
        return ScreeningResult(
            application_id=result.application_id,
            criteria_id=result.criteria_id,
            category_breakdown={
                name: breakdown.model_dump()
                for name, breakdown in result.category_breakdown.items()
            },
            matched_criteria=result.matched_criteria,
            missing_criteria=result.missing_criteria,
            matching_details=result.matching_details,
            overall_score=result.overall_score,
            passing_score=result.passing_score,
            confidence_score=None,
            final_status=result.final_status,
        )