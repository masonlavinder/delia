"""Natural-language scene requests, answered by Claude.

This adds no capability the buttons don't already have. The model's only job is
to PICK from the live BACKGROUNDS / OVERLAYS registry and set the params those
overlays already expose. Its output is constrained by a JSON Schema derived
from that registry at call time, so its vocabulary can never drift from what
`scenes.py` actually offers — add a background there and the model can use it
with no change here, the same way the client needs no rebuild.

The result then goes through the same `compose()` -> daemon path as a button
tap, and the daemon re-validates it like any other scene. An LLM is just
another untrusted client of the socket: it cannot express anything the schema
forbids, name a font that isn't an enum member, or reference a file.

Optional. With no ANTHROPIC_API_KEY in the environment the feature reports
itself disabled and the UI hides it; nothing else changes.
"""
from __future__ import annotations

import json
import os

from scenes import list_backgrounds, list_overlays

# Swap the model without a code change:  PANEL_AI_MODEL=claude-haiku-4-5
MODEL = os.environ.get("PANEL_AI_MODEL", "claude-opus-5")
# Picking from a short menu is not hard thinking, and this is a phone tapping a
# button — low effort keeps it feeling instant.
EFFORT = os.environ.get("PANEL_AI_EFFORT", "low")
TIMEOUT_S = float(os.environ.get("PANEL_AI_TIMEOUT", "60"))

MAX_PROMPT = 500


class AiError(RuntimeError):
    """Anything that stopped us producing a scene: no key, API failure, bad JSON."""


def enabled() -> bool:
    """True when a key is present. Checked per-call so adding one to the unit
    and restarting is enough — no rebuild, no code path to flip."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


# --- schema, derived from the registry -------------------------------------
# Structured outputs supports enum/const/anyOf/null but NOT `minimum`,
# `maximum`, or `maxLength`. Ranges are therefore documented in prose here and
# enforced by _to_request() below, so an out-of-range number is clamped rather
# than rejected by the daemon as a whole broken scene.


def _nullable(inner: dict) -> dict:
    """An optional field: null means 'leave this one alone'."""
    return {"anyOf": [inner, {"type": "null"}]}


def _param_schema(spec: dict) -> dict:
    """One tunable param, from the same spec `_params_for` hands the client."""
    if spec["type"] == "color":
        return _nullable({"type": "string", "description": "hex, e.g. #ff8800"})
    if spec["type"] == "font":
        return _nullable({"type": "string", "enum": spec["options"]})
    return _nullable({"type": "integer", "description": f"{spec['min']}..{spec['max']}"})


def _overlay_schema(overlay: dict) -> dict:
    """One overlay variant. Each overlay gets its OWN param shape, so the model
    can't set `x` on a scroll layer (which has no x, and would make the daemon
    reject the scene)."""
    props = {key: _param_schema(spec) for key, spec in overlay["params"].items()}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"const": overlay["name"]},
            "params": {
                "type": "object",
                "additionalProperties": False,
                "properties": props,
                "required": list(props),
            },
        },
        "required": ["name", "params"],
    }


def _schema() -> dict:
    names = [b["name"] for b in list_backgrounds()] + ["color"]
    variants = [_overlay_schema(o) for o in list_overlays()]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "background": {"type": "string", "enum": names},
            "color": _nullable(
                {"type": "string", "description": 'hex; only used when background is "color"'}
            ),
            "brightness": _nullable({"type": "integer", "description": "1..100"}),
            "overlays": {"type": "array", "items": {"anyOf": variants}},
            "note": {"type": "string", "description": "one short line for the app"},
        },
        "required": ["background", "color", "brightness", "overlays", "note"],
    }


def _system() -> str:
    """The menu plus what this physical panel is actually like. The registry is
    rendered in, so a new background is described to the model automatically."""
    backgrounds = "\n".join(
        f"  {b['emoji'] or ' '} {b['name']}" for b in list_backgrounds()
    )
    overlays = "\n".join(
        f"  {o['emoji'] or ' '} {o['name']}  (tunable: {', '.join(o['params']) or 'nothing'})"
        for o in list_overlays()
    )
    return f"""You dress a 128x64 RGB LED matrix — a bedside panel, read from across a room.

Pick ONE background and any number of overlays from this fixed menu.

backgrounds:
{backgrounds}
  🎨 color   a solid fill of any colour you choose

overlays (drawn on top, in the order you list them):
{overlays}

What this panel is actually like:
- It is a grid of physical LEDs, not a screen. Saturated, bright colours read
  well; dark or desaturated ones just look muddy.
- Text vanishes without hard contrast. Over a busy animated background, prefer
  white or one very bright colour.
- x is from the left edge; y is the text BASELINE from the top. The clock in
  10x20 is about 60px wide, so x=34 y=38 centres it.
- brightness is 1..100 and should stay modest: 15-40 in a dark room, up to 70
  in daylight. Animated backgrounds want the lower end.

Rules:
- Set a param only when the request implies it. Leave the others null and the
  panel keeps its current, hand-tuned value.
- "off", "dark", or "nothing" means the "black" background with no overlays.
- `note` is one short lowercase line shown in the app — what you picked, in a
  few words, no trailing punctuation.
"""


# --- the call ---------------------------------------------------------------


def plan_scene(prompt: str) -> dict:
    """Ask Claude for a scene selection. Returns a body `/api/scene` accepts,
    plus a `note`. Raises AiError for anything that went wrong."""
    if not enabled():
        raise AiError("no ANTHROPIC_API_KEY in the environment")
    try:
        import anthropic  # server-only dep; the engine and daemon never import this
    except ImportError as exc:
        raise AiError("the `anthropic` package is not installed") from exc

    client = anthropic.Anthropic(timeout=TIMEOUT_S, max_retries=1)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=_system(),
            messages=[{"role": "user", "content": prompt}],
            output_config={
                "effort": EFFORT,
                "format": {"type": "json_schema", "schema": _schema()},
            },
        )
    except anthropic.APIError as exc:
        raise AiError(f"claude: {exc}") from exc

    if response.stop_reason == "refusal":
        raise AiError("claude declined that one")
    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise AiError("claude returned no scene")
    try:
        plan = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AiError("claude returned malformed JSON") from exc
    return _to_request(plan)


# --- model output -> an /api/scene body -------------------------------------


def _hex_to_rgb(value: str) -> list[int] | None:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        return None
    try:
        return [int(text[i:i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        return None


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _to_request(plan: dict) -> dict:
    """Normalize the model's plan into the body the buttons already send.

    Nulls are dropped (= don't touch), hex becomes [r,g,b], and numbers are
    clamped to each param's declared range — the schema can't express bounds,
    so we do it here rather than let one bad coordinate sink the whole scene.
    """
    specs = {o["name"]: o["params"] for o in list_overlays()}

    overlays = []
    for item in plan.get("overlays") or []:
        name = item.get("name")
        if name not in specs:
            continue  # enum-constrained already; belt and braces
        params: dict = {}
        for key, raw in (item.get("params") or {}).items():
            spec = specs[name].get(key)
            if raw is None or spec is None:
                continue
            if spec["type"] == "color":
                rgb = _hex_to_rgb(raw) if isinstance(raw, str) else None
                if rgb:
                    params[key] = rgb
            elif spec["type"] == "font":
                if raw in spec["options"]:
                    params[key] = raw
            elif _is_int(raw):
                params[key] = _clamp(raw, spec["min"], spec["max"])
        overlays.append({"name": name, "params": params})

    request: dict = {
        "background": plan["background"],
        "overlays": overlays,
        "note": (plan.get("note") or "").strip(),
    }
    if _is_int(plan.get("brightness")):
        request["brightness"] = _clamp(plan["brightness"], 1, 100)
    if isinstance(plan.get("color"), str):
        request["color"] = _hex_to_rgb(plan["color"])
    if request["background"] == "color" and not request.get("color"):
        request["color"] = [255, 255, 255]  # a colour scene with no colour is just off
    return request
