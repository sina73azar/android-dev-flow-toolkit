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
  "project_name": "RefahDpi",
  "module": "app",
  "default_variant": "developDebug",
  "variants": {
    "develop": "developDebug",
    "staging": "stagingDebug",
    "production": "productionDebug"
  }
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
possible and the default development variants:

```json
{
  "project_name": "RefahDpi",
  "module": "app",
  "default_variant": "developDebug",
  "variants": {
    "develop": "developDebug",
    "staging": "stagingDebug",
    "production": "productionDebug"
  }
}
```

You can customize values during initialization:

```bash
adf init \
  --name RefahDpi \
  --module app \
  --default-variant developDebug \
  --variant develop=developDebug \
  --variant staging=stagingDebug \
  --variant production=productionDebug
```

Overwrite an existing config only when intended:

```bash
adf init --force
```

Validate project setup before building or running:

```bash
adf validate
```

## Current features

- Interactive menu.
- Project config initialization with `adf init`.
- Project config and Gradle layout validation with `adf validate`.
- Project config loading from `.android-dev-flow.json`.
- Gradle wrapper detection across Linux, macOS, and Windows.
- ADB and emulator tool detection from `ANDROID_HOME`, `ANDROID_SDK_ROOT`,
  common SDK locations, or `PATH`.
- Build a selected Gradle variant.
- Locate the generated APK through Gradle's `output-metadata.json`.
- Select an online adb device, or start an installed AVD when no device is
  online.
- Install and launch the generated APK.

## Roadmap

See [ROADMAP.md](ROADMAP.md).
