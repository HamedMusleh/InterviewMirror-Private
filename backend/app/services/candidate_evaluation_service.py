from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.repositories.candidate_evaluation_repository import (
    CandidateEvaluationRepository,
)
from app.schemas.evaluation import (
    CandidateEvaluationCreate,
    InterviewAnswerEvaluationCreate,
    InterviewAnswerEvaluationResponse,
    InterviewEvaluationsResponse,
    OverallEvaluationResponse,
    SkillScore,
)


class CandidateEvaluationService:
    def __init__(self, db: Session):
        self.repository = CandidateEvaluationRepository(db)

    def create_answer_evaluation(
        self,
        data: InterviewAnswerEvaluationCreate,
    ):
        return self.repository.create_answer_evaluation(
            answer_id=data.answer_id,
            relevance_score=data.relevance_score,
            correctness_score=data.correctness_score,
            depth_score=data.depth_score,
            practicality_score=data.practicality_score,
            score=data.score,
            strengths=data.strengths,
            weaknesses=data.weaknesses,
        )

    def get_candidate_interview_evaluations(
        self,
        interview_id: int,
        candidate_id: int,
    ) -> InterviewEvaluationsResponse:
        results = self.repository.get_candidate_interview_evaluations(
            interview_id=interview_id,
            candidate_id=candidate_id,
        )

        evaluations = [
            InterviewAnswerEvaluationResponse(
                answer_id=evaluation.answer_id,
                skill=skill,
                relevance_score=evaluation.relevance_score,
                correctness_score=evaluation.correctness_score,
                depth_score=evaluation.depth_score,
                practicality_score=evaluation.practicality_score,
                strengths=evaluation.strengths,
                weaknesses=evaluation.weaknesses,
                score=evaluation.score,
            )
            for evaluation, skill in results
        ]

        return InterviewEvaluationsResponse(
            interview_id=interview_id,
            candidate_id=candidate_id,
            evaluations=evaluations,
        )

    def create_candidate_evaluation(
        self,
        data: CandidateEvaluationCreate,
    ):
        """
        Create a persisted candidate-level evaluation.

        Candidate-level scores use the same 1-10 scale
        as answer-level evaluations.

        The candidate_evaluations database table stores:
        - interview_id
        - overall_score
        - skill_scores
        """

        return self.repository.create_candidate_evaluation(
            interview_id=data.interview_id,
            overall_score=data.overall_score,
            skill_scores=data.skill_scores,
        )

    def calculate_and_store_candidate_evaluation(
        self,
        interview_id: int,
    ):
        """
        Calculate and persist the candidate-level evaluation.

        All scores use the same 1-10 scale.

        Overall score:
            Average of all answer-level scores.

        Skill score:
            Average of all answer-level scores belonging
            to that skill.

        Strengths and weaknesses are intentionally not stored
        in candidate_evaluations because those columns do not
        exist in the database table.
        """

        existing = self.repository.get_by_interview_id(
            interview_id=interview_id,
        )

        if existing is not None:
            return existing

        results = self.repository.get_interview_evaluations(
            interview_id=interview_id,
        )

        if not results:
            return None

        answer_scores = [
            float(evaluation.score)
            for evaluation, _ in results
        ]

        overall_score = round(
            sum(answer_scores) / len(answer_scores),
            2,
        )

        skill_scores: dict[str, list[float]] = defaultdict(list)

        for evaluation, skill in results:
            if skill:
                skill_scores[skill].append(
                    float(evaluation.score)
                )

        calculated_skill_scores: dict[str, float] = {
            skill: round(
                sum(scores) / len(scores),
                2,
            )
            for skill, scores in sorted(
                skill_scores.items()
            )
        }

        return self.repository.create_candidate_evaluation(
            interview_id=interview_id,
            overall_score=overall_score,
            skill_scores=calculated_skill_scores,
        )

    def get_overall_candidate_evaluation(
        self,
        interview_id: int,
        candidate_id: int,
    ) -> OverallEvaluationResponse:
        """
        Calculate the overall evaluation for a candidate interview.

        All scores use the same 1-10 scale.

        Strengths and weaknesses are aggregated from
        answer-level evaluations.
        """

        results = self.repository.get_candidate_interview_evaluations(
            interview_id=interview_id,
            candidate_id=candidate_id,
        )

        if not results:
            return OverallEvaluationResponse(
                interview_id=interview_id,
                candidate_id=candidate_id,
                overall_score=None,
                skill_scores=[],
                strengths=[],
                weaknesses=[],
            )

        answer_scores = [
            float(evaluation.score)
            for evaluation, _ in results
        ]

        overall_score = round(
            sum(answer_scores) / len(answer_scores),
            2,
        )

        skill_scores_map: dict[str, list[float]] = defaultdict(list)

        for evaluation, skill in results:
            if skill:
                skill_scores_map[skill].append(
                    float(evaluation.score)
                )

        skill_scores = [
            SkillScore(
                skill=skill,
                score=round(
                    sum(scores) / len(scores),
                    2,
                ),
            )
            for skill, scores in sorted(
                skill_scores_map.items()
            )
        ]

        strengths: list[str] = []

        for evaluation, _ in results:
            if evaluation.strengths:
                strengths.extend(evaluation.strengths)

        weaknesses: list[str] = []

        for evaluation, _ in results:
            if evaluation.weaknesses:
                weaknesses.extend(evaluation.weaknesses)

        return OverallEvaluationResponse(
            interview_id=interview_id,
            candidate_id=candidate_id,
            overall_score=overall_score,
            skill_scores=skill_scores,
            strengths=self._unique_strings(strengths),
            weaknesses=self._unique_strings(weaknesses),
        )

    @staticmethod
    def _unique_strings(
        values: list[str],
    ) -> list[str]:
        """
        Remove duplicate strings while preserving
        their original order.
        """

        seen: set[str] = set()
        result: list[str] = []

        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)

        return result

