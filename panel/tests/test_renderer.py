"""Renderer tests against the mock backend — no GPIO, no fonts on disk."""
import pytest
from PIL import Image

from panel.backends.mock import MockBackend
from panel.renderer import Renderer, fit_image, scroll_x
from panel.schema import Direction, Fit, PANEL_CAPABILITIES, Scene


def renderer(assets_dir="/nonexistent"):
    return Renderer(MockBackend(128, 64), PANEL_CAPABILITIES, assets_dir=assets_dir)


def scene(layers, **kw):
    return Scene.model_validate({"name": "s", "layers": layers, **kw})


def test_solid_fills_whole_panel():
    r = renderer()
    r.set_scene(scene([{"type": "solid", "color": [10, 20, 30]}]))
    r.render_frame(0.0)
    img = r.backend.last_frame
    assert img.getpixel((0, 0)) == (10, 20, 30)
    assert img.getpixel((127, 63)) == (10, 20, 30)


def test_text_draws_blocks_in_color():
    r = renderer()
    r.set_scene(scene([
        {"type": "solid", "color": [0, 0, 0]},
        {"type": "text", "content": "A", "color": [255, 0, 0], "x": 0, "y": 13, "font": "7x13"},
    ]))
    r.render_frame(0.0)
    img = r.backend.last_frame
    assert img.getpixel((3, 6)) == (255, 0, 0)    # inside the 7x13 cell at (0..6, 0..12)
    assert img.getpixel((100, 6)) == (0, 0, 0)    # elsewhere is off


def test_layers_composite_back_to_front():
    r = renderer()
    r.set_scene(scene([
        {"type": "solid", "color": [0, 0, 255]},   # back
        {"type": "solid", "color": [255, 0, 0]},   # front overwrites
    ]))
    r.render_frame(0.0)
    assert r.backend.last_frame.getpixel((10, 10)) == (255, 0, 0)


def test_text_align_right():
    r = renderer()
    r.set_scene(scene([
        {"type": "text", "content": "AB", "color": [0, 255, 0], "align": "right", "y": 13, "font": "7x13"},
    ]))
    r.render_frame(0.0)
    img = r.backend.last_frame
    assert img.getpixel((116, 6)) == (0, 255, 0)   # "AB" is 14px wide -> starts at x=114
    assert img.getpixel((113, 6)) == (0, 0, 0)


def test_clock_renders_nonblank():
    r = renderer()
    r.set_scene(scene([
        {"type": "clock", "format": "%H:%M", "color": [255, 255, 255], "x": 0, "y": 20, "font": "10x20"},
    ]))
    r.render_frame(0.0)
    assert any(p == (255, 255, 255) for p in r.backend.last_frame.getdata())


# --- scroll: pure function of elapsed time ---------------------------------

def test_scroll_x_is_pure_and_periodic():
    assert scroll_x(128, 70, 30, Direction.LEFT, 1.0) == scroll_x(128, 70, 30, Direction.LEFT, 1.0)
    assert scroll_x(128, 70, 30, Direction.LEFT, 0.0) == 128
    period = (128 + 70) / 30.0
    assert scroll_x(128, 70, 30, Direction.LEFT, 0.0) == scroll_x(128, 70, 30, Direction.LEFT, period)


def test_scroll_moves_over_time():
    r = renderer()
    r.set_scene(scene([
        {"type": "scroll", "content": "X", "color": [255, 255, 255], "speed_px_s": 30,
         "direction": "left", "y": 13, "font": "7x13"},
    ]))
    r.render_frame(0.0)          # scene applied here; start = 0
    r.render_frame(0.5)
    f1 = list(r.backend.last_frame.getdata())
    r.render_frame(1.5)
    f2 = list(r.backend.last_frame.getdata())
    assert f1 != f2


# --- image + asset safety --------------------------------------------------

def test_image_layer_renders(tmp_path):
    Image.new("RGB", (20, 20), (0, 255, 0)).save(tmp_path / "logo.png")
    r = renderer(assets_dir=str(tmp_path))
    r.set_scene(scene([{"type": "image", "asset_id": "logo", "x": 0, "y": 0, "fit": "none"}]))
    r.render_frame(0.0)
    assert r.backend.last_frame.getpixel((5, 5)) == (0, 255, 0)


def test_load_asset_refuses_escape(tmp_path):
    # defense in depth: even a traversal id (schema would already reject it) is refused
    r = renderer(assets_dir=str(tmp_path))
    with pytest.raises(FileNotFoundError):
        r._load_asset("../../../etc/passwd", Fit.NONE)


def test_fit_contain_and_cover():
    img = Image.new("RGB", (200, 50), (255, 0, 0))
    assert fit_image(img, Fit.CONTAIN, 128, 64).size[0] <= 128
    assert fit_image(img, Fit.COVER, 128, 64).size == (128, 64)
