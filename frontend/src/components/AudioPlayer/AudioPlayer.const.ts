export const DEFAULT_VOLUME = 1
export const VOLUME_STEP = 0.1
export const VOLUME_MIN = 0
export const VOLUME_MAX = 1

export const PLAYBACK_STATE = {
  IDLE: 'idle',
  PLAYING: 'playing',
  PAUSED: 'paused',
  ENDED: 'ended',
  /*
   * The browser refused to start playback.
   *
   * Distinct from IDLE because the two need opposite handling: idle audio is
   * about to play, blocked audio never will. Collapsing them is what leaves a
   * candidate looking at a line of text that is never spoken, with nothing
   * on screen suggesting the interview is waiting for them.
   */
  BLOCKED: 'blocked',
} as const

export type PlaybackState =
  (typeof PLAYBACK_STATE)[keyof typeof PLAYBACK_STATE]