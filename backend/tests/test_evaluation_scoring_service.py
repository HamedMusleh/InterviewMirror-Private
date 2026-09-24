import pytest

from app.schemas.evaluation import CriteriaScores
from app.services.evaluation_scoring_service import (
    EvaluationScoringService,
)


def valid_scores() -> CriteriaScores:
    return CriteriaScores(
        relevance=9,
        correctness=8,
        depth=6,
        practicality=7,
    )


def test_calculate_weighted_score():
    service = EvaluationScoringService()

    result = service.calculate_score(valid_scores())

    assert result == pytest.approx(7.65)


def test_perfect_scores_return_ten():
    service = EvaluationScoringService()

    scores = CriteriaScores(
        relevance=10,
        correctness=10,
        depth=10,
        practicality=10,
    )

    result = service.calculate_score(scores)

    assert result == pytest.approx(10.0)


def test_minimum_scores_return_one():
    service = EvaluationScoringService()

    scores = CriteriaScores(
        relevance=1,
        correctness=1,
        depth=1,
        practicality=1,
    )

    result = service.calculate_score(scores)

    assert result == pytest.approx(1.0)


def test_weights_sum_to_one():
    service = EvaluationScoringService()

    assert sum(service.WEIGHTS.values()) == pytest.approx(1.0)


def test_all_criteria_have_weights():
    service = EvaluationScoringService()

    assert set(service.WEIGHTS.keys()) == {
        "relevance",
        "correctness",
        "depth",
        "practicality",
    }


def test_invalid_weights_sum_raise_error():
    with pytest.raises(ValueError, match="sum to 1.0"):
        EvaluationScoringService(
            weights={
                "relevance": 0.30,
                "correctness": 0.30,
                "depth": 0.25,
                "practicality": 0.20,
            }
        )


def test_missing_criteria_raise_error():
    with pytest.raises(ValueError, match="criteria"):
        EvaluationScoringService(
            weights={
                "relevance": 0.30,
                "correctness": 0.30,
                "depth": 0.25,
            }
        )


def test_extra_criteria_raise_error():
    with pytest.raises(ValueError, match="criteria"):
        EvaluationScoringService(
            weights={
                "relevance": 0.30,
                "correctness": 0.30,
                "depth": 0.25,
                "practicality": 0.15,
                "clarity": 0.00,
            }
        )


def test_negative_weight_raises_error():
    with pytest.raises(ValueError, match="between 0 and 1"):
        EvaluationScoringService(
            weights={
                "relevance": -0.30,
                "correctness": 0.30,
                "depth": 0.25,
                "practicality": 0.75,
            }
        )


def test_weight_greater_than_one_raises_error():
    with pytest.raises(ValueError, match="between 0 and 1"):
        EvaluationScoringService(
            weights={
                "relevance": 1.10,
                "correctness": 0.00,
                "depth": 0.00,
                "practicality": 0.00,
            }
        )