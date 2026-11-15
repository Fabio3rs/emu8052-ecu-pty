#!/usr/bin/env python3
"""Inventory and compare Fiat Tipo MA1.7 27C256 images without modifying them."""

import argparse
import collections
import hashlib
import itertools
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "FiatTipo_MA17_dump_27c256.bin"
VARIANTS = ROOT / "firmwares_modificados_ma17_tipo"
EXPECTED = (
    "tipo 1.6 alcool27c256.bin",
    "tipo 1.6 alcool27c256+1.5bar.bin",
    "tipo 1.6 alcool27c256 SUN 8817.bin",
    "tipo 1.6 alcool27c256 SUN 37a5.bin",
    "tipo 1.6 alcool27c256 SUN 36fd.bin",
)
SIDECARS = (("normal.txt", EXPECTED[0]),
            ("1.5bar.txt", EXPECTED[1]),
            ("sum36fd.txt", EXPECTED[4]))
MATRICES = ((0x7ED9, 6, 10), (0x7F15, 6, 10), (0x7F51, 6, 10),
            (0x7581, 15, 15), (0x7662, 15, 15), (0x7743, 15, 15))


def intervals(flags):
    """Return half-open runs where flags are true."""
    start = None
    for offset, changed in enumerate(itertools.chain(flags, (False,))):
        if changed and start is None:
            start = offset
        elif not changed and start is not None:
            yield start, offset
            start = None


def decode_xxd(text):
    """Decode xxd-style offsets, including `*` compression of repeated lines."""
    result = bytearray()
    previous = None
    for line in text.splitlines():
        if not re.match(r"^[0-9A-Fa-f]{8}(?:  |$)", line):
            continue
        address = int(line[:8], 16)
        if address < len(result):
            raise ValueError(f"overlapping hexdump line at 0x{address:04X}")
        if address > len(result):
            gap = address - len(result)
            if previous is None or gap % len(previous):
                raise ValueError(f"invalid hexdump gap before 0x{address:04X}")
            result.extend(previous * (gap // len(previous)))
        payload = bytes.fromhex(line.split("|", 1)[0][10:]) if "|" in line else b""
        if payload:
            result.extend(payload)
            previous = payload
    return bytes(result)


def compare(left, right):
    if len(left) != len(right):
        raise ValueError("images must have the same size")
    changed = bytes(a != b for a, b in zip(left, right))
    ranges = list(intervals(changed))
    identical = list(intervals(not flag for flag in changed))
    return {
        "different_bytes": sum(changed),
        "identical_percent": round(100 * (len(changed) - sum(changed)) / len(changed), 6),
        "changed_runs": len(ranges),
        "longest_changed_run": max((end - start for start, end in ranges), default=0),
        "by_4k_block": [sum(changed[start:start + 4096])
                        for start in range(0, len(changed), 4096)],
        "identical_runs": [[start, end] for start, end in identical],
        "changed_intervals": [
            {"start": start, "end_exclusive": end, "length": end - start,
             "left_start": left[max(0, start - 8):min(len(left), start + 16)].hex(" "),
             "right_start": right[max(0, start - 8):min(len(right), start + 16)].hex(" "),
             "left_end": left[max(0, end - 16):min(len(left), end + 8)].hex(" "),
             "right_end": right[max(0, end - 16):min(len(right), end + 8)].hex(" ")}
            for start, end in ranges],
    }


def inventory(paths):
    images = {}
    records = []
    for path in paths:
        data = path.read_bytes()
        if len(data) != 32768:
            raise ValueError(f"{path}: expected 32768 bytes, got {len(data)}")
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        images[key] = data
        records.append({"path": key, "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "sum16": f"0x{sum(data) & 0xFFFF:04X}",
                        "tail16": data[-16:].hex(" "),
                        "reset_ljmp": f"0x{int.from_bytes(data[1:3], 'big'):04X}"
                        if data[0] == 0x02 else None,
                        "erased_ff_bytes": data.count(0xFF)})
    matrix = []
    comparisons = {}
    for left in images:
        row = []
        for right in images:
            if left == right:
                row.append(0)
                continue
            pair = tuple(sorted((left, right)))
            if pair not in comparisons:
                comparisons[pair] = compare(images[pair[0]], images[pair[1]])
            row.append(comparisons[pair]["different_bytes"])
        matrix.append(row)
    return {"images": records, "matrix_order": list(images),
            "different_bytes_matrix": matrix,
            "pairs": [{"left": left, "right": right, **result}
                      for (left, right), result in comparisons.items()]}


def write_heatmap(paths, destination):
    """Show per-256-byte differences from the gasoline reference by ROM address."""
    reference = paths[0].read_bytes()
    rows = []
    for path in paths:
        image = path.read_bytes()
        rows.append([sum(a != b for a, b in zip(reference[start:start + 256],
                                                image[start:start + 256]))
                     for start in range(0, len(reference), 256)])
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="230" '
             'viewBox="0 0 1100 230">',
             '<rect width="1100" height="230" fill="white"/>',
             '<text x="340" y="17" font-family="monospace" font-size="14">'
             'Differences from Fiat gasoline by 256-byte ROM block</text>']
    for index, (path, row) in enumerate(zip(paths, rows)):
        y = 35 + index * 29
        lines.append(f'<text x="5" y="{y + 11}" font-family="monospace" '
                     f'font-size="11">{path.stem[:45]}</text>')
        for column, count in enumerate(row):
            red = 255
            other = 255 - round(count * 220 / 256)
            lines.append(f'<rect x="{350 + column * 5}" y="{y}" width="5" '
                         f'height="15" fill="#{red:02x}{other:02x}{other:02x}"/>')
    for address in range(0, 32768, 4096):
        lines.append(f'<text x="{350 + (address // 256) * 5}" y="225" '
                     f'font-family="monospace" font-size="10">{address:04X}</text>')
    destination.write_text("\n".join(lines + ["</svg>"]) + "\n")


def write_matrix_heatmap(paths, destination):
    """Plot raw unsigned cell deltas; geometry follows the verified G consumer."""
    images = [path.read_bytes() for path in paths]
    names = ("A", "A+", "S88", "S37", "S36")
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="930" height="920" '
             'viewBox="0 0 930 920">',
             '<rect width="930" height="920" fill="white"/>',
             '<text x="8" y="18" font-family="monospace" font-size="13">'
             'Raw u8 cell delta from G: red=positive, blue=negative, white=equal</text>']
    y = 38
    for start, rows, columns in MATRICES:
        lines.append(f'<text x="8" y="{y + 12}" font-family="monospace" '
                     f'font-size="12">{start:04X} {rows}x{columns}</text>')
        for variant, (name, image) in enumerate(zip(names, images[1:])):
            x = 170 + variant * 150
            lines.append(f'<text x="{x}" y="{y + 12}" font-family="monospace" '
                         f'font-size="12">{name}</text>')
            for cell in range(rows * columns):
                address = start + cell
                delta = image[address] - images[0][address]
                shade = max(25, min(225, abs(delta))) if delta else 0
                color = (f'#ff{255 - shade:02x}{255 - shade:02x}' if delta > 0 else
                         f'#{255 - shade:02x}{255 - shade:02x}ff' if delta < 0 else
                         '#ffffff')
                cx = x + (cell % columns) * 8
                cy = y + 20 + (cell // columns) * 8
                lines.append(f'<rect x="{cx}" y="{cy}" width="8" height="8" '
                             f'fill="{color}" stroke="#cccccc" stroke-width="0.2">'
                             f'<title>{name} {address:04X}: G={images[0][address]:02X} '
                             f'variant={image[address]:02X} raw_delta={delta:+d}</title>'
                             '</rect>')
        y += 28 + rows * 8 + 12
    lines.append('</svg>')
    destination.write_text("\n".join(lines) + "\n")


def catalog_matrix_deltas(paths):
    """Record exact raw-u8 cell differences without assuming physical units."""
    images = [path.read_bytes() for path in paths]
    tables = []
    for start, rows, columns in MATRICES:
        size = rows * columns
        reference = images[0][start:start + size]
        versions = []
        for path, image in zip(paths, images):
            cells = image[start:start + size]
            deltas = [int(value) - int(original)
                      for original, value in zip(reference, cells)]
            counts = collections.Counter(deltas)
            versions.append({
                "rom": str(path.relative_to(ROOT)),
                "rom_sha256": hashlib.sha256(image).hexdigest(),
                "changed_cells": size - counts[0],
                "raw_u8_delta_counts": {str(delta): counts[delta]
                                        for delta in sorted(counts)},
                "raw_u8_delta_grid": [deltas[row:row + columns]
                                      for row in range(0, size, columns)],
                "changed_cells_by_row": [sum(value != 0 for value in
                                              deltas[row:row + columns])
                                         for row in range(0, size, columns)],
                "raw_u8_min": min(cells), "raw_u8_max": max(cells),
                "cells_at_ff": cells.count(0xFF),
            })
        tables.append({"start": f"0x{start:04X}",
                       "end_exclusive": f"0x{start + size:04X}",
                       "dimensions": [rows, columns], "versions": versions})
    return {"interpretation": "raw unsigned byte subtraction only; G layout "
            "verified by code, other revisions require consumer verification",
            "tables": tables}


def catalog_candidate_tables(paths):
    """Record raw cells from three adjacent, referenced pointer targets."""
    images = [path.read_bytes() for path in paths]
    directory = 0x70A2
    expected = (0x7ED9, 0x7F15, 0x7F51)
    tables = []
    for index, start in enumerate(expected):
        pointer = directory + index * 2
        for path, data in zip(paths, images):
            actual = int.from_bytes(data[pointer:pointer + 2], "big")
            if actual != start:
                raise ValueError(f"{path}: pointer at 0x{pointer:04X} "
                                 f"is 0x{actual:04X}, expected 0x{start:04X}")
        end = expected[index + 1] if index + 1 < len(expected) else 0x7F8D
        reference = images[0][start:end]
        if len(reference) != 60:
            raise ValueError(f"0x{start:04X}: expected a 60-byte raw grid")
        versions = []
        for path, data in zip(paths, images):
            cells = data[start:end]
            changed = [a != b for a, b in zip(reference, cells)]
            versions.append({
                "rom": str(path.relative_to(ROOT)),
                "rom_sha256": hashlib.sha256(data).hexdigest(),
                "address": f"0x{start:04X}",
                "raw_hex": cells.hex(" "),
                "raw_u8_grid_6x10": [list(cells[row:row + 10])
                                     for row in range(0, 60, 10)],
                "raw_u8_delta_vs_gasoline_6x10": [
                    [int(cells[cell]) - int(reference[cell])
                     for cell in range(row, row + 10)]
                    for row in range(0, 60, 10)],
                "changed_cells_by_row": [sum(changed[row:row + 10])
                                         for row in range(0, 60, 10)],
                "changed_cells_vs_gasoline": sum(changed),
                "raw_u8_min": min(cells), "raw_u8_max": max(cells),
            })
        tables.append({
            "id": f"rom_{start:04x}_candidate",
            "pointer_address": f"0x{pointer:04X}",
            "pointer_encoding": "big_endian_u16",
            "start": f"0x{start:04X}",
            "end_exclusive": f"0x{end:04X}",
            "bytes": end - start,
            "element_encoding": "raw_u8; signed interpretation unverified",
            "dimensions": [6, 10],
            "layout_evidence": "G 3291h uses 10-column stride; other code revisions unverified",
            "known_consumer": "Fiat 0x3291 -> 0x5323 -> 0x5228 -> MOVC",
            "physical_function": None,
            "confidence": "pointer_and_bytes_confirmed_function_unknown",
            "versions": versions,
        })
    return {"catalog_scope": "three adjacent pointer targets only", "tables": tables}


def catalog_pointer_regions(paths):
    """Align candidate data regions by the 0x7002..0x70E9 pointer slots."""
    images = [path.read_bytes() for path in paths]
    slots = range(0x7002, 0x70EA, 2)
    targets = [{slot: int.from_bytes(data[slot:slot + 2], "big")
                for slot in slots} for data in images]
    for path, mapping in zip(paths, targets):
        values = list(mapping.values())
        if len(values) != len(set(values)) or not all(0x7000 <= v < 0x8000
                                                     for v in values):
            raise ValueError(f"{path}: invalid or repeated candidate pointer")
    next_target = []
    for mapping in targets:
        ordered = sorted(mapping.values())
        next_target.append({start: end for start, end in zip(ordered, ordered[1:])})
    regions = []
    for slot in slots:
        terminal = all(mapping[slot] == max(mapping.values())
                       for mapping in targets)
        versions = []
        for index, (path, data, mapping) in enumerate(zip(paths, images, targets)):
            start = mapping[slot]
            end = next_target[index].get(start, len(data))
            reference_start = targets[0][slot]
            reference_end = next_target[0].get(reference_start, len(images[0]))
            delta = (sum(a != b for a, b in zip(
                images[0][reference_start:reference_end], data[start:end]))
                if end - start == reference_end - reference_start else None)
            versions.append({
                "rom": str(path.relative_to(ROOT)),
                "rom_sha256": hashlib.sha256(data).hexdigest(),
                "start": f"0x{start:04X}",
                "candidate_end_exclusive": f"0x{end:04X}",
                "raw_hex": data[start:end].hex(" "),
                "different_bytes_vs_gasoline": delta,
            })
        regions.append({"id": f"pointer_0x{slot:04X}",
                        "pointer_slot": f"0x{slot:04X}",
                        "pointer_encoding": "big_endian_u16",
                        "same_target_all_roms": len({mapping[slot] for mapping in targets}) == 1,
                        "function": None,
                        "dimensions": None,
                        "extent_basis": ("ROM_end; includes filler and metadata; provisional"
                                         if terminal else
                                         "next_higher_directory_target; provisional"),
                        "versions": versions})
    patterns = {}
    for region in regions:
        raw = [version["raw_hex"] for version in region["versions"]]
        if any(value is None for value in raw):
            continue
        pattern = ",".join(str(raw.index(value)) for value in raw)
        patterns.setdefault(pattern, []).append(region["pointer_slot"])
    leading = [{"rom": str(path.relative_to(ROOT)),
                "value": f"0x{int.from_bytes(data[0x7000:0x7002], 'big'):04X}"}
               for path, data in zip(paths, images)]
    return {"leading_word_0x7000": leading,
            "directory_start": "0x7002", "directory_end_exclusive": "0x70EA",
            "raw_equality_patterns": patterns,
            "regions": regions}


def catalog_diagnostics(paths):
    """Decode fixed diagnostic records while retaining their original bytes."""
    images = [path.read_bytes() for path in paths]
    tables = []
    for name, start, end, record_size in (
        ("fault_triplets", 0x6E27, 0x6E78, 3),
        ("sensor_collection_1", 0x6E78, 0x6E8C, 2),
        ("sensor_collection_2", 0x6E8C, 0x6EA0, 2),
    ):
        versions = []
        for path, data in zip(paths, images):
            raw = data[start:end]
            records = []
            for offset in range(0, len(raw), record_size):
                entry = raw[offset:offset + record_size]
                if record_size == 3:
                    records.append({"address": f"0x{start + offset:04X}",
                                    "code_le16": f"0x{int.from_bytes(entry[:2], 'little'):04X}",
                                    "status": f"0x{entry[2]:02X}"})
                else:
                    records.append({"address": f"0x{start + offset:04X}",
                                    "selector": f"0x{entry[0]:02X}",
                                    "location": f"0x{entry[1]:02X}",
                                    "access": "IRAM" if entry[0] == 0 else "MOVX"})
            versions.append({"rom": str(path.relative_to(ROOT)),
                             "rom_sha256": hashlib.sha256(data).hexdigest(),
                             "raw_hex": raw.hex(" "), "records": records})
        tables.append({"id": name, "start": f"0x{start:04X}",
                       "end_exclusive": f"0x{end:04X}",
                       "record_size": record_size,
                       "record_count": (end - start) // record_size,
                       "byte_order": ("little_endian_code_then_status" if
                                      record_size == 3 else "selector_then_location"),
                       "versions": versions})
    return {"tables": tables,
            "note": "MOVX selector byte chooses space; it is not the XRAM page"}


def expand_curated_catalog(paths, catalog):
    """Attach original ROM bytes and raw-u8 deltas to curated intervals."""
    labels = ("G", "A", "A+", "S88", "S37", "S36")
    if len(paths) != len(labels):
        raise ValueError("expected six catalog ROMs")
    images = [path.read_bytes() for path in paths]
    for label, image in zip(labels, images):
        if len(image) != 32768 or hashlib.sha256(image).hexdigest() != catalog[
                "rom_sha256"][label]:
            raise ValueError(f"ROM size/hash mismatch: {label}")
    tables = []
    for table in catalog["tables"]:
        start = int(table["start"], 16)
        end = int(table["end_exclusive"], 16)
        if not 0 <= start < end <= 32768:
            raise ValueError(f"invalid interval: {table['id']}")
        baseline = images[0][start:end]
        versions = []
        for label, path, image in zip(labels, paths, images):
            if table["pointer_slot"] is not None:
                slot = int(table["pointer_slot"], 16)
                if int.from_bytes(image[slot:slot + 2], "big") != start:
                    raise ValueError(f"pointer mismatch: {table['id']} {label}")
            raw = image[start:end]
            differences = [
                {"offset": f"0x{start + index:04X}", "index": index,
                 "original": f"0x{old:02X}", "variant": f"0x{new:02X}",
                 "raw_u8_delta": new - old,
                 "raw_u8_relative_percent":
                     None if old == 0 else round(100 * (new - old) / old, 4)}
                for index, (old, new) in enumerate(zip(baseline, raw))
                if old != new]
            if label != "G" and len(differences) != table[
                    "different_bytes_vs_G"][label]:
                raise ValueError(f"difference count mismatch: {table['id']} {label}")
            versions.append({"id": label, "rom": str(path.relative_to(ROOT)),
                             "rom_sha256": catalog["rom_sha256"][label],
                             "start": table["start"],
                             "end_exclusive": table["end_exclusive"],
                             "raw_hex": raw.hex(" "),
                             "different_bytes_vs_G": len(differences),
                             "changed_cells_vs_G": differences})
        tables.append({**table, "versions": versions})
    return {"schema_version": 1, "delta_interpretation":
            "unsigned raw-byte arithmetic; not a signed or physical scale",
            "rom_sha256": catalog["rom_sha256"], "tables": tables}


def audit_pointer_catalog_coverage(directory, catalog):
    """Classify directory targets without treating subviews as new tables."""
    catalog_spans = sorted((int(table["start"], 16),
                            int(table["end_exclusive"], 16))
                           for table in catalog["tables"])

    def catalog_covers(start, end):
        cursor = start
        for low, high in catalog_spans:
            if low > cursor:
                break
            cursor = max(cursor, high)
            if cursor >= end:
                return True
        return False

    rows = []
    for region in directory["regions"]:
        slot = region["pointer_slot"]
        versions = region["versions"]
        direct = []
        contained = []
        for table in catalog["tables"]:
            table_start = int(table["start"], 16)
            table_end = int(table["end_exclusive"], 16)
            starts_inside = all(table_start <= int(version["start"], 16) <
                                table_end for version in versions)
            if (slot in ([table.get("pointer_slot")] +
                         table.get("pointer_slots", [])) and starts_inside):
                direct.append(table["id"])
            elif starts_inside and all(
                    int(version["candidate_end_exclusive"], 16) <= table_end
                    for version in versions):
                contained.append(table["id"])
        status = "direct" if direct else "contained" if contained else "unclassified"
        raw = [version["raw_hex"] for version in versions]
        selected = direct or contained
        covered_end = max((int(table["end_exclusive"], 16)
                           for table in catalog["tables"]
                           if table["id"] in selected), default=None)
        candidate_ends = [int(version["candidate_end_exclusive"], 16)
                          for version in versions]
        rows.append({"pointer_slot": slot, "status": status,
                     "covered_by": selected,
                     "selected_entry_fully_covers_candidate_interval":
                         covered_end is not None and
                         all(end <= covered_end for end in candidate_ends),
                     "catalog_fully_covers_candidate_interval": all(
                         catalog_covers(int(version["start"], 16), end)
                         for version, end in zip(versions, candidate_ends)),
                     "outside_selected_entry_suffix":
                         None if covered_end is None or
                         all(end <= covered_end for end in candidate_ends)
                         else {"start": f"0x{covered_end:04X}",
                               "end_exclusive":
                                   f"0x{max(candidate_ends):04X}"},
                     "same_bytes_all_roms": len(set(raw)) == 1,
                     "different_bytes_vs_G": [
                         version["different_bytes_vs_gasoline"]
                         for version in versions[1:]]})
    counts = {status: sum(row["status"] == status for row in rows)
              for status in ("direct", "contained", "unclassified")}
    return {"scope": "pointer-target intervals use provisional next-target ends",
            "counts": counts, "regions": rows}


def catalog_provisional_pointer_targets(directory, coverage):
    """Keep every uncatalogued pointer target visible without inferring a table."""
    by_slot = {row["pointer_slot"]: row for row in coverage["regions"]}
    candidates = []
    for region in directory["regions"]:
        slot = region["pointer_slot"]
        if by_slot[slot]["status"] != "unclassified":
            continue
        versions = []
        for version in region["versions"]:
            raw = bytes.fromhex(version["raw_hex"])
            versions.append({**version,
                             "byte_statistics": {
                                 "min_u8": min(raw), "max_u8": max(raw),
                                 "distinct_u8": len(set(raw)),
                                 "zero_count": raw.count(0),
                                 "ff_count": raw.count(0xFF)}})
        candidates.append({
            "id": f"unclassified_{slot.lower()}",
            "pointer_slot": slot,
            "pointer_encoding": region["pointer_encoding"],
            "extent_basis": region["extent_basis"],
            "dimensions": None,
            "element_encoding": "raw bytes; signedness and table layout unverified",
            "consumer": None,
            "physical_function": None,
            "confidence": {"pointer_and_bytes": "confirmed_all_six",
                           "table_extent_and_function": "unverified"},
            "open_questions": ["Identify the original-code consumer and exact bounds",
                               "Determine layout, inputs, outputs and physical meaning"],
            "same_target_all_roms": region["same_target_all_roms"],
            "versions": versions,
        })
    if len(candidates) != coverage["counts"]["unclassified"]:
        raise ValueError("provisional pointer catalog omits an unclassified slot")
    return {"scope": "unclassified directory targets, not proven tables",
            "count": len(candidates), "candidates": candidates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "build" / "ma17-analysis" / "variants")
    args = parser.parse_args()
    paths = [REFERENCE, *(VARIANTS / name for name in EXPECTED)]
    result = inventory(paths)
    result["sidecar_verification"] = [
        {"text": name, "rom": rom,
         "matches_binary": decode_xxd((VARIANTS / name).read_text()) ==
         (VARIANTS / rom).read_bytes()}
        for name, rom in SIDECARS]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = args.output_dir / "comparisons.json"
    destination.write_text(json.dumps(result, indent=2) + "\n")
    write_heatmap(paths, args.output_dir / "differences.svg")
    write_matrix_heatmap(paths, args.output_dir / "matrix_differences.svg")
    matrix_deltas = catalog_matrix_deltas(paths)
    (args.output_dir / "matrix_deltas.json").write_text(
        json.dumps(matrix_deltas, indent=2) + "\n")
    catalog = catalog_candidate_tables(paths)
    (args.output_dir / "candidate_tables.json").write_text(
        json.dumps(catalog, indent=2) + "\n")
    directory = catalog_pointer_regions(paths)
    (args.output_dir / "pointer_regions.json").write_text(
        json.dumps(directory, indent=2) + "\n")
    diagnostics = catalog_diagnostics(paths)
    (args.output_dir / "diagnostic_tables.json").write_text(
        json.dumps(diagnostics, indent=2) + "\n")
    curated = json.loads((ROOT / "docs" / "MA17_CALIBRATION_CATALOG.json").read_text())
    expanded = expand_curated_catalog(paths, curated)
    (args.output_dir / "calibration_catalog_expanded.json").write_text(
        json.dumps(expanded, indent=2) + "\n")
    coverage = audit_pointer_catalog_coverage(directory, curated)
    (args.output_dir / "pointer_catalog_coverage.json").write_text(
        json.dumps(coverage, indent=2) + "\n")
    provisional = catalog_provisional_pointer_targets(directory, coverage)
    (args.output_dir / "provisional_pointer_catalog.json").write_text(
        json.dumps(provisional, indent=2) + "\n")
    print(f"{len(result['images'])} images; {len(result['pairs'])} pairs; {destination}")
    for pair in result["pairs"]:
        print(f"{pair['left']} <> {pair['right']}: "
              f"{pair['different_bytes']} bytes in {pair['changed_runs']} runs")


if __name__ == "__main__":
    main()
