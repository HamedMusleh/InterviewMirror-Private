import pytest
from pydantic import ValidationError

from app.schemas.screening_score import ScreeningScoreRequest
from app.services.screening_score_service import calculate_screening_score


def make_request(category_scores):
    return ScreeningScoreRequest(
        candidate_id="candidate-1",
        job_id="job-1",
        category_scores=category_scores,
        category_weights={
            "skills": 50,
            "experience": 25,
            "education": 10,
            "projects": 5,
            "certifications": 3,
            "languages": 2,
            "soft_skills": 5,
        },
        passing_score=70,
    )


def test_full_screening_score():
    request = make_request(
        {
            "skills": {"score": 80, "weight": 50, "status": "evaluated"},
            "experience": {"score": 70, "weight": 25, "status": "evaluated"},
            "education": {"score": 90, "weight": 10, "status": "evaluated"},
            "projects": {"score": 60, "weight": 5, "status": "evaluated"},
            "certifications": {"score": 100, "weight": 3, "status": "evaluated"},
            "languages": {"score": 80, "weight": 2, "status": "evaluated"},
            "soft_skills": {"score": 70, "weight": 5, "status": "evaluated"},
        }
    )

    result = calculate_screening_score(request)

    assert result.overall_score == pytest.approx(77.6)
    assert result.final_status == "recommended"


def test_not_applicable_is_excluded():
    request = make_request(
        {
            "skills": {"score": 80, "weight": 50, "status": "evaluated"},
            "experience": {"score": 70, "weight": 25, "status": "evaluated"},
            "education": {"score": None, "weight": 10, "status": "not_applicable"},
            "projects": {"score": 60, "weight": 5, "status": "evaluated"},
            "certifications": {
                "score": None,
                "weight": 3,
                "status": "not_applicable",
            },
            "languages": {
                "score": None,
                "weight": 2,
                "status": "not_applicable",
            },
            "soft_skills": {
                "score": None,
                "weight": 5,
                "status": "not_applicable",
            },
        }
    )

    result = calculate_screening_score(request)

    assert result.overall_score == pytest.approx(75.62)
    assert result.category_breakdown["education"].score is None
    assert result.category_breakdown["education"].weight is None


def test_score_below_passing_score():
    request = make_request(
        {
            "skills": {"score": 50, "weight": 50, "status": "evaluated"},
            "experience": {"score": 40, "weight": 25, "status": "evaluated"},
            "education": {"score": 50, "weight": 10, "status": "evaluated"},
            "projects": {"score": 40, "weight": 5, "status": "evaluated"},
            "certifications": {"score": 50, "weight": 3, "status": "evaluated"},
            "languages": {"score": 50, "weight": 2, "status": "evaluated"},
            "soft_skills": {"score": 50, "weight": 5, "status": "evaluated"},
        }
    )

    result = calculate_screening_score(request)

    assert result.overall_score < 70
    assert result.final_status == "not_recommended"


def test_invalid_score_is_rejected():
    with pytest.raises(ValidationError):
        make_request(
            {
                "skills": {"score": 101, "weight": 50, "status": "evaluated"},
                "experience": {"score": 70, "weight": 25, "status": "evaluated"},
                "education": {"score": 90, "weight": 10, "status": "evaluated"},
                "projects": {"score": 60, "weight": 5, "status": "evaluated"},
                "certifications": {
                    "score": 100,
                    "weight": 3,
                    "status": "evaluated",
                },
                "languages": {"score": 80, "weight": 2, "status": "evaluated"},
                "soft_skills": {"score": 70, "weight": 5, "status": "evaluated"},
            }
        )