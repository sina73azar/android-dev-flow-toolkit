# scripts_mrc

A small home for practical and fun command-line scripts.

All scripts in this starter set use only Python's standard library, so you can
run them without installing packages.

## Quick start

```bash
python3 scripts/passphrase.py
python3 scripts/focus_timer.py --minutes 1
python3 scripts/file_sorter.py ~/Downloads
python3 scripts/dice_roller.py 2d6
```

Use `--help` on any script to see its options:

```bash
python3 scripts/file_sorter.py --help
```

## Scripts

- `file_sorter.py`: preview or apply a simple folder cleanup by file extension.
- `passphrase.py`: generate readable passphrases for throwaway accounts or notes.
- `focus_timer.py`: run a terminal countdown timer.
- `dice_roller.py`: roll dice expressions like `2d6`, `d20`, or `4d6+2`.
- `adb_avd_info.sh`: inspect installed Android Studio emulator definitions while
  they are off.
- `adb_emulator_info.sh`: print useful Android device/emulator info.
- `android_build_run.sh`: start an Android emulator, wait for boot, prepare it,
  then install an APK or build, install, and launch a selected Gradle variant.

## Android emulator scripts

List your installed Android Studio emulators:

```bash
./scripts/android_build_run.sh --list
```

Inspect an emulator while it is off:

```bash
./scripts/adb_avd_info.sh 3a_API_35
```

On this machine, the detected AVDs are:

```text
3a_API_35
Pixel_3a_API_22
```

Start an emulator and prepare it for development:

```bash
./scripts/android_build_run.sh 3a_API_35
```

After it is running, get device info:

```bash
./scripts/adb_emulator_info.sh
```

Install an APK after booting:

```bash
./scripts/android_build_run.sh 3a_API_35 --apk /path/to/app-debug.apk
```

Build, install, and launch a Gradle Android project. The default variant is
`developDebug`:

```bash
./scripts/android_build_run.sh 3a_API_35 --project /path/to/android/project
```

Build a specific variant:

```bash
./scripts/android_build_run.sh 3a_API_35 --project /path/to/android/project --variant stagingDebug
```

When the script installs an APK, it now launches the installed app by default.
Skip that with `--no-launch`, or force the launch package with `--package`:

```bash
./scripts/android_build_run.sh 3a_API_35 --project /path/to/android/project --package com.example.app
```

The prepare step wakes the emulator, waits for Android to finish booting,
keeps the screen awake while plugged in, and disables system animations.

## Script ideas to add next

- Batch rename photos by date.
- Find duplicate files by hash.
- Convert CSV files to JSON.
- Generate a daily note from a template.
- Pick a random lunch, workout, or study task.
