#!/usr/bin/env bash
# Launch an LED-matrix scene (needs sudo for GPIO access). Sets PYTHONPATH so
# scenes can import the shared `core` package and `config`.
#
#   ./run.sh everyday/weather          # runs scenes/everyday/weather.py
#   ./run.sh everyday/clock
#   ./run.sh party/gif cool.gif        # extra args pass through to the scene
#   ./run.sh scratch/hello
#   ./run.sh                           # lists available scenes
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

list_scenes() {
  (cd "$ROOT" && find scenes -name '*.py' | sed 's|scenes/||; s|\.py$||' | sort | sed 's/^/  /')
}

if [[ $# -eq 0 ]]; then
  echo "usage: ./run.sh <scene> [args...]"
  echo "available scenes:"; list_scenes
  exit 0
fi

scene="$1"
[[ "$scene" == *.py ]] || scene="$scene.py"
[[ -f "$ROOT/$scene" ]] || scene="scenes/$scene"

if [[ ! -f "$ROOT/$scene" ]]; then
  echo "No scene at $ROOT/$scene" >&2
  echo "available scenes:" >&2; list_scenes >&2
  exit 1
fi

exec sudo env "PYTHONPATH=$ROOT" python3 "$ROOT/$scene" "${@:2}"
