"""
Filling a newly created interview with its questions.

Creating the interview and generating its questions are two different kinds
of operation. The first is a small, certain database write. The second is an
LLM call that takes seconds and can fail for reasons that have nothing to do
with the candidate being accepted.

So they are committed separately, and the interview is committed first. An
accepted candidate keeps their interview even if question generation fails;
the questions can be produced on a later attempt, and this function is safe
to call again because it does nothing when a question set already exists.
"""

import logging

from sqlalchemy.orm import Session

from app.dependencies.interfaces.question_generation_service_interface import (
    IQuestionGenerationService,
)
from app.modules.interview_questions.pipeline import (
    run_interview_question_generation_pipeline,
)
from app.repositories.interview_question_repository import (
    InterviewQuestionRepository,
)
from app.services.interview_question_service import InterviewQuestionService


logger = logging.getLogger(__name__)


async def ensure_interview_questions(
    interview_id: int,
    db: Session,
    generation_service: IQuestionGenerationService,
) -> int:
    """
    Generate and store the interview's questions if it has none.

    Returns how many questions the interview ended up with, or 0 if
    generation was not possible. Never raises: the caller has already
    committed an interview that is valid without them.
    """

    repository = InterviewQuestionRepository(db)

    if repository.has_initial_questions(interview_id):
        return len(repository.get_by_interview_id(interview_id))

    try:
        questions = await run_interview_question_generation_pipeline(
            interview_id=interview_id,
            db=db,
            generation_service=generation_service,
            storage_service=InterviewQuestionService(db),
        )

        db.commit()

        return len(questions)
    except Exception:
        db.rollback()

        logger.exception(
            "Could not generate questions for interview %s. The interview "
            "exists and questions can be generated for it later.",
            interview_id,
        )

        return 0
