"""Play an animated GIF on the panel, scaled to fill 128x64, looping forever.
Drop .gif files into this folder (scenes/party/) and pass the filename.

Run:  ./run.sh party/gif mygif.gif        (Ctrl-C to stop)
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import time
from PIL import Image
from core.panel import build_matrix

name = sys.argv[1] if len(sys.argv) > 1 else "sample.gif"
# accept an absolute/relative path, else look next to this scene
path = name if os.path.isfile(name) else os.path.join(os.path.dirname(__file__), name)

matrix = build_matrix(brightness=50)
gif = Image.open(path)

frames = []
try:
    while True:
        frames.append(gif.copy().convert("RGB").resize((matrix.width, matrix.height)))
        gif.seek(gif.tell() + 1)
except EOFError:
    pass
print(f"Loaded {len(frames)} frames from {path}")

try:
    while True:
        for frame in frames:
            matrix.SetImage(frame)
            time.sleep(0.1)   # ~10 fps; tune to taste
except KeyboardInterrupt:
    matrix.Clear()
