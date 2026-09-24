import { useEffect, useRef } from 'react'

import styles from './InterviewVideo.module.css'

interface InterviewVideoProps {
  elapsedTime: number
  /** True while the microphone is open and capturing. */
  live?: boolean
  /** Live camera stream for the candidate video preview. */
  stream?: MediaStream | null
  /** Whether the camera is currently enabled. */
  cameraEnabled?: boolean
}

function formatTime(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60

  return `${minutes.toString().padStart(2, '0')}:${remainingSeconds
    .toString()
    .padStart(2, '0')}`
}

function InterviewVideo({
  elapsedTime,
  live = false,
  stream = null,
  cameraEnabled = false,
}: InterviewVideoProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null)

  useEffect(() => {
    const video = videoRef.current

    if (!video) {
      return
    }

    if (!stream || !cameraEnabled) {
      video.srcObject = null
      return
    }

    video.srcObject = stream

    void video.play().catch(() => {
      // Browser may block autoplay until user interaction.
    })

    return () => {
      video.srcObject = null
    }
  }, [stream, cameraEnabled])

  return (
    <section className={styles.videoContainer}>
      {stream && cameraEnabled ? (
        <video
          ref={videoRef}
          className={styles.video}
          autoPlay
          muted
          playsInline
        />
      ) : (
        <p className={styles.placeholder}>Camera is off</p>
      )}

      <div className={styles.timer}>
        <span className={styles.recordingDot} data-live={live} />
        <span>{formatTime(elapsedTime)}</span>
      </div>
    </section>
  )
}

export default InterviewVideo

