type Props = {
  label: string
  emoji: string | null
  active: boolean
  onSelect: () => void
}

/** One background, as a chamfered tile. The emoji reads first from across a
 * room; the mono label underneath confirms which one it is. */
export function SceneButton({ label, emoji, active, onSelect }: Props) {
  return (
    <button
      type="button"
      className={active ? 'chamfer scene active' : 'chamfer scene'}
      aria-pressed={active}
      onClick={onSelect}
    >
      <span className="emoji" aria-hidden="true">{emoji}</span>
      <span className="mono-label">{label}</span>
    </button>
  )
}
