import type { TurnPhase } from '../../hooks/useAnswerTurn'

import styles from './TurnIndicator.module.css'

interface TurnIndicatorProps {
  phase: TurnPhase
  transcript: string
  confirmProgress: number
  level: number
  muted: boolean
  onFinish: () => void
}

type Tone = 'idle' | 'live' | 'ending' | 'fault'

interface Status {
  tone: Tone
  text: string
  hint?: string
}

/*
 * Green means the interview can hear speech right now; amber means the
 * silence countdown is running and the turn is about to end. Keeping
 * "waiting" neutral is what gives green that meaning — if the panel were
 * green from the moment the microphone opened, the colour would only be
 * telling the candidate that the page had loaded.
 */
const STATUS: Record<TurnPhase, Status> = {
  idle: { tone: 'idle', text: 'Ready when you are' },
  connecting: { tone: 'idle', text: 'Connecting…' },
  waiting: {
    tone: 'idle',
    text: 'Waiting for you to start',
    hint: 'Just begin speaking. Pause when you are finished, or press ' +
      'I’m done.',
  },
  speaking: { tone: 'live', text: 'Listening' },
  confirming: {
    tone: 'ending',
    text: 'Wrapping up your answer',
    hint: 'Keep talking if you have more to say.',
  },
  saving: { tone: 'idle', text: 'Saving your answer…' },
  saved: { tone: 'idle', text: 'Answer saved' },
  error: { tone: 'fault', text: 'Something went wrong' },
}

const MUTED_STATUS: Status = {
  tone: 'idle',
  text: 'Microphone muted',
  hint: 'Unmute to carry on with your answer.',
}

/**
 * Shows the candidate what the interview currently believes about their turn.
 *
 * The ring is the important part. It runs for exactly as long as the silence
 * threshold the server last sent, so the candidate can see the turn is about
 * to end and simply keep talking to cancel it. Making the wait visible is
 * what turns a wrong endpoint decision from a lost answer into a ring that
 * fills partway and resets.
 */
function TurnIndicator({
  phase,
  transcript,
  confirmProgress,
  level,
  muted,
  onFinish,
}: TurnIndicatorProps) {
  const isLive =
    phase === 'waiting' || phase === 'speaking' || phase === 'confirming'

  const status = muted && isLive ? MUTED_STATUS : STATUS[phase]

  // Muting stops the clock, so the ring and the level stop with it.
  const progress = muted ? 0 : confirmProgress
  const inputLevel = muted ? 0 : Math.min(Math.max(level, 0), 1)

  const radius = 20
  const circumference = 2 * Math.PI * radius

  return (
    <div className={styles.panel} data-tone={status.tone}>
      <div className={styles.header}>
        <div className={styles.dial}>
          <svg viewBox="0 0 44 44" className={styles.ring} aria-hidden="true">
            <circle className={styles.ringTrack} cx="22" cy="22" r={radius} />
            <circle
              className={styles.ringProgress}
              cx="22"
              cy="22"
              r={radius}
              strokeDasharray={circumference}
              strokeDashoffset={circumference * (1 - progress)}
            />
          </svg>

          <span
            className={styles.levelDot}
            style={{ transform: `scale(${1 + inputLevel * 0.8})` }}
          />
        </div>

        <div className={styles.status}>
          <div>
            <p className={styles.statusText} aria-live="polite">
              {status.text}
            </p>

            {status.hint && <p className={styles.hint}>{status.hint}</p>}
          </div>

          {isLive && !muted && (
            <button
              type="button"
              className={styles.doneButton}
              onClick={onFinish}
            >
              I&rsquo;m done
            </button>
          )}
        </div>
      </div>

      {(isLive || phase === 'saving') && (
        <p
          className={styles.transcript}
          aria-live="polite"
          data-empty={transcript.length === 0}
        >
          {transcript || 'Your words will appear here as you speak.'}
        </p>
      )}
    </div>
  )
}

export default TurnIndicator
