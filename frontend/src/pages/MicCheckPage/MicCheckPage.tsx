import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { Alert, Box, Button, Card, CardContent, Typography } from '@mui/material'
import MicIcon from '@mui/icons-material/Mic'
import MicOffIcon from '@mui/icons-material/MicOff'
import VideocamIcon from '@mui/icons-material/Videocam'
import styles from './MicCheckPage.module.css'

type PermissionStatus = 'idle' | 'requesting' | 'granted' | 'denied'

export default function MicCheckPage() {
  const { interviewId } = useParams()
  const navigate = useNavigate()

  const [micStatus, setMicStatus] = useState<PermissionStatus>('idle')
  const [cameraStatus, setCameraStatus] = useState<PermissionStatus>('idle')
  const [micLevel, setMicLevel] = useState(0)

  const micStreamRef = useRef<MediaStream | null>(null)
  const cameraStreamRef = useRef<MediaStream | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const rafRef = useRef<number | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)

  const stopMicMeter = () => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    audioCtxRef.current?.close().catch(() => {})
    audioCtxRef.current = null
  }

  const startMicMeter = (stream: MediaStream) => {
    const audioCtx = new AudioContext()
    audioCtxRef.current = audioCtx
    const source = audioCtx.createMediaStreamSource(stream)
    const analyser = audioCtx.createAnalyser()
    analyser.fftSize = 256
    source.connect(analyser)
    const data = new Uint8Array(analyser.frequencyBinCount)
    const tick = () => {
      analyser.getByteFrequencyData(data)
      const avg = data.reduce((sum, v) => sum + v, 0) / data.length
      setMicLevel(Math.min(1, avg / 128))
      rafRef.current = requestAnimationFrame(tick)
    }
    tick()
  }

  const requestMic = async () => {
    setMicStatus('requesting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      micStreamRef.current = stream
      setMicStatus('granted')
      startMicMeter(stream)
    } catch {
      setMicStatus('denied')
    }
  }

  const requestCamera = async () => {
    setCameraStatus('requesting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      cameraStreamRef.current = stream
      setCameraStatus('granted')
      if (videoRef.current) videoRef.current.srcObject = stream
    } catch {
      setCameraStatus('denied')
    }
  }

  // Ask for the microphone as soon as the page loads — this is the whole
  // point of a pre-interview check. Camera stays opt-in (it's optional
  // in the interview room too).
  useEffect(() => {
    void requestMic()
    return () => {
      stopMicMeter()
      micStreamRef.current?.getTracks().forEach((track) => track.stop())
      cameraStreamRef.current?.getTracks().forEach((track) => track.stop())
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleContinue = () => {
    stopMicMeter()
    micStreamRef.current?.getTracks().forEach((track) => track.stop())
    cameraStreamRef.current?.getTracks().forEach((track) => track.stop())
    navigate(`/interview/${interviewId}`)
  }

  if (!interviewId) {
    navigate('/screening-results')
    return null
  }

  return (
    <Box className={styles.page}>
      <Card variant="outlined" className={styles.card}>
        <CardContent>
          <Typography variant="h5" fontWeight={700} textAlign="center">
            Let's check your microphone
          </Typography>
          <Typography variant="body1" color="text.secondary" textAlign="center" mt={1} mb={3}>
            We need access to your microphone so the interviewer can hear your answers.
          </Typography>

          <Box className={styles.micRow}>
            {micStatus === 'granted' ? (
              <MicIcon color="success" fontSize="large" />
            ) : (
              <MicOffIcon color={micStatus === 'denied' ? 'error' : 'disabled'} fontSize="large" />
            )}
            <Box className={styles.levelTrack}>
              <Box
                className={styles.levelFill}
                sx={{ width: `${micStatus === 'granted' ? Math.round(micLevel * 100) : 0}%` }}
              />
            </Box>
          </Box>

          {micStatus === 'requesting' && (
            <Typography variant="body2" color="text.secondary" textAlign="center" mt={1}>
              Waiting for microphone permission...
            </Typography>
          )}
          {micStatus === 'granted' && (
            <Typography variant="body2" color="success.main" textAlign="center" mt={1}>
              Microphone connected — try saying something.
            </Typography>
          )}
          {micStatus === 'denied' && (
            <Alert severity="error" sx={{ mt: 2 }}>
              Microphone access was blocked. Allow it from your browser's address-bar icon,
              then try again.
            </Alert>
          )}
          {micStatus === 'denied' && (
            <Button variant="outlined" onClick={() => void requestMic()} sx={{ mt: 2 }} fullWidth>
              Try Again
            </Button>
          )}

          <Box className={styles.cameraSection}>
            <Typography variant="subtitle2" color="text.secondary">
              Camera (optional)
            </Typography>
            {cameraStatus !== 'granted' ? (
              <Button
                variant="text"
                startIcon={<VideocamIcon />}
                onClick={() => void requestCamera()}
                disabled={cameraStatus === 'requesting'}
              >
                Test Camera
              </Button>
            ) : (
              <video ref={videoRef} autoPlay muted playsInline className={styles.cameraPreview} />
            )}
            {cameraStatus === 'denied' && (
              <Typography variant="body2" color="text.secondary">
                Camera access wasn't granted. You can still continue — camera is optional.
              </Typography>
            )}
          </Box>

          <Button
            variant="contained"
            size="large"
            fullWidth
            disabled={micStatus !== 'granted'}
            onClick={handleContinue}
            sx={{ mt: 3 }}
          >
            Continue to Interview
          </Button>
        </CardContent>
      </Card>
    </Box>
  )
}