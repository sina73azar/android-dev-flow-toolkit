#!/usr/bin/env python3
"""Preview or apply a simple folder cleanup by file extension."""

from __future__ import annotations

import argparse
import shutil
from collections import defaultdict
from pathlib import Path


CATEGORIES = {
    "Documents": {".csv", ".doc", ".docx", ".md", ".pdf", ".ppt", ".pptx", ".txt", ".xls", ".xlsx"},
    "Images": {".gif", ".heic", ".jpeg", ".jpg", ".png", ".svg", ".webp"},
    "Audio": {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"},
    "Video": {".avi", ".mkv", ".mov", ".mp4", ".webm"},
    "Archives": {".7z", ".gz", ".rar", ".tar", ".tgz", ".zip"},
    "Code": {".css", ".go", ".html", ".js", ".json", ".py", ".rs", ".sh", ".ts", ".xml", ".yaml", ".yml"},
}


def category_for(path: Path) -> str:
    suffix = path.suffix.lower()
    for category, suffixes in CATEGORIES.items():
        if suffix in suffixes:
            return category
    return "Other"


def unique_destination(destination: Path) -> Path:
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    parent = destination.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def sort_files(folder: Path, apply: bool) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    files = [path for path in folder.iterdir() if path.is_file()]

    for source in files:
        category = category_for(source)
        target_dir = folder / category
        destination = unique_destination(target_dir / source.name)
        counts[category] += 1

        if apply:
            target_dir.mkdir(exist_ok=True)
            shutil.move(str(source), str(destination))
            print(f"moved {source.name} -> {destination.relative_to(folder)}")
        else:
            print(f"would move {source.name} -> {category}/{destination.name}")

    return dict(counts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="folder to clean up")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually move files; without this flag it only previews",
    )
    args = parser.parse_args()

    folder = args.folder.expanduser().resolve()
    if not folder.exists():
        parser.error(f"{folder} does not exist")
    if not folder.is_dir():
        parser.error(f"{folder} is not a folder")

    counts = sort_files(folder, args.apply)
    if not counts:
        print("No files found.")
        return

    action = "Moved" if args.apply else "Previewed"
    total = sum(counts.values())
    print(f"{action} {total} file(s) across {len(counts)} category folder(s).")


if __name__ == "__main__":
    main()
