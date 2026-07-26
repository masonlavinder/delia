"""Built-in scene documents.

Each entry is a declarative document expressible in the daemon's layer types
(see `matrix/panel/schema.py` — that schema is the contract). Adding a scene
here is the only step needed for it to appear in the UI; the client renders
whatever `/api/scenes` returns.

Backgrounds are pure black `(0, 0, 0)` on purpose: unlit pixels stay OFF. A dark
tint would dimly light every pixel on the panel.
"""

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
    "plasma": {"name": "plasma", "brightness": 20, "layers": [
        {"type": "gif", "asset_id": "plasma", "fit": "cover", "fps": 10},
    ]},
    "rocket": {"name": "rocket", "layers": [
        {"type": "gif", "asset_id": "rocket", "fit": "cover", "fps": 12},
    ]},
}

# Presentation-only hint for the client. Kept beside the scenes so adding a
# scene is a one-file change; the client falls back to a neutral glyph.
SCENE_EMOJI: dict[str, str] = {
    "clock": "🕐",
    "hello": "👋",
    "scroll": "🔤",
    "plasma": "🌀",
    "rocket": "🚀",
}
