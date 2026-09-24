from sqlalchemy.orm import Session

from app.database.models.interview_answer import InterviewAnswer
from app.repositories.interview_answer_repository import (
    InterviewAnswerRepository,
)


class InterviewAnswerService:
    def __init__(self, db: Session):
        self.repository = InterviewAnswerRepository(db)

    def create_audio_answer(
        self,
        question_id: int,
        audio_url: str,
        transcript: str | None = None,
    ) -> InterviewAnswer:
        return self.repository.create_audio_answer(
            question_id=question_id,
            audio_url=audio_url,
            transcript=transcript,
        )
