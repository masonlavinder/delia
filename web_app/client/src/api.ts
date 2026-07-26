/** Typed wrapper over the Flask control API in `web_app/server`. */

export type Scene = {
  name: string
  /** Presentation hint from the server; may be absent for new scenes. */
  emoji: string | null
}

export type PanelState = {
  scenes: Scene[]
  /** Name of the scene currently rendering, or null when the panel is off. */
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

export function fetchState(): Promise<PanelState> {
  return request<PanelState>('/api/scenes')
}

export function setScene(name: string): Promise<Result> {
  return request<Result>('/api/scene', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export function turnOff(): Promise<Result> {
  return request<Result>('/api/off', { method: 'POST' })
}
