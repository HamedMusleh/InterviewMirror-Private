/**
 * What the interviewer says when it is not reading a stored question.
 *
 * The bridge between one answer and the next question does not come through
 * here — it arrives on the answer WebSocket alongside the stored answer, so
 * the candidate is not left waiting through an extra round trip at the one
 * moment they have nothing to do. This client covers the moments that are
 * not on that path: the opening, the reply to the check-in, and the close of
 * an interview that ended without a final answer.
 */

const API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api/interview-conversation`

export type ConversationMoment =
  | 'greeting'
  | 'warmup_reply'
  | 'transition'
  | 'closing'

export type LineStyle =
  | 'chat'
  | 'friendly'
  | 'cheerful'
  | 'empathetic'
  | 'hopeful'

export type LineMood =
  | 'warm'
  | 'attentive'
  | 'thoughtful'
  | 'encouraging'
  | 'neutral'

export interface ConversationLine {
  text: string
  style: LineStyle
  mood: LineMood
  /*
   * True when the interviewer has just asked the candidate something and is
   * waiting for an answer. The room listens again instead of moving on,
   * which is what lets the opening check-in be a conversation rather than a
   * single scripted exchange.
   */
  expects_reply: boolean
  /** False when the server fell back to its scripted wording. */
  generated: boolean
}

interface ConversationLineRequest {
  interview_id: number
  moment: ConversationMoment
  candidate_reply?: string
  /** How many check-in exchanges have already happened. Bounds small talk. */
  warmup_exchanges?: number
  last_question?: string
  last_answer?: string
  next_question?: string
  next_is_follow_up?: boolean
}

export async function getConversationLine(
  request: ConversationLineRequest,
): Promise<ConversationLine> {
  const response = await fetch(`${API_BASE_URL}/line`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    throw new Error('Failed to compose the interviewer line')
  }

  return (await response.json()) as ConversationLine
}
