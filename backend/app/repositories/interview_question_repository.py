from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models.interview import Interview
from app.database.models.interview_question import InterviewQuestion


class InterviewQuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        question: InterviewQuestion,
    ) -> InterviewQuestion:
        self.db.add(question)
        self.db.flush()
        self.db.refresh(question)

        return question

    def create_many(
        self,
        questions: list[InterviewQuestion],
    ) -> list[InterviewQuestion]:
        self.db.add_all(questions)
        self.db.flush()

        for question in questions:
            self.db.refresh(question)

        return questions

    def get_by_id(
        self,
        question_id: int,
    ) -> InterviewQuestion | None:
        statement = select(InterviewQuestion).where(
            InterviewQuestion.id == question_id
        )

        return self.db.scalar(statement)

    def get_by_interview_id(
        self,
        interview_id: int,
    ) -> Sequence[InterviewQuestion]:
        statement = (
            select(InterviewQuestion)
            .where(
                InterviewQuestion.interview_id == interview_id
            )
            .order_by(
                InterviewQuestion.sequence_number
            )
        )

        return self.db.scalars(statement).all()

    def lock_interview(
        self,
        interview_id: int,
    ) -> bool:
        statement = (
            select(Interview.id)
            .where(Interview.id == interview_id)
            .with_for_update()
        )

        return self.db.scalar(statement) is not None

    def get_max_sequence_number(
        self,
        interview_id: int,
    ) -> int:
        statement = select(
            func.coalesce(
                func.max(InterviewQuestion.sequence_number),
                0,
            )
        ).where(
            InterviewQuestion.interview_id == interview_id
        )

        return self.db.scalar(statement) or 0

    def has_initial_questions(
        self,
        interview_id: int,
    ) -> bool:
        """Whether an initial (non-follow-up) question set already exists."""
        statement = (
            select(InterviewQuestion.id)
            .where(
                InterviewQuestion.interview_id == interview_id,
                InterviewQuestion.is_follow_up.is_(False),
            )
            .limit(1)
        )

        return self.db.scalar(statement) is not None
