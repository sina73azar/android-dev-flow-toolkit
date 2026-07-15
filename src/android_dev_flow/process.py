from __future__ import annotations

import subprocess
from pathlib import Path


class CommandError(RuntimeError):
    def __init__(self, command: list[str], returncode: int) -> None:
        self.command = command
        self.returncode = returncode
        super().__init__(f"command failed with exit code {returncode}: {' '.join(command)}")


def run(command: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd, text=True)
    if check and result.returncode != 0:
        raise CommandError(command, result.returncode)
    return result


def capture(command: list[str], cwd: Path | None = None, check: bool = True) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip()
        if stderr:
            print(stderr)
        raise CommandError(command, result.returncode)
    return result.stdout
