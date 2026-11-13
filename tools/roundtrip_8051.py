#!/usr/bin/env python3
"""Disassemble and reassemble a C517A-compatible external ROM with asm51."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SFR = re.compile(r"^\s*(sfr|sbit)\s+(\w+)\s*=\s*0x([0-9a-fA-F]+);", re.M)
MA17_SHA256 = "a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f"
RENAULT_CLIO_SHA256 = "cf0c841d924bfc740ffbe825d7b87d9df22cfa7f3bfcfa4eafe7765e03795412"
# Fiat Tipo only: non-erased C517 vector entries in this 27C256 dump.
# CTF at 009Bh is also reached by the Timer 1 output handler at 0090h.
MA17_VECTORS = (0x03, 0x0B, 0x1B, 0x23, 0x2B, 0x43,
                0x53, 0x63, 0x6B, 0x9B)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def definitions(header, c517a=False):
    result = []
    seen = set()
    for kind, name, value in SFR.findall(header):
        if name.lower() in seen:
            raise ValueError(f"duplicate symbol: {name}")
        seen.add(name.lower())
        result.append((name, "DATA" if kind == "sfr" else "BIT", int(value, 16)))
    if c517a:
        # Infineon D80517A, XRAM section, pp. 20-22. This ROM uses both SFRs.
        result += [("XPAGE", "DATA", 0x91), ("SYSCON", "DATA", 0xB1)]
    # Late C517 serial reload registers in SAB80C517 manual, pp. 22, 81.
    result += [("S0RELL", "DATA", 0xAA), ("S0RELH", "DATA", 0xBA)]
    return result


def convert(source, symbols):
    lines = ["; MCS-51 register definitions from reg517.h"]
    if any(name == "XPAGE" for name, _, _ in symbols):
        lines[0] += "; C517A XPAGE/SYSCON profile"
    lines += [f"{name} {kind} 0{value:02X}h" for name, kind, value in symbols]
    lines += ["", "; disasm51 output; ORG gaps contain erased 0FFh bytes"]
    for line in source.splitlines():
        if line.startswith(("$nomod51", "$include")) or line == "cseg":
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def differences(expected, actual):
    offsets = [i for i in range(min(len(expected), len(actual))) if expected[i] != actual[i]]
    offsets.extend(range(min(len(expected), len(actual)), max(len(expected), len(actual))))
    groups = []
    for offset in offsets:
        if groups and offset == groups[-1][-1] + 1:
            groups[-1].append(offset)
        else:
            groups.append([offset])
    return offsets, groups


def classification(source, original):
    sys.path.insert(0, str(ROOT / "disasm51" / "src"))
    from disasm51.instructions import Instructions

    instructions = Instructions()
    code = set()
    data = set()
    owners = {}
    pc = 0
    for line in source.splitlines():
        body = line.split(";", 1)[0].strip()
        if not body:
            continue
        if body.lower().startswith("org\t"):
            pc = int(body.split()[1].removesuffix("h"), 16)
        elif body.lower().startswith(("db ", "dw ")):
            count = (2 if body.lower().startswith("dw ") else 1) * (body.count(",") + 1)
            data.update(range(pc, pc + count))
            owners.update({address: line.strip() for address in range(pc, pc + count)})
            pc += count
        elif line.startswith("\t") and body[0].isalpha():
            length = instructions[original[pc]].length
            code.update(range(pc, pc + length))
            owners.update({address: line.strip() for address in range(pc, pc + length)})
            pc += length
    if code & data or max(code | data, default=-1) >= len(original):
        raise ValueError("disassembly classification overlaps or exceeds ROM")
    return len(code), len(data), len(original) - len(code) - len(data), owners


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--entry", action="append", default=[])
    parser.add_argument("--indirect", action="append", default=[])
    parser.add_argument("--no-return-from", action="append", default=[])
    args = parser.parse_args()
    firmware = args.firmware.resolve()
    original = firmware.read_bytes()
    if not original or len(original) > 65536:
        parser.error("firmware must contain 1..65536 bytes")
    firmware_hash = sha256(original)
    firmware_origin = {
        MA17_SHA256: "Fiat Tipo Bosch Monomotronic MA1.7 27C256",
        RENAULT_CLIO_SHA256: "Renault Clio Bosch Monomotronic MA1.7 revision",
    }.get(firmware_hash, "unknown MCS-51 firmware")
    output = args.output_dir or ROOT / "build" / "roundtrip" / firmware.stem
    output.mkdir(parents=True, exist_ok=True)
    mcu = output / "sab80c517.mcu"
    raw = output / (firmware.stem + ".disasm51.asm")
    assembly = output / (firmware.stem + ".asm")
    rebuilt = output / (firmware.stem + ".rebuilt.bin")
    symbols = definitions((ROOT / "reg517.h").read_text(),
                          c517a=firmware_hash == MA17_SHA256)
    mcu.write_text("\n".join(f"{n} {k} 0{v:02X}h" for n, k, v in symbols) + "\n")
    disasm = ROOT / ".venv" / "bin" / "disasm51"
    command = [str(disasm), "--include", str(mcu), "--entry", "RESET"]
    if firmware_hash == MA17_SHA256:
        for vector in MA17_VECTORS:
            command += ["--entry", hex(vector)]
    for option, values in (("--entry", args.entry), ("--indirect", args.indirect),
                           ("--no-return-from", args.no_return_from)):
        for value in values:
            command += [option, value]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "disasm51" / "src")
    result = subprocess.run(command + [str(firmware)], text=True, capture_output=True,
                            env=environment)
    raw.write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(result.stderr)
    assembly.write_text(convert(result.stdout, symbols))
    assembler = ROOT / "asm51" / "asm51"
    assembled = subprocess.run([str(assembler), "-n", "-f", "bin", "-o", str(rebuilt),
                                str(assembly)], text=True, capture_output=True)
    if assembled.returncode:
        print(assembled.stderr, file=sys.stderr)
        return 2
    actual = rebuilt.read_bytes()
    offsets, groups = differences(original, actual)
    code_bytes, data_bytes, unclassified_bytes, owners = classification(result.stdout, original)
    report = {
        "firmware_origin": firmware_origin,
        "original_size": len(original), "rebuilt_size": len(actual),
        "original_sha256": sha256(original), "rebuilt_sha256": sha256(actual),
        "mismatched_bytes": len(offsets), "sha256_equal": sha256(original) == sha256(actual),
        "roundtrip": "PASS" if original == actual else "FAIL",
        "code_bytes": code_bytes, "data_bytes": data_bytes,
        "unclassified_bytes": unclassified_bytes,
        "first_mismatch": None if not offsets else f"0x{offsets[0]:04X}",
        "difference_groups": [{"start": f"0x{g[0]:04X}", "end": f"0x{g[-1]:04X}",
                               "count": len(g)} for g in groups[:20]],
        "disassembler_stderr": result.stderr.strip(), "assembler_stderr": assembled.stderr.strip(),
    }
    if offsets:
        pos = offsets[0]
        report["first_mismatch_source"] = owners.get(pos, "erased ORG gap (0FFh)")
        report["first_mismatch_context"] = {
            "expected": original[max(0, pos - 8):pos + 9].hex(" "),
            "actual": actual[max(0, pos - 8):pos + 9].hex(" ")}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if original == actual else 1


if __name__ == "__main__":
    sys.exit(main())
