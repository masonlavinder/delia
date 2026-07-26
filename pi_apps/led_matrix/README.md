# led_matrix — hardware setup, diagnostics, and the phone web UI

This directory is now the **hardware layer** for the LED matrix. The scene system
moved to [`../../panel/`](../../panel/) (a root renderer daemon + declarative
scene schema); the old CLI scene scripts (`display`, `run.sh`, `scenes/`) were
retired when the daemon took ownership of the GPIO.

## What's here

- **`web/server.py`** — the phone web UI (Flask, unprivileged). It talks to the
  renderer daemon over the Unix socket via `panel.client` and serves built-in
  scenes (`SCENES` dict). Runs as the `panel-api` systemd service. Open
  `http://delia-pi.local:8080` on your phone (home WiFi).
- **`led-matrix-setup.md`** — the hardware build/repair runbook. **Read this first
  if the panel misbehaves or you reflash the card.** Key facts: E address line on
  **GPIO 24** (bonnet "8" pad soldered), stock `adafruit-hat`, this panel is
  **BGR**, build the library with `make LTO_FLAGS= -j2`.
- **`diagnostics/`** — `check-address-lines.py` (verify A–E are driven),
  `tune-slowdown.sh`, `diag.py`.

## Running

The panel is driven by the `panel-renderer` + `panel-api` systemd services
(enabled on boot). To add or change scenes, edit `SCENES` in `web/server.py` or
add a `gif` asset under `panel/assets/` — see [`../../panel/README.md`](../../panel/README.md)
and the repo `CLAUDE.md`.
