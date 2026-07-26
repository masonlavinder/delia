"""Play an animated GIF on the panel, scaled to fill 128x64, looping forever.
Ships with cool.gif (a purple plasma). Drop your own .gif files in this folder.

Run:  display gif              # plays cool.gif
      display gif mine.gif     # plays scenes/party/mine.gif
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import time
from PIL import Image
from core.panel import build_matrix

HERE = os.path.dirname(__file__)
name = sys.argv[1] if len(sys.argv) > 1 else "cool.gif"
path = name if os.path.isfile(name) else os.path.join(HERE, name)

if not os.path.isfile(path):
    gifs = sorted(f for f in os.listdir(HERE) if f.lower().endswith(".gif"))
    print(f"No GIF named '{name}'.")
    print("Available in scenes/party/:", ", ".join(gifs) if gifs else "(none yet)")
    print("Usage: display gif <name.gif>")
    sys.exit(1)

matrix = build_matrix(brightness=60)
gif = Image.open(path)

frames = []
try:
    while True:
        frames.append(gif.copy().convert("RGB").resize((matrix.width, matrix.height)))
        gif.seek(gif.tell() + 1)
except EOFError:
    pass
print(f"Loaded {len(frames)} frames from {os.path.basename(path)}")

try:
    while True:
        for frame in frames:
            matrix.SetImage(frame)
            time.sleep(0.06)   # ~16 fps
except KeyboardInterrupt:
    matrix.Clear()
