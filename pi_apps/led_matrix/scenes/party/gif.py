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
delays = []
try:
    while True:
        frames.append(gif.copy().convert("RGB").resize((matrix.width, matrix.height)))
        delays.append(gif.info.get("duration", 60) / 1000.0)   # ms -> s, per frame
        gif.seek(gif.tell() + 1)
except EOFError:
    pass
print(f"Loaded {len(frames)} frames from {os.path.basename(path)}")

canvas = matrix.CreateFrameCanvas()   # offscreen buffer -> no tearing
try:
    while True:
        for frame, delay in zip(frames, delays):
            canvas.SetImage(frame)
            canvas = matrix.SwapOnVSync(canvas)
            time.sleep(max(delay, 0.02))
except KeyboardInterrupt:
    matrix.Clear()
