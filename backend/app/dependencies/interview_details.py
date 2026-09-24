from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.handlers.interview_details_handler import InterviewDetailsHandler
from app.repositories.interview_answer_evaluation_repository import (
    InterviewAnswerEvaluationRepository,
)
from app.repositories.interview_answer_repository import (
    InterviewAnswerRepository,
)
from app.repositories.interview_question_repository import (
    InterviewQuestionRepository,
)
from app.repositories.interview_repository import InterviewRepository


def get_interview_details_handler(
    db: Annotated[Session, Depends(get_db)],
) -> InterviewDetailsHandler:
    return InterviewDetailsHandler(
        interview_repository=InterviewRepository(db),
        interview_question_repository=InterviewQuestionRepository(db),
        interview_answer_repository=InterviewAnswerRepository(db),
        interview_answer_evaluation_repository=(
            InterviewAnswerEvaluationRepository(db)
        ),
    )