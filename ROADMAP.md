# Roadmap

## Goal

Build a reusable, cross-platform Android and Gradle development workflow toolkit.
It should help teams move faster during feature development, testing, debugging,
APK sharing, and release preparation.

## Phase 1: Interactive Build And Run

- Load project settings from `.android-dev-flow.json`.
- Show an interactive menu.
- Build a selected Gradle variant.
- Detect generated APKs from `output-metadata.json`.
- Select an online adb device when available.
- Start an installed AVD when no adb device is online.
- Install and launch the selected variant.
- Keep the implementation dependency-light and cross-platform.

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
