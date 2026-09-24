from unittest.mock import MagicMock

from app.repositories.interview_answer_repository import (
    InterviewAnswerRepository,
)


def test_create_persists_all_given_fields_without_committing():
    db = MagicMock()
    repository = InterviewAnswerRepository(db)

    answer = repository.create(
        question_id=25,
        answer_text="I used FastAPI.",
        transcript="I used FastAPI.",
    )

    assert answer.question_id == 25
    assert answer.answer_text == "I used FastAPI."
    assert answer.audio_url is None
    assert answer.video_url is None
    assert answer.transcript == "I used FastAPI."

    db.add.assert_called_once_with(answer)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(answer)
    db.commit.assert_not_called()


def test_create_audio_answer_persists_and_commits():
    db = MagicMock()
    repository = InterviewAnswerRepository(db)

    answer = repository.create_audio_answer(
        question_id=25,
        audio_url="https://example.com/answer.webm",
    )

    assert answer.question_id == 25
    assert answer.audio_url == "https://example.com/answer.webm"
    assert answer.answer_text is None

    db.add.assert_called_once_with(answer)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(answer)
    db.commit.assert_called_once()
