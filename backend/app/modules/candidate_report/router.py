from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.handlers.candidate_report_handler import (
    CandidateEvaluationNotFoundError,
    CandidateNotFoundError,
    CandidateReportAlreadyExistsError,
    CandidateReportHandler,
    CandidateReportNotFoundError,
    CandidateReportRelationshipError,
    InterviewNotFoundError,
)
from app.schemas.candidate_report import (
    CandidateReport,
    CandidateReportResponse,
    CandidateReportSummary,
)
from app.dependencies.candidate_report import (
    get_candidate_report_service,
)
from app.dependencies.candidate_report_storage import (
    get_candidate_evaluation_repository,
    get_candidate_report_handler,
)
from app.dependencies.interfaces.candidate_report_service_interface import (
    ICandidateReportService,
)
from app.modules.candidate_report.orchestration import (
    generate_and_store_candidate_report,
)
from app.repositories.candidate_evaluation_repository import (
    CandidateEvaluationRepository,
)
from app.services.candidate_report_service import CandidateReportError


router = APIRouter(
    prefix="/api/interviews",
    tags=["Candidate Report"],
)

reports_list_router = APIRouter(
    prefix="/api/reports",
    tags=["Candidate Report"],
)


@router.post(
    "/{interview_id}/report",
    response_model=CandidateReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store Lara's generated Candidate Report for an interview",
)
def store_candidate_report(
    interview_id: Annotated[int, Path(gt=0)],
    report: CandidateReport,
    handler: Annotated[
        CandidateReportHandler,
        Depends(get_candidate_report_handler),
    ],
) -> CandidateReportResponse:
    try:
        return handler.store_report(interview_id, report)
    except (
        InterviewNotFoundError,
        CandidateNotFoundError,
        CandidateEvaluationNotFoundError,
    ) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        CandidateReportRelationshipError,
        CandidateReportAlreadyExistsError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.post(
    "/{interview_id}/report/generate",
    response_model=CandidateReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and store Candidate Report for an interview",
)
async def generate_candidate_report(
    interview_id: Annotated[int, Path(gt=0)],
    candidate_evaluation_repository: Annotated[
        CandidateEvaluationRepository,
        Depends(get_candidate_evaluation_repository),
    ],
    report_service: Annotated[
        ICandidateReportService,
        Depends(get_candidate_report_service),
    ],
    handler: Annotated[
        CandidateReportHandler,
        Depends(get_candidate_report_handler),
    ],
) -> CandidateReportResponse:

    evaluation = candidate_evaluation_repository.get_by_interview_id(
        interview_id
    )

    if evaluation is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No candidate evaluation exists yet for interview "
                f"{interview_id}."
            ),
        )

    try:
        return await generate_and_store_candidate_report(
            evaluation=evaluation,
            report_service=report_service,
            report_handler=handler,
        )

    except CandidateReportAlreadyExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except (
        InterviewNotFoundError,
        CandidateNotFoundError,
        CandidateEvaluationNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except CandidateReportRelationshipError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except CandidateReportError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@router.get(
    "/{interview_id}/report",
    response_model=CandidateReportResponse,
    summary="Retrieve the complete Candidate Report for an interview",
)
def get_candidate_report(
    interview_id: Annotated[int, Path(gt=0)],
    handler: Annotated[
        CandidateReportHandler,
        Depends(get_candidate_report_handler),
    ],
) -> CandidateReportResponse:
    try:
        return handler.get_report(interview_id)
    except (
        InterviewNotFoundError,
        CandidateNotFoundError,
        CandidateEvaluationNotFoundError,
        CandidateReportNotFoundError,
    ) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@reports_list_router.get(
    "",
    response_model=list[CandidateReportSummary],
    summary="List all candidate reports",
)
def list_candidate_reports(
    handler: Annotated[
        CandidateReportHandler,
        Depends(get_candidate_report_handler),
    ],
) -> list[CandidateReportSummary]:
    return handler.list_reports()