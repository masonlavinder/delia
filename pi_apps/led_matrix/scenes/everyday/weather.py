"""Current temperature from Open-Meteo (free, no API key). Refreshes every 10 min.
Set your location in config.py (copy config.example.py first).

Run:  ./run.sh everyday/weather        (Ctrl-C to stop)
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import time
import requests
from rgbmatrix import graphics
from core.panel import build_matrix, load_font
import config


def fetch_temp():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={config.LAT}&longitude={config.LON}"
        f"&current=temperature_2m&temperature_unit={config.TEMP_UNIT}"
    )
    return requests.get(url, timeout=10).json()["current"]["temperature_2m"]


matrix = build_matrix(brightness=50)
canvas = matrix.CreateFrameCanvas()
font = load_font("10x20.bdf")
white = graphics.Color(255, 255, 255)
unit = "F" if config.TEMP_UNIT == "fahrenheit" else "C"

try:
    while True:
        try:
            text = f"{round(fetch_temp())}{unit}"
        except Exception as e:
            text = "..."
            print("weather fetch failed:", e)
        canvas.Clear()
        graphics.DrawText(canvas, font, 8, 42, white, text)
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(600)
except KeyboardInterrupt:
    matrix.Clear()
