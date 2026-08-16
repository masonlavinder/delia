import { AskBox } from './components/AskBox'
import { BrightnessSlider } from './components/BrightnessSlider'
import { ColorPicker } from './components/ColorPicker'
import { OffButton } from './components/OffButton'
import { OverlayChip } from './components/OverlayChip'
import { OverlayEditor } from './components/OverlayEditor'
import { SceneButton } from './components/SceneButton'
import { usePanel } from './usePanel'

export function App() {
  const {
    backgrounds,
    overlays,
    background,
    active,
    params,
    color,
    brightness,
    loading,
    error,
    ai,
    asking,
    note,
    pickBackground,
    toggleOverlay,
    setOverlayParam,
    pickColor,
    changeBrightness,
    off,
    ask,
  } = usePanel()

  const activeOverlays = overlays.filter((o) => active.includes(o.name))

  // Spec-sheet register: what is on the panel, separated the way a part
  // number is. The model's note is prose and stands on its own.
  let status: string
  if (error) status = error
  else if (loading) status = 'reading panel'
  else if (asking) status = 'composing'
  else if (note) status = note
  else if (background) status = [background, ...active].join(' · ')
  else status = 'dark'

  return (
    <main>
      <div className="strip knurl knurl-strip" aria-hidden="true" />

      <header className="lockup">
        <span className="chamfer mark" aria-hidden="true" />
        <span className="wordmark">delia</span>
        <span className="spec mono-label">128 × 64 · hub75</span>
      </header>

      <p className={error ? 'readout error' : 'readout'} role="status">
        {status}
      </p>

      <OffButton isOff={background === null} onSelect={off} />
      <BrightnessSlider value={brightness} onChange={changeBrightness} />

      <h2 className="section">
        <span className="mono-label">ask</span>
      </h2>
      <AskBox enabled={ai} busy={asking} onAsk={ask} />

      <h2 className="section">
        <span className="mono-label">background</span>
      </h2>
      <div className="grid">
        {backgrounds.map((b) => (
          <SceneButton
            key={b.name}
            label={b.name}
            emoji={b.emoji}
            active={b.name === background}
            onSelect={() => pickBackground(b.name)}
          />
        ))}
        <ColorPicker color={color} active={background === 'color'} onPick={pickColor} />
      </div>

      <h2 className="section">
        <span className="mono-label">overlays</span>
      </h2>
      <div className="chips">
        {overlays.map((o) => (
          <OverlayChip
            key={o.name}
            label={o.name}
            emoji={o.emoji}
            active={active.includes(o.name)}
            external={o.dynamic}
            onToggle={() => toggleOverlay(o.name)}
          />
        ))}
      </div>

      {activeOverlays.length > 0 && (
        <div className="editors">
          {activeOverlays.map((o) => (
            <OverlayEditor
              key={o.name}
              overlay={o}
              values={params[o.name] ?? {}}
              onChange={(key, value) => setOverlayParam(o.name, key, value)}
            />
          ))}
        </div>
      )}
    </main>
  )
}
