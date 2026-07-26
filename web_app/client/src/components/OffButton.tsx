type Props = {
  /** True when the panel is already dark. */
  isOff: boolean
  onSelect: () => void
}

export function OffButton({ isOff, onSelect }: Props) {
  return (
    <button
      type="button"
      className={isOff ? 'scene off active' : 'scene off'}
      aria-pressed={isOff}
      onClick={onSelect}
    >
      {isOff ? '○ off' : '⏻ turn off'}
    </button>
  )
}
