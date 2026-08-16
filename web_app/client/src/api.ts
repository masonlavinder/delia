/** Typed wrapper over the Flask control API in `web_app/server`. */

export type Item = {
  name: string
  /** Presentation hint from the server; may be absent. */
  emoji: string | null
}

/** One tunable parameter of an overlay, as described by the server. */
export type ParamSpec =
  | { type: 'color'; default: [number, number, number] }
  | { type: 'font'; options: string[]; default: string }
  | { type: 'int'; min: number; max: number; default: number }

export type ParamValue = [number, number, number] | string | number
export type Params = Record<string, ParamValue>

/** An overlay plus the spec of what's editable about it (color/font/position). */
export type Overlay = Item & { params: Record<string, ParamSpec> }

/** An overlay selection sent to the panel: its name + any param overrides. */
export type OverlaySel = { name: string; params?: Params }

export type BackgroundsState = {
  backgrounds: Item[]
  /** Composed name of the scene rendering now (e.g. "plasma-clock"), or null when off. */
  current: string | null
}

/** The server's `{ok, error?}` envelope. Errors are surfaced, never swallowed. */
type Result = { ok: boolean; error?: string }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  const body = (await res.json().catch(() => null)) as (T & Partial<Result>) | null
  if (!res.ok || body === null) {
    throw new Error(body?.error ?? `${path} failed (${res.status})`)
  }
  return body
}

export function fetchBackgrounds(): Promise<BackgroundsState> {
  return request<BackgroundsState>('/api/backgrounds')
}

export function fetchOverlays(): Promise<{ overlays: Overlay[] }> {
  return request<{ overlays: Overlay[] }>('/api/overlays')
}

/** Set the panel to a background with zero or more overlays composited on top.
 * Each overlay may carry `params` overrides (color/font/position). `color` is
 * used when background is "color"; `brightness` (1-100) rides along so it
 * persists across scene switches. */
export function setScene(
  background: string,
  overlays: OverlaySel[],
  opts: { color?: [number, number, number]; brightness?: number } = {},
): Promise<Result> {
  return request<Result>('/api/scene', {
    method: 'POST',
    body: JSON.stringify({ background, overlays, ...opts }),
  })
}

/** Set panel brightness live (1-100). */
export function setBrightness(value: number): Promise<Result> {
  return request<Result>('/api/brightness', {
    method: 'POST',
    body: JSON.stringify({ value }),
  })
}

export function turnOff(): Promise<Result> {
  return request<Result>('/api/off', { method: 'POST' })
}

/** Whether the server has an API key, i.e. whether to show the ask box. */
export type AiStatus = { enabled: boolean; model: string | null }

/** What the model chose, echoed back so the UI reflects the panel immediately. */
export type AiScene = {
  background: string
  overlays: OverlaySel[]
  brightness?: number
  color?: [number, number, number]
  /** One short line describing the choice, for the status row. */
  note: string
}

export function fetchAiStatus(): Promise<AiStatus> {
  return request<AiStatus>('/api/ai')
}

/** Describe a scene in words; the server asks Claude to pick from the registry
 * and applies the result through the same path as a button tap. */
export function askScene(prompt: string): Promise<AiScene> {
  return request<AiScene>('/api/ai/scene', {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  })
}
