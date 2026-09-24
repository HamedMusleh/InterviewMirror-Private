/**
 * Acoustic voice activity detection for the interview room.
 *
 * Answers one narrow question continuously: is the candidate making speech
 * sounds right now? It deliberately does not decide whether they have
 * finished their answer — that needs the transcript, which lives on the
 * server. This half only reports speech and silence, and how long the
 * current silence has lasted.
 *
 * Two details do most of the work in making it reliable:
 *
 * Adaptive noise floor. A fixed decibel threshold fails the moment someone
 * sits in a noisier room than whoever picked the number. Instead the floor
 * tracks the ambient level, falling quickly toward quiet and rising only
 * slowly — and never while speech is in progress, since otherwise a loud
 * answer drags the floor up behind it and the detector goes deaf mid-answer.
 *
 * Hysteresis. Speech has to clear a higher bar to start than to stop, and
 * both transitions need several consecutive frames to agree. Without this
 * the detector flaps on every consonant and every breath.
 *
 * The analysis runs in an AudioWorklet, off the main thread, so a busy React
 * render can never delay it.
 */

export interface VoiceActivityOptions {
  /** How far above the noise floor counts as speech starting. */
  onsetMarginDb?: number
  /** How far above the noise floor speech must fall below to stop. */
  offsetMarginDb?: number
  /** Consecutive loud frames required before speech is declared. */
  onsetFrames?: number
  /** Consecutive quiet frames required before silence is declared. */
  offsetFrames?: number
}

export interface VoiceActivityHandlers {
  onSpeechStart?: () => void
  onSpeechEnd?: () => void
  /** Normalised 0..1 level, for a live input meter. */
  onLevel?: (level: number) => void
}

/*
 * Tuned to ignore the room rather than to catch every syllable.
 *
 * The transcript is what actually ends a turn now, so a missed syllable
 * here costs nothing — the countdown simply starts a fraction later. A
 * false trigger, on the other hand, makes the interview look like it is
 * listening to a notification chime. So both the onset margin and the
 * number of frames that must agree are set higher than pure speech
 * detection would need: a chime or a click no longer sustains long enough
 * to register as somebody talking.
 */
const DEFAULTS: Required<VoiceActivityOptions> = {
  onsetMarginDb: 13,
  offsetMarginDb: 7,
  onsetFrames: 6,
  offsetFrames: 6,
}

/**
 * The worklet source, kept as a string and loaded through a blob URL so the
 * detector works without any bundler configuration for worklet assets.
 */
const WORKLET_SOURCE = `
class VadProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super()

    const settings = options.processorOptions || {}

    this.onsetMarginDb = settings.onsetMarginDb
    this.offsetMarginDb = settings.offsetMarginDb
    this.onsetFrames = settings.onsetFrames
    this.offsetFrames = settings.offsetFrames

    // ~20ms of audio per analysis frame at any sample rate.
    this.frameSize = Math.max(128, Math.round(sampleRate * 0.02))

    this.frame = new Float32Array(this.frameSize)
    this.filled = 0

    // Starts pessimistically low so the first real frames pull it up to the
    // room rather than the room having to fight a wrong initial guess.
    this.noiseFloorDb = -75
    this.calibrating = true
    this.framesSeen = 0

    this.speaking = false
    this.loudFrames = 0
    this.quietFrames = 0
    this.framesSinceLevel = 0
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0]

    if (!channel) {
      return true
    }

    for (let i = 0; i < channel.length; i += 1) {
      this.frame[this.filled] = channel[i]
      this.filled += 1

      if (this.filled === this.frameSize) {
        this.analyse()
        this.filled = 0
      }
    }

    return true
  }

  analyse() {
    let sum = 0

    for (let i = 0; i < this.frameSize; i += 1) {
      sum += this.frame[i] * this.frame[i]
    }

    const rms = Math.sqrt(sum / this.frameSize)
    const db = 20 * Math.log10(Math.max(rms, 1e-10))

    this.framesSeen += 1

    // First ~400ms: take the room at face value to converge quickly.
    if (this.calibrating) {
      this.noiseFloorDb = this.framesSeen === 1
        ? db
        : this.noiseFloorDb + (db - this.noiseFloorDb) * 0.3

      if (this.framesSeen >= 20) {
        this.calibrating = false
      }
    } else if (db < this.noiseFloorDb) {
      // Drop toward quiet quickly.
      this.noiseFloorDb += (db - this.noiseFloorDb) * 0.25
    } else if (!this.speaking) {
      // Creep upward only between utterances.
      this.noiseFloorDb += (db - this.noiseFloorDb) * 0.005
    }

    const onsetDb = this.noiseFloorDb + this.onsetMarginDb
    const offsetDb = this.noiseFloorDb + this.offsetMarginDb

    if (!this.speaking) {
      if (db > onsetDb) {
        this.loudFrames += 1

        if (this.loudFrames >= this.onsetFrames) {
          this.speaking = true
          this.quietFrames = 0
          this.port.postMessage({ type: 'speech-start' })
        }
      } else {
        this.loudFrames = 0
      }
    } else {
      if (db < offsetDb) {
        this.quietFrames += 1

        if (this.quietFrames >= this.offsetFrames) {
          this.speaking = false
          this.loudFrames = 0
          this.port.postMessage({ type: 'speech-end' })
        }
      } else {
        this.quietFrames = 0
      }
    }

    // Throttle the meter; the UI cannot use 50 updates a second.
    this.framesSinceLevel += 1

    if (this.framesSinceLevel >= 3) {
      this.framesSinceLevel = 0

      const headroom = db - this.noiseFloorDb
      const level = Math.min(1, Math.max(0, headroom / 40))

      this.port.postMessage({ type: 'level', level: level })
    }
  }
}

registerProcessor('vad-processor', VadProcessor)
`

export class VoiceActivityDetector {
  private context: AudioContext | null = null
  private source: MediaStreamAudioSourceNode | null = null
  private node: AudioWorkletNode | null = null

  private speaking = false
  private silenceSince: number | null = null

  private readonly options: Required<VoiceActivityOptions>
  private readonly handlers: VoiceActivityHandlers

  constructor(
    handlers: VoiceActivityHandlers = {},
    options: VoiceActivityOptions = {},
  ) {
    this.handlers = handlers
    this.options = { ...DEFAULTS, ...options }
  }

  /** True while the candidate is currently producing speech. */
  get isSpeaking(): boolean {
    return this.speaking
  }

  /**
   * Milliseconds since speech last stopped, or null if they are still
   * talking (or have not started yet).
   */
  get silenceDurationMs(): number | null {
    if (this.speaking || this.silenceSince === null) {
      return null
    }

    return performance.now() - this.silenceSince
  }

  async attach(stream: MediaStream): Promise<void> {
    const context = new AudioContext()

    try {
      const blob = new Blob([WORKLET_SOURCE], {
        type: 'application/javascript',
      })
      const workletUrl = URL.createObjectURL(blob)

      try {
        await context.audioWorklet.addModule(workletUrl)
      } finally {
        URL.revokeObjectURL(workletUrl)
      }

      const node = new AudioWorkletNode(context, 'vad-processor', {
        numberOfInputs: 1,
        numberOfOutputs: 0,
        processorOptions: this.options,
      })

      node.port.onmessage = (event) => this.handleMessage(event.data)

      const source = context.createMediaStreamSource(stream)
      source.connect(node)

      this.context = context
      this.source = source
      this.node = node
    } catch (attachError) {
      // Otherwise a failed attach leaves an open AudioContext behind, and
      // browsers cap how many a page may hold.
      await context.close()
      throw attachError
    }
  }

  /**
   * Treat this moment as the start of a fresh turn.
   *
   * Called when a new question begins, so silence accumulated while the
   * question was being read aloud does not count against the candidate.
   */
  reset(): void {
    this.speaking = false
    this.silenceSince = null
  }

  dispose(): void {
    if (this.node) {
      this.node.port.onmessage = null
      this.node.disconnect()
      this.node = null
    }

    this.source?.disconnect()
    this.source = null

    void this.context?.close()
    this.context = null

    this.reset()
  }

  private handleMessage(data: { type: string; level?: number }): void {
    if (data.type === 'speech-start') {
      this.speaking = true
      this.silenceSince = null
      this.handlers.onSpeechStart?.()
      return
    }

    if (data.type === 'speech-end') {
      this.speaking = false
      this.silenceSince = performance.now()
      this.handlers.onSpeechEnd?.()
      return
    }

    if (data.type === 'level' && typeof data.level === 'number') {
      this.handlers.onLevel?.(data.level)
    }
  }
}
