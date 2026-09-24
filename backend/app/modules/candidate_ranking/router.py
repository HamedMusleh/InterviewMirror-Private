import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.dependencies.candidate_ranking import get_candidate_ranking_service
from app.dependencies.db import get_db
from app.schemas.candidate_ranking import (
    CandidateRankingListResponse,
    CandidateRankingRequest,
)
from app.services.candidate_ranking_service import (
    CandidateRankingService,
    InvalidRankingEntryError,
    JobOpportunityNotFoundError,
)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/candidate-rankings",
    tags=["Candidate Rankings"],
)


@router.get(
    "/{job_opportunity_id}",
    response_model=CandidateRankingListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve the ranked candidate list of a job opportunity",
)
def get_candidate_rankings(
    job_opportunity_id: Annotated[int, Path(gt=0)],
    service: Annotated[
        CandidateRankingService, Depends(get_candidate_ranking_service)
    ],
) -> CandidateRankingListResponse:
    try:
        return service.get_ranked_candidates(job_opportunity_id)

    except JobOpportunityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Failed to retrieve candidate rankings for job opportunity %s",
            job_opportunity_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve the ranked candidate list.",
        ) from exc


@router.post(
    "/{job_opportunity_id}",
    response_model=CandidateRankingListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store the ranked candidate list of a job opportunity",
)
def store_candidate_rankings(
    job_opportunity_id: Annotated[int, Path(gt=0)],
    request: CandidateRankingRequest,
    service: Annotated[
        CandidateRankingService, Depends(get_candidate_ranking_service)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> CandidateRankingListResponse:
    try:
        response = service.replace_rankings(
            job_opportunity_id=job_opportunity_id,
            request=request,
        )

        db.commit()

        return response

    except JobOpportunityNotFoundError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except InvalidRankingEntryError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Failed to store candidate rankings for job opportunity %s",
            job_opportunity_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store the ranked candidate list.",
        ) from exc
