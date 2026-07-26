import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchState, setScene, turnOff } from './api'
import type { Scene } from './api'

const POLL_MS = 5000

/**
 * Owns all panel state. Scene changes apply optimistically so a tap feels
 * instant on a phone, then reconcile against the daemon's actual state on the
 * next poll (or immediately, on failure).
 */
export function usePanel() {
  const [scenes, setScenes] = useState<Scene[]>([])
  const [current, setCurrent] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Suppresses a poll landing between an optimistic update and its confirmation.
  const pending = useRef(false)

  const refresh = useCallback(async () => {
    if (pending.current) return
    try {
      const state = await fetchState()
      if (pending.current) return
      setScenes(state.scenes)
      setCurrent(state.current)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
    const id = setInterval(() => void refresh(), POLL_MS)
    return () => clearInterval(id)
  }, [refresh])

  const apply = useCallback(
    async (next: string | null, action: () => Promise<unknown>) => {
      const previous = current
      pending.current = true
      setCurrent(next)
      setError(null)
      try {
        await action()
      } catch (err) {
        setCurrent(previous) // roll back to what the daemon still has
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        pending.current = false
      }
      void refresh()
    },
    [current, refresh],
  )

  const play = useCallback(
    (name: string) => apply(name, () => setScene(name)),
    [apply],
  )
  const off = useCallback(() => apply(null, turnOff), [apply])

  return { scenes, current, loading, error, play, off }
}
