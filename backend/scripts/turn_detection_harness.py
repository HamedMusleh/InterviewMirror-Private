"""
Step 5 - watch turn detection work, live, with your own voice.

A browser page and a WebSocket. No database, no blob storage.

Runs the real StreamingTranscriptionSession and the real
TurnCompletenessAnalyzer against your microphone, and serves a page that
runs the real AudioWorklet — the worklet source is extracted straight out of
voiceActivityDetector.ts at request time, so what you see here is the code
that ships, not a copy of it that can drift.

What it lets you watch, live:

  * the input level and the speech/silence decision from the VAD
  * the transcript arriving while you are still talking
  * the silence threshold changing as the sentence becomes finished or
    unfinished, with the reason the analyzer gave
  * the countdown filling, and cancelling the moment you speak again

    python scripts/turn_detection_harness.py    then open
    http://127.0.0.1:8900
"""

import asyncio
import re
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from starlette.concurrency import run_in_threadpool

from _speech_env import REPO_ROOT, import_app_modules, setup


VAD_SOURCE_FILE = (
    REPO_ROOT / "frontend" / "src" / "services" / "voiceActivityDetector.ts"
)


def extract_worklet_source() -> str:
    """Pull the worklet out of the TypeScript module that ships it."""

    text = VAD_SOURCE_FILE.read_text(encoding="utf-8")

    match = re.search(
        r"const WORKLET_SOURCE = `(.*?)`\n", text, re.DOTALL
    )

    if match is None:
        raise SystemExit(
            f"Could not find WORKLET_SOURCE in {VAD_SOURCE_FILE}"
        )

    return match.group(1)


PAGE = """
<!doctype html>
<meta charset="utf-8">
<title>Turn detection harness</title>
<style>
  :root { color-scheme: dark; }
  body {
    margin: 0; padding: 32px; background: #0d1117; color: #e6edf3;
    font: 15px/1.6 system-ui, sans-serif;
  }
  main { max-width: 720px; margin: 0 auto; display: grid; gap: 20px; }
  h1 { font-size: 20px; margin: 0; font-weight: 600; }
  .hint { margin: 0; color: #8b949e; font-size: 14px; }
  button {
    font: inherit; padding: 10px 18px; border-radius: 6px; cursor: pointer;
    border: 1px solid #30363d; background: #21262d; color: inherit;
  }
  button:hover { background: #30363d; }
  .row { display: flex; align-items: center; gap: 16px; }
  .dial { position: relative; width: 72px; height: 72px; flex: none; }
  .dial svg { position: absolute; inset: 0; transform: rotate(-90deg); }
  .track { fill: none; stroke: #30363d; stroke-width: 4; }
  .prog  { fill: none; stroke: #d29922; stroke-width: 4; stroke-linecap: round;
           transition: stroke-dashoffset 60ms linear; }
  .dot {
    position: absolute; inset: 0; margin: auto; width: 16px; height: 16px;
    border-radius: 50%; background: #3fb950; transition: transform 80ms;
  }
  .dot.quiet { background: #6e7681; }
  .panel {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 8px; padding: 16px;
  }
  .label {
    font-size: 11px; text-transform: uppercase; letter-spacing: .1em;
    color: #8b949e; margin: 0 0 6px;
  }
  #transcript { margin: 0; min-height: 4em; }
  #transcript.empty { color: #6e7681; font-style: italic; }
  .threshold { display: flex; gap: 20px; align-items: baseline; }
  #seconds {
    font: 600 30px ui-monospace, monospace; color: #d29922;
    font-variant-numeric: tabular-nums;
  }
  #state { font: 600 13px ui-monospace, monospace; text-transform: uppercase; }
  #reason { margin: 8px 0 0; color: #8b949e; font-size: 13px; }
  .incomplete { color: #d29922; }
  .complete   { color: #3fb950; }
  .neutral    { color: #58a6ff; }
  .empty      { color: #8b949e; }
  #log {
    font: 12px/1.7 ui-monospace, monospace; color: #8b949e;
    max-height: 180px; overflow-y: auto; margin: 0; white-space: pre-wrap;
  }
</style>

<main>
  <div>
    <h1>Turn detection harness</h1>
    <p class="hint">
      Speak a sentence, then pause. Watch the threshold change depending on
      whether you stopped mid-thought or finished cleanly. Try ending on
      &ldquo;and then&hellip;&rdquo; versus a full sentence.
    </p>
  </div>

  <div class="row">
    <button id="toggle">Start listening</button>
    <div class="dial">
      <svg viewBox="0 0 72 72">
        <circle class="track" cx="36" cy="36" r="32"></circle>
        <circle class="prog" id="ring" cx="36" cy="36" r="32"
                stroke-dasharray="201" stroke-dashoffset="201"></circle>
      </svg>
      <span class="dot quiet" id="dot"></span>
    </div>
    <span id="status" class="hint">idle</span>
  </div>

  <div class="panel">
    <p class="label">Silence required before the turn ends</p>
    <div class="threshold">
      <span id="seconds">&mdash;</span>
      <span id="state" class="empty">waiting</span>
    </div>
    <p id="reason">Start listening and say something.</p>
  </div>

  <div class="panel">
    <p class="label">Live transcript</p>
    <p id="transcript" class="empty">Nothing yet.</p>
  </div>

  <div class="panel">
    <p class="label">Events</p>
    <pre id="log"></pre>
  </div>
</main>

<script type="module">
const CIRCUMFERENCE = 2 * Math.PI * 32;

const els = {
  toggle: document.getElementById('toggle'),
  ring: document.getElementById('ring'),
  dot: document.getElementById('dot'),
  status: document.getElementById('status'),
  seconds: document.getElementById('seconds'),
  state: document.getElementById('state'),
  reason: document.getElementById('reason'),
  transcript: document.getElementById('transcript'),
  log: document.getElementById('log'),
};

let running = false;
let socket, context, recorder, stream, node;
let speaking = false;
let silenceSince = null;
let thresholdSeconds = 4;
let speechMs = 0;
let frame;

function log(message) {
  const time = new Date().toLocaleTimeString();
  els.log.textContent = `[${time}] ${message}\\n` + els.log.textContent;
}

function setRing(progress) {
  els.ring.style.strokeDashoffset = String(CIRCUMFERENCE * (1 - progress));
}

async function start() {
  stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });

  socket = new WebSocket(`ws://${location.host}/ws`);
  await new Promise((resolve, reject) => {
    socket.onopen = resolve;
    socket.onerror = () => reject(new Error('socket failed'));
  });

  socket.onmessage = (message) => {
    const event = JSON.parse(message.data);

    if (event.type === 'transcript') {
      els.transcript.textContent = event.text || 'Nothing yet.';
      els.transcript.classList.toggle('empty', !event.text);
    }

    if (event.type === 'endpoint') {
      thresholdSeconds = event.silenceThresholdSeconds;
      els.seconds.textContent = thresholdSeconds.toFixed(1) + 's';
      els.state.textContent = event.state;
      els.state.className = event.state;
      els.reason.textContent = event.reason;
      log(`threshold -> ${thresholdSeconds}s (${event.state}: ${event.reason})`);
    }

    if (event.type === 'error') log('ERROR ' + event.detail);
  };

  context = new AudioContext();
  await context.audioWorklet.addModule('/vad-worklet.js');

  node = new AudioWorkletNode(context, 'vad-processor', {
    numberOfInputs: 1,
    numberOfOutputs: 0,
    processorOptions: {
      onsetMarginDb: 10, offsetMarginDb: 6, onsetFrames: 3, offsetFrames: 5,
    },
  });

  node.port.onmessage = ({ data }) => {
    if (data.type === 'speech-start') {
      speaking = true;
      silenceSince = null;
      els.dot.classList.remove('quiet');
      els.status.textContent = 'speaking';
      log('speech started');
    } else if (data.type === 'speech-end') {
      speaking = false;
      silenceSince = performance.now();
      els.dot.classList.add('quiet');
      els.status.textContent = 'silent';
      log('speech ended');
    } else if (data.type === 'level') {
      els.dot.style.transform = `scale(${1 + Math.min(data.level, 1) * 0.9})`;
    }
  };

  context.createMediaStreamSource(stream).connect(node);

  recorder = new MediaRecorder(stream, {
    mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus' : 'audio/webm',
  });

  recorder.ondataavailable = async (event) => {
    if (socket.readyState === WebSocket.OPEN && event.data.size) {
      socket.send(await event.data.arrayBuffer());
    }
  };

  recorder.start(250);

  els.status.textContent = 'listening';
  log('listening');

  const tick = () => {
    if (!running) return;

    if (silenceSince === null) {
      speechMs += 16;
      setRing(0);
    } else if (speechMs >= 700) {
      const progress = Math.min(1, (performance.now() - silenceSince) / (thresholdSeconds * 1000));
      setRing(progress);

      if (progress >= 1) {
        log('>>> TURN ENDED');
        els.status.textContent = 'turn ended';
        stop();
        return;
      }
    }

    frame = requestAnimationFrame(tick);
  };

  frame = requestAnimationFrame(tick);
}

function stop() {
  running = false;
  els.toggle.textContent = 'Start listening';

  if (frame) cancelAnimationFrame(frame);
  if (recorder && recorder.state === 'recording') recorder.stop();
  if (stream) stream.getTracks().forEach((t) => t.stop());
  if (node) node.port.onmessage = null;
  if (context) context.close();
  if (socket && socket.readyState === WebSocket.OPEN) socket.close();

  setRing(0);
  els.dot.classList.add('quiet');
  speaking = false;
  silenceSince = null;
  speechMs = 0;
}

els.toggle.onclick = async () => {
  if (running) { stop(); els.status.textContent = 'stopped'; return; }

  running = true;
  els.toggle.textContent = 'Stop';
  els.log.textContent = '';

  try {
    await start();
  } catch (error) {
    log('failed to start: ' + error.message);
    stop();
  }
};
</script>
"""


setup()
import_app_modules()

from app.services.streaming_transcription_service import (  # noqa: E402
    StreamingTranscriptionSession,
    build_push_stream,
    build_recognizer,
)
from app.services.turn_completeness_service import (  # noqa: E402
    TurnCompletenessAnalyzer,
)


app = FastAPI()
analyzer = TurnCompletenessAnalyzer()


@app.get("/")
def index() -> HTMLResponse:
    return HTMLResponse(PAGE)


@app.get("/vad-worklet.js")
def worklet() -> Response:
    return Response(
        extract_worklet_source(),
        media_type="application/javascript",
    )


@app.websocket("/ws")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()

    loop = asyncio.get_running_loop()
    updates: asyncio.Queue = asyncio.Queue()

    def on_transcript(text: str, is_final: bool) -> None:
        loop.call_soon_threadsafe(updates.put_nowait, (text, is_final))

    push_stream = build_push_stream()
    session = StreamingTranscriptionSession(
        recognizer=build_recognizer(push_stream),
        push_stream=push_stream,
        on_transcript=on_transcript,
    )
    session.start()

    async def publish() -> None:
        last = None

        while True:
            text, is_final = await updates.get()

            await websocket.send_json(
                {"type": "transcript", "text": text, "isFinal": is_final}
            )

            assessment = analyzer.assess(text)

            if assessment.silence_threshold_seconds != last:
                last = assessment.silence_threshold_seconds

                await websocket.send_json(
                    {
                        "type": "endpoint",
                        "silenceThresholdSeconds": last,
                        "state": assessment.state.value,
                        "reason": assessment.reason,
                    }
                )

    publisher = asyncio.create_task(publish())

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            chunk = message.get("bytes")

            if chunk:
                session.write(chunk)
    except WebSocketDisconnect:
        pass
    finally:
        publisher.cancel()
        await run_in_threadpool(session.stop)


if __name__ == "__main__":
    print("Turn detection harness -> http://127.0.0.1:8900")
    uvicorn.run(app, host="127.0.0.1", port=8900, log_level="warning")
