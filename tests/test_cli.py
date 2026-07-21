from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from android_dev_flow.apk_package import PackageResult
from android_dev_flow.cli import (
    apk_command,
    build_command,
    command_usage,
    help_command,
    menu_actions,
    package_command,
    parse_variant_args,
    print_project_info,
    resolve_output_dir,
    resolve_variant,
    run_menu_action,
    run_command,
    wrapper_command,
)
from android_dev_flow.config import ConfigError, ProjectConfig
from android_dev_flow.gradle import ApkOutput


class CliTests(unittest.TestCase):
    def test_resolve_variant_uses_default_when_missing(self) -> None:
        config = sample_config()

        self.assertEqual(resolve_variant(config, None), "qaDebug")

    def test_resolve_variant_accepts_label(self) -> None:
        config = sample_config()

        self.assertEqual(resolve_variant(config, "demo"), "demoDebug")

    def test_resolve_variant_accepts_exact_variant(self) -> None:
        config = sample_config()

        self.assertEqual(resolve_variant(config, "internalDebug"), "internalDebug")

    def test_resolve_variant_rejects_unknown_variant(self) -> None:
        config = sample_config()

        with self.assertRaises(ConfigError):
            resolve_variant(config, "release")

    def test_parse_variant_args_accepts_label_variant_pairs(self) -> None:
        self.assertEqual(
            parse_variant_args(["qa=qaDebug", "demo=demoDebug"]),
            {"qa": "qaDebug", "demo": "demoDebug"},
        )

    def test_parse_variant_args_rejects_values_without_separator(self) -> None:
        with self.assertRaises(ConfigError):
            parse_variant_args(["qaDebug"])

    def test_build_command_resolves_label_before_building(self) -> None:
        config = sample_config()
        apk = sample_apk()

        with (
            patch("builtins.print"),
            patch("android_dev_flow.cli.load_valid_config", return_value=config),
            patch("android_dev_flow.cli.build_variant") as build_variant,
            patch("android_dev_flow.cli.find_apk_output", return_value=apk),
            patch("android_dev_flow.cli.print_apk"),
        ):
            status = build_command(["demo", "--project", "/tmp/sample-app"])

        self.assertEqual(status, 0)
        build_variant.assert_called_once_with(config.project_dir, config.module, "demoDebug")

    def test_run_command_uses_default_variant_and_no_launch_flag(self) -> None:
        config = sample_config()

        with (
            patch("android_dev_flow.cli.load_valid_config", return_value=config),
            patch("android_dev_flow.cli.run_variant") as run_variant,
        ):
            status = run_command(["--no-launch"])

        self.assertEqual(status, 0)
        run_variant.assert_called_once_with(config, "qaDebug", None, None, build_only=False, launch=False)

    def test_apk_command_resolves_exact_variant(self) -> None:
        config = sample_config()
        apk = sample_apk()

        with (
            patch("android_dev_flow.cli.load_valid_config", return_value=config),
            patch("android_dev_flow.cli.find_apk_output", return_value=apk) as find_apk_output,
            patch("android_dev_flow.cli.print_apk"),
        ):
            status = apk_command(["internalDebug"])

        self.assertEqual(status, 0)
        find_apk_output.assert_called_once_with(config.project_dir, config.module, "internalDebug")

    def test_package_command_builds_by_default(self) -> None:
        config = sample_config()
        apk = sample_apk()
        result = sample_package_result()

        with (
            patch("builtins.print"),
            patch("android_dev_flow.cli.load_valid_config", return_value=config),
            patch("android_dev_flow.cli.build_variant") as build_variant,
            patch("android_dev_flow.cli.find_apk_output", return_value=apk),
            patch("android_dev_flow.cli.package_apk", return_value=result) as package_apk,
        ):
            status = package_command(["qa"])

        self.assertEqual(status, 0)
        build_variant.assert_called_once_with(config.project_dir, config.module, "qaDebug")
        package_apk.assert_called_once_with(config, apk, output_dir=None)

    def test_package_command_can_skip_build_and_use_output_dir(self) -> None:
        config = sample_config()
        apk = sample_apk()
        result = sample_package_result()
        output_dir = config.project_dir / "shared"

        with (
            patch("builtins.print"),
            patch("android_dev_flow.cli.load_valid_config", return_value=config),
            patch("android_dev_flow.cli.build_variant") as build_variant,
            patch("android_dev_flow.cli.find_apk_output", return_value=apk),
            patch("android_dev_flow.cli.package_apk", return_value=result) as package_apk,
        ):
            status = package_command(["demo", "--no-build", "--output-dir", "shared"])

        self.assertEqual(status, 0)
        build_variant.assert_not_called()
        package_apk.assert_called_once_with(config, apk, output_dir=output_dir)

    def test_resolve_output_dir_keeps_absolute_paths(self) -> None:
        config = sample_config()

        self.assertEqual(resolve_output_dir(config, "/tmp/shared"), Path("/tmp/shared"))

    def test_menu_actions_include_scriptable_variant_workflows(self) -> None:
        labels = [label for label, _, _ in menu_actions(sample_config())]

        self.assertIn("Run qa: qaDebug (default)", labels)
        self.assertIn("Build qa: qaDebug (default)", labels)
        self.assertIn("Show APK qa: qaDebug (default)", labels)
        self.assertIn("Package APK qa: qaDebug (default)", labels)
        self.assertIn("List devices", labels)
        self.assertIn("List AVDs", labels)
        self.assertIn("Project info", labels)

    def test_run_menu_action_dispatches_build(self) -> None:
        config = sample_config()

        with patch("android_dev_flow.cli.build_selected_variant") as build_selected_variant:
            run_menu_action(config, ("Build qa: qaDebug", "build", "qaDebug"))

        build_selected_variant.assert_called_once_with(config, "qaDebug")

    def test_run_menu_action_dispatches_apk_lookup(self) -> None:
        config = sample_config()
        apk = sample_apk()

        with (
            patch("android_dev_flow.cli.find_apk_output", return_value=apk) as find_apk_output,
            patch("android_dev_flow.cli.print_apk") as print_apk,
        ):
            run_menu_action(config, ("Show APK qa: qaDebug", "apk", "qaDebug"))

        find_apk_output.assert_called_once_with(config.project_dir, config.module, "qaDebug")
        print_apk.assert_called_once_with(apk)

    def test_run_menu_action_dispatches_package(self) -> None:
        config = sample_config()

        with patch("android_dev_flow.cli.package_selected_variant") as package_selected_variant:
            run_menu_action(config, ("Package APK qa: qaDebug", "package", "qaDebug"))

        package_selected_variant.assert_called_once_with(config, "qaDebug")

    def test_run_menu_action_prompts_for_module_and_variant_when_multiple_modules_exist(self) -> None:
        config = sample_config(application_modules=("app", "demo"))
        demo_config = ProjectConfig(
            project_dir=config.project_dir,
            project_name=config.project_name,
            module="demo",
            default_variant="debug",
            variants={"debug": "debug", "release": "release"},
            application_modules=("demo",),
            auto_detect_variants=True,
        )

        with (
            patch("android_dev_flow.cli.create_default_config", return_value=demo_config),
            patch("builtins.input", side_effect=["2", "2"]),
            patch("builtins.print"),
            patch("android_dev_flow.cli.run_variant") as run_variant,
        ):
            run_menu_action(config, ("Run qa: qaDebug", "run", "qaDebug"))

        run_variant.assert_called_once_with(demo_config, "release", serial=None, avd_name=None, build_only=False, launch=True)

    def test_print_project_info_lists_detected_application_modules(self) -> None:
        config = sample_config(application_modules=("app", "demo"))

        with patch("builtins.print") as print_mock:
            print_project_info(config)

        lines = [call.args[0] for call in print_mock.call_args_list]
        self.assertIn("Application modules:", lines)
        self.assertIn("  app (configured)", lines)
        self.assertIn("  demo", lines)

    def test_help_command_prints_full_usage(self) -> None:
        with patch("builtins.print") as print_mock:
            status = help_command([])

        self.assertEqual(status, 0)
        output = print_mock.call_args.args[0]
        self.assertIn("Android Dev Flow Toolkit", output)
        self.assertIn("adf init", output)
        self.assertIn("adf package", output)
        self.assertNotIn("qa", output)
        self.assertNotIn("demo", output)
        self.assertNotIn("internal", output)

    def test_help_command_prints_command_usage(self) -> None:
        with patch("builtins.print") as print_mock:
            status = help_command(["package"])

        self.assertEqual(status, 0)
        output = print_mock.call_args.args[0]
        self.assertIn("adf package [VARIANT]", output)
        self.assertIn("--output-dir", output)

    def test_help_command_rejects_unknown_command(self) -> None:
        with patch("builtins.print") as print_mock:
            status = help_command(["missing"])

        self.assertEqual(status, 1)
        self.assertEqual(print_mock.call_count, 2)

    def test_command_usage_exists_for_all_public_commands(self) -> None:
        for command in ("help", "init", "validate", "build", "run", "apk", "package", "devices", "avds", "wrapper"):
            self.assertIsNotNone(command_usage(command))

    def test_wrapper_command_creates_project_wrapper(self) -> None:
        with (
            patch("android_dev_flow.cli.create_project_wrapper") as create_wrapper,
            patch("builtins.print"),
        ):
            project_dir = Path("/tmp/sample-app").resolve()
            create_wrapper.return_value.unix_launcher = project_dir / "adfw"
            create_wrapper.return_value.windows_launcher = project_dir / "adfw.bat"
            create_wrapper.return_value.archive = project_dir / ".adf/wrapper/adf.pyz"
            create_wrapper.return_value.version_file = project_dir / ".adf/wrapper/version.txt"

            status = wrapper_command(["--project", str(project_dir), "--force"])

        self.assertEqual(status, 0)
        create_wrapper.assert_called_once_with(project_dir, overwrite=True)


def sample_config(application_modules: tuple[str, ...] = ("app",)) -> ProjectConfig:
    return ProjectConfig(
        project_dir=Path("/tmp/sample-app"),
        project_name="SampleApp",
        module="app",
        default_variant="qaDebug",
        variants={
            "qa": "qaDebug",
            "demo": "demoDebug",
            "internal": "internalDebug",
        },
        application_modules=application_modules,
    )


def sample_apk() -> ApkOutput:
    return ApkOutput(
        path=Path("/tmp/sample-app/app/build/outputs/apk/qa/debug/app.apk"),
        variant_name="qaDebug",
        application_id="com.example.sample",
        version_name="1.0",
        version_code=1,
    )


def sample_package_result() -> PackageResult:
    return PackageResult(
        apk_path=Path("/tmp/sample-app/dist/SampleApp-qaDebug-v1.0-1.apk"),
        metadata_path=Path("/tmp/sample-app/dist/SampleApp-qaDebug-v1.0-1.txt"),
        sha256="abc123",
    )


if __name__ == "__main__":
    unittest.main()
