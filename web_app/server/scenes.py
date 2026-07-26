"""Central registry: BACKGROUNDS + OVERLAYS, composed into scene documents.

Two building blocks, one place to manage them:

  * BACKGROUNDS — the base of a scene (a gif, image, or solid color). Add a new
    background here in ONE entry and it shows up everywhere.
  * OVERLAYS   — reusable things drawn ON TOP of any background (a clock, a date,
    a label). Add one here and it can be layered onto every background.

`compose(background, overlays)` builds a daemon Scene document: the background's
layers first, then each overlay's layers on top. The daemon composites layers
back-to-front, so overlays draw over the background.

Everything here must stay expressible in matrix/panel/schema.py (the contract).
Backgrounds are pure black where unlit -> those pixels stay OFF (a dark tint
would dimly light the whole panel).
"""
from __future__ import annotations

import os

# --- weather (Open-Meteo, no API key). Change location via env or here. ------
WEATHER_LAT = float(os.environ.get("PANEL_WEATHER_LAT", "0.00"))     # REDACTED
WEATHER_LON = float(os.environ.get("PANEL_WEATHER_LON", "0.00"))
WEATHER_UNIT = os.environ.get("PANEL_WEATHER_UNIT", "fahrenheit")      # or "celsius"


def _fetch_temp() -> int:
    import requests  # server-only dep; not needed by the schema/daemon
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={WEATHER_LAT}&longitude={WEATHER_LON}"
        f"&current=temperature_2m&temperature_unit={WEATHER_UNIT}"
    )
    return round(requests.get(url, timeout=8).json()["current"]["temperature_2m"])


def _weather_layers() -> list[dict]:
    unit = "F" if WEATHER_UNIT == "fahrenheit" else "C"
    try:
        text = f"{_fetch_temp()}{unit}"
    except Exception:
        text = "--"   # network hiccup -> placeholder, never crash a scene
    return [{"type": "text", "content": text, "font": "7x13",
             "color": [120, 200, 255], "x": 100, "y": 12}]


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
}

# --- OVERLAYS --------------------------------------------------------------
# Drawn on top of whatever background is chosen. Keep them readable on any bg
# (bright colors, near the panel edges).
OVERLAYS: dict[str, dict] = {
    "clock": {"emoji": "🕐", "layers": [
        {"type": "clock", "format": "%-I:%M", "font": "10x20",
         "color": [255, 255, 255], "x": 34, "y": 38},
    ]},
    "date": {"emoji": "📅", "layers": [
        {"type": "clock", "format": "%a %b %-d", "font": "6x10",
         "color": [210, 210, 210], "x": 30, "y": 60},
    ]},
    "label": {"emoji": "🔤", "layers": [
        {"type": "scroll", "content": "delia", "font": "7x13",
         "color": [0, 200, 120], "y": 12, "speed_px_s": 25, "direction": "left"},
    ]},
    # Dynamic: `build` is called at compose time (fetches live data). The server
    # re-composes weather-bearing scenes periodically so the temp stays fresh.
    "weather": {"emoji": "🌡️", "build": _weather_layers},
}


def _slug(text: str) -> str:
    out = "".join(c if (c.isalnum() or c in "-_") else "-" for c in text.lower())
    return out.strip("-") or "scene"


def compose(background: str, overlays: list[str] | None = None,
            brightness: int | None = None, color: list[int] | None = None) -> dict:
    """Build a Scene document: background layers, then overlay layers on top.

    The special background "color" is a generic solid of the given RGB `color`.
    """
    overlays = overlays or []
    if background == "color":
        layers = [{"type": "solid", "color": color or [0, 0, 0]}]
        bg_brightness = None
    else:
        if background not in BACKGROUNDS:
            raise KeyError(f"unknown background: {background!r}")
        bg = BACKGROUNDS[background]
        layers = [dict(layer) for layer in bg["layers"]]
        bg_brightness = bg.get("brightness")
    for name in overlays:
        ov = OVERLAYS.get(name)
        if ov is None:
            raise KeyError(f"unknown overlay: {name!r}")
        ov_layers = ov["build"]() if "build" in ov else ov["layers"]
        layers += [dict(layer) for layer in ov_layers]

    scene = {"name": _slug("-".join([background, *overlays])), "layers": layers}
    b = brightness if brightness is not None else bg_brightness
    if b is not None:
        scene["brightness"] = b
    return scene


def list_backgrounds() -> list[dict]:
    return [{"name": n, "emoji": b.get("emoji")} for n, b in BACKGROUNDS.items()]


def list_overlays() -> list[dict]:
    return [{"name": n, "emoji": o.get("emoji")} for n, o in OVERLAYS.items()]


def has_dynamic(scene_name: str) -> bool:
    """True if a composed scene name includes an overlay with live data (weather)."""
    return any(p in OVERLAYS and "build" in OVERLAYS[p] for p in scene_name.split("-"))


def recompose(scene_name: str) -> dict | None:
    """Rebuild a composed scene from its name, re-running dynamic overlays so
    their content refreshes. None if the name has no known background."""
    parts = scene_name.split("-")
    background = next((p for p in parts if p in BACKGROUNDS), None)
    if background is None:
        return None
    return compose(background, [p for p in parts if p in OVERLAYS])
