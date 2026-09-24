import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies.application import get_application_service
from app.dependencies.application_status import get_application_status_service
from app.dependencies.db import get_db
from app.dependencies.interfaces.question_generation_service_interface import (
    IQuestionGenerationService,
)
from app.dependencies.question_generation import (
    get_question_generation_service,
)
from app.modules.interviews.preparation import ensure_interview_questions
from app.repositories.resume_matching_repository import (
    ResumeMatchingDataError,
    ResumeMatchingNotFoundError,
)
from app.schemas.application import ApplicationSubmitResponse
from app.schemas.application_status import ApplicationStatusResponse
from app.services.application_service import (
    ApplicationService,
    DuplicateApplicationError,
    InvalidApplicantDataError,
    InvalidResumeFileError,
    JobNotReadyForApplicationsError,
    JobOpportunityNotFoundError,
)
from app.services.application_status_service import ApplicationStatusService
from app.services.llm_client import (
    LLMConfigurationError,
    LLMRequestError,
    LLMResponseError,
)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/applications",
    tags=["Applications"],
)


@router.post(
    "",
    response_model=ApplicationSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a candidate application with its resume",
)
async def submit_application(
    job_opportunity_id: Annotated[int, Form(gt=0)],
    # There is no login/registration flow yet: the candidate identity
    # (User + Candidate) is found or created from these fields inside
    # ApplicationService, using email as the temporary identity
    # mechanism. candidate_id is never accepted here.
    first_name: Annotated[str, Form(min_length=1, max_length=100)],
    last_name: Annotated[str, Form(min_length=1, max_length=100)],
    email: Annotated[str, Form(min_length=1, max_length=255)],
    phone: Annotated[str, Form(min_length=1, max_length=30)],
    file: Annotated[UploadFile, File(...)],
    service: Annotated[ApplicationService, Depends(get_application_service)],
    db: Annotated[Session, Depends(get_db)],
    generation_service: Annotated[
        IQuestionGenerationService,
        Depends(get_question_generation_service),
    ],
) -> ApplicationSubmitResponse:
    try:
        contents = await file.read()

        response = await service.submit_application(
            job_opportunity_id=job_opportunity_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            file_name=file.filename or "resume",
            content_type=file.content_type,
            file_bytes=contents,
        )

        db.commit()

        if response.interview_id is not None:
            # Best-effort, same as /api/cv-parser/parse: the
            # interview itself is already committed above, so a
            # failure here must never turn into an error response for
            # what was actually a successful submission -- it's
            # caught and logged here, not left to propagate into the
            # except-Exception block below.
            try:
                await ensure_interview_questions(
                    interview_id=response.interview_id,
                    db=db,
                    generation_service=generation_service,
                )
            except Exception:
                logger.exception(
                    "Failed to generate interview questions for "
                    "interview %s after a successful application "
                    "submission",
                    response.interview_id,
                )

        return response

    except JobOpportunityNotFoundError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except JobNotReadyForApplicationsError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except DuplicateApplicationError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except InvalidResumeFileError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except InvalidApplicantDataError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except ResumeMatchingNotFoundError as exc:
        # Covers a missing application/resume/job as well as a job
        # opportunity with no screening criteria configured yet.
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ResumeMatchingDataError as exc:
        db.rollback()

        logger.exception(
            "Stored resume matching data is invalid for job "
            "opportunity %s",
            job_opportunity_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored resume matching data is invalid.",
        ) from exc

    except LLMConfigurationError as exc:
        db.rollback()

        logger.error("Resume matching Azure OpenAI configuration error")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Resume matching AI service is not configured.",
        ) from exc

    except (LLMRequestError, LLMResponseError) as exc:
        db.rollback()

        logger.error("Resume matching Azure OpenAI request failed")

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resume matching AI service is temporarily unavailable.",
        ) from exc

    except IntegrityError as exc:
        # Two concurrent submissions can both pass the pre-check and
        # race to commit; the unique constraint on
        # (candidate_id, job_opportunity_id) is the real guard.
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied to this job.",
        ) from exc

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Failed to submit application for job opportunity %s",
            job_opportunity_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit the application. Please try again.",
        ) from exc


@router.get(
    "/status",
    response_model=ApplicationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Resolve which section the candidate-facing JobApplicationPage "
        "should show for this job and (optionally) this returning "
        "candidate"
    ),
)
def get_application_status(
    job_id: Annotated[str, Query(min_length=1)],
    service: Annotated[
        ApplicationStatusService, Depends(get_application_status_service)
    ],
    email: Annotated[str | None, Query()] = None,
) -> ApplicationStatusResponse:
    try:
        return service.get_status(job_id=job_id, email=email)

    except JobOpportunityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Failed to resolve application status for job %s", job_id
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load this job's application status.",
        ) from exc
