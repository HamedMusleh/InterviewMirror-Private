from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.interview_answer import InterviewAnswer
from app.database.models.interview_question import InterviewQuestion


class InterviewAnswerRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        question_id: int,
        answer_text: str | None = None,
        audio_url: str | None = None,
        video_url: str | None = None,
        transcript: str | None = None,
    ) -> InterviewAnswer:
        answer = InterviewAnswer(
            question_id=question_id,
            answer_text=answer_text,
            audio_url=audio_url,
            video_url=video_url,
            transcript=transcript,
        )

        self.db.add(answer)
        self.db.flush()
        self.db.refresh(answer)

        return answer

    def create_audio_answer(
        self,
        question_id: int,
        audio_url: str,
        transcript: str | None = None,
    ) -> InterviewAnswer:
        answer = self.create(
            question_id=question_id,
            audio_url=audio_url,
            transcript=transcript,
        )

        self.db.commit()

        return answer

    def get_by_interview_id(
        self,
        interview_id: int,
    ) -> Sequence[InterviewAnswer]:
        statement = (
            select(InterviewAnswer)
            .join(
                InterviewQuestion,
                InterviewAnswer.question_id == InterviewQuestion.id,
            )
            .where(
                InterviewQuestion.interview_id == interview_id
            )
        )

        return self.db.scalars(statement).all()

    def get_answered_question_ids(
        self,
        interview_id: int,
    ) -> list[int]:
        statement = (
            select(InterviewAnswer.question_id)
            .join(
                InterviewQuestion,
                InterviewAnswer.question_id == InterviewQuestion.id,
            )
            .where(
                InterviewQuestion.interview_id == interview_id
            )
            .distinct()
        )

        return list(self.db.scalars(statement).all())