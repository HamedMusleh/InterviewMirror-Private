from typing import Protocol, runtime_checkable

from app.schemas.adaptive_follow_up import (
    FollowUpQuestionRequest,
    FollowUpQuestionResponse,
)


@runtime_checkable
class IAdaptiveFollowUpService(Protocol):
    """Structural contract for the adaptive follow-up question generator."""

    def generate_follow_up_question(
        self,
        request: FollowUpQuestionRequest,
    ) -> FollowUpQuestionResponse | None:
        ...