from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from android_dev_flow.cli import apk_command, build_command, parse_variant_args, resolve_variant, run_command
from android_dev_flow.config import ConfigError, ProjectConfig
from android_dev_flow.gradle import ApkOutput


class CliTests(unittest.TestCase):
    def test_resolve_variant_uses_default_when_missing(self) -> None:
        config = sample_config()

        self.assertEqual(resolve_variant(config, None), "developDebug")

    def test_resolve_variant_accepts_label(self) -> None:
        config = sample_config()

        self.assertEqual(resolve_variant(config, "staging"), "stagingDebug")

    def test_resolve_variant_accepts_exact_variant(self) -> None:
        config = sample_config()

        self.assertEqual(resolve_variant(config, "productionDebug"), "productionDebug")

    def test_resolve_variant_rejects_unknown_variant(self) -> None:
        config = sample_config()

        with self.assertRaises(ConfigError):
            resolve_variant(config, "release")

    def test_parse_variant_args_accepts_label_variant_pairs(self) -> None:
        self.assertEqual(
            parse_variant_args(["develop=developDebug", "staging=stagingDebug"]),
            {"develop": "developDebug", "staging": "stagingDebug"},
        )

    def test_parse_variant_args_rejects_values_without_separator(self) -> None:
        with self.assertRaises(ConfigError):
            parse_variant_args(["developDebug"])

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
            status = build_command(["staging", "--project", "/tmp/sample-app"])

        self.assertEqual(status, 0)
        build_variant.assert_called_once_with(config.project_dir, config.module, "stagingDebug")

    def test_run_command_uses_default_variant_and_no_launch_flag(self) -> None:
        config = sample_config()

        with (
            patch("android_dev_flow.cli.load_valid_config", return_value=config),
            patch("android_dev_flow.cli.run_variant") as run_variant,
        ):
            status = run_command(["--no-launch"])

        self.assertEqual(status, 0)
        run_variant.assert_called_once_with(config, "developDebug", None, None, build_only=False, launch=False)

    def test_apk_command_resolves_exact_variant(self) -> None:
        config = sample_config()
        apk = sample_apk()

        with (
            patch("android_dev_flow.cli.load_valid_config", return_value=config),
            patch("android_dev_flow.cli.find_apk_output", return_value=apk) as find_apk_output,
            patch("android_dev_flow.cli.print_apk"),
        ):
            status = apk_command(["productionDebug"])

        self.assertEqual(status, 0)
        find_apk_output.assert_called_once_with(config.project_dir, config.module, "productionDebug")


def sample_config() -> ProjectConfig:
    return ProjectConfig(
        project_dir=Path("/tmp/sample-app"),
        project_name="SampleApp",
        module="app",
        default_variant="developDebug",
        variants={
            "develop": "developDebug",
            "staging": "stagingDebug",
            "production": "productionDebug",
        },
    )


def sample_apk() -> ApkOutput:
    return ApkOutput(
        path=Path("/tmp/sample-app/app/build/outputs/apk/develop/debug/app.apk"),
        variant_name="developDebug",
        application_id="com.example.sample",
        version_name="1.0",
        version_code=1,
    )


if __name__ == "__main__":
    unittest.main()
