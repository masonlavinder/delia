"""Central registry: BACKGROUNDS + OVERLAYS, composed into scene documents.

Two building blocks, one place to manage them:

  * BACKGROUNDS — the base of a scene (a gif, image, or solid color). Add a new
    background here in ONE entry and it shows up everywhere.
  * OVERLAYS   — reusable things drawn ON TOP of any background (a clock, a date,
    a label). Add one here and it can be layered onto every background.

`compose(background, overlays)` builds a daemon Scene document: the background's
layers first, then each overlay's layers on top. The daemon composites layers
back-to-front, so overlays draw over the background.

Overlays are tunable: each exposes an editable-parameter spec (text / color /
font / position) derived from its layer, and callers can pass per-overlay overrides
that get applied before compositing. The daemon re-validates everything.

Everything here must stay expressible in matrix/panel/schema.py (the contract).
Backgrounds are pure black where unlit -> those pixels stay OFF (a dark tint
would dimly light the whole panel).
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

# Fonts available on the panel (must match matrix/panel/schema.py FontName).
FONTS = ["4x6", "5x7", "6x10", "7x13", "9x18", "10x20"]

# Layer fields a user may tune. `_params_for` derives a spec from a layer so the
# client knows which controls to show; `_apply_params` writes overrides back.
_TUNABLE = ("content", "color", "font", "x", "y")

# Longest `content` each layer type accepts (matrix/panel/schema.py). We clamp to
# it here so an over-long message shortens instead of the daemon rejecting the
# whole scene.
_MAX_CONTENT = {"text": 256, "scroll": 512}


def _clean_text(value, limit: int) -> str:
    """User-typed content -> something the panel can draw. One line (the fonts
    have no notion of a newline), no control characters, length-capped."""
    text = value if isinstance(value, str) else str(value)
    text = "".join(" " if c in "\t\r\n" else c for c in text if c.isprintable() or c in "\t\r\n")
    return text[:limit]


def _params_for(layer: dict, *, dynamic: bool = False) -> dict:
    """Editable-parameter spec for a layer: what to tune and how to present it.

    A `dynamic` overlay fills its own `content` from live data, so that field is
    not the user's to type — everything else about it still is.
    """
    spec: dict = {}
    if "content" in layer and not dynamic:
        spec["content"] = {"type": "text",
                           "max_length": _MAX_CONTENT.get(layer.get("type"), 256),
                           "default": layer["content"]}
    if "color" in layer:
        spec["color"] = {"type": "color", "default": layer["color"]}
    if "font" in layer:
        spec["font"] = {"type": "font", "options": FONTS, "default": layer["font"]}
    if "x" in layer:
        spec["x"] = {"type": "int", "min": 0, "max": 128, "default": layer["x"]}
    if "y" in layer:
        spec["y"] = {"type": "int", "min": 0, "max": 64, "default": layer["y"]}
    return spec


def _apply_params(layer: dict, params: dict | None) -> dict:
    """Write caller overrides onto a layer, ignoring anything not tunable."""
    for key, val in (params or {}).items():
        if key not in _TUNABLE or key not in layer:
            continue
        if key == "content":
            val = _clean_text(val, _MAX_CONTENT.get(layer.get("type"), 256))
        layer[key] = val
    return layer


# --- weather (Open-Meteo, no API key) ---------------------------------------
# The location is deliberately NOT in this file. A home latitude/longitude is
# personal data, and it would be committed and permanent; the repo is meant to
# be shareable. Set PANEL_WEATHER_LAT / PANEL_WEATHER_LON in the Pi's
# ~/delia/.env — gitignored and rsync-excluded, the same place the API key
# lives, so the Pi owns its own copy. `.env.example` (repo root) is the
# template and explains how to find your coordinates.
#
# Unset or unparseable -> the overlay renders "--", exactly the placeholder it
# already shows when the network is down. No scene breaks and nothing else
# changes; the reason is in the journal.


def _env_coord(name: str) -> float | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        log.warning("%s=%r is not a number — weather overlay will show '--'", name, raw)
        return None


WEATHER_LAT = _env_coord("PANEL_WEATHER_LAT")
WEATHER_LON = _env_coord("PANEL_WEATHER_LON")
WEATHER_UNIT = os.environ.get("PANEL_WEATHER_UNIT", "fahrenheit")      # or "celsius"

if WEATHER_LAT is None or WEATHER_LON is None:
    log.warning(
        "no weather location — set PANEL_WEATHER_LAT and PANEL_WEATHER_LON in "
        "~/delia/.env (see .env.example). The weather overlay will show '--'."
    )

# Position/font/color of the weather readout; `content` is filled in live.
_WEATHER_TEMPLATE = {"type": "text", "content": "--", "font": "7x13",
                     "color": [255, 255, 255], "x": 100, "y": 12}


def _fetch_temp() -> int:
    if WEATHER_LAT is None or WEATHER_LON is None:
        raise RuntimeError("no weather location configured (PANEL_WEATHER_LAT/LON)")
    import requests  # server-only dep; not needed by the schema/daemon
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={WEATHER_LAT}&longitude={WEATHER_LON}"
        f"&current=temperature_2m&temperature_unit={WEATHER_UNIT}"
    )
    return round(requests.get(url, timeout=8).json()["current"]["temperature_2m"])


def _weather_layers(params: dict | None = None) -> list[dict]:
    layer = _apply_params(dict(_WEATHER_TEMPLATE), params)
    unit = "F" if WEATHER_UNIT == "fahrenheit" else "C"
    try:
        layer["content"] = f"{_fetch_temp()}{unit}"
    except Exception:
        layer["content"] = "--"   # network hiccup -> placeholder, never crash a scene
    return [layer]


# --- BACKGROUNDS -----------------------------------------------------------
# Add a new background (gif/image/solid) here. `brightness` is optional per-bg.
BACKGROUNDS: dict[str, dict] = {
    "black": {"emoji": "⬛", "layers": [
        {"type": "solid", "color": [0, 0, 0]},
    ]},
    "plasma": {"emoji": "🌀", "brightness": 20, "layers": [
        {"type": "gif", "asset_id": "plasma", "fit": "cover", "fps": 15},
    ]},
    "rocket": {"emoji": "🚀", "layers": [
        {"type": "gif", "asset_id": "rocket", "fit": "cover", "fps": 15},
    ]},
    "starfield": {"emoji": "✨", "layers": [
        {"type": "gif", "asset_id": "starfield", "fit": "cover", "fps": 12},
    ]},
    "matrix": {"emoji": "🟩", "layers": [
        {"type": "gif", "asset_id": "matrix", "fit": "cover", "fps": 14},
    ]},
    "aurora": {"emoji": "🌌", "layers": [
        {"type": "gif", "asset_id": "aurora", "fit": "cover", "fps": 14},
    ]},
    "snoopy": {"emoji": "🐶", "brightness": 30, "layers": [
        {"type": "gif", "asset_id": "snoopy", "fit": "cover", "fps": 8},
    ]},
    "fireworks": {"emoji": "🎆", "brightness": 35, "layers": [
        {"type": "gif", "asset_id": "fireworks", "fit": "cover", "fps": 15},
    ]},
    "bounce": {"emoji": "📺", "brightness": 35, "layers": [
        {"type": "gif", "asset_id": "bounce", "fit": "cover", "fps": 12},
    ]},
    "fireflies": {"emoji": "🐝", "layers": [
        {"type": "gif", "asset_id": "fireflies", "fit": "cover", "fps": 14},
    ]},
}

# --- OVERLAYS --------------------------------------------------------------
# Drawn on top of whatever background is chosen. Keep them readable on any bg
# (bright colors, near the panel edges). Their color/font/position are tunable.
OVERLAYS: dict[str, dict] = {
    "clock": {"emoji": "🕐", "layers": [
        {"type": "clock", "format": "%-I:%M", "font": "10x20",
         "color": [255, 255, 255], "x": 34, "y": 38},
    ]},
    "date": {"emoji": "📅", "layers": [
        {"type": "clock", "format": "%a %b %-d", "font": "6x10",
         "color": [255, 255, 255], "x": 30, "y": 60},
    ]},
    # Type your own line. Same shape as "label" — the difference is that this one
    # exists to be edited, so it starts blank-ish and sits mid-panel.
    "message": {"emoji": "💬", "layers": [
        {"type": "scroll", "content": "type a message", "font": "7x13",
         "color": [255, 255, 255], "y": 38, "speed_px_s": 25, "direction": "left"},
    ]},
    "label": {"emoji": "🔤", "layers": [
        {"type": "scroll", "content": "delia", "font": "7x13",
         "color": [255, 255, 255], "y": 12, "speed_px_s": 25, "direction": "left"},
    ]},
    # Dynamic: `build(params)` is called at compose time (fetches live data) and
    # applies the same tunable overrides. `template` describes its editable params
    # without a network round-trip. The server re-composes weather-bearing scenes
    # periodically so the temp stays fresh.
    "weather": {"emoji": "🌡️", "build": _weather_layers, "template": _WEATHER_TEMPLATE},
}


def _slug(text: str) -> str:
    out = "".join(c if (c.isalnum() or c in "-_") else "-" for c in text.lower())
    return out.strip("-") or "scene"


def _norm_overlays(overlays: list | None) -> list[tuple[str, dict]]:
    """Accept overlays as bare names or {"name", "params"} objects -> pairs."""
    pairs: list[tuple[str, dict]] = []
    for o in (overlays or []):
        if isinstance(o, str):
            pairs.append((o, {}))
        elif isinstance(o, dict) and o.get("name"):
            pairs.append((o["name"], o.get("params") or {}))
    return pairs


def compose(background: str, overlays: list | None = None,
            brightness: int | None = None, color: list[int] | None = None) -> dict:
    """Build a Scene document: background layers, then overlay layers on top.

    The special background "color" is a generic solid of the given RGB `color`.
    Each overlay may carry per-overlay `params` (color/font/x/y overrides).
    """
    pairs = _norm_overlays(overlays)
    if background == "color":
        layers = [{"type": "solid", "color": color or [0, 0, 0]}]
        bg_brightness = None
    else:
        if background not in BACKGROUNDS:
            raise KeyError(f"unknown background: {background!r}")
        bg = BACKGROUNDS[background]
        layers = [dict(layer) for layer in bg["layers"]]
        bg_brightness = bg.get("brightness")
    for name, params in pairs:
        ov = OVERLAYS.get(name)
        if ov is None:
            raise KeyError(f"unknown overlay: {name!r}")
        if "build" in ov:
            ov_layers = ov["build"](params)
        else:
            ov_layers = [dict(layer) for layer in ov["layers"]]
            if ov_layers:
                _apply_params(ov_layers[0], params)  # overrides land on the primary layer
        layers += ov_layers

    names = [name for name, _ in pairs]
    scene = {"name": _slug("-".join([background, *names])), "layers": layers}
    b = brightness if brightness is not None else bg_brightness
    if b is not None:
        scene["brightness"] = b
    return scene


def list_backgrounds() -> list[dict]:
    return [{"name": n, "emoji": b.get("emoji")} for n, b in BACKGROUNDS.items()]


def list_overlays() -> list[dict]:
    """Overlays plus each one's editable-parameter spec (for the UI editors).

    `dynamic` marks an overlay that fetches live data off the network. The UI
    colours those differently, so which ones they are stays declared here with
    the overlay rather than as a hardcoded name in the client.
    """
    out = []
    for n, o in OVERLAYS.items():
        dynamic = "build" in o
        template = o["template"] if "template" in o else o["layers"][0]
        out.append({"name": n, "emoji": o.get("emoji"),
                    "params": _params_for(template, dynamic=dynamic),
                    "dynamic": dynamic})
    return out


def overlays_have_dynamic(overlays: list | None) -> bool:
    """True if any of these overlays fetches live data (weather)."""
    return any("build" in (OVERLAYS.get(n) or {}) for n, _ in _norm_overlays(overlays))
