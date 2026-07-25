"""Show the current temperature, refreshed every 10 minutes.

Uses Open-Meteo (https://open-meteo.com) — a free weather API that needs NO
account or API key. Set your location in config.py first (copy config.example.py).

Run:  cd ~/delia/pi_apps/led_matrix && sudo python3 weather.py
Stop: Ctrl-C
"""
import time
import requests
from panel import build_matrix
from rgbmatrix import graphics
import config

# The Adafruit installer clones the library (and its fonts) into your home dir.
FONT_PATH = f"/home/{config.PI_USER}/rpi-rgb-led-matrix/fonts/7x13.bdf"


def fetch_temp():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={config.LAT}&longitude={config.LON}"
        f"&current=temperature_2m&temperature_unit={config.TEMP_UNIT}"
    )
    data = requests.get(url, timeout=10).json()
    return data["current"]["temperature_2m"]


matrix = build_matrix(brightness=50)
canvas = matrix.CreateFrameCanvas()
font = graphics.Font()
font.LoadFont(FONT_PATH)
white = graphics.Color(255, 255, 255)
unit = "F" if config.TEMP_UNIT == "fahrenheit" else "C"

try:
    while True:
        try:
            temp = fetch_temp()
            text = f"{round(temp)}{unit}"
        except Exception as e:
            text = "..."   # network hiccup; just show a placeholder and retry
            print("weather fetch failed:", e)

        canvas.Clear()
        graphics.DrawText(canvas, font, 4, 38, white, text)
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(600)   # refresh every 10 minutes
except KeyboardInterrupt:
    matrix.Clear()
