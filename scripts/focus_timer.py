#!/usr/bin/env python3
"""Run a simple terminal countdown timer."""

from __future__ import annotations

import argparse
import sys
import time


def format_time(total_seconds: int) -> str:
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def countdown(seconds: int, label: str) -> None:
    try:
        for remaining in range(seconds, -1, -1):
            sys.stdout.write(f"\r{label}: {format_time(remaining)}")
            sys.stdout.flush()
            if remaining:
                time.sleep(1)
        print("\nDone.\a")
    except KeyboardInterrupt:
        print("\nTimer cancelled.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-m",
        "--minutes",
        type=float,
        default=25,
        help="timer length in minutes",
    )
    parser.add_argument(
        "-l",
        "--label",
        default="Focus",
        help="label shown beside the countdown",
    )
    args = parser.parse_args()

    if args.minutes <= 0:
        parser.error("--minutes must be greater than 0")

    countdown(round(args.minutes * 60), args.label)


if __name__ == "__main__":
    main()
