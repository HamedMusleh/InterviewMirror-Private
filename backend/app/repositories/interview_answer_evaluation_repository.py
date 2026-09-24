from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.interview_answer_evaluation import (
    InterviewAnswerEvaluation,
)


class InterviewAnswerEvaluationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_answer_ids(
        self,
        answer_ids: Iterable[int],
    ) -> Sequence[InterviewAnswerEvaluation]:
        answer_ids = list(answer_ids)

        if not answer_ids:
            return []

        statement = select(InterviewAnswerEvaluation).where(
            InterviewAnswerEvaluation.answer_id.in_(answer_ids)
        )

        return self.db.scalars(statement).all()