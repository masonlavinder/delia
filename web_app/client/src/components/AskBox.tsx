import { useState } from 'react'

type Props = {
  /** Whether the server has a key. `null` while we're still asking it — treated
   * as enabled so the box doesn't flash a disabled state on every load. */
  enabled: boolean | null
  /** A request is in flight — the panel is about to change under you. */
  busy: boolean
  onAsk: (prompt: string) => void
}

/** Describe a scene in words. The server hands it to Claude, which picks from
 * the same backgrounds and overlays the buttons below offer.
 *
 * Always rendered, even with no key on the server: a box that says why it's
 * dead beats one that silently isn't there. */
export function AskBox({ enabled, busy, onAsk }: Props) {
  const [text, setText] = useState('')
  const prompt = text.trim()
  const off = enabled === false

  return (
    <form
      className="ask"
      onSubmit={(event) => {
        event.preventDefault()
        if (!prompt || busy || off) return
        onAsk(prompt)
        setText('')
      }}
    >
      {/* The disabled hint is kept short so a phone doesn't truncate it; the
          full instructions live in the title and web_app/README.md. */}
      <input
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={off ? 'no API key on the server' : 'make it look like a thunderstorm'}
        title={off ? 'Set ANTHROPIC_API_KEY for panel-api and restart it.' : undefined}
        aria-label="describe a scene"
        enterKeyHint="go"
        autoCapitalize="none"
        maxLength={500}
        disabled={busy || off}
      />
      <button type="submit" disabled={busy || off || !prompt} aria-label="apply">
        {busy ? '…' : '✨'}
      </button>
    </form>
  )
}
