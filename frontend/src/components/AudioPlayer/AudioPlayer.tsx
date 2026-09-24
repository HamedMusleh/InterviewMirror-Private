import { useEffect, useRef, useState } from 'react'
import {
  Pause,
  PlayArrow,
  Replay,
  VolumeOff,
  VolumeUp,
} from '@mui/icons-material'
import { IconButton, Slider, Tooltip } from '@mui/material'

import {
  DEFAULT_VOLUME,
  PLAYBACK_STATE,
  VOLUME_MAX,
  VOLUME_MIN,
  VOLUME_STEP,
  type PlaybackState,
} from './AudioPlayer.const'
import styles from './AudioPlayer.module.css'

const EMPTY_CAPTIONS_SRC = 'data:text/vtt,WEBVTT'

interface AudioPlayerProps {
  audioSrc: string | null
  captions: string
  autoPlay?: boolean
  onPlaybackStateChange?: (state: PlaybackState) => void
  /*
   * Hands the underlying element to the parent.
   *
   * The avatar lip-syncs against this element's `currentTime`, and it has to
   * be this element rather than a timer started next to it: only the element
   * knows when it stalled to buffer, and a parallel clock would drift past
   * the audio with no way back into step.
   */
  onAudioElement?: (element: HTMLAudioElement | null) => void
  className?: string
}

function AudioPlayer({
  audioSrc,
  captions,
  autoPlay = false,
  onPlaybackStateChange,
  onAudioElement,
  className,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [captionSrc, setCaptionSrc] = useState<string | null>(null)

  const [playbackState, setPlaybackState] = useState<PlaybackState>(
    PLAYBACK_STATE.IDLE,
  )
  const [volume, setVolume] = useState(DEFAULT_VOLUME)

  useEffect(() => {
    const audioElement = audioRef.current

    if (!audioElement) return

    audioElement.pause()
    audioElement.currentTime = 0
    setPlaybackState(PLAYBACK_STATE.IDLE)
  }, [audioSrc])

  /*
   * Start playback, once the element can actually play.
   *
   * Two things had to survive being merged here. Waiting for `canplay`
   * rather than calling `play()` the instant the source is set matters for
   * short generated clips, because the element may still be fetching the
   * blob. And a refusal has to be distinguishable from an interruption: an
   * abort means a newer line replaced this one mid-play, which is ordinary,
   * while anything else is the browser declining, and the parent has to hear
   * about that or the interview waits forever for an `ended` event that
   * cannot arrive.
   */
  useEffect(() => {
    const audioElement = audioRef.current

    if (!audioElement || !audioSrc || !autoPlay) {
      return
    }

    let cancelled = false

    const playAudio = async () => {
      try {
        await audioElement.play()

        if (!cancelled) {
          setPlaybackState(PLAYBACK_STATE.PLAYING)
        }
      } catch (playError) {
        if (!cancelled && (playError as Error)?.name !== 'AbortError') {
          setPlaybackState(PLAYBACK_STATE.BLOCKED)
        }
      }
    }

    if (audioElement.readyState >= HTMLMediaElement.HAVE_ENOUGH_DATA) {
      void playAudio()

      return () => {
        cancelled = true
      }
    }

    const handleCanPlay = () => {
      void playAudio()
    }

    audioElement.addEventListener('canplay', handleCanPlay, { once: true })

    return () => {
      cancelled = true
      audioElement.removeEventListener('canplay', handleCanPlay)
    }
  }, [audioSrc, autoPlay])

  /*
   * Report transitions, not renders.
   *
   * `onPlaybackStateChange` is rebuilt by the parent whenever the interview
   * moves on, and without this guard that new identity re-delivers the last
   * state against the new stage. A finished line was being reported a second
   * time as "ended" just after the stage advanced, which opened the
   * microphone before the next question had even been fetched — so the
   * recording captured the interviewer talking and the answer came back
   * empty.
   */
  const lastReportedRef = useRef<PlaybackState | null>(null)

  useEffect(() => {
    if (lastReportedRef.current === playbackState) {
      return
    }

    lastReportedRef.current = playbackState
    onPlaybackStateChange?.(playbackState)
  }, [playbackState, onPlaybackStateChange])

  useEffect(() => {
    onAudioElement?.(audioRef.current)

    return () => onAudioElement?.(null)
  }, [audioSrc, onAudioElement])

  useEffect(() => {
    const captionText = captions.trim()

    if (!captionText) {
      setCaptionSrc(null)
      return
    }

    const vtt = `WEBVTT\n\n00:00:00.000 --> 99:59:59.999\n${captionText.replace(/\r?\n/g, " ")}\n`
    const nextCaptionSrc = URL.createObjectURL(
      new Blob([vtt], { type: "text/vtt" }),
    )

    setCaptionSrc(nextCaptionSrc)

    return () => URL.revokeObjectURL(nextCaptionSrc)
  }, [captions])

  const handlePlayPause = async () => {
    const audioElement = audioRef.current

    if (!audioElement) return

    if (playbackState === PLAYBACK_STATE.PLAYING) {
      audioElement.pause()
      setPlaybackState(PLAYBACK_STATE.PAUSED)
      return
    }

    if (playbackState === PLAYBACK_STATE.ENDED) {
      audioElement.currentTime = 0
    }

    try {
      await audioElement.play()
      setPlaybackState(PLAYBACK_STATE.PLAYING)
    } catch {
      setPlaybackState(PLAYBACK_STATE.IDLE)
    }
  }

  const handleReplay = async () => {
    const audioElement = audioRef.current

    if (!audioElement) return

    audioElement.currentTime = 0

    try {
      await audioElement.play()
      setPlaybackState(PLAYBACK_STATE.PLAYING)
    } catch {
      setPlaybackState(PLAYBACK_STATE.IDLE)
    }
  }

  const handleVolumeChange = (_event: Event, newValue: number | number[]) => {
    const nextVolume = Array.isArray(newValue) ? newValue[0] : newValue

    setVolume(nextVolume)

    if (audioRef.current) {
      audioRef.current.volume = nextVolume
    }
  }

  const handleEnded = () => {
    setPlaybackState(PLAYBACK_STATE.ENDED)
  }

  const isPlaying = playbackState === PLAYBACK_STATE.PLAYING
  const isMuted = volume === VOLUME_MIN

  if (!audioSrc) {
    return null
  }

  return (
    <div className={`${styles.audioPlayer} ${className ?? ''}`}>
      <audio
        ref={audioRef}
        src={audioSrc}
        onEnded={handleEnded}
        aria-label="Question audio"
      >
        <track
          kind="captions"
          src={captionSrc ?? EMPTY_CAPTIONS_SRC}
          srcLang="en"
          label="Question captions"
          default
        />
      </audio>

      <Tooltip title={isPlaying ? 'Pause' : 'Play'}>
        <IconButton
          aria-label={isPlaying ? 'Pause' : 'Play'}
          onClick={handlePlayPause}
        >
          {isPlaying ? <Pause /> : <PlayArrow />}
        </IconButton>
      </Tooltip>

      <Tooltip title="Replay">
        <IconButton
          aria-label="Replay question audio"
          onClick={handleReplay}
        >
          <Replay />
        </IconButton>
      </Tooltip>

      <div className={styles.volumeControl}>
        {isMuted ? <VolumeOff /> : <VolumeUp />}

        <Slider
          aria-label="Volume"
          value={volume}
          min={VOLUME_MIN}
          max={VOLUME_MAX}
          step={VOLUME_STEP}
          onChange={handleVolumeChange}
          className={styles.volumeSlider}
        />
      </div>
    </div>
  )
}

export default AudioPlayer
