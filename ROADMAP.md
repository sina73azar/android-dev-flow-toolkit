# Roadmap

## Goal

Build a reusable, cross-platform Android and Gradle development workflow toolkit.
It should help teams move faster during feature development, testing, debugging,
APK sharing, and release preparation.

## Phase 1: Interactive Build And Run

Status: implemented baseline.

- Load project settings from `.android-dev-flow.json`.
- Initialize project settings with `adf init`.
- Validate project layout and config with `adf validate`.
- Show an interactive menu.
- Build a selected Gradle variant.
- Detect generated APKs from `output-metadata.json`.
- Select an online adb device when available.
- Start an installed AVD when no adb device is online.
- Install and launch the selected variant.
- Keep the implementation dependency-light and cross-platform.

Validation currently checks:

- project directory exists
- `.android-dev-flow.json` schema
- Gradle settings file exists
- Gradle wrapper exists
- configured module directory exists
- module `build.gradle` or `build.gradle.kts` exists
- default variant is included in configured variants
- Gradle module and variant names can produce explicit assemble task names

## Next Planned Work

These are the next implementation slices before broader device/debugging work.

### 1. Non-Interactive Commands

Add scriptable commands that mirror the interactive menu:

```bash
adf build develop
adf run staging
adf devices
adf avds
adf apk production
```

Planned behavior:

- Accept variant labels from `.android-dev-flow.json`, such as `develop`.
- Also accept exact Gradle variant names, such as `developDebug`.
- Print the exact Gradle or adb command before execution.
- Keep `adf` with no subcommand as the interactive menu.
- Preserve `--project`, `--serial`, `--avd`, and `--no-launch` where useful.

### 2. APK Packaging And Sharing

Add an APK export flow for manual QA and company sharing workflows:

```bash
adf package develop
```

Planned output:

```text
dist/RefahDpi-developDebug-v1.2.3-42.apk
dist/RefahDpi-developDebug-v1.2.3-42.txt
```

The metadata text file should include:

- project name
- module
- variant
- application id
- version name and version code
- source APK path
- packaged APK path
- git branch
- git commit hash
- build timestamp
- SHA-256

### 3. Stronger Gradle Awareness

Improve validation and command selection without making builds slower by
default:

- Detect available Gradle modules from `settings.gradle` and
  `settings.gradle.kts`.
- Optionally verify assemble tasks with Gradle when requested:

  ```bash
  adf validate --gradle
  ```

- Keep normal `adf validate` fast and local.
- Improve error messages for common flavor/build-type mismatches.

### 4. Test Coverage

Grow tests around behavior that should stay stable:

- config initialization and validation
- Gradle task naming
- module detection
- APK output metadata parsing
- CLI argument parsing
- Android SDK tool discovery

Use Python's standard `unittest` first so contributors do not need extra test
dependencies.

## Phase 2: Device Utilities

- Device and emulator info screen.
- Wi-Fi ADB helper for physical devices.
- Wake/unlock device.
- Keep screen awake while plugged in.
- Disable animations for testing.
- Optional `scrcpy` launcher when installed.

## Phase 3: Debugging And Logs

- Stream app logs for selected variant.
- Crash-only log view.
- Capture screenshot.
- Record screen.
- Create a bug report bundle with device info, logs, screenshots, recording,
  APK metadata, git branch, and commit hash.

## Phase 4: APK Packaging

- Build APK only.
- Open generated APK folder.
- Copy APK path to clipboard when possible.
- Generate a text summary next to APK:
  - project name
  - variant
  - version name/code
  - application id
  - git branch
  - commit hash
  - build timestamp
  - SHA-256

## Phase 5: GitLab Integration

- Support self-hosted GitLab.
- Show latest pipeline status for current branch.
- Open pipeline or merge request URL.
- Download latest successful APK artifact.
- Help create release tags and changelog notes.

## Phase 6: Reusable Project Distribution

- Publish on GitHub.
- Add installation docs for Linux, macOS, and Windows.
- Provide shell, PowerShell, and batch wrappers.
- Provide example configs for Android apps, Android libraries, and generic
  Gradle projects.
- Add tests around config parsing, Gradle task naming, APK metadata parsing,
  and tool discovery.
