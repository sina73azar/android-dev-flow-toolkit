from __future__ import annotations

import time
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .process import capture, run
from .tools import find_aapt, require_android_tool


@dataclass(frozen=True)
class AdbDevice:
    serial: str
    state: str
    details: str


def adb_path() -> Path:
    return require_android_tool("adb")


def emulator_path() -> Path:
    return require_android_tool("emulator")


def list_devices() -> list[AdbDevice]:
    output = capture([str(adb_path()), "devices", "-l"], check=False)
    devices: list[AdbDevice] = []
    for line in output.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=2)
        serial = parts[0]
        state = parts[1] if len(parts) > 1 else "unknown"
        details = parts[2] if len(parts) > 2 else ""
        devices.append(AdbDevice(serial=serial, state=state, details=details))
    return devices


def online_devices() -> list[AdbDevice]:
    return [device for device in list_devices() if device.state == "device"]


def list_avds() -> list[str]:
    output = capture([str(emulator_path()), "-list-avds"], check=False)
    return [line.strip() for line in output.splitlines() if line.strip()]


def start_avd(avd_name: str) -> None:
    log_file = Path(tempfile.gettempdir()) / f"android-dev-flow-toolkit-{avd_name}.log"
    print(f"Starting AVD {avd_name}")
    print(f"Emulator log: {log_file}")
    popen_kwargs = {}
    if sys.platform.startswith("win"):
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    with log_file.open("w", encoding="utf-8") as log_handle:
        subprocess.Popen(
            [str(emulator_path()), "-avd", avd_name],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            **popen_kwargs,
        )


def wait_for_device(timeout_seconds: int = 180) -> AdbDevice:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        devices = online_devices()
        if devices:
            return devices[0]
        time.sleep(2)
    raise RuntimeError(f"no online adb device appeared within {timeout_seconds} seconds")


def wait_for_boot(serial: str, timeout_seconds: int = 180) -> None:
    adb = str(adb_path())
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        value = capture([adb, "-s", serial, "shell", "getprop", "sys.boot_completed"], check=False).strip()
        if value == "1":
            return
        time.sleep(2)
    raise RuntimeError(f"device {serial} did not finish booting within {timeout_seconds} seconds")


def prepare_device(serial: str) -> None:
    adb = str(adb_path())
    commands = [
        ["shell", "input", "keyevent", "KEYCODE_WAKEUP"],
        ["shell", "input", "keyevent", "KEYCODE_MENU"],
        ["shell", "settings", "put", "global", "stay_on_while_plugged_in", "3"],
        ["shell", "settings", "put", "global", "window_animation_scale", "0"],
        ["shell", "settings", "put", "global", "transition_animation_scale", "0"],
        ["shell", "settings", "put", "global", "animator_duration_scale", "0"],
    ]
    for command in commands:
        run([adb, "-s", serial, *command], check=False)


def install_apk(serial: str, apk_path: Path) -> None:
    run([str(adb_path()), "-s", serial, "install", "-r", str(apk_path)])


def package_name_from_apk(apk_path: Path) -> str | None:
    aapt = find_aapt()
    if aapt is None:
        return None
    output = capture([str(aapt), "dump", "badging", str(apk_path)], check=False)
    for line in output.splitlines():
        if line.startswith("package: name='"):
            return line.split("'", 2)[1]
    return None


def launch_package(serial: str, package_name: str) -> None:
    run(
        [
            str(adb_path()),
            "-s",
            serial,
            "shell",
            "monkey",
            "-p",
            package_name,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ]
    )
