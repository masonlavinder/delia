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

# --- BACKGROUNDS -----------------------------------------------------------
# Add a new background (gif/image/solid) here. `brightness` is optional per-bg.
BACKGROUNDS: dict[str, dict] = {
    "black": {"emoji": "⬛", "layers": [
        {"type": "solid", "color": [0, 0, 0]},
    ]},
    "plasma": {"emoji": "🌀", "brightness": 20, "layers": [
        {"type": "gif", "asset_id": "plasma", "fit": "cover", "fps": 10},
    ]},
    "rocket": {"emoji": "🚀", "layers": [
        {"type": "gif", "asset_id": "rocket", "fit": "cover", "fps": 12},
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
}


def _slug(text: str) -> str:
    out = "".join(c if (c.isalnum() or c in "-_") else "-" for c in text.lower())
    return out.strip("-") or "scene"


def compose(background: str, overlays: list[str] | None = None,
            brightness: int | None = None) -> dict:
    """Build a Scene document: background layers, then overlay layers on top."""
    if background not in BACKGROUNDS:
        raise KeyError(f"unknown background: {background!r}")
    overlays = overlays or []
    bg = BACKGROUNDS[background]
    layers = [dict(layer) for layer in bg["layers"]]
    for name in overlays:
        if name not in OVERLAYS:
            raise KeyError(f"unknown overlay: {name!r}")
        layers += [dict(layer) for layer in OVERLAYS[name]["layers"]]

    scene = {"name": _slug("-".join([background, *overlays])), "layers": layers}
    b = brightness if brightness is not None else bg.get("brightness")
    if b is not None:
        scene["brightness"] = b
    return scene


def list_backgrounds() -> list[dict]:
    return [{"name": n, "emoji": b.get("emoji")} for n, b in BACKGROUNDS.items()]


def list_overlays() -> list[dict]:
    return [{"name": n, "emoji": o.get("emoji")} for n, o in OVERLAYS.items()]
