"""Panel renderer daemon — runs as root because GPIO requires it, so it is the
trust boundary and stays small and boring.

Protocol: newline-delimited JSON over an AF_UNIX stream socket, one request and
one response per line. No shelling out, no dynamic evaluation, no unsafe
deserialization (JSON only), and no filesystem path ever derived from caller
input. Every scene is revalidated here through validate_scene() — that re-check
is the security boundary, not redundant.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import socket
import sys
import threading

from pydantic import ValidationError

from .backends import get_backend
from .renderer import Renderer
from .schema import PANEL_CAPABILITIES, SceneCapabilityError, validate_scene

SOCK_PATH = os.environ.get("PANEL_SOCK", "/run/panel/panel.sock")
MAX_LINE = 64 * 1024
CAPS = PANEL_CAPABILITIES

log = logging.getLogger("panel.daemon")


class Daemon:
    def __init__(self, sock_path: str = SOCK_PATH):
        self.sock_path = sock_path
        self.backend = get_backend()              # PANEL_BACKEND selects (rgbmatrix on Pi)
        self.renderer = Renderer(self.backend, CAPS)
        self._srv: socket.socket | None = None
        self._stop = False

    # -- command dispatch ---------------------------------------------------
    def _handle(self, req: dict) -> dict:
        cmd = req.get("command")

        if cmd == "set_scene":
            payload = req.get("scene")
            if not isinstance(payload, dict):
                return {"ok": False, "error": "set_scene requires object field 'scene'"}
            try:
                scene = validate_scene(payload, CAPS)          # the trust boundary
            except ValidationError as exc:
                log.warning("reject set_scene (schema): %s", exc.errors())
                return {"ok": False, "error": "validation", "detail": json.loads(exc.json())}
            except SceneCapabilityError as exc:
                log.warning("reject set_scene (capability): %s", exc.errors)
                return {"ok": False, "error": "capability", "detail": exc.errors}
            self.renderer.set_scene(scene)
            log.info("accepted scene name=%s layers=%d source=socket", scene.name, len(scene.layers))
            return {"ok": True, "scene": scene.name}

        if cmd == "get_state":
            return {"ok": True, **self.renderer.state()}

        if cmd == "clear":
            self.renderer.clear()
            log.info("clear")
            return {"ok": True}

        if cmd == "set_brightness":
            b = req.get("brightness")
            if not isinstance(b, int) or isinstance(b, bool) or not (1 <= b <= 100):
                return {"ok": False, "error": "brightness must be an integer 1..100"}
            self.renderer.set_brightness(b)
            log.info("brightness=%d", b)
            return {"ok": True}

        if cmd == "capabilities":
            return {"ok": True, "capabilities": CAPS.model_dump()}

        return {"ok": False, "error": f"unknown command: {cmd!r}"}

    def _process_line(self, line: bytes) -> dict:
        line = line.strip()
        if not line:
            return {"ok": False, "error": "empty request"}
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": "invalid json", "detail": str(exc)}
        if not isinstance(req, dict):
            return {"ok": False, "error": "request must be a json object"}
        try:
            return self._handle(req)
        except Exception:                       # never leak a traceback to the caller
            log.exception("handler error")
            return {"ok": False, "error": "internal error"}

    @staticmethod
    def _send(conn: socket.socket, obj: dict) -> None:
        conn.sendall((json.dumps(obj) + "\n").encode())

    def _serve_conn(self, conn: socket.socket) -> None:
        buf = bytearray()
        with conn:
            while not self._stop:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                buf.extend(chunk)
                if len(buf) > MAX_LINE and b"\n" not in buf:      # reject BEFORE parsing
                    self._send(conn, {"ok": False, "error": "line too long"})
                    return
                while b"\n" in buf:
                    line, _, rest = buf.partition(b"\n")
                    buf = bytearray(rest)
                    if len(line) > MAX_LINE:
                        self._send(conn, {"ok": False, "error": "line too long"})
                        continue
                    self._send(conn, self._process_line(bytes(line)))

    # -- lifecycle ----------------------------------------------------------
    def run(self) -> None:
        self.renderer.start()

        sock_dir = os.path.dirname(self.sock_path)
        if sock_dir:
            os.makedirs(sock_dir, exist_ok=True)   # systemd RuntimeDirectory usually already did
        try:
            os.unlink(self.sock_path)
        except FileNotFoundError:
            pass

        self._srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._srv.bind(self.sock_path)
        self._set_socket_perms()
        self._srv.listen(8)
        self._srv.settimeout(0.5)

        # signal handlers only install in the main thread (tests run run() in a thread)
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGTERM, self._on_signal)
            signal.signal(signal.SIGINT, self._on_signal)

        log.info("listening on %s", self.sock_path)
        while not self._stop:
            try:
                conn, _ = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                self._serve_conn(conn)          # one connection at a time (serialized)
            except Exception:
                log.exception("connection error")
        self._shutdown()

    def _set_socket_perms(self) -> None:
        try:
            os.chmod(self.sock_path, 0o660)
            import grp
            gid = grp.getgrnam("panel").gr_gid
            os.chown(self.sock_path, -1, gid)     # root:panel so the API user can reach it
        except (KeyError, PermissionError, OSError):
            pass

    def _on_signal(self, signum, _frame) -> None:
        log.info("signal %s -> shutting down", signum)
        self._stop = True

    def _shutdown(self) -> None:
        try:
            self.renderer.stop()                  # blanks the panel + closes the matrix
        except Exception:
            log.exception("renderer stop failed")
        try:
            if self._srv is not None:
                self._srv.close()
        except Exception:
            pass
        try:
            os.unlink(self.sock_path)
        except FileNotFoundError:
            pass
        log.info("stopped")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    Daemon().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
