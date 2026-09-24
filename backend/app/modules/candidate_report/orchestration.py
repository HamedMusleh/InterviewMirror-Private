from sqlalchemy import select

from app.database.models.application import Application
from app.database.models.candidate_evaluation import CandidateEvaluation
from app.database.models.interview import Interview
from app.dependencies.interfaces.candidate_report_service_interface import (
    ICandidateReportService,
)
from app.handlers.candidate_report_handler import CandidateReportHandler
from app.modules.candidate_report.pipeline import (
    run_candidate_report_pipeline,
)
from app.schemas.candidate_report import (
    CandidateReportInput,
    CandidateReportResponse,
)
from app.services.candidate_evaluation_service import (
    CandidateEvaluationService,
)


async def generate_and_store_candidate_report(
    evaluation: CandidateEvaluation,
    report_service: ICandidateReportService,
    report_handler: CandidateReportHandler,
) -> CandidateReportResponse:
    """
    Generate and store the candidate report from a persisted
    candidate-level evaluation.

    Overall score and skill scores come from the persisted
    CandidateEvaluation.

    Strengths and weaknesses are aggregated from the answer-level
    evaluations using CandidateEvaluationService.
    """

    if evaluation.overall_score is None:
        raise ValueError(
            "Overall candidate evaluation is missing for "
            f"interview {evaluation.interview_id}."
        )

    db = report_handler.candidate_evaluation_repository.db

    candidate_id = db.scalar(
        select(Application.candidate_id)
        .join(
            Interview,
            Interview.application_id == Application.id,
        )
        .where(
            Interview.id == evaluation.interview_id,
        )
    )

    if candidate_id is None:
        raise ValueError(
            "Candidate could not be resolved for interview "
            f"{evaluation.interview_id}."
        )

    evaluation_service = CandidateEvaluationService(db)

    overall_evaluation = (
        evaluation_service.get_overall_candidate_evaluation(
            interview_id=evaluation.interview_id,
            candidate_id=candidate_id,
        )
    )

    report_input = CandidateReportInput(
        id=evaluation.id,
        interview_id=evaluation.interview_id,
        overall_score=evaluation.overall_score,
        skill_scores=evaluation.skill_scores,
        strengths=overall_evaluation.strengths,
        weaknesses=overall_evaluation.weaknesses,
    )

    generated_report = await run_candidate_report_pipeline(
        evaluation=report_input,
        service=report_service,
    )

    return report_handler.store_report(
        interview_id=evaluation.interview_id,
        report=generated_report,
    )