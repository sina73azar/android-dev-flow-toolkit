from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONFIG_NAME = ".android-dev-flow.json"
FALLBACK_VARIANTS = {"debug": "debug"}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ProjectConfig:
    project_dir: Path
    project_name: str
    module: str
    default_variant: str
    variants: dict[str, str]
    application_modules: tuple[str, ...] = ()
    auto_detect_variants: bool = False

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
    module = str(data.get("module") or detect_default_module(project_dir))
    application_modules = normalize_modules(data.get("modules"), project_dir, module)
    raw_variants = data.get("variants")
    has_config = config_file.is_file()
    auto_detect_variants = bool(data.get("auto_detect_variants")) or raw_variants == "auto" or not has_config

    if auto_detect_variants:
        variants = detect_android_variants(project_dir, module) or FALLBACK_VARIANTS
    else:
        has_explicit_variants = "variants" in data
        variants = normalize_variants(raw_variants or FALLBACK_VARIANTS)

    default_variant = str(data.get("default_variant") or detect_default_variant(variants))

    if default_variant not in variants.values() and not auto_detect_variants and not has_explicit_variants:
        variants = {"default": default_variant, **variants}
    elif default_variant not in variants.values() and auto_detect_variants:
        default_variant = detect_default_variant(variants)

    config = ProjectConfig(
        project_dir=project_dir,
        project_name=project_name,
        module=module,
        default_variant=default_variant,
        variants=variants,
        application_modules=application_modules,
        auto_detect_variants=auto_detect_variants,
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


def normalize_modules(raw: Any, project_dir: Path, default_module: str) -> tuple[str, ...]:
    modules: list[str] = []
    if raw is None:
        modules = detect_android_application_modules(project_dir)
    elif isinstance(raw, list):
        for item in raw:
            value = str(item).strip()
            if value:
                append_unique(modules, value)
    else:
        raise ConfigError("modules must be a list")

    if default_module:
        append_unique(modules, default_module)
    return tuple(modules)


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
    for module in config.application_modules:
        if not module.strip():
            raise ConfigError("modules must not contain empty values")
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
    default_variant: str | None = None,
    variants: dict[str, str] | None = None,
) -> ProjectConfig:
    application_modules = tuple(detect_android_application_modules(project_dir))
    selected_module = module or preferred_application_module(application_modules) or detect_default_module(project_dir)
    application_modules = normalize_modules(list(application_modules), project_dir, selected_module)
    selected_name = project_name or detect_project_name(project_dir) or project_dir.name
    auto_detect_variants = variants is None
    selected_variants = variants or detect_android_variants(project_dir, selected_module) or FALLBACK_VARIANTS
    selected_default_variant = default_variant or detect_default_variant(selected_variants)

    if selected_default_variant not in selected_variants.values():
        selected_variants = {"default": selected_default_variant, **selected_variants}

    config = ProjectConfig(
        project_dir=project_dir,
        project_name=selected_name,
        module=selected_module,
        default_variant=selected_default_variant,
        variants=selected_variants,
        application_modules=application_modules,
        auto_detect_variants=auto_detect_variants,
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
        "modules": list(config.application_modules),
        "default_variant": config.default_variant,
        "variants": "auto" if config.auto_detect_variants else config.variants,
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
    app_modules = detect_android_application_modules(project_dir)
    if len(app_modules) == 1:
        return app_modules[0]
    if "app" in app_modules:
        return "app"

    app_dir = project_dir / "app"
    if app_dir.is_dir() and has_build_file(app_dir):
        return "app"

    for module_name in discover_included_modules(project_dir):
        module_dir = project_dir / module_name
        if module_dir.is_dir() and has_build_file(module_dir):
            return module_name

    return "app"


def preferred_application_module(modules: tuple[str, ...]) -> str | None:
    if len(modules) == 1:
        return modules[0]
    if "app" in modules:
        return "app"
    return modules[0] if modules else None


def detect_android_application_modules(project_dir: Path) -> list[str]:
    modules: list[str] = []
    candidates = discover_included_modules(project_dir)

    children = sorted(project_dir.iterdir()) if project_dir.is_dir() else []
    for child in children:
        if child.is_dir():
            append_unique(candidates, child.name)

    for module in candidates:
        if is_android_application_module(project_dir, module):
            append_unique(modules, module)
    return modules


def is_android_application_module(project_dir: Path, module: str) -> bool:
    build_file = find_build_file(project_dir / module)
    if build_file is None:
        return False

    text = strip_gradle_comments(build_file.read_text(encoding="utf-8"))
    application_aliases = version_catalog_plugin_aliases(project_dir, "com.android.application")
    return bool(
        re.search(r"\bid\s*\(\s*['\"]com\.android\.application['\"]\s*\)", text)
        or re.search(r"\bid\s+['\"]com\.android\.application['\"]", text)
        or re.search(r"\bapply\s+plugin:\s*['\"]com\.android\.application['\"]", text)
        or any(has_plugin_alias(text, alias) for alias in application_aliases)
    )


def version_catalog_plugin_aliases(project_dir: Path, plugin_id: str) -> list[str]:
    catalog = project_dir / "gradle" / "libs.versions.toml"
    if not catalog.is_file():
        return []

    text = catalog.read_text(encoding="utf-8")
    plugins_block = extract_toml_section(text, "plugins")
    aliases: list[str] = []
    for match in re.finditer(r"^([A-Za-z0-9_.-]+)\s*=\s*\{[^}\n]*\bid\s*=\s*['\"]([^'\"]+)['\"]", plugins_block, re.MULTILINE):
        key, detected_plugin_id = match.groups()
        if detected_plugin_id != plugin_id:
            continue
        append_unique(aliases, f"libs.plugins.{key}")
        append_unique(aliases, f"libs.plugins.{key.replace('-', '.')}")
        append_unique(aliases, f"libs.plugins.{key.replace('_', '.')}")
    return aliases


def extract_toml_section(text: str, section_name: str) -> str:
    match = re.search(rf"^\[{re.escape(section_name)}\]\s*$", text, re.MULTILINE)
    if match is None:
        return ""

    start = match.end()
    next_section = re.search(r"^\[[^\]]+\]\s*$", text[start:], re.MULTILINE)
    end = start + next_section.start() if next_section else len(text)
    return text[start:end]


def has_plugin_alias(text: str, alias: str) -> bool:
    escaped = re.escape(alias)
    return bool(
        re.search(rf"\balias\s*\(\s*{escaped}\s*\)", text)
        or re.search(rf"\balias\s*\(\s*{escaped}\s*\)\s*\.apply\s*\(", text)
    )


def detect_android_variants(project_dir: Path, module: str) -> dict[str, str]:
    module_dir = project_dir / module
    build_file = find_build_file(module_dir)
    if build_file is None:
        return {}

    text = strip_gradle_comments(build_file.read_text(encoding="utf-8"))
    flavors = extract_gradle_names_from_block(text, "productFlavors")
    selected_build_types = detect_android_build_types(text)

    variants: dict[str, str] = {}
    if flavors:
        for flavor in flavors:
            for build_type in selected_build_types:
                variant = f"{flavor}{build_type[:1].upper()}{build_type[1:]}"
                label = flavor if len(selected_build_types) == 1 else f"{flavor}-{build_type}"
                variants[label] = variant
    else:
        for build_type in selected_build_types:
            variants[build_type] = build_type

    return variants


def detect_android_build_types(text: str) -> list[str]:
    build_types = ["debug", "release"]
    for build_type in extract_gradle_names_from_block(text, "buildTypes"):
        append_unique(build_types, build_type)
    return build_types


def detect_default_variant(variants: dict[str, str]) -> str:
    for preferred in ("debug", "Debug"):
        if preferred in variants.values():
            return preferred
    return next(iter(variants.values()), "debug")


def find_build_file(directory: Path) -> Path | None:
    for filename in ("build.gradle.kts", "build.gradle"):
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None


def strip_gradle_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def extract_gradle_names_from_block(text: str, block_name: str) -> list[str]:
    block = extract_named_block(text, block_name)
    if block is None:
        return []

    names: list[str] = []
    for match in re.finditer(r"\b(?:create|maybeCreate)\s*\(\s*['\"]([A-Za-z][A-Za-z0-9_]*)['\"]\s*\)", block):
        append_unique(names, match.group(1))
    for match in re.finditer(r"\b([A-Za-z][A-Za-z0-9_]*)\s*\{", block):
        name = match.group(1)
        if name not in {"android", "defaultConfig", "productFlavors", "buildTypes", "signingConfig"}:
            append_unique(names, name)
    return names


def extract_named_block(text: str, block_name: str) -> str | None:
    match = re.search(rf"\b{re.escape(block_name)}\s*\{{", text)
    if match is None:
        return None

    start = text.find("{", match.start())
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : index]
    return None


def append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


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
    return find_build_file(directory) is not None


def gradle_wrapper_name() -> str:
    import sys

    return "gradlew.bat" if sys.platform.startswith("win") else "gradlew"


def assemble_task_name(module: str, variant: str) -> str:
    return f":{module}:assemble{variant[:1].upper()}{variant[1:]}"


def is_gradle_name(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value))


def is_gradle_path_segment(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+", value))
