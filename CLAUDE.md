# delia — project guide for Claude

Personal Raspberry Pi project driving an **Adafruit 128x64 2mm HUB75 LED matrix**
from a Pi 3 A+.

## Architecture (current)

A long-lived **root daemon owns the matrix** and accepts **declarative scene
documents** over a Unix socket. An unprivileged web app validates and forwards
them. Nothing spawns a process; nothing derives a filesystem path from input.

```
phone -> web app (panel-api, user mlavinder, group panel)
             |  newline-JSON
        /run/panel/panel.sock  (root:panel, 0660)
             |
        renderer daemon (panel-renderer, root) -> RGBMatrix (GPIO)
```

- `matrix/panel/` — the engine package. `matrix/panel/schema.py` is the
  **contract** (Pydantic v2, strict, bounded, discriminated union on layer
  `type`). Layers: `solid`, `text`, `scroll`, `clock`, `image`, `gif`. Fonts are
  an enum; images/gifs are an `asset_id` (regex, resolved+contained under
  `matrix/assets/`). `renderer.py` is a render loop; `daemon.py` is the trust
  boundary; `backends/` has `rgbmatrix` (real, root) and `mock` (Pillow, for
  tests). See `matrix/README.md`.
- `web_app/server.py` — the phone web UI (Flask), a **separate root folder**.
  Unprivileged; talks to the daemon via `panel.client` (an installed package, so
  it stands alone). Built-in scenes live in its `SCENES` dict.
- `matrix/raspberry_pi/` — everything Pi-specific: the build/repair runbook
  (`led-matrix-setup.md`), SD-card headless setup (`pi-setup/`), diagnostics
  (`check-address-lines.py`, `tune-slowdown.sh`), and the systemd units.

Layout: `matrix/panel/` = portable engine (runs on the mock in CI),
`matrix/raspberry_pi/` = Pi-specific tooling/config, `web_app/` = the phone UI.
No `pi_apps/`.

Runs as two **systemd services, enabled on boot**: `panel-renderer` (root) and
`panel-api` (mlavinder). The old CLI/direct-GPIO approach (`display`, `run.sh`,
`scenes/*.py`) has been **removed** — the daemon owns the GPIO now.

## Dev workflow

- Off-Pi, everything runs on the **mock backend** (no GPIO, no fonts on disk):
  `cd matrix && PANEL_BACKEND=mock .venv/bin/pytest`.
- Edit, then deploy to the Pi and restart:
  ```
  rsync -az --exclude .venv --exclude __pycache__ matrix web_app mlavinder@delia-pi.local:~/delia/
  # on the Pi (needs a password now — see below):
  sudo systemctl restart panel-renderer panel-api
  ```
- **Add a scene:** add a declarative document to `SCENES` in `web_app/server.py`
  (built from the layer types). For an animation, drop a `.gif` in `matrix/assets/`
  and reference it with a `gif` layer (`asset_id` = filename without extension).
- Reach the Pi: `ssh mlavinder@delia-pi.local` (passwordless SSH key).
  **`sudo` now requires a password** (the broad NOPASSWD grant was removed) — to
  run a privileged command in a session, prefix it with `! sudo …`.

## LED matrix conventions — IMPORTANT

- **Backgrounds are OFF, not a dark color.** Fill with pure black `(0,0,0)` so
  unlit pixels are truly off. Never a dark tint — it dimly lights every pixel.
- **This panel is BGR-wired:** the rgbmatrix backend sets `led_rgb_sequence=BGR`.
  Schema colors are normal RGB; the backend corrects the order. Don't "fix"
  colors by swapping channels in scenes.
- **Panel config lives in ONE place:** `matrix/panel/backends/rgbmatrix.py` —
  stock `adafruit-hat`, `multiplexing=0`, E on **GPIO 24** (bonnet "8" pad
  soldered). If the panel bands/half-lights, it's the **E line / solder / a broken
  build — never multiplexing.** See `led-matrix-setup.md`.
- Build the library with `make LTO_FLAGS= -j2` (LTO OOMs on 512 MB). Keep
  brightness modest.
- **Animations must double-buffer** (the renderer already does via `SwapOnVSync`).

## Security model

The socket (root:panel, 0660) is the boundary; a VPN/tunnel is the network
boundary (no app-level auth yet — do not expose publicly as-is). The daemon
re-validates every scene even though the API did — that re-check is what protects
the device.
