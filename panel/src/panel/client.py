"""Thin synchronous client for the daemon: connect, send one request, read one
response, close. Also a CLI so the daemon can be exercised without the web app:

    python -m panel.client set-scene scene.json
    python -m panel.client get-state
    python -m panel.client clear
    python -m panel.client brightness 60
    python -m panel.client capabilities
"""
from __future__ import annotations

import json
import os
import socket
import sys

SOCK_PATH = os.environ.get("PANEL_SOCK", "/run/panel/panel.sock")
_MAX_RESP = 1 << 20   # 1 MiB response cap


class PanelClient:
    def __init__(self, sock_path: str = SOCK_PATH, timeout: float = 5.0):
        self.sock_path = sock_path
        self.timeout = timeout

    def request(self, obj: dict) -> dict:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        try:
            s.connect(self.sock_path)
            s.sendall((json.dumps(obj) + "\n").encode())
            buf = bytearray()
            while b"\n" not in buf and len(buf) < _MAX_RESP:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
            line, _, _ = bytes(buf).partition(b"\n")
            return json.loads(line) if line else {"ok": False, "error": "no response"}
        finally:
            s.close()

    def set_scene(self, scene: dict) -> dict:
        return self.request({"command": "set_scene", "scene": scene})

    def get_state(self) -> dict:
        return self.request({"command": "get_state"})

    def clear(self) -> dict:
        return self.request({"command": "clear"})

    def set_brightness(self, brightness: int) -> dict:
        return self.request({"command": "set_brightness", "brightness": brightness})

    def capabilities(self) -> dict:
        return self.request({"command": "capabilities"})


def _cli(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    client = PanelClient()
    usage = ("usage: python -m panel.client "
             "{set-scene FILE | get-state | clear | brightness N | capabilities}")
    if not argv:
        print(usage, file=sys.stderr)
        return 2

    cmd = argv[0]
    try:
        if cmd == "set-scene":
            with open(argv[1], encoding="utf-8") as fh:
                scene = json.load(fh)      # operator-supplied file path (not caller input)
            result = client.set_scene(scene)
        elif cmd == "get-state":
            result = client.get_state()
        elif cmd == "clear":
            result = client.clear()
        elif cmd == "brightness":
            result = client.set_brightness(int(argv[1]))
        elif cmd == "capabilities":
            result = client.capabilities()
        else:
            print(f"unknown command: {cmd}\n{usage}", file=sys.stderr)
            return 2
    except (IndexError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}\n{usage}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
