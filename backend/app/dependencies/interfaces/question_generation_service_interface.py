"""Interface for the question-generation service."""

from typing import Protocol, runtime_checkable

from app.schemas.interview_question import QuestionGenerationResponse


@runtime_checkable
class IQuestionGenerationService(Protocol):
    """Contract for services that generate role-based interview questions."""

    async def generate_questions(
        self,
        prompt: str,
        number_of_questions: int,
    ) -> QuestionGenerationResponse:
        ...
