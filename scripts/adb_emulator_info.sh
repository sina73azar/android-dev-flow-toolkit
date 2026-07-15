#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/adb_common.sh
source "$SCRIPT_DIR/adb_common.sh"

usage() {
  cat <<'USAGE'
Usage:
  adb_emulator_info.sh [--serial SERIAL]

Print useful Android emulator/device information.

Options:
  --serial SERIAL   Use a specific adb device serial, for example emulator-5554.
  -h, --help        Show this help.
USAGE
}

serial=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --serial)
      serial="${2:-}"
      if [[ -z "$serial" ]]; then
        printf 'Error: --serial needs a value.\n' >&2
        exit 1
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Error: unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

ADB_BIN="$(require_tool adb)"
EMULATOR_BIN="$(require_tool emulator)"

if [[ -z "$serial" ]]; then
  serial="$(first_online_device "$ADB_BIN" || true)"
fi

if [[ -z "$serial" ]]; then
  printf 'No online adb device found.\n\n'
  printf 'Available emulators:\n'
  "$EMULATOR_BIN" -list-avds | sed 's/^/  - /'
  printf '\nStart one with:\n'
  printf '  ./scripts/android_build_run.sh AVD_NAME\n'
  exit 0
fi

mapfile -t ADB_SERIAL_ARGS < <(adb_serial_args "$serial")

model="$("$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell getprop ro.product.model | tr -d '\r')"
manufacturer="$("$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell getprop ro.product.manufacturer | tr -d '\r')"
android_version="$("$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell getprop ro.build.version.release | tr -d '\r')"
api_level="$("$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell getprop ro.build.version.sdk | tr -d '\r')"
build_id="$("$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell getprop ro.build.display.id | tr -d '\r')"
boot_completed="$("$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell getprop sys.boot_completed | tr -d '\r')"
screen_size="$("$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell wm size | tr -d '\r' | sed 's/^Physical size: //')"
screen_density="$("$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell wm density | tr -d '\r' | sed 's/^Physical density: //')"
battery="$("$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell dumpsys battery | awk -F: '/level/{gsub(/ /, "", $2); print $2 "%"; exit}')"
storage="$("$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell df -h /data 2>/dev/null | awk 'NR == 2 {print $4 " free of " $2}')"
ip_addr="$("$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell ip -f inet addr show wlan0 2>/dev/null | awk '/inet / {print $2; exit}' || true)"
packages="$("$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell pm list packages | wc -l | tr -d ' ')"

printf 'ADB device info\n'
printf '===============\n'
print_kv "Serial" "$serial"
print_kv "Manufacturer" "${manufacturer:-unknown}"
print_kv "Model" "${model:-unknown}"
print_kv "Android" "${android_version:-unknown} / API ${api_level:-unknown}"
print_kv "Build" "${build_id:-unknown}"
print_kv "Boot completed" "${boot_completed:-unknown}"
print_kv "Screen size" "${screen_size:-unknown}"
print_kv "Screen density" "${screen_density:-unknown}"
print_kv "Battery" "${battery:-unknown}"
print_kv "Data storage" "${storage:-unknown}"
print_kv "Wi-Fi IP" "${ip_addr:-unavailable}"
print_kv "Package count" "${packages:-unknown}"
