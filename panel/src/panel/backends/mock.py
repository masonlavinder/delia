"""Mock backend — renders to Pillow images, optionally writing PNGs. Needs no
GPIO, no rgbmatrix, and no font files, so tests and dev run anywhere.

Text is drawn as filled character-cell blocks (deterministic, asset-free);
exact glyphs don't matter for layout/order/animation tests.
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw

from ..schema import FontName
from .base import LoadedFont, font_dimensions


class MockCanvas:
    def __init__(self, width: int, height: int):
        self.image = Image.new("RGB", (width, height), (0, 0, 0))
        self._draw = ImageDraw.Draw(self.image)

    def fill(self, color):
        self._draw.rectangle([0, 0, self.image.width - 1, self.image.height - 1],
                             fill=tuple(color))

    def set_pixel(self, x, y, color):
        if 0 <= x < self.image.width and 0 <= y < self.image.height:
            self.image.putpixel((x, y), tuple(color))

    def draw_text(self, font: LoadedFont, x, y, color, text):
        w, h = font.char_w, font.char_h
        top = y - h                      # y is the baseline (bottom), like graphics.DrawText
        for i, ch in enumerate(text):
            if ch == " ":
                continue
            cx = x + i * w
            self._draw.rectangle([cx, top, cx + w - 1, top + h - 1], fill=tuple(color))
        return len(text) * w

    def set_image(self, image, x=0, y=0):
        self.image.paste(image.convert("RGB"), (int(x), int(y)))


class MockBackend:
    def __init__(self, width: int = 128, height: int = 64, out_dir: str | None = None):
        self.width = width
        self.height = height
        self.brightness = 40
        self.out_dir = out_dir
        self.last_frame: Image.Image | None = None
        self._buffers = [MockCanvas(width, height), MockCanvas(width, height)]
        self._i = 0
        self._frame = 0

    def create_canvas(self) -> MockCanvas:
        return self._buffers[self._i]

    def swap(self, canvas: MockCanvas) -> MockCanvas:
        self.last_frame = canvas.image.copy()
        if self.out_dir:
            os.makedirs(self.out_dir, exist_ok=True)
            canvas.image.save(os.path.join(self.out_dir, f"frame_{self._frame:06d}.png"))
        self._frame += 1
        self._i ^= 1
        return self._buffers[self._i]

    def set_brightness(self, pct: int) -> None:
        self.brightness = int(pct)

    def load_font(self, name: FontName) -> LoadedFont:
        w, h = font_dimensions(name)
        return LoadedFont(name=name, char_w=w, char_h=h, native=None)

    def close(self) -> None:
        pass
