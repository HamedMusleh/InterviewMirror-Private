from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.adaptive_follow_up import (
    get_adaptive_follow_up_service,
)
from app.dependencies.interfaces.adaptive_follow_up_interface import (
    IAdaptiveFollowUpService,
)
from app.schemas.adaptive_follow_up import (
    FollowUpQuestionRequest,
    FollowUpQuestionResponse,
)


router = APIRouter(
    prefix="/api/interviews",
    tags=["Adaptive Follow-Up"],
)


@router.post(
    "/follow-up",
    response_model=FollowUpQuestionResponse | None,
)
def generate_follow_up_question(
    request: FollowUpQuestionRequest,
    service: Annotated[
        IAdaptiveFollowUpService,
        Depends(get_adaptive_follow_up_service),
    ],
) -> FollowUpQuestionResponse | None:
    return service.generate_follow_up_question(request)