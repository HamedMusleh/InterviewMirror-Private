import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.candidate_report import (
    get_candidate_report_service,
)
from app.dependencies.candidate_report_storage import (
    get_candidate_report_handler,
)
from app.dependencies.db import get_db
from app.dependencies.evaluation import (
    get_evaluation_scoring_service,
    get_evaluation_service,
)
from app.dependencies.interfaces.candidate_report_service_interface import (
    ICandidateReportService,
)
from app.handlers.candidate_report_handler import CandidateReportHandler
from app.modules.candidate_report.orchestration import (
    generate_and_store_candidate_report,
)
from app.modules.evaluation.pipeline import run_evaluation_pipeline
from app.schemas.evaluation import (
    CandidateEvaluationCreate,
    CandidateEvaluationResponse,
    EvaluationInput,
    FinalEvaluationResult,
    InterviewAnswerEvaluationCreate,
    InterviewAnswerEvaluationResponse,
    InterviewEvaluationsResponse,
    OverallEvaluationResponse,
)
from app.services.candidate_evaluation_service import (
    CandidateEvaluationService,
)
from app.services.evaluation_scoring_service import (
    EvaluationScoringService,
)
from app.services.evaluation_service import EvaluationService


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/evaluation",
    tags=["evaluation"],
)


@router.post(
    "/evaluate",
    response_model=FinalEvaluationResult,
)
async def evaluate_answer(
    context: EvaluationInput,
    evaluation_service: EvaluationService = Depends(
        get_evaluation_service
    ),
    scoring_service: EvaluationScoringService = Depends(
        get_evaluation_scoring_service
    ),
) -> FinalEvaluationResult:
    return await run_evaluation_pipeline(
        context=context,
        evaluation_service=evaluation_service,
        scoring_service=scoring_service,
    )


@router.post(
    "/answer-evaluations",
    response_model=InterviewAnswerEvaluationResponse,
    status_code=201,
)
def create_answer_evaluation(
    data: InterviewAnswerEvaluationCreate,
    db: Session = Depends(get_db),
) -> InterviewAnswerEvaluationResponse:

    service = CandidateEvaluationService(db)

    try:
        evaluation = service.create_answer_evaluation(data)

        db.commit()
        db.refresh(evaluation)

    except Exception:
        db.rollback()
        raise

    return InterviewAnswerEvaluationResponse(
        answer_id=evaluation.answer_id,
        skill=None,
        relevance_score=evaluation.relevance_score,
        correctness_score=evaluation.correctness_score,
        depth_score=evaluation.depth_score,
        practicality_score=evaluation.practicality_score,
        strengths=evaluation.strengths,
        weaknesses=evaluation.weaknesses,
        score=evaluation.score,
    )


@router.post(
    "/candidate-evaluations",
    response_model=CandidateEvaluationResponse,
    status_code=201,
)
async def create_candidate_evaluation(
    data: CandidateEvaluationCreate,
    db: Session = Depends(get_db),
    report_service: ICandidateReportService = Depends(
        get_candidate_report_service
    ),
    report_handler: CandidateReportHandler = Depends(
        get_candidate_report_handler
    ),
) -> CandidateEvaluationResponse:

    service = CandidateEvaluationService(db)

    try:
        evaluation = service.create_candidate_evaluation(data)

        db.commit()
        db.refresh(evaluation)

    except Exception:
        db.rollback()
        raise

    try:
        await generate_and_store_candidate_report(
            evaluation=evaluation,
            report_service=report_service,
            report_handler=report_handler,
            strengths=data.strengths,
            weaknesses=data.weaknesses,
        )

    except Exception:
        logger.exception(
            "Automatic candidate report generation failed for "
            "candidate_evaluation_id=%s (interview_id=%s). The evaluation "
            "was still saved successfully; the report can be generated "
            "later via POST /api/interviews/{interview_id}/report/generate.",
            evaluation.id,
            evaluation.interview_id,
        )

    return CandidateEvaluationResponse(
        id=evaluation.id,
        interview_id=evaluation.interview_id,
        overall_score=evaluation.overall_score,
        skill_scores=evaluation.skill_scores,
        strengths=data.strengths,
        weaknesses=data.weaknesses,
    )


@router.get(
    "/interviews/{interview_id}/candidates/{candidate_id}",
    response_model=InterviewEvaluationsResponse,
)
def get_candidate_interview_evaluations(
    interview_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
) -> InterviewEvaluationsResponse:

    service = CandidateEvaluationService(db)

    return service.get_candidate_interview_evaluations(
        interview_id=interview_id,
        candidate_id=candidate_id,
    )


@router.get(
    "/interviews/{interview_id}/candidates/{candidate_id}/overall-evaluation",
    response_model=OverallEvaluationResponse,
)
def get_overall_candidate_evaluation(
    interview_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
) -> OverallEvaluationResponse:

    service = CandidateEvaluationService(db)

    return service.get_overall_candidate_evaluation(
        interview_id=interview_id,
        candidate_id=candidate_id,
    )