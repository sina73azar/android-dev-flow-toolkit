from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from android_dev_flow.apk_package import apk_filename, package_apk, safe_filename_part, sha256_file
from android_dev_flow.config import ProjectConfig
from android_dev_flow.gradle import ApkOutput


class ApkPackageTests(unittest.TestCase):
    def test_safe_filename_part_removes_problem_characters(self) -> None:
        self.assertEqual(safe_filename_part("Refah Dpi / develop"), "Refah-Dpi-develop")

    def test_apk_filename_includes_project_variant_and_version(self) -> None:
        self.assertEqual(apk_filename(sample_config(Path("/tmp/project")), sample_apk(Path("/tmp/app.apk"))), "RefahDpi-developDebug-v1.2.3-42.apk")

    def test_package_apk_copies_apk_and_writes_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            source_apk = project_dir / "app" / "build" / "outputs" / "apk" / "develop" / "debug" / "app.apk"
            source_apk.parent.mkdir(parents=True)
            source_apk.write_bytes(b"apk bytes")

            config = sample_config(project_dir)
            apk = sample_apk(source_apk)
            result = package_apk(config, apk)

            self.assertTrue(result.apk_path.is_file())
            self.assertTrue(result.metadata_path.is_file())
            self.assertEqual(result.apk_path.read_bytes(), b"apk bytes")
            self.assertEqual(result.sha256, sha256_file(result.apk_path))

            metadata = result.metadata_path.read_text(encoding="utf-8")
            self.assertIn("Project: RefahDpi", metadata)
            self.assertIn("Module: app", metadata)
            self.assertIn("Variant: developDebug", metadata)
            self.assertIn("Application ID: ir.refah.app", metadata)
            self.assertIn(f"Source APK: {source_apk}", metadata)
            self.assertIn(f"Packaged APK: {result.apk_path}", metadata)
            self.assertIn(f"SHA-256: {result.sha256}", metadata)


def sample_config(project_dir: Path) -> ProjectConfig:
    return ProjectConfig(
        project_dir=project_dir,
        project_name="RefahDpi",
        module="app",
        default_variant="developDebug",
        variants={"develop": "developDebug"},
    )


def sample_apk(path: Path) -> ApkOutput:
    return ApkOutput(
        path=path,
        variant_name="developDebug",
        application_id="ir.refah.app",
        version_name="1.2.3",
        version_code=42,
    )


if __name__ == "__main__":
    unittest.main()
