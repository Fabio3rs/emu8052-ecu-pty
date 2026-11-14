#!/usr/bin/env python3
"""Render a bounded static control-flow graph from the verified modular ROM assembly."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULAR = ROOT / "build/ma17-analysis/modular"
ROM = ROOT / "FiatTipo_MA17_dump_27c256.bin"
BRANCH = {"jb", "jnb", "jbc", "jc", "jnc", "jz", "jnz", "cjne", "djnz"}
JUMP = {"ajmp", "ljmp", "sjmp", "jmp"}
CALL = {"acall", "lcall"}
STOP = {"ret", "reti"}


def read_assembly(source, rom):
    sys.path.insert(0, str(ROOT / "disasm51/src"))
    from disasm51.instructions import Instructions

    lengths = Instructions()
    labels, code = {}, {}
    pc = 0
    for include in re.findall(r"^\$include\s+(\S+\.inc)$", source.read_text(), re.M):
        for line in (source.parent / include).read_text().splitlines():
            statement = line.split(";", 1)[0].strip()
            if not statement:
                continue
            if statement.lower().startswith("org ") or statement.lower().startswith("org\t"):
                pc = int(statement.split()[1].removesuffix("h"), 16)
            elif statement.endswith(":"):
                labels[statement[:-1]] = pc
            elif statement.lower().startswith(("db ", "dw ")):
                pc += (2 if statement.lower().startswith("dw ") else 1) * (statement.count(",") + 1)
            elif line.startswith("\t") and statement[0].isalpha():
                if pc >= len(rom):
                    raise ValueError(f"instruction outside ROM at {pc:04X}")
                size = lengths[rom[pc]].length
                code[pc] = (statement, pc + size)
                pc += size
    return labels, code


def destination(statement, labels):
    operand = statement.split(None, 1)[1].split(",")[-1].strip()
    if operand in labels:
        return labels[operand]
    if re.fullmatch(r"[0-9A-Fa-f]+h", operand):
        return int(operand[:-1], 16)
    return None


def build_graph(code, labels, start, end):
    selected = {pc: instruction for pc, instruction in code.items() if start <= pc < end}
    if not selected:
        raise ValueError("interval contains no assembly instructions")
    leaders = {min(selected)}
    for pc, (statement, following) in selected.items():
        mnemonic = statement.split()[0].lower()
        if mnemonic in BRANCH | JUMP | CALL | STOP:
            if following in selected:
                leaders.add(following)
            if mnemonic in BRANCH | JUMP | CALL and not (mnemonic == "jmp" and "@" in statement):
                target = destination(statement, labels)
                if target in selected:
                    leaders.add(target)
        elif following not in selected:
            higher = [address for address in selected if address > pc]
            if higher:
                leaders.add(min(higher))
    blocks, owner = {}, {}
    current = None
    for pc in sorted(selected):
        if pc in leaders:
            current = pc
            blocks[current] = []
        blocks[current].append(pc)
        owner[pc] = current
    edges = set()
    for block, addresses in blocks.items():
        last = addresses[-1]
        statement, following = selected[last]
        mnemonic = statement.split()[0].lower()
        target = (destination(statement, labels) if mnemonic in BRANCH | JUMP | CALL
                  and not (mnemonic == "jmp" and "@" in statement) else None)
        if mnemonic in BRANCH | JUMP | CALL and target is not None:
            edges.add((block, owner.get(target, target), "call" if mnemonic in CALL else "taken"))
        if mnemonic == "jmp" and "@" in statement:
            edges.add((block, "indirect", "indirect"))
        if mnemonic not in JUMP | STOP and following in owner:
            edges.add((block, owner[following], "next"))
    return blocks, sorted(edges, key=lambda edge: (edge[0], str(edge[1]), edge[2]))


def filter_observed_paths(blocks, edges, observed):
    """Find every block on a static path between successive observed PCs."""
    owner = {pc: block for block, addresses in blocks.items() for pc in addresses}
    missing = [pc for pc in observed if pc not in owner]
    if missing:
        raise ValueError("observed PC outside instructions in view: " +
                         ", ".join(f"{pc:04X}" for pc in missing))
    forward = {block: set() for block in blocks}
    reverse = {block: set() for block in blocks}
    for source, target, _ in edges:
        if target in blocks:
            forward[source].add(target)
            reverse[target].add(source)

    def reachable(adjacency, origin):
        seen, pending = set(), [origin]
        while pending:
            node = pending.pop()
            if node not in seen:
                seen.add(node)
                pending.extend(adjacency[node] - seen)
        return seen

    included = {owner[pc] for pc in observed}
    selected_edges = set()
    segments = []
    for first, second in zip(observed, observed[1:]):
        source, target = owner[first], owner[second]
        if source == target:
            candidates = {source} if first < second else set()
        else:
            candidates = reachable(forward, source) & reachable(reverse, target)
        possible_edges = {(a, b, kind) for a, b, kind in edges
                          if a in candidates and b in candidates}
        included.update(candidates)
        selected_edges.update(possible_edges)
        segments.append({"from_pc": f"{first:04X}", "to_pc": f"{second:04X}",
                         "status": "possible" if candidates else "no_static_path_in_view",
                         "candidate_blocks": [f"{pc:04X}" for pc in sorted(candidates)],
                         "candidate_edges": len(possible_edges)})
    return {block: blocks[block] for block in sorted(included)}, sorted(
        selected_edges, key=lambda edge: (edge[0], edge[1], edge[2])), segments


def write_dot(path, code, blocks, edges, observed=()):
    rows = ["digraph cfg {", '  graph [rankdir=TB, fontname="monospace"];',
            '  node [shape=box, fontname="monospace", fontsize=9];']
    observed = set(observed)
    for block, addresses in blocks.items():
        lines = [f"{pc:04X}: {code[pc][0]}" for pc in addresses]
        color = ', style=filled, fillcolor="lightskyblue"' if observed.intersection(addresses) else ''
        rows.append(f'  n{block:04X} [label={json.dumps(chr(10).join(lines))}{color}];')
    external = {target for _, target, _ in edges if isinstance(target, int) and target not in blocks}
    for address in sorted(external):
        rows.append(f'  n{address:04X} [label="{address:04X} outside view", shape=ellipse];')
    if any(target == "indirect" for _, target, _ in edges):
        rows.append('  indirect [label="indirect target unresolved", shape=diamond];')
    for source, target, kind in edges:
        destination_id = "indirect" if target == "indirect" else f"n{target:04X}"
        style = "dashed" if kind in {"call", "indirect"} else "solid"
        rows.append(f'  n{source:04X} -> {destination_id} [label="{kind}", style={style}];')
    path.write_text("\n".join(rows) + "\n}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=lambda value: int(value, 0), default=0x36DE)
    parser.add_argument("--end", type=lambda value: int(value, 0), default=0x371D)
    parser.add_argument("--source", type=Path, default=MODULAR / "ma17.asm")
    parser.add_argument("--rom", type=Path, default=ROM)
    parser.add_argument("--output", type=Path, default=ROOT / "build/ma17-analysis/cfg_36de.svg")
    parser.add_argument("--pcs", nargs="+", metavar="PC",
                        help="ordered observed PCs, e.g. --pcs 0x36DE 0x36E1 0x36E4")
    args = parser.parse_args()
    if args.start >= args.end:
        parser.error("start must precede end")
    labels, code = read_assembly(args.source, args.rom.read_bytes())
    blocks, edges = build_graph(code, labels, args.start, args.end)
    observed = [int(item, 0) for pc in args.pcs or [] for item in pc.split(",")]
    if observed:
        blocks, edges, segments = filter_observed_paths(blocks, edges, observed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dot = args.output.with_suffix(".dot")
    write_dot(dot, code, blocks, edges, observed)
    subprocess.run(["dot", "-Tsvg", str(dot), "-o", str(args.output)], check=True)
    if observed:
        report = args.output.with_suffix(".json")
        report.write_text(json.dumps({"window": [f"{args.start:04X}", f"{args.end:04X}"],
                                      "observed_pcs": [f"{pc:04X}" for pc in observed],
                                      "segments": segments,
                                      "limits": "static branches inside window only; calls have no return-stack model; indirect targets unresolved"},
                                     indent=2) + "\n")
        print(f"analysis: {report}")
    print(f"blocks: {len(blocks)}; edges: {len(edges)}; DOT: {dot}; SVG: {args.output}")


if __name__ == "__main__":
    main()
