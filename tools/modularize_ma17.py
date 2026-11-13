#!/usr/bin/env python3
"""Split and reassemble the verified Fiat Tipo 27C256 MA1.7 assembly."""

import bisect
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "FiatTipo_MA17_dump_27c256.bin"
SOURCE = ROOT / "build" / "roundtrip" / ROM.stem / (ROM.stem + ".asm")
OUTPUT = ROOT / "build" / "ma17-analysis" / "modular"
ALIASES = ROOT / "asm" / "ma17" / "semantic_labels.tsv"
SECTIONS = (
    (0x0000, "00_interrupts_and_timer_control"),
    (0x0850, "01_boot_and_engine_control"),
    (0x4AD1, "02_kline_and_low_level_io"),
    (0x5205, "03_arithmetic_and_memory"),
    (0x6004, "04_diagnostics_and_adc"),
    (0x6E00, "05_tables_and_calibration"),
)
AMBIGUOUS_DB_RANGES = (
    (0x5269, 0x5278, "instruction-like arithmetic sequence; no confirmed entry"),
    (0x53DA, 0x5418, "instruction-like arithmetic sequence; no confirmed entry"),
)


def group_fault_triplets(body, rom):
    start, end = 0x6E27, 0x6E78
    first = body.index(f"dptr_{start:04X}:\n")
    last = body.index(f"dptr_{end:04X}:", first)
    original = body[first:last]
    seen = set()
    for line in original.splitlines():
        if not line or line == f"dptr_{start:04X}:" or line.startswith("org\t"):
            continue
        match = re.match(r"\tdb ([0-9A-F]+)h\t; \[([0-9A-F]{4})h\]", line)
        if not match:
            raise ValueError(f"unexpected source inside fault table: {line}")
        value, address = int(match.group(1), 16), int(match.group(2), 16)
        if not start <= address < end or address in seen or rom[address] != value:
            raise ValueError(f"fault table source differs at {address:04X}")
        seen.add(address)
    expected = {address for address in range(start, end) if rom[address] != 0xFF}
    expected.add(start)  # the labeled FF byte is emitted by disasm51
    if seen != expected:
        raise ValueError(f"fault table source has missing/extra bytes: {seen ^ expected}")
    rows = [f"dptr_{start:04X}:"]
    for address in range(start, end, 3):
        low, high, status = rom[address:address + 3]
        rows.append(f"\tdb 0{low:02X}h, 0{high:02X}h, 0{status:02X}h"
                    f"\t; [{address:04X}h] code_le16={high:02X}{low:02X}h status={status:02X}h")
    return body[:first] + "\n".join(rows) + "\n" + body[last:]


def group_sensor_pairs(body, rom, start, end, terminator):
    first = body.index(f"dptr_{start:04X}:\n")
    last = body.index(terminator, first)
    original = body[first:last]
    seen = set()
    for line in original.splitlines():
        if not line or line == f"dptr_{start:04X}:":
            continue
        match = re.fullmatch(r"\tdb ([0-9A-F]+)h\t; \[([0-9A-F]{4})h\].*", line)
        if not match:
            raise ValueError(f"unexpected source inside sensor table: {line}")
        value, address = int(match.group(1), 16), int(match.group(2), 16)
        if not start <= address < end or address in seen or rom[address] != value:
            raise ValueError(f"sensor table source differs at {address:04X}")
        seen.add(address)
    if seen != set(range(start, end)):
        raise ValueError(f"sensor table source has missing/extra bytes: {seen ^ set(range(start, end))}")
    rows = [f"dptr_{start:04X}:"]
    for address in range(start, end, 2):
        selector, location = rom[address:address + 2]
        mode = "IRAM" if selector == 0 else "MOVX"
        rows.append(f"\tdb 0{selector:02X}h, 0{location:02X}h"
                    f"\t; [{address:04X}h] mode={mode} address={location:02X}h"
                    f" selector={selector:02X}h")
    return body[:first] + "\n".join(rows) + "\n" + body[last:]


def split_source(source, rom):
    sys.path.insert(0, str(ROOT / "disasm51" / "src"))
    from disasm51.instructions import Instructions

    marker = "; disasm51 output; ORG gaps contain erased 0FFh bytes\n"
    if source.count(marker) != 1:
        raise ValueError("unknown input assembly format")
    registers, body = source.split(marker)
    body = group_fault_triplets(body, rom)
    body = group_sensor_pairs(body, rom, 0x6E78, 0x6E8C, "dptr_6E8C:")
    body = group_sensor_pairs(body, rom, 0x6E8C, 0x6EA0, "org\t7000h")
    boundaries = [start for start, _ in SECTIONS]
    modules = [[] for _ in SECTIONS]
    aliases = {}
    for row in ALIASES.read_text().splitlines():
        if row.startswith("#") or not row:
            continue
        address, name, confidence, evidence = row.split("\t", 3)
        aliases[int(address, 16)] = (name, confidence, evidence)
    instructions = Instructions()
    reference = re.compile(r"\b(?:jump|dptr)_([0-9A-Fa-f]{4})\b")
    pc = 0
    inserted = set()
    for line in body.splitlines():
        statement = line.split(";", 1)[0].strip()
        if statement.lower() == "end":
            continue
        if statement.lower().startswith("org\t"):
            pc = int(statement.split()[1].removesuffix("h"), 16)
        section = bisect.bisect_right(boundaries, pc) - 1
        if section < 0 or section >= len(SECTIONS):
            raise ValueError(f"address outside section map: {pc:04X}")
        if line in (f"jump_{pc:04X}:", f"dptr_{pc:04X}:") and pc in aliases:
            name, confidence, evidence = aliases[pc]
            modules[section].extend((f"; {confidence}: {evidence}", f"{name}:"))
            inserted.add(pc)
        elif pc in aliases and pc not in inserted and line.startswith("\t") and statement:
            name, confidence, evidence = aliases[pc]
            is_data = statement.lower().startswith(("db ", "dw "))
            if confidence != ("confirmed_bytes" if is_data else "confirmed_code"):
                raise ValueError(f"alias type does not match source at {pc:04X}")
            modules[section].extend((f"; {confidence}: {evidence}", f"{name}:"))
            inserted.add(pc)
        for start, end, reason in AMBIGUOUS_DB_RANGES:
            if pc == start and statement.lower().startswith("db "):
                modules[section].append(
                    f"; ambiguous DB {start:04X}h..{end:04X}h: {reason}; "
                    "preserved as data pending a control-flow reference")
        if line.startswith("\t"):
            code, separator, comment = line.partition(";")
            code = reference.sub(lambda match: aliases.get(int(match.group(1), 16),
                                                         (match.group(0),))[0], code)
            line = code + separator + comment
        modules[section].append(line)
        length = 0
        if statement.lower().startswith(("db ", "dw ")):
            length = (2 if statement.lower().startswith("dw ") else 1) * (statement.count(",") + 1)
        elif line.startswith("\t") and statement and statement[0].isalpha():
            length = instructions[rom[pc]].length
        if section + 1 < len(boundaries) and pc < boundaries[section + 1] < pc + length:
            raise ValueError(f"section boundary bisects instruction/data at {pc:04X}")
        pc += length
    if inserted != aliases.keys():
        raise ValueError(f"semantic aliases without matching source positions: {aliases.keys() - inserted}")
    return registers, modules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT,
                        help="directory for editable include files and validation report")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    rom = ROM.read_bytes()
    if len(rom) != 32768:
        raise SystemExit("expected 32 KiB Fiat Tipo ROM")
    expected_hash = "a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f"
    if hashlib.sha256(rom).hexdigest() != expected_hash:
        raise SystemExit("firmware hash changed")
    if not SOURCE.exists():
        subprocess.run([sys.executable, str(ROOT / "tools" / "roundtrip_8051.py"),
                        str(ROM)], check=True, stdout=subprocess.DEVNULL)
    registers, modules = split_source(SOURCE.read_text(), rom)
    from roundtrip_8051 import classification
    classified_source = "\n".join(
        f"org\t{start:04X}h\n" + "\n".join(lines)
        for (start, _), lines in zip(SECTIONS, modules))
    code_bytes, data_bytes, unclassified_bytes, _ = classification(classified_source, rom)
    output.mkdir(parents=True, exist_ok=True)
    (output / "registers.inc").write_text(registers)
    master = ["; Fiat Tipo MA1.7 27C256: absolute addresses and original bytes.",
              "$include registers.inc"]
    summary = []
    for index, ((start, name), lines) in enumerate(zip(SECTIONS, modules)):
        end = SECTIONS[index + 1][0] if index + 1 < len(SECTIONS) else len(rom)
        filename = name + ".inc"
        path = output / filename
        path.write_text(f"; {name}: ROM {start:04X}h..{end - 1:04X}h\n"
                        f"org 0{start:04X}h\n" + "\n".join(lines) + "\n")
        master.append(f"$include {filename}")
        summary.append({"file": filename, "start": f"0x{start:04X}",
                        "end": f"0x{end - 1:04X}", "source_lines": len(lines)})
    master.append("end")
    (output / "ma17.asm").write_text("\n".join(master) + "\n")
    assembled = subprocess.run([str(ROOT / "asm51" / "asm51"), "-n", "-f", "bin",
                                "-o", "ma17.rebuilt.bin", "ma17.asm"], cwd=output,
                               text=True, capture_output=True)
    if assembled.returncode:
        raise SystemExit(assembled.stderr)
    rebuilt = (output / "ma17.rebuilt.bin").read_bytes()
    report = {"original_size": len(rom), "rebuilt_size": len(rebuilt),
              "original_sha256": hashlib.sha256(rom).hexdigest(),
              "rebuilt_sha256": hashlib.sha256(rebuilt).hexdigest(),
              "mismatched_bytes": sum(a != b for a, b in zip(rom, rebuilt))
              + abs(len(rom) - len(rebuilt)),
              "roundtrip": "PASS" if rom == rebuilt else "FAIL", "modules": summary,
              "code_bytes": code_bytes, "data_bytes": data_bytes,
              "unclassified_bytes": unclassified_bytes,
              "ambiguous_db_regions": [
                  {"start": f"0x{start:04X}", "end": f"0x{end:04X}",
                   "bytes": end - start + 1, "reason": reason}
                  for start, end, reason in AMBIGUOUS_DB_RANGES],
              "assembler_stderr": assembled.stderr.strip()}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if rom == rebuilt else 1


if __name__ == "__main__":
    sys.exit(main())
