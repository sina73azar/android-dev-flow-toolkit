from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from android_dev_flow.config import (
    CONFIG_NAME,
    ConfigError,
    create_default_config,
    detect_android_application_modules,
    detect_android_variants,
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
            self.assertEqual(config.default_variant, "qaDebug")
            self.assertEqual(config.variants["qa-debug"], "qaDebug")
            self.assertEqual(config.variants["qa-release"], "qaRelease")
            self.assertEqual(config.application_modules, ("app",))
            self.assertTrue(config.auto_detect_variants)

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
            self.assertEqual(loaded.application_modules, ("app",))
            self.assertEqual(loaded.variants["demo-debug"], "demoDebug")
            self.assertEqual(loaded.variants["demo-release"], "demoRelease")
            self.assertTrue(loaded.auto_detect_variants)

    def test_create_default_config_records_all_application_modules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_multi_module_android_project(project_dir, modules=("app", "demo", "memory_game"))

            config = create_default_config(project_dir)
            config_file = write_config(config)
            loaded = load_config(str(project_dir))

            self.assertEqual(config.module, "app")
            self.assertEqual(config.application_modules, ("app", "demo", "memory_game"))
            self.assertIn('"modules": [', config_file.read_text(encoding="utf-8"))
            self.assertEqual(loaded.application_modules, ("app", "demo", "memory_game"))

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
            normalize_variants({"qa": ""})

    def test_detect_android_variants_without_flavors_uses_debug_build_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_android_project(project_dir, build_file_text='plugins { id("com.android.application") }\n')

            self.assertEqual(detect_android_variants(project_dir, "app"), {"debug": "debug", "release": "release"})

    def test_detect_android_variants_includes_debug_and_release_for_release_only_build_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_android_project(
                project_dir,
                build_file_text="""
plugins { id("com.android.application") }

android {
    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
}
""".lstrip(),
            )

            config = create_default_config(project_dir)

            self.assertEqual(config.default_variant, "debug")
            self.assertEqual(config.variants, {"debug": "debug", "release": "release"})

    def test_create_default_config_falls_back_to_debug_without_detected_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            project_dir.mkdir(exist_ok=True)

            config = create_default_config(project_dir, module="app")

            self.assertEqual(config.default_variant, "debug")
            self.assertEqual(config.variants, {"debug": "debug"})

    def test_detect_android_application_modules_from_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_multi_module_android_project(project_dir)

            self.assertEqual(detect_android_application_modules(project_dir), ["app", "demo"])

    def test_detect_android_application_modules_from_version_catalog_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_version_catalog_android_project(project_dir)

            self.assertEqual(detect_android_application_modules(project_dir), ["app", "analoge_clock", "memory_game"])

    def test_detect_default_module_prefers_single_application_module(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_multi_module_android_project(project_dir, modules=("mobile",), library_modules=("core",))

            config = create_default_config(project_dir)

            self.assertEqual(config.module, "mobile")
            self.assertEqual(config.application_modules, ("mobile",))

    def test_load_config_auto_detects_variants_from_build_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_android_project(project_dir)
            (project_dir / CONFIG_NAME).write_text(
                """
{
  "project_name": "SampleApp",
  "module": "app",
  "variants": "auto"
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            config = load_config(str(project_dir))

            self.assertEqual(config.default_variant, "qaDebug")
            self.assertEqual(config.application_modules, ("app",))
            self.assertEqual(
                config.variants,
                {
                    "qa-debug": "qaDebug",
                    "qa-release": "qaRelease",
                    "demo-debug": "demoDebug",
                    "demo-release": "demoRelease",
                    "internal-debug": "internalDebug",
                    "internal-release": "internalRelease",
                },
            )
            self.assertTrue(config.auto_detect_variants)

    def test_load_config_rejects_default_variant_missing_from_explicit_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            create_android_project(project_dir)
            (project_dir / CONFIG_NAME).write_text(
                """
{
  "project_name": "SampleApp",
  "module": "app",
  "default_variant": "qaDebug",
  "variants": {
    "demo": "demoDebug"
  }
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(str(project_dir))


def create_android_project(project_dir: Path, build_file_text: str | None = None) -> None:
    (project_dir / "settings.gradle.kts").write_text('rootProject.name = "SampleApp"\ninclude(":app")\n', encoding="utf-8")
    (project_dir / gradle_wrapper_name()).write_text("#!/bin/sh\n", encoding="utf-8")
    app_dir = project_dir / "app"
    app_dir.mkdir()
    (app_dir / "build.gradle.kts").write_text(build_file_text or sample_android_build_file(), encoding="utf-8")


def create_multi_module_android_project(
    project_dir: Path,
    modules: tuple[str, ...] = ("app", "demo"),
    library_modules: tuple[str, ...] = ("core",),
) -> None:
    included = [*modules, *library_modules]
    include_lines = "\n".join(f'include(":{module}")' for module in included)
    (project_dir / "settings.gradle.kts").write_text(f'rootProject.name = "SampleApp"\n{include_lines}\n', encoding="utf-8")
    (project_dir / gradle_wrapper_name()).write_text("#!/bin/sh\n", encoding="utf-8")

    for module in modules:
        module_dir = project_dir / module
        module_dir.mkdir()
        (module_dir / "build.gradle.kts").write_text(sample_android_build_file(), encoding="utf-8")

    for module in library_modules:
        module_dir = project_dir / module
        module_dir.mkdir()
        (module_dir / "build.gradle.kts").write_text('plugins { id("com.android.library") }\n', encoding="utf-8")


def create_version_catalog_android_project(project_dir: Path) -> None:
    (project_dir / "settings.gradle.kts").write_text(
        """
rootProject.name = "SampleApp"
include(":app")
include(":analoge_clock")
include(":memory_game")
include(":network-logger-core")
""".lstrip(),
        encoding="utf-8",
    )
    (project_dir / gradle_wrapper_name()).write_text("#!/bin/sh\n", encoding="utf-8")
    gradle_dir = project_dir / "gradle"
    gradle_dir.mkdir()
    (gradle_dir / "libs.versions.toml").write_text(
        """
[plugins]
android-application = { id = "com.android.application", version = "8.13.2" }
android-library = { id = "com.android.library", version = "8.13.2" }
""".lstrip(),
        encoding="utf-8",
    )

    for module in ("app", "analoge_clock", "memory_game"):
        module_dir = project_dir / module
        module_dir.mkdir()
        (module_dir / "build.gradle.kts").write_text(
            """
plugins {
    alias(libs.plugins.android.application)
}
android { buildTypes { release {} } }
""".lstrip(),
            encoding="utf-8",
        )

    library_dir = project_dir / "network-logger-core"
    library_dir.mkdir()
    (library_dir / "build.gradle.kts").write_text(
        """
plugins {
    alias(libs.plugins.android.library)
}
""".lstrip(),
        encoding="utf-8",
    )


def sample_android_build_file() -> str:
    return """
plugins { id("com.android.application") }

android {
    productFlavors {
        qa {
            dimension = "environment"
        }
        demo {
            dimension = "environment"
        }
        internal {
            dimension = "environment"
        }
    }
    buildTypes {
        debug {}
        release {}
    }
}
""".lstrip()


if __name__ == "__main__":
    unittest.main()
