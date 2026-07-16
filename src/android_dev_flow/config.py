from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONFIG_NAME = ".android-dev-flow.json"
DEFAULT_VARIANTS = {
    "develop": "developDebug",
    "staging": "stagingDebug",
    "production": "productionDebug",
}


class ConfigError(ValueError):
    pass


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


@dataclass(frozen=True)
class ValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


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
        data = read_config_data(config_file)

    project_name = str(data.get("project_name") or project_dir.name)
    module = str(data.get("module") or "app")
    default_variant = str(data.get("default_variant") or "developDebug")
    has_explicit_variants = "variants" in data
    raw_variants = data.get("variants") or DEFAULT_VARIANTS
    variants = normalize_variants(raw_variants)

    if default_variant not in variants.values() and not has_explicit_variants:
        variants = {"default": default_variant, **variants}

    config = ProjectConfig(
        project_dir=project_dir,
        project_name=project_name,
        module=module,
        default_variant=default_variant,
        variants=variants,
    )
    validate_config_schema(config)
    return config


def read_config_data(config_file: Path) -> dict[str, Any]:
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ConfigError(f"{config_file} contains invalid JSON: {error}") from error

    if not isinstance(data, dict):
        raise ConfigError(f"{config_file} must contain a JSON object")
    return data


def normalize_variants(raw: Any) -> dict[str, str]:
    if isinstance(raw, dict):
        variants = {str(key).strip(): str(value).strip() for key, value in raw.items()}
        validate_variants(variants)
        return variants

    if isinstance(raw, list):
        variants: dict[str, str] = {}
        for item in raw:
            value = str(item).strip()
            variants[value] = value
        validate_variants(variants)
        return variants

    raise ConfigError("variants must be an object or a list")


def validate_variants(variants: dict[str, str]) -> None:
    if not variants:
        raise ConfigError("variants must not be empty")

    for label, variant in variants.items():
        if not label:
            raise ConfigError("variant labels must not be empty")
        if not variant:
            raise ConfigError(f"variant for label {label!r} must not be empty")


def validate_config_schema(config: ProjectConfig) -> None:
    if not config.project_name.strip():
        raise ConfigError("project_name must not be empty")
    if not config.module.strip():
        raise ConfigError("module must not be empty")
    if not config.default_variant.strip():
        raise ConfigError("default_variant must not be empty")
    validate_variants(config.variants)
    if config.default_variant not in config.variants.values():
        raise ConfigError("default_variant must exist in variants")


def validate_project(config: ProjectConfig) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    project_dir = config.project_dir

    if not project_dir.is_dir():
        errors.append(f"project directory does not exist: {project_dir}")
        return ValidationResult(errors=errors, warnings=warnings)

    config_file = project_dir / CONFIG_NAME
    if not config_file.is_file():
        warnings.append(f"config file not found: {config_file}")

    if not has_settings_file(project_dir):
        errors.append("Gradle settings file not found: settings.gradle or settings.gradle.kts")

    wrapper = project_dir / gradle_wrapper_name()
    if not wrapper.is_file():
        errors.append(f"Gradle wrapper not found: {wrapper}")

    module_dir = project_dir / config.module
    if not module_dir.is_dir():
        errors.append(f"configured module directory does not exist: {module_dir}")
    elif not has_build_file(module_dir):
        errors.append(f"module build file not found in {module_dir}: build.gradle or build.gradle.kts")

    if not is_gradle_path_segment(config.module):
        errors.append(f"module name is not a simple Gradle path segment: {config.module}")

    for label, variant in config.variants.items():
        if not is_gradle_name(variant):
            errors.append(f"variant name for {label!r} is not a simple Gradle task suffix: {variant}")

    return ValidationResult(errors=errors, warnings=warnings)


def create_default_config(
    project_dir: Path,
    *,
    project_name: str | None = None,
    module: str | None = None,
    default_variant: str = "developDebug",
    variants: dict[str, str] | None = None,
) -> ProjectConfig:
    selected_variants = variants or DEFAULT_VARIANTS
    selected_module = module or detect_default_module(project_dir)
    selected_name = project_name or detect_project_name(project_dir) or project_dir.name

    if default_variant not in selected_variants.values():
        selected_variants = {"default": default_variant, **selected_variants}

    config = ProjectConfig(
        project_dir=project_dir,
        project_name=selected_name,
        module=selected_module,
        default_variant=default_variant,
        variants=selected_variants,
    )
    validate_config_schema(config)
    return config


def write_config(config: ProjectConfig, *, overwrite: bool = False) -> Path:
    config_file = config.project_dir / CONFIG_NAME
    if not config.project_dir.is_dir():
        raise ConfigError(f"project directory does not exist: {config.project_dir}")
    if config_file.exists() and not overwrite:
        raise ConfigError(f"config file already exists: {config_file}")

    data = {
        "project_name": config.project_name,
        "module": config.module,
        "default_variant": config.default_variant,
        "variants": config.variants,
    }
    config_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return config_file


def detect_project_name(project_dir: Path) -> str | None:
    for settings_file in settings_files(project_dir):
        if not settings_file.is_file():
            continue
        match = re.search(r"rootProject\.name\s*=\s*['\"]([^'\"]+)['\"]", settings_file.read_text(encoding="utf-8"))
        if match:
            return match.group(1)
    return None


def detect_default_module(project_dir: Path) -> str:
    app_dir = project_dir / "app"
    if app_dir.is_dir() and has_build_file(app_dir):
        return "app"

    for module_name in discover_included_modules(project_dir):
        module_dir = project_dir / module_name
        if module_dir.is_dir() and has_build_file(module_dir):
            return module_name

    return "app"


def discover_included_modules(project_dir: Path) -> list[str]:
    modules: list[str] = []
    for settings_file in settings_files(project_dir):
        if not settings_file.is_file():
            continue
        text = settings_file.read_text(encoding="utf-8")
        for match in re.finditer(r"include\s*\(?\s*([^\n)]+)", text):
            for value in re.findall(r"['\"]:([^'\"]+)['\"]", match.group(1)):
                modules.append(value.replace(":", "/"))
    return modules


def settings_files(project_dir: Path) -> list[Path]:
    return [project_dir / "settings.gradle", project_dir / "settings.gradle.kts"]


def has_settings_file(project_dir: Path) -> bool:
    return any(path.is_file() for path in settings_files(project_dir))


def has_build_file(directory: Path) -> bool:
    return (directory / "build.gradle").is_file() or (directory / "build.gradle.kts").is_file()


def gradle_wrapper_name() -> str:
    import sys

    return "gradlew.bat" if sys.platform.startswith("win") else "gradlew"


def assemble_task_name(module: str, variant: str) -> str:
    return f":{module}:assemble{variant[:1].upper()}{variant[1:]}"


def is_gradle_name(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value))


def is_gradle_path_segment(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+", value))
