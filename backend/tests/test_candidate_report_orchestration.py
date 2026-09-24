from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.modules.candidate_report.orchestration import (
    generate_and_store_candidate_report,
)
from app.schemas.candidate_report import (
    CandidateReport,
    CandidateReportResponse,
    GeneratedReportContent,
)


@pytest.mark.asyncio
async def test_generate_and_store_candidate_report():
    evaluation = SimpleNamespace(
        id=1,
        interview_id=4,
        overall_score=78,
        skill_scores={
            "Python": 85,
            "FastAPI": 75,
        },
        strengths=[
            "Strong Python knowledge",
        ],
        weaknesses=[
            "Limited FastAPI depth",
        ],
    )

    report_service = Mock()
    report_service.generate_report = AsyncMock(
        return_value=GeneratedReportContent(
            summary="Good backend candidate.",
            strengths=[
                "Strong Python knowledge",
            ],
            areas_for_improvement=[
                "Improve FastAPI depth",
            ],
            recommendation="Proceed to the next stage.",
        )
    )

    expected_response = CandidateReportResponse(
        report_id=7,
        candidate_evaluation_id=1,
        candidate_id=12,
        interview_id=4,
        candidate_name="Ahmad Khalil",
        job_title="Backend Developer",
        overall_score=78,
        skill_scores={
            "Python": 85,
            "FastAPI": 75,
        },
        summary="Good backend candidate.",
        strengths=[
            "Strong Python knowledge",
        ],
        areas_for_improvement=[
            "Improve FastAPI depth",
        ],
        recommendation="Proceed to the next stage.",
    )

    handler = Mock()
    handler.store_report.return_value = expected_response

    result = await generate_and_store_candidate_report(
        evaluation=evaluation,
        report_service=report_service,
        report_handler=handler,
    )

    assert result == expected_response

    handler.store_report.assert_called_once()

    stored_report = handler.store_report.call_args.kwargs["report"]

    assert isinstance(stored_report, CandidateReport)
    assert stored_report.candidate_evaluation_id == 1
    assert stored_report.interview_id == 4
    assert stored_report.overall_score == 78