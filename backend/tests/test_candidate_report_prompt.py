from app.prompts.candidate_report_prompt import (
    CANDIDATE_REPORT_SYSTEM_PROMPT,
    build_candidate_report_prompt,
)
from app.schemas.candidate_report import CandidateReportInput


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


def test_build_candidate_report_prompt_contains_evaluation_data():
    evaluation = CandidateReportInput.model_validate(valid_input())

    prompt = build_candidate_report_prompt(evaluation)

    assert '"id": 1' in prompt
    assert '"interview_id": 4' in prompt
    assert '"overall_score": 78.0' in prompt
    assert '"FastAPI": 75.0' in prompt
    assert "Strong Python knowledge" in prompt
    assert "Limited technical depth in FastAPI" in prompt


def test_build_candidate_report_prompt_contains_output_schema():
    evaluation = CandidateReportInput.model_validate(valid_input())

    prompt = build_candidate_report_prompt(evaluation)

    assert '"summary"' in prompt
    assert '"strengths"' in prompt
    assert '"areas_for_improvement"' in prompt
    assert '"recommendation"' in prompt


def test_prompt_prevents_score_modification():
    assert (
        "Do not recalculate, modify, reinterpret, or replace"
        in CANDIDATE_REPORT_SYSTEM_PROMPT
    )
    assert (
        "Do not include id, interview_id, overall_score, or skill_scores"
        in CANDIDATE_REPORT_SYSTEM_PROMPT
    )


def test_prompt_restricts_report_to_evaluation_data():
    assert (
        "Use only information contained"
        in CANDIDATE_REPORT_SYSTEM_PROMPT
    )
    assert (
        "Do not invent experience, skills, achievements"
        in CANDIDATE_REPORT_SYSTEM_PROMPT
    )