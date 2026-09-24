import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status

from app.dependencies.job_description import (
    get_job_description_service,
)
from app.dependencies.job_opportunity import (
    get_job_opportunity_repository,
)
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.schemas.job_description import (
    JobDescriptionRequest,
    JobDescriptionResponse,
    JobOpportunityEditResponse,
    JobOpportunitySummaryResponse,
    JobStatusUpdateRequest,
)
from app.services.job_description_service import JobDescriptionService

from app.dependencies.interview_context import (
    get_application_repository,
)
from app.dependencies.screening_criteria import (
    get_screening_criteria_handler,
    get_screening_criteria_repository,
)
from app.handlers.screening_criteria_handler import (
    ScreeningCriteriaHandler,
)
from app.repositories.application_repository import ApplicationRepository
from app.repositories.screening_criteria_repository import (
    ScreeningCriteriaRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/job-description",
    tags=["Job Description"],
)


@router.post(
    "/process",
    response_model=JobDescriptionResponse,
    summary="Process and store structured job description",
)
async def process_job_description(
    request: JobDescriptionRequest,
    recruiter_id: int,
    service: Annotated[
        JobDescriptionService,
        Depends(get_job_description_service),
    ],
    repository: Annotated[
        JobOpportunityRepository,
        Depends(get_job_opportunity_repository),
    ],
    screening_criteria_handler: Annotated[
        ScreeningCriteriaHandler,
        Depends(get_screening_criteria_handler),
    ],
) -> JobDescriptionResponse:
    processed_job = service.process_job_description(request)

    repository.save(processed_job, recruiter_id)

    screening_criteria_handler.handle_generate_screening_criteria(
        processed_job.model_dump()
    )

    return processed_job

@router.get(
    "",
    response_model=list[JobOpportunitySummaryResponse],
    summary="Get all job opportunities",
)
async def get_job_opportunities(
    repository: Annotated[
        JobOpportunityRepository,
        Depends(get_job_opportunity_repository),
    ],
    application_repository: Annotated[
        ApplicationRepository,
        Depends(get_application_repository),
    ],
    include_archived: bool = True,
) -> list[JobOpportunitySummaryResponse]:
    """
    Every posting, newest first.

    The candidate-facing board passes include_archived=false. The default
    is true so the recruiter's board -- and every existing caller -- keeps
    seeing closed postings, which is what the person who closed one
    expects.
    """

    jobs = repository.get_all(include_archived=include_archived)

    # One grouped query for the whole page rather than a count per card.
    application_counts = application_repository.counts_by_job_opportunity()

    return [
        JobOpportunitySummaryResponse(
            application_count=application_counts.get(job.id, 0),
            job_id=job.job_id,
            title=job.title,
            department=job.department,
            employment_type=job.employment_type,
            location=job.location,
            job_summary=job.job_summary,
            required_skills=job.required_skills,
            minimum_years=job.minimum_years,
            experience_level=job.experience_level,
            status=job.status,
        )
        for job in jobs
    ]


@router.get(
    "/{job_id}",
    response_model=JobOpportunityEditResponse,
    summary="Get a job opportunity for editing",
)
async def get_job_description_for_edit(
    job_id: Annotated[str, Path(min_length=1)],
    repository: Annotated[
        JobOpportunityRepository,
        Depends(get_job_opportunity_repository),
    ],
) -> JobOpportunityEditResponse:
    """
    The recruiter's view of a posting, including the screening threshold
    that the candidate-facing endpoint withholds.
    """

    job_opportunity = repository.get_by_job_id(job_id)

    if job_opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job opportunity '{job_id}' does not exist.",
        )

    return JobOpportunityEditResponse.model_validate(job_opportunity)


@router.put(
    "/{job_id}",
    response_model=JobDescriptionResponse,
    summary="Update an existing job opportunity",
)
async def update_job_description(
    job_id: Annotated[str, Path(min_length=1)],
    request: JobDescriptionRequest,
    service: Annotated[
        JobDescriptionService,
        Depends(get_job_description_service),
    ],
    repository: Annotated[
        JobOpportunityRepository,
        Depends(get_job_opportunity_repository),
    ],
    screening_criteria_repository: Annotated[
        ScreeningCriteriaRepository,
        Depends(get_screening_criteria_repository),
    ],
    screening_criteria_handler: Annotated[
        ScreeningCriteriaHandler,
        Depends(get_screening_criteria_handler),
    ],
) -> JobDescriptionResponse:
    """
    Replace what a posting says, keeping which posting it is.

    The screening criteria are regenerated from the edited description.
    They are derived from the skills and weights in the job, so leaving the
    old ones in place after an edit would quietly screen every future
    candidate against requirements the posting no longer states -- a wrong
    answer that nothing on screen would reveal.
    """

    existing = repository.get_by_job_id(job_id)

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job opportunity '{job_id}' does not exist.",
        )

    processed_job = service.process_job_description(request)

    # process_job_description mints a fresh job_id. An edit must keep the
    # existing one: applications, screening criteria and any link a
    # candidate already holds are all addressed by it.
    processed_job = processed_job.model_copy(
        update={"job_id": existing.job_id}
    )

    repository.update(existing, processed_job)

    # The criteria row is unique per job, so the old one goes before the
    # new one is generated.
    screening_criteria_repository.delete_for_job_opportunity(existing.id)

    try:
        screening_criteria_handler.handle_generate_screening_criteria(
            processed_job.model_dump()
        )
    except Exception:
        # The edit itself is saved and correct. Regeneration reaches the
        # model, so it can fail on its own; that leaves the posting without
        # criteria until it is edited again, which is visible and fixable,
        # whereas failing the whole request would roll the recruiter's edit
        # back for a reason that has nothing to do with what they typed.
        logger.exception(
            "Saved the edit to job %s but could not regenerate its "
            "screening criteria.",
            existing.job_id,
        )

    return processed_job


@router.patch(
    "/{job_id}/status",
    response_model=JobOpportunityEditResponse,
    summary="Close a job posting, or reopen it",
)
async def update_job_status(
    job_id: Annotated[str, Path(min_length=1)],
    request: JobStatusUpdateRequest,
    repository: Annotated[
        JobOpportunityRepository,
        Depends(get_job_opportunity_repository),
    ],
) -> JobOpportunityEditResponse:
    """
    Close a posting without destroying anything attached to it.

    Archiving is what a finished job needs and deleting cannot give it:
    applications, resumes, screening results, interviews and recorded
    answers all stay, while the posting stops accepting new applications
    and leaves the candidate board. A posting that candidates have already
    worked on cannot be deleted for exactly that reason, so this is the
    path that ends it.
    """

    job_opportunity = repository.get_by_job_id(job_id)

    if job_opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job opportunity '{job_id}' does not exist.",
        )

    repository.set_status(job_opportunity, request.status)

    return JobOpportunityEditResponse.model_validate(job_opportunity)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job opportunity",
)
async def delete_job_description(
    job_id: Annotated[str, Path(min_length=1)],
    repository: Annotated[
        JobOpportunityRepository,
        Depends(get_job_opportunity_repository),
    ],
    application_repository: Annotated[
        ApplicationRepository,
        Depends(get_application_repository),
    ],
    screening_criteria_repository: Annotated[
        ScreeningCriteriaRepository,
        Depends(get_screening_criteria_repository),
    ],
) -> Response:
    """
    Remove a posting that nobody has applied to.

    An application is the root of a candidate's resume, screening result,
    interview and recorded answers. Deleting a posting that has any would
    either take all of that with it or fail on a foreign key halfway
    through, so this refuses instead and says how many applications are in
    the way. Removing a posting put up by mistake stays a single click;
    discarding candidates' work does not.
    """

    job_opportunity = repository.get_by_job_id(job_id)

    if job_opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job opportunity '{job_id}' does not exist.",
        )

    application_count = application_repository.count_for_job_opportunity(
        job_opportunity.id
    )

    if application_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This job has {application_count} application"
                f"{'' if application_count == 1 else 's'} and cannot be "
                "deleted. Deleting it would remove those candidates' "
                "resumes, screening results and interviews as well."
            ),
        )

    # Criteria belong to the posting and nothing else refers to them, so
    # they go with it rather than being left pointing at a missing row.
    screening_criteria_repository.delete_for_job_opportunity(
        job_opportunity.id
    )

    repository.delete(job_opportunity)

    return Response(status_code=status.HTTP_204_NO_CONTENT)

