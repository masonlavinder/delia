type Props = {
  label: string
  emoji: string | null
  /** True when this overlay is currently composited on the background. */
  active: boolean
  onToggle: () => void
}

/** A multi-select pill for an "info" overlay (clock, date, …). Unlike a scene
 * button, several can be active at once. */
export function OverlayChip({ label, emoji, active, onToggle }: Props) {
  return (
    <button
      type="button"
      className={active ? 'chip active' : 'chip'}
      aria-pressed={active}
      onClick={onToggle}
    >
      <span className="emoji-sm" aria-hidden="true">{emoji ?? '▫️'}</span>
      {label}
    </button>
  )
}
