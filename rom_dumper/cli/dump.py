"""Simple converter: hex-dump text -> raw binary.

Reads lines containing space-separated hex bytes. If a line contains a
colon ("addr: bytes..."), the part after the first colon is used.

Usage:
  python3 cli/dump.py input.txt -o firmware.bin
  cat input.txt | python3 cli/dump.py - -o firmware.bin
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert hex dump text to raw binary")
    p.add_argument("input", help="Input file ('-' for stdin).")
    p.add_argument("-o", "--output", type=Path, default=Path("dump.bin"), help="Output binary file")
    return p.parse_args(argv)


def parse_hex_lines(lines):
    data = bytearray()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            _, hexpart = line.split(":", 1)
        else:
            hexpart = line
        for token in hexpart.strip().split():
            # accept tokens like '00' or ignore if invalid
            if len(token) != 2:
                continue
            try:
                data.append(int(token, 16))
            except ValueError:
                continue
    return data


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # Open input
    if args.input == "-":
        lines = sys.stdin
    else:
        try:
            f = open(args.input, "r", encoding="utf-8")
        except OSError as e:
            print(f"Failed to open input file {args.input}: {e}", file=sys.stderr)
            return 2
        lines = f

    data = parse_hex_lines(lines)

    # Close if we opened a file
    if args.input != "-":
        f.close()

    try:
        args.output.write_bytes(data)
    except OSError as e:
        print(f"Failed to write output file {args.output}: {e}", file=sys.stderr)
        return 3

    print(f"Wrote {len(data)} bytes to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

