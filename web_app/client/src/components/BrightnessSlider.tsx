type Props = {
  value: number
  onChange: (value: number) => void
}

/** Global panel brightness (1-100). Applies live and rides along in scene
 * compositions so it survives scene switches. */
export function BrightnessSlider({ value, onChange }: Props) {
  return (
    <div className="meter">
      <div className="meter-head">
        <label htmlFor="brightness" className="mono-label">brightness</label>
        <span className="mono-value tabular">{value} %</span>
      </div>
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
