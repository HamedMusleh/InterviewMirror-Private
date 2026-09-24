"""
The live answer channel.

A candidate's answer arrives here as it is spoken, over a WebSocket, instead
of as a finished file uploaded afterwards. That is what makes turn detection
possible: the transcript is available while the person is still talking, so
the system can reason about whether they have finished.

Responsibilities are split deliberately between the two ends:

    the browser  measures how long the candidate has been silent
    the server   decides how long that silence needs to be

The browser has the audio and can react instantly with no round trip. The
server has the transcript, which is the only place the evidence about an
unfinished sentence lives. So the server pushes a threshold whenever the
transcript changes, and the browser fires against its own clock. Neither end
waits on the other at the moment that matters.

Wire protocol
-------------
client -> server   binary frames  raw audio chunks from MediaRecorder
                   {"type": "stop"}          candidate finished
                   {"type": "cancel"}        discard, do not store

server -> client   {"type": "ready"}
                   {"type": "transcript", "text": str, "isFinal": bool}
                   {"type": "endpoint", "silenceThresholdSeconds": float,
                    "state": str, "reason": str}
                   {"type": "stored", "transcript": str,
                    "audioUrl": str, "followUpGenerated": bool,
                    "interviewCompleted": bool, "nextQuestion": object|null,
                    "line": {"text": str, "style": str, "mood": str}}
                   {"type": "error", "detail": str}

`line` is what the interviewer says next: the bridge out of this answer and
into the next question, or the closing if that was the last one. It is
written here rather than fetched afterwards because the candidate is sitting
in silence waiting for it, and a separate request would add a round trip to
a gap that is already the least comfortable moment in the interview.
"""

import asyncio
import contextlib
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.database.session import SessionLocal
from app.dependencies.blob_storage import get_blob_storage_service
from app.dependencies.interview_conversation import (
    build_interview_conversation_service,
)
from app.dependencies.interview_flow import build_interview_flow_service
from app.dependencies.turn_detection import get_turn_completeness_analyzer
from app.repositories.interview_question_repository import (
    InterviewQuestionRepository,
)
from app.schemas.interview_context import InterviewContextRequest
from app.schemas.interview_conversation import (
    ConversationLine,
    ConversationLineRequest,
    ConversationMoment,
)
from app.schemas.interview_flow import InterviewFlowResult
from app.services.blob_storage_service import BlobStorageService
from app.services.streaming_transcription_service import (
    StreamingTranscriptionSession,
    build_push_stream,
    build_recognizer,
)
from app.services.turn_completeness_service import TurnCompletenessAnalyzer


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/interview-stream",
    tags=["Interview Stream"],
)


# An answer runs for minutes, so this connection is long-lived. The cap
# bounds the noisy-room case, where acoustic silence never arrives and the
# turn would otherwise never end: roughly 45 minutes of Opus.
MAX_ANSWER_BYTES = 32 * 1024 * 1024

# Archiving the recording should not be able to hold up the interview. If
# storage is slow or misconfigured the candidate must not sit waiting, so
# the upload is bounded and the answer proceeds without it.
AUDIO_UPLOAD_TIMEOUT_SECONDS = 30.0


def _load_question(question_id: int) -> tuple[int, str] | None:
    """
    Resolve which interview a question belongs to and what it asked, or None
    if it does not exist. Doubles as the existence check.

    The text is read here, at the start, rather than after the answer: by
    then a follow-up may have been generated and the interview moved on, and
    the bridge needs to refer to the question the candidate was actually
    answering.

    Uses its own short-lived session rather than `Depends(get_db)`: a
    request-scoped session would be pinned for the entire length of an
    answer, and with the default pool that caps concurrent interviews at
    fifteen. The database is only needed at the two ends of this connection.
    """

    db = SessionLocal()

    try:
        question = InterviewQuestionRepository(db).get_by_id(question_id)

        if question is None:
            return None

        return question.interview_id, question.question_text
    finally:
        db.close()


async def _compose_line(
    interview_id: int,
    moment: ConversationMoment,
    last_question: str,
    last_answer: str,
    next_question: str | None,
    next_is_follow_up: bool,
) -> ConversationLine:
    """
    Write what the interviewer says next.

    Runs on its own short-lived session for the same reason as everything
    else at this end of the connection. The service never raises -- it falls
    back to a scripted line -- but the session handling is still guarded,
    because a database that has gone away must not take the stored answer
    down with it.
    """

    db = SessionLocal()

    try:
        service = build_interview_conversation_service(db)

        return await service.compose(
            ConversationLineRequest(
                interview_id=interview_id,
                moment=moment,
                last_question=last_question,
                last_answer=last_answer,
                next_question=next_question,
                next_is_follow_up=next_is_follow_up,
            )
        )
    finally:
        db.close()


async def _submit_answer(
    interview_id: int,
    question_id: int,
    audio_url: str | None,
    transcript: str,
) -> InterviewFlowResult:
    """
    Hand the finished answer to the interview flow.

    Storing the answer directly here would be simpler and wrong: the flow is
    what analyses the answer, decides whether a follow-up is needed, stores
    the generated follow-up, and works out which question comes next or
    whether the interview is over. Bypassing it means an interview that never
    asks a follow-up, so the answer goes through the flow and the flow does
    the storing.

    The transcript is passed as `answer_text` so the flow uses what was
    already recognised live, rather than paying for the whole recording to be
    transcribed a second time.
    """

    db = SessionLocal()

    try:
        service = build_interview_flow_service(db)

        result = await service.submit_answer(
            InterviewContextRequest(
                interview_id=interview_id,
                question_id=question_id,
                answer_text=transcript,
                audio_url=audio_url,
            )
        )

        db.commit()

        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.websocket("/answers/{question_id}")
async def stream_answer(
    websocket: WebSocket,
    question_id: int,
    blob_storage_service: BlobStorageService = Depends(
        get_blob_storage_service
    ),
    analyzer: TurnCompletenessAnalyzer = Depends(
        get_turn_completeness_analyzer
    ),
) -> None:
    await websocket.accept()

    question = await run_in_threadpool(_load_question, question_id)

    if question is None:
        await _send(
            websocket,
            {"type": "error", "detail": "Interview question not found."},
        )
        await _close(websocket)
        return

    interview_id, question_text = question

    loop = asyncio.get_running_loop()
    updates: asyncio.Queue[tuple[str, bool]] = asyncio.Queue()

    def on_transcript(transcript: str, is_final: bool) -> None:
        # Azure calls this from its own threads, so hop back onto the loop.
        loop.call_soon_threadsafe(updates.put_nowait, (transcript, is_final))

    try:
        push_stream = build_push_stream()
        session = StreamingTranscriptionSession(
            recognizer=build_recognizer(push_stream),
            push_stream=push_stream,
            on_transcript=on_transcript,
        )
        session.start()
    except Exception as exc:
        logger.exception("Could not start live transcription.")
        await _send(
            websocket,
            {"type": "error", "detail": f"Transcription unavailable: {exc}"},
        )
        await _close(websocket)
        return

    publisher = asyncio.create_task(
        _publish_updates(websocket, updates, analyzer)
    )

    chunks: list[bytes] = []
    total_bytes = 0
    should_store = False

    await _send(websocket, {"type": "ready"})

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            payload = message.get("bytes")

            if payload:
                total_bytes += len(payload)

                if total_bytes > MAX_ANSWER_BYTES:
                    await _send(
                        websocket,
                        {
                            "type": "error",
                            "detail": "Answer exceeded the maximum length.",
                        },
                    )
                    break

                chunks.append(payload)
                session.write(payload)
                continue

            control = _parse_control(message.get("text"))

            if control == "stop":
                should_store = True
                break

            if control == "cancel":
                break

    except WebSocketDisconnect:
        pass
    finally:
        publisher.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await publisher

    # Always stop the session, even when the answer is being discarded, so
    # the recognizer and its connection are not left running.
    try:
        transcript = await run_in_threadpool(session.stop)
    except Exception as exc:
        logger.exception("Live transcription failed.")
        await _send(websocket, {"type": "error", "detail": str(exc)})
        await _close(websocket)
        return

    if not should_store or not chunks:
        await _close(websocket)
        return

    # Nothing was recognised.
    #
    # Submitting anyway is worse than it sounds: the flow treats an empty
    # `answer_text` as "no text supplied" and falls back to transcribing the
    # recording in batch, which fails on the same silence and surfaces as a
    # hard error the candidate can do nothing about. An unheard answer is a
    # normal thing to happen in a real room, so it is reported as something
    # to try again rather than as a fault.
    if not transcript.strip():
        await _send(
            websocket,
            {
                "type": "error",
                "detail": (
                    "I didn't catch that. Let's give that answer another go."
                ),
                "retryable": True,
            },
        )
        await _close(websocket)
        return

    audio_url = await _archive_audio(
        blob_storage_service, question_id, b"".join(chunks)
    )

    try:
        result = await _submit_answer(
            interview_id=interview_id,
            question_id=question_id,
            audio_url=audio_url,
            transcript=transcript,
        )

        next_question = result.next_question

        line = await _compose_line(
            interview_id=interview_id,
            moment=(
                ConversationMoment.CLOSING
                if next_question is None
                else ConversationMoment.TRANSITION
            ),
            last_question=question_text,
            last_answer=transcript,
            next_question=(
                next_question.question_text
                if next_question is not None
                else None
            ),
            next_is_follow_up=(
                next_question.is_follow_up
                if next_question is not None
                else False
            ),
        )

        await _send(
            websocket,
            {
                "type": "stored",
                "transcript": transcript,
                "audioUrl": audio_url,
                "followUpGenerated": result.follow_up_generated,
                "interviewCompleted": result.interview_completed,
                "nextQuestion": (
                    next_question.model_dump(mode="json")
                    if next_question is not None
                    else None
                ),
                "line": line.model_dump(mode="json"),
            },
        )
    except Exception as exc:
        logger.exception("Could not submit the streamed answer.")
        await _send(websocket, {"type": "error", "detail": str(exc)})

    await _close(websocket)


async def _archive_audio(
    blob_storage_service: BlobStorageService,
    question_id: int,
    audio_data: bytes,
) -> str | None:
    """
    Store the recording, or give up and return None.

    The transcript is what the rest of the pipeline consumes — analysis,
    follow-ups, evaluation, the report. The audio file is an archive of it.
    Losing a candidate's answer entirely because archival storage was
    unreachable is a far worse outcome than keeping the answer without its
    recording, so a failure here is logged and the turn continues.
    """

    try:
        return await asyncio.wait_for(
            run_in_threadpool(
                blob_storage_service.upload_audio,
                audio_data=audio_data,
                blob_name=(
                    f"interview-answers/question-{question_id}-{uuid4()}.webm"
                ),
                content_type="audio/webm",
            ),
            timeout=AUDIO_UPLOAD_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception(
            "Could not archive the recording for question %s; keeping the "
            "answer without it.",
            question_id,
        )
        return None


def _parse_control(text: str | None) -> str | None:
    """Read a control frame, tolerating anything that is not valid JSON."""

    if not text:
        return None

    try:
        message = json.loads(text)
    except (TypeError, ValueError):
        return None

    if not isinstance(message, dict):
        return None

    kind = message.get("type")

    return kind if isinstance(kind, str) else None


async def _publish_updates(
    websocket: WebSocket,
    updates: "asyncio.Queue[tuple[str, bool]]",
    analyzer: TurnCompletenessAnalyzer,
) -> None:
    """Forward each transcript update, followed by the threshold it implies."""

    last_threshold: float | None = None

    try:
        while True:
            transcript, is_final = await updates.get()

            await websocket.send_json(
                {
                    "type": "transcript",
                    "text": transcript,
                    "isFinal": is_final,
                }
            )

            assessment = analyzer.assess(transcript)

            # Only speak up when the guidance actually changes.
            if assessment.silence_threshold_seconds != last_threshold:
                last_threshold = assessment.silence_threshold_seconds

                await websocket.send_json(
                    {
                        "type": "endpoint",
                        "silenceThresholdSeconds": (
                            assessment.silence_threshold_seconds
                        ),
                        "state": assessment.state.value,
                        "reason": assessment.reason,
                    }
                )
    except asyncio.CancelledError:
        raise
    except Exception:
        # The socket went away mid-send. The receive loop notices too, and
        # owns the teardown; this task just stops.
        logger.debug("Stopped publishing turn updates.", exc_info=True)


async def _send(websocket: WebSocket, payload: dict) -> None:
    """Send, tolerating a socket the client has already dropped."""

    try:
        await websocket.send_json(payload)
    except Exception:
        logger.debug("Could not send on a closed socket.", exc_info=True)


async def _close(websocket: WebSocket) -> None:
    try:
        await websocket.close()
    except Exception:
        logger.debug("Could not close an already-closed socket.", exc_info=True)
