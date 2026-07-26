type Props = {
  label: string
  emoji: string | null
  active: boolean
  onSelect: () => void
}

export function SceneButton({ label, emoji, active, onSelect }: Props) {
  return (
    <button
      type="button"
      className={active ? 'scene active' : 'scene'}
      aria-pressed={active}
      onClick={onSelect}
    >
      <span className="emoji" aria-hidden="true">{emoji ?? '▫️'}</span>
      {label}
    </button>
  )
}
