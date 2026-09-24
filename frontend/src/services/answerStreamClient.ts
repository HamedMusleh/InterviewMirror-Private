/**
 * WebSocket client for the live answer channel.
 *
 * Sends audio chunks up as they are recorded and receives two things back:
 * the transcript as it is recognised, and the silence threshold the server
 * thinks the current transcript deserves. The threshold is advice, not a
 * command — the browser is the one holding the clock.
 */

import type { ConversationLine } from './interviewConversationApi'

/** An interview question as the flow returns it. */
export interface StreamedQuestion {
  id: number
  interview_id: number
  question_text: string
  question_type: string
  skill: string | null
  sequence_number: number
  is_follow_up: boolean
  parent_question_id: number | null
}

export type AnswerStreamEvent =
  | { type: 'ready' }
  | { type: 'transcript'; text: string; isFinal: boolean }
  | {
      type: 'endpoint'
      silenceThresholdSeconds: number
      state: string
      reason: string
    }
  | {
      type: 'stored'
      transcript: string
      audioUrl: string
      /** True when the answer earned an adaptive follow-up question. */
      followUpGenerated: boolean
      /** True when that was the last question in the interview. */
      interviewCompleted: boolean
      /** The question to ask next, resolved by the server. */
      nextQuestion: StreamedQuestion | null
      /*
       * What the interviewer says before that question: the bridge out of
       * the answer just given, or the closing if there is no next question.
       *
       * It rides along with the stored answer rather than being fetched
       * afterwards. This is the one moment in an interview when the
       * candidate has finished talking and has nothing to do, so a second
       * round trip here is felt more than anywhere else.
       */
      line: ConversationLine | null
    }
  | {
      type: 'error'
      detail: string
      /*
       * True when going again is worth a try — most often the recogniser
       * hearing nothing usable. Distinguishes "that did not work, have
       * another go" from a genuine fault.
       */
      retryable?: boolean
    }

function buildSocketUrl(questionId: number): string {
  const base = import.meta.env.VITE_API_BASE_URL

  // Every service in this app is configured the same way, and `.env` is not
  // committed. Falling back to the page's own origin would silently point
  // the socket at the Vite dev server instead of the API, which fails in a
  // way that looks like a backend problem, so fail here instead.
  if (!base) {
    throw new Error(
      'VITE_API_BASE_URL is not set. Add it to frontend/.env, ' +
        'e.g. VITE_API_BASE_URL=http://127.0.0.1:8000',
    )
  }

  const url = new URL(`/api/interview-stream/answers/${questionId}`, base)

  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'

  return url.toString()
}

export class AnswerStreamClient {
  private socket: WebSocket | null = null

  constructor(private readonly onEvent: (event: AnswerStreamEvent) => void) {}

  get isOpen(): boolean {
    return this.socket?.readyState === WebSocket.OPEN
  }

  /** Open the channel and resolve once the server is ready for audio. */
  connect(questionId: number): Promise<void> {
    return new Promise((resolve, reject) => {
      let settled = false

      const socket = new WebSocket(buildSocketUrl(questionId))
      socket.binaryType = 'arraybuffer'

      socket.onmessage = (message) => {
        let event: AnswerStreamEvent

        try {
          event = JSON.parse(message.data as string)
        } catch {
          return
        }

        if (event.type === 'ready' && !settled) {
          settled = true
          resolve()
        }

        if (event.type === 'error' && !settled) {
          settled = true
          reject(new Error(event.detail))
        }

        this.onEvent(event)
      }

      socket.onerror = () => {
        if (!settled) {
          settled = true
          reject(new Error('Could not reach the interview audio service'))
        }
      }

      socket.onclose = () => {
        if (!settled) {
          settled = true
          reject(new Error('The interview audio connection closed'))
        }

        this.socket = null
      }

      this.socket = socket
    })
  }

  async sendAudio(chunk: Blob): Promise<void> {
    if (!this.isOpen || chunk.size === 0) {
      return
    }

    const buffer = await chunk.arrayBuffer()

    // Re-check: the socket may have closed while the blob was being read,
    // and sending on a closed socket throws.
    if (this.isOpen) {
      this.socket?.send(buffer)
    }
  }

  /** Tell the server the answer is finished and should be stored. */
  finish(): void {
    this.sendControl('stop')
  }

  /** Abandon the answer without storing it. */
  cancel(): void {
    this.sendControl('cancel')
  }

  close(): void {
    this.socket?.close()
    this.socket = null
  }

  private sendControl(type: 'stop' | 'cancel'): void {
    if (this.isOpen) {
      this.socket?.send(JSON.stringify({ type }))
    }
  }
}
