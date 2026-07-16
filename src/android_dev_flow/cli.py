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


MenuAction = tuple[str, str, str | None]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in {"help", "usage"}:
        return help_command(argv[1:])
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
        epilog="Commands: help, init, validate, build, run, apk, package, devices, avds. Use 'help' for full usage.",
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


def help_command(argv: list[str]) -> int:
    if not argv:
        print(usage_guide())
        return 0

    command = argv[0]
    usage = command_usage(command)
    if usage is None:
        commands = ", ".join(command_names())
        print(f"Unknown command: {command}", file=sys.stderr)
        print(f"Commands: {commands}", file=sys.stderr)
        return 1

    print(usage)
    return 0


def command_names() -> list[str]:
    return ["help", "init", "validate", "build", "run", "apk", "package", "devices", "avds"]


def usage_guide() -> str:
    return """Android Dev Flow Toolkit

Usage:
  adf
  adf help [command]
  adf init [--project DIR] [--module MODULE] [--force]
  adf validate [--project DIR]
  adf build [VARIANT] [--project DIR]
  adf run [VARIANT] [--project DIR] [--serial SERIAL] [--avd NAME] [--no-launch]
  adf apk [VARIANT] [--project DIR]
  adf package [VARIANT] [--project DIR] [--no-build] [--output-dir DIR]
  adf devices
  adf avds

Setup:
  cd /path/to/android/project
  adf init
  adf validate
  adf

Interactive menu:
  Running adf without a command opens the menu. The menu includes Run, Build,
  Show APK, and Package APK actions for each configured variant, plus device,
  AVD, and project info actions. When multiple Android application modules are
  configured, Run asks which module and variant to use.

Variants:
  VARIANT can be a detected label from .android-dev-flow.json or an exact
  Gradle variant. If omitted, default_variant is used. With \"variants\":
  \"auto\", Android variants are detected from the configured module build
  file. The default variant prefers debug when available.

Modules:
  adf init detects Android application modules and writes them to the
  "modules" list in .android-dev-flow.json. The "module" value is the default
  module used by scriptable commands and older configs. When multiple modules
  are configured, interactive Run asks which module and variant to use.

Examples:
  adf build
  adf build <variant-label>
  adf run <variant-label> --serial emulator-5554
  adf run <variant-label> --avd Pixel_8_API_35 --no-launch
  adf apk <variant-label>
  adf package <variant-label> --output-dir /path/to/company/share

Use adf help <command> for command-specific examples.""".strip()


def command_usage(command: str) -> str | None:
    usages = {
        "help": """Usage:
  adf help
  adf help <command>

Show the full usage guide or command-specific usage.

Examples:
  adf help
  adf help init
  adf help package""",
        "init": """Usage:
  adf init [--project DIR] [--name NAME] [--module MODULE] [--default-variant VARIANT] [--variant LABEL=VARIANT] [--force]

Create .android-dev-flow.json for an Android/Gradle project.

Behavior:
  - Detects project name from Gradle settings when possible.
  - Detects Android application modules and writes them to "modules".
  - Uses --module as the default module when provided; otherwise prefers app.
  - Writes \"variants\": \"auto\" unless fixed --variant mappings are provided.

Examples:
  adf init
  adf init --module app
  adf init --module mobile --force
  adf init --variant debug=debug
  adf init --variant <label>=<exactGradleVariant>""",
        "validate": """Usage:
  adf validate [--project DIR]

Validate project configuration and Gradle layout.

Checks:
  - .android-dev-flow.json schema
  - Gradle settings file
  - Gradle wrapper
  - configured module directory
  - module build file
  - configured variants/default variant

Examples:
  adf validate
  adf validate --project /path/to/android/project""",
        "build": """Usage:
  adf build [VARIANT] [--project DIR]

Build a configured Android variant and print the generated APK metadata.

Examples:
  adf build
  adf build debug
  adf build <variant-label>
  adf build <exactGradleVariant> --project /path/to/android/project""",
        "run": """Usage:
  adf run [VARIANT] [--project DIR] [--serial SERIAL] [--avd NAME] [--no-launch]

Build, install, and launch a configured Android variant.

Examples:
  adf run
  adf run debug
  adf run <variant-label> --serial emulator-5554
  adf run <variant-label> --avd Pixel_8_API_35
  adf run <variant-label> --no-launch""",
        "apk": """Usage:
  adf apk [VARIANT] [--project DIR]

Print the latest generated APK path and metadata for a configured variant.
Run adf build first if the APK has not been generated.

Examples:
  adf apk
  adf apk debug
  adf apk <variant-label>
  adf apk <exactGradleVariant>""",
        "package": """Usage:
  adf package [VARIANT] [--project DIR] [--no-build] [--output-dir DIR]

Build and export a shareable APK copy plus a metadata text file.
The metadata includes project, module, variant, app id, version, source APK,
packaged APK, git branch, git commit, timestamp, and SHA-256.

Examples:
  adf package
  adf package debug
  adf package <variant-label> --no-build
  adf package <variant-label> --output-dir /path/to/company/share""",
        "devices": """Usage:
  adf devices

List adb devices.

Example:
  adf devices""",
        "avds": """Usage:
  adf avds

List installed Android Virtual Devices.

Example:
  adf avds""",
    }
    return usages.get(command)


def init_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create .android-dev-flow.json for an Android/Gradle project.")
    parser.add_argument("--project", help="Android/Gradle project directory. Defaults to current directory.")
    parser.add_argument("--name", help="Project display name. Defaults to Gradle rootProject.name or directory name.")
    parser.add_argument("--module", help="Default Android app module. Defaults to app or the first detected app module.")
    parser.add_argument("--default-variant", help="Default Gradle variant. Defaults to detected debug variant when available.")
    parser.add_argument(
        "--variant",
        action="append",
        default=[],
        metavar="LABEL=VARIANT",
        help="Variant mapping. Can be used multiple times, for example --variant <label>=<exactGradleVariant>.",
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

        actions = menu_actions(config)

        for index, (label, _, _) in enumerate(actions, start=1):
            print(f"{index}. {label}")
        print("0. Exit")

        choice = input("> ").strip()
        if choice == "0":
            return 0

        if choice.isdigit():
            selected = int(choice)
            if 1 <= selected <= len(actions):
                run_menu_action(config, actions[selected - 1])
                continue

        print("Unknown choice.")


def menu_actions(config: ProjectConfig) -> list[MenuAction]:
    actions: list[MenuAction] = []
    for label, variant in config.variants.items():
        suffix = " (default)" if variant == config.default_variant else ""
        actions.extend(
            [
                (f"Run {label}: {variant}{suffix}", "run", variant),
                (f"Build {label}: {variant}{suffix}", "build", variant),
                (f"Show APK {label}: {variant}{suffix}", "apk", variant),
                (f"Package APK {label}: {variant}{suffix}", "package", variant),
            ]
        )

    actions.extend(
        [
            ("List devices", "devices", None),
            ("List AVDs", "avds", None),
            ("Project info", "project_info", None),
        ]
    )
    return actions


def run_menu_action(config: ProjectConfig, action: MenuAction) -> None:
    _, action_name, variant = action
    if action_name == "run":
        assert variant is not None
        run_interactive_variant(config, variant)
        return
    if action_name == "build":
        assert variant is not None
        build_selected_variant(config, variant)
        return
    if action_name == "apk":
        assert variant is not None
        print_apk(find_apk_output(config.project_dir, config.module, variant))
        return
    if action_name == "package":
        assert variant is not None
        package_selected_variant(config, variant)
        return
    if action_name == "devices":
        print_devices()
        return
    if action_name == "avds":
        print_avds()
        return
    if action_name == "project_info":
        print_project_info(config)
        return

    raise RuntimeError(f"unknown menu action: {action_name}")


def run_interactive_variant(config: ProjectConfig, variant: str) -> None:
    module_configs = runnable_module_configs(config)
    if len(module_configs) == 1:
        run_variant(config, variant, serial=None, avd_name=None, build_only=False, launch=True)
        return

    selected_config = choose_module_config(config, module_configs)
    selected_variant = choose_variant(selected_config, "Select variant to run:")
    run_variant(selected_config, selected_variant, serial=None, avd_name=None, build_only=False, launch=True)


def runnable_module_configs(config: ProjectConfig) -> list[ProjectConfig]:
    modules = list(config.application_modules)
    if not modules:
        return [config]
    return [config_for_module(config, module) for module in modules]


def config_for_module(config: ProjectConfig, module: str) -> ProjectConfig:
    if module == config.module:
        return config
    return create_default_config(config.project_dir, project_name=config.project_name, module=module)


def choose_module_config(current_config: ProjectConfig, configs: list[ProjectConfig]) -> ProjectConfig:
    print("Select Android application module:")
    for index, module_config in enumerate(configs, start=1):
        suffix = " (configured)" if module_config.module == current_config.module else ""
        print(f"{index}. {module_config.module}{suffix}")
    selected = read_number(1, len(configs))
    return configs[selected - 1]


def choose_variant(config: ProjectConfig, prompt: str) -> str:
    print(prompt)
    variants = list(config.variants.items())
    for index, (label, variant) in enumerate(variants, start=1):
        suffix = " (default)" if variant == config.default_variant else ""
        print(f"{index}. {label}: {variant}{suffix}")
    selected = read_number(1, len(variants))
    return variants[selected - 1][1]


def build_selected_variant(config: ProjectConfig, variant: str) -> ApkOutput:
    print(f"Building variant: {variant}")
    build_variant(config.project_dir, config.module, variant)
    apk = find_apk_output(config.project_dir, config.module, variant)
    print_apk(apk)
    return apk


def package_selected_variant(config: ProjectConfig, variant: str) -> PackageResult:
    print(f"Building variant: {variant}")
    build_variant(config.project_dir, config.module, variant)
    apk = find_apk_output(config.project_dir, config.module, variant)
    result = package_apk(config, apk)
    print_package_result(result)
    return result


def run_variant(
    config: ProjectConfig,
    variant: str,
    serial: str | None,
    avd_name: str | None,
    build_only: bool,
    launch: bool,
) -> None:
    apk = build_selected_variant(config, variant)

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

    modules = list(config.application_modules)
    if modules:
        print("Application modules:")
        for module in modules:
            suffix = " (configured)" if module == config.module else ""
            print(f"  {module}{suffix}")


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
