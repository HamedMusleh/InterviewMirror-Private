"""
Step 1 - is Azure Speech reachable and configured correctly?

Speaks a sentence to WAV and recognises it back through Azure's native
uncompressed path. Deliberately does not touch SpeechToTextService, and
deliberately does not need GStreamer, so that a failure here means exactly
one thing: credentials, network or quota. Nothing further down is worth
debugging until this passes.

    python scripts/check_speech_service.py
"""

import sys

import azure.cognitiveservices.speech as speechsdk

from _speech_env import FIXTURE_DIR, setup


SENTENCE = (
    "I used FastAPI to build REST APIs, and I handled dependency "
    "injection with the Depends system."
)


def main() -> int:
    key, region, _ = setup()

    wav_path = FIXTURE_DIR / "speech_check.wav"

    print(f"region : {region}")

    synth_config = speechsdk.SpeechConfig(subscription=key, region=region)
    synth_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=synth_config,
        audio_config=speechsdk.audio.AudioOutputConfig(filename=str(wav_path)),
    )

    synth_result = synthesizer.speak_text_async(SENTENCE).get()

    if synth_result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        details = speechsdk.SpeechSynthesisCancellationDetails(synth_result)
        print(f"TTS FAILED: {details.reason} - {details.error_details}")
        return 1

    print(f"TTS ok : {wav_path.stat().st_size} bytes")

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speechsdk.SpeechConfig(subscription=key, region=region),
        audio_config=speechsdk.audio.AudioConfig(filename=str(wav_path)),
    )

    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print()
        print(f"  sent      : {SENTENCE}")
        print(f"  recognised: {result.text}")
        print()
        print("PASSED - credentials, network and recognition all work.")
        return 0

    if result.reason == speechsdk.ResultReason.NoMatch:
        print("NoMatch - audio reached Azure but was not understood.")
        return 1

    details = speechsdk.CancellationDetails(result)
    print(f"CANCELED: {details.reason} - {details.error_details}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
