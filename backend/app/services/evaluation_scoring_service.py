from math import isclose

from app.schemas.evaluation import (
    CriteriaScores,
    EvaluationResult,
    FinalEvaluationResult,
)


class EvaluationScoringService:
    """
    Calculate the final weighted evaluation score.

    The individual criterion scores are produced by the Evaluation LLM.
    This service validates the evaluation weights and calculates the
    deterministic final score.
    """

    WEIGHTS = {
        "relevance": 0.30,
        "correctness": 0.30,
        "depth": 0.25,
        "practicality": 0.15,
    }

    REQUIRED_CRITERIA = {
        "relevance",
        "correctness",
        "depth",
        "practicality",
    }

    def __init__(
        self,
        weights: dict[str, float] | None = None,
    ) -> None:
        """
        Initialize the scoring service.

        If custom weights are provided, they are validated before use.
        Otherwise, the default evaluation weights are used.
        """

        if weights is None:
            weights = self.WEIGHTS.copy()

        self._validate_weights(weights)

        self.WEIGHTS = weights.copy()

    @classmethod
    def _validate_weights(
        cls,
        weights: dict[str, float],
    ) -> None:
        """Validate evaluation criteria weights."""

        if set(weights.keys()) != cls.REQUIRED_CRITERIA:
            raise ValueError(
                "Weights must contain exactly the required criteria."
            )

        for criterion, weight in weights.items():
            if not 0 <= weight <= 1:
                raise ValueError(
                    f"Weight for '{criterion}' must be between 0 and 1."
                )

        total = sum(weights.values())

        if not isclose(
            total,
            1.0,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            raise ValueError(
                f"Evaluation weights must sum to 1.0, got {total}."
            )

    def calculate_score(
        self,
        criteria_scores: CriteriaScores,
    ) -> float:
        """Calculate the weighted score from 1 to 10."""

        return round(
            (
                criteria_scores.relevance
                * self.WEIGHTS["relevance"]
                + criteria_scores.correctness
                * self.WEIGHTS["correctness"]
                + criteria_scores.depth
                * self.WEIGHTS["depth"]
                + criteria_scores.practicality
                * self.WEIGHTS["practicality"]
            ),
            2,
        )

    def build_final_result(
        self,
        evaluation_result: EvaluationResult,
    ) -> FinalEvaluationResult:
        """
        Build the final evaluation result.

        The LLM-generated evaluation data is preserved unchanged.
        Only the deterministic weighted score is added.
        """

        score = self.calculate_score(
            evaluation_result.criteria_scores
        )

        return FinalEvaluationResult(
            criteria_scores=evaluation_result.criteria_scores,
            strengths=evaluation_result.strengths,
            weaknesses=evaluation_result.weaknesses,
            score=score,
        )