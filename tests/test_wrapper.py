from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from android_dev_flow import __version__
from android_dev_flow.wrapper import WrapperError, create_project_wrapper


class WrapperTests(unittest.TestCase):
    def test_create_project_wrapper_builds_runnable_pinned_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project_dir = Path(temporary)

            result = create_project_wrapper(project_dir)

            self.assertTrue(result.unix_launcher.is_file())
            self.assertTrue(result.windows_launcher.is_file())
            self.assertTrue(result.archive.is_file())
            self.assertEqual(result.version_file.read_text(encoding="utf-8"), f"{__version__}\n")
            self.assertTrue(result.unix_launcher.stat().st_mode & stat.S_IXUSR)

            completed = subprocess.run(
                [sys.executable, str(result.archive), "--version"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.stdout.strip(), f"android-dev-flow-toolkit {__version__}")

            launcher_command = (
                ["cmd", "/c", str(result.windows_launcher), "--version"]
                if os.name == "nt"
                else [str(result.unix_launcher), "--version"]
            )
            launcher_completed = subprocess.run(
                launcher_command,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(launcher_completed.stdout.strip(), f"android-dev-flow-toolkit {__version__}")

    def test_create_project_wrapper_refuses_to_replace_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project_dir = Path(temporary)
            create_project_wrapper(project_dir)

            with self.assertRaises(WrapperError):
                create_project_wrapper(project_dir)

    def test_create_project_wrapper_force_replaces_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project_dir = Path(temporary)
            result = create_project_wrapper(project_dir)
            result.version_file.write_text("old\n", encoding="utf-8")

            replaced = create_project_wrapper(project_dir, overwrite=True)

            self.assertEqual(replaced.version_file.read_text(encoding="utf-8"), f"{__version__}\n")


if __name__ == "__main__":
    unittest.main()
