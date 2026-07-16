from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import ProjectConfig
from .gradle import ApkOutput
from .process import capture


@dataclass(frozen=True)
class PackageResult:
    apk_path: Path
    metadata_path: Path
    sha256: str


def package_apk(config: ProjectConfig, apk: ApkOutput, output_dir: Path | None = None) -> PackageResult:
    target_dir = output_dir or config.project_dir / "dist"
    target_dir.mkdir(parents=True, exist_ok=True)

    target_apk = target_dir / apk_filename(config, apk)
    shutil.copy2(apk.path, target_apk)

    digest = sha256_file(target_apk)
    metadata_path = target_apk.with_suffix(".txt")
    metadata_path.write_text(metadata_text(config, apk, target_apk, digest), encoding="utf-8")

    return PackageResult(apk_path=target_apk, metadata_path=metadata_path, sha256=digest)


def apk_filename(config: ProjectConfig, apk: ApkOutput) -> str:
    parts = [config.display_name, apk.variant_name]
    version = version_part(apk)
    if version:
        parts.append(version)
    return "-".join(safe_filename_part(part) for part in parts if part) + ".apk"


def version_part(apk: ApkOutput) -> str | None:
    if apk.version_name and apk.version_code is not None:
        return f"v{apk.version_name}-{apk.version_code}"
    if apk.version_name:
        return f"v{apk.version_name}"
    if apk.version_code is not None:
        return f"vc{apk.version_code}"
    return None


def safe_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-._")
    return cleaned or "unknown"


def metadata_text(config: ProjectConfig, apk: ApkOutput, packaged_apk: Path, digest: str) -> str:
    branch, commit = git_info(config.project_dir)
    lines = [
        f"Project: {config.display_name}",
        f"Project path: {config.project_dir}",
        f"Module: {config.module}",
        f"Variant: {apk.variant_name}",
        f"Application ID: {apk.application_id or 'unknown'}",
        f"Version name: {apk.version_name or 'unknown'}",
        f"Version code: {apk.version_code if apk.version_code is not None else 'unknown'}",
        f"Source APK: {apk.path}",
        f"Packaged APK: {packaged_apk}",
        f"Git branch: {branch or 'unknown'}",
        f"Git commit: {commit or 'unknown'}",
        f"Build timestamp: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"SHA-256: {digest}",
        "",
    ]
    return "\n".join(lines)


def git_info(project_dir: Path) -> tuple[str | None, str | None]:
    branch = capture(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=project_dir, check=False).strip()
    commit = capture(["git", "rev-parse", "--short", "HEAD"], cwd=project_dir, check=False).strip()
    return branch or None, commit or None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
