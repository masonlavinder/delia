"""Backend abstraction: the renderer draws through these, so it runs on a laptop
(mock backend) or the Pi (rgbmatrix backend) unchanged.

The renderer never imports `rgbmatrix` or `graphics` — the rgbmatrix Canvas uses
them internally; the mock Canvas uses Pillow. That is what makes the renderer
and its tests run off-device.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..schema import FontName


@dataclass
class LoadedFont:
    """A font ready to draw. `char_w`/`char_h` come from the enum name (fonts are
    fixed-width, e.g. '7x13'), which lets both backends measure text identically
    for alignment/scroll without touching a font file off-device."""

    name: FontName
    char_w: int
    char_h: int
    native: Any = None   # graphics.Font (rgbmatrix) or None (mock)


def font_dimensions(name: FontName) -> tuple[int, int]:
    """'7x13' -> (7, 13)."""
    w, _, h = name.value.partition("x")
    return int(w), int(h)


@runtime_checkable
class Canvas(Protocol):
    def fill(self, color: tuple[int, int, int]) -> None: ...
    def set_pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None: ...
    def draw_text(self, font: LoadedFont, x: int, y: int,
                  color: tuple[int, int, int], text: str) -> int: ...
    def set_image(self, image: Any, x: int = 0, y: int = 0) -> None: ...


@runtime_checkable
class MatrixBackend(Protocol):
    width: int
    height: int

    def create_canvas(self) -> Canvas: ...
    def swap(self, canvas: Canvas) -> Canvas: ...
    def set_brightness(self, pct: int) -> None: ...
    def load_font(self, name: FontName) -> LoadedFont: ...
    def close(self) -> None: ...
