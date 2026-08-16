type Props = {
  /** True when the panel is already dark. */
  isOff: boolean
  onSelect: () => void
}

/** Off is a state, not a warning — the studio has no red, so a dark panel is
 * marked the way any other selection is.
 *
 * No glyph: Geist ships a latin subset, and a power symbol (U+23FB) is not in
 * it, so one renders as tofu. The label carries the meaning on its own. */
export function OffButton({ isOff, onSelect }: Props) {
  return (
    <button
      type="button"
      className={isOff ? 'chamfer power active' : 'chamfer power'}
      aria-pressed={isOff}
      onClick={onSelect}
    >
      <span className="mono-label">{isOff ? 'panel dark' : 'turn off'}</span>
    </button>
  )
}
