"""
Step 3 - does the batch path transcribe a whole recording?

Serves an audio file over 127.0.0.1 and calls the real, unmodified
SpeechToTextService.transcribe() against that URL. Nothing is mocked, so this
exercises the same code path production does: download, push into the
compressed stream, recognise. Localhost stands in for Blob Storage, so no
storage credentials and no database are needed.

The check that matters is completeness. This is the path where a single
recognize_once call used to return only the opening sentence of a minutes-
long answer, with no error raised - so a run that transcribes a short clip
correctly proves very little. Use the long fixture.

    python scripts/check_batch_transcription.py                  # long fixture
    python scripts/check_batch_transcription.py path/to/audio.mp3
"""

import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from _speech_env import FIXTURE_DIR, import_app_modules, setup


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(directory: Path) -> tuple[ThreadingHTTPServer, int]:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=str(directory))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()

    return server, server.server_address[1]


def expected_text_for(audio_path: Path) -> str | None:
    for candidate in (
        audio_path.with_suffix(audio_path.suffix + ".expected.txt"),
        audio_path.with_suffix(".expected.txt"),
    ):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")

    return None


def report(transcript: str, expected: str | None) -> int:
    words = len(transcript.split())

    print(f"TRANSCRIPT ({words} words):")
    print()
    print(f"  {transcript}")
    print()

    if expected is None:
        print("No expected text alongside the audio - nothing to compare.")
        return 0

    expected_words = len(expected.split())
    ratio = words / expected_words if expected_words else 0

    print(f"  expected : {expected_words} words")
    print(f"  got      : {words} words ({ratio:.0%})")

    if ratio >= 0.8:
        print("  -> COMPLETE")
        return 0

    print("  -> TRUNCATED: the recording was cut short during recognition.")
    return 1


def main() -> int:
    _, region, has_gstreamer = setup()

    audio_path = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else FIXTURE_DIR / "answer_long.mp3"
    )

    if not audio_path.is_file():
        print(f"No such file: {audio_path}")
        print("Run scripts/make_speech_fixtures.py first.")
        return 1

    print(f"region    : {region}")
    print(f"gstreamer : {'found' if has_gstreamer else 'MISSING'}")

    if not has_gstreamer:
        print("GStreamer is required to decode compressed audio.")
        return 1

    import_app_modules()

    from app.services.speech_to_text_service import SpeechToTextService

    server, port = serve(audio_path.parent)
    url = f"http://127.0.0.1:{port}/{audio_path.name}"

    print(f"serving   : {url} ({audio_path.stat().st_size} bytes)")
    print()

    started = time.monotonic()

    try:
        transcript = SpeechToTextService().transcribe(url)
    except Exception as exc:
        print(f"FAILED after {time.monotonic() - started:.1f}s")
        print(f"  {type(exc).__name__}: {exc}")
        return 1
    finally:
        server.shutdown()

    print(f"(took {time.monotonic() - started:.1f}s)")
    print()

    return report(transcript, expected_text_for(audio_path))


if __name__ == "__main__":
    sys.exit(main())
