# panel — declarative scene schema + renderer daemon

A long-lived **root daemon** owns the LED matrix and accepts **declarative scene
documents** over a Unix socket. An unprivileged process (the web API) validates
and forwards them. Nothing spawns a process; nothing derives a filesystem path
from caller input. This is the foundation for later work (AI-generated scenes,
MQTT, multiple devices) — the **scene schema is the contract**.

## Architecture

```
web API (mlavinder, group panel)  --newline JSON-->  /run/panel/panel.sock
                                                          |
                                          panel-renderer daemon (root)
                                                          |
                                                    RGBMatrix (GPIO)
```

- `schema.py` — Pydantic v2 contract. Strict (`extra="forbid"`), every field
  bounded, discriminated union on layer `type`. Fonts are an enum; images are an
  `asset_id` (regex, resolved+contained by the daemon). No paths, no URLs.
- `backends/` — `MatrixBackend` protocol; `rgbmatrix` (real, root-only) and
  `mock` (Pillow PNGs, for dev/CI). `PANEL_BACKEND` selects; defaults to `mock`.
- `renderer.py` — a render loop (not a launcher): ~60 FPS fixed timestep, layers
  composite back-to-front, scene switches are atomic, animation is a pure
  function of elapsed time.
- `daemon.py` — the trust boundary. Newline-JSON, 64 KiB line cap, revalidates
  every payload, structured errors, clean SIGTERM shutdown. No shelling out, no
  dynamic evaluation, no unsafe deserialization.
- `client.py` — thin sync client + CLI.
- (the phone web UI lives in the sibling root folder `../web_app/server.py` —
  Flask, unprivileged; talks to the daemon via `panel.client`; runs as `panel-api`.)
- `hardware/` — the build/repair runbook (`led-matrix-setup.md`), SD-card
  headless setup (`pi-setup/`), and diagnostics (`check-address-lines.py`,
  `tune-slowdown.sh`).
- `assets/` — image/gif assets referenced by `asset_id`. `tools/` — asset generators.

## Layer types

`solid`, `text`, `scroll`, `clock`, `image` — see `schema.py`. Example scene:

```json
{
  "name": "greeting",
  "layers": [
    {"type": "solid", "color": [0, 0, 0]},
    {"type": "text", "content": "hello", "font": "7x13", "color": [120, 40, 200],
     "align": "center", "y": 40}
  ]
}
```

## Dev (off-Pi, mock backend)

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
PANEL_BACKEND=mock .venv/bin/pytest        # all tests, no GPIO
.venv/bin/python -m panel.schema export    # writes scene.schema.json
```

## On the Pi

The daemon's Python must be able to `import rgbmatrix` (system site-packages,
root only). Install into system Python:

```bash
sudo pip install --break-system-packages "pydantic>=2" pillow
sudo pip install --break-system-packages -e /home/mlavinder/delia/panel

# create the group the socket is shared through, add the api user to it
sudo groupadd -f panel && sudo usermod -aG panel mlavinder

# run the daemon (root, rgbmatrix backend)
sudo PANEL_BACKEND=rgbmatrix python3 -m panel.daemon

# from another shell, drive it:
python3 -m panel.client set-scene scene.json
python3 -m panel.client get-state
```

### systemd

`systemd/panel-renderer.service` (root) and `panel-api.service` (unprivileged).
Install but **do not auto-enable** — that's the operator's call:

```bash
sudo cp systemd/*.service /etc/systemd/system/ && sudo systemctl daemon-reload
sudo systemctl start panel-renderer     # then panel-api
```

`systemctl stop panel-renderer` blanks the panel and removes the socket.

## Security model

The socket (root:panel, 0660) is the boundary; the tailnet/VPN is the network
boundary (no auth in the app yet — do not expose it publicly as-is). The daemon
re-validates every scene even though the API already did — that re-check, not the
API's, is what actually protects the device.
