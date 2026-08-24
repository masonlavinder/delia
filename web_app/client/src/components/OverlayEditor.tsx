import type { Overlay, ParamValue } from '../api'

type Props = {
  overlay: Overlay
  /** Current overrides for this overlay (empty = every param at its default). */
  values: Record<string, ParamValue>
  onChange: (key: string, value: ParamValue) => void
}

function rgbToHex(rgb: [number, number, number]): string {
  return (
    '#' +
    rgb.map((c) => Math.max(0, Math.min(255, c)).toString(16).padStart(2, '0')).join('')
  )
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  return [
    parseInt(h.slice(0, 2), 16) || 0,
    parseInt(h.slice(2, 4), 16) || 0,
    parseInt(h.slice(4, 6), 16) || 0,
  ]
}

/** Inline editor for one active overlay: a control per tunable parameter
 * (text line, colour swatch, font dropdown, position sliders), driven by the
 * server's spec. Reads as a spec table — label left, value right. */
export function OverlayEditor({ overlay, values, onChange }: Props) {
  const entries = Object.entries(overlay.params)
  if (entries.length === 0) return null

  return (
    <div className="chamfer editor">
      <div className="editor-head">
        {overlay.emoji && (
          <span className="emoji-sm" aria-hidden="true">{overlay.emoji}</span>
        )}
        <span className="mono-label">{overlay.name}</span>
      </div>

      {entries.map(([key, spec]) => {
        if (spec.type === 'text') {
          const val = (values[key] as string) ?? spec.default
          return (
            /* Full width and stacked: a typed line is the point of the overlay,
               not a value in the right-hand column. */
            <label className="field field-stack" key={key}>
              <span className="mono-label">{key}</span>
              <input
                type="text"
                className="text-input"
                value={val}
                maxLength={spec.max_length}
                autoCapitalize="none"
                enterKeyHint="done"
                onChange={(e) => onChange(key, e.target.value)}
              />
            </label>
          )
        }

        if (spec.type === 'color') {
          const rgb = (values[key] as [number, number, number]) ?? spec.default
          return (
            <label className="field" key={key}>
              <span className="mono-label">{key}</span>
              <input
                type="color"
                value={rgbToHex(rgb)}
                onChange={(e) => onChange(key, hexToRgb(e.target.value))}
              />
            </label>
          )
        }

        if (spec.type === 'font') {
          const val = (values[key] as string) ?? spec.default
          return (
            <label className="field" key={key}>
              <span className="mono-label">{key}</span>
              <select value={val} onChange={(e) => onChange(key, e.target.value)}>
                {spec.options.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            </label>
          )
        }

        const val = (values[key] as number) ?? spec.default
        return (
          <label className="field" key={key}>
            <span className="mono-label">
              {key} <span className="mono-value tabular">{val}</span>
            </span>
            <input
              type="range"
              min={spec.min}
              max={spec.max}
              value={val}
              onChange={(e) => onChange(key, Number(e.target.value))}
            />
          </label>
        )
      })}
    </div>
  )
}
