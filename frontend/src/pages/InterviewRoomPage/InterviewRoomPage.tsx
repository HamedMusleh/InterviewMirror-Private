import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router'

import AiInterviewer from '../../components/AiInterviewer'
import type {
  InterviewerState,
} from '../../components/AiInterviewer/AiInterviewer.const'
import AudioPlayer from '../../components/AudioPlayer'
import {
  PLAYBACK_STATE,
  type PlaybackState,
} from '../../components/AudioPlayer/AudioPlayer.const'
import InterviewControls from '../../components/InterviewControls'
import InterviewQuestion from '../../components/InterviewQuestion'
import InterviewVideo from '../../components/InterviewVideo'
import TurnIndicator from '../../components/TurnIndicator/TurnIndicator'
import {
  useAnswerTurn,
  type AnswerTurnOutcome,
} from '../../hooks/useAnswerTurn'
import {
  useInterviewerVoice,
  type Utterance,
} from '../../hooks/useInterviewerVoice'
import { useAudioInputs } from '../../hooks/useAudioInputs'
import { useWarmupSpeech } from '../../hooks/useWarmupSpeech'

import {
  getConversationLine,
  type ConversationLine,
} from '../../services/interviewConversationApi'
import {
  getInterviewQuestions,
  getInterviewStatus,
  startInterview,
  type InterviewQuestionResponse,
} from '../../services/interviewQuestionsApi'

import styles from './InterviewRoomPage.module.css'

interface InterviewRoomPageProps {
  interviewId: string
}

/*
 * Where the conversation currently is.
 */
type ConversationStage =
  | 'intro'
  | 'greeting'
  | 'warmupListening'
  | 'warmupReply'
  | 'question'
  | 'closing'

/*
 * What the interviewer is called, on screen and in the fallback greeting.
 *
 * The server has the same name in its own prompts, and the two have to agree
 * -- a voice that introduces itself as one name beside a label reading
 * another is two systems, not one.
 */
const INTERVIEWER_NAME = 'Mira'

/*
 * How long a pause hands the answer back.
 *
 * Only ever spoken, never used for timing: the real threshold is adaptive
 * and comes from the server per answer. This is the round number the
 * fallback greeting quotes, matching SPOKEN_SILENCE_HINT_SECONDS on the
 * backend.
 */
const SPOKEN_SILENCE_HINT_SECONDS = 3

const FALLBACK_CLOSING: ConversationLine = {
  expects_reply: false,
  text:
    'That is everything. Thanks for your time — your answers have been ' +
    'saved.',
  style: 'friendly',
  mood: 'warm',
  generated: false,
}

const FALLBACK_GREETING: ConversationLine = {
  expects_reply: true,
  text:
    `Hi, I am ${INTERVIEWER_NAME}, an AI interviewer, and I will be ` +
    `running your interview today. When you have finished an answer, ` +
    `just stay quiet for about ` +
    `${SPOKEN_SILENCE_HINT_SECONDS} seconds and I will take it, or press ` +
    `the “I’m done” button. How are you doing?`,
  style: 'friendly',
  mood: 'warm',
  generated: false,
}

const FALLBACK_TRANSITION: ConversationLine = {
  expects_reply: false,
  text: 'Thanks. Here is the next one.',
  style: 'chat',
  mood: 'attentive',
  generated: false,
}

const FALLBACK_WARMUP_REPLY: ConversationLine = {
  expects_reply: false,
  text: 'Thanks. Let us get started.',
  style: 'chat',
  mood: 'encouraging',
  generated: false,
}

/*
 * Said when the candidate reloads mid-interview.
 *
 * Scripted rather than composed: the candidate is already staring at a blank
 * page waiting for the room to come back, and a round trip to the model to
 * write six words is the one thing that would make the wait worse.
 */
const FALLBACK_RESUME: ConversationLine = {
  expects_reply: false,
  text: 'Welcome back. Picking up where we left off.',
  style: 'chat',
  mood: 'warm',
  generated: false,
}

const MICROPHONE_LEAD_IN_MS = 400

function InterviewRoomPage({ interviewId }: InterviewRoomPageProps) {
  const [currentQuestion, setCurrentQuestion] =
    useState<InterviewQuestionResponse | null>(null)

  const [questionNumber, setQuestionNumber] =
    useState(1)
  const [plannedTotal, setPlannedTotal] =
    useState(0)

  const [cameraEnabled, setCameraEnabled] =
    useState(true)
  const [cameraStream, setCameraStream] =
    useState<MediaStream | null>(null)

  const [microphoneEnabled, setMicrophoneEnabled] =
    useState(true)
  const [elapsedTime, setElapsedTime] =
    useState(0)

  const [stage, setStage] =
    useState<ConversationStage>('intro')

  const [line, setLine] =
    useState<ConversationLine | null>(null)
  const [lineNumber, setLineNumber] =
    useState(0)

  const [playbackState, setPlaybackState] =
    useState<PlaybackState>(
      PLAYBACK_STATE.IDLE,
    )

  const [audioElement, setAudioElement] =
    useState<HTMLAudioElement | null>(null)

  const [questionDelivered, setQuestionDelivered] =
    useState(false)

  const [answerAttempt, setAnswerAttempt] =
    useState(0)

  const [microphoneId, setMicrophoneId] =
    useState('')
  const audioInputs = useAudioInputs()

  const [composing, setComposing] =
    useState(false)

  const [warmupExchanges, setWarmupExchanges] =
    useState(0)

  const [loading, setLoading] =
    useState(true)
  const [error, setError] =
    useState<string | null>(null)

  /*
   * NEW:
   * The backend tells us whether this interview is already completed.
   */
  const [interviewCompleted, setInterviewCompleted] =
    useState(false)

  /*
   * True when this interview had already been started before this page
   * loaded, which means the candidate is coming back to it rather than
   * arriving at it for the first time.
   */
  const [resuming, setResuming] =
    useState(false)

  /*
   * How many answers are already stored. Only wording depends on it; the
   * decision to resume is started_at's.
   */
  const [answeredCount, setAnsweredCount] =
    useState(0)

  /*
   * Whether the elapsed clock should be ticking. False until the interview
   * has actually been started, so a room sitting on the opening screen
   * shows 00:00 rather than counting time the candidate has not spent.
   */
  const [clockRunning, setClockRunning] =
    useState(false)

  const navigate = useNavigate()

  const numericInterviewId = Number(interviewId)

  const stopCamera = useCallback(() => {
    setCameraStream((stream) => {
      stream?.getTracks().forEach((track) => track.stop())

      return null
    })
  }, [])

  const say = useCallback(
    (
      next: ConversationLine,
      nextStage: ConversationStage,
    ) => {
      setLine(next)
      setLineNumber(
        (previous) => previous + 1,
      )
      setQuestionDelivered(false)
      setPlaybackState(
        PLAYBACK_STATE.IDLE,
      )
      setStage(nextStage)
    },
    [],
  )

  const compose = useCallback(
    async (
      request: Parameters<
        typeof getConversationLine
      >[0],
      fallback: ConversationLine,
    ): Promise<ConversationLine> => {
      setComposing(true)

      try {
        return await getConversationLine(request)
      } catch {
        return fallback
      } finally {
        setComposing(false)
      }
    },
    [],
  )

  const handleWarmupFinished = useCallback(
    (transcript: string) => {
      const respond = async () => {
        const reply = await compose(
          {
            interview_id:
              numericInterviewId,
            moment: 'warmup_reply',
            candidate_reply: transcript,
            warmup_exchanges:
              warmupExchanges,
          },
          FALLBACK_WARMUP_REPLY,
        )

        say(reply, 'warmupReply')
      }

      void respond()
    },
    [
      compose,
      numericInterviewId,
      say,
      warmupExchanges,
    ],
  )

  const warmup =
    useWarmupSpeech(handleWarmupFinished)

  const {
    start: startWarmup,
    cancel: cancelWarmup,
  } = warmup

  const handleAnswerFinished = useCallback(
    (outcome: AnswerTurnOutcome) => {
      if (
        outcome.interviewCompleted ||
        outcome.nextQuestion === null
      ) {
        setCurrentQuestion(null)
        stopCamera()
        say(
          outcome.line ??
            FALLBACK_CLOSING,
          'closing',
        )
        return
      }

      const next = outcome.nextQuestion

      setCurrentQuestion({
        id: next.id,
        interview_id: next.interview_id,
        question: next.question_text,
        question_type:
          next.question_type,
        skill: next.skill,
        sequence_number:
          next.sequence_number,
        is_follow_up:
          next.is_follow_up,
        parent_question_id:
          next.parent_question_id,
      })

      if (!next.is_follow_up) {
        setQuestionNumber(
          (previous) => previous + 1,
        )
      }

      say(
        outcome.line ??
          FALLBACK_TRANSITION,
        'question',
      )
    },
    [
      say,
      stopCamera,
    ],
  )

  const turn =
    useAnswerTurn(handleAnswerFinished)

  const {
    start: startTurn,
    cancel: cancelTurn,
    setMicrophoneEnabled:
      setTurnMicrophoneEnabled,
  } = turn

  const utterance: Utterance | null =
    useMemo(() => {
      if (!line) {
        return null
      }

      if (stage === 'question') {
        const key =
          `${lineNumber}-${currentQuestion?.id ?? 'none'}`

        const question =
          currentQuestion?.question ?? ''

        return line.text
          ? {
              key,
              text: line.text,
              then: question,
              style: line.style,
            }
          : {
              key,
              text: question,
              style: line.style,
            }
      }

      if (
        stage === 'warmupListening' ||
        stage === 'intro'
      ) {
        return null
      }

      return {
        key: String(lineNumber),
        text: line.text,
        style: line.style,
      }
    }, [
      currentQuestion,
      line,
      lineNumber,
      stage,
    ])

  const voice =
    useInterviewerVoice(utterance)

  const handleStartInterview =
    useCallback(() => {
      /*
       * Stamp the beginning and sync the clock.
       *
       * Idempotent on the server, so calling it when resuming simply reads
       * back the original start time. Deliberately not awaited before
       * speaking: the clock is decoration next to the interview itself, and
       * making the candidate wait on a round trip before anything happens
       * would be a worse trade than a timer that settles a moment late.
       */
      const stampStart = async () => {
        try {
          const started =
            await startInterview(
              interviewId,
            )

          setElapsedTime(
            started.elapsed_seconds,
          )
        } catch {
          /*
           * A failure here costs an accurate clock and nothing else, so
           * the interview carries on and the timer counts from where it
           * was.
           */
        } finally {
          setClockRunning(true)
        }
      }

      void stampStart()

      /*
       * Coming back to an interview already in progress: no greeting, no
       * check-in, straight to the question that is still unanswered.
       */
      if (resuming) {
        say(
          FALLBACK_RESUME,
          'question',
        )

        return
      }

      const open = async () => {
        const greeting = await compose(
          {
            interview_id:
              numericInterviewId,
            moment: 'greeting',
          },
          FALLBACK_GREETING,
        )

        say(greeting, 'greeting')
      }

      void open()
    }, [
      compose,
      interviewId,
      numericInterviewId,
      resuming,
      say,
    ])

  const handleSkipWarmup =
    useCallback(() => {
      cancelWarmup()
      say(
        {
          ...FALLBACK_TRANSITION,
          text: '',
        },
        'question',
      )
    }, [
      cancelWarmup,
      say,
    ])

  const advancedLineRef =
    useRef(0)

  const finishLine =
    useCallback(() => {
      if (
        advancedLineRef.current >=
        lineNumber
      ) {
        return
      }

      advancedLineRef.current =
        lineNumber

      if (stage === 'greeting') {
        setStage('warmupListening')
        startWarmup()
        return
      }

      if (stage === 'warmupReply') {
        if (line?.expects_reply) {
          setWarmupExchanges(
            (previous) =>
              previous + 1,
          )

          setStage(
            'warmupListening',
          )

          startWarmup()
          return
        }

        say(
          {
            ...FALLBACK_TRANSITION,
            text: '',
          },
          'question',
        )
        return
      }

      if (stage === 'question') {
        setQuestionDelivered(true)
      }
    }, [
      line?.expects_reply,
      lineNumber,
      say,
      stage,
      startWarmup,
    ])

  const handleVoicePlaybackState =
    useCallback(
      (state: PlaybackState) => {
        setPlaybackState(state)

        if (
          state === PLAYBACK_STATE.ENDED ||
          state === PLAYBACK_STATE.BLOCKED
        ) {
          finishLine()
        }
      },
      [finishLine],
    )

  useEffect(() => {
    if (
      !line ||
      stage === 'intro' ||
      stage === 'warmupListening'
    ) {
      return
    }

    if (voice.loading) {
      return
    }

    const spokenLength =
      (utterance?.text.length ?? 0) +
      (utterance?.then?.length ?? 0)

    /*
     * A backstop in case playback never reports that it finished.
     *
     * When the clip's real length is known, the wait is that plus a little
     * slack, which is both accurate and short. The character-count guesses
     * below are only for when there is no clip to measure: synthesis
     * failed, so nothing is going to play and the room is really just
     * giving the candidate time to read the line before moving on.
     *
     * The guess used to run to sixty seconds, which is what a stalled
     * synthesis felt like from the candidate's side -- a silent screen with
     * no way to tell whether anything was still happening.
     */
    const budgetMs = voice.durationMs
      ? voice.durationMs + 2_500
      : voice.error
        ? Math.min(
            12_000,
            2_000 + spokenLength * 45,
          )
        : Math.min(
            20_000,
            4_000 + spokenLength * 60,
          )

    const timer =
      window.setTimeout(
        finishLine,
        budgetMs,
      )

    return () =>
      window.clearTimeout(timer)
  }, [
    finishLine,
    line,
    stage,
    utterance?.text,
    utterance?.then,
    voice.durationMs,
    voice.error,
    voice.loading,
  ])

  /*
   * Load interview status first.
   *
   * IMPORTANT:
   * We do NOT change the existing intro/greeting/warmup flow.
   *
   * The only difference is that currentQuestion comes from
   * `next_question` returned by the backend instead of always
   * taking question #1.
   */
  useEffect(() => {
    cancelWarmup()

    setStage('intro')
    setLine(null)
    setLineNumber(0)

    /*
     * Reset alongside lineNumber, never independently.
     *
     * This is the high-water mark of which spoken line has already been
     * acted on, and finishLine ignores anything at or below it. Leaving it
     * behind while lineNumber goes back to zero means every subsequent line
     * looks already-finished: the question appears, the interviewer reads
     * it, and the microphone never opens because questionDelivered is never
     * set. The two are one piece of state in two variables.
     */
    advancedLineRef.current = 0
    setQuestionDelivered(false)
    setWarmupExchanges(0)
    setAnswerAttempt(0)
    setCurrentQuestion(null)
    setInterviewCompleted(false)
    setResuming(false)
    setAnsweredCount(0)
    setElapsedTime(0)
    setClockRunning(false)

    const fetchInterviewState =
      async () => {
        setLoading(true)
        setError(null)

        try {
          /*
           * First ask the backend if the interview is already completed
           * and which question should be answered next.
           */
          const interviewStatus =
            await getInterviewStatus(
              interviewId,
            )

          /*
           * Completed interview:
           * do not enter the interview UI.
           */
          if (
            interviewStatus.completed
          ) {
            setInterviewCompleted(true)
            setCurrentQuestion(null)
            return
          }

          /*
           * Not completed:
           * backend gives us the first unanswered question.
           */
          const nextQuestion =
            interviewStatus.next_question

          if (!nextQuestion) {
            setInterviewCompleted(true)
            setCurrentQuestion(null)
            return
          }

          /*
           * Load all questions only for calculating the progress number.
           */
          const questions =
            await getInterviewQuestions(
              interviewId,
            )

          const rootQuestions =
            [...questions]
              .filter(
                (question) =>
                  !question.is_follow_up,
              )
              .sort(
                (a, b) => {
                  if (
                    a.sequence_number !==
                    b.sequence_number
                  ) {
                    return (
                      a.sequence_number -
                      b.sequence_number
                    )
                  }

                  return a.id - b.id
                },
              )

          setPlannedTotal(
            rootQuestions.length,
          )

          /*
           * Calculate question number.
           *
           * Follow-ups belong to their parent question,
           * so they do not increment the main question counter.
           */
          if (
            nextQuestion.is_follow_up
          ) {
            const rootQuestion =
              questions.find(
                (question) =>
                  question.id ===
                  nextQuestion.parent_question_id,
              )

            if (rootQuestion) {
              const rootIndex =
                rootQuestions.findIndex(
                  (question) =>
                    question.id ===
                    rootQuestion.id,
                )

              setQuestionNumber(
                rootIndex >= 0
                  ? rootIndex + 1
                  : 1,
              )
            } else {
              setQuestionNumber(1)
            }
          } else {
            const rootIndex =
              rootQuestions.findIndex(
                (question) =>
                  question.id ===
                  nextQuestion.id,
              )

            setQuestionNumber(
              rootIndex >= 0
                ? rootIndex + 1
                : 1,
            )
          }

          setCurrentQuestion(
            nextQuestion,
          )

          setAnsweredCount(
            interviewStatus.answered_count,
          )

          /*
           * Resuming an interview that is already under way.
           *
           * A candidate who reloads on question three has already been
           * greeted and already done the check-in; walking them back
           * through both is the bug this guards against. started_at is the
           * signal rather than the answer count, because someone who
           * reloads while still on the first question has answered nothing
           * and has still already been greeted.
           *
           * Both facts are the backend's, not the browser's, so this
           * survives a new tab, a different browser or a different
           * machine — none of which locally stored state would.
           *
           * It still costs one click rather than resuming outright. A
           * reload is a fresh document with no user gesture behind it, and
           * browsers refuse to play audio until there is one; resuming
           * silently would put the candidate on question three with the
           * question unspoken and the microphone already listening. The
           * click is what buys the audio, so it stays.
           */
          const alreadyStarted =
            interviewStatus.started_at !==
            null

          setResuming(alreadyStarted)

          /*
           * Pick the clock up where it was rather than from zero. The
           * server measures the elapsed time, so a candidate whose device
           * clock is wrong still sees the true duration.
           */
          setElapsedTime(
            interviewStatus.elapsed_seconds,
          )
          setClockRunning(alreadyStarted)
        } catch {
          setError(
            'Failed to load interview',
          )
        } finally {
          setLoading(false)
        }
      }

    void fetchInterviewState()
  }, [
    cancelWarmup,
    interviewId,
  ])

  /*
   * Camera.
   */
  useEffect(() => {
    let stream: MediaStream | null =
      null

    const startCamera =
      async () => {
        if (!cameraEnabled) {
          setCameraStream(null)
          return
        }

        try {
          stream =
            await navigator.mediaDevices.getUserMedia(
              {
                video: true,
                audio: false,
              },
            )

          setCameraStream(stream)
        } catch {
          setCameraStream(null)
          setCameraEnabled(false)
        }
      }

    void startCamera()

    return () => {
      stream
        ?.getTracks()
        .forEach((track) =>
          track.stop(),
        )
    }
  }, [cameraEnabled])

  /*
   * Interview clock.
   *
   * Seeded from the server on load and again when the interview is
   * started, so it measures the interview rather than the life of this
   * page: a reload picks the count up where it was instead of at zero.
   * It runs through the resume screen too, because time spent deciding to
   * come back is still time the interview has been open.
   */
  useEffect(() => {
    if (
      !clockRunning ||
      stage === 'closing'
    ) {
      return
    }

    const timer =
      window.setInterval(() => {
        setElapsedTime(
          (previousTime) =>
            previousTime + 1,
        )
      }, 1000)

    return () => {
      window.clearInterval(timer)
    }
  }, [clockRunning, stage])

  const currentQuestionId =
    currentQuestion?.id

  const microphoneEnabledRef =
    useRef(microphoneEnabled)

  microphoneEnabledRef.current =
    microphoneEnabled

  useEffect(() => {
    if (
      stage !== 'question' ||
      currentQuestionId ===
        undefined ||
      !questionDelivered
    ) {
      return
    }

    const openTurn =
      async () => {
        await startTurn(
          currentQuestionId,
          microphoneId || undefined,
        )

        if (
          !microphoneEnabledRef.current
        ) {
          setTurnMicrophoneEnabled(
            false,
          )
        }
      }

    const opening =
      window.setTimeout(
        () => {
          void openTurn()
        },
        MICROPHONE_LEAD_IN_MS,
      )

    return () => {
      window.clearTimeout(opening)
      cancelTurn()
    }
  }, [
    answerAttempt,
    cancelTurn,
    currentQuestionId,
    microphoneId,
    questionDelivered,
    setTurnMicrophoneEnabled,
    stage,
    startTurn,
  ])

  const isSpeaking =
    playbackState ===
    PLAYBACK_STATE.PLAYING

  const isListening =
    (
      stage === 'question' &&
      questionDelivered &&
      (
        turn.phase === 'waiting' ||
        turn.phase === 'speaking' ||
        turn.phase === 'confirming'
      )
    ) ||
    (
      stage === 'warmupListening' &&
      warmup.phase === 'listening'
    )

  const isThinking =
    composing ||
    voice.loading ||
    turn.phase === 'saving'

  const interviewerState:
    InterviewerState =
    isSpeaking
      ? stage === 'greeting'
        ? 'greeting'
        : 'speaking'
      : isThinking
        ? 'thinking'
        : isListening
          ? 'listening'
          : 'idle'

  const isQuestionOnScreen =
    stage === 'question' &&
    Boolean(currentQuestion)

  const displayedPrompt =
    isQuestionOnScreen
      ? currentQuestion?.question ?? ''
      : line?.text ??
        (resuming
          ? 'Welcome back. Your interview is still in progress.'
          : 'Welcome. Take a moment to get comfortable.')

  const progressLabel =
    isQuestionOnScreen
      ? undefined
      : stage === 'closing'
        ? 'Interview complete'
        : stage === 'warmupListening'
          ? 'Your turn'
          : stage === 'warmupReply'
            ? 'Before we begin'
            : resuming
              ? 'Welcome back'
              : 'Welcome'

  const conversationHint =
    stage === 'intro'
      ? resuming
        ? answeredCount > 0
          ? 'Nothing has been lost — your answers so far are saved. ' +
            `You will pick up on question ${questionNumber}.`
          : 'Nothing has been lost. You will pick up on question ' +
            `${questionNumber}, and the introductions are already done.`
        : 'Your interviewer will say hello and ask how you are before the ' +
          'first question.'
      : stage === 'greeting'
        ? 'Listen along — you will get a turn to reply in a moment.'
        : stage === 'warmupListening'
          ? 'A sentence is plenty. This check-in is not scored.'
          : stage === 'warmupReply'
            ? 'The first question is next.'
            : stage === 'question'
              ? questionDelivered
                ? 'Take your time. I will listen until you are finished.'
                : 'Read along — your microphone opens once I finish.'
              : 'Your answers have been saved.'

  const candidateStatus =
    !microphoneEnabled
      ? 'Muted'
      : isListening
        ? 'Speaking'
        : 'Mic ready'

  const interviewerStatus =
    isSpeaking
      ? 'Speaking'
      : isThinking
        ? 'Thinking'
        : isListening
          ? 'Listening'
          : 'Ready'

  const handleToggleCamera =
    () => {
      setCameraEnabled(
        (previousValue) =>
          !previousValue,
      )
    }

  const handleToggleMicrophone =
    () => {
      const next =
        !microphoneEnabled

      setMicrophoneEnabled(next)
      setTurnMicrophoneEnabled(
        next,
      )

      if (
        !next &&
        stage === 'warmupListening'
      ) {
        warmup.finish()
      }
    }

  const handleLeaveInterview =
    () => {
      cancelTurn()
      warmup.cancel()
      stopCamera()

      navigate('/jobs', { replace: true })
    }

  if (loading) {
    return (
      <main className={styles.page}>
        <section className={styles.message}>
          <p
            className={
              styles.messageTitle
            }
          >
            Preparing your interview
          </p>

          <p
            className={
              styles.messageBody
            }
          >
            This only takes a moment.
          </p>
        </section>
      </main>
    )
  }

  if (error) {
    return (
      <main className={styles.page}>
        <section className={styles.message}>
          <p
            className={
              styles.messageTitle
            }
          >
            We couldn&rsquo;t load this interview
          </p>

          <p
            className={
              styles.messageBody
            }
          >
            {error}
          </p>
        </section>
      </main>
    )
  }

  /*
   * Completed interview:
   * block the interview UI completely.
   */
  if (interviewCompleted) {
    return (
      <main className={styles.page}>
        <section className={styles.message}>
          <p
            className={
              styles.messageTitle
            }
          >
            Interview already completed
          </p>

          <p
            className={
              styles.messageBody
            }
          >
            You have already completed this interview.
          </p>

          <div
            className={
              styles.actions
            }
          >
            <button
              type="button"
              className={
                styles.primaryButton
              }
              onClick={
                handleLeaveInterview
              }
            >
              Back to jobs
            </button>
          </div>
        </section>
      </main>
    )
  }

  if (
    !currentQuestion &&
    stage !== 'closing'
  ) {
    return (
      <main className={styles.page}>
        <section className={styles.message}>
          <p
            className={
              styles.messageTitle
            }
          >
            No questions yet
          </p>

          <p
            className={
              styles.messageBody
            }
          >
            This interview has no questions prepared for it.
          </p>
        </section>
      </main>
    )
  }

  return (
    <main className={styles.page}>
      <section
        className={
          styles.interviewCard
        }
      >
        <div
          className={
            styles.stageGrid
          }
        >
          <figure
            className={
              styles.interviewerPane
            }
          >
            <AiInterviewer
              state={
                interviewerState
              }
              mood={
                line?.mood ??
                'neutral'
              }
              visemes={
                voice.visemes
              }
              audioElement={
                audioElement
              }
              listeningLevel={
                microphoneEnabled
                  ? turn.level
                  : 0
              }
            />

            <figcaption
              className={
                styles.paneLabel
              }
            >
              <span
                className={
                  styles.paneDot
                }
                data-active={
                  isSpeaking ||
                  isListening
                }
                aria-hidden="true"
              />

              {INTERVIEWER_NAME} ·{' '}
              {interviewerStatus}
            </figcaption>
          </figure>

          <figure
            className={
              styles.candidatePane
            }
          >
            <InterviewVideo
              elapsedTime={
                elapsedTime
              }
              live={
                isListening &&
                microphoneEnabled
              }
              stream={
                cameraStream
              }
              cameraEnabled={
                cameraEnabled
              }
            />

            <figcaption
              className={
                styles.paneLabel
              }
            >
              <span
                className={
                  styles.paneDot
                }
                data-active={
                  isListening &&
                  microphoneEnabled
                }
                aria-hidden="true"
              />

              You ·{' '}
              {candidateStatus}
            </figcaption>
          </figure>
        </div>

        <InterviewQuestion
          key={
            isQuestionOnScreen
              ? currentQuestion?.id
              : `line-${lineNumber}`
          }
          question={
            displayedPrompt
          }
          currentQuestion={
            questionNumber
          }
          totalQuestions={Math.max(
            plannedTotal,
            questionNumber,
          )}
          isFollowUp={
            isQuestionOnScreen &&
            Boolean(
              currentQuestion?.is_follow_up,
            )
          }
          progressLabel={
            progressLabel
          }
        />

        <p
          className={
            styles.conversationHint
          }
        >
          {conversationHint}
        </p>

        <AudioPlayer
          audioSrc={
            voice.audioUrl
          }
          captions={
            utterance?.text ?? ''
          }
          autoPlay
          onPlaybackStateChange={
            handleVoicePlaybackState
          }
          onAudioElement={
            setAudioElement
          }
        />

        {voice.loading && (
          <p
            className={
              styles.notice
            }
          >
            The interviewer is thinking&hellip;
          </p>
        )}

        {voice.error && (
          <output
            className={
              styles.notice
            }
            aria-live="polite"
          >
            {voice.error}
          </output>
        )}

        {stage === 'intro' && (
          <div
            className={
              styles.actions
            }
          >
            <button
              type="button"
              className={
                styles.primaryButton
              }
              onClick={
                handleStartInterview
              }
              disabled={
                composing
              }
            >
              {composing
                ? 'Starting…'
                : resuming
                  ? `Resume from question ${questionNumber}`
                  : 'I’m ready — start the interview'}
            </button>
          </div>
        )}

        {stage ===
          'warmupListening' && (
          <section
            className={
              styles.warmupStatus
            }
            aria-live="polite"
          >
            <div
              className={
                styles.warmupStatusHeader
              }
            >
              <span
                className={
                  styles.warmupDot
                }
                data-live={
                  warmup.phase ===
                  'listening'
                }
                aria-hidden="true"
              />

              <p>
                {warmup.phase ===
                'listening'
                  ? 'Listening for your check-in'
                  : 'Voice check-in unavailable'}
              </p>
            </div>

            <p
              className={
                styles.warmupTranscript
              }
            >
              {warmup.transcript ||
                warmup.error ||
                'Say a sentence when you are ready.'}
            </p>

            <div
              className={
                styles.actions
              }
            >
              {warmup.phase ===
                'listening' && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  onClick={
                    warmup.finish
                  }
                >
                  That&rsquo;s enough
                </button>
              )}

              <button
                type="button"
                className={
                  styles.secondaryButton
                }
                onClick={
                  handleSkipWarmup
                }
              >
                Skip and start the interview
              </button>
            </div>
          </section>
        )}

        {stage === 'question' &&
          questionDelivered && (
          <div
            className={
              styles.statusRegion
            }
          >
            <TurnIndicator
              phase={
                turn.phase
              }
              transcript={
                turn.transcript
              }
              confirmProgress={
                turn.confirmProgress
              }
              level={
                turn.level
              }
              muted={
                !microphoneEnabled
              }
              onFinish={
                turn.finish
              }
            />
          </div>
        )}

        {stage === 'closing' && (
          <>
            <p
              className={
                styles.closingNote
              }
            >
              Your answers have been
              saved. You can leave
              whenever you are ready.
            </p>

            {/*
              * The interview controls are gone by this point -- camera,
              * microphone and the answer indicator all belong to a turn
              * that is over. Leaving was the one thing among them that
              * still applied, so it comes back on its own here rather
              * than the candidate being told to close the tab and left
              * to find their own way back.
              */}
            <div
              className={
                styles.actions
              }
            >
              <button
                type="button"
                className={
                  styles.primaryButton
                }
                onClick={
                  handleLeaveInterview
                }
              >
                Back to jobs
              </button>
            </div>
          </>
        )}

        {turn.error && (
          <div
            className={
              styles.alert
            }
            role="alert"
          >
            <p
              className={
                styles.alertText
              }
            >
              {turn.error}
            </p>

            {stage ===
              'question' && (
              <button
                type="button"
                className={
                  styles.primaryButton
                }
                onClick={() =>
                  setAnswerAttempt(
                    (previous) =>
                      previous + 1,
                  )
                }
              >
                Try that answer again
              </button>
            )}
          </div>
        )}

        {stage !== 'closing' &&
          audioInputs.length > 1 && (
          <div
            className={
              styles.deviceRow
            }
          >
            <label
              className={
                styles.deviceLabel
              }
              htmlFor="interview-mic"
            >
              Microphone
            </label>

            <select
              id="interview-mic"
              className={
                styles.deviceSelect
              }
              value={
                microphoneId
              }
              onChange={(
                event,
              ) =>
                setMicrophoneId(
                  event.target
                    .value,
                )
              }
            >
              <option value="">
                System default
              </option>

              {audioInputs.map(
                (input) => (
                  <option
                    key={
                      input.deviceId
                    }
                    value={
                      input.deviceId
                    }
                  >
                    {input.label}
                  </option>
                ),
              )}
            </select>
          </div>
        )}

        {stage !== 'closing' && (
          <InterviewControls
            cameraEnabled={
              cameraEnabled
            }
            microphoneEnabled={
              microphoneEnabled
            }
            onToggleCamera={
              handleToggleCamera
            }
            onToggleMicrophone={
              handleToggleMicrophone
            }
            onLeave={
              handleLeaveInterview
            }
          />
        )}
      </section>
    </main>
  )
}

export default InterviewRoomPage