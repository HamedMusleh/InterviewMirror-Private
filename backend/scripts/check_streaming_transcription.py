"""
Step 4 - does the live streaming path work, and is it actually live?

Feeds a real webm/opus file into StreamingTranscriptionSession in small
chunks at roughly recording speed, imitating what MediaRecorder sends with a
250ms timeslice. Nothing is mocked.

Two separate properties are under test, and a run can pass one and fail the
other:

  live       results arrive *during* the stream. Turn detection reasons about
             the transcript while the candidate is still talking, so a
             transcript that only appears at the end is useless to it.

  complete   the final transcript covers the whole recording. Audio is
             written faster than Azure transcribes it, so ending the session
             without letting it drain silently discards the tail.

Each partial is printed with the silence threshold the turn analyzer assigned
to it, which is also a live demonstration of the endpointing logic.

    python scripts/check_streaming_transcription.py                   # fixture
    python scripts/check_streaming_transcription.py path/to/audio.webm
"""

import sys
import time
from pathlib import Path

from _speech_env import FIXTURE_DIR, import_app_modules, setup


# ~250ms of 32 kbit/s Opus, matching the browser's timeslice.
CHUNK_BYTES = 2400
CHUNK_DELAY_SECONDS = 0.25


def expected_text_for(audio_path: Path) -> str | None:
    for candidate in (
        audio_path.with_suffix(audio_path.suffix + ".expected.txt"),
        audio_path.with_suffix(".expected.txt"),
    ):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")

    return None


def main() -> int:
    _, region, has_gstreamer = setup()

    audio_path = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else FIXTURE_DIR / "answer_long.webm"
    )

    if not audio_path.is_file():
        print(f"No such file: {audio_path}")
        print("Run scripts/make_speech_fixtures.py first.")
        return 1

    print(f"region    : {region}")
    print(f"gstreamer : {'found' if has_gstreamer else 'MISSING'}")

    if not has_gstreamer:
        return 1

    import_app_modules()

    from app.services.streaming_transcription_service import (
        StreamingTranscriptionSession,
        build_push_stream,
        build_recognizer,
    )
    from app.services.turn_completeness_service import TurnCompletenessAnalyzer

    analyzer = TurnCompletenessAnalyzer()
    started = time.monotonic()
    arrival_times: list[float] = []

    def on_transcript(text: str, is_final: bool) -> None:
        elapsed = time.monotonic() - started
        arrival_times.append(elapsed)

        assessment = analyzer.assess(text)

        print(
            f"  [{elapsed:5.1f}s] {'FINAL  ' if is_final else 'partial'} "
            f"{len(text.split()):>3}w  "
            f"wait={assessment.silence_threshold_seconds:.1f}s "
            f"({assessment.state.value})"
        )

    push_stream = build_push_stream()
    session = StreamingTranscriptionSession(
        recognizer=build_recognizer(push_stream),
        push_stream=push_stream,
        on_transcript=on_transcript,
    )
    session.start()

    data = audio_path.read_bytes()
    chunks = [
        data[offset : offset + CHUNK_BYTES]
        for offset in range(0, len(data), CHUNK_BYTES)
    ]

    print(f"streaming : {len(chunks)} chunks of ~{CHUNK_BYTES} bytes")
    print()

    for chunk in chunks:
        session.write(chunk)
        time.sleep(CHUNK_DELAY_SECONDS)

    feed_seconds = time.monotonic() - started

    print()
    print(f"sent everything after {feed_seconds:.1f}s; draining...")

    try:
        transcript = session.stop()
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        return 1

    print()
    print(f"FINAL TRANSCRIPT ({len(transcript.split())} words):")
    print()
    print(f"  {transcript}")
    print()

    failures = 0

    mid_stream = [t for t in arrival_times if t < feed_seconds - 0.5]

    print("CHECKS")
    print(f"  updates            : {len(arrival_times)}")
    print(f"  arrived mid-stream : {len(mid_stream)}")

    if mid_stream:
        print(f"  first result at    : {mid_stream[0]:.1f}s")
        print("  -> LIVE")
    else:
        print("  -> NOT LIVE: nothing arrived until the stream ended")
        failures += 1

    expected = expected_text_for(audio_path)

    if expected is not None:
        expected_words = len(expected.split())
        actual_words = len(transcript.split())
        ratio = actual_words / expected_words if expected_words else 0

        print(f"  expected           : {expected_words} words")
        print(f"  transcribed        : {actual_words} words ({ratio:.0%})")

        if ratio >= 0.8:
            print("  -> COMPLETE")
        else:
            print("  -> TRUNCATED: audio was dropped before it was recognised")
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
