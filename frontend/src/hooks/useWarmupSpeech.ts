import { useCallback, useEffect, useRef, useState } from 'react'

interface SpeechRecognitionAlternativeLike {
  transcript: string
}

interface SpeechRecognitionResultLike {
  isFinal: boolean
  length: number
  [index: number]: SpeechRecognitionAlternativeLike
}

interface SpeechRecognitionResultListLike {
  length: number
  [index: number]: SpeechRecognitionResultLike
}

interface SpeechRecognitionEventLike extends Event {
  results: SpeechRecognitionResultListLike
}

interface SpeechRecognitionErrorEventLike extends Event {
  error: string
}

interface BrowserSpeechRecognition {
  continuous: boolean
  interimResults: boolean
  lang: string
  onend: (() => void) | null
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}

type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition

interface SpeechRecognitionWindow extends Window {
  SpeechRecognition?: BrowserSpeechRecognitionConstructor
  webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor
}

export type WarmupSpeechPhase =
  | 'idle'
  | 'listening'
  | 'complete'
  | 'unsupported'
  | 'error'

export interface WarmupSpeechState {
  phase: WarmupSpeechPhase
  transcript: string
  error: string | null
}

const MAX_WARMUP_DURATION_MS = 8_000

function createRecognition(): BrowserSpeechRecognition | null {
  const speechWindow = window as SpeechRecognitionWindow
  const Recognition =
    speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition

  return Recognition ? new Recognition() : null
}

/**
 * Captures one short, disposable warm-up response before the scored interview.
 * It deliberately uses the browser's speech recognition instead of the answer
 * WebSocket, so the greeting never becomes an interview answer or affects a
 * candidate's evaluation.
 */
export function useWarmupSpeech(
  onFinished?: (transcript: string) => void,
) {
  const [state, setState] = useState<WarmupSpeechState>({
    phase: 'idle',
    transcript: '',
    error: null,
  })

  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null)
  const timeoutRef = useRef<number | null>(null)
  const transcriptRef = useRef('')
  const finishedRef = useRef(false)
  const onFinishedRef = useRef(onFinished)

  useEffect(() => {
    onFinishedRef.current = onFinished
  }, [onFinished])

  const clearTimeoutRef = useCallback(() => {
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
  }, [])

  const complete = useCallback(() => {
    if (finishedRef.current) {
      return
    }

    finishedRef.current = true
    clearTimeoutRef()

    try {
      recognitionRef.current?.stop()
    } catch {
      // The browser can report an invalid state when recognition ended itself.
    }

    recognitionRef.current = null

    const transcript = transcriptRef.current.trim()

    setState((previous) => ({
      ...previous,
      phase: 'complete',
      transcript,
      error: null,
    }))

    onFinishedRef.current?.(transcript)
  }, [clearTimeoutRef])

  const start = useCallback(() => {
    if (recognitionRef.current) {
      return
    }

    const recognition = createRecognition()

    if (!recognition) {
      setState({
        phase: 'unsupported',
        transcript: '',
        error: 'Quick voice check-in is not supported in this browser.',
      })
      return
    }

    clearTimeoutRef()
    transcriptRef.current = ''
    finishedRef.current = false

    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (event) => {
      let transcript = ''

      for (let index = 0; index < event.results.length; index += 1) {
        transcript += `${event.results[index][0].transcript} `
      }

      transcriptRef.current = transcript.trim()
      setState((previous) => ({
        ...previous,
        transcript: transcriptRef.current,
      }))
    }

    recognition.onerror = (event) => {
      if (finishedRef.current) {
        return
      }

      if (event.error === 'no-speech' || event.error === 'aborted') {
        complete()
        return
      }

      finishedRef.current = true
      clearTimeoutRef()
      recognitionRef.current = null
      setState((previous) => ({
        ...previous,
        phase: 'error',
        error: 'I could not hear the check-in. You can skip it and begin.',
      }))
    }

    recognition.onend = () => {
      if (!finishedRef.current) {
        complete()
      }
    }

    recognitionRef.current = recognition

    try {
      recognition.start()
      setState({ phase: 'listening', transcript: '', error: null })
      timeoutRef.current = window.setTimeout(complete, MAX_WARMUP_DURATION_MS)
    } catch {
      finishedRef.current = true
      clearTimeoutRef()
      recognitionRef.current = null
      setState({
        phase: 'error',
        transcript: '',
        error: 'I could not access voice input. You can skip it and begin.',
      })
    }
  }, [clearTimeoutRef, complete])

  const cancel = useCallback(() => {
    finishedRef.current = true
    clearTimeoutRef()

    try {
      recognitionRef.current?.abort()
    } catch {
      // The recognition session may already have ended.
    }

    recognitionRef.current = null
    transcriptRef.current = ''
    setState({ phase: 'idle', transcript: '', error: null })
  }, [clearTimeoutRef])

  useEffect(
    () => () => {
      finishedRef.current = true
      clearTimeoutRef()

      try {
        recognitionRef.current?.abort()
      } catch {
        // The recognition session may already have ended.
      }

      recognitionRef.current = null
    },
    [clearTimeoutRef],
  )

  return { ...state, start, finish: complete, cancel }
}
