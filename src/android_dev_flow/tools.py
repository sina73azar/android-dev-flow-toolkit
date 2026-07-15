from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def executable_name(name: str) -> str:
    if sys.platform.startswith("win") and not name.endswith(".exe"):
        return f"{name}.exe"
    return name


def find_android_tool(name: str) -> Path | None:
    executable = executable_name(name)
    sdk_roots: list[Path] = []

    for env_name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        value = os.environ.get(env_name)
        if value:
            sdk_roots.append(Path(value).expanduser())

    home = Path.home()
    sdk_roots.extend(
        [
            home / "Android" / "Sdk",
            home / "Library" / "Android" / "sdk",
            home / "AppData" / "Local" / "Android" / "Sdk",
        ]
    )

    for root in sdk_roots:
        for relative in ("emulator", "platform-tools", "tools"):
            candidate = root / relative / executable
            if candidate.is_file():
                return candidate

    from_path = shutil.which(name)
    if from_path:
        return Path(from_path)

    return None


def require_android_tool(name: str) -> Path:
    path = find_android_tool(name)
    if path is None:
        raise RuntimeError(f"could not find Android SDK tool: {name}")
    return path


def find_aapt() -> Path | None:
    sdk_roots: list[Path] = []
    for env_name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        value = os.environ.get(env_name)
        if value:
            sdk_roots.append(Path(value).expanduser())

    home = Path.home()
    sdk_roots.extend(
        [
            home / "Android" / "Sdk",
            home / "Library" / "Android" / "sdk",
            home / "AppData" / "Local" / "Android" / "Sdk",
        ]
    )

    executable = executable_name("aapt")
    for root in sdk_roots:
        build_tools = root / "build-tools"
        if not build_tools.is_dir():
            continue
        for version_dir in sorted(build_tools.iterdir(), reverse=True):
            candidate = version_dir / executable
            if candidate.is_file():
                return candidate

    from_path = shutil.which("aapt")
    if from_path:
        return Path(from_path)

    return None
