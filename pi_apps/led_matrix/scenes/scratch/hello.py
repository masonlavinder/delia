"""First-light test: cycle the whole panel red -> green -> blue -> white.
The quickest "is the panel working?" check.

Run:  ./run.sh scratch/hello        (Ctrl-C to stop)
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import time
from core.panel import build_matrix

matrix = build_matrix(brightness=40)
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]

try:
    while True:
        for r, g, b in colors:
            matrix.Fill(r, g, b)
            time.sleep(1)
except KeyboardInterrupt:
    matrix.Clear()
