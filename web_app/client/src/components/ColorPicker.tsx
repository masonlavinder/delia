type Props = {
  /** Current hex color, e.g. "#8b5cf6". */
  color: string
  /** True when the panel is showing this generic color background. */
  active: boolean
  onPick: (hex: string) => void
}

/** A "generic" background: any solid color. Styled like a scene button; the
 * whole tile is a native color input, so tapping it opens the OS color picker. */
export function ColorPicker({ color, active, onPick }: Props) {
  return (
    <label className={active ? 'scene color active' : 'scene color'}>
      <span className="swatch" style={{ background: color }} aria-hidden="true" />
      color
      <input
        type="color"
        value={color}
        aria-label="background color"
        onChange={(e) => onPick(e.target.value)}
      />
    </label>
  )
}
