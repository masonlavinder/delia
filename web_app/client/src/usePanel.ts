import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { fetchBackgrounds, fetchOverlays, setScene, turnOff } from './api'
import type { Item } from './api'

const POLL_MS = 5000

/** Split a composed scene name ("plasma-clock-date") back into the selection.
 * Names contain no dashes, so a plain split + membership check is unambiguous. */
function parseSelection(
  current: string | null,
  bgNames: Set<string>,
  ovNames: Set<string>,
): { background: string | null; overlays: string[] } {
  if (!current) return { background: null, overlays: [] }
  const parts = current.split('-')
  return {
    background: parts.find((p) => bgNames.has(p)) ?? null,
    overlays: parts.filter((p) => ovNames.has(p)),
  }
}

/**
 * Owns all panel state. A scene = one background + any number of overlays.
 * Selecting a background or toggling an overlay recomposes and applies
 * optimistically (instant on a phone), then reconciles against the daemon on
 * the next poll — or rolls back immediately on failure.
 */
export function usePanel() {
  const [backgrounds, setBackgrounds] = useState<Item[]>([])
  const [overlays, setOverlays] = useState<Item[]>([])
  const [background, setBackground] = useState<string | null>(null)
  const [active, setActive] = useState<string[]>([]) // active overlay names
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const pending = useRef(false)
  const ovNames = useMemo(() => new Set(overlays.map((o) => o.name)), [overlays])

  const refresh = useCallback(async () => {
    if (pending.current) return
    try {
      const { backgrounds: bgs, current } = await fetchBackgrounds()
      if (pending.current) return
      setBackgrounds(bgs)
      const sel = parseSelection(current, new Set(bgs.map((b) => b.name)), ovNames)
      setBackground(sel.background)
      setActive(sel.overlays)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [ovNames])

  // Overlay list is server-defined and static; fetch it once.
  useEffect(() => {
    fetchOverlays()
      .then((o) => setOverlays(o.overlays))
      .catch(() => {})
  }, [])

  useEffect(() => {
    void refresh()
    const id = setInterval(() => void refresh(), POLL_MS)
    return () => clearInterval(id)
  }, [refresh])

  const apply = useCallback(
    async (bg: string | null, ovs: string[], action: () => Promise<unknown>) => {
      const prev = { bg: background, ovs: active }
      pending.current = true
      setBackground(bg)
      setActive(ovs)
      setError(null)
      try {
        await action()
      } catch (err) {
        setBackground(prev.bg)
        setActive(prev.ovs)
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        pending.current = false
      }
      void refresh()
    },
    [background, active, refresh],
  )

  const pickBackground = useCallback(
    (name: string) => apply(name, active, () => setScene(name, active)),
    [apply, active],
  )

  const toggleOverlay = useCallback(
    (name: string) => {
      // An overlay needs a background under it; default to black if none chosen.
      const bg = background ?? backgrounds.find((b) => b.name === 'black')?.name ?? backgrounds[0]?.name
      if (!bg) return
      const next = active.includes(name)
        ? active.filter((x) => x !== name)
        : [...active, name]
      void apply(bg, next, () => setScene(bg, next))
    },
    [apply, background, active, backgrounds],
  )

  const off = useCallback(() => apply(null, [], turnOff), [apply])

  return {
    backgrounds,
    overlays,
    background,
    active,
    loading,
    error,
    pickBackground,
    toggleOverlay,
    off,
  }
}
