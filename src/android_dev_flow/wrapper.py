from __future__ import annotations

import os
import shutil
import stat
import tempfile
import zipapp
from dataclasses import dataclass
from pathlib import Path

from . import __version__


WRAPPER_DIR = Path(".adf") / "wrapper"
ARCHIVE_NAME = "adf.pyz"
VERSION_NAME = "version.txt"


class WrapperError(RuntimeError):
    pass


@dataclass(frozen=True)
class WrapperResult:
    unix_launcher: Path
    windows_launcher: Path
    archive: Path
    version_file: Path


def create_project_wrapper(project_dir: Path, *, overwrite: bool = False) -> WrapperResult:
    project_dir = project_dir.expanduser().resolve()
    if not project_dir.is_dir():
        raise WrapperError(f"project directory does not exist: {project_dir}")

    result = WrapperResult(
        unix_launcher=project_dir / "adfw",
        windows_launcher=project_dir / "adfw.bat",
        archive=project_dir / WRAPPER_DIR / ARCHIVE_NAME,
        version_file=project_dir / WRAPPER_DIR / VERSION_NAME,
    )
    existing = [path for path in wrapper_paths(result) if path.exists()]
    if existing and not overwrite:
        paths = ", ".join(str(path.relative_to(project_dir)) for path in existing)
        raise WrapperError(f"wrapper files already exist: {paths}. Use --force to replace them")

    result.archive.parent.mkdir(parents=True, exist_ok=True)
    build_wrapper_archive(result.archive)
    result.version_file.write_text(f"{__version__}\n", encoding="utf-8")
    result.unix_launcher.write_text(unix_launcher_text(), encoding="utf-8", newline="\n")
    result.windows_launcher.write_text(windows_launcher_text(), encoding="utf-8", newline="")
    make_executable(result.unix_launcher)
    return result


def build_wrapper_archive(target: Path) -> None:
    package_dir = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="adf-wrapper-") as temporary:
        archive_root = Path(temporary) / "archive"
        bundled_package = archive_root / package_dir.name
        shutil.copytree(package_dir, bundled_package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

        temporary_archive = Path(temporary) / ARCHIVE_NAME
        zipapp.create_archive(
            archive_root,
            target=temporary_archive,
            main="android_dev_flow.cli:main",
            compressed=True,
        )
        os.replace(temporary_archive, target)


def wrapper_paths(result: WrapperResult) -> tuple[Path, ...]:
    return result.unix_launcher, result.windows_launcher, result.archive, result.version_file


def make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def unix_launcher_text() -> str:
    return """#!/usr/bin/env sh
set -eu

ADF_PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if command -v python3 >/dev/null 2>&1; then
    ADF_PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    ADF_PYTHON=python
else
    echo "Android Dev Flow requires Python 3.10 or newer." >&2
    exit 1
fi

cd "$ADF_PROJECT_DIR"
exec "$ADF_PYTHON" "$ADF_PROJECT_DIR/.adf/wrapper/adf.pyz" "$@"
"""


def windows_launcher_text() -> str:
    return """@echo off\r
setlocal\r
set "ADF_PROJECT_DIR=%~dp0"\r
pushd "%ADF_PROJECT_DIR%"\r
where py >nul 2>nul\r
if %errorlevel% equ 0 goto use_py\r
where python >nul 2>nul\r
if %errorlevel% equ 0 goto use_python\r
echo Android Dev Flow requires Python 3.10 or newer. 1>&2\r
popd\r
exit /b 1\r
\r
:use_py\r
py -3 "%ADF_PROJECT_DIR%.adf\\wrapper\\adf.pyz" %*\r
goto finish\r
\r
:use_python\r
python "%ADF_PROJECT_DIR%.adf\\wrapper\\adf.pyz" %*\r
\r
:finish\r
set "ADF_EXIT_CODE=%errorlevel%"\r
popd\r
exit /b %ADF_EXIT_CODE%\r
"""
