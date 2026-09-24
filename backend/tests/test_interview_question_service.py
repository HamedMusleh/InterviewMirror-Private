from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.adaptive_follow_up import FollowUpQuestionResponse
from app.services.interview_question_service import InterviewQuestionService


def make_parent_question(id=25, interview_id=4):
    return SimpleNamespace(id=id, interview_id=interview_id)


def make_service(parent_question=None, max_sequence_number=1):
    mock_repository = MagicMock()
    mock_repository.get_by_id.return_value = parent_question
    mock_repository.get_max_sequence_number.return_value = (
        max_sequence_number
    )
    mock_repository.create.side_effect = lambda question: question

    with patch(
        "app.services.interview_question_service."
        "InterviewQuestionRepository",
        return_value=mock_repository,
    ):
        service = InterviewQuestionService(db=MagicMock())

    return service, mock_repository


def test_store_follow_up_question_persists_expected_fields():
    service, mock_repository = make_service(
        parent_question=make_parent_question(id=25, interview_id=4),
        max_sequence_number=2,
    )

    follow_up = FollowUpQuestionResponse(
        parent_question_id=25,
        question="Can you give a specific example?",
        category="skills",
        skill="FastAPI",
    )

    question = service.store_follow_up_question(
        interview_id=4,
        follow_up=follow_up,
    )

    assert question.interview_id == 4
    assert question.question_text == "Can you give a specific example?"
    assert question.question_type == "skills"
    assert question.skill == "FastAPI"
    assert question.sequence_number == 3
    assert question.is_follow_up is True
    assert question.parent_question_id == 25


def test_store_follow_up_question_locks_interview_before_sequencing():
    service, mock_repository = make_service(
        parent_question=make_parent_question(id=25, interview_id=4),
    )

    follow_up = FollowUpQuestionResponse(
        parent_question_id=25,
        question="Can you give a specific example?",
        category="skills",
    )

    service.store_follow_up_question(interview_id=4, follow_up=follow_up)

    mock_repository.lock_interview.assert_called_once_with(4)
    mock_repository.get_max_sequence_number.assert_called_once_with(4)


def test_store_follow_up_question_raises_when_parent_not_found():
    service, _ = make_service(parent_question=None)

    follow_up = FollowUpQuestionResponse(
        parent_question_id=99,
        question="Can you give a specific example?",
        category="skills",
    )

    with pytest.raises(ValueError, match="question 99 not found"):
        service.store_follow_up_question(interview_id=4, follow_up=follow_up)


def test_store_follow_up_question_raises_when_parent_belongs_to_other_interview():
    service, _ = make_service(
        parent_question=make_parent_question(id=25, interview_id=999),
    )

    follow_up = FollowUpQuestionResponse(
        parent_question_id=25,
        question="Can you give a specific example?",
        category="skills",
    )

    with pytest.raises(ValueError, match="does not belong to interview 4"):
        service.store_follow_up_question(interview_id=4, follow_up=follow_up)
