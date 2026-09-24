from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.dependencies.candidate import get_candidate_service
from app.schemas.candidate import CandidateInfoResponse
from app.services.candidate_service import (
    CandidateNotFoundError,
    CandidateService,
)

router = APIRouter(
    prefix="/api/candidates",
    tags=["Candidates"],
)


@router.get(
    "/{candidate_id}",
    response_model=CandidateInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve read-only candidate identity for the application page",
)
def get_candidate(
    candidate_id: Annotated[int, Path(gt=0)],
    service: Annotated[CandidateService, Depends(get_candidate_service)],
) -> CandidateInfoResponse:
    try:
        return service.get_candidate_info(candidate_id)

    except CandidateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
