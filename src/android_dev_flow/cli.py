from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import adb
from .apk_package import PackageResult, package_apk
from .config import (
    ConfigError,
    ProjectConfig,
    ValidationResult,
    create_default_config,
    load_config,
    validate_project,
    write_config,
)
from .gradle import ApkOutput, build_variant, find_apk_output


class ProjectValidationError(RuntimeError):
    pass


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "init":
        return init_command(argv[1:])
    if argv and argv[0] == "validate":
        return validate_command(argv[1:])
    if argv and argv[0] == "build":
        return build_command(argv[1:])
    if argv and argv[0] == "run":
        return run_command(argv[1:])
    if argv and argv[0] == "apk":
        return apk_command(argv[1:])
    if argv and argv[0] == "package":
        return package_command(argv[1:])
    if argv and argv[0] == "devices":
        return devices_command(argv[1:])
    if argv and argv[0] == "avds":
        return avds_command(argv[1:])

    parser = argparse.ArgumentParser(
        description="Interactive Android and Gradle development workflow helper.",
        epilog="Commands: init, validate, build, run, apk, package, devices, avds. Use '<command> --help' for details.",
    )
    parser.add_argument("--project", help="Android/Gradle project directory. Defaults to current directory.")
    parser.add_argument("--variant", help="Build and run this variant label or exact Gradle variant without opening the menu.")
    parser.add_argument("--build-only", action="store_true", help="Build selected variant but do not install it.")
    parser.add_argument("--serial", help="Use this adb device serial.")
    parser.add_argument("--avd", help="Start/use this AVD when no device is online.")
    parser.add_argument("--no-launch", action="store_true", help="Install APK but do not launch it.")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.project)
        validation = validate_project(config)
        if not validation.ok:
            print_validation(validation)
            return 1

        if args.variant:
            variant = resolve_variant(config, args.variant)
            run_variant(config, variant, args.serial, args.avd, args.build_only, not args.no_launch)
            return 0

        return interactive_menu(config)
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except ProjectValidationError:
        return 1
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def init_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create .android-dev-flow.json for an Android/Gradle project.")
    parser.add_argument("--project", help="Android/Gradle project directory. Defaults to current directory.")
    parser.add_argument("--name", help="Project display name. Defaults to Gradle rootProject.name or directory name.")
    parser.add_argument("--module", help="Android app module. Defaults to detected app module or app.")
    parser.add_argument("--default-variant", default="developDebug", help="Default Gradle variant.")
    parser.add_argument(
        "--variant",
        action="append",
        default=[],
        metavar="LABEL=VARIANT",
        help="Variant mapping. Can be used multiple times, for example --variant develop=developDebug.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing .android-dev-flow.json.")
    args = parser.parse_args(argv)

    try:
        project_dir = Path(args.project).expanduser().resolve() if args.project else Path.cwd().resolve()
        variants = parse_variant_args(args.variant) if args.variant else None
        config = create_default_config(
            project_dir,
            project_name=args.name,
            module=args.module,
            default_variant=args.default_variant,
            variants=variants,
        )
        config_file = write_config(config, overwrite=args.force)
        print(f"Created config: {config_file}")
        print_project_info(config)

        validation = validate_project(config)
        print_validation(validation)
        return 0 if validation.ok else 1
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except ProjectValidationError:
        return 1
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def validate_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate android-dev-flow project configuration.")
    parser.add_argument("--project", help="Android/Gradle project directory. Defaults to current directory.")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.project)
        print_project_info(config)
        validation = validate_project(config)
        print_validation(validation)
        return 0 if validation.ok else 1
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except ProjectValidationError:
        return 1
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def build_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build a configured Android variant.")
    add_project_argument(parser)
    parser.add_argument("variant", nargs="?", help="Variant label or exact Gradle variant. Defaults to configured default.")
    args = parser.parse_args(argv)

    try:
        config = load_valid_config(args.project)
        variant = resolve_variant(config, args.variant)
        print(f"Building variant: {variant}")
        build_variant(config.project_dir, config.module, variant)
        print_apk(find_apk_output(config.project_dir, config.module, variant))
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except ProjectValidationError:
        return 1
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def run_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build, install, and launch a configured Android variant.")
    add_project_argument(parser)
    parser.add_argument("variant", nargs="?", help="Variant label or exact Gradle variant. Defaults to configured default.")
    parser.add_argument("--serial", help="Use this adb device serial.")
    parser.add_argument("--avd", help="Start/use this AVD when no device is online.")
    parser.add_argument("--no-launch", action="store_true", help="Install APK but do not launch it.")
    args = parser.parse_args(argv)

    try:
        config = load_valid_config(args.project)
        variant = resolve_variant(config, args.variant)
        run_variant(config, variant, args.serial, args.avd, build_only=False, launch=not args.no_launch)
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except ProjectValidationError:
        return 1
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def apk_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Print the generated APK path for a configured Android variant.")
    add_project_argument(parser)
    parser.add_argument("variant", nargs="?", help="Variant label or exact Gradle variant. Defaults to configured default.")
    args = parser.parse_args(argv)

    try:
        config = load_valid_config(args.project)
        variant = resolve_variant(config, args.variant)
        print_apk(find_apk_output(config.project_dir, config.module, variant))
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except ProjectValidationError:
        return 1
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def package_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build and export a shareable APK package.")
    add_project_argument(parser)
    parser.add_argument("variant", nargs="?", help="Variant label or exact Gradle variant. Defaults to configured default.")
    parser.add_argument("--no-build", action="store_true", help="Package the latest existing APK without building first.")
    parser.add_argument("--output-dir", help="Directory for exported APK and metadata. Defaults to project dist/.")
    args = parser.parse_args(argv)

    try:
        config = load_valid_config(args.project)
        variant = resolve_variant(config, args.variant)
        if not args.no_build:
            print(f"Building variant: {variant}")
            build_variant(config.project_dir, config.module, variant)

        apk = find_apk_output(config.project_dir, config.module, variant)
        result = package_apk(config, apk, output_dir=resolve_output_dir(config, args.output_dir))
        print_package_result(result)
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except ProjectValidationError:
        return 1
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def devices_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="List adb devices.")
    parser.parse_args(argv)

    try:
        print_devices()
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def avds_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="List installed Android Virtual Devices.")
    parser.parse_args(argv)

    try:
        print_avds()
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def add_project_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", help="Android/Gradle project directory. Defaults to current directory.")


def resolve_output_dir(config: ProjectConfig, output_dir: str | None) -> Path | None:
    if output_dir is None:
        return None

    path = Path(output_dir).expanduser()
    if path.is_absolute():
        return path
    return config.project_dir / path


def load_valid_config(project_arg: str | None) -> ProjectConfig:
    config = load_config(project_arg)
    validation = validate_project(config)
    if not validation.ok:
        print_validation(validation)
        raise ProjectValidationError("project validation failed")
    return config


def resolve_variant(config: ProjectConfig, requested: str | None) -> str:
    if requested is None:
        return config.default_variant
    if requested in config.variants:
        return config.variants[requested]
    if requested in config.variants.values():
        return requested

    choices = ", ".join([*config.variants.keys(), *config.variants.values()])
    raise ConfigError(f"unknown variant {requested!r}. Expected one of: {choices}")


def parse_variant_args(values: list[str]) -> dict[str, str]:
    variants: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ConfigError(f"variant must use LABEL=VARIANT format: {value}")
        label, variant = value.split("=", 1)
        label = label.strip()
        variant = variant.strip()
        if not label or not variant:
            raise ConfigError(f"variant must use LABEL=VARIANT format: {value}")
        variants[label] = variant
    return variants


def print_validation(validation: ValidationResult) -> None:
    if validation.errors:
        print("Validation errors:")
        for error in validation.errors:
            print(f"  - {error}")
    if validation.warnings:
        print("Validation warnings:")
        for warning in validation.warnings:
            print(f"  - {warning}")
    if validation.ok:
        print("Validation passed.")


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


def print_package_result(result: PackageResult) -> None:
    print(f"Packaged APK: {result.apk_path}")
    print(f"Metadata: {result.metadata_path}")
    print(f"SHA-256: {result.sha256}")
