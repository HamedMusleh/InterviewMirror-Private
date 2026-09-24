from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.models.interview_question import InterviewQuestion
from app.repositories.interview_question_repository import (
    InterviewQuestionRepository,
)
from app.schemas.adaptive_follow_up import FollowUpQuestionResponse
from app.schemas.interview_question_storage import GeneratedQuestions


class InterviewQuestionServiceError(Exception):
    """Base class for storage-layer failures raised by InterviewQuestionService."""


class InterviewNotFoundError(InterviewQuestionServiceError):
    """Raised when interview_id does not refer to an existing Interview.
    """


class DuplicateInitialQuestionsError(InterviewQuestionServiceError):
    """Raised when an initial (non-follow-up) question set already exists.

    Guards against creating a second initial question set for the same
    interview, e.g. if the generation endpoint is retried. Follow-up
    questions (is_follow_up=True) are a separate workflow and are not
    affected by this check.
    """


class InterviewQuestionService:
    def __init__(self, db: Session):
        self.repository = InterviewQuestionRepository(db)

    def store_questions(
        self,
        interview_id: int,
        generated_questions: GeneratedQuestions,
    ) -> list[InterviewQuestion]:
        interview_exists = self.repository.lock_interview(interview_id)

        if not interview_exists:
            raise InterviewNotFoundError(
                f"Interview {interview_id} does not exist."
            )

        if self.repository.has_initial_questions(interview_id):
            raise DuplicateInitialQuestionsError(
                "Initial questions already exist for interview "
                f"{interview_id}."
            )

        last_sequence_number = (
            self.repository.get_max_sequence_number(
                interview_id
            )
        )

        questions: list[InterviewQuestion] = []

        for sequence_number, generated_question in enumerate(
            generated_questions.questions,
            start=last_sequence_number + 1,
        ):
            question = InterviewQuestion(
                interview_id=interview_id,
                question_text=generated_question.question,
                question_type=generated_question.category.value,
                skill=generated_question.skill,
                sequence_number=sequence_number,
                is_follow_up=False,
                parent_question_id=None,
                created_at=datetime.now(timezone.utc),
            )

            questions.append(question)

        return self.repository.create_many(questions)

    def store_follow_up_question(
        self,
        interview_id: int,
        follow_up: FollowUpQuestionResponse,
    ) -> InterviewQuestion:
        parent_question = self.repository.get_by_id(
            follow_up.parent_question_id
        )

        if parent_question is None:
            raise ValueError(
                f"Interview question {follow_up.parent_question_id} "
                "not found"
            )

        if parent_question.interview_id != interview_id:
            raise ValueError(
                f"Question {follow_up.parent_question_id} does not "
                f"belong to interview {interview_id}"
            )

        self.repository.lock_interview(interview_id)

        next_sequence_number = (
            self.repository.get_max_sequence_number(interview_id) + 1
        )

        question = InterviewQuestion(
            interview_id=interview_id,
            question_text=follow_up.question,
            question_type=follow_up.category,
            skill=follow_up.skill,
            sequence_number=next_sequence_number,
            is_follow_up=True,
            parent_question_id=follow_up.parent_question_id,
            created_at=datetime.now(timezone.utc),
        )

        return self.repository.create(question)