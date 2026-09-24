import pytest
from pydantic import ValidationError

from app.schemas.candidate_report import (
    CandidateReport,
    CandidateReportInput,
    GeneratedReportContent,
)


def valid_input() -> dict:
    return {
        "id": 1,
        "interview_id": 4,
        "overall_score": 78,
        "skill_scores": {
            "FastAPI": 75,
            "Python": 85,
        },
        "strengths": [
            "Strong Python knowledge",
            "Relevant backend experience",
        ],
        "weaknesses": [
            "Limited technical depth in FastAPI",
        ],
    }


def test_candidate_report_input_accepts_valid_evaluation():
    result = CandidateReportInput.model_validate(valid_input())

    assert result.id == 1
    assert result.interview_id == 4
    assert result.overall_score == 78
    assert result.skill_scores["FastAPI"] == 75


@pytest.mark.parametrize(
    "field_name",
    ["id", "interview_id"],
)
def test_candidate_report_input_rejects_non_positive_ids(field_name):
    data = valid_input()
    data[field_name] = 0

    with pytest.raises(ValidationError):
        CandidateReportInput.model_validate(data)


@pytest.mark.parametrize("score", [-1, 101])
def test_candidate_report_input_rejects_invalid_overall_score(score):
    data = valid_input()
    data["overall_score"] = score

    with pytest.raises(ValidationError):
        CandidateReportInput.model_validate(data)


@pytest.mark.parametrize("score", [-1, 101])
def test_candidate_report_input_rejects_invalid_skill_score(score):
    data = valid_input()
    data["skill_scores"]["FastAPI"] = score

    with pytest.raises(ValidationError):
        CandidateReportInput.model_validate(data)


def test_candidate_report_input_rejects_blank_strength():
    data = valid_input()
    data["strengths"] = ["   "]

    with pytest.raises(ValidationError):
        CandidateReportInput.model_validate(data)


def test_generated_report_content_accepts_valid_content():
    content = GeneratedReportContent.model_validate(
        {
            "summary": "The candidate demonstrated good backend knowledge.",
            "strengths": ["Strong Python knowledge"],
            "areas_for_improvement": [
                "Needs greater technical depth in FastAPI"
            ],
            "recommendation": (
                "The candidate demonstrates good potential for the role."
            ),
        }
    )

    assert content.summary
    assert content.strengths == ["Strong Python knowledge"]


def test_generated_report_content_rejects_blank_text():
    with pytest.raises(ValidationError):
        GeneratedReportContent.model_validate(
            {
                "summary": "   ",
                "strengths": ["Strong Python knowledge"],
                "areas_for_improvement": ["Improve FastAPI depth"],
                "recommendation": "Good potential",
            }
        )


def test_generated_report_content_rejects_extra_fields():
    with pytest.raises(ValidationError):
        GeneratedReportContent.model_validate(
            {
                "summary": "Good backend knowledge",
                "strengths": ["Strong Python knowledge"],
                "areas_for_improvement": ["Improve FastAPI depth"],
                "recommendation": "Good potential",
                "overall_score": 99,
            }
        )


def test_candidate_report_accepts_final_output():
    report = CandidateReport.model_validate(
        {
            "candidate_evaluation_id": 1,
            "interview_id": 4,
            "overall_score": 78,
            "skill_scores": {
                "FastAPI": 75,
                "Python": 85,
            },
            "summary": (
                "The candidate demonstrated strong Python knowledge "
                "and relevant backend experience."
            ),
            "strengths": [
                "Strong Python knowledge",
                "Relevant backend experience",
            ],
            "areas_for_improvement": [
                "Needs greater technical depth in FastAPI",
            ],
            "recommendation": (
                "The candidate demonstrates good potential for the role."
            ),
        }
    )

    assert report.candidate_evaluation_id == 1
    assert report.overall_score == 78
    assert report.skill_scores["Python"] == 85