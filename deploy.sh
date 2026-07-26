#!/usr/bin/env bash
#
# deploy.sh — push delia to the Pi.
#
#   ./deploy.sh            everything: build client, push all, restart both services
#   ./deploy.sh client     build the React client and push dist/  (no restart needed)
#   ./deploy.sh api        push web_app/server/ and restart panel-api
#   ./deploy.sh engine     push matrix/ and restart panel-renderer
#   ./deploy.sh units      install the systemd units into /etc and daemon-reload
#   ./deploy.sh restart    restart both services
#   ./deploy.sh status     systemctl status for both
#   ./deploy.sh logs       follow both journals (Ctrl-C to stop)
#
#   -n / --dry-run         show what rsync would do, change nothing
#
# The client is built HERE, never on the Pi (512 MB, no Node). `sudo` on the Pi
# needs a password, so restarts use `ssh -t` and will prompt.
#
# Override the target:  PI_HOST=user@host  PI_DIR=delia  ./deploy.sh
set -euo pipefail

PI_HOST="${PI_HOST:-mlavinder@delia-pi.local}"
PI_DIR="${PI_DIR:-delia}" # relative to $HOME on the Pi
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Excluded paths are also protected from --delete on the receiver, so the Pi's
# own .venv survives a sync.
EXCLUDES=(
  --exclude .venv
  --exclude __pycache__
  --exclude node_modules
  --exclude .pytest_cache
  --exclude '*.egg-info'
  --exclude .git
)

RSYNC=(rsync -az --human-readable)
DRY_RUN=""

say() { printf '\033[1;35m==>\033[0m %s\n' "$*"; }

# The comment block at the top of this file is the usage text.
usage() {
  awk 'NR > 1 && /^#/ { sub(/^#/, ""); sub(/^ /, ""); print; next }
       NR > 1         { exit }' "${BASH_SOURCE[0]}"
}

# ------------------------------------------------------------------ actions

# rsync creates only the LAST component of a destination path, so a nested
# target on a fresh Pi fails with "mkdir ... No such file or directory". Note a
# --dry-run cannot catch this: it skips the mkdir and reports success anyway.
mkpath() { printf -- '--rsync-path=mkdir -p %q && rsync' "$1"; }

build_client() {
  say "building client"
  (cd "$REPO/web_app/client" && npm run build)
}

push_client() {
  # --delete matters here: asset filenames are content-hashed, so without it
  # every build leaves its predecessors behind forever.
  say "pushing client/dist -> $PI_HOST:~/$PI_DIR/web_app/client/dist"
  "${RSYNC[@]}" --delete "$(mkpath "$PI_DIR/web_app/client/dist")" \
    "$REPO/web_app/client/dist/" \
    "$PI_HOST:$PI_DIR/web_app/client/dist/"
}

push_api() {
  say "pushing web_app/server -> $PI_HOST:~/$PI_DIR/web_app/"
  "${RSYNC[@]}" "${EXCLUDES[@]}" "$(mkpath "$PI_DIR/web_app")" \
    "$REPO/web_app/server" \
    "$PI_HOST:$PI_DIR/web_app/"
}

push_engine() {
  say "pushing matrix -> $PI_HOST:~/$PI_DIR/"
  "${RSYNC[@]}" "${EXCLUDES[@]}" "$(mkpath "$PI_DIR")" \
    "$REPO/matrix" \
    "$PI_HOST:$PI_DIR/"
}

# The units live in /etc/systemd/system as root-owned COPIES, so syncing the
# repo alone never updates the running service — an edited ExecStart would be
# silently ignored. Install from the copy push_engine just synced, and only
# escalate to sudo when something actually changed.
push_units() {
  local src="$PI_DIR/matrix/raspberry_pi/systemd"
  # Sync the units ourselves rather than leaning on push_engine, so `./deploy.sh
  # api` compares against what's in THIS working tree, not a stale Pi-side copy.
  "${RSYNC[@]}" "$(mkpath "$src")" \
    "$REPO/matrix/raspberry_pi/systemd/panel-renderer.service" \
    "$REPO/matrix/raspberry_pi/systemd/panel-api.service" \
    "$PI_HOST:$src/"
  if ssh "$PI_HOST" "for u in panel-renderer panel-api; do
        cmp -s $src/\$u.service /etc/systemd/system/\$u.service || exit 1
      done" 2>/dev/null; then
    say "systemd units unchanged"
    return
  fi
  say "installing systemd units (sudo will prompt)"
  ssh -t "$PI_HOST" "sudo install -m 644 -o root -g root \
      $src/panel-renderer.service $src/panel-api.service /etc/systemd/system/ &&
    sudo systemctl daemon-reload"
}

restart() {
  local units="$*"
  say "restarting $units (sudo will prompt)"
  ssh -t "$PI_HOST" "sudo systemctl restart $units"
}

# ------------------------------------------------------------------ dispatch

for arg in "$@"; do
  case "$arg" in
    -n | --dry-run)
      RSYNC+=(--dry-run --itemize-changes)
      DRY_RUN=1
      say "DRY RUN — nothing will change"
      ;;
    -h | --help)
      usage
      exit 0
      ;;
  esac
done

if [[ -n "$DRY_RUN" ]]; then
  restart() { say "would restart: $*"; }
  build_client() { say "would build client"; }
  push_units() { say "would install systemd units if changed"; }
fi

target="${1:-all}"
[[ "$target" == -* ]] && target="${2:-all}"

case "$target" in
  client)
    build_client
    push_client
    say "done — no restart needed, Flask serves dist/ off disk per request"
    ;;
  api)
    push_api
    push_units
    restart panel-api
    ;;
  engine | matrix)
    push_engine
    push_units
    restart panel-renderer
    ;;
  units)
    push_units
    ;;
  all)
    build_client
    push_engine
    push_api
    push_client
    push_units
    restart panel-renderer panel-api
    ;;
  restart)
    restart panel-renderer panel-api
    ;;
  status)
    ssh "$PI_HOST" 'systemctl --no-pager --lines=0 status panel-renderer panel-api'
    ;;
  logs)
    ssh -t "$PI_HOST" 'journalctl -f -u panel-renderer -u panel-api'
    ;;
  *)
    echo "unknown target: $target" >&2
    usage >&2
    exit 2
    ;;
esac
