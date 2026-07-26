#!/usr/bin/env python3
"""Web control server — talks to the panel renderer daemon over its Unix socket.

Performs NO privileged operation: no subprocess, no sudo. Switching a scene is a
single JSON message to the daemon, which validates and renders it. The daemon is
the trust boundary; this process only needs `panel` group membership to reach the
socket.

Serves two things:
  * `/api/*`     — the JSON control API consumed by the React client
  * everything else — the built client from `web_app/client/dist`

The client is a Vite/React app built ahead of time on a dev machine (the Pi 3 A+
has 512 MB — see web_app/README.md). Same origin, so no CORS.

Run:   python3 server/server.py     (or the panel-api systemd unit)
Open:  http://delia-pi.local:8080
"""
import os
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

# The panel package is installed system-wide; the client is pure Python (no GPIO).
from panel.client import PanelClient

from scenes import compose, has_dynamic, list_backgrounds, list_overlays, recompose

CLIENT_DIST = Path(__file__).resolve().parent.parent / "client" / "dist"

client = PanelClient(sock_path=os.environ.get("PANEL_SOCK", "/run/panel/panel.sock"))

app = Flask(__name__, static_folder=str(CLIENT_DIST), static_url_path="")


def _refresh_dynamic_scenes(interval_s: int = 600) -> None:
    """Periodically re-apply the active scene if it has a live overlay (weather),
    so its data doesn't go stale. Static scenes are left untouched."""
    import threading
    import time

    def loop():
        while True:
            time.sleep(interval_s)
            try:
                state = client.get_state()
                name = state.get("scene") if state.get("ok") else None
                if name and has_dynamic(name):
                    scene = recompose(name)
                    if scene:
                        client.set_scene(scene)
            except Exception:
                pass  # transient (daemon/network) -> try again next tick

    threading.Thread(target=loop, name="weather-refresh", daemon=True).start()


_refresh_dynamic_scenes()


# ---------------------------------------------------------------- control API

def _current_scene():
    try:
        state = client.get_state()
        return state.get("scene") if state.get("ok") else None
    except OSError:
        return None  # daemon down -> report nothing playing


@app.get("/api/backgrounds")
def api_backgrounds():
    return jsonify(backgrounds=list_backgrounds(), current=_current_scene())


@app.get("/api/overlays")
def api_overlays():
    return jsonify(overlays=list_overlays())


@app.get("/api/scenes")
def api_scenes():
    # Back-compat alias: older clients treat each background as a tappable "scene".
    return jsonify(scenes=list_backgrounds(), current=_current_scene())


@app.post("/api/scene")
def api_scene():
    """Set a scene = a background + optional overlays.

    Body: {"background": "plasma", "overlays": ["clock"]}
    ({"name": "plasma"} is still accepted and means the background alone.)
    """
    body = request.get_json(silent=True) or {}
    background = body.get("background") or body.get("name")
    overlays = body.get("overlays") or []
    if not background:
        return jsonify(ok=False, error="background required"), 400
    if not isinstance(overlays, list):
        return jsonify(ok=False, error="overlays must be a list"), 400
    try:
        scene = compose(background, overlays, brightness=body.get("brightness"))
    except KeyError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    try:
        result = client.set_scene(scene)
    except OSError as exc:
        return jsonify(ok=False, error=f"renderer unreachable: {exc}"), 503
    return jsonify(result), (200 if result.get("ok") else 400)


@app.post("/api/off")
def api_off():
    try:
        client.clear()
    except OSError as exc:
        return jsonify(ok=False, error=str(exc)), 503
    return jsonify(ok=True)


# ------------------------------------------------------------- static client

@app.get("/")
def index():
    return _client_index()


@app.errorhandler(404)
def spa_fallback(_exc):
    """Unknown non-API path -> hand back the SPA shell so client routing works."""
    if request.path.startswith("/api/"):
        return jsonify(ok=False, error="not found"), 404
    return _client_index()


def _client_index():
    if not (CLIENT_DIST / "index.html").is_file():
        return Response(
            "Client not built.\n\n"
            "  cd web_app/client && npm install && npm run build\n\n"
            f"Expected: {CLIENT_DIST / 'index.html'}\n",
            status=503,
            mimetype="text/plain",
        )
    return send_from_directory(CLIENT_DIST, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
