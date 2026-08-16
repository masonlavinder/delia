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
 * the same backgrounds and overlays the tiles below offer.
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
      {/* An <input> cannot carry a ::before, so the chamfer keeps its wrapper
          here — the one place the studio's two-element construction survives. */}
      <div className="chamfer ask-field">
        <input
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={off ? 'no API key on the server' : 'a thunderstorm, clock in white'}
          title={off ? 'Set ANTHROPIC_API_KEY for panel-api and restart it.' : undefined}
          aria-label="describe a scene"
          enterKeyHint="go"
          autoCapitalize="none"
          maxLength={500}
          disabled={busy || off}
        />
      </div>
      {/* Text, not an arrow glyph — Geist's latin subset has no U+2192. */}
      <button
        type="submit"
        className="chamfer ask-go mono-label"
        disabled={busy || off || !prompt}
        aria-label="apply"
      >
        {busy ? '···' : 'go'}
      </button>
    </form>
  )
}
