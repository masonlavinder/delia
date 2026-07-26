/** Typed wrapper over the Flask control API in `web_app/server`. */

export type Item = {
  name: string
  /** Presentation hint from the server; may be absent. */
  emoji: string | null
}

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

export function fetchOverlays(): Promise<{ overlays: Item[] }> {
  return request<{ overlays: Item[] }>('/api/overlays')
}

/** Set the panel to a background with zero or more overlays composited on top. */
export function setScene(background: string, overlays: string[]): Promise<Result> {
  return request<Result>('/api/scene', {
    method: 'POST',
    body: JSON.stringify({ background, overlays }),
  })
}

export function turnOff(): Promise<Result> {
  return request<Result>('/api/off', { method: 'POST' })
}
