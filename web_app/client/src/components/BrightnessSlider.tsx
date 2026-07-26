type Props = {
  value: number
  onChange: (value: number) => void
}

/** Global panel brightness (1-100). Applies live and rides along in scene
 * compositions so it survives scene switches. */
export function BrightnessSlider({ value, onChange }: Props) {
  return (
    <div className="brightness">
      <label htmlFor="brightness">☀ brightness — {value}%</label>
      <input
        id="brightness"
        type="range"
        min={1}
        max={100}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  )
}
