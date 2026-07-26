"""Scene schema — the contract every other component depends on.

Pydantic v2. Strict (`extra="forbid"`) everywhere, every numeric field bounded,
every string length-capped, no field ever carries a filesystem path or URL.
Imports with no `rgbmatrix` and no hardware, so it runs on a laptop and in CI.

Fonts are an enum (never a path). Images are an `asset_id` matched against a
regex (never a path/URL) — the daemon resolves and confirms containment.
"""
from __future__ import annotations

import json
import sys
from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

# ---------------------------------------------------------------------------
# enums (closed vocabularies — a caller can never widen these)
# ---------------------------------------------------------------------------


class FontName(StrEnum):
    """BDF fonts shipped with rpi-rgb-led-matrix. Value = base filename stem.

    The daemon resolves the enum to `<fonts_dir>/<value>.bdf` itself; a caller
    only ever sends the enum, never a path.
    """

    F4x6 = "4x6"
    F5x7 = "5x7"
    F6x10 = "6x10"
    F7x13 = "7x13"
    F9x18 = "9x18"
    F10x20 = "10x20"


class Align(StrEnum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class Direction(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class Fit(StrEnum):
    NONE = "none"
    CONTAIN = "contain"
    COVER = "cover"


ALL_LAYER_TYPES: tuple[str, ...] = ("solid", "text", "scroll", "clock", "image")

# Generous sanity bounds on coordinates; per-device panel bounds are enforced
# separately by validate_scene() against Capabilities.
_COORD = dict(ge=-1024, le=1024)
_ASSET_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"
_SLUG_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"


# ---------------------------------------------------------------------------
# color — accepts [r,g,b] or {"r":..,"g":..,"b":..}, normalized to fields
# ---------------------------------------------------------------------------


class Color(BaseModel):
    model_config = ConfigDict(extra="forbid")

    r: int = Field(ge=0, le=255)
    g: int = Field(ge=0, le=255)
    b: int = Field(ge=0, le=255)

    @model_validator(mode="before")
    @classmethod
    def _accept_sequence(cls, v):
        if isinstance(v, (list, tuple)):
            if len(v) != 3:
                raise ValueError("color sequence must be exactly [r, g, b]")
            return {"r": v[0], "g": v[1], "b": v[2]}
        return v

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)


# ---------------------------------------------------------------------------
# layers — discriminated union on `type`
# ---------------------------------------------------------------------------


class _StrictLayer(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SolidLayer(_StrictLayer):
    type: Literal["solid"] = "solid"
    color: Color


class TextLayer(_StrictLayer):
    type: Literal["text"] = "text"
    content: str = Field(max_length=256)
    font: FontName = FontName.F7x13
    color: Color
    x: int = Field(default=0, **_COORD)
    y: int = Field(default=13, **_COORD)
    align: Align = Align.LEFT


class ScrollLayer(_StrictLayer):
    type: Literal["scroll"] = "scroll"
    content: str = Field(max_length=512)
    font: FontName = FontName.F7x13
    color: Color
    y: int = Field(default=13, **_COORD)
    speed_px_s: int = Field(default=30, ge=1, le=120)
    direction: Direction = Direction.LEFT


class ClockLayer(_StrictLayer):
    type: Literal["clock"] = "clock"
    format: str = Field(default="%H:%M", max_length=32)
    font: FontName = FontName.F10x20
    color: Color
    x: int = Field(default=0, **_COORD)
    y: int = Field(default=20, **_COORD)


class ImageLayer(_StrictLayer):
    type: Literal["image"] = "image"
    asset_id: str = Field(pattern=_ASSET_ID_PATTERN)
    x: int = Field(default=0, **_COORD)
    y: int = Field(default=0, **_COORD)
    fit: Fit = Fit.NONE


Layer = Annotated[
    Union[SolidLayer, TextLayer, ScrollLayer, ClockLayer, ImageLayer],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# scene + capabilities
# ---------------------------------------------------------------------------


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=_SLUG_PATTERN)
    layers: list[Layer] = Field(min_length=1, max_length=8)  # back-to-front
    duration_s: int | None = Field(default=None, ge=1, le=86400)
    brightness: int | None = Field(default=None, ge=1, le=100)


class Capabilities(BaseModel):
    """What a device can render. Exists so a second device can advertise a
    different panel later without changing the schema."""

    model_config = ConfigDict(extra="forbid")

    width: int = Field(ge=1, le=4096)
    height: int = Field(ge=1, le=4096)
    color_depth: int = Field(ge=1, le=24)
    supported_layer_types: list[str] = Field(max_length=32)
    supported_fonts: list[FontName] = Field(max_length=64)


# The capabilities of THIS panel (Adafruit 128x64 2mm on the Bonnet).
PANEL_CAPABILITIES = Capabilities(
    width=128,
    height=64,
    color_depth=24,
    supported_layer_types=list(ALL_LAYER_TYPES),
    supported_fonts=list(FontName),
)


# ---------------------------------------------------------------------------
# validation — schema + capability check (the security boundary)
# ---------------------------------------------------------------------------


class SceneCapabilityError(ValueError):
    """Scene is schema-valid but not renderable by this device."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_scene(payload: dict, caps: Capabilities) -> Scene:
    """Validate a raw payload against the schema AND the device capabilities.

    Both the API process and the daemon call this. The daemon re-calling it is
    NOT redundant — it is the actual trust boundary. Raises pydantic
    ValidationError for schema problems, SceneCapabilityError for device ones.
    """
    scene = Scene.model_validate(payload)

    errors: list[str] = []
    for i, layer in enumerate(scene.layers):
        if layer.type not in caps.supported_layer_types:
            errors.append(f"layers[{i}]: type '{layer.type}' unsupported by device")

        font = getattr(layer, "font", None)
        if font is not None and font not in caps.supported_fonts:
            errors.append(f"layers[{i}]: font '{font}' not available on device")

        # anchor coordinates must fall within the panel
        if (x := getattr(layer, "x", None)) is not None and not (0 <= x <= caps.width):
            errors.append(f"layers[{i}]: x={x} outside panel width 0..{caps.width}")
        if (y := getattr(layer, "y", None)) is not None and not (0 <= y <= caps.height):
            errors.append(f"layers[{i}]: y={y} outside panel height 0..{caps.height}")

    if errors:
        raise SceneCapabilityError(errors)
    return scene


# ---------------------------------------------------------------------------
# JSON Schema export CLI:  python -m panel.schema export [outfile]
# ---------------------------------------------------------------------------


def export_schema(path: str = "scene.schema.json") -> str:
    schema = Scene.model_json_schema()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(schema, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def _cli(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "export":
        out = argv[1] if len(argv) > 1 else "scene.schema.json"
        print(f"wrote {export_schema(out)}")
        return 0
    print("usage: python -m panel.schema export [outfile]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())


__all__ = [
    "FontName", "Align", "Direction", "Fit", "Color",
    "SolidLayer", "TextLayer", "ScrollLayer", "ClockLayer", "ImageLayer",
    "Layer", "Scene", "Capabilities", "PANEL_CAPABILITIES",
    "ALL_LAYER_TYPES", "SceneCapabilityError", "validate_scene",
    "export_schema", "ValidationError",
]
