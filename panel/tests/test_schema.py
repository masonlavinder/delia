"""Schema tests — run against no hardware. `PANEL_BACKEND=mock pytest`."""
import pytest
from pydantic import ValidationError

from panel.schema import (
    ALL_LAYER_TYPES,
    Capabilities,
    Color,
    FontName,
    ImageLayer,
    PANEL_CAPABILITIES,
    Scene,
    SceneCapabilityError,
    validate_scene,
)

VALID = {
    "name": "hello",
    "layers": [
        {"type": "solid", "color": [0, 0, 0]},
        {"type": "text", "content": "hi", "color": [255, 0, 255], "x": 2, "y": 20},
    ],
}


# --- color -----------------------------------------------------------------

def test_color_accepts_list_and_dict():
    assert Color.model_validate([255, 0, 128]).as_tuple() == (255, 0, 128)
    assert Color.model_validate({"r": 1, "g": 2, "b": 3}).as_tuple() == (1, 2, 3)


@pytest.mark.parametrize("bad", [[256, 0, 0], [-1, 0, 0], [0, 0], [0, 0, 0, 0]])
def test_color_bounds_and_shape(bad):
    with pytest.raises(ValidationError):
        Color.model_validate(bad)


def test_color_extra_forbidden():
    with pytest.raises(ValidationError):
        Color.model_validate({"r": 1, "g": 2, "b": 3, "a": 4})


# --- scene / layers --------------------------------------------------------

def test_valid_scene_roundtrips():
    s = Scene.model_validate(VALID)
    assert s.name == "hello" and len(s.layers) == 2 and s.layers[1].type == "text"
    Scene.model_validate(s.model_dump())  # dumped form re-validates


def test_extra_field_forbidden():
    with pytest.raises(ValidationError):
        Scene.model_validate({**VALID, "wat": 1})


def test_layer_extra_forbidden():
    with pytest.raises(ValidationError):
        Scene.model_validate({"name": "x", "layers": [{"type": "solid", "color": [0, 0, 0], "nope": 1}]})


def test_unknown_layer_type_rejected():
    with pytest.raises(ValidationError):
        Scene.model_validate({"name": "x", "layers": [{"type": "wormhole", "color": [0, 0, 0]}]})


def test_layers_count_bounds():
    with pytest.raises(ValidationError):
        Scene.model_validate({"name": "x", "layers": []})
    nine = [{"type": "solid", "color": [0, 0, 0]}] * 9
    with pytest.raises(ValidationError):
        Scene.model_validate({"name": "x", "layers": nine})


@pytest.mark.parametrize("name", ["Bad Name!", "a" * 65, "", "-lead", "UP"])
def test_name_slug_rejected(name):
    with pytest.raises(ValidationError):
        Scene.model_validate({**VALID, "name": name})


def test_duration_brightness_bounds():
    Scene.model_validate({**VALID, "duration_s": 1, "brightness": 100})
    for bad in ({"duration_s": 0}, {"duration_s": 86401}, {"brightness": 0}, {"brightness": 101}):
        with pytest.raises(ValidationError):
            Scene.model_validate({**VALID, **bad})


def test_text_content_maxlen():
    with pytest.raises(ValidationError):
        Scene.model_validate({"name": "x", "layers": [{"type": "text", "content": "a" * 257, "color": [1, 1, 1]}]})


@pytest.mark.parametrize("speed", [0, 121, -5])
def test_scroll_speed_bounds(speed):
    with pytest.raises(ValidationError):
        Scene.model_validate({"name": "x", "layers": [{"type": "scroll", "content": "hi", "color": [1, 1, 1], "speed_px_s": speed}]})


def test_scroll_speed_ok():
    Scene.model_validate({"name": "x", "layers": [{"type": "scroll", "content": "hi", "color": [1, 1, 1], "speed_px_s": 120}]})


# --- asset_id path safety --------------------------------------------------

@pytest.mark.parametrize("bad_id", [
    "../../etc/passwd", "..", "/etc/passwd", "a/b", "foo/../bar",
    "file:///etc/passwd", "http://evil/x.png", "a\x00b", "UPPER",
    "-lead", "with space", "a" * 65, "",
])
def test_asset_id_rejects_dangerous(bad_id):
    with pytest.raises(ValidationError):
        ImageLayer.model_validate({"type": "image", "asset_id": bad_id})


@pytest.mark.parametrize("ok_id", ["a", "logo", "cool_gif-1", "0abc", "a" * 64])
def test_asset_id_accepts_safe(ok_id):
    ImageLayer.model_validate({"type": "image", "asset_id": ok_id})


# --- capability validation (the security boundary) -------------------------

def test_validate_scene_ok():
    assert validate_scene(VALID, PANEL_CAPABILITIES).name == "hello"


def test_validate_scene_coord_out_of_bounds():
    bad = {"name": "x", "layers": [{"type": "text", "content": "hi", "color": [1, 1, 1], "x": 500, "y": 10}]}
    with pytest.raises(SceneCapabilityError):
        validate_scene(bad, PANEL_CAPABILITIES)


def test_validate_scene_unsupported_type():
    caps = Capabilities(width=128, height=64, color_depth=24,
                        supported_layer_types=["solid"], supported_fonts=list(FontName))
    bad = {"name": "x", "layers": [{"type": "text", "content": "hi", "color": [1, 1, 1]}]}
    with pytest.raises(SceneCapabilityError):
        validate_scene(bad, caps)


def test_validate_scene_unsupported_font():
    caps = Capabilities(width=128, height=64, color_depth=24,
                        supported_layer_types=list(ALL_LAYER_TYPES),
                        supported_fonts=[FontName.F4x6])
    bad = {"name": "x", "layers": [{"type": "text", "content": "hi", "color": [1, 1, 1], "font": "7x13"}]}
    with pytest.raises(SceneCapabilityError):
        validate_scene(bad, caps)


def test_json_schema_exports(tmp_path):
    from panel.schema import export_schema
    out = export_schema(str(tmp_path / "scene.schema.json"))
    import json
    data = json.loads(open(out).read())
    assert "properties" in data and "layers" in data["properties"]
