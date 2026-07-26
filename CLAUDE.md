# delia — project guide for Claude

Personal Raspberry Pi project. Primary subsystem: an **LED matrix display**
(`pi_apps/led_matrix/`) driven by a Pi 3 A+.

## Reaching the Pi

- Pi 3 Model A+ → Adafruit **128x64 2mm HUB75 panel** via the RGB Matrix Bonnet.
- `ssh mlavinder@delia-pi.local` — passwordless key + passwordless sudo.
- The Pi holds a clone of this repo at `~/delia/`; scene code at
  `~/delia/pi_apps/led_matrix/`.

## Dev workflow (LED matrix)

- Edit locally under `pi_apps/led_matrix/`, then push to the Pi:
  `rsync -az pi_apps/led_matrix/ mlavinder@delia-pi.local:~/delia/pi_apps/led_matrix/`
  (exclude `config.py` and `__pycache__`; keep `run.sh` / `display` executable —
  rsync resets the +x bit, so `chmod +x` after if needed).
- Run a scene on the panel: **`display <scene>`** (or `./run.sh <scene>`), e.g.
  `display rocket`. Scenes need root for GPIO — `display`/`run.sh` add `sudo`.
- Scenes are auto-discovered from `scenes/<group>/*.py`; files starting with `_`
  are hidden (generators/helpers).

## LED matrix conventions — IMPORTANT

- **Backgrounds are OFF, not a dark color.** Fill scene backgrounds with pure
  black `(0, 0, 0)` so unlit pixels are genuinely off. NEVER use a "dark" tint
  (e.g. `(5,5,16)`) as a background — on an LED panel that dimly lights every
  pixel and looks worse. Only light the pixels that are actual content.
- **Animations must double-buffer** (or they tear): draw into
  `canvas = matrix.CreateFrameCanvas()`, then `canvas = matrix.SwapOnVSync(canvas)`
  each frame. Do NOT call `matrix.SetImage()` directly on the live matrix in a loop.
- **Panel config lives in ONE place:** `core/panel.py` `build_matrix()` — stock
  `hardware_mapping='adafruit-hat'`, `multiplexing=0`, defaults. Do NOT add
  FM6126A or sweep multiplexing values. If the panel bands / half-lights, it's the
  **E address line (GPIO 24) / solder / a broken build — never multiplexing.**
  See `pi_apps/led_matrix/led-matrix-setup.md`.
- Keep brightness modest (≈40–60); full white draws a lot of current.

## Layout

- `pi_apps/led_matrix/scenes/{everyday,party,scratch}/` — scenes
- `pi_apps/led_matrix/core/panel.py` — `build_matrix()` + `load_font()`
- `pi_apps/led_matrix/display`, `run.sh` — launchers
- `pi_apps/led_matrix/led-matrix-setup.md` — hardware/build/repair runbook
- `pi_apps/led_matrix/diagnostics/` — troubleshooting tools
