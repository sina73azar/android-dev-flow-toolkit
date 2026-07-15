#!/usr/bin/env python3
"""Roll dice expressions like 2d6, d20, or 4d6+2."""

from __future__ import annotations

import argparse
import random
import re


DICE_RE = re.compile(r"^(?P<count>\d*)d(?P<sides>\d+)(?P<modifier>[+-]\d+)?$")


def parse_expression(expression: str) -> tuple[int, int, int]:
    match = DICE_RE.match(expression.lower().strip())
    if not match:
        raise ValueError("use a dice expression like 2d6, d20, or 4d6+2")

    count = int(match.group("count") or 1)
    sides = int(match.group("sides"))
    modifier = int(match.group("modifier") or 0)

    if count < 1 or count > 100:
        raise ValueError("dice count must be between 1 and 100")
    if sides < 2 or sides > 1000:
        raise ValueError("sides must be between 2 and 1000")

    return count, sides, modifier


def roll(expression: str) -> tuple[list[int], int, int]:
    count, sides, modifier = parse_expression(expression)
    rolls = [random.randint(1, sides) for _ in range(count)]
    return rolls, modifier, sum(rolls) + modifier


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expression", nargs="?", default="d20")
    parser.add_argument(
        "-r",
        "--repeat",
        type=int,
        default=1,
        help="number of times to roll",
    )
    args = parser.parse_args()

    if args.repeat < 1:
        parser.error("--repeat must be at least 1")

    try:
        for _ in range(args.repeat):
            rolls, modifier, total = roll(args.expression)
            modifier_text = f" {'+' if modifier >= 0 else '-'} {abs(modifier)}" if modifier else ""
            print(f"{args.expression}: {rolls}{modifier_text} = {total}")
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
