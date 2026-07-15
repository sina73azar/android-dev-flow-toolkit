from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONFIG_NAME = ".android-dev-flow.json"


@dataclass(frozen=True)
class ProjectConfig:
    project_dir: Path
    project_name: str
    module: str
    default_variant: str
    variants: dict[str, str]

    @property
    def display_name(self) -> str:
        return self.project_name or self.project_dir.name


def find_project_dir(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / CONFIG_NAME).is_file():
            return candidate
        if (candidate / "settings.gradle").is_file() or (candidate / "settings.gradle.kts").is_file():
            return candidate

    return current


def load_config(project_arg: str | None) -> ProjectConfig:
    start = Path(project_arg).expanduser() if project_arg else Path.cwd()
    project_dir = find_project_dir(start)
    config_file = project_dir / CONFIG_NAME

    data: dict[str, Any] = {}
    if config_file.is_file():
        data = json.loads(config_file.read_text(encoding="utf-8"))

    project_name = str(data.get("project_name") or project_dir.name)
    module = str(data.get("module") or "app")
    default_variant = str(data.get("default_variant") or "developDebug")
    raw_variants = data.get("variants") or {"develop": default_variant}
    variants = normalize_variants(raw_variants)

    if default_variant not in variants.values():
        variants = {"default": default_variant, **variants}

    return ProjectConfig(
        project_dir=project_dir,
        project_name=project_name,
        module=module,
        default_variant=default_variant,
        variants=variants,
    )


def normalize_variants(raw: Any) -> dict[str, str]:
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}

    if isinstance(raw, list):
        variants: dict[str, str] = {}
        for item in raw:
            value = str(item)
            variants[value] = value
        return variants

    raise ValueError("variants must be an object or a list")
