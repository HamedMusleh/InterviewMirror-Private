"""
Tests for the live answer channel's submission path.

The WebSocket handler itself needs a socket, but the part that matters most
is testable directly: a streamed answer must go through the interview flow,
not straight into storage. Bypassing the flow produces an interview that
never asks a follow-up and never reports itself finished, and nothing about
that failure is visible at the API boundary — the answer is stored, the
socket closes cleanly, and the candidate simply never gets asked anything
adaptive.
"""

import asyncio
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.interview_stream import router as stream_router
from app.schemas.interview_flow import InterviewFlowResult
from app.schemas.interview_question_storage import InterviewQuestionResponse


def make_question_response(
    id=26,
    interview_id=4,
    is_follow_up=True,
    parent_question_id=25,
):
    return InterviewQuestionResponse(
        id=id,
        interview_id=interview_id,
        question_text=(
            "Can you say more about how you handled the failure case?"
        ),
        question_type="skills",
        skill="FastAPI",
        sequence_number=2,
        is_follow_up=is_follow_up,
        parent_question_id=parent_question_id,
    )


def test_interview_and_question_text_are_resolved_from_the_question():
    """
    The text matters as much as the id. It is what the interviewer refers
    back to when bridging into the next question, and it has to be read
    before the answer is submitted, because submitting can generate a
    follow-up and move the interview on.
    """

    session = MagicMock()

    with patch.object(
        stream_router, "SessionLocal", return_value=session
    ), patch.object(
        stream_router, "InterviewQuestionRepository"
    ) as repository:
        repository.return_value.get_by_id.return_value = SimpleNamespace(
            id=25,
            interview_id=4,
            question_text="Tell me about a system you designed.",
        )

        assert stream_router._load_question(25) == (
            4,
            "Tell me about a system you designed.",
        )

    session.close.assert_called_once()


def test_unknown_question_resolves_to_none():
    session = MagicMock()

    with patch.object(
        stream_router, "SessionLocal", return_value=session
    ), patch.object(
        stream_router, "InterviewQuestionRepository"
    ) as repository:
        repository.return_value.get_by_id.return_value = None

        assert stream_router._load_question(999) is None

    session.close.assert_called_once()


def test_submitting_goes_through_the_interview_flow():
    """The regression guard: storing directly would skip follow-ups."""

    session = MagicMock()
    service = MagicMock()
    service.submit_answer = AsyncMock(
        return_value=InterviewFlowResult(
            follow_up_generated=True,
            next_question=make_question_response(),
            interview_completed=False,
        )
    )

    with patch.object(
        stream_router, "SessionLocal", return_value=session
    ), patch.object(
        stream_router, "build_interview_flow_service", return_value=service
    ):
        result = asyncio.run(
            stream_router._submit_answer(
                interview_id=4,
                question_id=25,
                audio_url="https://blob.example/answer.webm",
                transcript="I handled it with a retry and a dead letter queue.",
            )
        )

    assert result.follow_up_generated is True
    assert result.next_question.is_follow_up is True

    service.submit_answer.assert_awaited_once()
    session.commit.assert_called_once()
    session.close.assert_called_once()


def test_the_live_transcript_is_reused_instead_of_transcribing_again():
    """
    The transcript goes in as `answer_text`.

    The flow falls back to speech-to-text only when no text is supplied, so
    passing it here is what stops the whole recording being transcribed a
    second time after it has already been recognised live.
    """

    service = MagicMock()
    service.submit_answer = AsyncMock(
        return_value=InterviewFlowResult(
            follow_up_generated=False,
            next_question=None,
            interview_completed=True,
        )
    )

    with patch.object(
        stream_router, "SessionLocal", return_value=MagicMock()
    ), patch.object(
        stream_router, "build_interview_flow_service", return_value=service
    ):
        asyncio.run(
            stream_router._submit_answer(
                interview_id=4,
                question_id=25,
                audio_url="https://blob.example/answer.webm",
                transcript="A complete spoken answer.",
            )
        )

    request = service.submit_answer.await_args.args[0]

    assert request.interview_id == 4
    assert request.question_id == 25
    assert request.answer_text == "A complete spoken answer."
    assert request.audio_url == "https://blob.example/answer.webm"


def test_a_failed_submission_rolls_back_and_closes():
    session = MagicMock()
    service = MagicMock()
    service.submit_answer = AsyncMock(side_effect=ValueError("no such question"))

    with patch.object(
        stream_router, "SessionLocal", return_value=session
    ), patch.object(
        stream_router, "build_interview_flow_service", return_value=service
    ):
        try:
            asyncio.run(
                stream_router._submit_answer(
                    interview_id=4,
                    question_id=25,
                    audio_url="https://blob.example/answer.webm",
                    transcript="Something.",
                )
            )
        except ValueError:
            pass
        else:
            raise AssertionError("the error should propagate")

    session.rollback.assert_called_once()
    session.commit.assert_not_called()
    session.close.assert_called_once()


def test_control_frames_are_parsed_and_junk_is_ignored():
    assert stream_router._parse_control('{"type": "stop"}') == "stop"
    assert stream_router._parse_control('{"type": "cancel"}') == "cancel"
    assert stream_router._parse_control("not json") is None
    assert stream_router._parse_control('["stop"]') is None
    assert stream_router._parse_control('{"type": 3}') is None
    assert stream_router._parse_control(None) is None


def test_an_unheard_answer_is_offered_as_a_retry_not_a_fault():
    """
    The regression this guards is a dead end, not a crash.

    An empty transcript used to be submitted anyway. The flow reads a blank
    `answer_text` as "no text supplied" and falls back to transcribing the
    recording in batch, which fails on the same silence and reaches the
    candidate as "Speech recognition could not understand the audio" with no
    way forward. Saying nothing usable is an ordinary thing to happen in a
    real interview, so it has to come back as something to try again.
    """

    source = inspect.getsource(stream_router.stream_answer)

    assert "if not transcript.strip():" in source
    assert '"retryable": True' in source

    # And it must bail out before the answer reaches the flow, or the batch
    # fallback still runs and still fails.
    assert source.index("if not transcript.strip():") < source.index(
        "result = await _submit_answer("
    )
