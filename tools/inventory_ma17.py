#!/usr/bin/env python3
"""Index IDA C517 addresses and operands without trusting semantic comments."""

import collections
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "FiatTipo_MA17_dump_27c256.bin"
IDA = ROOT / "FiatTipoIDAFullDump_27c256.asm"
OUTPUT = ROOT / "build" / "ma17-analysis" / "inventory.json"
EXPECTED_HASH = "a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f"
LINE = re.compile(r"^code:([0-9A-Fa-f]{8})\s+(.*)$")
LABEL = re.compile(r"^([A-Za-z_][A-Za-z_0-9]*):")
OPERAND = re.compile(r"^(\w+)(?:\s+([^;]+))?")
COLLAPSED = re.compile(r"COLLAPSED FUNCTION (\w+)")
RAM = re.compile(r"\bRAM_([0-9A-Fa-f]{1,2})\b")
WORD = re.compile(r"\b[A-Za-z_][A-Za-z_0-9]*\b")
BRANCHES = {"lcall", "acall", "ljmp", "ajmp", "sjmp", "jmp", "jz", "jnz",
            "jc", "jnc", "jb", "jnb", "jbc", "djnz", "cjne"}
CALLS = {"lcall", "acall"}


def main():
    rom = ROM.read_bytes()
    digest = hashlib.sha256(rom).hexdigest()
    if digest != EXPECTED_HASH:
        raise SystemExit(f"IDA listing hash does not match ROM: {digest}")
    from roundtrip_8051 import classification
    raw_assembly = (ROOT / "build" / "roundtrip" / ROM.stem /
                    (ROM.stem + ".disasm51.asm"))
    if not raw_assembly.exists():
        raise SystemExit("run tools/roundtrip_8051.py first")
    code_bytes, data_bytes, unknown_bytes, occupied = classification(
        raw_assembly.read_text(), rom)
    unknown_regions = []
    start = None
    for address in range(len(rom) + 1):
        absent = address < len(rom) and address not in occupied
        if absent and start is None:
            start = address
        elif not absent and start is not None:
            unknown_regions.append({"start": f"0x{start:04X}",
                                    "end": f"0x{address - 1:04X}",
                                    "bytes": address - start})
            start = None
    sfr = {name for name in re.findall(r"^sfr\s+(\w+)\s*=", (ROOT / "reg517.h").read_text(), re.M)}
    sfr.update(("S0RELL", "S0RELH"))
    sys.path.insert(0, str(ROOT / "disasm51" / "src"))
    from disasm51.instructions import Instructions
    mnemonics = {op.mnemonic.split()[0] for op in Instructions().instructions.values()}
    labels = {}
    functions = {}
    instructions = []
    pending_function = False
    for number, line in enumerate(IDA.read_text(errors="replace").splitlines(), 1):
        if "S U B R O U T I N E" in line:
            pending_function = True
        match = LINE.match(line)
        if not match:
            continue
        address = int(match.group(1), 16)
        body = match.group(2).strip()
        collapsed = COLLAPSED.search(body)
        if collapsed:
            name = collapsed.group(1)
            labels[name] = address
            functions[address] = {"name": name, "address": f"0x{address:04X}",
                                  "ida_line": number, "evidence": "IDA collapsed function; ROM byte verified separately",
                                  "confidence": "unreviewed"}
        found_label = LABEL.match(body)
        if found_label:
            name = found_label.group(1)
            labels[name] = address
            if pending_function:
                functions[address] = {"name": name, "address": f"0x{address:04X}",
                                      "ida_line": number, "evidence": "IDA subroutine entry",
                                      "confidence": "unreviewed"}
                pending_function = False
            body = body[found_label.end():].strip()
        found_op = OPERAND.match(body)
        if not found_op:
            continue
        mnemonic, operands = found_op.groups()
        mnemonic = mnemonic.lower()
        if mnemonic not in mnemonics or address >= len(rom):
            continue
        operands = operands or ""
        memories = sorted({f"0x{int(value, 16):02X}" for value in RAM.findall(operands)})
        registers = sorted(set(WORD.findall(operands)) & sfr)
        target = operands.split(",")[-1].strip() if mnemonic in BRANCHES else None
        instructions.append({"address": f"0x{address:04X}", "ida_line": number,
                             "mnemonic": mnemonic, "operands": operands.strip(),
                             "ram": memories, "sfr": registers, "target": target})
    references = []
    dptr_immediate_loads = []
    ram_uses = collections.defaultdict(list)
    sfr_uses = collections.defaultdict(list)
    for item in instructions:
        site = item["address"]
        pc = int(site, 16)
        if pc + 2 < len(rom) and rom[pc] == 0x90:
            value = (rom[pc + 1] << 8) | rom[pc + 2]
            owner = occupied.get(value)
            target_class = ("outside_rom" if value >= len(rom) else
                            "unclassified" if owner is None else
                            "data" if owner.lower().startswith(("db ", "dw ")) else "code")
            dptr_immediate_loads.append({"site": site, "value": f"0x{value:04X}",
                                         "target_class": target_class,
                                         "ida_line": item["ida_line"]})
        for address in item["ram"]:
            ram_uses[address].append(site)
        for name in item["sfr"]:
            sfr_uses[name].append(site)
        if item["target"]:
            target = item["target"].split()[0]
            resolved = labels.get(target)
            if resolved is None and re.fullmatch(r"0x[0-9A-Fa-f]+", target):
                resolved = int(target, 16)
            references.append({"site": site, "kind": "call" if item["mnemonic"] in CALLS else "branch",
                               "target": target, "target_address": None if resolved is None
                               else f"0x{resolved:04X}", "ida_line": item["ida_line"]})
    incoming = collections.Counter(ref["target_address"] for ref in references
                                   if ref["kind"] == "call" and ref["target_address"])
    for item in functions.values():
        item["incoming_calls"] = incoming[item["address"]]
    semantic = {}
    for row in (ROOT / "asm" / "ma17" / "semantic_labels.tsv").read_text().splitlines():
        if row and not row.startswith("#"):
            address, name, confidence, evidence = row.split("\t", 3)
            semantic[int(address, 16)] = (name, confidence, evidence)
    for address, function in functions.items():
        if address in semantic:
            alias, confidence, evidence = semantic[address]
            function.update({"semantic_alias": alias, "confidence": confidence,
                             "semantic_evidence": evidence})
        elif address not in occupied and rom[address] == 0xFF:
            function.update({"confidence": "confirmed_erased",
                             "semantic_evidence": "ROM byte FFh is in an unclassified ORG gap"})
    by_address = {int(row["address"], 16): row for row in instructions}
    direct_targets = {int(ref["site"], 16): int(ref["target_address"], 16)
                      for ref in references if ref["target_address"]}
    opcode_table = Instructions()
    reached_by = collections.Counter()
    for function in functions.values():
        if function["confidence"] == "confirmed_erased":
            function.update({"flow_reachable_instruction_starts": 0,
                             "flow_missing_edges": 0, "flow_iram": [], "flow_sfr": []})
            continue
        work = [int(function["address"], 16)]
        seen = set()
        missing = set()
        while work:
            pc = work.pop()
            if pc in seen or pc in missing or pc >= len(rom):
                continue
            row = by_address.get(pc)
            if row is None:
                missing.add(pc)
                continue
            seen.add(pc)
            mnemonic = row["mnemonic"]
            next_pc = pc + opcode_table[rom[pc]].length
            target = direct_targets.get(pc)
            if mnemonic in {"ret", "reti"}:
                continue
            if mnemonic in BRANCHES - CALLS:
                if target is not None:
                    work.append(target)
                if mnemonic in {"ljmp", "ajmp", "sjmp", "jmp"}:
                    continue
            work.append(next_pc)
        for pc in seen:
            reached_by[pc] += 1
        function["flow_reachable_instruction_starts"] = len(seen)
        function["flow_missing_edges"] = len(missing)
        function["flow_iram"] = sorted({value for pc in seen for value in by_address[pc]["ram"]})
        function["flow_sfr"] = sorted({value for pc in seen for value in by_address[pc]["sfr"]})
    result = {"rom_sha256": digest, "source": str(IDA.relative_to(ROOT)),
              "metrics": {"ida_subroutine_entries": len(functions),
                          "ida_instruction_lines": len(instructions),
                          "references": len(references),
                          "dptr_immediate_loads": len(dptr_immediate_loads),
                          "pc_relative_movc_sites": sum(
                              item["mnemonic"] == "movc" and "@A+PC" in item["operands"].upper()
                              for item in instructions),
                          "unresolved_references": sum(r["target_address"] is None for r in references),
                          "iram_addresses_referenced": len(ram_uses),
                          "sfr_names_referenced": len(sfr_uses),
                          "functions_with_confirmed_code_alias": sum(
                              f["confidence"] == "confirmed_code" for f in functions.values()),
                          "functions_unreviewed": sum(
                              f["confidence"] == "unreviewed" for f in functions.values()),
                          "functions_hypothetical": sum(
                              f["confidence"] == "hypothesis" for f in functions.values()),
                          "functions_erased_slots": sum(
                              f["confidence"] == "confirmed_erased" for f in functions.values()),
                          "code_bytes": code_bytes, "data_bytes": data_bytes,
                          "unclassified_bytes": unknown_bytes,
                          "unclassified_regions": len(unknown_regions),
                          "instruction_starts_in_multiple_flows": sum(value > 1 for value in reached_by.values()),
                          "instruction_starts_in_no_function_flow": len(by_address.keys() - reached_by.keys())},
              "analysis_priority": sorted(
                  ({"address": f["address"], "ida_name": f["name"],
                    "incoming_calls": f["incoming_calls"]} for f in functions.values()
                   if f["confidence"] == "unreviewed"),
                  key=lambda f: (-f["incoming_calls"], f["address"]))[:20],
              "functions": sorted(functions.values(), key=lambda x: x["address"]),
              "unclassified_regions": unknown_regions,
              "instructions": instructions,
              "references": references, "dptr_immediate_loads": dptr_immediate_loads,
              "ram_uses": dict(sorted(ram_uses.items())),
              "sfr_uses": dict(sorted(sfr_uses.items()))}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
