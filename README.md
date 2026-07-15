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

Or after installing in editable mode:

```bash
python3 -m pip install -e .
adf --project /path/to/android/project
```

Inside an Android project, create `.android-dev-flow.json`:

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

## Current features

- Interactive menu.
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
