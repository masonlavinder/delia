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
 * (color swatch, font dropdown, position sliders), driven by the server's spec. */
export function OverlayEditor({ overlay, values, onChange }: Props) {
  const entries = Object.entries(overlay.params)
  if (entries.length === 0) return null

  return (
    <div className="editor">
      <div className="editor-title">
        {overlay.emoji && <span className="emoji-sm">{overlay.emoji}</span>}
        {overlay.name}
      </div>
      {entries.map(([key, spec]) => {
        if (spec.type === 'color') {
          const rgb = (values[key] as [number, number, number]) ?? spec.default
          return (
            <label className="field" key={key}>
              <span>{key}</span>
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
              <span>{key} (size)</span>
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
            <span>
              {key} — {val}
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
