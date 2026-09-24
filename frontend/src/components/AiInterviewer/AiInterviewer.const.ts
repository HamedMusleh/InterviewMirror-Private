/**
 * The shapes the interviewer's face can hold.
 *
 * Azure emits a viseme id for every mouth position in the audio it
 * synthesises, on the standard 0-21 scale. Each id is a phonetic class, not
 * a drawing, so this file is where the phonetics become geometry.
 *
 * Four numbers describe any mouth well enough to read as speech:
 *
 *   open   how far the jaw drops
 *   wide   how far the corners pull apart
 *   round  how far the lips purse forward, which narrows as it rises
 *   teeth  how much of the upper teeth show
 *
 * Getting a few of these slightly wrong is invisible. Getting the closures
 * wrong is not: /p/, /b/ and /m/ must reach a genuinely shut mouth, and /f/
 * and /v/ must show teeth on the lower lip, because those are the two shapes
 * a viewer can consciously spot as being out of step with the sound.
 */

export interface MouthShape {
  open: number
  wide: number
  round: number
  teeth: number
}

export const VISEME_SHAPES: Record<number, MouthShape> = {
  // silence
  0: { open: 0.0, wide: 0.3, round: 0.0, teeth: 0.0 },
  // æ, ə, ʌ
  1: { open: 0.55, wide: 0.55, round: 0.0, teeth: 0.3 },
  // ɑ — the widest open vowel
  2: { open: 0.9, wide: 0.6, round: 0.0, teeth: 0.4 },
  // ɔ
  3: { open: 0.7, wide: 0.3, round: 0.55, teeth: 0.2 },
  // ɛ, ʊ
  4: { open: 0.45, wide: 0.45, round: 0.15, teeth: 0.3 },
  // ɝ
  5: { open: 0.4, wide: 0.35, round: 0.35, teeth: 0.2 },
  // j, i, ɪ — the wide smile vowels
  6: { open: 0.28, wide: 0.82, round: 0.0, teeth: 0.5 },
  // w, u — the tightest purse
  7: { open: 0.25, wide: 0.08, round: 0.92, teeth: 0.0 },
  // o
  8: { open: 0.5, wide: 0.2, round: 0.72, teeth: 0.1 },
  // aʊ
  9: { open: 0.7, wide: 0.35, round: 0.45, teeth: 0.2 },
  // ɔɪ
  10: { open: 0.6, wide: 0.4, round: 0.45, teeth: 0.2 },
  // aɪ
  11: { open: 0.75, wide: 0.55, round: 0.05, teeth: 0.35 },
  // h
  12: { open: 0.35, wide: 0.45, round: 0.1, teeth: 0.2 },
  // ɹ
  13: { open: 0.35, wide: 0.3, round: 0.45, teeth: 0.15 },
  // l
  14: { open: 0.4, wide: 0.5, round: 0.05, teeth: 0.4 },
  // s, z — narrow, teeth nearly together
  15: { open: 0.16, wide: 0.7, round: 0.0, teeth: 0.7 },
  // ʃ, tʃ, dʒ, ʒ
  16: { open: 0.25, wide: 0.35, round: 0.55, teeth: 0.5 },
  // ð
  17: { open: 0.22, wide: 0.55, round: 0.0, teeth: 0.6 },
  // f, v — lower lip against the upper teeth
  18: { open: 0.14, wide: 0.55, round: 0.05, teeth: 0.78 },
  // d, t, n, θ
  19: { open: 0.3, wide: 0.55, round: 0.0, teeth: 0.5 },
  // k, g, ŋ
  20: { open: 0.38, wide: 0.45, round: 0.05, teeth: 0.3 },
  // p, b, m — must actually close
  21: { open: 0.0, wide: 0.4, round: 0.05, teeth: 0.0 },
}

export const SILENT_MOUTH: MouthShape = VISEME_SHAPES[0]

export type InterviewerState =
  | 'idle'
  | 'greeting'
  | 'speaking'
  | 'listening'
  | 'thinking'

export type InterviewerMood =
  | 'warm'
  | 'attentive'
  | 'thoughtful'
  | 'encouraging'
  | 'neutral'

export interface MoodExpression {
  /** Upward brow travel in SVG units. Negative lowers them. */
  brow: number
  /** Corner lift of the resting mouth, 0..1. */
  smile: number
  /** Resting head tilt in degrees. */
  tilt: number
}

export const MOOD_EXPRESSIONS: Record<InterviewerMood, MoodExpression> = {
  warm: { brow: 1.2, smile: 0.75, tilt: 0 },
  attentive: { brow: 1.8, smile: 0.3, tilt: 2.5 },
  thoughtful: { brow: -0.8, smile: 0.12, tilt: -3 },
  encouraging: { brow: 2.2, smile: 0.6, tilt: 1.5 },
  neutral: { brow: 0, smile: 0.25, tilt: 0 },
}

/*
 * How quickly the drawn mouth chases the shape the timeline asks for.
 *
 * Snapping straight to each viseme looks mechanical, because real lips have
 * mass. Too much smoothing and the closures never arrive, which is the
 * failure that reads as bad dubbing. Roughly 55ms of lag is the window where
 * the motion looks physical and /p/ still lands shut.
 */
export const MOUTH_SMOOTHING_MS = 55

/** Blink timing, in milliseconds. */
export const BLINK_DURATION_MS = 130
export const BLINK_INTERVAL_MIN_MS = 2200
export const BLINK_INTERVAL_MAX_MS = 6200

/** How often the eyes shift where they are looking, in milliseconds. */
export const SACCADE_INTERVAL_MIN_MS = 1400
export const SACCADE_INTERVAL_MAX_MS = 4200
