"""panel — declarative scene schema + renderer daemon for an LED matrix.

The schema (`panel.schema`) is the contract everything else hangs off, and it
imports without `rgbmatrix` so it runs on a dev laptop and in CI.
"""

__version__ = "0.1.0"
