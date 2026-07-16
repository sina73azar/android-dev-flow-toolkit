# android-dev-flow-toolkit

Interactive developer automation for Android and Gradle projects.

This project is starting as a practical toolkit for daily Android development:
building variants, selecting devices/emulators, installing APKs, launching apps,
and later capturing logs, bug reports, and GitLab build context.

The first version intentionally uses Python's standard library only, so it can
run on Linux, macOS, and Windows with Python 3.10+.

## Quick start

From this repository:

```bash
PYTHONPATH=src python3 -m android_dev_flow --project /path/to/android/project
```

Or install the CLI once and run it from any Android project:

```bash
cd /path/to/android-dev-flow-toolkit
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .

cd /path/to/android/project
adf init
adf
```

Inside an Android project, `adf init` creates `.android-dev-flow.json`:

```json
{
  "project_name": "MyApp",
  "module": "app",
  "modules": [
    "app"
  ],
  "default_variant": "debug",
  "variants": "auto"
}
```

Then run:

```bash
adf
```

## Installing the CLI for a project

Install `android-dev-flow-toolkit` from this repository, not inside each Android
project. The install creates the `adf` command and points it back to this source
tree in editable mode, so changes in `src/android_dev_flow/` are used
immediately.

```bash
cd /home/azarfarshi.s@drp.local/Documents/android-dev-flow-toolkit

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

Then use the CLI from an Android project directory:

```bash
cd /home/azarfarshi.s@drp.local/StudioProjects/kotlin_new_android_design
adf init
adf validate
adf
```

`adf init` creates `.android-dev-flow.json`. `adf validate` checks that the
project has a Gradle settings file, Gradle wrapper, configured module, module
build file, and valid variant names.

If the Android project already has `.android-dev-flow.json` in its root, this
is enough:

```bash
adf
```

When opening a new terminal, activate the toolkit environment again before using
`adf`:

```bash
source /home/azarfarshi.s@drp.local/Documents/android-dev-flow-toolkit/.venv/bin/activate
```

If editable install fails with a `build_editable` or PEP 660 error, upgrade the
packaging tools inside the virtual environment:

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

## Project setup

From an Android project root, initialize the toolkit config:

```bash
adf init
```

This creates `.android-dev-flow.json` with detected project name/module when
possible and automatic variant detection:

```json
{
  "project_name": "MyApp",
  "module": "app",
  "modules": [
    "app"
  ],
  "default_variant": "debug",
  "variants": "auto"
}
```

If the Gradle project has multiple Android application modules, `adf init`
stores all detected runnable modules in `modules` and keeps `module` as the
default module for scriptable commands:

```json
{
  "project_name": "MyApp",
  "module": "app",
  "modules": [
    "app",
    "analoge_clock",
    "memory_game"
  ],
  "default_variant": "debug",
  "variants": "auto"
}
```

The default module prefers `app` when it exists, otherwise the first detected
Android application module. Override the default when needed:

```bash
adf init --module app
adf init --module mobile
```

With `variants` set to `auto`, the toolkit reads the configured module's
`build.gradle` or `build.gradle.kts`, detects common Android `productFlavors`
and `buildTypes`, and exposes detected variants in the menu and commands. For
an app without flavors, labels include `debug` and `release`. For a flavored
app, labels combine flavor and build type, such as `<flavor>-debug` and
`<flavor>-release`. The default variant prefers debug when available.

You can customize values during initialization:

```bash
adf init \
  --name MyApp \
  --module app \
  --default-variant qaDebug \
  --variant qa=qaDebug \
  --variant demo=demoDebug
```

Passing `--variant` writes a fixed variant map instead of `variants: "auto"`.

Overwrite an existing config only when intended:

```bash
adf init --force
```

Validate project setup before building or running:

```bash
adf validate
```

## Usage help

Show the complete usage guide:

```bash
adf help
```

Show command-specific help and examples:

```bash
adf help init
adf help build
adf help run
adf help package
```

## Non-interactive commands

Use `adf` without a subcommand for the interactive menu. The menu exposes Run,
Build, Show APK, and Package APK actions for each configured variant, plus
device, AVD, and project info actions.

When multiple Android application modules are configured, Run asks which
runnable module and variant to use. Project info lists configured Android
application modules and marks the default module.

Use subcommands for repeatable terminal workflows:

```bash
adf build <variant-label>
adf run <variant-label>
adf apk <variant-label>
adf package <variant-label>
adf devices
adf avds
```

Variant arguments can be detected labels from `.android-dev-flow.json` or exact
Gradle variant names. If a variant is omitted, the configured `default_variant`
is used.

Useful run options:

```bash
adf run <variant-label> --serial emulator-5554
adf run <variant-label> --avd Pixel_8_API_35
adf run <variant-label> --no-launch
```

`adf apk` prints an existing generated APK path. Run `adf build` first if the
APK has not been generated yet.

## APK packaging

Use `adf package` to create a shareable APK copy and metadata file:

```bash
adf package <variant-label>
```

By default this builds first, finds the generated APK through Gradle's
`output-metadata.json`, and writes files to `dist/`:

```text
dist/MyApp-debug-v1.2.3-42.apk
dist/MyApp-debug-v1.2.3-42.txt
```

The metadata file includes project/module/variant details, application ID,
version name/code, source APK path, packaged APK path, git branch, git commit,
build timestamp, and SHA-256.

Package an existing APK without rebuilding:

```bash
adf package <variant-label> --no-build
```

Write to a custom folder:

```bash
adf package <variant-label> --output-dir /path/to/company/share
```

## Current features

- Interactive menu.
- Non-interactive commands: `build`, `run`, `apk`, `package`, `devices`, and
  `avds`.
- Project config initialization with `adf init`.
- Project config and Gradle layout validation with `adf validate`.
- Project config loading from `.android-dev-flow.json`.
- Automatic Android variant detection from module Gradle files.
- Gradle wrapper detection across Linux, macOS, and Windows.
- ADB and emulator tool detection from `ANDROID_HOME`, `ANDROID_SDK_ROOT`,
  common SDK locations, or `PATH`.
- Build a selected Gradle variant.
- Locate the generated APK through Gradle's `output-metadata.json`.
- Export shareable APK copies and metadata files with `adf package`.
- Select an online adb device, or start an installed AVD when no device is
  online.
- Install and launch the generated APK.

## Roadmap

See [ROADMAP.md](ROADMAP.md).
