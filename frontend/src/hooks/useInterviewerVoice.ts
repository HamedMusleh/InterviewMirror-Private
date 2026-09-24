/**
 * Fetches the audio for whatever the interviewer is about to say.
 *
 * Playback is not handled here — `AudioPlayer` owns that, because the
 * candidate needs to be able to replay a question and adjust the volume.
 * This hook only turns a line of text into a playable clip and the mouth
 * timeline that goes on top of it, and makes sure the object URL behind that
 * clip is released when the interviewer moves on.
 */

import { useEffect, useState } from 'react'

import { getSpokenLine, type VisemeMark } from '../services/textToSpeechApi'

export interface Utterance {
  /*
   * Distinguishes two utterances that happen to read the same.
   *
   * Without it, an interviewer that says "Thank you. Let's continue." twice
   * in a row would not re-fetch the second one, and the room would sit
   * waiting for an `ended` event from audio that never started.
   */
  key: string
  text: string
  style: string
  /** Spoken after `text`, with a real pause in between. */
  then?: string
}

export interface InterviewerVoice {
  audioUrl: string | null
  visemes: VisemeMark[]
  loading: boolean
  /** Set when synthesis failed. The line is still readable on screen. */
  error: string | null
  /*
   * How long the clip actually runs, straight from the synthesiser.
   *
   * The room needs an upper bound on how long to wait for playback to
   * finish in case the `ended` event never arrives. Measured is far better
   * than guessed: a guess from character count has to be generous enough
   * for the worst case, which means every ordinary line sits through a
   * wait several times longer than the audio it is covering.
   */
  durationMs: number | null
}

export function useInterviewerVoice(
  utterance: Utterance | null,
): InterviewerVoice {
  const [voice, setVoice] = useState<InterviewerVoice>({
    audioUrl: null,
    visemes: [],
    loading: false,
    error: null,
    durationMs: null,
  })

  const key = utterance?.key ?? null
  const text = utterance?.text ?? null
  const style = utterance?.style ?? 'chat'
  const then = utterance?.then

  useEffect(() => {
    if (!key || !text) {
      setVoice({
        audioUrl: null,
        visemes: [],
        loading: false,
        error: null,
        durationMs: null,
      })

      return
    }

    let cancelled = false
    let objectUrl: string | null = null

    setVoice({
      audioUrl: null,
      visemes: [],
      loading: true,
      error: null,
      durationMs: null,
    })

    const load = async () => {
      try {
        const line = await getSpokenLine(text, style, then)

        objectUrl = line.audioUrl

        if (cancelled) {
          URL.revokeObjectURL(objectUrl)
          return
        }

        setVoice({
          audioUrl: line.audioUrl,
          visemes: line.visemes,
          loading: false,
          error: null,
          durationMs: line.durationMs,
        })
      } catch {
        if (!cancelled) {
          setVoice({
            audioUrl: null,
            visemes: [],
            loading: false,
            durationMs: null,
            error:
              'The interviewer’s voice is unavailable. You can read ' +
              'along below.',
          })
        }
      }
    }

    void load()

    return () => {
      cancelled = true

      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
      }
    }
  }, [key, text, style, then])

  return voice
}
