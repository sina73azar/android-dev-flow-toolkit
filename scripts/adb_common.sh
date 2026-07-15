#!/usr/bin/env bash

set -euo pipefail

find_android_tool() {
  local tool_name="$1"

  local candidates=()
  if [[ -n "${ANDROID_HOME:-}" ]]; then
    candidates+=("$ANDROID_HOME/emulator/$tool_name")
    candidates+=("$ANDROID_HOME/platform-tools/$tool_name")
    candidates+=("$ANDROID_HOME/tools/$tool_name")
  fi
  if [[ -n "${ANDROID_SDK_ROOT:-}" ]]; then
    candidates+=("$ANDROID_SDK_ROOT/emulator/$tool_name")
    candidates+=("$ANDROID_SDK_ROOT/platform-tools/$tool_name")
    candidates+=("$ANDROID_SDK_ROOT/tools/$tool_name")
  fi
  candidates+=("$HOME/Android/Sdk/emulator/$tool_name")
  candidates+=("$HOME/Android/Sdk/platform-tools/$tool_name")
  candidates+=("$HOME/Android/Sdk/tools/$tool_name")

  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return
    fi
  done

  if command -v "$tool_name" >/dev/null 2>&1; then
    command -v "$tool_name"
    return
  fi

  return 1
}

require_tool() {
  local tool_name="$1"
  local path

  if ! path="$(find_android_tool "$tool_name")"; then
    printf 'Error: could not find %s. Install Android SDK tools or add them to PATH.\n' "$tool_name" >&2
    exit 1
  fi

  printf '%s\n' "$path"
}

find_android_build_tool() {
  local tool_name="$1"
  local roots=()

  if [[ -n "${ANDROID_HOME:-}" ]]; then
    roots+=("$ANDROID_HOME/build-tools")
  fi
  if [[ -n "${ANDROID_SDK_ROOT:-}" ]]; then
    roots+=("$ANDROID_SDK_ROOT/build-tools")
  fi
  roots+=("$HOME/Android/Sdk/build-tools")

  local root
  local version
  local candidate
  for root in "${roots[@]}"; do
    if [[ ! -d "$root" ]]; then
      continue
    fi

    while IFS= read -r version; do
      candidate="$root/$version/$tool_name"
      if [[ -x "$candidate" ]]; then
        printf '%s\n' "$candidate"
        return
      fi
    done < <(find "$root" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -Vr)
  done

  return 1
}

package_name_from_apk() {
  local apk_path="$1"
  local aapt_bin

  if ! aapt_bin="$(find_android_build_tool aapt)"; then
    return 1
  fi

  "$aapt_bin" dump badging "$apk_path" 2>/dev/null | awk -F"'" '/^package: name=/{print $2; exit}'
}

adb_serial_args() {
  local serial="${1:-}"
  if [[ -n "$serial" ]]; then
    printf '%s\n%s\n' "-s" "$serial"
  fi
}

first_online_device() {
  local adb_bin="$1"
  "$adb_bin" devices | awk 'NR > 1 && $2 == "device" { print $1; exit }'
}

first_online_emulator() {
  local adb_bin="$1"
  "$adb_bin" devices | awk 'NR > 1 && $1 ~ /^emulator-/ && $2 == "device" { print $1; exit }'
}

wait_for_boot() {
  local adb_bin="$1"
  local serial="$2"
  local timeout_seconds="${3:-180}"
  local started
  local now
  local boot_completed

  started="$(date +%s)"
  while true; do
    boot_completed="$("$adb_bin" "${ADB_SERIAL_ARGS[@]}" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
    if [[ "$boot_completed" == "1" ]]; then
      return 0
    fi

    now="$(date +%s)"
    if (( now - started >= timeout_seconds )); then
      printf 'Error: device %s did not finish booting within %s seconds.\n' "$serial" "$timeout_seconds" >&2
      return 1
    fi

    sleep 2
  done
}

print_kv() {
  printf '%-22s %s\n' "$1:" "$2"
}
