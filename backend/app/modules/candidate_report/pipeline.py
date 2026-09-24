from app.dependencies.interfaces.candidate_report_service_interface import (
    ICandidateReportService,
)
from app.prompts.candidate_report_prompt import (
    CANDIDATE_REPORT_SYSTEM_PROMPT,
    build_candidate_report_prompt,
)
from app.schemas.candidate_report import (
    CandidateReport,
    CandidateReportInput,
)


async def run_candidate_report_pipeline(
    evaluation: CandidateReportInput,
    service: ICandidateReportService,
) -> CandidateReport:
    """Generate the final candidate report from an evaluation result."""

    user_prompt = build_candidate_report_prompt(evaluation)

    generated_content = await service.generate_report(
        system_prompt=CANDIDATE_REPORT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    return CandidateReport(
        candidate_evaluation_id=evaluation.id,
        interview_id=evaluation.interview_id,
        overall_score=evaluation.overall_score,
        skill_scores=evaluation.skill_scores,
        summary=generated_content.summary,
        strengths=generated_content.strengths,
        areas_for_improvement=generated_content.areas_for_improvement,
        recommendation=generated_content.recommendation,
    )