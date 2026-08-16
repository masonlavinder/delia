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
  - `web_app/server/` — Flask (`server.py` routes, `scenes.py` the
    `BACKGROUNDS` + `OVERLAYS` registry, `ai.py` the optional ask box). A scene
    is composed at request time: `compose(background, overlays)` stacks the
    background's layers, then each overlay's layers on top; overlays carry
    per-instance `params` (color/font/position) overrides. Unprivileged; talks
    to the daemon via `panel.client` (an installed package, so it stands
    alone). Also static-hosts the built client.
  - `web_app/client/` — React + TypeScript + Vite SPA. Hardcodes **no**
    background/overlay list; it renders whatever `/api/backgrounds` and
    `/api/overlays` return, including each overlay's editable-parameter spec.
    A generic color-picker background and a global brightness slider are built
    in. `src/styles/` is the Knurled Studio design layer, vendored. See
    `web_app/README.md`.
- `matrix/raspberry_pi/` — everything Pi-specific: the build/repair runbook
  (`led-matrix-setup.md`), SD-card headless setup (`pi-setup/`), diagnostics
  (`check-address-lines.py`, `tune-slowdown.sh`), and the systemd units.

- `instructions/` — procedural how-tos, one `.md` per task, indexed by its
  `README.md`. Rare operations you'd otherwise re-derive (currently: moving the
  Pi to a new WiFi network). Not architecture — that's this file.

Layout: `matrix/panel/` = portable engine (runs on the mock in CI),
`matrix/raspberry_pi/` = Pi-specific tooling/config, `web_app/` = the phone UI
(`server/` + `client/`), `instructions/` = how-tos. No `pi_apps/`.

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
- **Add a background or overlay:** edit the `BACKGROUNDS` / `OVERLAYS` dicts in
  `web_app/server/scenes.py` — one entry each (`layers` + an `emoji`).
  Backgrounds are the base (a `solid`, `image`, or `gif`); overlays draw on top
  (a `clock`, `text`, `scroll`). The client needs no change and no rebuild — it
  discovers both from the API. For an animation, drop a `.gif` in
  `matrix/assets/` and reference it with a `gif` layer (`asset_id` = filename
  without extension). Overlays are **auto-tunable**: any `color`/`font`/`x`/`y`
  on the primary layer becomes an editable control in the UI (see `_params_for`).
  The generic "color" background and the global brightness slider are built in,
  not registry entries.
- **The ask box (`web_app/server/ai.py`) adds no capability.** Claude picks
  from the registry and nothing else: the JSON Schema it answers in is derived
  from `list_backgrounds()`/`list_overlays()` per call, so a new background is
  in its vocabulary with no change to `ai.py`. Its answer goes through the same
  `_apply()` → `compose()` → daemon path as a button tap and is re-validated
  there. **Never let it emit raw scene documents** — that would move the
  vocabulary out of `scenes.py` and make the layer schema the only guard.
  Optional: no `ANTHROPIC_API_KEY` (in `~/delia/.env` on the Pi, loaded by the
  unit's `EnvironmentFile=-`) → `/api/ai` reports disabled and the box renders
  disabled, explaining itself, rather than disappearing.
  `PANEL_AI_MODEL` overrides the model. Requires `anthropic` on the Pi, which
  the engine and daemon must never import.
- **The UI follows Knurled Studio.** Rules in `~/Desktop/knurled-studio/KNURLED.md`;
  the design layer is **vendored** into `web_app/client/src/styles/` because
  delia is a separate repo that rsyncs to a Pi and cannot resolve a
  `@knurled/kit` workspace dependency. Chamfers, never `border-radius`. No
  faked light — no gradients, shadows or glows; depth is hairline borders and
  flat surface steps. Colour only from a custom property (raw hex belongs in
  `tokens.css`). Durations from `--dur-*`. Grain at 45°, never rotated. Dark
  only. **`global.css` must be imported first** — it declares the layer order,
  and a layer named before that declaration is pinned where it lands.
  Verdigris is reserved for what leaves the device, which here is exactly the
  overlays `/api/overlays` flags `dynamic`. Verify with the studio's own lint,
  which needs nothing installed here:
  `cd ../knurled-studio && npx stylelint --config packages/stylelint-config/index.js "…/web_app/client/src/**/*.css"`.
- **WiFi is config-driven, not hand-typed `nmcli`.** The networks the Pi knows
  live in `matrix/raspberry_pi/pi-setup/wifi.conf` (gitignored, from
  `wifi.conf.example`); `apply-wifi.sh` renders each `[section]` into a
  NetworkManager keyfile and installs it over SSH — or with `--write-to` onto a
  mounted SD card when the Pi is unreachable. Adding a network never removes the
  old one: the Pi has no ethernet, so the old profile is the only way back in.
  Procedure: `instructions/wifi-new-network.md`.
- The Pi runs **Raspberry Pi OS on Debian 13 (trixie)** with **NetworkManager**
  managing WiFi — profiles are keyfiles in
  `/etc/NetworkManager/system-connections/`, root-owned `0600` or NM ignores
  them. Reflashing the card to fix a network problem throws away the compiled
  `rpi-rgb-led-matrix` and the whole install; don't.
- Reach the Pi: `ping delia-pi.local`, then `ssh mlavinder@delia-pi.local`
  (passwordless SSH key); `instructions/reaching-the-pi.md` when it won't answer.
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
