import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { fetchBackgrounds, fetchOverlays, setBrightness, setScene, turnOff } from './api'
import type { Item, Overlay, OverlaySel, Params } from './api'
import { useThrottledCallback } from './useThrottle'

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

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  return [
    parseInt(h.slice(0, 2), 16) || 0,
    parseInt(h.slice(2, 4), 16) || 0,
    parseInt(h.slice(4, 6), 16) || 0,
  ]
}

/**
 * Owns all panel state. A scene = one background (a preset or a picked color)
 * + any number of overlays, each with its own tunable params (color/font/
 * position), at a global brightness. Any change recomposes and applies
 * optimistically, then reconciles against the daemon on the next poll.
 *
 * The daemon only reports the composed scene NAME (not params), so param state
 * lives here and rides along in every composition.
 */
export function usePanel() {
  const [backgrounds, setBackgrounds] = useState<Item[]>([])
  const [overlays, setOverlays] = useState<Overlay[]>([])
  const [background, setBackground] = useState<string | null>(null)
  const [active, setActive] = useState<string[]>([]) // active overlay names
  const [params, setParams] = useState<Record<string, Params>>({}) // per-overlay overrides
  const [color, setColorState] = useState('#8b5cf6') // last-picked solid color
  const [brightness, setBrightnessState] = useState(40)
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
      // "color" is a valid background even though it's not in the preset list.
      const names = new Set([...bgs.map((b) => b.name), 'color'])
      const sel = parseSelection(current, names, ovNames)
      setBackground(sel.background)
      setActive(sel.overlays)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [ovNames])

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

  // overlay names -> selections, attaching each overlay's current param overrides.
  const select = useCallback(
    (names: string[], overrides: Record<string, Params> = params): OverlaySel[] =>
      names.map((n) => ({ name: n, params: overrides[n] ?? {} })),
    [params],
  )

  // opts for the currently-selected background (carries the color when it's "color")
  const bgOpts = useCallback(
    (bg: string) =>
      bg === 'color' ? { color: hexToRgb(color), brightness } : { brightness },
    [color, brightness],
  )

  // Continuous controls (brightness / position sliders, color pickers) fire a
  // flood of onChange events per drag. We update local state instantly for a
  // responsive UI but THROTTLE the actual panel command — ~one per 150ms while
  // dragging, plus a guaranteed final one on release. This is what stops the
  // daemon from being buried in commands.
  const commitScene = useThrottledCallback(
    (bg: string, names: string[], ps: Record<string, Params>, br: number, hex: string) => {
      const opts = bg === 'color' ? { color: hexToRgb(hex), brightness: br } : { brightness: br }
      const sel: OverlaySel[] = names.map((n) => ({ name: n, params: ps[n] ?? {} }))
      void setScene(bg, sel, opts).catch((err) =>
        setError(err instanceof Error ? err.message : String(err)),
      )
    },
    150,
  )

  const commitBrightness = useThrottledCallback((v: number) => {
    void setBrightness(v).catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, 150)

  const pickBackground = useCallback(
    (name: string) => apply(name, active, () => setScene(name, select(active), { brightness })),
    [apply, active, select, brightness],
  )

  const toggleOverlay = useCallback(
    (name: string) => {
      const bg = background ?? backgrounds.find((b) => b.name === 'black')?.name ?? backgrounds[0]?.name
      if (!bg) return
      const next = active.includes(name) ? active.filter((x) => x !== name) : [...active, name]
      void apply(bg, next, () => setScene(bg, select(next), bgOpts(bg)))
    },
    [apply, background, active, backgrounds, select, bgOpts],
  )

  const pickColor = useCallback(
    (hex: string) => {
      setColorState(hex)
      setBackground('color') // optimistic; the throttled commit pushes it to the panel
      commitScene('color', active, params, brightness, hex)
    },
    [active, params, brightness, commitScene],
  )

  // Tune one parameter of an active overlay (e.g. clock color / position).
  const setOverlayParam = useCallback(
    (name: string, key: string, value: Params[string]) => {
      if (!background) return
      const next = { ...params, [name]: { ...(params[name] ?? {}), [key]: value } }
      setParams(next)
      commitScene(background, active, next, brightness, color)
    },
    [background, active, params, brightness, color, commitScene],
  )

  const changeBrightness = useCallback(
    (value: number) => {
      setBrightnessState(value)
      commitBrightness(value) // live + throttled; persists via future compositions
    },
    [commitBrightness],
  )

  const off = useCallback(() => apply(null, [], turnOff), [apply])

  return {
    backgrounds,
    overlays,
    background,
    active,
    params,
    color,
    brightness,
    loading,
    error,
    pickBackground,
    toggleOverlay,
    setOverlayParam,
    pickColor,
    changeBrightness,
    off,
  }
}
