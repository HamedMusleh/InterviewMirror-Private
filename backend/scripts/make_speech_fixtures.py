"""
Step 2 - generate the audio the transcription checks run against.

Uses the project's own Azure TTS voice, so no microphone or external tooling
is involved and the expected words are known exactly. That last part is what
makes truncation measurable instead of a matter of opinion: the checks
compare the transcript against the text that was actually spoken.

Produces, in a scratch directory outside the repository:

    answer_short.mp3   a few seconds, one sentence
    answer_long.mp3    ~60s, several sentences with natural pauses
    answer_long.webm   the same audio as webm/opus, i.e. exactly what the
                       browser's MediaRecorder sends
    *.expected.txt     the words spoken, for comparison

The long fixture is the important one. A short clip passes even against a
transcriber that stops at the first pause.

    python scripts/make_speech_fixtures.py
"""

import subprocess
import sys

import azure.cognitiveservices.speech as speechsdk

from _speech_env import FIXTURE_DIR, gstreamer_launcher, setup


SHORT_TEXT = (
    "I used FastAPI to build REST APIs, and I handled dependency "
    "injection with the Depends system."
)

# Sentence breaks become real pauses in the synthesized audio, which is what
# exercises the endpointing behaviour under test.
LONG_TEXT = (
    "I would start by keeping the routers thin and putting the actual "
    "logic in services. "
    "The router declares its collaborators using Depends, so a provider "
    "builds the service and the router never constructs a repository "
    "itself. "
    "That matters for testing, because the tests can pass mocks through "
    "exactly the same constructor the provider uses. "
    "On the database side, I let the request own the transaction. "
    "Repositories flush so they can read back generated identifiers, but "
    "the commit happens once at the edge. "
    "If something fails halfway through a multi step operation, the whole "
    "thing rolls back instead of leaving half written rows behind. "
    "For storing AI generated evaluations, I would keep one row per answer "
    "holding the individual criterion scores and the weighted score, and "
    "then one aggregate row per interview. "
    "Keeping the per answer detail means the aggregate can be recomputed "
    "later if the weights ever change, rather than being a number that "
    "nobody is able to explain afterwards."
)


def synthesize(key: str, region: str, text: str, name: str) -> None:
    path = FIXTURE_DIR / f"{name}.mp3"

    config = speechsdk.SpeechConfig(subscription=key, region=region)
    config.speech_synthesis_voice_name = "en-US-JennyNeural"
    config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=config,
        audio_config=speechsdk.audio.AudioOutputConfig(filename=str(path)),
    )

    result = synthesizer.speak_text_async(text).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        details = speechsdk.SpeechSynthesisCancellationDetails(result)
        raise SystemExit(f"TTS failed: {details.reason} - {details.error_details}")

    (FIXTURE_DIR / f"{name}.expected.txt").write_text(text, encoding="utf-8")

    size = path.stat().st_size
    # 32 kbit/s mono mp3 is roughly 4 KB per second of audio.
    print(
        f"  {path.name:18} {size:>8} bytes  ~{size / 4000:5.1f}s  "
        f"{len(text.split()):>3} words"
    )


def transcode_to_webm(name: str) -> None:
    """Re-encode to webm/opus, the container the browser actually sends."""

    launcher = gstreamer_launcher()

    if launcher is None:
        print("  (GStreamer not found - skipping the webm fixture)")
        return

    source = FIXTURE_DIR / f"{name}.mp3"
    target = FIXTURE_DIR / f"{name}.webm"

    # Forward slashes: gst-launch treats a backslash as an escape inside
    # its pipeline syntax, so Windows paths have to be posix-style here.
    result = subprocess.run(
        [
            str(launcher), "-q",
            "filesrc", f"location={source.as_posix()}", "!",
            "decodebin", "!", "audioconvert", "!", "audioresample", "!",
            "opusenc", "!", "webmmux", "!",
            "filesink", f"location={target.as_posix()}",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 or not target.is_file():
        print("  (webm transcode failed - the mp3 fixtures still work)")
        print(f"  {(result.stderr or result.stdout or '').strip()[:200]}")
        return

    # The expected text is shared with the mp3 it was made from.
    (FIXTURE_DIR / f"{name}.webm.expected.txt").write_text(
        (FIXTURE_DIR / f"{name}.expected.txt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    print(f"  {target.name:18} {target.stat().st_size:>8} bytes  (webm/opus)")


def main() -> int:
    key, region, _ = setup()

    print(f"region: {region}")
    print(f"writing to: {FIXTURE_DIR}")
    print()

    synthesize(key, region, SHORT_TEXT, "answer_short")
    synthesize(key, region, LONG_TEXT, "answer_long")
    transcode_to_webm("answer_long")

    return 0


if __name__ == "__main__":
    sys.exit(main())
