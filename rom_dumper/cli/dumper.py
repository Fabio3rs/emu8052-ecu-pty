#!/usr/bin/env python3
"""
EPROM TMS27C256 dumper over Arduino serial.

The Arduino sketch prints:
- A header line containing "Dump da EPROM"
- Lines of 16 bytes in hex (e.g. "00 1F 3A ...")
- A final line containing "Fim do dump."

This script:
1. Connects to the given serial port.
2. Optionally resets the Arduino via DTR.
3. Waits for the header line.
4. Reads hex lines until the end marker or the expected size.
5. Writes the collected bytes to a binary file.

Requires: pyserial
    pip install pyserial
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

import serial  # type: ignore[import-not-found]


DEFAULT_BAUD = 115200
DEFAULT_OUTPUT = "dump_27c256.bin"
DEFAULT_EXPECTED_SIZE = 0x8000  # 32 KiB
DEFAULT_BEGIN_PATTERN = "Dump da EPROM"
DEFAULT_END_PATTERN = "Fim do dump."


def parse_size(value: str) -> int:
    """
    Parse a size argument which may be decimal or hex (e.g. '32768' or '0x8000').
    """
    try:
        size = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid size value: {value!r}") from exc

    if size <= 0:
        raise argparse.ArgumentTypeError("Size must be a positive integer.")
    return size


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dump EPROM data from an Arduino-based TMS27C256 reader."
    )

    parser.add_argument(
        "port",
        help="Serial port device (e.g. /dev/ttyACM0, /dev/ttyUSB0).",
    )

    parser.add_argument(
        "-b",
        "--baud",
        type=int,
        default=DEFAULT_BAUD,
        help=f"Baud rate (default: {DEFAULT_BAUD}).",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(DEFAULT_OUTPUT),
        help=f"Output binary file (default: {DEFAULT_OUTPUT}).",
    )

    parser.add_argument(
        "-s",
        "--size",
        type=parse_size,
        default=DEFAULT_EXPECTED_SIZE,
        help=(
            "Expected number of bytes to read. "
            "Accepts decimal or hex (e.g. 32768 or 0x8000). "
            f"Default: {DEFAULT_EXPECTED_SIZE} (0x{DEFAULT_EXPECTED_SIZE:X})."
        ),
    )

    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not toggle DTR to reset the Arduino.",
    )

    parser.add_argument(
        "--begin-pattern",
        default=DEFAULT_BEGIN_PATTERN,
        help=f"Text that marks the start of the dump (default: {DEFAULT_BEGIN_PATTERN!r}).",
    )

    parser.add_argument(
        "--end-pattern",
        default=DEFAULT_END_PATTERN,
        help=f"Text that marks the end of the dump (default: {DEFAULT_END_PATTERN!r}).",
    )

    parser.add_argument(
        "--begin-timeout",
        type=float,
        default=15.0,
        help="Timeout in seconds while waiting for the begin pattern (default: 15.0).",
    )

    parser.add_argument(
        "--read-timeout",
        type=float,
        default=5.0,
        help="Timeout in seconds without data before aborting the dump (default: 5.0).",
    )

    return parser.parse_args(argv)


def reboot_arduino(ser: serial.Serial) -> None:
    """
    Reset the Arduino by toggling DTR.
    On most Arduino boards this will pulse RESET via the USB–serial bridge.
    """
    print("[INFO] Resetting Arduino via DTR...", file=sys.stderr)
    ser.setDTR(False)
    time.sleep(0.1)
    ser.setDTR(True)
    # Give the bootloader + setup() some time to run
    time.sleep(2.0)


def wait_for_begin(
    ser: serial.Serial,
    begin_pattern: str,
    timeout: float,
) -> None:
    """
    Wait until a line containing `begin_pattern` is received or timeout expires.
    Raises RuntimeError on failure.
    """
    print(f"[INFO] Waiting for begin pattern: {begin_pattern!r}", file=sys.stderr)
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        line = ser.readline()
        if not line:
            # No data yet – keep waiting until deadline
            continue

        text = line.decode("utf-8", errors="ignore").strip()
        print(f"[SER] {text}", file=sys.stderr)

        if begin_pattern in text:
            print("[INFO] Begin pattern detected.", file=sys.stderr)
            return

    raise RuntimeError("Timed out waiting for begin pattern.")


def read_dump(
    ser: serial.Serial,
    end_pattern: str,
    expected_size: int,
    idle_timeout: float,
) -> bytes:
    """
    Read hex lines from the serial port and convert them to bytes.

    Stops when:
    - A line containing `end_pattern` is received, OR
    - `expected_size` bytes have been collected, OR
    - No data is received for `idle_timeout` seconds.

    Returns:
        Collected bytes.
    """
    print("[INFO] Starting dump read...", file=sys.stderr)

    data = bytearray()
    last_data_time = time.monotonic()

    while True:
        now = time.monotonic()
        if now - last_data_time > idle_timeout:
            print("[WARN] Idle timeout while reading dump.", file=sys.stderr)
            break

        line = ser.readline()
        if not line:
            # No data this cycle – loop and check idle timeout
            continue

        last_data_time = time.monotonic()
        text = line.decode("utf-8", errors="ignore").strip()

        if not text:
            continue

        if end_pattern in text:
            print("[INFO] End pattern detected.", file=sys.stderr)
            break

        # Expected line format: "00 1F 3A ..."
        tokens = text.split()
        for tok in tokens:
            if len(tok) != 2:
                continue
            try:
                value = int(tok, 16)
            except ValueError:
                continue
            data.append(value)

        if len(data) >= expected_size:
            print(
                f"[INFO] Reached expected size: {expected_size} bytes.",
                file=sys.stderr,
            )
            break

    return bytes(data)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    print(
        f"[INFO] Opening serial port {args.port!r} at {args.baud} baud...",
        file=sys.stderr,
    )

    try:
        with serial.Serial(
            args.port,
            args.baud,
            timeout=0.5,  # read timeout in seconds
        ) as ser:
            # Clear any stale data
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            if not args.no_reset:
                reboot_arduino(ser)
            else:
                print("[INFO] Skipping Arduino reset (--no-reset).", file=sys.stderr)

            wait_for_begin(ser, args.begin_pattern, args.begin_timeout)

            dump = read_dump(
                ser=ser,
                end_pattern=args.end_pattern,
                expected_size=args.size,
                idle_timeout=args.read_timeout,
            )

    except serial.SerialException as exc:
        print(f"[ERROR] Serial error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[INFO] Bytes collected: {len(dump)}", file=sys.stderr)

    try:
        args.output.write_bytes(dump)
    except OSError as exc:
        print(
            f"[ERROR] Failed to write output file {args.output!s}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"[INFO] Dump written to: {args.output.resolve()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

