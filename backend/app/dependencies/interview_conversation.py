from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.repositories.application_repository import ApplicationRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.interview_answer_repository import (
    InterviewAnswerRepository,
)
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.repositories.user_repository import UserRepository
from app.services.interview_conversation_service import (
    InterviewConversationService,
)
from app.services.llm_client import AzureOpenAIClient


def build_interview_conversation_service(
    db: Session,
) -> InterviewConversationService:
    """
    Build the service from a plain session, outside FastAPI's injection.

    The answer WebSocket needs this. It writes the bridge into the next
    question at the moment an answer is stored, and it cannot take the
    service as a request dependency without pinning a pooled connection for
    the whole length of an answer. Sharing the factory with the HTTP provider
    below keeps one construction path, so the two callers cannot drift.
    """

    return InterviewConversationService(
        llm_client=AzureOpenAIClient(),
        interview_repository=InterviewRepository(db),
        application_repository=ApplicationRepository(db),
        job_opportunity_repository=JobOpportunityRepository(db),
        candidate_repository=CandidateRepository(db),
        user_repository=UserRepository(db),
        answer_repository=InterviewAnswerRepository(db),
    )


def get_interview_conversation_service(
    db: Annotated[Session, Depends(get_db)],
) -> InterviewConversationService:
    return build_interview_conversation_service(db)
