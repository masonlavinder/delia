import { OffButton } from './components/OffButton'
import { SceneButton } from './components/SceneButton'
import { usePanel } from './usePanel'

export function App() {
  const { scenes, current, loading, error, play, off } = usePanel()

  let status: string
  if (error) status = error
  else if (loading) status = 'loading…'
  else if (current) status = `playing: ${current}`
  else status = 'panel is off'

  return (
    <main>
      <h1>💡 delia panel</h1>
      <p className={error ? 'sub error' : 'sub'} role="status">{status}</p>

      <div className="grid">
        {scenes.map((scene) => (
          <SceneButton
            key={scene.name}
            label={scene.name}
            emoji={scene.emoji}
            active={scene.name === current}
            onSelect={() => play(scene.name)}
          />
        ))}
        <OffButton isOff={current === null} onSelect={off} />
      </div>
    </main>
  )
}
