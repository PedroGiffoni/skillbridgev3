import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from './api'

export function useLearningRequest(onExpired: () => void) {
  const controller = useRef<AbortController | null>(null)
  const expired = useRef(onExpired)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { expired.current = onExpired }, [onExpired])
  useEffect(() => () => controller.current?.abort(), [])

  const run = useCallback(async (task: (signal: AbortSignal) => Promise<void>) => {
    controller.current?.abort()
    const active = new AbortController()
    controller.current = active
    setBusy(true)
    setError('')
    try {
      await task(active.signal)
    } catch (failure) {
      if (active.signal.aborted) return
      if (failure instanceof ApiError && failure.status === 401) expired.current()
      else setError(failure instanceof Error ? failure.message : 'Não foi possível concluir. Tente novamente.')
    } finally {
      if (!active.signal.aborted) {
        controller.current = null
        setBusy(false)
      }
    }
  }, [])
  return { busy, error, run }
}