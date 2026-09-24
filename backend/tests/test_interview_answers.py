from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies.blob_storage import get_blob_storage_service
from app.dependencies.db import get_db
from app.dependencies.speech_to_text import get_speech_to_text_service
from app.main import app
from app.services.interview_answer_service import InterviewAnswerService


ENDPOINT = "/api/interview-answers/audio"


def test_create_audio_answer_passes_transcript_to_repository():
    db = MagicMock()
    service = InterviewAnswerService(db)

    service.repository = MagicMock()

    expected_answer = MagicMock()
    service.repository.create_audio_answer.return_value = expected_answer

    result = service.create_audio_answer(
        question_id=25,
        audio_url="https://example.com/answer.webm",
        transcript="I used FastAPI to build REST APIs.",
    )

    assert result == expected_answer

    service.repository.create_audio_answer.assert_called_once_with(
        question_id=25,
        audio_url="https://example.com/answer.webm",
        transcript="I used FastAPI to build REST APIs.",
    )


def test_create_audio_answer_allows_missing_transcript():
    db = MagicMock()
    service = InterviewAnswerService(db)

    service.repository = MagicMock()

    service.create_audio_answer(
        question_id=25,
        audio_url="https://example.com/answer.webm",
    )

    service.repository.create_audio_answer.assert_called_once_with(
        question_id=25,
        audio_url="https://example.com/answer.webm",
        transcript=None,
    )


@pytest.fixture
def client():
    db = MagicMock()

    app.dependency_overrides[get_db] = lambda: db

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_audio_answer_returns_404_when_question_does_not_exist(client):
    with patch(
        "app.modules.interview_answers.router."
        "InterviewQuestionRepository"
    ) as repository_class:
        repository_class.return_value.get_by_id.return_value = None

        response = client.post(
            ENDPOINT,
            data={"question_id": 999},
            files={
                "audio": (
                    "answer.webm",
                    b"fake-audio",
                    "audio/webm",
                )
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Interview question not found."
    )


def test_audio_answer_hides_internal_error_details(client):
    blob_storage_service = MagicMock()
    blob_storage_service.upload_audio.side_effect = RuntimeError(
        "secret internal Azure error"
    )

    speech_to_text_service = MagicMock()

    app.dependency_overrides[get_blob_storage_service] = (
        lambda: blob_storage_service
    )
    app.dependency_overrides[get_speech_to_text_service] = (
        lambda: speech_to_text_service
    )

    question = SimpleNamespace(id=25)

    with patch(
        "app.modules.interview_answers.router."
        "InterviewQuestionRepository"
    ) as repository_class:
        repository_class.return_value.get_by_id.return_value = question

        response = client.post(
            ENDPOINT,
            data={"question_id": 25},
            files={
                "audio": (
                    "answer.webm",
                    b"fake-audio",
                    "audio/webm",
                )
            },
        )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Failed to process interview answer."
    )
    assert "secret internal Azure error" not in response.text