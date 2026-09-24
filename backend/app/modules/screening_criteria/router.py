from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.core.logging import ILogger, get_logger
from app.dependencies.screening_criteria import get_screening_criteria_handler
from app.handlers.screening_criteria_handler import (
    JobOpportunityNotFoundError,
    ScreeningCriteriaHandler,
)
from app.schemas.screening_criteria import ScreeningCriteria


router = APIRouter(
    prefix="/screening-criteria",
    tags=["Screening Criteria"],
)


@router.post("/generate", response_model=ScreeningCriteria)
async def generate_screening_criteria_endpoint(
    job_description_json: dict,
    handler: Annotated[
        ScreeningCriteriaHandler, Depends(get_screening_criteria_handler)
    ],
    logger: ILogger = Depends(get_logger),
):
    """
    Receives a structured Job Description JSON, generates the
    Screening Criteria JSON, saves it against the matching
    JobOpportunity, and returns the generated Screening Criteria JSON.
    """
    try:
        result = handler.handle_generate_screening_criteria(job_description_json)
        return result

    except ValidationError as e:
        logger.warning(f"Invalid job description payload: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    except JobOpportunityNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to generate screening criteria: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate screening criteria",
        )
