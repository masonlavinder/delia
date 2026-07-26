"""Daemon round-trip tests over a real socket in a temp dir, mock backend."""
import json
import os
import signal
import socket
import threading
import time

import pytest

from panel.client import PanelClient
from panel.daemon import Daemon


def _wait_for(path, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if os.path.exists(path):
            return True
        time.sleep(0.02)
    return False


def _readline(sock):
    buf = bytearray()
    while b"\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf.extend(chunk)
    line, _, _ = bytes(buf).partition(b"\n")
    return json.loads(line)


@pytest.fixture
def daemon(tmp_path, monkeypatch):
    monkeypatch.setenv("PANEL_BACKEND", "mock")
    sock = str(tmp_path / "panel.sock")
    d = Daemon(sock_path=sock)
    t = threading.Thread(target=d.run, daemon=True)
    t.start()
    assert _wait_for(sock), "daemon did not create socket"
    yield sock
    d._stop = True
    t.join(timeout=3)


def test_roundtrip_set_scene_and_state(daemon):
    c = PanelClient(sock_path=daemon)
    r = c.set_scene({"name": "hi", "layers": [{"type": "solid", "color": [1, 2, 3]}]})
    assert r["ok"] is True and r["scene"] == "hi"
    st = c.get_state()
    assert st["ok"] is True and st["scene"] == "hi" and "fps" in st


def test_capabilities(daemon):
    r = PanelClient(sock_path=daemon).capabilities()
    assert r["ok"] and r["capabilities"]["width"] == 128 and r["capabilities"]["height"] == 64


def test_clear_and_brightness(daemon):
    c = PanelClient(sock_path=daemon)
    assert c.set_brightness(60)["ok"] is True
    assert c.set_brightness(0)["ok"] is False        # out of range
    assert c.clear()["ok"] is True


def test_unknown_command(daemon):
    r = PanelClient(sock_path=daemon).request({"command": "nope"})
    assert r["ok"] is False and "unknown" in r["error"]


def test_malformed_json_structured_error(daemon):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(daemon)
    s.sendall(b"{not valid json\n")
    resp = _readline(s)
    s.close()
    assert resp["ok"] is False and resp["error"] == "invalid json"


def test_schema_validation_error_detail(daemon):
    r = PanelClient(sock_path=daemon).set_scene(
        {"name": "BAD NAME", "layers": [{"type": "solid", "color": [0, 0, 0]}]})
    assert r["ok"] is False and r["error"] == "validation" and "detail" in r


def test_capability_error_out_of_bounds(daemon):
    r = PanelClient(sock_path=daemon).set_scene(
        {"name": "x", "layers": [{"type": "text", "content": "hi", "color": [0, 0, 0], "x": 500, "y": 0}]})
    assert r["ok"] is False and r["error"] == "capability"


def test_asset_traversal_rejected_by_schema(daemon):
    # a scene with asset_id "../../etc/passwd" must be refused, nothing read from disk
    r = PanelClient(sock_path=daemon).set_scene(
        {"name": "x", "layers": [{"type": "image", "asset_id": "../../etc/passwd"}]})
    assert r["ok"] is False and r["error"] == "validation"


def test_oversized_line_rejected_without_parsing(daemon):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(daemon)
    payload = b'{"command":"set_scene","scene":"' + b"A" * 70000 + b'"}\n'
    s.sendall(payload)
    resp = _readline(s)
    s.close()
    assert resp["ok"] is False and "too long" in resp["error"]


def test_sigterm_clean_shutdown(tmp_path, monkeypatch):
    monkeypatch.setenv("PANEL_BACKEND", "mock")
    sock = str(tmp_path / "p.sock")
    d = Daemon(sock_path=sock)
    t = threading.Thread(target=d.run, daemon=True)
    t.start()
    assert _wait_for(sock)
    d._on_signal(signal.SIGTERM, None)     # simulate SIGTERM
    t.join(timeout=3)
    assert not os.path.exists(sock)        # socket removed on clean shutdown
