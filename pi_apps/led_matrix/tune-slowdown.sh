#!/usr/bin/env bash
# Sweep --led-slowdown-gpio and pick the lowest value that renders cleanly.
#
# Lower slowdown = higher refresh rate. Too low = flicker, tearing, garbage
# pixels. This runs each value for a few seconds, captures the measured
# refresh rate, and asks you whether the panel looked clean.
#
#   ./tune-slowdown.sh            # sweep 0..4
#   ./tune-slowdown.sh 0 1 2      # sweep specific values
#
set -uo pipefail

DEMO="${DEMO:-$HOME/rpi-rgb-led-matrix/examples-api-use/demo}"
SECONDS_PER_STEP="${SECONDS_PER_STEP:-8}"

BASE=(
  --led-rows=64
  --led-cols=128
  --led-chain=1
  --led-gpio-mapping=adafruit-hat
  --led-brightness=40
  --led-show-refresh
)

VALUES=("$@")
[[ ${#VALUES[@]} -eq 0 ]] && VALUES=(0 1 2 3 4)

if [[ ! -x "$DEMO" ]]; then
  echo "Can't find the demo binary at: $DEMO" >&2
  echo "Build it first:  cd ~/rpi-rgb-led-matrix && make LTO_FLAGS= -j2" >&2
  exit 1
fi

# Ask for sudo once so the password prompt doesn't land mid-test.
sudo -v || exit 1

declare -A REFRESH
declare -A CLEAN

cleanup() { sudo pkill -f "$DEMO" 2>/dev/null; stty sane 2>/dev/null; }
trap cleanup EXIT INT

echo
echo "Sweeping ${#VALUES[@]} values, ${SECONDS_PER_STEP}s each."
echo "Watch the PANEL, not the terminal. Look for flicker, tearing, or"
echo "stray pixels. Ignore the first half-second of startup noise."
echo

for s in "${VALUES[@]}"; do
  echo "──────────────────────────────────────────"
  echo "  slowdown = $s"
  echo "──────────────────────────────────────────"

  out=$(sudo timeout "$SECONDS_PER_STEP" "$DEMO" -D5 "${BASE[@]}" \
        --led-slowdown-gpio="$s" 2>&1)

  # --led-show-refresh emits lines containing a Hz figure; take the last one.
  hz=$(printf '%s\n' "$out" | grep -oE '[0-9]+\.[0-9]+ Hz' | tail -1)
  REFRESH[$s]="${hz:-unknown}"
  echo "  measured refresh: ${REFRESH[$s]}"

  read -rp "  Did it look clean? [y/N] " ans </dev/tty
  case "$ans" in
    [Yy]*) CLEAN[$s]=yes ;;
    *)     CLEAN[$s]=no  ;;
  esac
  echo
done

echo "=========================================="
echo " RESULTS"
echo "=========================================="
printf "  %-10s %-14s %s\n" "slowdown" "refresh" "clean"
best=""
for s in "${VALUES[@]}"; do
  printf "  %-10s %-14s %s\n" "$s" "${REFRESH[$s]}" "${CLEAN[$s]}"
  [[ -z "$best" && "${CLEAN[$s]}" == "yes" ]] && best="$s"
done
echo

if [[ -n "$best" ]]; then
  echo "Use --led-slowdown-gpio=$best  (lowest clean value)"
  echo
  echo "Full command:"
  echo "  sudo $DEMO -D5 \\"
  echo "    --led-rows=64 --led-cols=128 --led-chain=1 \\"
  echo "    --led-gpio-mapping=adafruit-hat \\"
  echo "    --led-slowdown-gpio=$best --led-brightness=40"
else
  echo "Nothing rendered cleanly. Things to try:"
  echo "  - Higher values:  ./tune-slowdown.sh 5 6 7 8"
  echo "  - Check the power supply (needs 5V 4A for this panel)"
  echo "  - Reseat the bonnet on the 40-pin header"
  echo "  - Confirm the Pi is not overclocked (raspi-config)"
fi
