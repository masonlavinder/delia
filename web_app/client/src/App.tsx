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

  let status: string
  if (error) status = error
  else if (loading) status = 'loading…'
  else if (asking) status = 'thinking…'
  else if (note) status = note // what the model said it picked
  else if (background) status = active.length ? `${background} + ${active.join(', ')}` : background
  else status = 'panel is off'

  return (
    <main>
      <h1>💡 delia panel</h1>
      <p className={error ? 'sub error' : 'sub'} role="status">{status}</p>

      <OffButton isOff={background === null} onSelect={off} />
      <BrightnessSlider value={brightness} onChange={changeBrightness} />

      <h2 className="section">Ask</h2>
      <AskBox enabled={ai} busy={asking} onAsk={ask} />

      <h2 className="section">Scenes</h2>
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

      <h2 className="section">Info</h2>
      <div className="chips">
        {overlays.map((o) => (
          <OverlayChip
            key={o.name}
            label={o.name}
            emoji={o.emoji}
            active={active.includes(o.name)}
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
