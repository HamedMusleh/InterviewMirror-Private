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
from app.schemas.interview_details import (
    InterviewDetailsResponse,
    InterviewQuestionDetail,
)


class InterviewDetailsHandlerError(Exception):
    """Base error for interview details retrieval failures."""


class InterviewNotFoundError(InterviewDetailsHandlerError):
    """Raised when interview_id does not refer to an existing Interview."""


class InterviewDetailsHandler:
    """
    Assembles the "See Details" view for a single interview: every
    question, its answer (if any), and its per-question evaluation
    breakdown (if evaluated yet).

    Does not generate or evaluate anything itself - purely reads and
    joins data already produced by question generation, answer
    recording, and per-answer evaluation.
    """

    def __init__(
        self,
        interview_repository: InterviewRepository,
        interview_question_repository: InterviewQuestionRepository,
        interview_answer_repository: InterviewAnswerRepository,
        interview_answer_evaluation_repository: (
            InterviewAnswerEvaluationRepository
        ),
    ) -> None:
        self.interview_repository = interview_repository
        self.interview_question_repository = interview_question_repository
        self.interview_answer_repository = interview_answer_repository
        self.interview_answer_evaluation_repository = (
            interview_answer_evaluation_repository
        )

    def get_details(self, interview_id: int) -> InterviewDetailsResponse:
        interview = self.interview_repository.get_by_id(interview_id)
        if interview is None:
            raise InterviewNotFoundError(
                f"Interview {interview_id} was not found."
            )

        questions = self.interview_question_repository.get_by_interview_id(
            interview_id
        )
        answers = self.interview_answer_repository.get_by_interview_id(
            interview_id
        )

        answer_by_question_id = {
            answer.question_id: answer for answer in answers
        }

        evaluations = (
            self.interview_answer_evaluation_repository.get_by_answer_ids(
                answer.id for answer in answers
            )
        )
        evaluation_by_answer_id = {
            evaluation.answer_id: evaluation for evaluation in evaluations
        }

        details: list[InterviewQuestionDetail] = []

        for question in questions:
            answer = answer_by_question_id.get(question.id)
            evaluation = (
                evaluation_by_answer_id.get(answer.id)
                if answer is not None
                else None
            )

            answer_text = None
            if answer is not None:
                answer_text = answer.answer_text or answer.transcript

            details.append(
                InterviewQuestionDetail(
                    question_id=question.id,
                    question=question.question_text,
                    skill=question.skill,
                    is_follow_up=question.is_follow_up,
                    parent_question_id=question.parent_question_id,
                    answer=answer_text,
                    score=evaluation.score if evaluation else None,
                    relevance_score=(
                        evaluation.relevance_score if evaluation else None
                    ),
                    correctness_score=(
                        evaluation.correctness_score
                        if evaluation
                        else None
                    ),
                    depth_score=(
                        evaluation.depth_score if evaluation else None
                    ),
                    practicality_score=(
                        evaluation.practicality_score
                        if evaluation
                        else None
                    ),
                    strengths=(
                        list(evaluation.strengths) if evaluation else []
                    ),
                    weaknesses=(
                        list(evaluation.weaknesses) if evaluation else []
                    ),
                )
            )

        return InterviewDetailsResponse(
            interview_id=interview_id,
            questions=details,
        )