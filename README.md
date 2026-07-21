# Android Dev Flow Toolkit

`adf` is a cross-platform CLI for common Android development work: selecting a
variant and device, building with the Gradle wrapper, installing and launching
the APK, and preparing APKs for sharing.

It supports Linux, macOS, and Windows and has no runtime Python dependencies.

## Requirements

Before installing, make sure the machine has:

- Python 3.10 or newer.
- A JDK compatible with the Android project's Gradle version.
- Android Studio or the Android SDK command-line tools.
- The required SDK platforms, build tools, emulator images, and device drivers.
- `adb` and `emulator`, either under `ANDROID_HOME`/`ANDROID_SDK_ROOT`, in a
  standard SDK location, or on `PATH`.
- Access to the Android project's Git repository.

Useful checks:

```bash
python3 --version
java -version
adb version
```

On Windows, use `py --version` if `python3` is unavailable.

## Clean global installation

The recommended installation uses
[pipx](https://pipx.pypa.io/stable/how-to/install-pipx.html). It installs `adf`
in an isolated environment and exposes the command globally. Do not clone this
toolkit or activate a virtual environment for normal use.

### Linux

On Ubuntu 23.04 or newer:

```bash
sudo apt update
sudo apt install python3 python3-venv pipx
pipx ensurepath
```

Open a new terminal, then install and verify the toolkit:

```bash
pipx install "https://github.com/sina73azar/android-dev-flow-toolkit/archive/refs/tags/v0.1.0.zip"
adf --version
```

For other Linux distributions, install Python 3.10+ and pipx with the system
package manager, then run the same `pipx ensurepath` and `pipx install`
commands.

### macOS

Using Homebrew:

```bash
brew install python pipx
pipx ensurepath
```

Open a new terminal, then install and verify the toolkit:

```bash
pipx install "https://github.com/sina73azar/android-dev-flow-toolkit/archive/refs/tags/v0.1.0.zip"
adf --version
```

### Windows PowerShell

Install Python 3.10 or newer first. The Python launcher (`py`) should be
available in PowerShell.

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
```

Open a new PowerShell window, then install and verify the toolkit:

```powershell
pipx install "https://github.com/sina73azar/android-dev-flow-toolkit/archive/refs/tags/v0.1.0.zip"
adf --version
```

If `adf` is not found after installation, open a new terminal and run
`pipx ensurepath` again.

## Configure an Android project

Only one maintainer needs to perform this setup for each Android repository.
From the project root:

```bash
adf init
adf validate
adf wrapper
```

`adf init` detects the project name, application modules, and common Android
variants. Review `.android-dev-flow.json` before committing it.

For a project with develop, staging, and production debug variants, an explicit
configuration can look like this:

```json
{
  "project_name": "MyApp",
  "module": "app",
  "modules": [
    "app"
  ],
  "default_variant": "developDebug",
  "variants": {
    "develop": "developDebug",
    "staging": "stagingDebug",
    "production": "productionDebug"
  }
}
```

Alternatively, keep `"variants": "auto"` to detect variants from the module's
Gradle build file.

Commit these files to the Android repository:

```text
.android-dev-flow.json
adfw
adfw.bat
.adf/wrapper/adf.pyz
.adf/wrapper/version.txt
```

The committed wrapper pins the toolkit version used by the project. Teammates
who use the wrapper do not need a global `adf` installation; they only need
Python 3.10+ and the Android/JDK requirements above.

## Teammate workflow

After cloning the configured Android project:

```bash
# Linux and macOS
./adfw validate
./adfw
```

```powershell
# Windows
adfw.bat validate
adfw.bat
```

Running the wrapper without a command opens the interactive menu. Scriptable
examples are:

```bash
./adfw build develop
./adfw run develop
./adfw run staging --serial emulator-5554
./adfw run production --no-launch
./adfw apk develop
./adfw package staging
./adfw devices
./adfw avds
```

On Windows, replace `./adfw` with `adfw.bat`. A variant argument may be a label
from `.android-dev-flow.json` or an exact Gradle variant. Omitting it uses the
configured default variant.

## Global CLI usage

Users who installed the toolkit globally can run the same commands with `adf`:

```bash
adf
adf validate
adf build develop
adf run staging
adf package production
adf help
adf help run
```

Useful run options:

```bash
adf run develop --serial emulator-5554
adf run develop --avd Pixel_8_API_35
adf run develop --no-launch
```

`adf package` builds by default and writes a shareable APK plus a metadata file
to `dist/`. Use `--no-build` to package an existing APK or `--output-dir DIR`
to choose another destination.

## Upgrade

Replace `v0.1.0` in the install URL with the desired published release tag,
then reinstall it. For example, reinstalling `v0.1.0` uses:

```bash
pipx install --force "https://github.com/sina73azar/android-dev-flow-toolkit/archive/refs/tags/v0.1.0.zip"
adf --version
```

To update the version pinned in an Android repository:

```bash
cd /path/to/android/project
adf wrapper --force
```

Review and commit the changed wrapper files. Teammates receive the upgrade when
they update the Android repository.

## Uninstall

Remove a global installation with:

```bash
pipx uninstall android-dev-flow-toolkit
```

Project wrappers remain available because they are committed to each Android
repository.

## Toolkit development

For contributors working on this repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
python -m unittest discover -v
```

On Windows, activate with `.venv\Scripts\Activate.ps1`.

See [ROADMAP.md](ROADMAP.md) for planned work and [CHANGELOG.md](CHANGELOG.md)
for released changes. This project is licensed under the [MIT License](LICENSE).
