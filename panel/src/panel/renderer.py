"""Renderer: a render loop that composites a Scene's layers onto the backend.

- Fixed ~60 FPS timestep; on a slow frame it skips the sleep rather than
  accumulating lag. Animated layers derive state from elapsed wall time, so a
  dropped frame never causes drift.
- Layers composite back-to-front over a black-cleared canvas (backgrounds are
  OFF unless a solid layer paints them).
- Scene switches are atomic: the new scene is fully prepared (fonts + images
  loaded once), then swapped in at a frame boundary.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any

from PIL import Image

from .backends.base import LoadedFont, MatrixBackend
from .schema import Align, Capabilities, Direction, Fit, Scene

DEFAULT_ASSETS_DIR = "/home/mlavinder/delia/panel/assets"
_UNSET = object()


# --- pure helpers (unit-testable without a backend) ------------------------

def scroll_x(width: int, text_px: int, speed_px_s: int, direction: Direction,
             elapsed_s: float) -> int:
    """Scroll head x as a pure function of elapsed time. Loops every
    (width + text_px) pixels so it never accumulates state."""
    total = width + text_px
    dist = (speed_px_s * elapsed_s) % total
    if direction == Direction.LEFT:
        return width - int(dist)
    return -text_px + int(dist)


def fit_image(img: Image.Image, fit: Fit, W: int, H: int) -> Image.Image:
    if fit == Fit.NONE:
        return img
    if fit == Fit.CONTAIN:
        im = img.copy()
        im.thumbnail((W, H))
        return im
    ratio = max(W / img.width, H / img.height)          # cover
    nw, nh = max(1, round(img.width * ratio)), max(1, round(img.height * ratio))
    im = img.resize((nw, nh))
    left, top = (nw - W) // 2, (nh - H) // 2
    return im.crop((left, top, left + W, top + H))


# --- prepared scene --------------------------------------------------------

@dataclass
class _Item:
    layer: Any
    font: LoadedFont | None
    image: Image.Image | None


@dataclass
class _Prepared:
    scene: Scene
    items: list[_Item]


# --- per-layer render functions --------------------------------------------

def _r_solid(c, item, elapsed, caps):
    c.fill(item.layer.color.as_tuple())


def _r_text(c, item, elapsed, caps):
    L = item.layer
    tw = len(L.content) * item.font.char_w
    x = L.x
    if L.align == Align.CENTER:
        x = (caps.width - tw) // 2
    elif L.align == Align.RIGHT:
        x = caps.width - tw
    c.draw_text(item.font, x, L.y, L.color.as_tuple(), L.content)


def _r_scroll(c, item, elapsed, caps):
    L = item.layer
    tw = len(L.content) * item.font.char_w
    x = scroll_x(caps.width, tw, L.speed_px_s, L.direction, elapsed)
    c.draw_text(item.font, x, L.y, L.color.as_tuple(), L.content)


def _r_clock(c, item, elapsed, caps):
    L = item.layer
    c.draw_text(item.font, L.x, L.y, L.color.as_tuple(),
                time.strftime(L.format, time.localtime()))


def _r_image(c, item, elapsed, caps):
    if item.image is not None:
        c.set_image(item.image, item.layer.x, item.layer.y)


_RENDERERS = {
    "solid": _r_solid, "text": _r_text, "scroll": _r_scroll,
    "clock": _r_clock, "image": _r_image,
}


# --- renderer --------------------------------------------------------------

class Renderer:
    def __init__(self, backend: MatrixBackend, caps: Capabilities,
                 assets_dir: str | None = None):
        self.backend = backend
        self.caps = caps
        self.assets_dir = assets_dir or os.environ.get("PANEL_ASSETS_DIR", DEFAULT_ASSETS_DIR)
        self._lock = threading.Lock()
        self._active: _Prepared | None = None
        self._pending: Any = _UNSET          # _UNSET=no change, None=clear, _Prepared=set
        self._scene_name: str | None = None  # reported state (set synchronously, not render-timed)
        self._active_start = 0.0
        self._canvas = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._start_mono: float | None = None
        self._fps = 0.0

    # -- asset resolution (security boundary; asset_id is regex-checked already) --
    def _load_asset(self, asset_id: str, fit: Fit) -> Image.Image:
        base = os.path.realpath(self.assets_dir)
        for ext in (".png", ".gif", ".jpg", ".jpeg", ".bmp"):
            path = os.path.realpath(os.path.join(base, asset_id + ext))
            if not (path == base or path.startswith(base + os.sep)):
                continue  # escaped the asset dir -> refuse
            if os.path.isfile(path):
                return fit_image(Image.open(path).convert("RGB"), fit,
                                 self.caps.width, self.caps.height)
        raise FileNotFoundError(f"asset not found: {asset_id}")

    def prepare(self, scene: Scene) -> _Prepared:
        items = []
        for layer in scene.layers:
            font = self.backend.load_font(layer.font) if hasattr(layer, "font") else None
            image = self._load_asset(layer.asset_id, layer.fit) if layer.type == "image" else None
            items.append(_Item(layer=layer, font=font, image=image))
        return _Prepared(scene=scene, items=items)

    # -- control (thread-safe) --
    def set_scene(self, scene: Scene) -> None:
        prepared = self.prepare(scene)   # build fully BEFORE taking the lock
        with self._lock:
            self._pending = prepared
            self._scene_name = scene.name

    def clear(self) -> None:
        with self._lock:
            self._pending = None
            self._scene_name = None

    def set_brightness(self, pct: int) -> None:
        self.backend.set_brightness(pct)

    def state(self) -> dict:
        return {
            "scene": self._scene_name,
            "uptime_s": round(time.monotonic() - self._start_mono, 1) if self._start_mono else 0.0,
            "fps": round(self._fps, 1),
        }

    # -- frame + loop --
    def _apply_pending(self, now: float) -> None:
        with self._lock:
            if self._pending is _UNSET:
                return
            self._active = self._pending
            self._pending = _UNSET
            self._active_start = now
        if self._active is not None and self._active.scene.brightness is not None:
            self.backend.set_brightness(self._active.scene.brightness)

    def render_frame(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self._apply_pending(now)
        if self._canvas is None:
            self._canvas = self.backend.create_canvas()
        canvas = self._canvas
        canvas.fill((0, 0, 0))
        active = self._active
        if active is not None:
            elapsed = now - self._active_start
            for item in active.items:
                _RENDERERS[item.layer.type](canvas, item, elapsed, self.caps)
        self._canvas = self.backend.swap(canvas)

    def _loop(self) -> None:
        target = 1.0 / 60.0
        frames, window_start = 0, time.monotonic()
        while self._running:
            frame_start = time.monotonic()
            self.render_frame(frame_start)
            frames += 1
            if frame_start - window_start >= 1.0:
                self._fps = frames / (frame_start - window_start)
                frames, window_start = 0, frame_start
            slack = target - (time.monotonic() - frame_start)
            if slack > 0:
                time.sleep(slack)   # behind? skip sleep, don't accumulate lag

    def start(self) -> None:
        self._running = True
        self._start_mono = time.monotonic()
        self._thread = threading.Thread(target=self._loop, name="panel-renderer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self.backend.close()
