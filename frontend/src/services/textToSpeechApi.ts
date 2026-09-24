const API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api/speech`

export async function getQuestionAudio(
  text: string,
): Promise<Blob> {
  const response = await fetch(API_BASE_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  })

  if (!response.ok) {
    throw new Error('Failed to generate question audio')
  }

  return response.blob()
}

/** One mouth shape and the moment in the audio it belongs to. */
export interface VisemeMark {
  viseme_id: number
  offset_ms: number
}

export interface WordMark {
  text: string
  offset_ms: number
  duration_ms: number
}

/** Audio the interviewer speaks, with the movement that goes on top of it. */
export interface SpokenLine {
  audioUrl: string
  durationMs: number
  visemes: VisemeMark[]
  words: WordMark[]
}

interface SpokenLineResponse {
  audio_base64: string
  audio_mime_type: string
  duration_ms: number
  visemes: VisemeMark[]
  words: WordMark[]
}

/**
 * Fetch a line to speak, together with its mouth movement.
 *
 * `then` is spoken after a real pause. It is how the interviewer's own words
 * are kept audibly separate from the question it goes on to read: run
 * together they land as one breathless announcement, while a beat between
 * them lets the first part read as a response to what the candidate just
 * said.
 *
 * The caller owns the returned object URL and must revoke it. Decoding
 * base64 here rather than taking a second binary response keeps the marks
 * attached to the exact audio they were measured against, which is what
 * stops the mouth drifting out of sync after a retry.
 */
/*
 * How long to wait for synthesis before giving up on it.
 *
 * Synthesis normally lands in two to five seconds. Without a ceiling, a
 * request that never returns leaves the room showing "Thinking" forever,
 * because the loading flag is only ever cleared by the fetch settling.
 * Failing at twenty seconds turns a hang into a readable question with no
 * audio, which is a far better outcome than a frozen screen.
 */
const SYNTHESIS_TIMEOUT_MS = 20_000

export async function getSpokenLine(
  text: string,
  style = 'chat',
  then?: string,
): Promise<SpokenLine> {
  const response = await fetch(`${API_BASE_URL}/line`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text, style, then: then || null }),
    signal: AbortSignal.timeout(SYNTHESIS_TIMEOUT_MS),
  })

  if (!response.ok) {
    throw new Error(
      `Failed to generate the interviewer audio (${response.status})`,
    )
  }

  const payload = (await response.json()) as SpokenLineResponse

  return {
    audioUrl: URL.createObjectURL(
      decodeAudio(payload.audio_base64, payload.audio_mime_type),
    ),
    durationMs: payload.duration_ms,
    visemes: payload.visemes ?? [],
    words: payload.words ?? [],
  }
}

function decodeAudio(base64: string, mimeType: string): Blob {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }

  return new Blob([bytes], { type: mimeType })
}
