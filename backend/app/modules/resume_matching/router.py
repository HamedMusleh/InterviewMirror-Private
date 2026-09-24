from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.core.logging import ILogger
from app.dependencies.resume_matching import ResumeMatchingDependencies
from app.modules.resume_matching.pipeline import ResumeMatchingPipeline
from app.repositories.resume_matching_repository import (
    ResumeMatchingDataError,
    ResumeMatchingNotFoundError,
)
from app.schemas.resume_matching import (
    DatabaseMatchingResponse,
    MatchingRequest,
    MatchingResponse,
)
from app.services.llm_client import (
    LLMConfigurationError,
    LLMRequestError,
    LLMResponseError,
)


router = APIRouter(
    prefix="/api/resume-matching",
    tags=["Resume Matching"],
)


@router.post("", response_model=MatchingResponse)
async def match_resume(
    request: MatchingRequest,
    pipeline: Annotated[
        ResumeMatchingPipeline,
        Depends(ResumeMatchingDependencies.get_resume_matching_pipeline),
    ],
    logger: Annotated[
        ILogger,
        Depends(ResumeMatchingDependencies.get_resume_matching_logger),
    ],
) -> MatchingResponse:
    try:
        return await pipeline.match(request)
    except LLMConfigurationError as exc:
        logger.error("Resume matching Azure OpenAI configuration error")
        raise HTTPException(
            status_code=503,
            detail="Resume matching AI service is not configured.",
        ) from exc
    except (LLMRequestError, LLMResponseError) as exc:
        logger.error("Resume matching Azure OpenAI request failed")
        raise HTTPException(
            status_code=502,
            detail="Resume matching AI service is temporarily unavailable.",
        ) from exc


@router.post(
    "/applications/{application_id}",
    response_model=DatabaseMatchingResponse,
    summary="Match a stored application resume against its job criteria",
)
async def match_stored_resume(
    application_id: Annotated[int, Path(gt=0)],
    pipeline: Annotated[
        ResumeMatchingPipeline,
        Depends(
            ResumeMatchingDependencies.get_database_resume_matching_pipeline
        ),
    ],
    logger: Annotated[
        ILogger,
        Depends(ResumeMatchingDependencies.get_resume_matching_logger),
    ],
) -> DatabaseMatchingResponse:
    try:
        return await pipeline.match_application(application_id)
    except ResumeMatchingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ResumeMatchingDataError as exc:
        logger.error("Stored resume matching data is invalid")
        raise HTTPException(
            status_code=500,
            detail="Stored resume matching data is invalid.",
        ) from exc
    except LLMConfigurationError as exc:
        logger.error("Resume matching Azure OpenAI configuration error")
        raise HTTPException(
            status_code=503,
            detail="Resume matching AI service is not configured.",
        ) from exc
    except (LLMRequestError, LLMResponseError) as exc:
        logger.error("Resume matching Azure OpenAI request failed")
        raise HTTPException(
            status_code=502,
            detail="Resume matching AI service is temporarily unavailable.",
        ) from exc
