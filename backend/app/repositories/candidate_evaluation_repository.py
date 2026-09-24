from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.application import Application
from app.database.models.candidate_evaluation import CandidateEvaluation
from app.database.models.interview import Interview
from app.database.models.interview_answer import InterviewAnswer
from app.database.models.interview_answer_evaluation import (
    InterviewAnswerEvaluation,
)
from app.database.models.interview_question import InterviewQuestion


class CandidateEvaluationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_answer_evaluation(
        self,
        answer_id: int,
        relevance_score: int,
        correctness_score: int,
        depth_score: int,
        practicality_score: int,
        score: float,
        strengths: list[str],
        weaknesses: list[str],
    ) -> InterviewAnswerEvaluation:
        """
        Create an evaluation for a single interview answer.

        The repository only flushes here. The surrounding service/endpoint
        owns the transaction and decides when to commit.
        """
        evaluation = InterviewAnswerEvaluation(
            answer_id=answer_id,
            relevance_score=relevance_score,
            correctness_score=correctness_score,
            depth_score=depth_score,
            practicality_score=practicality_score,
            score=score,
            strengths=strengths,
            weaknesses=weaknesses,
        )

        self.db.add(evaluation)
        self.db.flush()
        self.db.refresh(evaluation)

        return evaluation

    def get_interview_evaluations(
        self,
        interview_id: int,
    ) -> list[tuple[InterviewAnswerEvaluation, str | None]]:
        statement = (
            select(
                InterviewAnswerEvaluation,
                InterviewQuestion.skill,
            )
            .join(
                InterviewAnswer,
                InterviewAnswer.id
                == InterviewAnswerEvaluation.answer_id,
            )
            .join(
                InterviewQuestion,
                InterviewQuestion.id
                == InterviewAnswer.question_id,
            )
            .where(
                InterviewQuestion.interview_id == interview_id,
            )
        )

        return list(self.db.execute(statement).all())

    def get_candidate_interview_evaluations(
        self,
        interview_id: int,
        candidate_id: int,
    ) -> list[tuple[InterviewAnswerEvaluation, str | None]]:
        statement = (
            select(
                InterviewAnswerEvaluation,
                InterviewQuestion.skill,
            )
            .join(
                InterviewAnswer,
                InterviewAnswer.id
                == InterviewAnswerEvaluation.answer_id,
            )
            .join(
                InterviewQuestion,
                InterviewQuestion.id
                == InterviewAnswer.question_id,
            )
            .join(
                Interview,
                Interview.id
                == InterviewQuestion.interview_id,
            )
            .join(
                Application,
                Application.id
                == Interview.application_id,
            )
            .where(
                Interview.id == interview_id,
                Application.candidate_id == candidate_id,
            )
        )

        return list(self.db.execute(statement).all())

    def create_candidate_evaluation(
        self,
        interview_id: int,
        overall_score: float,
        skill_scores: dict[str, float],
    ) -> CandidateEvaluation:
        """
        Create the persisted candidate-level evaluation.

        The candidate_evaluations table only stores:
        - interview_id
        - overall_score
        - skill_scores

        Strengths and weaknesses are aggregated from the individual
        answer evaluations when needed and are not persisted here.

        The repository only flushes. The caller owns the transaction.
        """
        evaluation = CandidateEvaluation(
            interview_id=interview_id,
            overall_score=overall_score,
            skill_scores=skill_scores,
        )

        self.db.add(evaluation)
        self.db.flush()
        self.db.refresh(evaluation)

        return evaluation

    def get_by_candidate_id(
        self,
        candidate_id: int,
    ) -> list[CandidateEvaluation]:
        statement = (
            select(CandidateEvaluation)
            .join(
                Interview,
                Interview.id == CandidateEvaluation.interview_id,
            )
            .join(
                Application,
                Application.id == Interview.application_id,
            )
            .where(
                Application.candidate_id == candidate_id,
            )
        )

        return list(self.db.scalars(statement).all())

    def get_by_id(
        self,
        candidate_evaluation_id: int,
    ) -> CandidateEvaluation | None:
        statement = select(CandidateEvaluation).where(
            CandidateEvaluation.id == candidate_evaluation_id,
        )

        return self.db.scalar(statement)

    def get_by_interview_id(
        self,
        interview_id: int,
    ) -> CandidateEvaluation | None:
        statement = select(CandidateEvaluation).where(
            CandidateEvaluation.interview_id == interview_id,
        )

        return self.db.scalar(statement)