type Props = {
  /** Current hex color, e.g. "#8b5cf6". */
  color: string
  /** True when the panel is showing this generic color background. */
  active: boolean
  onPick: (hex: string) => void
}

/** A "generic" background: any solid colour. Styled as a scene tile; the whole
 * tile is a native colour input, so tapping it opens the OS picker.
 *
 * The swatch is the one colour on the page that is not a token — it is the
 * user's data, not the design's. */
export function ColorPicker({ color, active, onPick }: Props) {
  return (
    <label className={active ? 'chamfer scene picker active' : 'chamfer scene picker'}>
      <span className="swatch" style={{ background: color }} aria-hidden="true" />
      <span className="mono-label">colour</span>
      <input
        type="color"
        value={color}
        aria-label="background colour"
        onChange={(e) => onPick(e.target.value)}
      />
    </label>
  )
}
