/**
 * The microphones the candidate could be interviewed through.
 *
 * Worth offering as a choice rather than trusting the system default,
 * because the default is often wrong in exactly the way that ruins an
 * interview: a monitor's built-in microphone across the room, or a loopback
 * device like "Stereo Mix" that hears everything the computer plays. A
 * candidate wearing a headset can be recorded through their laptop lid
 * without any indication that is what is happening.
 *
 * Device labels are only populated once microphone permission has been
 * granted, so the list is re-read after the interview's first turn opens.
 */

import { useCallback, useEffect, useState } from 'react'

export interface AudioInput {
  deviceId: string
  label: string
}

export function useAudioInputs(): AudioInput[] {
  const [inputs, setInputs] = useState<AudioInput[]>([])

  const refresh = useCallback(async () => {
    if (!navigator.mediaDevices?.enumerateDevices) {
      return
    }

    try {
      const devices = await navigator.mediaDevices.enumerateDevices()

      setInputs(
        devices
          .filter((device) => device.kind === 'audioinput')
          // Before permission is granted every label is an empty string, so
          // there is nothing to choose between. Numbering them at least
          // keeps the list usable if labels never arrive.
          .map((device, index) => ({
            deviceId: device.deviceId,
            label: device.label || `Microphone ${index + 1}`,
          }))
          // The synthetic "default"/"communications" entries duplicate a real
          // device under a name that hides which one it actually is.
          .filter((device) => device.deviceId !== 'communications'),
      )
    } catch {
      // Enumeration is a convenience. Failing it must not stop an interview.
      setInputs([])
    }
  }, [])

  useEffect(() => {
    void refresh()

    navigator.mediaDevices?.addEventListener?.('devicechange', refresh)

    return () => {
      navigator.mediaDevices?.removeEventListener?.('devicechange', refresh)
    }
  }, [refresh])

  return inputs
}
