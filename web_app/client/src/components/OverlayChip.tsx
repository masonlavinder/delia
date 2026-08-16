type Props = {
  label: string
  emoji: string | null
  /** True when this overlay is currently composited on the background. */
  active: boolean
  /** True when the overlay fetches live data off the network. Wears the
   * second hue — colour alone says which one leaves the device. */
  external?: boolean
  onToggle: () => void
}

/** A multi-select control for an "info" overlay (clock, date, …). Unlike a
 * scene tile, several can be on at once — square-bordered rather than
 * chamfered, because at this height a 13px cut takes the corner off. */
export function OverlayChip({ label, emoji, active, external, onToggle }: Props) {
  const className = ['chip', external && 'external', active && 'active']
    .filter(Boolean)
    .join(' ')

  return (
    <button type="button" className={className} aria-pressed={active} onClick={onToggle}>
      <span className="emoji-sm" aria-hidden="true">{emoji}</span>
      {label}
    </button>
  )
}
