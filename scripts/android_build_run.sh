#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/adb_common.sh
source "$SCRIPT_DIR/adb_common.sh"

usage() {
  cat <<'USAGE'
Usage:
  android_build_run.sh [AVD_NAME] [options]

Start an Android emulator, wait until it is booted, prepare it for development,
then optionally build, install, and launch an Android APK.

Options:
  --avd NAME          AVD name to start. Same as positional AVD_NAME.
  --apk PATH          Install this APK after the emulator is ready.
  --project DIR       Build an Android Gradle project before install.
  --variant NAME      Gradle variant to build. Default: developDebug.
  --package NAME      Package to launch after install. Auto-detected when omitted.
  --no-launch         Install only; do not launch the app after install.
  --serial SERIAL     Use an already-running adb serial instead of starting a new emulator.
  --no-window         Start emulator headlessly.
  --wipe-data         Start emulator with a clean data partition.
  --timeout SECONDS   Boot timeout. Default: 180.
  --list              List available AVD names.
  -h, --help          Show this help.

Examples:
  ./scripts/android_build_run.sh 3a_API_35
  ./scripts/android_build_run.sh --avd 3a_API_35 --apk app-debug.apk
  ./scripts/android_build_run.sh --avd 3a_API_35 --project /path/to/android/project
  ./scripts/android_build_run.sh 3a_API_35 --project /path/to/android/project --variant stagingDebug
USAGE
}

capitalize_first() {
  local value="$1"
  printf '%s%s\n' "${value:0:1}" "${value:1}" | sed 's/^\(.\)/\U\1/'
}

find_apk_for_variant() {
  local project_dir="$1"
  local variant="$2"
  local metadata
  local output_file

  while IFS= read -r metadata; do
    if ! grep -q "\"variantName\"[[:space:]]*:[[:space:]]*\"$variant\"" "$metadata"; then
      continue
    fi

    output_file="$(awk -F'"' '/"outputFile"[[:space:]]*:/ {print $4; exit}' "$metadata")"
    if [[ -n "$output_file" && -f "$(dirname "$metadata")/$output_file" ]]; then
      printf '%s\n' "$(dirname "$metadata")/$output_file"
      return 0
    fi
  done < <(find "$project_dir" -path '*/build/outputs/apk/*/output-metadata.json' -type f -printf '%T@ %p\n' | sort -nr | cut -d' ' -f2-)

  return 1
}

avd_name=""
apk_path=""
project_dir=""
variant_name="developDebug"
serial=""
package_name=""
launch_after_install="1"
timeout_seconds="180"
emulator_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --avd)
      avd_name="${2:-}"
      if [[ -z "$avd_name" ]]; then
        printf 'Error: --avd needs a value.\n' >&2
        exit 1
      fi
      shift 2
      ;;
    --apk)
      apk_path="${2:-}"
      if [[ -z "$apk_path" ]]; then
        printf 'Error: --apk needs a value.\n' >&2
        exit 1
      fi
      shift 2
      ;;
    --project)
      project_dir="${2:-}"
      if [[ -z "$project_dir" ]]; then
        printf 'Error: --project needs a value.\n' >&2
        exit 1
      fi
      shift 2
      ;;
    --variant)
      variant_name="${2:-}"
      if [[ -z "$variant_name" ]]; then
        printf 'Error: --variant needs a value.\n' >&2
        exit 1
      fi
      shift 2
      ;;
    --package)
      package_name="${2:-}"
      if [[ -z "$package_name" ]]; then
        printf 'Error: --package needs a value.\n' >&2
        exit 1
      fi
      shift 2
      ;;
    --no-launch)
      launch_after_install="0"
      shift
      ;;
    --serial)
      serial="${2:-}"
      if [[ -z "$serial" ]]; then
        printf 'Error: --serial needs a value.\n' >&2
        exit 1
      fi
      shift 2
      ;;
    --timeout)
      timeout_seconds="${2:-}"
      if [[ ! "$timeout_seconds" =~ ^[0-9]+$ ]]; then
        printf 'Error: --timeout must be a number of seconds.\n' >&2
        exit 1
      fi
      shift 2
      ;;
    --no-window|--wipe-data)
      emulator_args+=("$1")
      shift
      ;;
    --list)
      EMULATOR_BIN="$(require_tool emulator)"
      "$EMULATOR_BIN" -list-avds
      exit 0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      printf 'Error: unknown option: %s\n' "$1" >&2
      usage >&2
      exit 1
      ;;
    *)
      if [[ -n "$avd_name" ]]; then
        printf 'Error: AVD name already set to %s.\n' "$avd_name" >&2
        exit 1
      fi
      avd_name="$1"
      shift
      ;;
  esac
done

ADB_BIN="$(require_tool adb)"
EMULATOR_BIN="$(require_tool emulator)"

if [[ -z "$serial" && -z "$avd_name" ]]; then
  avd_name="$("$EMULATOR_BIN" -list-avds | head -n 1)"
fi

if [[ -z "$serial" && -z "$avd_name" ]]; then
  printf 'Error: no AVD found. Create one in Android Studio Device Manager.\n' >&2
  exit 1
fi

if [[ -n "$serial" && -n "$avd_name" ]]; then
  printf 'Error: use either --serial or --avd, not both.\n' >&2
  exit 1
fi

if [[ -n "$project_dir" && -n "$apk_path" ]]; then
  printf 'Error: use either --project or --apk, not both.\n' >&2
  exit 1
fi

if [[ -n "$project_dir" ]]; then
  project_dir="$(cd "$project_dir" && pwd)"
  if [[ ! -x "$project_dir/gradlew" ]]; then
    printf 'Error: %s does not contain an executable ./gradlew.\n' "$project_dir" >&2
    exit 1
  fi
fi

if [[ -n "$apk_path" ]]; then
  apk_path="$(realpath "$apk_path")"
  if [[ ! -f "$apk_path" ]]; then
    printf 'Error: APK does not exist: %s\n' "$apk_path" >&2
    exit 1
  fi
fi

if [[ -z "$serial" ]]; then
  if ! "$EMULATOR_BIN" -list-avds | grep -Fxq "$avd_name"; then
    printf 'Error: AVD not found: %s\n\nAvailable AVDs:\n' "$avd_name" >&2
    "$EMULATOR_BIN" -list-avds >&2
    exit 1
  fi

  existing_emulator="$(first_online_emulator "$ADB_BIN" || true)"
  if [[ -n "$existing_emulator" ]]; then
    serial="$existing_emulator"
    printf 'Using already-running emulator: %s\n' "$serial"
  else
    log_file="/tmp/adb-emulator-${avd_name}.log"
    printf 'Starting emulator %s...\n' "$avd_name"
    printf 'Emulator log: %s\n' "$log_file"
    nohup "$EMULATOR_BIN" -avd "$avd_name" "${emulator_args[@]}" >"$log_file" 2>&1 &
    "$ADB_BIN" wait-for-device
    serial="$(first_online_emulator "$ADB_BIN" || true)"
    if [[ -z "$serial" ]]; then
      printf 'Error: emulator started, but no online emulator serial was detected.\n' >&2
      exit 1
    fi
  fi
fi

mapfile -t ADB_SERIAL_ARGS < <(adb_serial_args "$serial")

printf 'Waiting for Android boot on %s...\n' "$serial"
wait_for_boot "$ADB_BIN" "$serial" "$timeout_seconds"

printf 'Preparing emulator for development...\n'
"$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell input keyevent KEYCODE_WAKEUP >/dev/null 2>&1 || true
"$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell input keyevent KEYCODE_MENU >/dev/null 2>&1 || true
"$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell settings put global stay_on_while_plugged_in 3 >/dev/null 2>&1 || true
"$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell settings put global window_animation_scale 0 >/dev/null 2>&1 || true
"$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell settings put global transition_animation_scale 0 >/dev/null 2>&1 || true
"$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell settings put global animator_duration_scale 0 >/dev/null 2>&1 || true

if [[ -n "$project_dir" ]]; then
  assemble_task=":app:assemble$(capitalize_first "$variant_name")"
  printf 'Building %s in %s...\n' "$variant_name" "$project_dir"
  (cd "$project_dir" && ./gradlew "$assemble_task")
  if ! apk_path="$(find_apk_for_variant "$project_dir" "$variant_name")"; then
    printf 'Error: build completed, but no APK output was found for variant %s.\n' "$variant_name" >&2
    printf 'Expected Gradle output metadata under */build/outputs/apk/*/output-metadata.json.\n' >&2
    exit 1
  fi
fi

if [[ -n "$apk_path" ]]; then
  printf 'Installing %s...\n' "$apk_path"
  "$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" install -r "$apk_path"

  if [[ "$launch_after_install" == "1" ]]; then
    if [[ -z "$package_name" ]]; then
      package_name="$(package_name_from_apk "$apk_path" || true)"
    fi

    if [[ -z "$package_name" ]]; then
      printf 'Warning: installed APK, but could not detect package name to launch.\n' >&2
      printf 'Run again with --package com.example.app or launch manually with adb monkey.\n' >&2
    else
      printf 'Launching %s...\n' "$package_name"
      "$ADB_BIN" "${ADB_SERIAL_ARGS[@]}" shell monkey -p "$package_name" -c android.intent.category.LAUNCHER 1 >/dev/null
    fi
  fi
fi

printf 'Ready: %s\n' "$serial"
"$SCRIPT_DIR/adb_emulator_info.sh" --serial "$serial"
