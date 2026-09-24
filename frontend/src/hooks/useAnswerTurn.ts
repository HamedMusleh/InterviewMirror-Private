/**
 * Turn-taking for a single interview answer.
 *
 * Brings together the two halves of the decision. The detector reports, from
 * the audio, whether the candidate is speaking. The server reports, from the
 * transcript, how much silence should count as finished. This hook holds the
 * clock between them.
 *
 * The key UX property: the wait is *visible and cancellable*. When silence
 * begins, a countdown starts and its duration is the current threshold, so
 * the candidate can see they are about to be moved on. Speaking again
 * cancels it instantly and costs nothing. That is what makes an occasional
 * wrong detection harmless rather than destructive — a mistake shows up as a
 * progress ring that fills partway and resets, not as a truncated answer.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import {
  AnswerStreamClient,
  type AnswerStreamEvent,
  type StreamedQuestion,
} from '../services/answerStreamClient'
import type { ConversationLine } from '../services/interviewConversationApi'
import { VoiceActivityDetector } from '../services/voiceActivityDetector'

export type TurnPhase =
  | 'idle'
  | 'connecting'
  | 'waiting'
  | 'speaking'
  | 'confirming'
  | 'saving'
  | 'saved'
  | 'error'

export interface AnswerTurnState {
  phase: TurnPhase
  transcript: string
  /** 0..1 through the silence countdown; 0 when not counting down. */
  confirmProgress: number
  /** Input level, 0..1, for a live meter. */
  level: number
  error: string | null
}

/**
 * What the interview flow decided once the answer was submitted: whether it
 * generated a follow-up, which question comes next, and whether that was the
 * last one.
 */
export interface AnswerTurnOutcome {
  transcript: string
  followUpGenerated: boolean
  interviewCompleted: boolean
  nextQuestion: StreamedQuestion | null
  /** What the interviewer says next, written while the answer was stored. */
  line: ConversationLine | null
}

/** Chunk cadence: small enough to feel live, large enough to stay efficient. */
const CHUNK_INTERVAL_MS = 250

/**
 * Used until the server has seen any transcript at all.
 *
 * Midway between the 4s this started at and the 6s it was raised to, in step
 * with the server's own thresholds. It only governs the window before the
 * first words are recognised, after which the server's adaptive figure takes
 * over.
 */
const INITIAL_THRESHOLD_SECONDS = 5

/**
 * Never end a turn before the candidate has actually said something.
 *
 * Generous, because the sounds this is meant to disregard are short: a
 * notification chime, a door, a chair. A real answer clears it in the first
 * few words.
 *
 * Midway between the 700ms this started at and the 1200ms it was raised to.
 * It adds to how long a short answer takes to submit, so it moves with the
 * silence thresholds rather than being tuned on its own.
 */
const MIN_SPEECH_BEFORE_END_MS = 950

/** Nominal frame interval, used only to accumulate rough speech duration. */
const FRAME_MS = 16

export function useAnswerTurn(
  onFinished?: (outcome: AnswerTurnOutcome) => void,
) {
  const [state, setState] = useState<AnswerTurnState>({
    phase: 'idle',
    transcript: '',
    confirmProgress: 0,
    level: 0,
    error: null,
  })

  const clientRef = useRef<AnswerStreamClient | null>(null)
  const detectorRef = useRef<VoiceActivityDetector | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const frameRef = useRef<number | null>(null)

  const thresholdRef = useRef(INITIAL_THRESHOLD_SECONDS)
  const speechMsRef = useRef(0)

  /*
   * The transcript, mirrored for the frame loop.
   *
   * Read every frame by `tick`, which cannot depend on React state without
   * being rebuilt on every partial result the recogniser sends.
   */
  const transcriptRef = useRef('')
  const finishedRef = useRef(false)
  const mutedRef = useRef(false)
  const onFinishedRef = useRef(onFinished)

  useEffect(() => {
    onFinishedRef.current = onFinished
  }, [onFinished])

  const patch = useCallback((changes: Partial<AnswerTurnState>) => {
    setState((previous) => ({ ...previous, ...changes }))
  }, [])

  const teardown = useCallback(() => {
    if (frameRef.current !== null) {
      cancelAnimationFrame(frameRef.current)
      frameRef.current = null
    }

    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop()
    }
    recorderRef.current = null

    detectorRef.current?.dispose()
    detectorRef.current = null

    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null

    clientRef.current?.close()
    clientRef.current = null
  }, [])

  /** Signal that the answer is complete and let the server store it. */
  const finish = useCallback(() => {
    if (finishedRef.current) {
      return
    }

    finishedRef.current = true

    if (frameRef.current !== null) {
      cancelAnimationFrame(frameRef.current)
      frameRef.current = null
    }

    patch({ phase: 'saving', confirmProgress: 0 })

    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop()
    }

    clientRef.current?.finish()
  }, [patch])

  /**
   * The clock. Runs each frame while a turn is live, comparing how long the
   * candidate has been silent against the threshold the server last sent.
   */
  const tick = useCallback(() => {
    const detector = detectorRef.current

    if (!detector || finishedRef.current) {
      return
    }

    // While muted the microphone produces silence by definition, so the
    // countdown has to stop as well - otherwise muting would end the turn.
    if (mutedRef.current) {
      frameRef.current = requestAnimationFrame(tick)
      return
    }

    if (detector.isSpeaking) {
      // Still talking. Accumulate speech time and clear any countdown.
      speechMsRef.current += FRAME_MS

      setState((previous) =>
        previous.phase === 'speaking' && previous.confirmProgress === 0
          ? previous
          : { ...previous, phase: 'speaking', confirmProgress: 0 },
      )

      frameRef.current = requestAnimationFrame(tick)
      return
    }

    const silenceMs = detector.silenceDurationMs

    /*
     * A turn may only end on words that were actually recognised.
     *
     * Acoustic energy is not evidence that the candidate spoke. A
     * notification chime, a colleague talking nearby, audio leaking from
     * headphones — all of it clears the detector's bar, and ending a turn on
     * any of it submits an answer with nothing in it. The server then cannot
     * transcribe that recording either, and the candidate is shown a failure
     * they had no part in causing.
     *
     * Requiring recognised text costs a real answer nothing, because a real
     * answer always has some by the time the speaker pauses.
     */
    const hasWords = transcriptRef.current.trim().length > 0

    // Null silence means no speech has been detected at all yet, which is a
    // different thing from a pause: the candidate is still reading the
    // question, and no countdown should be running.
    const hasSpokenEnough =
      silenceMs !== null &&
      hasWords &&
      speechMsRef.current >= MIN_SPEECH_BEFORE_END_MS

    if (hasSpokenEnough) {
      const thresholdMs = Math.max(thresholdRef.current, 0.1) * 1000
      const progress = Math.min(1, silenceMs / thresholdMs)

      if (progress >= 1) {
        finish()
        return
      }

      setState((previous) => ({
        ...previous,
        phase: 'confirming',
        confirmProgress: progress,
      }))
    }

    frameRef.current = requestAnimationFrame(tick)
  }, [finish])

  const handleEvent = useCallback(
    (event: AnswerStreamEvent) => {
      if (event.type === 'transcript') {
        transcriptRef.current = event.text
        patch({ transcript: event.text })
        return
      }

      if (event.type === 'endpoint') {
        thresholdRef.current = event.silenceThresholdSeconds
        return
      }

      if (event.type === 'stored') {
        patch({
          phase: 'saved',
          transcript: event.transcript,
          confirmProgress: 0,
        })

        onFinishedRef.current?.({
          transcript: event.transcript,
          followUpGenerated: event.followUpGenerated,
          interviewCompleted: event.interviewCompleted,
          nextQuestion: event.nextQuestion,
          line: event.line ?? null,
        })

        teardown()
        return
      }

      if (event.type === 'error') {
        patch({ phase: 'error', error: event.detail, confirmProgress: 0 })
        teardown()
      }
    },
    [patch, teardown],
  )

  const start = useCallback(
    async (questionId: number, deviceId?: string) => {
      finishedRef.current = false
      speechMsRef.current = 0
      transcriptRef.current = ''
      mutedRef.current = false
      thresholdRef.current = INITIAL_THRESHOLD_SECONDS

      setState({
        phase: 'connecting',
        transcript: '',
        confirmProgress: 0,
        level: 0,
        error: null,
      })

      try {
        /*
         * `voiceIsolation` asks the browser to separate the person at the
         * microphone from everything else in the room — other voices,
         * background audio. It is stated as `ideal` rather than required so
         * a browser without it carries on rather than refusing the
         * microphone outright, and it is unknown to older TypeScript DOM
         * types, hence the cast.
         */
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            deviceId: deviceId ? { exact: deviceId } : undefined,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            voiceIsolation: { ideal: true },
          } as MediaTrackConstraints,
        })

        streamRef.current = stream

        const client = new AnswerStreamClient(handleEvent)
        await client.connect(questionId)
        clientRef.current = client

        const detector = new VoiceActivityDetector({
          onLevel: (level) => patch({ level }),
        })

        await detector.attach(stream)
        detectorRef.current = detector

        const mimeType = MediaRecorder.isTypeSupported(
          'audio/webm;codecs=opus',
        )
          ? 'audio/webm;codecs=opus'
          : 'audio/webm'

        const recorder = new MediaRecorder(stream, { mimeType })

        recorder.ondataavailable = (chunkEvent) => {
          void client.sendAudio(chunkEvent.data)
        }

        recorder.start(CHUNK_INTERVAL_MS)
        recorderRef.current = recorder

        patch({ phase: 'waiting' })

        frameRef.current = requestAnimationFrame(tick)
      } catch (startError) {
        teardown()

        patch({
          phase: 'error',
          error:
            startError instanceof Error
              ? startError.message
              : 'Could not start recording',
        })
      }
    },
    [handleEvent, patch, teardown, tick],
  )

  /**
   * Mute or unmute the microphone for real.
   *
   * Disabling the track makes the browser emit silence rather than dropping
   * frames, so the recording stays continuous and nothing is captured while
   * muted. Turning it back on also clears the accumulated silence, so a long
   * mute does not immediately end the turn on unmute.
   */
  const setMicrophoneEnabled = useCallback((enabled: boolean) => {
    mutedRef.current = !enabled

    streamRef.current?.getAudioTracks().forEach((track) => {
      track.enabled = enabled
    })

    if (enabled) {
      detectorRef.current?.reset()
    }
  }, [])

  /** Abandon the current answer without storing it. */
  const cancel = useCallback(() => {
    finishedRef.current = true
    clientRef.current?.cancel()
    teardown()
    patch({ phase: 'idle', confirmProgress: 0 })
  }, [patch, teardown])

  useEffect(() => teardown, [teardown])

  return { ...state, start, finish, cancel, setMicrophoneEnabled }
}
