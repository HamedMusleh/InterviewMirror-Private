import pytest
from pydantic import ValidationError

from app.prompts.answer_analysis_prompt import (
    build_answer_analysis_prompt,
)
from app.schemas.answer_analysis import AnswerAnalysisInput


def valid_input() -> dict:
    return {
        "interview_id": 4,
        "question_id": 25,
        "role": "Backend Developer",
        "question": "Explain your experience with FastAPI.",
        "question_type": "skills",
        "skill": "FastAPI",
        "answer": (
            "I used FastAPI to build REST APIs "
            "for a university project."
        ),
        "previous_interactions": [],
    }


def test_answer_analysis_input_accepts_valid_context():
    data = AnswerAnalysisInput.model_validate(valid_input())

    assert data.interview_id == 4
    assert data.question_id == 25
    assert data.skill == "FastAPI"


def test_build_answer_analysis_prompt_contains_context():
    validated = AnswerAnalysisInput.model_validate(valid_input())

    prompt = build_answer_analysis_prompt(validated)

    assert "Backend Developer" in prompt
    assert "FastAPI" in prompt
    assert "I used FastAPI to build REST APIs" in prompt
    assert '"interview_id": 4' in prompt
    assert '"question_id": 25' in prompt


def test_build_answer_analysis_prompt_contains_output_schema():
    validated = AnswerAnalysisInput.model_validate(valid_input())

    prompt = build_answer_analysis_prompt(validated)

    assert '"answer_quality"' in prompt
    assert '"relevant_points"' in prompt
    assert '"missing_areas"' in prompt
    assert '"evidence"' in prompt
    assert '"follow_up_needed"' in prompt
    assert '"follow_up_reason"' in prompt


def test_prompt_does_not_request_follow_up_question_generation():
    validated = AnswerAnalysisInput.model_validate(valid_input())

    prompt = build_answer_analysis_prompt(validated)

    assert "Do not generate the follow-up question" in prompt
    assert "Do not assign a numeric evaluation score" in prompt


def test_answer_analysis_input_rejects_empty_answer():
    data = valid_input()
    data["answer"] = ""

    with pytest.raises(ValidationError):
        AnswerAnalysisInput.model_validate(data)


def test_answer_analysis_input_rejects_whitespace_only_answer():
    data = valid_input()
    data["answer"] = "   "

    with pytest.raises(ValidationError):
        AnswerAnalysisInput.model_validate(data)


def test_answer_analysis_input_rejects_empty_question():
    data = valid_input()
    data["question"] = ""

    with pytest.raises(ValidationError):
        AnswerAnalysisInput.model_validate(data)


def test_answer_analysis_input_accepts_missing_skill():
    data = valid_input()
    data["skill"] = None

    validated = AnswerAnalysisInput.model_validate(data)

    assert validated.skill is None


def test_answer_analysis_input_rejects_non_positive_ids():
    data = valid_input()
    data["interview_id"] = 0

    with pytest.raises(ValidationError):
        AnswerAnalysisInput.model_validate(data)


def test_build_answer_analysis_prompt_contains_previous_interactions():
    data = valid_input()

    data["previous_interactions"] = [
        {
            "question": "Which Python frameworks have you used?",
            "answer": "I have used Django and FastAPI.",
        }
    ]

    validated = AnswerAnalysisInput.model_validate(data)

    prompt = build_answer_analysis_prompt(validated)

    assert "Which Python frameworks have you used?" in prompt
    assert "I have used Django and FastAPI." in prompt

def test_prompt_defines_follow_up_reason_contract():
    validated = AnswerAnalysisInput.model_validate(valid_input())

    prompt = build_answer_analysis_prompt(validated)

    assert '"follow_up_reason": null' in prompt
    assert "When follow_up_needed is true" in prompt
    assert "When follow_up_needed is false" in prompt