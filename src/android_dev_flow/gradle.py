from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from .process import run


@dataclass(frozen=True)
class ApkOutput:
    path: Path
    variant_name: str
    application_id: str | None
    version_name: str | None
    version_code: int | None


def gradle_wrapper(project_dir: Path) -> Path:
    wrapper = project_dir / ("gradlew.bat" if sys.platform.startswith("win") else "gradlew")
    if not wrapper.is_file():
        raise RuntimeError(f"Gradle wrapper not found in {project_dir}")
    return wrapper


def assemble_task(module: str, variant: str) -> str:
    return f":{module}:assemble{variant[:1].upper()}{variant[1:]}"


def build_variant(project_dir: Path, module: str, variant: str) -> None:
    wrapper = gradle_wrapper(project_dir)
    run([str(wrapper), assemble_task(module, variant)], cwd=project_dir)


def find_apk_output(project_dir: Path, module: str, variant: str) -> ApkOutput:
    output_root = project_dir / module / "build" / "outputs" / "apk"
    if not output_root.is_dir():
        raise RuntimeError(f"APK output folder does not exist: {output_root}")

    metadata_files = sorted(
        output_root.rglob("output-metadata.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    for metadata_file in metadata_files:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        if metadata.get("variantName") != variant:
            continue

        elements = metadata.get("elements") or []
        if not elements:
            continue

        element = elements[0]
        output_file = element.get("outputFile")
        if not output_file:
            continue

        apk_path = metadata_file.parent / output_file
        if apk_path.is_file():
            return ApkOutput(
                path=apk_path,
                variant_name=str(metadata.get("variantName") or variant),
                application_id=metadata.get("applicationId"),
                version_name=element.get("versionName"),
                version_code=element.get("versionCode"),
            )

    raise RuntimeError(f"no APK output found for variant {variant}")
