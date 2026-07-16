from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from android_dev_flow.config import (
    CONFIG_NAME,
    ConfigError,
    create_default_config,
    gradle_wrapper_name,
    load_config,
    normalize_variants,
    validate_project,
    write_config,
)


class ConfigTests(unittest.TestCase):
    def test_create_default_config_detects_project_name_and_app_module(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_android_project(project_dir)

            config = create_default_config(project_dir)

            self.assertEqual(config.project_name, "SampleApp")
            self.assertEqual(config.module, "app")
            self.assertEqual(config.default_variant, "developDebug")
            self.assertEqual(config.variants["develop"], "developDebug")

    def test_write_and_load_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_android_project(project_dir)
            config = create_default_config(project_dir)

            config_file = write_config(config)
            loaded = load_config(str(project_dir))

            self.assertEqual(config_file, project_dir / CONFIG_NAME)
            self.assertEqual(loaded.project_dir, project_dir)
            self.assertEqual(loaded.project_name, "SampleApp")
            self.assertEqual(loaded.module, "app")

    def test_validate_project_passes_for_minimal_android_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_android_project(project_dir)
            config = create_default_config(project_dir)
            write_config(config)

            validation = validate_project(config)

            self.assertTrue(validation.ok)
            self.assertEqual(validation.errors, [])

    def test_validate_project_reports_missing_module(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_android_project(project_dir)
            config = create_default_config(project_dir, module="missing")

            validation = validate_project(config)

            self.assertFalse(validation.ok)
            self.assertIn("configured module directory does not exist", "\n".join(validation.errors))

    def test_normalize_variants_rejects_empty_values(self) -> None:
        with self.assertRaises(ConfigError):
            normalize_variants({"develop": ""})

    def test_load_config_rejects_default_variant_missing_from_explicit_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_android_project(project_dir)
            (project_dir / CONFIG_NAME).write_text(
                """
{
  "project_name": "SampleApp",
  "module": "app",
  "default_variant": "developDebug",
  "variants": {
    "staging": "stagingDebug"
  }
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(str(project_dir))


def create_android_project(project_dir: Path) -> None:
    (project_dir / "settings.gradle.kts").write_text('rootProject.name = "SampleApp"\ninclude(":app")\n', encoding="utf-8")
    (project_dir / gradle_wrapper_name()).write_text("#!/bin/sh\n", encoding="utf-8")
    app_dir = project_dir / "app"
    app_dir.mkdir()
    (app_dir / "build.gradle.kts").write_text("plugins { id(\"com.android.application\") }\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
