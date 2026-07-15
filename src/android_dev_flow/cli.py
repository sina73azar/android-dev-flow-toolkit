from __future__ import annotations

import argparse
import sys

from . import adb
from .config import ProjectConfig, load_config
from .gradle import ApkOutput, build_variant, find_apk_output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Interactive Android and Gradle development workflow helper.")
    parser.add_argument("--project", help="Android/Gradle project directory. Defaults to current directory.")
    parser.add_argument("--variant", help="Build and run this variant without opening the menu.")
    parser.add_argument("--build-only", action="store_true", help="Build selected variant but do not install it.")
    parser.add_argument("--serial", help="Use this adb device serial.")
    parser.add_argument("--avd", help="Start/use this AVD when no device is online.")
    parser.add_argument("--no-launch", action="store_true", help="Install APK but do not launch it.")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.project)
        if args.variant:
            run_variant(config, args.variant, args.serial, args.avd, args.build_only, not args.no_launch)
            return 0

        return interactive_menu(config)
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def interactive_menu(config: ProjectConfig) -> int:
    while True:
        print()
        print(f"Android Dev Flow - {config.display_name}")
        print(f"Project: {config.project_dir}")
        print()

        actions: list[tuple[str, str | None]] = []
        for label, variant in config.variants.items():
            suffix = " (default)" if variant == config.default_variant else ""
            actions.append((f"Run {label}: {variant}{suffix}", variant))

        for index, (label, _) in enumerate(actions, start=1):
            print(f"{index}. {label}")
        print(f"{len(actions) + 1}. List devices")
        print(f"{len(actions) + 2}. List AVDs")
        print(f"{len(actions) + 3}. Project info")
        print("0. Exit")

        choice = input("> ").strip()
        if choice == "0":
            return 0

        if choice.isdigit():
            selected = int(choice)
            if 1 <= selected <= len(actions):
                variant = actions[selected - 1][1]
                assert variant is not None
                run_variant(config, variant, serial=None, avd_name=None, build_only=False, launch=True)
                continue
            if selected == len(actions) + 1:
                print_devices()
                continue
            if selected == len(actions) + 2:
                print_avds()
                continue
            if selected == len(actions) + 3:
                print_project_info(config)
                continue

        print("Unknown choice.")


def run_variant(
    config: ProjectConfig,
    variant: str,
    serial: str | None,
    avd_name: str | None,
    build_only: bool,
    launch: bool,
) -> None:
    print(f"Building variant: {variant}")
    build_variant(config.project_dir, config.module, variant)
    apk = find_apk_output(config.project_dir, config.module, variant)
    print_apk(apk)

    if build_only:
        return

    device = select_or_start_device(serial, avd_name)
    print(f"Using device: {device.serial}")
    adb.wait_for_boot(device.serial)
    adb.prepare_device(device.serial)
    adb.install_apk(device.serial, apk.path)

    if launch:
        package_name = apk.application_id or adb.package_name_from_apk(apk.path)
        if package_name:
            adb.launch_package(device.serial, package_name)
        else:
            print("Installed APK, but package name could not be detected for launch.")


def select_or_start_device(serial: str | None, avd_name: str | None) -> adb.AdbDevice:
    if serial:
        return adb.AdbDevice(serial=serial, state="device", details="selected by --serial")

    devices = adb.online_devices()
    if len(devices) == 1:
        return devices[0]
    if len(devices) > 1:
        return choose_device(devices)

    avds = adb.list_avds()
    if not avds:
        raise RuntimeError("no online adb device and no installed AVDs found")

    selected_avd = avd_name or choose_avd(avds)
    adb.start_avd(selected_avd)
    return adb.wait_for_device()


def choose_device(devices: list[adb.AdbDevice]) -> adb.AdbDevice:
    print("Select device:")
    for index, device in enumerate(devices, start=1):
        detail = f" {device.details}" if device.details else ""
        print(f"{index}. {device.serial}{detail}")
    selected = read_number(1, len(devices))
    return devices[selected - 1]


def choose_avd(avds: list[str]) -> str:
    print("Select AVD to start:")
    for index, avd_name in enumerate(avds, start=1):
        print(f"{index}. {avd_name}")
    selected = read_number(1, len(avds))
    return avds[selected - 1]


def read_number(minimum: int, maximum: int) -> int:
    while True:
        value = input("> ").strip()
        if value.isdigit():
            number = int(value)
            if minimum <= number <= maximum:
                return number
        print(f"Enter a number from {minimum} to {maximum}.")


def print_devices() -> None:
    devices = adb.list_devices()
    if not devices:
        print("No adb devices found.")
        return
    for device in devices:
        detail = f" {device.details}" if device.details else ""
        print(f"{device.serial}\t{device.state}{detail}")


def print_avds() -> None:
    avds = adb.list_avds()
    if not avds:
        print("No AVDs found.")
        return
    for avd_name in avds:
        print(avd_name)


def print_project_info(config: ProjectConfig) -> None:
    print(f"Name: {config.display_name}")
    print(f"Path: {config.project_dir}")
    print(f"Module: {config.module}")
    print(f"Default variant: {config.default_variant}")
    print("Variants:")
    for label, variant in config.variants.items():
        print(f"  {label}: {variant}")


def print_apk(apk: ApkOutput) -> None:
    print(f"APK: {apk.path}")
    if apk.application_id:
        print(f"Application ID: {apk.application_id}")
    if apk.version_name:
        print(f"Version: {apk.version_name} ({apk.version_code})")
