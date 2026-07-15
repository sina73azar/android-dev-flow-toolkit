#!/usr/bin/env python3
"""Generate readable passphrases."""

from __future__ import annotations

import argparse
import secrets


WORDS = [
    "amber",
    "anchor",
    "apricot",
    "atlas",
    "basil",
    "beacon",
    "brisk",
    "cabin",
    "cactus",
    "canvas",
    "cedar",
    "cinder",
    "citrus",
    "clover",
    "cobalt",
    "comet",
    "copper",
    "coral",
    "daisy",
    "delta",
    "ember",
    "falcon",
    "fennel",
    "fjord",
    "forest",
    "ginger",
    "glacier",
    "harbor",
    "hazel",
    "indigo",
    "jasmine",
    "kernel",
    "lagoon",
    "lantern",
    "maple",
    "marble",
    "meadow",
    "meteor",
    "mosaic",
    "nectar",
    "onyx",
    "orchid",
    "pepper",
    "plum",
    "prairie",
    "quartz",
    "raven",
    "river",
    "saffron",
    "shadow",
    "silver",
    "spruce",
    "summit",
    "thistle",
    "tulip",
    "velvet",
    "violet",
    "willow",
    "zephyr",
]


def build_passphrase(word_count: int, separator: str, include_number: bool) -> str:
    words = [secrets.choice(WORDS) for _ in range(word_count)]
    phrase = separator.join(words)
    if include_number:
        phrase = f"{phrase}{separator}{secrets.randbelow(90) + 10}"
    return phrase


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-w",
        "--words",
        type=int,
        default=4,
        help="number of words to include",
    )
    parser.add_argument(
        "-s",
        "--separator",
        default="-",
        help="separator between words",
    )
    parser.add_argument(
        "-n",
        "--number",
        action="store_true",
        help="append a random two-digit number",
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=1,
        help="number of passphrases to print",
    )
    args = parser.parse_args()

    if args.words < 2:
        parser.error("--words must be at least 2")
    if args.count < 1:
        parser.error("--count must be at least 1")

    for _ in range(args.count):
        print(build_passphrase(args.words, args.separator, args.number))


if __name__ == "__main__":
    main()
