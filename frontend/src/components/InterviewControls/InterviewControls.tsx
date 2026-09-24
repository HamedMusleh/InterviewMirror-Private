import {
  CallEnd,
  Videocam,
  VideocamOff,
  Mic,
  MicOff,
} from '@mui/icons-material'

import { IconButton, Tooltip } from '@mui/material'
import styles from './InterviewControls.module.css'

interface InterviewControlsProps {
  cameraEnabled: boolean
  microphoneEnabled: boolean
  onToggleCamera: () => void
  onToggleMicrophone: () => void
  onLeave: () => void
}

/**
 * Deliberately no record button and no next button.
 *
 * The interview listens continuously and decides when an answer has ended,
 * so asking the candidate to press record and stop would be asking them to
 * do work the system already does. Advancing is the server's decision too,
 * since answering can produce a follow-up question that did not exist a
 * moment ago. Ending a turn early is still possible — that control lives on
 * the turn indicator, next to the countdown it interrupts.
 */
function InterviewControls({
  cameraEnabled,
  microphoneEnabled,
  onToggleCamera,
  onToggleMicrophone,
  onLeave,
}: InterviewControlsProps) {
  return (
    <div className={styles.controls}>
      <Tooltip title="Leave interview">
        <IconButton
          aria-label="Leave interview"
          onClick={onLeave}
          className={styles.leaveButton}
        >
          <CallEnd />
        </IconButton>
      </Tooltip>

      <Tooltip title={cameraEnabled ? 'Turn camera off' : 'Turn camera on'}>
        <IconButton
          aria-label={cameraEnabled ? 'Turn camera off' : 'Turn camera on'}
          onClick={onToggleCamera}
        >
          {cameraEnabled ? <Videocam /> : <VideocamOff />}
        </IconButton>
      </Tooltip>

      <Tooltip
        title={microphoneEnabled ? 'Mute microphone' : 'Unmute microphone'}
      >
        <IconButton
          aria-label={
            microphoneEnabled ? 'Mute microphone' : 'Unmute microphone'
          }
          onClick={onToggleMicrophone}
        >
          {microphoneEnabled ? <Mic /> : <MicOff />}
        </IconButton>
      </Tooltip>

    </div>
  )
}

export default InterviewControls
