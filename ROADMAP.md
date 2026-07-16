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
- Detect Android application modules during `adf init` and persist all runnable
  modules in `.android-dev-flow.json`.
- List configured Android application modules in project info.
- Prompt for runnable module and variant during interactive Run when multiple
  app modules are present.
- Auto-detect Android variants from module Gradle files when
  `variants` is set to `auto`.
- Show an interactive menu.
- Support non-interactive `build`, `run`, `apk`, `package`, `devices`, and `avds`
  commands.
- Build a selected Gradle variant.
- Detect generated APKs from `output-metadata.json`.
- Export shareable APK copies and metadata files.
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

### 1. Stronger Gradle Awareness

Improve validation and command selection without making builds slower by
default:

- Detect available Gradle modules from `settings.gradle` and
  `settings.gradle.kts`.
- Improve module detection for customized Gradle source sets and plugin
  aliases.
- Improve auto-detection for multi-dimension flavor matrices.
- Optionally verify assemble tasks with Gradle when requested:

  ```bash
  adf validate --gradle
  ```

- Keep normal `adf validate` fast and local.
- Improve error messages for uncommon flavor/build-type mismatches.

### 2. Test Coverage

Grow tests around behavior that should stay stable:

- config initialization and validation
- Gradle task naming
- module detection
- APK output metadata parsing
- CLI argument parsing
- Android SDK tool discovery

Use Python's standard `unittest` first so contributors do not need extra test
dependencies.

### Completed: Non-Interactive Commands

Implemented scriptable commands that mirror common interactive menu actions:

```bash
adf build <variant-label>
adf run <variant-label>
adf devices
adf avds
adf apk <variant-label>
```

Implemented behavior:

- Accept detected variant labels from `.android-dev-flow.json`.
- Also accept exact Gradle variant names.
- Keep `adf` with no subcommand as the interactive menu.
- Preserve `--project`, `--serial`, `--avd`, and `--no-launch` where useful.

### Completed: APK Packaging And Sharing

Implemented APK export for manual QA and company sharing workflows:

```bash
adf package <variant-label>
```

Implemented output:

```text
dist/MyApp-debug-v1.2.3-42.apk
dist/MyApp-debug-v1.2.3-42.txt
```

Implemented behavior:

- Accept variant labels and exact Gradle variant names.
- Build before packaging by default.
- Support `--no-build` to package an existing APK.
- Write packages to `dist/` by default.
- Support `--output-dir` for company share folders.
- Keep generated filenames filesystem-safe and inspectable.
- Include metadata for project, module, variant, application ID, version,
  source APK, packaged APK, git branch, git commit, timestamp, and SHA-256.

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

- Status: implemented baseline with `adf build`, `adf apk`, and
  `adf package`.
- Later: open generated APK folder.
- Later: copy APK path to clipboard when possible.
- Implemented: generate a text summary next to APK with:
  - project name
  - module
  - variant
  - version name/code
  - application id
  - source APK path
  - packaged APK path
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
