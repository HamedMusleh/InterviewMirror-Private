/**
 * The interviewer's face.
 *
 * Drawn as SVG and animated by mutating attributes inside a single
 * requestAnimationFrame loop. Nothing here goes through React state: at
 * sixty frames a second a re-render per frame would cost more than the
 * drawing does, and none of this motion is something the rest of the page
 * needs to know about.
 *
 * The mouth is driven by the viseme timeline the server captured while Azure
 * synthesised this exact audio, read against the audio element's own
 * `currentTime`. Reading the clock from the element rather than from a timer
 * started alongside it is what keeps the mouth on the sound: the element is
 * the thing that can stall for buffering, and a timer would carry on without
 * it and never recover.
 *
 * Everything else on the face exists because a head that only moves its
 * mouth reads as a puppet. Blinking, breathing, a slow postural drift, small
 * gaze shifts, and a nod when the candidate is talking are all
 * unremarkable individually, and collectively they are the difference
 * between a face and a diagram of one.
 */

import { useEffect, useRef } from 'react'

import {
  BLINK_DURATION_MS,
  BLINK_INTERVAL_MAX_MS,
  BLINK_INTERVAL_MIN_MS,
  MOOD_EXPRESSIONS,
  MOUTH_SMOOTHING_MS,
  SACCADE_INTERVAL_MAX_MS,
  SACCADE_INTERVAL_MIN_MS,
  SILENT_MOUTH,
  VISEME_SHAPES,
  type InterviewerMood,
  type InterviewerState,
  type MouthShape,
} from './AiInterviewer.const'
import styles from './AiInterviewer.module.css'
import type { VisemeMark } from '../../services/textToSpeechApi'

interface AiInterviewerProps {
  state: InterviewerState
  mood?: InterviewerMood
  /** Mouth timeline for the line currently playing. */
  visemes?: VisemeMark[]
  /** The element actually playing that line. The clock is read from it. */
  audioElement?: HTMLAudioElement | null
  /** Candidate input level, 0..1. Drives listening nods. */
  listeningLevel?: number
}

// --- face geometry, in the SVG's own units -----------------------------

const FACE_CENTER_X = 160
const NECK_PIVOT_Y = 236

const EYE_Y = 132
const EYE_OFFSET_X = 25
const EYE_RX = 14
const EYE_RY = 9.5

const BROW_Y = 108
const MOUTH_Y = 187

const LEFT_EYE_X = FACE_CENTER_X - EYE_OFFSET_X
const RIGHT_EYE_X = FACE_CENTER_X + EYE_OFFSET_X

function randomBetween(minimum: number, maximum: number): number {
  return minimum + Math.random() * (maximum - minimum)
}

/**
 * Turn the four mouth numbers into the outline of an opening.
 *
 * `lift` raises the corners without opening the mouth, which is what a
 * closed smile is. It is damped away while speaking, because a mouth trying
 * to hold a smile and articulate at the same time does neither.
 */
function lensPath(
  centerY: number,
  halfWidth: number,
  upper: number,
  lower: number,
  lift: number,
): string {
  const cornerY = centerY - lift
  const x = FACE_CENTER_X

  return [
    `M ${x - halfWidth} ${cornerY}`,
    `C ${x - halfWidth * 0.55} ${centerY - upper}`,
    `${x + halfWidth * 0.55} ${centerY - upper}`,
    `${x + halfWidth} ${cornerY}`,
    `C ${x + halfWidth * 0.55} ${centerY + lower}`,
    `${x - halfWidth * 0.55} ${centerY + lower}`,
    `${x - halfWidth} ${cornerY}`,
    'Z',
  ].join(' ')
}

function AiInterviewer({
  state,
  mood = 'neutral',
  visemes,
  audioElement = null,
  listeningLevel = 0,
}: AiInterviewerProps) {
  const headRef = useRef<SVGGElement>(null)
  const torsoRef = useRef<SVGGElement>(null)

  const leftLidRef = useRef<SVGGElement>(null)
  const rightLidRef = useRef<SVGGElement>(null)
  const leftIrisRef = useRef<SVGGElement>(null)
  const rightIrisRef = useRef<SVGGElement>(null)
  const leftBrowRef = useRef<SVGPathElement>(null)
  const rightBrowRef = useRef<SVGPathElement>(null)

  const lipsRef = useRef<SVGPathElement>(null)
  const mouthRef = useRef<SVGPathElement>(null)
  const mouthClipRef = useRef<SVGPathElement>(null)
  const teethRef = useRef<SVGRectElement>(null)
  const tongueRef = useRef<SVGEllipseElement>(null)
  const cheeksRef = useRef<SVGGElement>(null)

  /*
   * Live props, mirrored into a ref.
   *
   * The animation loop is started once and must not be torn down and
   * rebuilt every time the state or the mood changes — restarting it would
   * reset the blink timer and the postural drift, producing a visible
   * twitch at exactly the moments the interviewer changes what it is doing.
   */
  const liveRef = useRef({ state, mood, visemes, audioElement, listeningLevel })

  liveRef.current = { state, mood, visemes, audioElement, listeningLevel }

  useEffect(() => {
    const reduceMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches

    // Mutable animation state. Kept out of React entirely.
    const mouth: MouthShape = { ...SILENT_MOUTH }
    let smile = 0

    let blink = 0
    let blinkStartedAt = 0
    let nextBlinkAt = performance.now() + randomBetween(600, 2000)

    const gaze = { x: 0, y: 0 }
    const gazeTarget = { x: 0, y: 0 }
    let nextSaccadeAt = performance.now() + 1200

    let nodAmplitude = 0
    let nodPhase = 0
    let lastNodAt = 0

    let visemeIndex = 0
    let lastVisemes: VisemeMark[] | undefined

    let lastFrameAt = performance.now()
    let frame = 0

    const draw = () => {
      const now = performance.now()
      const deltaMs = Math.min(now - lastFrameAt, 100)
      lastFrameAt = now

      const live = liveRef.current
      const expression = MOOD_EXPRESSIONS[live.mood]
      const isSpeaking = live.state === 'speaking' || live.state === 'greeting'

      // --- mouth ------------------------------------------------------
      let target = SILENT_MOUTH

      if (isSpeaking && live.visemes && live.visemes.length > 0) {
        if (live.visemes !== lastVisemes) {
          lastVisemes = live.visemes
          visemeIndex = 0
        }

        const positionMs = (live.audioElement?.currentTime ?? 0) * 1000

        // A replay winds the clock back, so the search restarts rather than
        // running off the end of the timeline and freezing the mouth open.
        if (positionMs < live.visemes[visemeIndex].offset_ms) {
          visemeIndex = 0
        }

        while (
          visemeIndex + 1 < live.visemes.length &&
          live.visemes[visemeIndex + 1].offset_ms <= positionMs
        ) {
          visemeIndex += 1
        }

        target =
          VISEME_SHAPES[live.visemes[visemeIndex].viseme_id] ?? SILENT_MOUTH
      }

      const chase = 1 - Math.exp(-deltaMs / MOUTH_SMOOTHING_MS)

      mouth.open += (target.open - mouth.open) * chase
      mouth.wide += (target.wide - mouth.wide) * chase
      mouth.round += (target.round - mouth.round) * chase
      mouth.teeth += (target.teeth - mouth.teeth) * chase

      const smileTarget = isSpeaking ? expression.smile * 0.3 : expression.smile
      smile += (smileTarget - smile) * (1 - Math.exp(-deltaMs / 260))

      const halfWidth =
        21 * (0.55 + 0.62 * mouth.wide) * (1 - 0.42 * mouth.round)
      const upper = 1.2 + 13 * mouth.open * 0.42
      const lower = 1.6 + 13 * mouth.open * 0.72
      const lift = smile * 3.6

      const openingPath = lensPath(MOUTH_Y, halfWidth, upper, lower, lift)
      const lipPath = lensPath(
        MOUTH_Y,
        halfWidth + 3.4,
        upper + 3.6,
        lower + 4.4,
        lift,
      )

      mouthRef.current?.setAttribute('d', openingPath)
      mouthClipRef.current?.setAttribute('d', openingPath)
      lipsRef.current?.setAttribute('d', lipPath)

      teethRef.current?.setAttribute('x', String(FACE_CENTER_X - halfWidth))
      teethRef.current?.setAttribute('y', String(MOUTH_Y - upper))
      teethRef.current?.setAttribute('width', String(halfWidth * 2))
      teethRef.current?.setAttribute('height', String(Math.max(upper, 0.1)))
      teethRef.current?.setAttribute('opacity', String(mouth.teeth))

      tongueRef.current?.setAttribute(
        'cy',
        String(MOUTH_Y + lower * 0.55),
      )
      tongueRef.current?.setAttribute('rx', String(halfWidth * 0.62))
      tongueRef.current?.setAttribute('ry', String(Math.max(lower * 0.5, 0.1)))
      tongueRef.current?.setAttribute(
        'opacity',
        String(Math.max(0, mouth.open - 0.25)),
      )

      cheeksRef.current?.setAttribute('opacity', String(0.1 + smile * 0.3))

      // --- blinking ---------------------------------------------------
      if (blink === 0 && now >= nextBlinkAt) {
        blink = 0.0001
        blinkStartedAt = now
      }

      if (blink > 0) {
        const through = (now - blinkStartedAt) / BLINK_DURATION_MS

        if (through >= 1) {
          blink = 0
          // Thinking slows blinking down; it is one of the cues that reads
          // as attention being directed inward rather than at the camera.
          const slower = live.state === 'thinking' ? 1.6 : 1
          nextBlinkAt =
            now +
            randomBetween(BLINK_INTERVAL_MIN_MS, BLINK_INTERVAL_MAX_MS) *
              slower
        } else {
          // Down fast, up slower, the way a real lid moves.
          blink =
            through < 0.42
              ? through / 0.42
              : 1 - (through - 0.42) / 0.58
        }
      }

      const lidTravel = (EYE_RY * 2 + 4) * Math.min(Math.max(blink, 0), 1)

      leftLidRef.current?.setAttribute(
        'transform',
        `translate(0 ${lidTravel})`,
      )
      rightLidRef.current?.setAttribute(
        'transform',
        `translate(0 ${lidTravel})`,
      )

      // --- gaze -------------------------------------------------------
      if (now >= nextSaccadeAt) {
        if (live.state === 'thinking') {
          // Looking up and away while composing a thought.
          gazeTarget.x = randomBetween(-3.4, -1.2)
          gazeTarget.y = randomBetween(-3.2, -1.6)
          nextSaccadeAt = now + randomBetween(700, 1600)
        } else if (live.state === 'listening') {
          // Mostly holding the candidate's gaze, with small breaks.
          gazeTarget.x = randomBetween(-1.4, 1.4)
          gazeTarget.y = randomBetween(-0.8, 0.9)
          nextSaccadeAt =
            now +
            randomBetween(SACCADE_INTERVAL_MIN_MS, SACCADE_INTERVAL_MAX_MS)
        } else {
          gazeTarget.x = randomBetween(-2.2, 2.2)
          gazeTarget.y = randomBetween(-1.4, 1.4)
          nextSaccadeAt =
            now +
            randomBetween(SACCADE_INTERVAL_MIN_MS, SACCADE_INTERVAL_MAX_MS)
        }
      }

      // Saccades are fast; the eye arrives long before the head does.
      const gazeChase = 1 - Math.exp(-deltaMs / 70)
      gaze.x += (gazeTarget.x - gaze.x) * gazeChase
      gaze.y += (gazeTarget.y - gaze.y) * gazeChase

      leftIrisRef.current?.setAttribute(
        'transform',
        `translate(${gaze.x} ${gaze.y})`,
      )
      rightIrisRef.current?.setAttribute(
        'transform',
        `translate(${gaze.x} ${gaze.y})`,
      )

      // --- brows ------------------------------------------------------
      const listeningLift = live.state === 'listening' ? 1.4 : 0
      const speakingAccent = isSpeaking ? mouth.open * 1.6 : 0
      const browShift = -(expression.brow + listeningLift + speakingAccent)

      leftBrowRef.current?.setAttribute(
        'transform',
        `translate(0 ${browShift})`,
      )
      rightBrowRef.current?.setAttribute(
        'transform',
        `translate(0 ${browShift})`,
      )

      // --- head and breathing -----------------------------------------
      if (!reduceMotion) {
        // A nod when the candidate has been talking for a moment. It is
        // acknowledgement without interruption, which is the only kind
        // available while the microphone is open.
        if (
          live.state === 'listening' &&
          live.listeningLevel > 0.16 &&
          now - lastNodAt > 2600
        ) {
          lastNodAt = now
          nodAmplitude = 1
          nodPhase = 0
        }

        if (nodAmplitude > 0.01) {
          nodPhase += deltaMs / 420
          nodAmplitude *= Math.exp(-deltaMs / 520)
        } else {
          nodAmplitude = 0
        }

        const nod = Math.sin(nodPhase * Math.PI * 2) * nodAmplitude
        const breath = Math.sin(now / 2600)

        const swayX =
          Math.sin(now / 2400) * 1.3 + Math.sin(now / 3700) * 0.7
        const swayY = Math.sin(now / 3100) * 0.8 + breath * 1.1

        const rotation = expression.tilt + swayX * 0.5 + nod * 1.6

        headRef.current?.setAttribute(
          'transform',
          `translate(${swayX * 0.6} ${swayY + nod * 3.4}) ` +
            `rotate(${rotation} ${FACE_CENTER_X} ${NECK_PIVOT_Y})`,
        )

        torsoRef.current?.setAttribute(
          'transform',
          `translate(0 ${breath * 0.9})`,
        )
      } else {
        headRef.current?.setAttribute(
          'transform',
          `rotate(${expression.tilt} ${FACE_CENTER_X} ${NECK_PIVOT_Y})`,
        )
      }

      frame = requestAnimationFrame(draw)
    }

    frame = requestAnimationFrame(draw)

    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <div className={styles.stage}>
      <svg className={styles.avatar} viewBox="0 0 320 300">
        {/* Names the drawing for assistive technology, and updates as the
            interviewer changes what it is doing. */}
        <title>{ARIA_LABELS[state]}</title>

        <defs>
          <radialGradient id="aiBackdrop" cx="50%" cy="38%" r="72%">
            <stop offset="0%" stopColor="#f4f6fb" />
            <stop offset="100%" stopColor="#dde3ef" />
          </radialGradient>

          <linearGradient id="aiSkin" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f6d6ba" />
            <stop offset="100%" stopColor="#e7b992" />
          </linearGradient>

          <linearGradient id="aiHair" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4a4262" />
            <stop offset="100%" stopColor="#302b45" />
          </linearGradient>

          <linearGradient id="aiShirt" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#38497c" />
            <stop offset="100%" stopColor="#2b3a67" />
          </linearGradient>

          <radialGradient id="aiCheek" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#e8907f" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#e8907f" stopOpacity="0" />
          </radialGradient>

          <clipPath id="aiLeftEye">
            <ellipse
              cx={LEFT_EYE_X}
              cy={EYE_Y}
              rx={EYE_RX}
              ry={EYE_RY}
            />
          </clipPath>

          <clipPath id="aiRightEye">
            <ellipse
              cx={RIGHT_EYE_X}
              cy={EYE_Y}
              rx={EYE_RX}
              ry={EYE_RY}
            />
          </clipPath>

          <clipPath id="aiMouth">
            <path ref={mouthClipRef} d="" />
          </clipPath>
        </defs>

        <rect width="320" height="300" rx="14" fill="url(#aiBackdrop)" />

        <g ref={torsoRef}>
          {/* Shoulders. Drawn wide and low so the head has something to sit
              on; a floating head reads as a mask. */}
          <path
            d="M 42 300 C 46 258 96 236 160 236 C 224 236 274 258 278 300 Z"
            fill="url(#aiShirt)"
          />
          <path
            d="M 134 240 C 146 262 174 262 186 240 C 178 236 142 236 134 240 Z"
            fill="#f7f9fd"
            opacity="0.9"
          />
        </g>

        <g ref={headRef}>
          {/* Neck, with the shadow the jaw casts on it. */}
          <path
            d="M 141 186 L 141 226 C 141 238 179 238 179 226 L 179 186 Z"
            fill="#e0ae86"
          />
          <ellipse cx={FACE_CENTER_X} cy="196" rx="24" ry="10" fill="#d19f78" />

          {/* Hair behind the face. */}
          <ellipse
            cx={FACE_CENTER_X}
            cy="134"
            rx="70"
            ry="80"
            fill="url(#aiHair)"
          />

          {/* Ears. */}
          <ellipse cx="99" cy="142" rx="8" ry="13" fill="#e7b992" />
          <ellipse cx="221" cy="142" rx="8" ry="13" fill="#e7b992" />

          {/* Face. */}
          <ellipse
            cx={FACE_CENTER_X}
            cy="140"
            rx="62"
            ry="74"
            fill="url(#aiSkin)"
          />

          {/* Fringe, drawn over the top of the face. */}
          <path
            d="M 98 118 C 104 72 132 58 160 58 C 190 58 218 74 222 120
               C 214 96 196 84 168 88 C 140 92 116 100 98 118 Z"
            fill="url(#aiHair)"
          />

          <g ref={cheeksRef} opacity="0.15">
            <ellipse cx="124" cy="163" rx="15" ry="10" fill="url(#aiCheek)" />
            <ellipse cx="196" cy="163" rx="15" ry="10" fill="url(#aiCheek)" />
          </g>

          {/* Brows. */}
          <path
            ref={leftBrowRef}
            d={`M ${LEFT_EYE_X - 16} ${BROW_Y + 2}
                Q ${LEFT_EYE_X} ${BROW_Y - 5}
                  ${LEFT_EYE_X + 15} ${BROW_Y + 1}`}
            fill="none"
            stroke="#3d3550"
            strokeWidth="3.6"
            strokeLinecap="round"
          />
          <path
            ref={rightBrowRef}
            d={`M ${RIGHT_EYE_X - 15} ${BROW_Y + 1}
                Q ${RIGHT_EYE_X} ${BROW_Y - 5}
                  ${RIGHT_EYE_X + 16} ${BROW_Y + 2}`}
            fill="none"
            stroke="#3d3550"
            strokeWidth="3.6"
            strokeLinecap="round"
          />

          <Eye
            centerX={LEFT_EYE_X}
            clipId="aiLeftEye"
            irisRef={leftIrisRef}
            lidRef={leftLidRef}
          />
          <Eye
            centerX={RIGHT_EYE_X}
            clipId="aiRightEye"
            irisRef={rightIrisRef}
            lidRef={rightLidRef}
          />

          {/* Nose. */}
          <path
            d="M 158 146 C 152 160 150 165 155 168 C 159 170 163 170 167 167"
            fill="none"
            stroke="#d09b73"
            strokeWidth="2.6"
            strokeLinecap="round"
          />

          {/* Mouth: lips behind, opening in front, teeth and tongue
              clipped to the opening so they can never spill onto the chin. */}
          <path ref={lipsRef} d="" fill="#cf7d78" />
          <path ref={mouthRef} d="" fill="#5c2b33" />
          <g clipPath="url(#aiMouth)">
            <rect ref={teethRef} x="0" y="0" width="0" height="0" fill="#fdfdfa" />
            <ellipse
              ref={tongueRef}
              cx={FACE_CENTER_X}
              cy={MOUTH_Y}
              rx="0"
              ry="0"
              fill="#c06b76"
            />
          </g>
        </g>
      </svg>
    </div>
  )
}

const ARIA_LABELS: Record<InterviewerState, string> = {
  idle: 'The AI interviewer, waiting',
  greeting: 'The AI interviewer, greeting you',
  speaking: 'The AI interviewer, speaking',
  listening: 'The AI interviewer, listening to your answer',
  thinking: 'The AI interviewer, considering your answer',
}

interface EyeProps {
  centerX: number
  clipId: string
  irisRef: React.RefObject<SVGGElement | null>
  lidRef: React.RefObject<SVGGElement | null>
}

function Eye({ centerX, clipId, irisRef, lidRef }: EyeProps) {
  return (
    <g>
      <g clipPath={`url(#${clipId})`}>
        <ellipse
          cx={centerX}
          cy={EYE_Y}
          rx={EYE_RX}
          ry={EYE_RY}
          fill="#fbfcfe"
        />

        <g ref={irisRef}>
          <circle cx={centerX} cy={EYE_Y} r="6.6" fill="#3d5a80" />
          <circle cx={centerX} cy={EYE_Y} r="3" fill="#171b28" />
          <circle
            cx={centerX - 2.4}
            cy={EYE_Y - 2.6}
            r="2"
            fill="#ffffff"
            opacity="0.9"
          />
        </g>

        {/* The lid sits just above the eye and is translated down to close
            it, so a blink is one number rather than a redrawn shape. */}
        <g ref={lidRef}>
          <rect
            x={centerX - EYE_RX - 2}
            y={EYE_Y - EYE_RY * 3 - 4}
            width={EYE_RX * 2 + 4}
            height={EYE_RY * 2 + 4}
            fill="url(#aiSkin)"
          />
          <path
            d={`M ${centerX - EYE_RX - 1} ${EYE_Y - EYE_RY - 4}
                Q ${centerX} ${EYE_Y - EYE_RY - 1}
                  ${centerX + EYE_RX + 1} ${EYE_Y - EYE_RY - 4}`}
            fill="none"
            stroke="#c98f68"
            strokeWidth="1.6"
          />
        </g>
      </g>

      {/* Lash line, outside the clip so it reads as the edge of the lid. */}
      <path
        d={`M ${centerX - EYE_RX} ${EYE_Y - 2}
            Q ${centerX} ${EYE_Y - EYE_RY - 2.5}
              ${centerX + EYE_RX} ${EYE_Y - 2}`}
        fill="none"
        stroke="#4a4055"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </g>
  )
}

export default AiInterviewer
