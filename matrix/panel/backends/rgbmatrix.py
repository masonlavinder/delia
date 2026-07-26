"""Real-hardware backend. Only imports on the Pi, as root.

Known-working config for this panel (do not change; see led-matrix-setup.md):
rows=64, cols=128, adafruit-hat (E on stock GPIO 24), gpio_slowdown=2.
Double-buffered via CreateFrameCanvas()/SwapOnVSync().
"""
from __future__ import annotations

import os
from typing import Any

from ..schema import FontName
from .base import LoadedFont, font_dimensions

# rgbmatrix imports successfully only as root, only on the device. Give a clear
# error off-device instead of a bare ImportError traceback.
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
except Exception as exc:  # noqa: BLE001 - want any import/runtime failure here
    raise RuntimeError(
        "rgbmatrix backend unavailable: the library imports only on the Pi and "
        "only as root. Off-device, use PANEL_BACKEND=mock."
    ) from exc

# Fonts live with the built library. Root's ~ is /root, so resolve explicitly;
# override with PANEL_FONTS_DIR if the library lives elsewhere.
FONTS_DIR = os.environ.get(
    "PANEL_FONTS_DIR", "/home/mlavinder/rpi-rgb-led-matrix/fonts"
)


class _RGBCanvas:
    def __init__(self, native):
        self.native = native

    def fill(self, color):
        self.native.Fill(int(color[0]), int(color[1]), int(color[2]))

    def set_pixel(self, x, y, color):
        self.native.SetPixel(int(x), int(y), int(color[0]), int(color[1]), int(color[2]))

    def draw_text(self, font: LoadedFont, x, y, color, text):
        gcolor = graphics.Color(int(color[0]), int(color[1]), int(color[2]))
        return graphics.DrawText(self.native, font.native, int(x), int(y), gcolor, text)

    def set_image(self, image: Any, x=0, y=0):
        self.native.SetImage(image.convert("RGB"), int(x), int(y))


class RGBMatrixBackend:
    def __init__(self):
        opts = RGBMatrixOptions()
        opts.rows = 64
        opts.cols = 128
        opts.chain_length = 1
        opts.parallel = 1
        opts.hardware_mapping = "adafruit-hat"
        opts.gpio_slowdown = int(os.environ.get("PANEL_GPIO_SLOWDOWN", "2"))
        opts.brightness = int(os.environ.get("PANEL_BRIGHTNESS", "40"))
        # Full color depth (11). Flashing lines that show ONLY on lit pixels are a
        # POWER issue (5V sag under load), not refresh -- lowering pwm_bits doesn't
        # fix it and costs color, so keep it high. Lower PANEL_BRIGHTNESS to reduce
        # current draw if the supply/wiring sags on full-panel scenes.
        opts.pwm_bits = int(os.environ.get("PANEL_PWM_BITS", "11"))
        # This panel is wired BGR: without this, red<->blue are swapped. One
        # setting corrects Fill/DrawText/SetImage uniformly. Override if a future
        # panel differs.
        opts.led_rgb_sequence = os.environ.get("PANEL_RGB_SEQUENCE", "BGR")
        opts.drop_privileges = False
        self._m = RGBMatrix(options=opts)
        self.width = self._m.width
        self.height = self._m.height
        self._font_cache: dict[FontName, LoadedFont] = {}

    def create_canvas(self) -> _RGBCanvas:
        return _RGBCanvas(self._m.CreateFrameCanvas())

    def swap(self, canvas: _RGBCanvas) -> _RGBCanvas:
        return _RGBCanvas(self._m.SwapOnVSync(canvas.native))

    def set_brightness(self, pct: int) -> None:
        self._m.brightness = max(1, min(100, int(pct)))

    def load_font(self, name: FontName) -> LoadedFont:
        if name in self._font_cache:
            return self._font_cache[name]
        base = os.path.realpath(FONTS_DIR)
        path = os.path.realpath(os.path.join(base, name.value + ".bdf"))
        # containment check (enum already constrains this, but defense in depth)
        if not (path == base or path.startswith(base + os.sep)) or not os.path.isfile(path):
            raise FileNotFoundError(f"font not found: {name.value} (looked in {FONTS_DIR})")
        f = graphics.Font()
        f.LoadFont(path)
        w, h = font_dimensions(name)
        loaded = LoadedFont(name=name, char_w=w, char_h=h, native=f)
        self._font_cache[name] = loaded
        return loaded

    def close(self) -> None:
        try:
            self._m.Clear()
        except Exception:
            pass
