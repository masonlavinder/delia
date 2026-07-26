"""Backend selection. Defaults to `mock` so nothing accidentally grabs the GPIO
during a test run; set PANEL_BACKEND=rgbmatrix on the device.
"""
from __future__ import annotations

import os

from .base import Canvas, LoadedFont, MatrixBackend, font_dimensions

__all__ = ["Canvas", "LoadedFont", "MatrixBackend", "font_dimensions", "get_backend"]


def get_backend(**kwargs) -> MatrixBackend:
    name = os.environ.get("PANEL_BACKEND", "mock").lower()
    if name == "rgbmatrix":
        from .rgbmatrix import RGBMatrixBackend
        return RGBMatrixBackend()
    if name == "mock":
        from .mock import MockBackend
        return MockBackend(**kwargs)
    raise ValueError(f"unknown PANEL_BACKEND={name!r} (use 'mock' or 'rgbmatrix')")
