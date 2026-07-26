# delia — project guide for Claude

Personal Raspberry Pi project driving an **Adafruit 128x64 2mm HUB75 LED matrix**
from a Pi 3 A+.

## Architecture (current)

A long-lived **root daemon owns the matrix** and accepts **declarative scene
documents** over a Unix socket. An unprivileged web app validates and forwards
them. Nothing spawns a process; nothing derives a filesystem path from input.

```
phone -> React client (static, served by the API)
             |  fetch /api/*
         web app (panel-api, user mlavinder, group panel)
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
- `web_app/` — the phone UI, a **separate root folder**, itself split
  client/server:
  - `web_app/server/` — Flask (`server.py` routes, `scenes.py` the built-in
    `SCENES` dict). Unprivileged; talks to the daemon via `panel.client` (an
    installed package, so it stands alone). Also static-hosts the built client.
  - `web_app/client/` — React + TypeScript + Vite SPA. Hardcodes **no** scene
    list; it renders whatever `/api/scenes` returns. See `web_app/README.md`.
- `matrix/raspberry_pi/` — everything Pi-specific: the build/repair runbook
  (`led-matrix-setup.md`), SD-card headless setup (`pi-setup/`), diagnostics
  (`check-address-lines.py`, `tune-slowdown.sh`), and the systemd units.

Layout: `matrix/panel/` = portable engine (runs on the mock in CI),
`matrix/raspberry_pi/` = Pi-specific tooling/config, `web_app/` = the phone UI
(`server/` + `client/`). No `pi_apps/`.

Runs as two **systemd services, enabled on boot**: `panel-renderer` (root) and
`panel-api` (mlavinder). The old CLI/direct-GPIO approach (`display`, `run.sh`,
`scenes/*.py`) has been **removed** — the daemon owns the GPIO now.

## Dev workflow

- Off-Pi, everything runs on the **mock backend** (no GPIO, no fonts on disk):
  `cd matrix && PANEL_BACKEND=mock .venv/bin/pytest`.
- Client dev loop: `cd web_app/client && npm run dev` — Vite on :5173 with HMR,
  proxying `/api` to `delia-pi.local:8080` (override with `PANEL_API=…`). So you
  develop the UI against the real daemon without deploying.
- **Deploy with `./deploy.sh`** (repo root) — don't hand-roll the rsync:
  ```
  ./deploy.sh          # build client, push all, install units, restart both
  ./deploy.sh client   # build + push dist/ only; NO restart needed
  ./deploy.sh api      # push web_app/server/ + restart panel-api
  ./deploy.sh engine   # push matrix/ + restart panel-renderer
  ./deploy.sh -n …     # dry run;  also: units, restart, status, logs
  ```
  It builds the client here (the Pi has no Node and 512 MB), pushes `dist/`
  with `--delete` (asset names are content-hashed), and prompts for the Pi's
  sudo password on the steps that need it.
- **The systemd units are COPIES in `/etc/systemd/system`.** Editing
  `matrix/raspberry_pi/systemd/*.service` and rsyncing does nothing on its own —
  the running service keeps its old definition. `./deploy.sh` handles this: it
  compares, and reinstalls + `daemon-reload`s only when they differ.
- **Add a scene:** add a declarative document to `SCENES` in
  `web_app/server/scenes.py` (built from the layer types), plus an entry in
  `SCENE_EMOJI` beside it. The client needs no change and no rebuild. For an
  animation, drop a `.gif` in `matrix/assets/` and reference it with a `gif`
  layer (`asset_id` = filename without extension).
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
