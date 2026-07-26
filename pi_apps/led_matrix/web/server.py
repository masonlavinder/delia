#!/usr/bin/env python3
"""Web control server — talks to the panel renderer daemon over its Unix socket.

Performs NO privileged operation: no subprocess, no sudo. Switching a scene is a
single JSON message to the daemon, which validates and renders it. The daemon is
the trust boundary; this process only needs `panel` group membership to reach the
socket.

Run:   python3 server.py        (or the panel-api systemd unit)
Open:  http://delia-pi.local:8080
"""
import os

from flask import Flask, Response, jsonify, request

# The panel package is installed system-wide; the client is pure Python (no GPIO).
from panel.client import PanelClient

client = PanelClient(sock_path=os.environ.get("PANEL_SOCK", "/run/panel/panel.sock"))

# Built-in declarative scenes (each expressible in the daemon's layer types).
SCENES: dict[str, dict] = {
    "clock": {"name": "clock", "layers": [
        {"type": "solid", "color": [0, 0, 0]},
        {"type": "clock", "format": "%-I:%M", "font": "10x20", "color": [0, 120, 255], "x": 34, "y": 40},
    ]},
    "hello": {"name": "hello", "layers": [
        {"type": "solid", "color": [0, 0, 0]},
        {"type": "text", "content": "HELLO", "font": "9x18", "color": [150, 40, 220], "align": "center", "y": 40},
    ]},
    "scroll": {"name": "scroll", "layers": [
        {"type": "solid", "color": [0, 0, 0]},
        {"type": "scroll", "content": "delia panel online", "font": "7x13", "color": [0, 200, 120],
         "y": 38, "speed_px_s": 30, "direction": "left"},
    ]},
}

app = Flask(__name__)


@app.get("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.get("/api/scenes")
def api_scenes():
    current = None
    try:
        state = client.get_state()
        if state.get("ok"):
            current = state.get("scene")
    except OSError:
        pass  # daemon down -> report nothing playing
    return jsonify(scenes=list(SCENES), current=current)


@app.post("/api/scene")
def api_scene():
    name = (request.get_json(silent=True) or {}).get("name")
    if name not in SCENES:
        return jsonify(ok=False, error="unknown scene"), 400
    try:
        result = client.set_scene(SCENES[name])
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


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>delia panel</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  body { margin: 0; font: 16px/1.4 system-ui, sans-serif; background: #0b0b12; color: #e8e8f0;
         padding: max(16px, env(safe-area-inset-top)) 16px 24px; }
  h1 { font-size: 20px; margin: 4px 0 2px; }
  .sub { color: #8a8aa0; font-size: 13px; margin-bottom: 18px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  button { appearance: none; border: 1px solid #2a2a3c; background: #16161f; color: #e8e8f0;
           border-radius: 14px; padding: 22px 12px; font-size: 17px; font-weight: 600;
           display: flex; flex-direction: column; align-items: center; gap: 6px; cursor: pointer; }
  button:active { transform: scale(0.97); }
  button.active { background: #6d28d9; border-color: #8b5cf6; box-shadow: 0 0 0 2px #8b5cf655; }
  .emoji { font-size: 26px; }
  .off { grid-column: 1 / -1; background: #1c1420; border-color: #442; color: #f0a0a0; margin-top: 6px; }
  .off.active { background: #3a1020; border-color: #a33; }
</style>
</head>
<body>
  <h1>💡 delia panel</h1>
  <div class="sub" id="status">loading…</div>
  <div class="grid" id="grid"></div>
<script>
const EMOJI = { clock:"🕐", hello:"👋", scroll:"🔤" };
let current = null;

async function load() {
  const r = await fetch("/api/scenes"); const d = await r.json();
  current = d.current;
  const grid = document.getElementById("grid"); grid.innerHTML = "";
  for (const s of d.scenes) {
    const b = document.createElement("button");
    b.className = (s === current) ? "active" : "";
    b.innerHTML = `<span class="emoji">${EMOJI[s] || "▫️"}</span>${s}`;
    b.onclick = () => run(s, b);
    grid.appendChild(b);
  }
  const off = document.createElement("button");
  off.className = "off" + (current ? "" : " active");
  off.textContent = current ? "⏻ turn off" : "○ off";
  off.onclick = () => turnOff();
  grid.appendChild(off);
  document.getElementById("status").textContent = current ? ("playing: " + current) : "panel is off";
}
async function run(name, btn) {
  document.querySelectorAll("button").forEach(x => x.classList.remove("active"));
  btn.classList.add("active");
  await fetch("/api/scene", { method:"POST", headers:{"Content-Type":"application/json"},
                              body: JSON.stringify({name}) });
  load();
}
async function turnOff() { await fetch("/api/off", { method:"POST" }); load(); }
load();
setInterval(load, 5000);
</script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
