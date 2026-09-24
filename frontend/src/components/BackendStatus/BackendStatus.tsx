import { useState } from 'react'
import styles from './BackendStatus.module.css'

type StatusResponse = {
  status: string
}

export default function BackendStatus() {  const [status, setStatus] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleCallBackend = async () => {
    setIsLoading(true)
    setError('')

    try {
      const response = await fetch('http://127.0.0.1:8000/api/status')

      if (!response.ok) {
        throw new Error('Failed to connect to the backend')
      }

      const data: StatusResponse = await response.json()
      setStatus(data.status)
    } catch {
      setError('Unable to connect to the backend')
      setStatus('')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <button
        type="button"
        className={styles.button}
        onClick={handleCallBackend}
        disabled={isLoading}
      >
        {isLoading ? 'Calling backend...' : 'Call Backend'}
      </button>

      {status && <p className={styles.success}>Backend status: {status}</p>}
      {error && <p className={styles.error}>{error}</p>}
    </div>
  )
}