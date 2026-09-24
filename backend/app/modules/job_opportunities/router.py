from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.dependencies.job_opportunity import (
    get_job_opportunity_repository,
)
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.schemas.job_opportunity import JobOpportunityResponse

router = APIRouter(
    prefix="/api/job-opportunities",
    tags=["Job Opportunities"],
)


@router.get(
    "/{job_id}",
    response_model=JobOpportunityResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a job opportunity for the candidate application page",
)
def get_job_opportunity(
    job_id: Annotated[str, Path(min_length=1)],
    repository: Annotated[
        JobOpportunityRepository, Depends(get_job_opportunity_repository)
    ],
) -> JobOpportunityResponse:
    job_opportunity = repository.get_by_job_id(job_id)

    if job_opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job opportunity '{job_id}' does not exist.",
        )

    return JobOpportunityResponse.model_validate(job_opportunity)
