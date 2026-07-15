#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/adb_common.sh
source "$SCRIPT_DIR/adb_common.sh"

usage() {
  cat <<'USAGE'
Usage:
  adb_avd_info.sh [AVD_NAME]

Print installed Android Virtual Device configuration without starting it.

Examples:
  ./scripts/adb_avd_info.sh
  ./scripts/adb_avd_info.sh 3a_API_35
USAGE
}

ini_value() {
  local file="$1"
  local key="$2"
  if [[ -f "$file" ]]; then
    awk -F= -v key="$key" '$1 == key {print substr($0, index($0, "=") + 1); exit}' "$file"
  fi
}

avd_name="${1:-}"
if [[ "${avd_name:-}" == "-h" || "${avd_name:-}" == "--help" ]]; then
  usage
  exit 0
fi

EMULATOR_BIN="$(require_tool emulator)"

if [[ -z "$avd_name" ]]; then
  printf 'Available AVDs:\n'
  "$EMULATOR_BIN" -list-avds | sed 's/^/  - /'
  printf '\nShow one with:\n'
  printf '  ./scripts/adb_avd_info.sh AVD_NAME\n'
  exit 0
fi

if ! "$EMULATOR_BIN" -list-avds | grep -Fxq "$avd_name"; then
  printf 'Error: AVD not found: %s\n\nAvailable AVDs:\n' "$avd_name" >&2
  "$EMULATOR_BIN" -list-avds >&2
  exit 1
fi

avd_ini="$HOME/.android/avd/${avd_name}.ini"
avd_dir="$(ini_value "$avd_ini" path)"
config_ini="$avd_dir/config.ini"

if [[ -z "$avd_dir" || ! -f "$config_ini" ]]; then
  printf 'Error: could not find config.ini for AVD: %s\n' "$avd_name" >&2
  exit 1
fi

target="$(ini_value "$config_ini" target)"
tag="$(ini_value "$config_ini" tag.display)"
abi="$(ini_value "$config_ini" abi.type)"
device="$(ini_value "$config_ini" hw.device.name)"
manufacturer="$(ini_value "$config_ini" hw.device.manufacturer)"
width="$(ini_value "$config_ini" hw.lcd.width)"
height="$(ini_value "$config_ini" hw.lcd.height)"
density="$(ini_value "$config_ini" hw.lcd.density)"
ram="$(ini_value "$config_ini" hw.ramSize)"
heap="$(ini_value "$config_ini" vm.heapSize)"
disk="$(ini_value "$config_ini" disk.dataPartition.size)"
sdcard="$(ini_value "$config_ini" sdcard.size)"
keyboard="$(ini_value "$config_ini" hw.keyboard)"
play_store="$(ini_value "$config_ini" PlayStore.enabled)"
snapshot="$(ini_value "$config_ini" fastboot.forceColdBoot)"

printf 'AVD config info\n'
printf '===============\n'
print_kv "Name" "$avd_name"
print_kv "Path" "$avd_dir"
print_kv "Target" "${target:-unknown}"
print_kv "System image tag" "${tag:-unknown}"
print_kv "ABI" "${abi:-unknown}"
print_kv "Device" "${manufacturer:-unknown} ${device:-unknown}"
print_kv "Screen" "${width:-?}x${height:-?} @ ${density:-?} dpi"
print_kv "RAM" "${ram:-unknown} MB"
print_kv "VM heap" "${heap:-unknown} MB"
print_kv "Data partition" "${disk:-unknown}"
print_kv "SD card" "${sdcard:-unknown}"
print_kv "Hardware keyboard" "${keyboard:-unknown}"
print_kv "Play Store" "${play_store:-unknown}"
print_kv "Force cold boot" "${snapshot:-unknown}"
