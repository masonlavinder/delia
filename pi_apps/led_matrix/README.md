# LED Matrix — Adafruit 128x64 RGB panel on a Pi 3 A+

Drive an Adafruit **128x64 RGB LED Matrix (HUB75, 2mm pitch)** from a
Raspberry Pi 3 A+ using the **Adafruit RGB Matrix Bonnet**. Starter scenes
included: a first-light test, a live weather display, and a GIF animation player.

> Prerequisite: the Pi is set up and you can SSH into it. If not, do
> [`../bootstrap`](../bootstrap/README.md) first.

## Hardware checklist

- [x] Raspberry Pi 3 A+ (Raspberry Pi OS Lite)
- [x] Adafruit RGB Matrix Bonnet (snapped onto the Pi's 40-pin header)
- [x] 128x64 RGB LED matrix panel + its HUB75 ribbon cable
- [x] Separate **5V power supply, 4A minimum** (5A+ gives headroom)

### ⚠️ Power — read this first

- Plug the **5V supply into the Bonnet's screw terminals** (watch polarity: + and −).
  The Bonnet feeds 5V to **both the panel and the Pi** through the header, so with
  a beefy enough supply you may not need to plug the Pi's micro-USB in at all.
- **Use only ONE power source at a time.** Don't power the Pi from its micro-USB
  *and* the Bonnet simultaneously — pick one to avoid back-feeding.
- Connect the panel's **HUB75 ribbon** to the Bonnet's output, and the panel's
  **power leads to the Bonnet's screw terminals** too (per Adafruit's panel guide).
- Start scenes at **low brightness**. Full white on 8,192 LEDs is the peak current draw.

## Step 1 — Attach hardware (Pi powered OFF)

1. Seat the Bonnet firmly on all 40 GPIO pins.
2. Connect the panel's ribbon cable to the Bonnet (note the arrow / input side on the panel).
3. Wire the panel + Bonnet power to your 5V supply as above.

## Step 2 — Install the Adafruit RGB matrix library

SSH into the Pi, then:

```bash
curl https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/main/rgb-matrix.sh >rgb-matrix.sh
sudo bash rgb-matrix.sh
```

The installer will ask a couple of questions:

- **Interface board type** → choose **Adafruit RGB Matrix Bonnet**.
- **Quality vs convenience** → for now choose the simple option that keeps you
  off the soldering iron. It will **disable the onboard sound** (required — the
  audio hardware conflicts with the panel's timing). That's expected.
  - If it mentions a **GPIO4↔GPIO18 solder jumper**: you can skip that today.
    Soldering it later + switching `hardware_mapping` to `'adafruit-hat-pwm'`
    in `panel.py` gives noticeably smoother, flicker-free output.

Let it build, then **reboot** when it asks:

```bash
sudo reboot
```

This installs the `rgbmatrix` Python module system-wide and clones the library
(with fonts + examples) into `~/rpi-rgb-led-matrix`.

## Step 3 — Install Python deps + get this code onto the Pi

```bash
sudo apt install -y git python3-pil python3-requests
git clone <your delia repo URL> ~/delia      # or copy the folder over
cd ~/delia/pi_apps/led_matrix
```

## Step 4 — First light 🎉

```bash
sudo python3 hello.py     # Ctrl-C to stop
```

You should see the panel cycle **red → green → blue → white**. If it does, the
hardware and library are working. (`sudo` is required — driving the GPIO needs root.)

**If the image looks garbled/offset** (some panels vary): edit `panel.py` and try
`options.gpio_slowdown = 3`, or add `options.multiplexing = 1` (values 0–17 exist;
1 is a common fix). See the Troubleshooting section below.

## Step 5 — Weather

```bash
cp config.example.py config.py
nano config.py            # set PI_USER, your LAT/LON, and units
sudo python3 weather.py
```

Uses **Open-Meteo** — free, no API key. Shows the current temp, refreshing every
10 minutes.

## Step 6 — Animations

```bash
# put a .gif in this folder, then:
sudo python3 animation.py mycoolgif.gif
```

Scales any GIF to 128×64 and loops it.

## Files

| File | What it is |
|------|-----------|
| `panel.py` | Shared panel config — all scenes import `build_matrix()` from here. Edit hardware settings in ONE place. |
| `hello.py` | First-light color-cycle test. |
| `weather.py` | Current temperature via Open-Meteo (needs `config.py`). |
| `animation.py` | GIF player. |
| `config.example.py` | Copy to `config.py` and fill in location. |
| `requirements.txt` | Python deps (install via apt — see the file). |

## Run a scene automatically on boot (optional, later)

Once a scene is the one you want always running, make a systemd service so it
starts on boot and restarts if it crashes. Ask and I'll generate the unit file.

## Troubleshooting

| Symptom | Try |
|---|---|
| Flicker / tearing | Solder the GPIO4↔GPIO18 jumper, set `hardware_mapping='adafruit-hat-pwm'`. Or raise `gpio_slowdown`. |
| Garbled / wrong pixels | In `panel.py` try `options.multiplexing = 1` (or 2), and/or `gpio_slowdown = 3`. |
| Random crashes / brownouts | Power problem — bigger 5V supply, and make sure you're not double-powering the Pi. |
| `ModuleNotFoundError: rgbmatrix` | The Adafruit installer (step 2) didn't finish, or you didn't reboot. |
| Colors look dim/washed | Raise `brightness` in the scene (watch current draw). |

Reference: Adafruit "RGB Matrix Bonnet" guide and the underlying
[hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) docs.
