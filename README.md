# delia

Personal Raspberry Pi projects. The main one is an **LED matrix display** — a
128×64 RGB HUB75 panel driven by a Pi 3 A+, controllable from your phone.

## Layout

```
delia/
├── matrix/            LED matrix display system
│   ├── panel/         portable engine: scene schema (the contract), renderer,
│   │                  daemon, client, backends (mock + rgbmatrix). Runs in CI on
│   │                  the mock backend — no hardware needed.
│   ├── raspberry_pi/  Pi-specific: build/repair runbook, diagnostics, SD-card
│   │                  headless setup (pi-setup/), and the systemd units.
│   ├── assets/        image/gif assets (referenced by scenes via asset_id)
│   ├── tools/         asset generators
│   └── tests/         run with: cd matrix && PANEL_BACKEND=mock .venv/bin/pytest
├── web_app/           phone web UI to switch scenes
│   ├── server/        Flask: the control API + static host for the built client;
│   │                  owns the scene documents, talks to the daemon
│   └── client/        React + TypeScript (Vite) SPA; build on a laptop, not the Pi
├── clove_plans/       (placeholder)
└── deploy.sh          push to the Pi (client / api / engine / units / all)
```

## How the LED matrix runs

A long-lived **root daemon** (`panel-renderer`) owns the panel and accepts
**declarative scene documents** over a Unix socket. An unprivileged web app
(`panel-api`, serving `web_app/`) validates and forwards them. Both are systemd
services, enabled on boot. Nothing spawns a process; nothing derives a filesystem
path from input; every scene is re-validated at the daemon (the trust boundary).

- **Control it:** open `http://delia-pi.local:8080` on your phone (home WiFi).
- **Reach the Pi:** `ssh mlavinder@delia-pi.local` (passwordless key; `sudo`
  needs a password).
- **Deploy:** `./deploy.sh` (or `./deploy.sh client` for a UI-only change —
  that one needs no service restart). `./deploy.sh -h` for all targets.

## Docs

- **`CLAUDE.md`** — architecture, dev workflow, and conventions (start here).
- **`matrix/README.md`** — the panel system in depth.
- **`matrix/raspberry_pi/led-matrix-setup.md`** — hardware build/repair runbook;
  read it first if the panel misbehaves or you reflash the card.
