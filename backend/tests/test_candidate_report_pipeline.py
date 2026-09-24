import pytest

from app.modules.candidate_report.pipeline import (
    run_candidate_report_pipeline,
)
from app.schemas.candidate_report import (
    CandidateReportInput,
    GeneratedReportContent,
)


class FakeCandidateReportService:
    async def generate_report(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> GeneratedReportContent:
        return GeneratedReportContent(
            summary=(
                "The candidate demonstrated strong Python knowledge "
                "and relevant backend experience."
            ),
            strengths=[
                "Strong Python knowledge",
                "Relevant backend experience",
            ],
            areas_for_improvement=[
                "Needs greater technical depth in FastAPI",
            ],
            recommendation=(
                "The candidate demonstrates good potential for the role."
            ),
        )


@pytest.mark.anyio
async def test_candidate_report_pipeline_builds_final_report():
    evaluation = CandidateReportInput(
        id=1,
        interview_id=4,
        overall_score=78,
        skill_scores={
            "FastAPI": 75,
            "Python": 85,
        },
        strengths=[
            "Strong Python knowledge",
            "Relevant backend experience",
        ],
        weaknesses=[
            "Limited technical depth in FastAPI",
        ],
    )

    service = FakeCandidateReportService()

    report = await run_candidate_report_pipeline(
        evaluation,
        service,
    )

    assert report.candidate_evaluation_id == 1
    assert report.interview_id == 4

    # Evaluation scores must remain unchanged.
    assert report.overall_score == 78
    assert report.skill_scores == {
        "FastAPI": 75,
        "Python": 85,
    }

    assert report.summary == (
        "The candidate demonstrated strong Python knowledge "
        "and relevant backend experience."
    )
    assert report.strengths == [
        "Strong Python knowledge",
        "Relevant backend experience",
    ]
    assert report.areas_for_improvement == [
        "Needs greater technical depth in FastAPI",
    ]
    assert report.recommendation == (
        "The candidate demonstrates good potential for the role."
    )