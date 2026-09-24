import base64
import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from starlette.concurrency import run_in_threadpool

from app.dependencies.text_to_speech import (
    get_text_to_speech_service,
)
from app.schemas.speech import (
    SpokenLine,
    SpokenLineRequest,
    TextToSpeechRequest,
)
from app.services.text_to_speech_service import TextToSpeechService


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/speech",
    tags=["Text to Speech"],
)


@router.post(
    "",
    summary="Convert interview question text to speech",
    response_class=Response,
    responses={
        200: {
            "content": {
                "audio/mpeg": {}
            },
            "description": "MP3 audio generated from the question text",
        }
    },
)
async def synthesize_speech(
    request: TextToSpeechRequest,
    service: TextToSpeechService = Depends(
        get_text_to_speech_service
    ),
) -> Response:
    try:
        audio_data = await run_in_threadpool(
            service.synthesize,
            request.text,
        )

        return Response(
            content=audio_data,
            media_type="audio/mpeg",
        )

    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post(
    "/line",
    summary="Speak a line and return the mouth movement that goes with it",
    response_model=SpokenLine,
)
async def synthesize_line(
    request: SpokenLineRequest,
    service: TextToSpeechService = Depends(
        get_text_to_speech_service
    ),
) -> SpokenLine:
    """
    The interview room's version of the endpoint above.

    Audio is returned base64-encoded inside JSON rather than as a binary
    body, so that the marks travel with the exact audio they describe. Two
    responses could be mismatched by a retry; one cannot.
    """

    try:
        spoken = await run_in_threadpool(
            service.synthesize_line,
            request.text,
            request.style,
            request.then,
            request.pause_ms,
        )

        return SpokenLine(
            audio_base64=base64.b64encode(spoken.audio_data).decode("ascii"),
            duration_ms=spoken.duration_ms,
            visemes=spoken.visemes,
            words=spoken.words,
        )

    except (ValueError, RuntimeError) as exc:
        # The room falls back to a silent, timed wait when this fails, so
        # the failure is close to invisible from the outside: the
        # interviewer simply never speaks and the candidate waits out a
        # countdown. Logging the cause is what makes it diagnosable.
        logger.exception(
            "Could not speak the line (style=%s, %d chars, then=%s)",
            request.style,
            len(request.text),
            "yes" if request.then else "no",
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
