from fastapi import APIRouter, Depends

from app.dependencies.interview_conversation import (
    get_interview_conversation_service,
)
from app.schemas.interview_conversation import (
    ConversationLine,
    ConversationLineRequest,
)
from app.services.interview_conversation_service import (
    InterviewConversationService,
)


router = APIRouter(
    prefix="/api/interview-conversation",
    tags=["Interview Conversation"],
)


@router.post(
    "/line",
    summary="Write what the interviewer says at a conversational moment",
    response_model=ConversationLine,
)
async def compose_line(
    request: ConversationLineRequest,
    service: InterviewConversationService = Depends(
        get_interview_conversation_service
    ),
) -> ConversationLine:
    """
    Never returns an error for a failed generation.

    The service falls back to a scripted line instead, because a candidate
    mid-interview needs to hear something. Only a malformed request is worth
    a non-200 here, and validation has already handled that.
    """

    return await service.compose(request)
