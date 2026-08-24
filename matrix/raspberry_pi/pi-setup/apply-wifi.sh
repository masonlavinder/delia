#!/usr/bin/env bash
#
# apply-wifi.sh — push the networks in wifi.conf to the Pi.
#
#   ./apply-wifi.sh                 install every network in wifi.conf, over SSH
#   ./apply-wifi.sh home            install only the [home] section
#   ./apply-wifi.sh --write-to DIR  write the profiles into DIR instead of using
#                                   SSH — for a mounted SD card, when the Pi is
#                                   no longer reachable. Run that under sudo.
#
#   -n / --dry-run   show what would be installed, passwords redacted
#   -h / --help
#
# Override the target:  PI_HOST=user@host ./apply-wifi.sh
# Override the config:  WIFI_CONF=/path/to/wifi.conf ./apply-wifi.sh
#
# Both modes produce the same artifact — a NetworkManager keyfile
# (root:root 0600) in /etc/NetworkManager/system-connections/. NM ignores a
# keyfile that is group- or world-readable, which is also why the password is
# never passed as a command-line argument: it would show up in the Pi's process
# list. It travels inside the file, over scp.
#
# See instructions/wifi-new-network.md for the whole procedure.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="${WIFI_CONF:-$HERE/wifi.conf}"
PI_HOST="${PI_HOST:-mlavinder@delia.local}"
NM_DIR=/etc/NetworkManager/system-connections

say() { printf '\033[1;35m==>\033[0m %s\n' "$*"; }
die() {
  printf '\033[1;31merror:\033[0m %s\n' "$*" >&2
  exit 1
}

usage() {
  awk 'NR > 1 && /^#/ { sub(/^#/, ""); sub(/^ /, ""); print; next }
       NR > 1         { exit }' "${BASH_SOURCE[0]}"
}

# ------------------------------------------------------------------ arguments

DRY_RUN=""
WRITE_TO=""
WANTED=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n | --dry-run) DRY_RUN=1 ;;
    -h | --help)
      usage
      exit 0
      ;;
    --write-to)
      WRITE_TO="${2:-}"
      [[ -n "$WRITE_TO" ]] || die "--write-to needs a directory"
      shift
      ;;
    -*) die "unknown option: $1" ;;
    *) WANTED+=("$1") ;;
  esac
  shift
done

# ------------------------------------------------------------------ the config

[[ -f "$CONF" ]] || die "no config at $CONF
       Copy $HERE/wifi.conf.example to wifi.conf and fill it in."

trim() {
  local s=$1
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

declare -A CFG
SECTIONS=()
section=""
lineno=0

# A hand-rolled INI parse rather than `source`, so the file stays data: a
# password full of shell metacharacters can't turn into a command.
while IFS= read -r raw || [[ -n "$raw" ]]; do
  lineno=$((lineno + 1))
  line="$(trim "$raw")"
  # Comments are whole-line only — a `#` mid-line is part of the password.
  [[ -z "$line" || "${line:0:1}" == "#" || "${line:0:1}" == ";" ]] && continue

  if [[ "$line" == "["*"]" ]]; then
    section="$(trim "${line:1:${#line}-2}")"
    [[ "$section" =~ ^[A-Za-z0-9_-]+$ ]] ||
      die "$CONF:$lineno: section name must be letters, digits, - or _: [$section]"
    [[ -n "${CFG[$section.__seen]:-}" ]] && die "$CONF:$lineno: duplicate section [$section]"
    CFG["$section.__seen"]=1
    SECTIONS+=("$section")
    continue
  fi

  [[ -n "$section" ]] || die "$CONF:$lineno: '$line' is outside any [section]"
  [[ "$line" == *"="* ]] || die "$CONF:$lineno: expected 'key = value', got '$line'"

  key="$(trim "${line%%=*}")"
  val="$(trim "${line#*=}")"
  # A quoted value is taken literally, so trailing spaces survive.
  if [[ ${#val} -ge 2 && "${val:0:1}" == '"' && "${val: -1}" == '"' ]]; then
    val="${val:1:${#val}-2}"
  fi
  case "$key" in
    ssid | psk | priority | hidden) CFG["$section.$key"]="$val" ;;
    *) die "$CONF:$lineno: unknown key '$key' (want ssid, psk, priority or hidden)" ;;
  esac
done <"$CONF"

((${#SECTIONS[@]})) || die "$CONF has no [sections] — nothing to install"

# Named sections only, if any were given.
if ((${#WANTED[@]})); then
  for w in "${WANTED[@]}"; do
    [[ -n "${CFG[$w.__seen]:-}" ]] || die "no [$w] section in $CONF"
  done
  SECTIONS=("${WANTED[@]}")
fi

# ------------------------------------------------------------------ profiles

get() { printf '%s' "${CFG[$1.$2]:-${3:-}}"; }

uuid() {
  if [[ -r /proc/sys/kernel/random/uuid ]]; then
    cat /proc/sys/kernel/random/uuid
  else
    uuidgen
  fi
}

# Emit one NetworkManager keyfile on stdout. With $1 = "redact" the password is
# replaced, so --dry-run can show the real shape of the file without leaking it.
profile() {
  local mode=$1 name=$2 ssid psk hidden priority
  ssid="$(get "$name" ssid)"
  psk="$(get "$name" psk)"
  priority="$(get "$name" priority 0)"
  hidden="$(get "$name" hidden false)"

  [[ -n "$ssid" ]] || die "[$name]: ssid is required"
  [[ "$ssid" == CHANGE_ME* ]] && die "[$name]: ssid is still the placeholder — edit $CONF"
  [[ "$psk" == CHANGE_ME* ]] && die "[$name]: psk is still the placeholder — edit $CONF"
  [[ "$priority" =~ ^-?[0-9]+$ ]] || die "[$name]: priority must be a whole number, got '$priority'"
  case "${hidden,,}" in
    true | yes | 1) hidden=true ;;
    false | no | 0 | "") hidden=false ;;
    *) die "[$name]: hidden must be true or false, got '$hidden'" ;;
  esac
  # WPA-PSK is 8–63 characters; anything shorter is a typo, not a password.
  if [[ -n "$psk" && (${#psk} -lt 8 || ${#psk} -gt 63) ]]; then
    die "[$name]: a WPA password must be 8-63 characters (this one is ${#psk})"
  fi
  [[ "$mode" == redact ]] && psk="${psk:+<${#psk} characters, hidden>}"

  cat <<-EOF
		[connection]
		id=$name
		uuid=$(uuid)
		type=wifi
		autoconnect=true
		autoconnect-priority=$priority

		[wifi]
		mode=infrastructure
		ssid=$ssid
		hidden=$hidden
	EOF

  # No [wifi-security] block at all means an open network.
  if [[ -n "$psk" ]]; then
    cat <<-EOF

			[wifi-security]
			key-mgmt=wpa-psk
			psk=$psk
		EOF
  fi

  cat <<-EOF

		[ipv4]
		method=auto

		[ipv6]
		method=auto
		addr-gen-mode=stable-privacy
	EOF
}

if [[ -n "$DRY_RUN" ]]; then
  say "DRY RUN — nothing will be written"
  for name in "${SECTIONS[@]}"; do
    # Render first: a validation error should not follow a header claiming the
    # file is about to be written.
    rendered="$(profile redact "$name")"
    printf '\n--- %s/%s.nmconnection (root:root 0600)\n%s\n' \
      "${WRITE_TO:-$NM_DIR}" "$name" "$rendered"
  done
  exit 0
fi

# Stage the files locally first, so a config error aborts before anything is
# installed — half-applied networks are how a headless Pi goes missing.
umask 077
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
for name in "${SECTIONS[@]}"; do
  profile plain "$name" >"$STAGE/$name.nmconnection"
done

# ------------------------------------------------------------------ install

if [[ -n "$WRITE_TO" ]]; then
  [[ -d "$WRITE_TO" ]] || die "not a directory: $WRITE_TO
       For a mounted SD card this is <mountpoint>$NM_DIR"
  say "writing ${#SECTIONS[@]} profile(s) to $WRITE_TO"
  if [[ $EUID -eq 0 ]]; then
    install -m 600 -o root -g root "$STAGE"/*.nmconnection "$WRITE_TO/"
  else
    # NetworkManager silently skips a keyfile it doesn't trust, so a non-root
    # write is a trap: it looks like it worked and the Pi never joins.
    install -m 600 "$STAGE"/*.nmconnection "$WRITE_TO/"
    printf '\033[1;33mwarning:\033[0m not running as root — the files are owned by %s.\n' "$(id -un)" >&2
    printf '         NetworkManager ignores keyfiles it does not own. Fix with:\n' >&2
    printf '           sudo chown root:root %s/*.nmconnection\n' "$WRITE_TO" >&2
  fi
  say "done — unmount the card before pulling it"
  exit 0
fi

say "pushing ${#SECTIONS[@]} profile(s) to $PI_HOST"
REMOTE_TMP="$(ssh "$PI_HOST" 'umask 077; mktemp -d')"
[[ -n "$REMOTE_TMP" ]] || die "could not create a temp dir on $PI_HOST"
scp -q "$STAGE"/*.nmconnection "$PI_HOST:$REMOTE_TMP/"

say "installing (sudo on the Pi will prompt)"
ssh -t "$PI_HOST" "
  sudo install -m 600 -o root -g root $REMOTE_TMP/*.nmconnection $NM_DIR/ &&
  sudo nmcli connection reload
  rm -rf $REMOTE_TMP"

say "installed: ${SECTIONS[*]}"
cat <<EOF

The Pi keeps every profile it has and joins whichever is in range. To switch now
(only works if the new network is already reachable from where the Pi sits):

  ssh $PI_HOST 'sudo nmcli device wifi rescan; sudo nmcli connection up ${SECTIONS[0]}'

Otherwise just move it and power it back on. Verify with:

  ssh $PI_HOST 'nmcli -f NAME,DEVICE,ACTIVE connection show'
EOF
