"""Regressions for MA1.7 variant inventory and byte interval reporting."""

import ast
import copy
import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from compare_ma17_variants import (EXPECTED, REFERENCE, SIDECARS, VARIANTS,
                                   audit_pointer_catalog_coverage,
                                   catalog_provisional_pointer_targets,
                                   catalog_candidate_tables, catalog_diagnostics,
                                   catalog_matrix_deltas,
                                   catalog_pointer_regions, compare, decode_xxd,
                                   expand_curated_catalog,
                                   inventory, write_matrix_heatmap)
from audit_ma17_pointer_lookahead import audit as audit_pointer_lookahead
from audit_ma17_directory_prefix import audit as audit_directory_prefix
from trace_ma17 import parse_ram69_producer, summarize_injection_flow


class CompareVariantsTests(unittest.TestCase):
    def test_directory_prefix_audit_detects_effective_movc_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, rows in (("no_hit", [{"pc": "523B", "address": "7002",
                                            "count": 4}]),
                               ("hit", [{"pc": "523B", "address": "7000",
                                         "count": 3}])):
                output = root / name
                output.mkdir()
                (output / "execution.json").write_text(json.dumps({
                    "firmware_sha256": name,
                    "movc_observation": {"reads": rows}}))
            result = audit_directory_prefix(root)
            self.assertEqual(result["execution_files"], 2)
            self.assertEqual(result["movc_reports"], 2)
            self.assertEqual(result["prefix_read_occurrences"], 3)
            self.assertEqual(result["prefix_read_rows"][0]["address"], "7000")

    def test_7310_rpm_bound_consumer_is_relocated_in_a_family(self):
        gasoline = REFERENCE.read_bytes()
        reference = gasoline[0x2C49:0x2D61]
        self.assertEqual(reference[:13],
                         bytes.fromhex("74 10 93 FA 20 39 03 30 C9 03 02 2C D3"))
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                a_family = name != "G" and "SUN 8817" not in name
                start = 0x2C65 if a_family else 0x2C49
                expected = bytearray(reference)
                if a_family:
                    expected[12] = 0xEF  # LJMP 2CD3h relocates to 2CEFh.
                self.assertEqual(image[start:start + len(reference)], expected)
                self.assertEqual(image[0x7310], 0x38)

    def test_ram70_guard_and_fault_sites_align_across_six_roms(self):
        gasoline = REFERENCE.read_bytes()
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                shift = 0 if name == "G" or name == EXPECTED[2] else 0x1C
                for first, last in ((0x29CB, 0x29D7),
                                    (0x2C0C, 0x2C2C)):
                    self.assertEqual(image[first + shift:last + shift],
                                     gasoline[first:last])
                guard = bytearray(gasoline[0x2C3C:0x2D16])
                scheduler = bytearray(gasoline[0x1F9B:0x205C])
                if shift:
                    # Relocated jump targets and two revised call targets.
                    guard[0x2C48 - 0x2C3C] = 0xE9
                    guard[0x2C55 - 0x2C3C] = 0xEF
                    scheduler[0x2029 - 0x1F9B:0x202B - 0x1F9B] = (
                        bytes.fromhex("53 1C"))
                    scheduler[0x2037 - 0x1F9B:0x2039 - 0x1F9B] = (
                        bytes.fromhex("55 2C"))
                self.assertEqual(image[0x2C3C + shift:0x2D16 + shift],
                                 guard)
                self.assertEqual(image[0x1F9B + shift:0x205C + shift],
                                 scheduler)

    def test_ram6f_pre_movc_guard_sites_align_across_six_roms(self):
        gasoline = REFERENCE.read_bytes()
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                shift = 0 if name == "G" or name == EXPECTED[2] else 0x1C
                self.assertEqual(image[0x11C4:0x11D4],
                                 gasoline[0x11C4:0x11D4])
                for start, end in ((0x299A, 0x29A8), (0x2A78, 0x2AB4),
                                   (0x2AF9, 0x2B05), (0x2B38, 0x2B41),
                                   (0x2B42, 0x2B4F)):
                    self.assertEqual(image[start + shift:end + shift],
                                     gasoline[start:end], (name, start))

    def test_pointer_lookahead_audit_distinguishes_direct_and_crossing_reads(self):
        catalog = {"candidates": [
            {"pointer_slot": "0x7082", "versions": [
                {"start": "0x78A9", "candidate_end_exclusive": "0x78BD"}]},
            {"pointer_slot": "0x7086", "versions": [
                {"start": "0x78D1", "candidate_end_exclusive": "0x78E5"}]}]}
        reads = [
            {"pc": "5350", "opcode": "93", "dptr": "7895",
             "address": "78A9", "value": "00", "count": 3},
            {"pc": "5350", "opcode": "93", "dptr": "78A9",
             "address": "78AA", "value": "00", "count": 2},
            {"pc": "06E1", "opcode": "83", "dptr": "78D1",
             "address": "78D1", "value": "00", "count": 7},
        ]
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / f"trace{i}.json" for i in range(2)]
            for index, path in enumerate(paths):
                path.write_text(json.dumps({"firmware_sha256": f"rom{index}",
                                            "movc_observation": {"reads": reads}}))
            report = audit_pointer_lookahead(catalog, paths)
        self.assertEqual(report["trace_files"], 2)
        self.assertEqual(report["trace_files_by_rom"], {"rom0": 1, "rom1": 1})
        first, second = report["slots"]
        self.assertEqual((first["cross_boundary"]["trace_files"],
                          first["cross_boundary"]["occurrences"]), (2, 6))
        self.assertEqual((first["direct_base"]["trace_files"],
                          first["direct_base"]["occurrences"]), (2, 4))
        self.assertEqual(first["cross_boundary"]["by_rom"], {
            "rom0": {"trace_files": 1, "occurrences": 3},
            "rom1": {"trace_files": 1, "occurrences": 3}})
        self.assertEqual(second["direct_base"]["occurrences"], 0)
        self.assertEqual(second["cross_boundary"]["occurrences"], 0)
        changed = copy.deepcopy(catalog)
        changed["candidates"][0]["versions"].append(
            {"start": "0x78AA", "candidate_end_exclusive": "0x78BD"})
        with self.assertRaisesRegex(ValueError, "variant intervals differ"):
            audit_pointer_lookahead(changed, [])

    def test_t2i1_has_no_setter_in_classified_fiat_code(self):
        sys.path.insert(0, str(ROOT / "disasm51" / "src"))
        from disasm51.instructions import Instructions

        instructions = Instructions()
        write = re.compile(
            r"^(?:(?:mov|orl|anl|xrl|inc|dec|djnz|pop|setb|clr|cpl|jbc)"
            r"\s+(?:T2CON|T2I1)\b|xch\s+A,\s*T2CON\b)", re.I)
        with tempfile.TemporaryDirectory() as directory:
            for name, path in (("G", REFERENCE),
                               *((name, VARIANTS / name) for name in EXPECTED)):
                with self.subTest(rom=name):
                    output = Path(directory) / path.stem
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "roundtrip_8051.py"),
                         str(path), "--output-dir", str(output)],
                        capture_output=True, text=True, timeout=15,
                        check=False)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["roundtrip"], "PASS")
                    source = (output / (path.stem + ".disasm51.asm")).read_text()
                    rom = path.read_bytes()
                    pc = 0
                    writes = []
                    for line in source.splitlines():
                        body = line.split(";", 1)[0].strip()
                        if not body:
                            continue
                        if body.lower().startswith("org\t"):
                            pc = int(body.split()[1].removesuffix("h"), 16)
                        elif body.lower().startswith(("db ", "dw ")):
                            pc += (2 if body.lower().startswith("dw ") else 1) * (
                                body.count(",") + 1)
                        elif line.startswith("\t") and body[0].isalpha():
                            length = instructions[rom[pc]].length
                            if write.search(body):
                                writes.append((pc, rom[pc:pc + length].hex()))
                            pc += length
                    later = "SUN 8817" not in name and name != "G"
                    self.assertEqual(writes, [
                        (0x0AF6, "75c885"),
                        (0x3B9A if later else 0x3B6C, "43c885"),
                        (0x4B7F if later else 0x4ABC, "75c800"),
                        (0x6320, "75c800"), (0x6334, "75c811")])
                    # SAB80C517 T2I1 is bit C9h. Check raw bytes too: a
                    # possible JBC straddles POP 10h and XCH A,R1.
                    for opcode in (0xC2, 0xD2, 0xB2, 0x92):
                        self.assertNotIn(bytes((opcode, 0xC9)), rom)
                    apparent_jbc = 0x5753 if later else 0x5690
                    self.assertEqual(
                        [i for i in range(len(rom) - 1)
                         if rom[i:i + 2] == b"\x10\xC9"], [apparent_jbc])
                    self.assertEqual(rom[apparent_jbc - 1:apparent_jbc + 3],
                                     b"\xD0\x10\xC9\x22")

    def test_7958_rpm_curve_pointer_and_relocated_calls(self):
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                self.assertEqual(image[0x706A:0x706C], bytes.fromhex("79 58"))
                self.assertEqual(image[0x7958:0x7960],
                                 bytes.fromhex("47 03 04 04 EE FF 9A 24"))
                call = "90 70 6A 12 52 F2" if name == "G" or "SUN 8817" in name \
                    else "90 70 6A 12 53 B5"
                base = 0x15AF if name == "G" or "SUN 8817" in name else 0x15FD
                self.assertEqual(image[base:base + 6], bytes.fromhex(call))
        gasoline = REFERENCE.read_bytes()
        self.assertEqual(gasoline[0x15B5:0x15C5],
                         bytes.fromhex("E5 4B 8A F0 A4 E5 4A B5 F0 00 40 02 E5 F0 FB 7A"))

    def test_78fd_7911_matrix_layout_and_g_consumers(self):
        first = bytes.fromhex("80 80 81 82" * 5)
        second = bytes(20)
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                self.assertEqual(image[0x7060:0x7064], bytes.fromhex("78 FD 79 11"))
                self.assertEqual(image[0x78FD:0x7911], first)
                self.assertEqual(image[0x7911:0x7925], second)
        gasoline = REFERENCE.read_bytes()
        self.assertEqual(gasoline[0x3D7E:0x3D84],
                         bytes.fromhex("90 70 60 12 53 2B"))
        self.assertEqual(gasoline[0x3DA8:0x3DB3],
                         bytes.fromhex("79 B1 F7 90 70 62 12 53 2B F5 58"))
        self.assertEqual(gasoline[0x1891:0x1897],
                         bytes.fromhex("79 B1 E7 30 E7 03"))
        self.assertEqual(gasoline[0x1913:0x1919],
                         bytes.fromhex("79 B1 E7 20 E7 03"))
        self.assertEqual(gasoline[0x18FD:0x1900], bytes.fromhex("85 58 3C"))
        self.assertEqual(gasoline[0x1906:0x1909], bytes.fromhex("85 58 3C"))

    def test_78f9_rpm_curve_pointer_and_g_consumer(self):
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                self.assertEqual(image[0x705E:0x7060], bytes.fromhex("78 F9"))
                self.assertEqual(image[0x78F9:0x78FD], bytes.fromhex("00 13 2A 3A"))
        gasoline = REFERENCE.read_bytes()
        self.assertEqual(gasoline[0x3D18:0x3D1E],
                         bytes.fromhex("90 70 5E 12 53 29"))
        self.assertEqual(gasoline[0x3D25:0x3D2A],
                         bytes.fromhex("E5 6F 9A 92 2B"))

    def test_7952_curve_pointer_layout_and_g_consumer(self):
        curve = bytes.fromhex("63 02 5E 2F 10 22")
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                self.assertEqual(image[0x7068:0x706A], bytes.fromhex("79 52"))
                self.assertEqual(image[0x7952:0x7958], curve)
                call = "90 70 68 12 52 F2" if name == "G" or "SUN 8817" in name \
                    else "90 70 68 12 53 B5"
                self.assertEqual(image[0x1274:0x127A], bytes.fromhex(call))
                self.assertEqual(image[0x1282:0x128A],
                                 bytes.fromhex("B5 47 00 50 03 02 12 DE"))
        gasoline = REFERENCE.read_bytes()
        self.assertEqual(gasoline[0x1274:0x127A],
                         bytes.fromhex("90 70 68 12 52 F2"))
        self.assertEqual(gasoline[0x1282:0x128A],
                         bytes.fromhex("B5 47 00 50 03 02 12 DE"))

    def test_79c4_curve_pointer_layout_and_g_consumer(self):
        curve = bytes.fromhex("47 04 3c 64 40 0c 83 82 7e 7c")
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                self.assertEqual(image[0x70D6:0x70D8], bytes.fromhex("79 C4"))
                self.assertEqual(image[0x79C4:0x79CE], curve)
        gasoline = REFERENCE.read_bytes()
        self.assertEqual(gasoline[0x35B7:0x35BD],
                         bytes.fromhex("90 70 D6 12 52 F2"))
        self.assertEqual(gasoline[0x35BD:0x35C3],
                         bytes.fromhex("EA B2 E7 78 E1 F2"))

    def test_74a8_iram63_selector_and_ram46_reader_are_homologous(self):
        gasoline = REFERENCE.read_bytes()
        self.assertEqual(gasoline[0x7002:0x7004], bytes.fromhex("73 D4"))
        self.assertEqual(gasoline[0x700A:0x700C], bytes.fromhex("74 A8"))
        segment = gasoline[0x4773:0x4783]
        reader = gasoline[0x48E0:0x4901]
        curve = gasoline[0x74A8:0x74B2]
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                g_family = name == "G" or "SUN 8817" in name
                expected_segment = bytearray(segment)
                expected_reader = bytearray(reader)
                if not g_family:
                    expected_segment[4:6] = bytes.fromhex("53 3C")
                    expected_reader[11] = 0xE4
                segment_base = 0x4773 if g_family else 0x4830
                reader_base = 0x48E0 if g_family else 0x499D
                self.assertEqual(image[segment_base:segment_base + 16],
                                 expected_segment)
                self.assertEqual(image[reader_base:reader_base + 33],
                                 expected_reader)
                self.assertEqual(image[0x7002:0x7004], bytes.fromhex("73 D4"))
                self.assertEqual(image[0x700A:0x700C], bytes.fromhex("74 A8"))
                self.assertEqual(image[0x74A8:0x74B2], curve)
                self.assertEqual(image[0x7276:0x7279],
                                 bytes.fromhex("25 2E 30"))
                self.assertEqual(image[0x7302], 0x02)
                self.assertEqual(image[0x7309], 0x02)
                self.assertEqual(image[0x7318], 0x10)
                self.assertEqual(image[0x7358], 0x18)

    def test_post_coolant_fallback_constant_and_reader_are_homologous(self):
        gasoline = REFERENCE.read_bytes()
        prefix = gasoline[0x4901:0x4914]
        self.assertEqual(gasoline[0x727F], 0x2E)
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                reader = 0x4901 if name == "G" or "SUN 8817" in name \
                    else 0x49BE
                self.assertEqual(image[reader:reader + len(prefix)], prefix)
                self.assertEqual(image[0x727F], 0x2E)

    def test_air_segment_73c0_and_xram91_producer_are_homologous(self):
        gasoline = REFERENCE.read_bytes()
        self.assertEqual(gasoline[0x708E:0x7090], bytes.fromhex("73 C0"))
        table = bytes.fromhex("62 06 31 1A 18 20 0F 18")
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                base = 0x45F9 if name == "G" or "SUN 8817" in name \
                    else 0x46B6
                target = 0x5279 if base == 0x45F9 else 0x533C
                self.assertEqual(image[0x708E:0x7090], bytes.fromhex("73 C0"))
                self.assertEqual(image[0x73C0:0x73C8], table)
                self.assertEqual(image[base:base + 4], bytes.fromhex("90 70 8E 12"))
                self.assertEqual(image[base + 4:base + 6],
                                 target.to_bytes(2, "big"))
                self.assertEqual(image[base + 6:base + 16],
                                 gasoline[0x45FF:0x4609])

    def test_ram69_producer_parser_preserves_flag_and_output_bytes(self):
        line = ("[RAM69-PATH] tick=123 PC=3B06 A=89 B=A5 DPTR=7200 "
                "R2=00 U8C=89 RAM47=28 RAM69=89 flags2B=38 PSW=00")
        self.assertEqual(parse_ram69_producer(line),
                         {"U8C": "89", "RAM47": "28", "RAM69": "89",
                          "flags2B": "38"})
        self.assertIsNone(parse_ram69_producer(line.replace("PC=3B06", "PC=3AF1")))
        with self.assertRaises(ValueError):
            parse_ram69_producer(line.replace("flags2B=38", "flags2B=GG"))

    def test_matrix_selector_limit_consumers_map_across_code_revisions(self):
        gasoline = REFERENCE.read_bytes()
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                g_code = name == "G" or "SUN 8817" in name
                selector = 0x47E1 if g_code else 0x489E
                guarded = 0x3CFC if g_code else 0x3DB4
                self.assertEqual(image[selector:selector + 20],
                                 gasoline[0x47E1:0x47F5])
                self.assertEqual(image[guarded:guarded + 18],
                                 gasoline[0x3CFC:0x3D0E])
                self.assertEqual(image[0x721C:0x721E], bytes.fromhex("7F 21"))
                self.assertEqual(image[0x72BD], 0x7C)

    def test_7939_writer_and_ram5b_consumer_are_homologous_in_six_roms(self):
        gasoline = bytes.fromhex(
            "13 23 3d 52 1f 37 52 52 52 52 52 52 52 52 52 52 52 52 52 52")
        alcohol = bytes.fromhex(
            "3b 4b 65 7a 47 37 52 52 52 52 52 52 52 52 52 52 52 52 52 52")
        multiply = bytes.fromhex("75 f0 20 e5 5b a4 fc ad f0 22")
        addition = REFERENCE.read_bytes()[0x1958:0x1958 + 38]
        diagnostic = bytes.fromhex("30 c8 20 20 c9 1d ee a2 e7 ef 33")
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                g_layout = name == "G" or "SUN 8817" in name
                writer = 0x3DD6 if g_layout else 0x3E93
                consumer = 0x1863 if g_layout else 0x187F
                guard = 0x18B2 if g_layout else 0x18CE
                add_pc = 0x1958 if g_layout else 0x1974
                serializer = 0x19B6 if g_layout else 0x19D2
                write = 0x19D0 if g_layout else 0x19EC
                self.assertEqual(image[0x7066:0x7068], bytes.fromhex("79 39"))
                self.assertEqual(image[0x7939:0x794D],
                                 alcohol if name in EXPECTED[:2] else gasoline)
                self.assertEqual(image[writer:writer + 8],
                                 bytes.fromhex("90 70 66 12 53 2b f5 5b"
                                               if g_layout else
                                               "90 70 66 12 53 ee f5 5b"))
                self.assertEqual(image[consumer:consumer + len(multiply)], multiply)
                self.assertEqual(image[guard:guard + 6],
                                 bytes.fromhex("20 64 20 12 18 63"
                                               if g_layout else
                                               "20 64 20 12 18 7f"))
                self.assertEqual(image[add_pc:add_pc + len(addition)], addition)
                self.assertEqual(image[serializer:serializer + len(diagnostic)],
                                 diagnostic)
                self.assertEqual(image[write:write + 3],
                                 bytes.fromhex("78 0c f2"))

    def test_upper_ae_curve_and_writer_are_homologous_in_six_roms(self):
        curve = bytes.fromhex("60 6c 78 84 90 9d b1 ba c0")
        g_writer = bytes.fromhex("90 71 5a 12 53 14 ef ca 12 52 59 78 ae f6")
        a_writer = bytes.fromhex("90 71 5a 12 53 d7 ef ca 12 53 1c 78 ae f6")
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = path.read_bytes()
                self.assertEqual(image[0x715A:0x7163], curve)
                if name == "G" or name == EXPECTED[2]:
                    self.assertEqual(image[0x14F0:0x14FE], g_writer)
                else:
                    self.assertEqual(image[0x153E:0x154C], a_writer)

    def test_idle_fault_state_and_countdown_have_homologous_sites(self):
        restore = bytes.fromhex("78 47 e2 a2 e0 92 39 a2 e1 92 3b")
        save = bytes.fromhex("79 47 e3 a2 39 92 e0 a2 3b 92 e1")
        countdown = bytes.fromhex("d2 3b 79 27 74 0a f3 79 3b e3 60 03 14 c2 3b f3")
        for name, firmware in (("G", REFERENCE),
                               *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = firmware.read_bytes()
                save_pc = 0x2D21 if name == "G" or "SUN 8817" in name else 0x2D3D
                countdown_pc = 0x2C0C if name == "G" or "SUN 8817" in name else 0x2C28
                self.assertEqual(image[0x0CB5:0x0CB5 + len(restore)], restore)
                self.assertEqual(image[save_pc:save_pc + len(save)], save)
                self.assertEqual(image[0x0CAB:0x0CB0],
                                 bytes.fromhex("78 3b 74 32 f2"))
                self.assertEqual(image[countdown_pc:countdown_pc + len(countdown)],
                                 countdown)

    def test_lambda_load_gate_rpm_tables_match_in_six_roms(self):
        expected = bytes.fromhex(
            "47 0a 16 14 1c 10 24 14 1a 1a 1c 10 "
            "62 81 a0 a0 a0 44 33 2e 2a 28")
        for name, firmware in (("G", REFERENCE),
                               *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = firmware.read_bytes()
                self.assertEqual(len(image), 32768)
                self.assertEqual(image[0x7090:0x7094],
                                 bytes.fromhex("79 92 79 9e"))
                self.assertEqual(image[0x7992:0x79A8], expected)

    def test_coolant_ram4f_curves_and_pointer_slots_across_six_roms(self):
        gasoline = bytes.fromhex(
            "00 00 04 07 0b 11 16 1a 20 24 "
            "00 02 05 08 0e 12 16 1a 20 24 "
            "00 00 04 07 0b 11 16 1a 20 24")
        alcohol = bytes.fromhex(
            "10 10 14 17 1b 21 26 2a 30 34 "
            "22 24 27 2a 30 34 38 3c 42 46 "
            "22 22 26 29 2d 33 38 3c 42 46")
        for name, firmware in (("G", REFERENCE),
                               *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = firmware.read_bytes()
                self.assertEqual([int.from_bytes(image[slot:slot + 2], "big")
                                  for slot in (0x7030, 0x7032, 0x7034)],
                                 [0x74EE, 0x74F8, 0x7502])
                self.assertEqual(image[0x74EE:0x750C],
                                 alcohol if name in EXPECTED[:2] else gasoline)

    def test_7294_threshold_block_has_homologous_consumer_in_six_roms(self):
        reference = REFERENCE.read_bytes()[0x145E:0x1487]
        for name, firmware in (("G", REFERENCE),
                               *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = firmware.read_bytes()
                pc = 0x145E if name == "G" or "SUN 8817" in name else 0x14AC
                self.assertEqual(image[pc:pc + len(reference)], reference)
                first = "BC" if pc == 0x145E else "38"
                self.assertEqual(image[0x7294:0x729A],
                                 bytes.fromhex(f"{first} 26 3E 68 AF E9"))

    def test_all_six_roms_keep_ram57_direct_writers_separate_from_mode_selector(self):
        for name, path in (("G", REFERENCE),
                           *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(name=name):
                image = path.read_bytes()
                reset = 0x3B94 if name == "G" or "SUN 8817" in name else 0x3BC2
                for address in (0x0B0F, reset):
                    self.assertEqual(image[address:address + 3],
                                     bytes.fromhex("75 57 00"))
                self.assertEqual(image[0x601D:0x6020],
                                 bytes.fromhex("75 57 5A"))
                self.assertEqual(image[0x6078:0x607B],
                                 bytes.fromhex("85 F0 57"))
                for value in (1, 2):
                    self.assertNotIn(bytes((0x75, 0x57, value)), image)

    def test_sun36fd_changes_iex3_vector_and_byte_sum(self):
        s37 = (VARIANTS / "tipo 1.6 alcool27c256 SUN 37a5.bin").read_bytes()
        s36 = (VARIANTS / "tipo 1.6 alcool27c256 SUN 36fd.bin").read_bytes()
        self.assertEqual(len(s37), 32768)
        self.assertEqual(len(s36), 32768)
        self.assertEqual([i for i, (left, right) in enumerate(zip(s37, s36))
                          if left != right], [0x4C, 0x4E, 0x50, 0x54, 0x55])
        self.assertEqual(s37[0x53:0x56], bytes.fromhex("02 00 b0"))
        self.assertEqual(s36[0x53:0x56], bytes.fromhex("02 aa 0d"))
        self.assertEqual(s37[0x07E1:0x07E3], bytes.fromhex("d2 ba"))
        self.assertEqual(s36[0x07B6:0x07E3], s37[0x07B6:0x07E3])
        self.assertEqual(sum(s37) & 0xFFFF, 0x37A5)
        self.assertEqual(sum(s36) & 0xFFFF, 0x36FD)
        # Only if A15 is not decoded does AA0Dh alias 2A0Dh in this ROM.
        self.assertEqual(s36[0x2A0C:0x2A10], bytes.fromhex("30 38 04 80"))

    def test_cc3_scheduler_consumes_iram14_15_in_all_six_roms(self):
        reference = REFERENCE.read_bytes()
        scheduler = reference[0x058E:0x05DD]
        self.assertEqual(scheduler[6:8], bytes.fromhex("e5 14"))
        self.assertEqual(scheduler[10:12], bytes.fromhex("e5 15"))
        for name in EXPECTED:
            with self.subTest(name=name):
                image = (VARIANTS / name).read_bytes()
                self.assertEqual(image[0x058E:0x05DD], scheduler)

    def test_iram4e_factor_consumer_is_identical_in_all_six_roms(self):
        reference = REFERENCE.read_bytes()
        consumer = reference[0x0781:0x07B6]
        self.assertEqual(reference[0x078D:0x0790],
                         bytes.fromhex("90 73 e0"))
        for name in EXPECTED:
            with self.subTest(name=name):
                image = (VARIANTS / name).read_bytes()
                self.assertEqual(image[0x0781:0x07B6], consumer)
                self.assertEqual(image[0x73E0:0x7412],
                                 reference[0x73E0:0x7412])

    def test_alcohol_matrix_consumer_uses_flag_selected_views(self):
        names = ("tipo 1.6 alcool27c256.bin",
                 "tipo 1.6 alcool27c256+1.5bar.bin",
                 "tipo 1.6 alcool27c256 SUN 37a5.bin",
                 "tipo 1.6 alcool27c256 SUN 36fd.bin")
        baseline = (VARIANTS / names[0]).read_bytes()
        slots = ((0x7048, 0x7581), (0x704A, 0x7662),
                 (0x704E, 0x7617), (0x7050, 0x76F8))
        for name in names:
            with self.subTest(name=name):
                image = (VARIANTS / name).read_bytes()
                self.assertEqual(image[0x1339:0x1378],
                                 baseline[0x1339:0x1378])
                self.assertEqual(image[0x1386:0x13CC],
                                 baseline[0x1386:0x13CC])
                self.assertEqual(image[0x7570:0x7580],
                                 baseline[0x7570:0x7580])
                expected_last = (0x24 if "SUN 37a5" in name or "SUN 36fd" in name
                                 else 0x10)
                self.assertEqual(image[0x7580], expected_last)
                self.assertEqual(image[0x3C7D:0x3D04],
                                 baseline[0x3C7D:0x3D04])
                self.assertEqual(image[0x72DF:0x72EA],
                                 bytes.fromhex("78 5c 13 0d 0f 32 41 58 52 5e a0"))
                for slot, target in slots:
                    self.assertEqual(int.from_bytes(image[slot:slot + 2], "big"),
                                     target)

    def test_lambda_bound_update_is_homologous_in_all_six_roms(self):
        reference = REFERENCE.read_bytes()
        boot = reference[0x0D59:0x0D74]
        update = reference[0x1687:0x16EB]
        self.assertEqual(reference[0x733D:0x7343],
                         bytes.fromhex("1e 01 0a 1e 01 0f"))
        for name in EXPECTED:
            with self.subTest(name=name):
                image = (VARIANTS / name).read_bytes()
                self.assertEqual(image[0x733D:0x7343],
                                 reference[0x733D:0x7343])
                self.assertEqual(image.find(boot), 0x0D59)
                expected_update = (0x1687 if "SUN 8817" in name
                                   else 0x16A3)
                self.assertEqual(image.find(update), expected_update)

    def test_sun8817_three_upper_ae_matrices_are_uniform_plus_eight(self):
        gasoline = REFERENCE.read_bytes()
        sun8817 = (VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin").read_bytes()
        for start, end in ((0x7B46, 0x7BBE), (0x7BBE, 0x7C36),
                           (0x7C36, 0x7CAE)):
            with self.subTest(start=hex(start)):
                self.assertEqual(end - start, 8 * 15)
                self.assertTrue(all((sun8817[offset] - gasoline[offset]) & 0xFF
                                    == 8 for offset in range(start, end)))

    def test_flag_selected_120_byte_matrices_have_original_pointer_and_reader(self):
        gasoline = REFERENCE.read_bytes()
        alcohol = (VARIANTS / "tipo 1.6 alcool27c256.bin").read_bytes()
        regions = ((0x70B6, 0x7CAE), (0x70B8, 0x7D26),
                   (0x70BA, 0x7D9E), (0x70CE, 0x7E16))
        for name in EXPECTED:
            image = (VARIANTS / name).read_bytes()
            for slot, start in regions:
                with self.subTest(name=name, start=hex(start)):
                    self.assertEqual(int.from_bytes(image[slot:slot + 2], "big"),
                                     start)
                    self.assertEqual(len(image[start:start + 120]), 8 * 15)
        self.assertEqual(gasoline[0x334D:0x3359], bytes.fromhex(
            "90 70 b6 20 7a 03 90 70 9c 12 53 23"))
        self.assertEqual(alcohol[0x3369:0x3381], bytes.fromhex(
            "90 70 b8 20 5f 03 90 70 b6 20 7a 09 90 70 9e "
            "20 5f 03 90 70 9c 12 53 e6"))
        self.assertEqual(gasoline[0x3830:0x3836],
                         bytes.fromhex("90 70 ce 12 53 2b"))
        self.assertEqual(alcohol[0x385E:0x3864],
                         bytes.fromhex("90 70 ce 12 53 ee"))

    def test_alcohol_7e16_matrix_adds_26_except_zero_endpoints(self):
        gasoline = REFERENCE.read_bytes()[0x7E16:0x7E8E]
        alcohol = (VARIANTS / "tipo 1.6 alcool27c256.bin").read_bytes()[
            0x7E16:0x7E8E]
        self.assertEqual(len(gasoline), len(alcohol))
        self.assertEqual(len(gasoline), 8 * 15)
        self.assertEqual(gasoline[0], alcohol[0])
        self.assertEqual(gasoline[-1], alcohol[-1])
        self.assertEqual(gasoline[0], gasoline[-1])
        self.assertEqual(gasoline[0], 0)
        self.assertTrue(all((changed - original) & 0xFF == 26
                            for original, changed in zip(gasoline[1:-1],
                                                         alcohol[1:-1])))

    def test_runs_include_last_byte_and_exclude_equal_bytes(self):
        result = compare(b"\x00\x01\x02\x03", b"\x00\x09\x02\x08")
        self.assertEqual(result["different_bytes"], 2)
        self.assertEqual(result["identical_percent"], 50)
        self.assertEqual(result["changed_runs"], 2)
        self.assertEqual([(r["start"], r["end_exclusive"])
                          for r in result["changed_intervals"]], [(1, 2), (3, 4)])
        self.assertEqual(result["identical_runs"], [[0, 1], [2, 3]])

    def test_equal_images_and_invalid_size(self):
        result = compare(b"\xff" * 32768, b"\xff" * 32768)
        self.assertEqual(result["changed_runs"], 0)
        self.assertEqual(result["identical_runs"], [[0, 32768]])
        with self.assertRaises(ValueError):
            compare(b"\x00", b"\x00\x00")

    def test_xxd_repeat_marker_and_sidecars(self):
        sample = "00000000  ff ff  |..|\n*\n00000006  01 02  |..|\n00000008\n"
        self.assertEqual(decode_xxd(sample), b"\xff" * 6 + b"\x01\x02")
        with self.assertRaises(ValueError):
            decode_xxd("00000002  00  |.|\n")
        for text_name, rom_name in SIDECARS:
            with self.subTest(text=text_name):
                text = (VARIANTS / text_name).read_text()
                self.assertEqual(decode_xxd(text), (VARIANTS / rom_name).read_bytes())

    def test_inventory_real_roms(self):
        result = inventory([REFERENCE, *(VARIANTS / name for name in EXPECTED)])
        self.assertEqual(len(result["images"]), 6)
        self.assertEqual(len(result["pairs"]), 15)
        self.assertEqual(result["different_bytes_matrix"][1][2], 0)
        self.assertEqual(result["different_bytes_matrix"][4][5], 5)
        for i, row in enumerate(result["different_bytes_matrix"]):
            for j, difference in enumerate(row):
                self.assertEqual(difference, result["different_bytes_matrix"][j][i])
        self.assertEqual(result["images"][0]["sum16"], "0x8817")

    def test_candidate_tables_follow_verified_big_endian_pointers(self):
        paths = [REFERENCE, *(VARIANTS / name for name in EXPECTED)]
        tables = catalog_candidate_tables(paths)["tables"]
        self.assertEqual([table["bytes"] for table in tables], [60, 60, 60])
        self.assertEqual([table["pointer_address"] for table in tables],
                         ["0x70A2", "0x70A4", "0x70A6"])
        self.assertTrue(all(len(table["versions"]) == 6 for table in tables))
        self.assertTrue(all(table["versions"][0]["changed_cells_vs_gasoline"] == 0
                            for table in tables))
        self.assertTrue(all(table["versions"][3]["changed_cells_vs_gasoline"] == 0
                            for table in tables))
        for table in tables:
            self.assertEqual(table["dimensions"], [6, 10])
            reference = table["versions"][0]["raw_u8_grid_6x10"]
            self.assertEqual(len(reference), 6)
            self.assertTrue(all(len(row) == 10 for row in reference))
            for version in table["versions"]:
                cells = version["raw_u8_grid_6x10"]
                deltas = version["raw_u8_delta_vs_gasoline_6x10"]
                self.assertEqual([item - original for row, source in
                                  zip(cells, reference) for item, original in
                                  zip(row, source)],
                                 [item for row in deltas for item in row])
                self.assertEqual(sum(version["changed_cells_by_row"]),
                                 version["changed_cells_vs_gasoline"])

    def test_matrix_heatmap_uses_original_byte_deltas(self):
        paths = [REFERENCE, *(VARIANTS / name for name in EXPECTED)]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "matrix.svg"
            write_matrix_heatmap(paths, output)
            svg = output.read_text()
            self.assertIn('S88 7581: G=47 variant=', svg)
            self.assertIn('A 7ED9: G=13 variant=', svg)
            self.assertIn('raw_delta=', svg)

    def test_sun8817_matrix_delta_distributions(self):
        paths = [REFERENCE, *(VARIANTS / name for name in EXPECTED)]
        tables = catalog_matrix_deltas(paths)["tables"]
        by_start = {row["start"]: row for row in tables}
        self.assertEqual(by_start["0x7581"]["versions"][3]["raw_u8_delta_counts"],
                         {"21": 225})
        self.assertEqual(by_start["0x7662"]["versions"][3]["raw_u8_delta_counts"]["26"],
                         204)
        self.assertEqual(by_start["0x7743"]["versions"][3]["raw_u8_delta_counts"],
                         {"0": 14, "8": 211})
        for table in tables:
            for version in table["versions"]:
                self.assertEqual(sum(version["changed_cells_by_row"]),
                                 version["changed_cells"])

    def test_pointer_directory_aligns_unknown_regions(self):
        paths = [REFERENCE, *(VARIANTS / name for name in EXPECTED)]
        directory = catalog_pointer_regions(paths)
        regions = directory["regions"]
        self.assertEqual(len(regions), 116)
        self.assertTrue(all(row["same_target_all_roms"] for row in regions))
        patterns = directory["raw_equality_patterns"]
        self.assertEqual(sum(len(slots) for slots in patterns.values()), 116)
        self.assertEqual(len(patterns["0,0,0,0,0,0"]), 75)
        self.assertIn("0x70A2", patterns["0,1,1,0,0,0"])
        self.assertEqual([row["value"] for row in directory["leading_word_0x7000"]],
                         ["0x56B4", "0x5777", "0x5777", "0x56B4", "0x5777", "0x5777"])
        terminal = next(row for row in regions
                        if row["pointer_slot"] == "0x70C4")
        self.assertEqual(terminal["versions"][0]["start"], "0x7F8D")
        self.assertEqual(terminal["versions"][0]["candidate_end_exclusive"],
                         "0x8000")
        self.assertEqual(bytes.fromhex(terminal["versions"][1]["raw_hex"][:48])[:9],
                         bytes.fromhex("35 07 01 01 02 04 08 10 FF"))
        self.assertEqual(terminal["versions"][1]["different_bytes_vs_gasoline"], 8)
        segment_bytes = [path.read_bytes()[0x7F8D:0x7F96] for path in paths]
        self.assertEqual(segment_bytes[0], bytes.fromhex("0F 07 01 01 02 04 08 10 E0"))
        self.assertEqual(segment_bytes[1], bytes.fromhex("35 07 01 01 02 04 08 10 FF"))
        self.assertEqual(segment_bytes[2], segment_bytes[1])
        self.assertTrue(all(row == segment_bytes[0]
                            for row in segment_bytes[3:]))
        self.assertEqual({path.read_bytes()[0x7F96:0x7F9D] for path in paths},
                         {bytes.fromhex("01 01 03 03 04 06 09")})
        self.assertEqual(paths[0].read_bytes()[0x527C:0x52C9],
                         paths[1].read_bytes()[0x533F:0x538C])
        selected = next(row for row in regions if row["pointer_slot"] == "0x70A2")
        self.assertEqual(selected["versions"][0]["start"], "0x7ED9")
        self.assertEqual(selected["versions"][0]["candidate_end_exclusive"], "0x7F15")
        for row in regions:
            for version in row["versions"]:
                if version["raw_hex"] is not None:
                    start = int(version["start"], 16)
                    end = int(version["candidate_end_exclusive"], 16)
                    self.assertEqual(len(bytes.fromhex(version["raw_hex"])), end - start)

    def test_pointer_catalog_coverage_tracks_subviews_and_unknowns(self):
        paths = [REFERENCE, *(VARIANTS / name for name in EXPECTED)]
        directory = catalog_pointer_regions(paths)
        curated = json.loads((ROOT / "docs" / "MA17_CALIBRATION_CATALOG.json").read_text())
        coverage = audit_pointer_catalog_coverage(directory, curated)
        self.assertEqual(coverage["counts"],
                         {"direct": 104, "contained": 8, "unclassified": 4})
        rows = {row["pointer_slot"]: row for row in coverage["regions"]}
        self.assertEqual(len(rows), 116)
        for slot, entry in (("0x7024", "conditional_additive_curve_748a"),
                            ("0x7026", "conditional_additive_curve_7494"),
                            ("0x7028", "conditional_additive_curve_749e"),
                            ("0x702C", "conditional_additive_curve_7476"),
                            ("0x702E", "conditional_additive_curve_7480"),
                            ("0x7074", "iram6a_bit0_clear_curve_797a"),
                            ("0x7076", "iram6a_bit0_set_curve_7982")):
            self.assertEqual(rows[slot]["status"], "direct")
            self.assertEqual(rows[slot]["covered_by"], [entry])
        self.assertEqual(rows["0x7006"]["covered_by"], ["constant_curve_741c"])
        self.assertEqual(rows["0x7016"]["covered_by"],
                         ["iram49_direct_index_table_74e4"])
        self.assertEqual(rows["0x7036"]["covered_by"],
                         ["constant_xram_f87f_table_7ae0"])
        self.assertEqual(rows["0x7058"]["covered_by"],
                         ["tps_derived_70_segment_7970"])
        self.assertEqual(rows["0x7054"]["covered_by"],
                         ["iram70_segment_7824"])
        self.assertEqual(rows["0x7056"]["covered_by"],
                         ["rpm_segment_782b"])
        self.assertEqual(rows["0x70DE"]["covered_by"],
                         ["rpm_segment_79e8_r1_gate"])
        self.assertEqual(rows["0x709A"]["covered_by"],
                         ["rpm_curve_to_f8a3_79a8"])
        self.assertEqual(rows["0x70C6"]["covered_by"],
                         ["upper_iram85_curve_79b0"])
        self.assertEqual(rows["0x70C8"]["covered_by"],
                         ["upper_iram86_curve_79ba"])
        self.assertEqual(rows["0x70D6"]["covered_by"],
                         ["iram47_curve_to_xram_f8e1_79c4"])
        self.assertEqual(rows["0x7068"]["covered_by"],
                         ["iram63_gate_curve_7952"])
        self.assertEqual(rows["0x705E"]["covered_by"],
                         ["rpm_curve_to_iram25_bit3_78f9"])
        self.assertEqual(rows["0x7060"]["covered_by"],
                         ["iram70_rpm_matrix_to_upper_b1_78fd"])
        self.assertEqual(rows["0x7062"]["covered_by"],
                         ["iram70_rpm_matrix_to_iram58_7911"])
        self.assertEqual(rows["0x706A"]["covered_by"],
                         ["rpm_curve_to_iram59_7958"])
        self.assertEqual(rows["0x7010"]["covered_by"],
                         ["t2i1_iram46_curve_74c6"])
        for slot, entry in (("0x700C", "iram46_mode0_selector1_curve_74b2"),
                            ("0x700E", "iram46_mode0_selector2_curve_74bc"),
                            ("0x7012", "iram46_mode1_selector1_curve_74d0"),
                            ("0x7014", "iram46_mode1_selector2_curve_74da")):
            self.assertEqual(rows[slot]["covered_by"], [entry])
        self.assertTrue(rows["0x7058"][
            "selected_entry_fully_covers_candidate_interval"])
        for slot, start in (("0x70E0", "0x79F0"), ("0x70E2", "0x7A20"),
                            ("0x70E4", "0x7A50"), ("0x70E6", "0x7A80"),
                            ("0x70E8", "0x7AB0")):
            self.assertEqual(rows[slot]["status"], "direct")
            self.assertTrue(rows[slot]["selected_entry_fully_covers_candidate_interval"])
            self.assertEqual(next(row for row in directory["regions"]
                                  if row["pointer_slot"] == slot)["versions"][0]["start"],
                             start)
        self.assertEqual((rows["0x7050"]["status"],
                          rows["0x7050"]["covered_by"]),
                         ("contained", ["lookup_table_7662"]))
        self.assertEqual((rows["0x7032"]["status"],
                          rows["0x7032"]["covered_by"]),
                         ("direct", ["coolant_iram4f_curves_74ee"]))
        self.assertFalse(rows["0x70C4"][
            "selected_entry_fully_covers_candidate_interval"])
        self.assertTrue(rows["0x70C4"]["catalog_fully_covers_candidate_interval"])
        self.assertEqual(rows["0x70C4"]["outside_selected_entry_suffix"],
                         {"start": "0x7F96", "end_exclusive": "0x8000"})
        baseline_suffix = paths[0].read_bytes()[0x7F96:0x8000]
        self.assertEqual([
            sum(left != right for left, right in zip(
                baseline_suffix, path.read_bytes()[0x7F96:0x8000]))
            for path in paths[1:]], [6, 6, 74, 87, 87])
        self.assertTrue(all(row["selected_entry_fully_covers_candidate_interval"]
                            for row in coverage["regions"]
                            if row["status"] in ("direct", "contained") and
                            row["pointer_slot"] != "0x70C4"))
        self.assertTrue(all(row["same_bytes_all_roms"] and
                            row["different_bytes_vs_G"] == [0] * 5
                            for row in coverage["regions"]
                            if row["status"] == "unclassified"))

    def test_provisional_pointer_catalog_preserves_all_unclassified_bytes(self):
        paths = [REFERENCE, *(VARIANTS / name for name in EXPECTED)]
        directory = catalog_pointer_regions(paths)
        curated = json.loads((ROOT / "docs" / "MA17_CALIBRATION_CATALOG.json").read_text())
        coverage = audit_pointer_catalog_coverage(directory, curated)
        provisional = catalog_provisional_pointer_targets(directory, coverage)
        expected = {row["pointer_slot"] for row in coverage["regions"]
                    if row["status"] == "unclassified"}
        self.assertEqual(provisional["count"], len(expected))
        self.assertEqual({row["pointer_slot"] for row in provisional["candidates"]},
                         expected)
        images = {str(path.relative_to(ROOT)): path.read_bytes() for path in paths}
        for row in provisional["candidates"]:
            slot = int(row["pointer_slot"], 16)
            self.assertIsNone(row["dimensions"])
            self.assertIsNone(row["physical_function"])
            for version in row["versions"]:
                image = images[version["rom"]]
                start = int(version["start"], 16)
                end = int(version["candidate_end_exclusive"], 16)
                raw = bytes.fromhex(version["raw_hex"])
                self.assertEqual(int.from_bytes(image[slot:slot + 2], "big"), start)
                self.assertEqual(raw, image[start:end])
                self.assertEqual(version["rom_sha256"], hashlib.sha256(image).hexdigest())
                self.assertEqual(version["byte_statistics"]["ff_count"], raw.count(0xFF))

    def test_r1_gate_lookup_windows_are_nonzero_even_with_index_spill(self):
        paths = [REFERENCE, *(VARIANTS / name for name in EXPECTED)]
        starts = {0x70E0: 0x79F0, 0x70E2: 0x7A20, 0x70E4: 0x7A50,
                  0x70E6: 0x7A80, 0x70E8: 0x7AB0}
        for path in paths:
            image = path.read_bytes()
            with self.subTest(rom=path.name):
                for slot, expected in starts.items():
                    start = int.from_bytes(image[slot:slot + 2], "big")
                    self.assertEqual(start, expected)
                    span = image[start:start + 96]  # R4 can reach 15*6+5.
                    self.assertEqual(len(span), 96)
                    self.assertGreater(min(span), 0)
                    self.assertEqual(span.count(0), 0)

    def test_diagnostic_byte_order_and_collection_selector(self):
        paths = [REFERENCE, *(VARIANTS / name for name in EXPECTED)]
        fault, first, second = catalog_diagnostics(paths)["tables"]
        self.assertEqual([row["record_count"] for row in (fault, first, second)],
                         [27, 10, 10])
        self.assertEqual(fault["versions"][0]["records"][0],
                         {"address": "0x6E27", "code_le16": "0xFFFF", "status": "0x88"})
        self.assertEqual(first["versions"][0]["records"][0]["location"], "0x63")
        self.assertEqual(first["versions"][0]["records"][0]["access"], "IRAM")
        self.assertEqual(first["versions"][0]["records"][4],
                         {"address": "0x6E80", "selector": "0xF8",
                          "location": "0x0C", "access": "MOVX"})
        for table in (fault, first, second):
            self.assertEqual(len({row["raw_hex"] for row in table["versions"]}), 1)

    def test_sensor_collector_code_is_homologous_across_six_roms(self):
        collector = REFERENCE.read_bytes()[0x4EAF:0x4EC7]
        self.assertEqual(len(collector), 24)
        self.assertEqual(collector[:4], bytes.fromhex("e4 93 a3 70"))
        for name in EXPECTED:
            image = (VARIANTS / name).read_bytes()
            start = 0x4EAF if "SUN 8817" in name else 0x4F72
            with self.subTest(name=name):
                self.assertEqual(image[start:start + len(collector)], collector)

    def test_curated_catalog_matches_original_rom_bytes(self):
        catalog = json.loads((ROOT / "docs" / "MA17_CALIBRATION_CATALOG.json").read_text())
        images = dict(zip(("G", "A", "A+", "S88", "S37", "S36"),
                          [REFERENCE.read_bytes(),
                           *((VARIANTS / name).read_bytes() for name in EXPECTED)]))
        self.assertGreaterEqual(len(catalog["tables"]), 11)
        self.assertEqual(len({table["id"] for table in catalog["tables"]}),
                         len(catalog["tables"]))
        for name, image in images.items():
            self.assertEqual(catalog["rom_sha256"][name], hashlib.sha256(image).hexdigest())
        for table in catalog["tables"]:
            required = ("id", "start", "end_exclusive", "pointer_slot",
                        "dimensions", "format", "axes", "consumer", "output",
                        "confidence", "open_questions", "tests")
            for field in required:
                self.assertIn(field, table, (table.get("id"), field))
            self.assertTrue(table["confidence"], table["id"])
            self.assertIn("physical_function", table["confidence"], table["id"])
            self.assertIn(table["confidence"]["physical_function"],
                          {"unknown", "not_applicable", "unverified",
                           "scanner_hypothesis", "probable RPM axis"}, table["id"])
            self.assertIsInstance(table["open_questions"], list)
            self.assertIsInstance(table["tests"], list)
            start = int(table["start"], 16)
            end = int(table["end_exclusive"], 16)
            self.assertGreater(end, start)
            cells = math.prod(table["dimensions"])
            self.assertIn(end - start - cells, (0, 2), table["id"])
            for name, image in images.items():
                if end - start == cells + 2:
                    self.assertEqual(image[start + 1], table["dimensions"][0],
                                     (table["id"], name, "segment count"))
                raw_hex = table.get(f"raw_{name}_hex")
                if raw_hex:
                    self.assertEqual(bytes.fromhex(raw_hex), image[start:end],
                                     (table["id"], name))
                if table["pointer_slot"] is not None:
                    pointer = int(table["pointer_slot"], 16)
                    self.assertEqual(int.from_bytes(image[pointer:pointer + 2], "big"),
                                     start, (table["id"], name))
                if table.get("nested_pointer_slot"):
                    nested = int(table["nested_pointer_slot"], 16)
                    self.assertEqual(end - start, 225)
                    self.assertEqual(table["dimensions"], [15, 15])
                    self.assertEqual(int.from_bytes(image[nested:nested + 2], "big"),
                                     start + 150, (table["id"], name))
                if name != "G":
                    actual = sum(a != b for a, b in
                                 zip(images["G"][start:end], image[start:end]))
                    self.assertEqual(table["different_bytes_vs_G"][name], actual,
                                     (table["id"], name))
        self.assertEqual(images["G"][0x755C:0x755E], b"\x6f\x0b")
        self.assertEqual(images["G"][0x7569:0x756B], b"\x6f\x05")

    def test_unclassified_nonpointer_intervals_preserve_variant_bytes(self):
        catalog = json.loads((ROOT / "docs" / "MA17_CALIBRATION_CATALOG.json")
                             .read_text())
        images = dict(zip(("G", "A", "A+", "S88", "S37", "S36"),
                          [REFERENCE.read_bytes(),
                           *((VARIANTS / name).read_bytes() for name in EXPECTED)]))
        intervals = {entry["id"]: entry for entry in
                     catalog["unclassified_nonpointer_intervals"]}
        self.assertEqual(set(intervals), {"opaque_6eab_6fca",
                                          "opaque_7199_71f0", "opaque_722c"})
        first = intervals["opaque_6eab_6fca"]
        second = intervals["opaque_7199_71f0"]
        third = intervals["opaque_722c"]
        self.assertEqual((int(first["start"], 16), int(first["end_exclusive"], 16)),
                         (0x6EAB, 0x6FCA))
        self.assertEqual((int(second["start"], 16), int(second["end_exclusive"], 16)),
                         (0x7199, 0x71F0))
        self.assertEqual((int(third["start"], 16), int(third["end_exclusive"], 16)),
                         (0x722C, 0x722D))
        for name, image in images.items():
            self.assertEqual(hashlib.sha256(image).hexdigest(),
                             catalog["rom_sha256"][name])
            targets = {int.from_bytes(image[slot:slot + 2], "big")
                       for slot in range(0x7002, 0x70EA, 2)}
            for entry in intervals.values():
                start, end = int(entry["start"], 16), int(entry["end_exclusive"], 16)
                self.assertFalse(any(start <= target < end for target in targets))
            left, right = image[0x6EAB:0x6FCA], image[0x7199:0x71F0]
            self.assertEqual(image[0x722C], 0 if name in ("G", "S88")
                             else 0x9C, name)
            self.assertEqual(left, b"\xCB" * 286 + b"\xD0" if name in
                             ("A", "A+") else b"\xFF" * 287, name)
            if name in ("S37", "S36"):
                self.assertEqual({byte: right.count(byte) for byte in set(right)},
                                 {0x7F: 62, 0x77: 20, 0x76: 1, 0x67: 4})
            else:
                self.assertEqual(right, b"\xFF" * 87, name)
        self.assertEqual(images["S37"][0x7199:0x71F0],
                         images["S36"][0x7199:0x71F0])

    def test_catalog_covers_changed_data_pages(self):
        catalog = json.loads((ROOT / "docs" / "MA17_CALIBRATION_CATALOG.json")
                             .read_text())
        images = [REFERENCE.read_bytes(),
                  *((VARIANTS / name).read_bytes() for name in EXPECTED)]
        self.assertTrue(all(len(image) == 32768 for image in images))
        changed = {offset for offset in range(0x6E00, 0x8000)
                   if len({image[offset] for image in images}) > 1}
        self.assertEqual(len(changed), 2399)
        entries = catalog["tables"] + catalog["unclassified_nonpointer_intervals"]
        intervals = {entry["id"]: (int(entry["start"], 16),
                                   int(entry["end_exclusive"], 16))
                     for entry in entries if "start" in entry and
                     "end_exclusive" in entry}
        self.assertEqual(intervals["kline_identification_ascii_6e00"],
                         (0x6E00, 0x6E18))
        self.assertEqual(intervals["directory_prefix_pointer_7000"],
                         (0x7000, 0x7002))
        self.assertEqual(intervals["a_matrix_state_bounds_72df"],
                         (0x72DF, 0x72EA))
        covered = set().union(*(set(range(start, end)) for start, end in
                                intervals.values()))
        self.assertEqual(changed - covered, set())
        for image in images:
            self.assertEqual(image[0x6E00:0x6E0C].decode("ascii")[:9],
                             "0261 203 ")
            self.assertEqual(int.from_bytes(image[0x7000:0x7002], "big"),
                             0x56B4 if image[0x722C] == 0 else 0x5777)

    def test_catalog_accounts_for_changed_pointer_tail_as_unknown_and_boot(self):
        catalog = json.loads((ROOT / "docs" / "MA17_CALIBRATION_CATALOG.json").read_text())
        paths = [REFERENCE, *(VARIANTS / name for name in EXPECTED)]
        images = [path.read_bytes() for path in paths]
        regions = catalog_pointer_regions(paths)["regions"]
        covered = set().union(*(set(range(int(table["start"], 16),
                                         int(table["end_exclusive"], 16)))
                                for table in catalog["tables"]))
        changed = set()
        for region in regions:
            for index, version in enumerate(region["versions"][1:], 1):
                start = int(version["start"], 16)
                end = int(version["candidate_end_exclusive"], 16)
                changed.update(address for address in range(start, end)
                               if images[0][address] != images[index][address])
        self.assertTrue(changed)
        self.assertFalse(changed - covered)
        tail_changed = {address for address in changed if address >= 0x7F9D}
        self.assertEqual((len(tail_changed), min(tail_changed)), (87, 0x7F9F))
        by_id = {table["id"]: table for table in catalog["tables"]}
        self.assertEqual((by_id["rom_tail_unclassified_7f9d"]["start"],
                          by_id["rom_tail_unclassified_7f9d"]["end_exclusive"],
                          by_id["boot_xram_constants_7ff6"]["start"],
                          by_id["boot_xram_constants_7ff6"]["end_exclusive"]),
                         ("0x7F9D", "0x7FF6", "0x7FF6", "0x8000"))
        self.assertIsNone(by_id["rom_tail_unclassified_7f9d"]["consumer"])

    def test_unclassified_rom_tail_gap_has_variant_specific_raw_patterns(self):
        paths = [("G", REFERENCE),
                 *((name, VARIANTS / name) for name in EXPECTED)]
        s88_gap = (b"\xff" * 8 + b"\x11" * 4 + b"\x06" * 3 +
                   b"\x11\x10" + b"\x11" * 65 + b"\xff")
        self.assertEqual(len(s88_gap), 83)
        for name, path in paths:
            with self.subTest(rom=name):
                image = path.read_bytes()
                self.assertEqual(len(image), 32768)
                if name == EXPECTED[2]:
                    expected = s88_gap
                elif name in EXPECTED[3:]:
                    expected = b"\xff" * 2 + b"\x00" * 81
                else:
                    expected = b"\xff" * 83
                self.assertEqual(image[0x7F9D:0x7FF0], expected)
                self.assertEqual(image[0x7FF0:0x7FF6],
                                 bytes.fromhex("ff ff ff 07 45 ff"))

    def test_curated_catalog_test_references_exist(self):
        catalog = json.loads((ROOT / "docs" / "MA17_CALIBRATION_CATALOG.json").read_text())
        test_dir = ROOT / "tests"
        known = {f"{suite}.{case}" for path in test_dir.glob("*.cpp")
                 for suite, case in re.findall(
                     r"TEST(?:_F)?\(\s*(\w+)\s*,\s*(\w+)\s*\)",
                     path.read_text())}
        for path in test_dir.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ClassDef):
                    known.update(f"{node.name}.{method.name}" for method in node.body
                                 if isinstance(method, ast.FunctionDef))
        for table in catalog["tables"]:
            self.assertTrue(table.get("tests"), table["id"])
            for reference in table["tests"]:
                name = reference.split(" (", 1)[0]
                if name.endswith(".sh"):
                    self.assertEqual(Path(name).name, name,
                                     (table["id"], reference))
                    script = ROOT / name
                    self.assertTrue(script.is_file() and os.access(script, os.X_OK),
                                    (table["id"], reference))
                else:
                    self.assertIn(name, known, (table["id"], reference))

    def test_expanded_catalog_separates_table_bytes_from_code_revision(self):
        catalog = json.loads((ROOT / "docs" / "MA17_CALIBRATION_CATALOG.json").read_text())
        paths = [REFERENCE, *(VARIANTS / name for name in EXPECTED)]
        expanded = expand_curated_catalog(paths, catalog)
        self.assertEqual(len(expanded["tables"]), len(catalog["tables"]))
        by_id = {table["id"]: table for table in expanded["tables"]}
        factor = {row["id"]: row for row in
                  by_id["iram4e_gate_factor_7426"]["versions"]}
        self.assertEqual(factor["A"]["different_bytes_vs_G"], 9)
        self.assertEqual(factor["A"]["raw_hex"], factor["A+"]["raw_hex"])
        self.assertEqual(factor["G"]["raw_hex"], factor["S37"]["raw_hex"])
        self.assertEqual(factor["G"]["raw_hex"], factor["S36"]["raw_hex"])
        self.assertEqual(factor["A"]["changed_cells_vs_G"][0],
                         {"offset": "0x7427", "index": 1, "original": "0x03",
                          "variant": "0x13", "raw_u8_delta": 16,
                          "raw_u8_relative_percent": 533.3333})
        self.assertEqual(len(by_id["interpolation_table_7f15"]["versions"]), 6)
        zero_baseline = next(cell for row in
                             by_id["flag_selected_matrix_7d26"]["versions"]
                             if row["id"] == "A" for cell in
                             row["changed_cells_vs_G"]
                             if cell["offset"] == "0x7D5D")
        self.assertEqual(zero_baseline["raw_u8_delta"], 0x7C)
        self.assertIsNone(zero_baseline["raw_u8_relative_percent"])
        wrong_hash = copy.deepcopy(catalog)
        wrong_hash["rom_sha256"]["S37"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "ROM size/hash mismatch: S37"):
            expand_curated_catalog(paths, wrong_hash)
        wrong_pointer = copy.deepcopy(catalog)
        wrong_pointer["tables"][0]["pointer_slot"] = "0x7002"
        with self.assertRaisesRegex(ValueError, "pointer mismatch"):
            expand_curated_catalog(paths, wrong_pointer)

    def test_alcohol_code_group_uses_six_by_ten_7f_matrices(self):
        images = {name: (VARIANTS / filename).read_bytes()
                  for name, filename in zip(("A", "A+", "S88", "S37", "S36"),
                                            EXPECTED)}
        reference = images["A"]
        # 32ADh calls the segment reader at 533Ch for both axes; its
        # R0=0Ah stride is used by the second interpolation stage at 53E6h.
        self.assertEqual(reference[0x32AD:0x32B3],
                         bytes.fromhex("90 70 AA 12 53 3C"))
        self.assertEqual(reference[0x32C7:0x32CF],
                         bytes.fromhex("90 70 A2 12 53 E6 B4 F3"))
        self.assertEqual(reference[0x32BE:0x32C7],
                         bytes.fromhex("8C F0 FC EB A8 F0 A4 2D FD"))
        self.assertEqual(reference[0x53E6:0x53E9],
                         bytes.fromhex("12 52 EB"))
        for name in ("A", "A+", "S37", "S36"):
            image = images[name]
            for start, end in ((0x3295, 0x32D8), (0x52EB, 0x5309),
                               (0x533C, 0x53A9), (0x53E6, 0x542A)):
                self.assertEqual(image[start:end], reference[start:end], name)
            self.assertEqual(image[0x7B32:0x7B34], b"\x47\x0a")
            self.assertEqual(image[0x7B3F], 6)
            self.assertEqual(image[0x70A2:0x70A8],
                             bytes.fromhex("7E D9 7F 15 7F 51"))
            self.assertEqual(image[0x7B3E],
                             0xAF if name in ("A", "A+") else 0x7D)
        for name in ("A", "A+"):
            image = images[name]
            self.assertEqual(image[0x7ED9:0x7ED9 + 51],
                             image[0x7F15:0x7F15 + 51])
            self.assertTrue(all(a != b for a, b in zip(
                image[0x7ED9 + 51:0x7F15], image[0x7F15 + 51:0x7F51])))
        for name in ("S37", "S36"):
            image = images[name]
            self.assertEqual(image[0x7ED9:0x7F15], image[0x7F15:0x7F51])


class VariantTraceTests(unittest.TestCase):
    def test_g_s88_full_boot_transmits_five_serial_key_bytes(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        firmware_images = (
            ("G", REFERENCE),
            ("S88", VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"))
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("MA17_")}
        expected = ["55", "46", "85", "89", "13", "BC"]
        with tempfile.TemporaryDirectory() as directory:
            for name, firmware in firmware_images:
                with self.subTest(rom=name):
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--crank-immediate",
                         "--rpm", "1000", "--seconds", "9",
                         "--inject-after", "1", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=15, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    log = (output / "emulator-trace.log").read_text()
                    transmitted = re.findall(
                        r"\[PTY-TX\] Byte 0x([0-9A-F]{2}) written "
                        r"to PTY \(result=1\)", log)
                    self.assertGreaterEqual(len(transmitted), len(expected))
                    self.assertEqual(transmitted[:len(expected)], expected)

    def test_movc_time_buckets_preserve_total_reads_and_rom_addresses(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("MA17_")}
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--trace-movc", "--movc-bucket-ticks", "100000",
                 "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                 "--stop-ticks", "400000", "--seconds", "15",
                 "--output-dir", directory],
                capture_output=True, text=True, env=environment,
                timeout=20, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((Path(directory) / "execution.json").read_text())
            observation = report["movc_observation"]
            self.assertEqual(observation["bucket_ticks"], 100000)
            self.assertEqual(sum(row["count"] for row in observation["buckets"]),
                             observation["total_reads"])
            self.assertEqual({row["start_tick"] for row in
                              observation["buckets"]},
                             {0, 100000, 200000, 300000})
            image = REFERENCE.read_bytes()
            self.assertTrue(all(int(row["address"], 16) < len(image)
                                for row in observation["buckets"]))
            invalid = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--movc-bucket-ticks", "100000", "--output-dir", directory],
                capture_output=True, text=True, env=environment,
                timeout=5, check=False)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("requires --trace-movc", invalid.stderr)

    def test_coolant_sweep_buckets_follow_adc_steps_in_original_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        reports = {}
        edges = {}
        overrides = {}
        sweep_steps = "1200000:180,1700000:200,2200000:220,2700000:200"
        with tempfile.TemporaryDirectory() as directory:
            for name, steps in (("control", None),
                                ("sweep", sweep_steps),
                                ("a_cell", sweep_steps),
                                ("cell_7523", sweep_steps),
                                ("cell_752d", sweep_steps)):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment.update(MA17_ADC10_CH2="400", MA17_ADC10_CH3="160",
                                   MA17_ADC_CH7="63")
                if steps:
                    environment["MA17_ADC10_STEP_CH3"] = steps
                if name == "a_cell":
                    environment["MA17_OVERRIDE_MOVC_AT"] = "5333:7451:4D"
                if name == "cell_7523":
                    environment["MA17_OVERRIDE_MOVC_AT"] = "5333:7523:B5"
                if name == "cell_752d":
                    environment["MA17_OVERRIDE_MOVC_AT"] = "5333:752D:A2"
                output = Path(directory) / name
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--trace-movc", "--movc-bucket-ticks", "100000",
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                     "--stop-ticks", "3200000", "--seconds", "30",
                     "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=35, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                reports[name] = json.loads((output / "execution.json").read_text())
                log = (output / "emulator-trace.log").read_text()
                edges[name] = re.findall(
                    r"\[CC3-PIN\] tick=(\d+).*?value=([01])", log)
                overrides[name] = "PC=5333 mapped=7451 original=33 supplied=4D" in log
        control, sweep = reports["control"], reports["sweep"]
        expected_hash = hashlib.sha256(REFERENCE.read_bytes()).hexdigest()
        self.assertEqual(control["firmware_sha256"], expected_hash)
        self.assertEqual(sweep["firmware_sha256"], expected_hash)
        def before(report):
            counts = Counter()
            for row in report["movc_observation"]["buckets"]:
                if row["start_tick"] < 1200000:
                    counts[row["address"]] += row["count"]
            return counts
        self.assertEqual(before(sweep), before(control))
        self.assertEqual(sum(before(sweep).values()), 73588)
        first = {address: min(row["start_tick"] for row in
                              sweep["movc_observation"]["buckets"]
                              if row["address"] == address)
                 for address in ("7451", "7266", "79D1")}
        self.assertEqual(first, {"7451": 1200000, "7266": 1700000,
                                 "79D1": 2000000})
        self.assertNotIn("7266", {row["address"] for row in
                                    control["movc_observation"]["buckets"]})
        self.assertEqual([row["after"] for row in
                          sweep["sensor_ram_observation"]["63"][-4:]],
                         ["2D", "32", "37", "32"])
        donor = reports["a_cell"]
        self.assertEqual(donor["firmware_sha256"], expected_hash)
        self.assertTrue(overrides["a_cell"])
        self.assertEqual(edges["a_cell"], edges["sweep"])
        self.assertEqual(len(edges["sweep"]), 203)
        self.assertEqual([row["after"] for row in
                          sweep["engine_ram_observation"]["4D"][-4:]],
                         ["2A", "2B", "2D", "2B"])
        self.assertEqual([row["after"] for row in
                          donor["engine_ram_observation"]["4D"][-4:]],
                         ["2B", "30", "37", "30"])
        curve79, curve7b = reports["cell_7523"], reports["cell_752d"]
        self.assertEqual(curve79["firmware_sha256"], expected_hash)
        self.assertEqual(curve7b["firmware_sha256"], expected_hash)
        self.assertEqual(edges["cell_7523"], edges["sweep"])
        self.assertEqual([row["after"] for row in
                          curve79["engine_ram_observation"]["79"][-4:]],
                         ["77", "7F", "8C", "7F"])
        self.assertEqual([row["after"] for row in
                          curve7b["engine_ram_observation"]["7B"][-4:]],
                         ["7D", "82", "89", "82"])
        self.assertEqual([level for _, level in edges["cell_752d"]],
                         [level for _, level in edges["sweep"]])
        self.assertEqual(sum(left != right for left, right in
                             zip(edges["cell_752d"], edges["sweep"])), 5)

    def test_s88_phase_and_upper_a4_split_across_four_original_movc_bytes(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        arms = (("G", REFERENCE, None), ("S88", s88, None),
                ("G_7580", REFERENCE, "5289:7580:25"),
                ("G_7B45", REFERENCE, "5289:7B45:0D"),
                ("G_both", REFERENCE, "5289:7580:25,5289:7B45:0D"),
                ("G_four", REFERENCE, "5289:7580:25,5289:7B45:0D,"
                 "532F:7B46:A1,5333:7B47:A1"))
        reports, edges = {}, {}
        with tempfile.TemporaryDirectory() as directory:
            for name, firmware, override in arms:
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment.update(
                    MA17_ADC10_CH2="400", MA17_ADC10_CH3="160",
                    MA17_ADC_CH7="63", MA17_ADC10_STEP_CH3=(
                        "1200000:180,1700000:200,2200000:220,2700000:200"))
                if override:
                    environment["MA17_OVERRIDE_MOVC_AT"] = override
                output = Path(directory) / name
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--firmware", str(firmware), "--trace-movc",
                     "--movc-bucket-ticks", "100000", "--no-kline-inject",
                     "--crank-immediate", "--rpm", "1000",
                     "--stop-ticks", "3200000", "--seconds", "30",
                     "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=35, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                reports[name] = json.loads((output / "execution.json").read_text())
                edges[name] = re.findall(
                    r"\[CC3-PIN\] tick=(\d+).*?value=([01])",
                    (output / "emulator-trace.log").read_text())
                self.assertEqual(reports[name]["firmware_sha256"],
                                 hashlib.sha256(firmware.read_bytes()).hexdigest())
        self.assertEqual(len(edges["S88"]), 203)
        for name in ("G", "G_7580", "G_7B45"):
            self.assertNotEqual(edges[name], edges["S88"], name)
        for name in ("G_both", "G_four"):
            self.assertEqual(edges[name], edges["S88"], name)
            self.assertEqual(reports[name]["pc_coverage"],
                             reports["S88"]["pc_coverage"])
            self.assertEqual(reports[name]["movc_observation"]["buckets"],
                             reports["S88"]["movc_observation"]["buckets"])
        self.assertNotEqual(reports["G_both"]["engine_ram_observation"]["A4"],
                            reports["S88"]["engine_ram_observation"]["A4"])
        for key in ("sensor_ram_observation", "engine_ram_observation",
                    "output_latches", "cc3_observation"):
            self.assertEqual(reports["G_four"][key], reports["S88"][key], key)
        raw = {row["mapped"]: row["value"] for row in
               reports["G_four"]["movc_observation"]["reads"]
               if row["mapped"] in ("7580", "7B45", "7B46", "7B47")}
        self.assertEqual(raw, {"7580": "10", "7B45": "05",
                               "7B46": "99", "7B47": "99"})

    def test_s88_phase_cell_pair_reproduces_adc3_sweep_at_1500_rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        arms = (("G", REFERENCE, None), ("S88", s88, None),
                ("G_7580", REFERENCE, "5289:7580:25"),
                ("G_7B45", REFERENCE, "5289:7B45:0D"),
                ("G_both", REFERENCE, "5289:7580:25,5289:7B45:0D"),
                ("G_four", REFERENCE, "5289:7580:25,5289:7B45:0D,"
                 "532F:7B46:A1,5333:7B47:A1"))
        reports, edges, sensor_updates, cc3_entries, resume_pcs = {}, {}, {}, {}, {}
        with tempfile.TemporaryDirectory() as directory:
            for name, firmware, override in arms:
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment.update(
                    MA17_ADC10_CH2="400", MA17_ADC10_CH3="160",
                    MA17_ADC_CH7="63", MA17_ADC10_STEP_CH3=(
                        "900000:180,1300000:200,1700000:220,2100000:200"),
                    MA17_TRACE_PC_WINDOW="901820:901880")
                if override:
                    environment["MA17_OVERRIDE_MOVC_AT"] = override
                output = Path(directory) / name
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--firmware", str(firmware), "--trace-movc",
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1500",
                     "--stop-ticks", "2400000", "--seconds", "30",
                     "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=35, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                reports[name] = json.loads((output / "execution.json").read_text())
                trace = (output / "emulator-trace.log").read_text()
                edges[name] = re.findall(
                    r"\[CC3-PIN\] tick=(\d+).*?value=([01])", trace)
                sensor_updates[name] = re.findall(
                    r"\[SENSOR-RAM\] tick=(\d+) addr=63 value=28->2D", trace)
                cc3_entries[name] = re.findall(
                    r"\[CC3-ENTRY\] instr=923099 .*?IRAM14_15=([0-9A-F]{4})", trace)
                resume_pcs[name] = re.findall(
                    r"\[PC-WINDOW\] tick=901853 PC=([0-9A-F]{4})", trace)
                self.assertEqual(reports[name]["firmware_sha256"],
                                 hashlib.sha256(firmware.read_bytes()).hexdigest())
        reference_edges = edges["S88"]
        self.assertEqual(len(reference_edges), 226)
        self.assertEqual(edges["G"][76], reference_edges[76])
        self.assertEqual((int(edges["G"][77][0]) - int(edges["G"][76][0]),
                          int(reference_edges[77][0]) -
                          int(reference_edges[76][0])), (4901, 4765))
        self.assertEqual(edges["G_7580"][76:78], reference_edges[76:78])
        self.assertEqual({name: sensor_updates[name] for name in
                          ("G", "S88", "G_7580", "G_both")},
                         {"G": ["903126"], "S88": ["923594"],
                          "G_7580": ["923597"], "G_both": ["923594"]})
        self.assertEqual({name: cc3_entries[name] for name in
                          ("G", "S88", "G_7580", "G_both")},
                         {"G": ["04CC"], "S88": ["04AA"],
                          "G_7580": ["04AA"], "G_both": ["04AA"]})
        self.assertEqual({name: resume_pcs[name] for name in
                          ("G", "S88", "G_7580")},
                         {"G": ["5246"], "S88": ["4697"],
                          "G_7580": ["468E"]})
        self.assertEqual({name: sum(a == b for a, b in
                                   zip(edges[name], reference_edges))
                          for name in ("G", "G_7580", "G_7B45", "G_both")},
                         {"G": 215, "G_7580": 221,
                          "G_7B45": 211, "G_both": 226})
        self.assertEqual(edges["G_four"], reference_edges)
        self.assertEqual(reports["G_both"]["pc_coverage"],
                         reports["S88"]["pc_coverage"])
        self.assertNotEqual(reports["G_both"]["engine_ram_observation"]["A4"],
                            reports["S88"]["engine_ram_observation"]["A4"])
        self.assertEqual(reports["G_four"]["engine_ram_observation"],
                         reports["S88"]["engine_ram_observation"])

    def test_s88_phase_cell_pair_reproduces_adc3_sweep_at_3000_rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        arms = (("G", REFERENCE, None), ("S88", s88, None),
                ("G_7580", REFERENCE, "5289:7580:25"),
                ("G_7B45", REFERENCE, "5289:7B45:0D"),
                ("G_both", REFERENCE, "5289:7580:25,5289:7B45:0D"),
                ("G_four", REFERENCE, "5289:7580:25,5289:7B45:0D,"
                 "532F:7B46:A1,5333:7B47:A1"))
        reports, edges = {}, {}
        with tempfile.TemporaryDirectory() as directory:
            for name, firmware, override in arms:
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment.update(
                    MA17_ADC10_CH2="400", MA17_ADC10_CH3="160",
                    MA17_ADC_CH7="63", MA17_ADC10_STEP_CH3=(
                        "900000:180,1300000:200,1700000:220,2100000:200"))
                if override:
                    environment["MA17_OVERRIDE_MOVC_AT"] = override
                output = Path(directory) / name
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--firmware", str(firmware), "--trace-movc",
                     "--no-kline-inject", "--crank-immediate", "--rpm", "3000",
                     "--stop-ticks", "2400000", "--seconds", "30",
                     "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=35, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                reports[name] = json.loads((output / "execution.json").read_text())
                edges[name] = re.findall(
                    r"\[CC3-PIN\] tick=(\d+).*?value=([01])",
                    (output / "emulator-trace.log").read_text())
                self.assertEqual(reports[name]["firmware_sha256"],
                                 hashlib.sha256(firmware.read_bytes()).hexdigest())
        reference_edges = edges["S88"]
        self.assertEqual(len(reference_edges), 456)
        self.assertEqual({name: sum(a == b for a, b in
                                   zip(edges[name], reference_edges))
                          for name in ("G", "G_7580", "G_7B45", "G_both")},
                         {"G": 427, "G_7580": 435,
                          "G_7B45": 425, "G_both": 456})
        self.assertEqual(edges["G_four"], reference_edges)
        self.assertEqual(reports["G_both"]["movc_observation"]["total_reads"],
                         reports["S88"]["movc_observation"]["total_reads"])
        self.assertNotEqual(reports["G_both"]["engine_ram_observation"]["A4"],
                            reports["S88"]["engine_ram_observation"]["A4"])
        self.assertEqual(reports["G_four"]["engine_ram_observation"],
                         reports["S88"]["engine_ram_observation"])

    def test_7958_ordinate_changes_first_g_iram59_write(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        hashes = set()
        with tempfile.TemporaryDirectory() as directory:
            for name, override, ordinate, bounded in (
                    ("native", None, "FF", "05"),
                    ("ordinate_40", "532F:795D:40", "40", "01")):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment.update({f"MA17_ADC_CH{i}": str(value) for i, value
                                    in enumerate((120, 130, 100, 4, 90, 40, 95, 63))})
                environment["MA17_TRACE_CURVE_7958_PATH"] = "1"
                if override:
                    environment["MA17_OVERRIDE_MOVC_AT"] = override
                output = Path(directory) / name
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "1000", "--stop-ticks", "120000",
                     "--seconds", "10", "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=15, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                reads = [row for row in report["movc_observation"]["reads"]
                         if row["pc"] == "532F" and row["address"] == "795D"]
                self.assertEqual(len(reads), 1)
                self.assertEqual(reads[0]["value"], "FF")
                lines = [line for line in (output / "emulator-trace.log").read_text().splitlines()
                         if line.startswith("[CURVE7958-PATH]")]
                self.assertGreaterEqual(len(lines), 4)
                self.assertIn(f"PC=15B5 A={ordinate} R1=00 R2={ordinate}", lines[0])
                self.assertIn(f"PC=15C3 A={bounded}", lines[1])
                self.assertIn(f"PC=15CF A={bounded} R1=00 R2=00 R3={bounded}", lines[2])
                self.assertIn(f"PC=1644 A={bounded} R1=00 R2=00 R3={bounded}",
                              lines[3])
                self.assertEqual(report["engine_ram_observation"]["59"][0]["after"],
                                 bounded)
                hashes.add(report["emulator_sha256"])
        self.assertEqual(len(hashes), 1)

    def test_7958_cc3_pulses_are_mediated_by_early_59_5a_reads(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        pulse = re.compile(r"\[CC3-PIN\] tick=(\d+) PC=[0-9A-F]+ value=([01])")
        widths = {}
        published = {}
        hashes = set()
        with tempfile.TemporaryDirectory() as directory:
            for name, donor, supply in (
                    ("native", False, None),
                    ("donor", True, None),
                    ("late_supply", True, "1D5C:59:05,1D5E:5A:00"),
                    ("early_59", True, "1C99:59:05"),
                    ("early_5a", True, "1C9B:5A:00"),
                    ("early_both", True, "1C99:59:05,1C9B:5A:00"),
                    ("native_early_supply", False,
                     "1C99:59:05,1C9B:5A:00")):
                with self.subTest(name=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    environment.update({f"MA17_ADC_CH{i}": str(value)
                                        for i, value in enumerate(
                                            (120, 130, 100, 4, 90, 40, 95, 63))})
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_AT"] = "532F:795D:40"
                    if supply:
                        environment["MA17_OVERRIDE_IRAM_READ_AT"] = supply
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", "1000",
                         "--stop-ticks", "400000", "--seconds", "10",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=15, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    hashes.add(report["emulator_sha256"])
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    log = (output / "emulator-trace.log").read_text()
                    published[name] = next(
                        re.search(r"R2=([0-9A-F]{2}) R3=([0-9A-F]{2})", line)
                        for line in log.splitlines()
                        if line.startswith("[INJECTION-FLOW]") and
                        "PC=1ED3" in line and "RAM63=04" in line)
                    edges = [(int(tick), value) for tick, value in pulse.findall(log)]
                    widths[name] = [edges[i + 1][0] - edges[i][0]
                                    for i in range(len(edges) - 1)
                                    if edges[i][1] == "0" and edges[i + 1][1] == "1"][:3]
                    if supply:
                        for entry in supply.split(","):
                            pc, address, _ = entry.split(":")
                            self.assertIn(
                                f"[IRAM-READ-OVERRIDE] PC={pc} addr={address}", log)
        self.assertEqual(len(hashes), 1)
        self.assertEqual(widths["native"], [5381, 5380, 5380])
        self.assertEqual(widths["native_early_supply"], widths["native"])
        self.assertEqual(widths["donor"], [4373, 4372, 4372])
        self.assertEqual(widths["late_supply"], widths["donor"])
        self.assertEqual(widths["early_59"], [5397, 5396, 5396])
        self.assertEqual(widths["early_5a"], [4357, 4356, 4356])
        self.assertEqual(widths["early_both"], widths["native"])
        for name, pair in (("native", ("05", "44")),
                           ("donor", ("04", "48")),
                           ("early_59", ("05", "48")),
                           ("early_5a", ("04", "44")),
                           ("early_both", ("05", "44"))):
            self.assertEqual(published[name].groups()[::-1], pair)

    def test_7958_early_cc3_mediation_repeats_across_rpm_and_adc_states(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        pulse = re.compile(r"\[CC3-PIN\] tick=(\d+) PC=[0-9A-F]+ value=([01])")
        widths = {}
        hashes = set()
        scenarios = (
            (3000, 130, 4, 95, "1C99:59:05,1C9B:5A:00",
             [5381, 5381, 5381], [4373, 4373, 4373]),
            (1000, 40, 4, 95, "1C99:59:05,1C9B:5A:00",
             [6309, 6308, 6308], [5301, 5300, 5300]),
            (1000, 130, 40, 95, "1C99:59:06,1C9B:5A:00",
             [6405, 6404, 6404], [4765, 4764, 4764]),
            (1000, 130, 4, 180, "1C99:59:06,1C9B:5A:7C",
             [6901, 6900, 6900], [3973, 3972, 3972]))
        with tempfile.TemporaryDirectory() as directory:
            for scenario, donor, supply in (
                    (scenario, donor, supply)
                    for scenario in scenarios
                    for donor, supply in ((False, False), (True, False),
                                          (True, True), (False, True))):
                rpm, adc1, adc3, adc6, supplied, _, _ = scenario
                with self.subTest(rpm=rpm, adc1=adc1, adc3=adc3, adc6=adc6,
                                  donor=donor,
                                  supply=supply):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    environment.update({f"MA17_ADC_CH{i}": str(value)
                                        for i, value in enumerate(
                                            (120, adc1, 100, adc3, 90, 40, adc6, 63))})
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_AT"] = "532F:795D:40"
                    if supply:
                        environment["MA17_OVERRIDE_IRAM_READ_AT"] = supplied
                    output = Path(directory) / (
                        f"{rpm}_{adc1}_{adc3}_{adc6}_{donor}_{supply}")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", str(rpm), "--stop-ticks", "1000000",
                         "--seconds", "10", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=20, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    hashes.add(report["emulator_sha256"])
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    edges = [(int(tick), value) for tick, value in pulse.findall(
                        (output / "emulator-trace.log").read_text())]
                    widths[rpm, adc1, adc3, adc6, donor, supply] = [
                        edges[i + 1][0] - edges[i][0]
                        for i in range(len(edges) - 1)
                        if edges[i][1] == "0" and edges[i + 1][1] == "1"][:3]
        self.assertEqual(len(hashes), 1)
        for scenario in scenarios:
            rpm, adc1, adc3, adc6 = scenario[:4]
            native, donor = scenario[-2:]
            self.assertEqual(widths[rpm, adc1, adc3, adc6, False, False], native)
            self.assertEqual(widths[rpm, adc1, adc3, adc6, False, True], native)
            self.assertEqual(widths[rpm, adc1, adc3, adc6, True, False], donor)
            self.assertEqual(widths[rpm, adc1, adc3, adc6, True, True], native)

    def test_78fd_b1_reader_branch_and_7911_58_reader_reachability(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        hashes = set()
        cases = (("native", None, "00", "00", False),
                 ("first_40", "532F:78FD:40", "D0", "00", True),
                 ("second_40", "532F:7911:40", "00", "30", False))
        with tempfile.TemporaryDirectory() as directory:
            for name, override, upper_b1, ram58, extra_branch in cases:
                with self.subTest(name=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    environment.update({f"MA17_ADC_CH{i}": str(value) for i, value
                                        in enumerate((120, 130, 100, 4, 90, 40, 95, 63))})
                    environment["MA17_TRACE_B1_58_READERS"] = "1"
                    if override:
                        environment["MA17_OVERRIDE_MOVC_AT"] = override
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", "1000", "--stop-ticks", "1400000",
                         "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=25, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    lines = [line for line in (output / "emulator-trace.log").read_text().splitlines()
                             if line.startswith("[B1-58-READER]")]
                    self.assertEqual(sum("PC=1894" in line for line in lines), 16)
                    self.assertEqual(sum("PC=1897" in line for line in lines),
                                     16 if extra_branch else 0)
                    self.assertIn(f"PC=1894 A={upper_b1} U_B1={upper_b1} "
                                  f"RAM58={ram58} RAM3C=00", lines[0])
                    hits = set((output / "pc-hits.txt").read_text().splitlines())
                    self.assertNotIn("18FD", hits)
                    self.assertNotIn("1906", hits)
                    hashes.add(report["emulator_sha256"])
        self.assertEqual(len(hashes), 1)

    def test_78fd_7911_matrix_cells_write_separate_iram_destinations(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        hashes = set()
        cases = (("native", None, "80", "00", "00"),
                 ("first_40", "532F:78FD:40", "50", "D0", "00"),
                 ("second_40", "532F:7911:40", "80", "00", "30"))
        with tempfile.TemporaryDirectory() as directory:
            for name, override, r2, upper_b1, ram58 in cases:
                with self.subTest(name=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    environment["MA17_TRACE_78FD_7911_OUTPUTS"] = "1"
                    if override:
                        environment["MA17_OVERRIDE_MOVC_AT"] = override
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", "1000", "--stop-ticks", "600000",
                         "--seconds", "15", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=20, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    for address, original in (("78FD", "80"), ("7911", "00")):
                        reads = [row for row in report["movc_observation"]["reads"]
                                 if row["pc"] == "532F" and row["address"] == address]
                        self.assertTrue(reads)
                        self.assertTrue(all(row["value"] == original for row in reads))
                    lines = [line for line in (output / "emulator-trace.log").read_text().splitlines()
                             if line.startswith("[MATRIX78FD-7911]")]
                    self.assertGreaterEqual(len(lines), 4)
                    self.assertIn(f"PC=3D84 A={r2} R2={r2}", lines[0])
                    self.assertIn(f"PC=3DAB A={upper_b1} R2={upper_b1}", lines[1])
                    self.assertIn(f"U_B1={upper_b1}", lines[1])
                    self.assertIn(f"PC=3DB3 A={ram58} R2={ram58}", lines[3])
                    self.assertIn(f"RAM58={ram58} U_B1={upper_b1}", lines[3])
                    hashes.add(report["emulator_sha256"])
        self.assertEqual(len(hashes), 1)

    def test_78f9_ordinate_is_masked_by_iram28_bit1_in_late_g_state(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        hashes = set()
        with tempfile.TemporaryDirectory() as directory:
            for name, override, expected_r2 in (
                    ("native", None, "05"),
                    ("ordinate_80", "532F:78F9:80", "65")):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment["MA17_TRACE_CURVE_78F9_GATE"] = "1"
                environment["MA17_TRACE_CURVE_78F9_LATE"] = "1"
                if override:
                    environment["MA17_OVERRIDE_MOVC_AT"] = override
                output = Path(directory) / name
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "1000", "--stop-ticks", "2400000",
                     "--seconds", "30", "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=35, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                lines = [line for line in (output / "emulator-trace.log").read_text().splitlines()
                         if line.startswith("[CURVE78F9-GATE]")]
                self.assertGreaterEqual(len(lines), 2)
                self.assertIn(f"PC=3D1E R2={expected_r2} R5=00 R6=40", lines[0])
                self.assertIn("RAM47=28 RAM6F=27 F25=76 F28=06 F2E=84", lines[0])
                self.assertIn(f"PC=3D2A R2={expected_r2}", lines[1])
                self.assertIn("F25=76 F28=06 F2E=84", lines[1])
                hashes.add(report["emulator_sha256"])
        self.assertEqual(len(hashes), 1)

    def test_78f9_ordinate_sets_iram25_bit3_when_unmasked(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        emulators = set()
        with tempfile.TemporaryDirectory() as directory:
            for name, override, r2, f25 in (
                    ("native", None, "00", "17"),
                    ("ordinate_80", "532F:78F9:80", "80", "1F")):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment["MA17_TRACE_CURVE_78F9_GATE"] = "1"
                if override:
                    environment["MA17_OVERRIDE_MOVC_AT"] = override
                output = Path(directory) / name
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "1000", "--stop-ticks", "600000",
                     "--seconds", "15", "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=20, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                reads = [row for row in report["movc_observation"]["reads"]
                         if row["pc"] == "532F" and row["address"] == "78F9"]
                self.assertEqual(len(reads), 1)
                self.assertEqual(reads[0]["value"], "00")
                gates = [line for line in (output / "emulator-trace.log").read_text().splitlines()
                         if line.startswith("[CURVE78F9-GATE]")]
                self.assertGreaterEqual(len(gates), 2)
                self.assertIn(f"PC=3D1E R2={r2} R5=00 R6=00", gates[0])
                self.assertIn("RAM6F=73 F25=17 F28=00 F2E=87", gates[0])
                self.assertIn(f"PC=3D2A R2={r2}", gates[1])
                self.assertIn(f"F25={f25} F28=00 F2E=87", gates[1])
                emulators.add(report["emulator_sha256"])
        self.assertEqual(len(emulators), 1)

    def test_7952_curve_ordinate_switches_g_1285_branch(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        results = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, override, value, branch in (
                    ("native", None, "10", "12DE"),
                    ("ordinate_80", "532F:7956:80", "80", "128A")):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment["MA17_TRACE_CURVE_7952_GATE"] = "1"
                if override:
                    environment["MA17_OVERRIDE_MOVC_AT"] = override
                output = Path(directory) / name
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "1000", "--stop-ticks", "600000",
                     "--seconds", "15", "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=20, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                reads = [row for row in report["movc_observation"]["reads"]
                         if row["pc"] == "532F" and row["address"] == "7956"]
                self.assertEqual(len(reads), 1)
                self.assertEqual(reads[0]["value"], "10")
                gates = [line for line in (output / "emulator-trace.log").read_text().splitlines()
                         if line.startswith("[CURVE7952-GATE]")]
                self.assertEqual(len([line for line in gates if "PC=1285" in line]), 33)
                self.assertIn(f"PC=1285 A={value} RAM47=28 RAM63=50", gates[0])
                self.assertIn(f"PC={branch}", gates[1])
                results[name] = (report["emulator_sha256"], report["stop_ticks_observed"])
        self.assertEqual(results["native"], results["ordinate_80"])

    def test_79c4_movc_ordinate_changes_xram_f8e1_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        results = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, override, expected in (("native", None, "03"),
                                             ("ordinate_40", "532F:79CA:40", "C0")):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment["MA17_TRACE_CURVE_79C4_WRITE"] = "1"
                if override:
                    environment["MA17_OVERRIDE_MOVC_AT"] = override
                output = Path(directory) / name
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "1000", "--stop-ticks", "600000",
                     "--seconds", "15", "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=20, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                reads = [row for row in report["movc_observation"]["reads"]
                         if row["pc"] == "532F" and row["address"] == "79CA"]
                self.assertEqual(len(reads), 1)
                self.assertGreater(int(reads[0]["count"]), 0)
                self.assertEqual(reads[0]["value"], "83")
                writes = [line for line in (output / "emulator-trace.log").read_text().splitlines()
                          if line.startswith("[CURVE79C4-WRITE]")]
                self.assertTrue(writes)
                self.assertIn(f"addr=F8E1 previous=00 value={expected}", writes[0])
                results[name] = (report["emulator_sha256"], report["stop_ticks_observed"])
        self.assertEqual(results["native"], results["ordinate_40"])

    def test_constant_741c_curve_natural_indices_stay_in_bounds_in_two_states(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (("baseline_1000", 1000, 40, 95, 80, {0, 1, 3, 4}),
                 ("high_tps_4000_cold", 4000, 180, 247, 4, {0, 1}))
        with tempfile.TemporaryDirectory() as directory:
            for name, rpm, adc0, adc6, adc3, expected_offsets in cases:
                with self.subTest(name=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    environment.update({"MA17_ADC_CH0": str(adc0),
                                        "MA17_ADC_CH2": "100",
                                        "MA17_ADC_CH3": str(adc3),
                                        "MA17_ADC_CH5": "40",
                                        "MA17_ADC_CH6": str(adc6),
                                        "MA17_ADC_CH7": "63"})
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", str(rpm),
                         "--trace-movc", "--stop-ticks", "2400000",
                         "--seconds", "30", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["dptr"] == "741C" and row["pc"] in ("532F", "5333")]
                    self.assertTrue(reads)
                    self.assertEqual({int(row["mapped"], 16) - 0x741C for row in reads},
                                     expected_offsets)
                    self.assertTrue(all(int(row["mapped"], 16) <= 0x7425
                                        for row in reads))

    def test_mode_one_two_last_column_difference_is_reached(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        image = REFERENCE.read_bytes()
        first = image[0x7D26:0x7D9E]
        second = image[0x7D9E:0x7E16]
        self.assertEqual([index for index, pair in enumerate(zip(first, second))
                          if pair[0] != pair[1]],
                         [14, 29, 44, 59, 74, 89, 104])
        cases = (("1", 0x7D26, "63", "18", "20", "7D", 6017),
                 ("2", 0x7D9E, "52", "14", "1C", "B2", 6016))
        with tempfile.TemporaryDirectory() as directory:
            for mode, base, cell, a4, ram69, ram34, p5 in cases:
                with self.subTest(mode=mode):
                    output = Path(directory) / mode
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    environment.update({"MA17_ADC_CH0": "180",
                                        "MA17_ADC_CH2": "100",
                                        "MA17_ADC_CH3": "80",
                                        "MA17_ADC_CH6": "247",
                                        "MA17_ADC_CH7": "63",
                                        "MA17_OVERRIDE_RAM57": mode,
                                        "MA17_OVERRIDE_RPM_SELECTOR": "0E"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", "750", "--stop-ticks", "2400000",
                         "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(image).hexdigest())
                    self.assertEqual(report["rpm_selector_override_hex"], "0E")
                    self.assertIn("[RPM-SELECTOR-OVERRIDE] RAM47=1E BC=0E",
                                  (output / "emulator-trace.log").read_text())
                    observed = [row for row in report["movc_observation"]["reads"]
                                if int(row["address"], 16) == base + 104]
                    self.assertEqual(sum(row["count"] for row in observed), 212)
                    self.assertEqual({row["value"] for row in observed}, {cell})
                    for address, value in (("A4", a4), ("69", ram69),
                                           ("34", ram34)):
                        self.assertEqual(report["engine_ram_observation"][address]
                                         [-1]["after"], value)
                    for pin in ("P5.0", "P5.1"):
                        self.assertEqual(report["output_latches"][pin]
                                         ["median_low_width_ticks"], p5)

    def test_mode_one_and_two_select_flag_matrices_and_donors(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = (("0", False, 1000, 0x7CAE, 912, "9A", "A2", "A8", 1861),
                 ("1", False, 1000, 0x7D26, 494, "8E", "96", "DD", 5910),
                 ("1", True, 1000, 0x7D26, 494, "96", "9E", "FA", 5910),
                 ("2", False, 750, 0x7D9E, 912, "98", "A0", "7D", 6017),
                 ("2", True, 750, 0x7D9E, 912, "A0", "A5", "D9", 6094),
                 ("2", False, 1000, 0x7D9E, 494, "8E", "96", "DD", 5910),
                 ("2", True, 1000, 0x7D9E, 494, "96", "9E", "FA", 5910),
                 ("2", False, 1500, 0x7D9E, 480, "7D", "84", "65", 5260),
                 ("2", True, 1500, 0x7D9E, 480, "85", "8C", "78", 5234))
        with tempfile.TemporaryDirectory() as directory:
            for mode, use_donor, rpm, base, reads, a4, ram69, ram34, p5 in cases:
                with self.subTest(mode=mode, rpm=rpm, donor=use_donor):
                    output = Path(directory) / mode / str(rpm) / str(use_donor)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    environment.update({"MA17_ADC_CH0": "180",
                                        "MA17_ADC_CH2": "100",
                                        "MA17_ADC_CH3": "80",
                                        "MA17_ADC_CH6": "247",
                                        "MA17_ADC_CH7": "63",
                                        "MA17_OVERRIDE_RAM57": mode})
                    if use_donor:
                        environment.update({
                            "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(donor),
                            "MA17_OVERRIDE_MOVC_MATRIX_BASE": f"{base:04X}"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", str(rpm), "--stop-ticks", "2400000",
                         "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["ram57_override_hex"], mode)
                    self.assertEqual(report["movc_matrix_size"],
                                     120 if use_donor else None)
                    observed_reads = sum(row["count"] for row in
                                         report["movc_observation"]["reads"]
                                         if base <= int(row["address"], 16) < base + 120)
                    self.assertEqual(observed_reads, reads)
                    observed = report["engine_ram_observation"]
                    for address, value in (("A4", a4), ("69", ram69),
                                           ("34", ram34)):
                        self.assertEqual(observed[address][-1]["after"], value)
                    if mode != "0":
                        self.assertTrue(any(row["source_pc"] == "3B94"
                                            for row in observed["57"]))
                    for pin in ("P5.0", "P5.1"):
                        self.assertEqual(report["output_latches"][pin]
                                         ["median_low_width_ticks"], p5)

    def test_7cae_p5_width_is_mediated_by_ram69_at_tested_rpms(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        # Cross the native/donor RAM69 values before its Timer 1 calculation
        # reads; the active G ROM remains unchanged.
        cases = ((750, False, "A5", 1940, "17", "1E"),
                 (750, True, "A2", 1860, "B2", "1E"),
                 (1000, False, "A5", 1921, "34", "28"),
                 (1000, True, "A2", 1861, "A8", "28"),
                 (1500, False, "A4", 1766, "04", "3C"),
                 (1500, True, "9C", 1767, "F1", "3C"))
        with tempfile.TemporaryDirectory() as directory:
            for rpm, use_donor, ram69, expected_width, expected_reload, rpm_byte in cases:
                with self.subTest(rpm=rpm, donor=use_donor, ram69=ram69):
                    output = Path(directory) / str(rpm) / str(use_donor)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    environment.update({"MA17_ADC_CH0": "180",
                                        "MA17_ADC_CH2": "100",
                                        "MA17_ADC_CH3": "80",
                                        "MA17_ADC_CH6": "247",
                                        "MA17_ADC_CH7": "63",
                                        "MA17_OVERRIDE_RAM69": ram69})
                    if use_donor:
                        environment.update({
                            "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(donor),
                            "MA17_OVERRIDE_MOVC_MATRIX_BASE": "7CAE"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", str(rpm), "--stop-ticks", "2400000",
                         "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["ram69_override_hex"], ram69)
                    trace = (output / "emulator-trace.log").read_text()
                    self.assertIn(f"[RAM69-OVERRIDE] RAM47={rpm_byte} RAM69={ram69}",
                                  trace)
                    self.assertNotIn("[RAM69-OVERRIDE] RAM47=00", trace)
                    self.assertEqual(report["engine_ram_observation"]["34"][-1]
                                     ["after"], expected_reload)
                    for pin in ("P5.0", "P5.1"):
                        self.assertEqual(report["output_latches"][pin]
                                         ["median_low_width_ticks"], expected_width)

    def test_7cae_donor_changes_upper_a4_with_original_roms(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((REFERENCE, sun, 750, "9A", "A2", 1860, 1940, 79200,
                  "A2", "A5", "B2", "17"),
                 (REFERENCE, sun, 1000, "9A", "A2", 1861, 1921, 59400,
                  "A2", "A5", "A8", "34"),
                 (REFERENCE, sun, 1500, "95", "9D", 1767, 1766, 39600,
                  "9C", "A4", "F1", "04"),
                 (sun, REFERENCE, 1000, "A1", "99", 1921, 1921, 59400,
                  "A5", "A1", "34", "2F"))
        with tempfile.TemporaryDirectory() as directory:
            for (firmware, donor, rpm, native_a4, donor_a4, native_p5,
                 donor_p5, expected_period, native_69, donor_69,
                 native_34, donor_34) in cases:
                for use_donor, expected, expected_p5, ram69, ram34 in (
                        (False, native_a4, native_p5, native_69, native_34),
                        (True, donor_a4, donor_p5, donor_69, donor_34)):
                    with self.subTest(firmware=firmware.name, rpm=rpm,
                                      donor=use_donor):
                        output = Path(directory) / firmware.stem / str(rpm) / str(use_donor)
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_OVERRIDE_",
                                                              "MA17_TRACE_"))}
                        environment.update({"MA17_ADC_CH0": "180",
                                            "MA17_ADC_CH2": "100",
                                            "MA17_ADC_CH3": "80",
                                            "MA17_ADC_CH6": "247",
                                            "MA17_ADC_CH7": "63"})
                        if use_donor:
                            environment.update({
                                "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(donor),
                                "MA17_OVERRIDE_MOVC_MATRIX_BASE": "7CAE"})
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--trace-movc",
                             "--no-kline-inject", "--crank-immediate",
                             "--rpm", str(rpm), "--stop-ticks", "2400000",
                             "--seconds", "20", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertEqual(report["engine_ram_observation"]["A4"]
                                         [-1]["after"], expected)
                        for address, value, writer in (("69", ram69, "3B06"),
                                                       ("34", ram34, "051C")):
                            self.assertEqual(report["engine_ram_observation"]
                                             [address][-1]["after"], value)
                            self.assertEqual(report["engine_ram_observation"]
                                             [address][-1]["source_pc"], writer)
                        self.assertEqual(report["movc_matrix_donor_sha256"],
                                         hashlib.sha256(donor.read_bytes()).hexdigest()
                                         if use_donor else None)
                        self.assertTrue(any(
                            0x7CAE <= int(row["address"], 16) < 0x7D26
                            for row in report["movc_observation"]["reads"]))
                        for pin in ("P5.0", "P5.1"):
                            self.assertGreaterEqual(report["output_latches"]
                                                    [pin]["low_starts"], 20)
                            self.assertEqual(report["output_latches"][pin]
                                             ["median_low_width_ticks"], expected_p5)
                            self.assertEqual(report["output_latches"][pin]
                                             ["median_period_ticks"], expected_period)

    def test_7f15_donor_effect_persists_across_rpm_and_adc1(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        cases = ((750, 130, ("27", 6093), ("0C", 1940), 1422),
                 (2000, 130, ("52", 4759), ("1F", 1789), 1422),
                 (1000, 40, ("D0", 24136), ("7F", 14731), 1654))
        with tempfile.TemporaryDirectory() as directory:
            for rpm, adc1, control, supplied, cc3 in cases:
                for donor_enabled, expected in ((False, control), (True, supplied)):
                    with self.subTest(rpm=rpm, adc1=adc1, donor=donor_enabled):
                        output = Path(directory) / f"{rpm}_{adc1}_{donor_enabled}"
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({"MA17_OVERRIDE_RAM57": "1",
                                            "MA17_ADC_CH1": str(adc1),
                                            "MA17_ADC_CH7": "63"})
                        if donor_enabled:
                            environment.update({
                                "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(donor),
                                "MA17_OVERRIDE_MOVC_MATRIX_BASE": "7F15"})
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--trace-movc", "--trace-lookup",
                             "--no-kline-inject", "--crank-immediate",
                             "--rpm", str(rpm), "--stop-ticks", "2400000",
                             "--seconds", "30", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=40, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                        reads = [row for row in report["movc_observation"]["reads"]
                                 if 0x7F15 <= int(row["mapped"], 16) < 0x7F51]
                        self.assertTrue(reads)
                        self.assertEqual(report["engine_ram_observation"]["31"][-1]
                                         ["after"], expected[0])
                        self.assertEqual(report["output_latches"]["P5.0"]
                                         ["median_low_width_ticks"], expected[1])
                        self.assertEqual(report["cc3_observation"]
                                         ["iram14_15_median"], cc3)

    def test_7f15_7f51_donor_cells_change_p5_in_fixed_selector_modes(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        alcohol = VARIANTS / "tipo 1.6 alcool27c256.bin"
        s37 = VARIANTS / "tipo 1.6 alcool27c256 SUN 37a5.bin"
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        observed = {}
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                for selector, base, addresses, donors in (
                        (1, "7F15", {0x7F29, 0x7F2A, 0x7F33, 0x7F34,
                                      0x7F47, 0x7F48, 0x7F4A, 0x7F4B},
                         (None, alcohol, s37)),
                        (2, "7F51", {0x7F65, 0x7F66, 0x7F6F, 0x7F70,
                                      0x7F83, 0x7F84, 0x7F86, 0x7F87},
                         (None, alcohol))):
                    for donor in donors:
                        name = donor.stem if donor else "control"
                        with self.subTest(firmware=firmware.name,
                                          selector=selector, donor=name):
                            output = Path(directory) / firmware.stem / base / name
                            environment = {
                                key: value for key, value in os.environ.items()
                                if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                       "MA17_OVERRIDE_"))}
                            environment.update({"MA17_OVERRIDE_RAM57": str(selector),
                                                "MA17_ADC_CH7": "63"})
                            if donor:
                                environment.update({
                                    "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(donor),
                                    "MA17_OVERRIDE_MOVC_MATRIX_BASE": base})
                            result = subprocess.run(
                                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                                 "--firmware", str(firmware), "--trace-movc",
                                 "--trace-lookup", "--no-kline-inject",
                                 "--crank-immediate", "--rpm", "1000",
                                 "--stop-ticks", "2400000", "--seconds", "30",
                                 "--output-dir", str(output)],
                                capture_output=True, text=True, env=environment,
                                timeout=40, check=False)
                            self.assertEqual(result.returncode, 0,
                                             result.stderr[-1500:])
                            report = json.loads((output / "execution.json").read_text())
                            active_bytes = firmware.read_bytes()
                            self.assertEqual(report["firmware_sha256"],
                                             hashlib.sha256(active_bytes).hexdigest())
                            self.assertEqual(report["movc_matrix_donor_sha256"],
                                             hashlib.sha256(donor.read_bytes()).hexdigest()
                                             if donor else None)
                            reads = [row for row in report["movc_observation"]["reads"]
                                     if int(base, 16) <= int(row["mapped"], 16)
                                     < int(base, 16) + 60]
                            self.assertEqual(sum(row["count"] for row in reads), 462)
                            self.assertEqual({int(row["mapped"], 16) for row in reads},
                                             addresses)
                            self.assertTrue(all(int(row["value"], 16) ==
                                                active_bytes[int(row["mapped"], 16)]
                                                for row in reads))
                            self.assertEqual(report["cc3_observation"]
                                             ["iram14_15_median"], 1422)
                            observed[(firmware == sun, selector, name)] = (
                                report["engine_ram_observation"]["31"][-1]["after"],
                                report["output_latches"]["P5.0"]
                                      ["median_low_width_ticks"])
        for is_sun, own_p5, donor1_p5, donor2_p5 in (
                (False, 5908, 1861, 10334),
                (True, 5970, 1921, 10394)):
            self.assertEqual(observed[(is_sun, 1, "control")], ("33", own_p5))
            self.assertEqual(observed[(is_sun, 2, "control")], ("33", own_p5))
            self.assertEqual(observed[(is_sun, 1, alcohol.stem)],
                             ("10", donor1_p5))
            self.assertEqual(observed[(is_sun, 1, s37.stem)],
                             ("10", donor1_p5))
            self.assertEqual(observed[(is_sun, 2, alcohol.stem)],
                             ("59", donor2_p5))

    def test_7ed9_p5_effect_is_mediated_by_ram31_at_timer1_read(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        alcohol = VARIANTS / "tipo 1.6 alcool27c256.bin"
        cases = ((False, None, "10", 1861),
                 (False, "32", "10", 5792),
                 (True, None, "32", 5792),
                 (True, "10", "32", 1861))
        with tempfile.TemporaryDirectory() as directory:
            for donor, forced31, natural31, expected_p5 in cases:
                with self.subTest(donor=donor, forced31=forced31):
                    output = Path(directory) / f"{donor}_{forced31}"
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_OVERRIDE_RAM57": "0",
                                        "MA17_ADC_CH7": "63",
                                        "MA17_TRACE_RAM31_GATE": "1"})
                    if donor:
                        environment.update({
                            "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(alcohol),
                            "MA17_OVERRIDE_MOVC_MATRIX_BASE": "7ED9"})
                    if forced31 is not None:
                        environment["MA17_OVERRIDE_RAM31"] = forced31
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes())
                                     .hexdigest())
                    self.assertEqual(report["ram31_override_hex"], forced31)
                    self.assertTrue(report["ram31_gate_trace_enabled"])
                    self.assertEqual(report["engine_ram_observation"]["31"]
                                     [-1]["after"], natural31)
                    effective31 = forced31 or natural31
                    late = [line for line in
                            (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[RAM31-GATE]") and
                            "PC=049B " in line and
                            int(line.split("tick=")[1].split()[0]) > 1000000]
                    self.assertGreater(len(late), 30)
                    self.assertEqual({(line.split("RAM69=")[1][:2],
                                       line.split("A=")[1][:2],
                                       line.split("B=")[1][:2],
                                       int(line.split("PSW=")[1][:2], 16) & 0x80)
                                      for line in late},
                                     {("9A", f"{0x4D - int(effective31, 16):02X}",
                                       effective31, 0x80)})
                    for pin in ("P5.0", "P5.1"):
                        self.assertEqual(report["output_latches"][pin]
                                         ["median_low_width_ticks"], expected_p5)

    def test_ram31_p5_scaling_has_low_value_floor(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for value, expected_width in (("00", 989), ("20", 3725),
                                          ("80", 14849)):
                with self.subTest(ram31=value):
                    output = Path(directory) / value
                    environment = {key: setting for key, setting in
                                   os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_OVERRIDE_RAM57": "0",
                                        "MA17_OVERRIDE_RAM31": value,
                                        "MA17_ADC_CH7": "63"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate",
                         "--rpm", "1000", "--stop-ticks", "2400000",
                         "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes())
                                     .hexdigest())
                    self.assertEqual(report["engine_ram_observation"]["31"]
                                     [-1]["after"], "10")
                    pin = report["output_latches"]["P5.0"]
                    self.assertEqual(pin["median_period_ticks"], 59400)
                    self.assertEqual(pin["median_low_width_ticks"],
                                     expected_width)
                    if value != "00":
                        self.assertLessEqual(abs(expected_width -
                                                 59400 * int(value, 16) / 512),
                                             15)

    def test_rpm47_matches_crank_rate_in_g_and_s88_profiles(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((REFERENCE, ((750, 0x1E), (1000, 0x28),
                              (775, 0x1F), (825, 0x21),
                              (1175, 0x2F), (1225, 0x31),
                              (1500, 0x3C), (1713, 0x44),
                              (1724, 0x45), (1725, 0x45),
                              (1738, 0x45), (1749, 0x46),
                              (1975, 0x4F), (2000, 0x50), (2025, 0x51),
                              (2725, 0x6D), (2775, 0x6F),
                              (3000, 0x78), (3575, 0x8F),
                              (3625, 0x91), (4000, 0xA0))),
                 (VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin",
                  ((750, 0x1E), (3000, 0x78))))
        with tempfile.TemporaryDirectory() as directory:
            for firmware, speeds in cases:
                for rpm, expected_raw in speeds:
                    with self.subTest(firmware=firmware.name, rpm=rpm):
                        output = Path(directory) / f"{firmware.stem}_{rpm}"
                        environment = {key: value for key, value in
                                       os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_",
                                                              "MA17_OVERRIDE_"))}
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" /
                                                 "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", str(rpm),
                             "--stop-ticks", "1200000", "--seconds", "20",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0,
                                         result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes())
                                         .hexdigest())
                        changes = report["rpm_observation"]["ram47_changes"]
                        self.assertTrue(changes)
                        self.assertEqual(changes[-1]["after"],
                                         f"{expected_raw:02X}")
                        self.assertEqual(changes[-1]["next_pc"], "0EA7")

    def test_7ed9_ram31_mediation_at_750_and_2000_rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        alcohol = VARIANTS / "tipo 1.6 alcool27c256.bin"
        cases = ((750, "1E", "0C", "2E", 1940, 7181),
                 (2000, "50", "1F", "41", 1789, 3769))
        with tempfile.TemporaryDirectory() as directory:
            for rpm, rpm_byte, g31, a31, g_p5, a_p5 in cases:
                for donor, forced31, expected_p5 in (
                        (False, None, g_p5), (False, a31, a_p5),
                        (True, None, a_p5), (True, g31, g_p5)):
                    with self.subTest(rpm=rpm, donor=donor, forced31=forced31):
                        output = Path(directory) / f"{rpm}_{donor}_{forced31}"
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({"MA17_OVERRIDE_RAM57": "0",
                                            "MA17_ADC_CH7": "63"})
                        if donor:
                            environment.update({
                                "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(alcohol),
                                "MA17_OVERRIDE_MOVC_MATRIX_BASE": "7ED9"})
                        if forced31 is not None:
                            environment["MA17_OVERRIDE_RAM31"] = forced31
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--trace-movc", "--no-kline-inject",
                             "--crank-immediate", "--rpm", str(rpm),
                             "--stop-ticks", "2400000", "--seconds", "30",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=40, check=False)
                        self.assertEqual(result.returncode, 0,
                                         result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["stop_ticks_observed"], 2400000)
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(REFERENCE.read_bytes())
                                         .hexdigest())
                        self.assertEqual(report["engine_ram_observation"]["31"]
                                         [-1]["after"], a31 if donor else g31)
                        for pin in ("P5.0", "P5.1"):
                            self.assertEqual(report["output_latches"][pin]
                                             ["median_low_width_ticks"],
                                             expected_p5)
                        lines = (output / "emulator-trace.log").read_text().splitlines()
                        messages = [line for line in lines if line.startswith(
                                    "[RAM31-OVERRIDE]")]
                        self.assertEqual(messages,
                                         [f"[RAM31-OVERRIDE] RAM47={rpm_byte} "
                                          f"RAM31={forced31}"] if forced31 else [])

    def test_7ed9_alcohol_cells_change_ram31_and_p5_in_fiat_code(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        alcohol = VARIANTS / "tipo 1.6 alcool27c256.bin"
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        with tempfile.TemporaryDirectory() as directory:
            for firmware, p5_control in ((REFERENCE, 1861), (sun, 1921)):
                for donor_enabled in (False, True):
                    with self.subTest(firmware=firmware.name, donor=donor_enabled):
                        output = Path(directory) / firmware.stem / str(donor_enabled)
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({"MA17_OVERRIDE_RAM57": "0",
                                            "MA17_ADC_CH7": "63"})
                        if donor_enabled:
                            environment.update({
                                "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(alcohol),
                                "MA17_OVERRIDE_MOVC_MATRIX_BASE": "7ED9"})
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--trace-movc",
                             "--trace-lookup", "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "30",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=40, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        original = firmware.read_bytes()
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(original).hexdigest())
                        self.assertEqual(report["movc_matrix_donor_sha256"],
                                         hashlib.sha256(alcohol.read_bytes()).hexdigest()
                                         if donor_enabled else None)
                        if donor_enabled:
                            self.assertEqual(report["movc_matrix_pointer_slot_hex"],
                                             "70A2")
                            self.assertEqual(report["movc_matrix_size"], 60)
                        reads = [row for row in report["movc_observation"]["reads"]
                                 if 0x7ED9 <= int(row["mapped"], 16) < 0x7F15]
                        self.assertTrue(reads)
                        self.assertTrue(all(int(row["value"], 16) ==
                                            original[int(row["mapped"], 16)]
                                            for row in reads))
                        self.assertEqual(report["engine_ram_observation"]["31"][-1]
                                         ["after"], "32" if donor_enabled else "10")
                        self.assertEqual(report["output_latches"]["P5.0"]
                                         ["median_low_width_ticks"],
                                         p5_control + (3931 if donor_enabled else 0))
                        self.assertEqual(report["cc3_observation"]
                                         ["iram14_15_median"], 1422)

    def test_matrix_donor_rejects_different_code_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            incompatible = bytearray(REFERENCE.read_bytes())
            incompatible[0x100] ^= 1
            donor = Path(directory) / "different-code.bin"
            donor.write_bytes(incompatible)
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith("MA17_OVERRIDE_")}
            environment.update({"MA17_OVERRIDE_MOVC_MATRIX_ROM": str(donor),
                                "MA17_OVERRIDE_MOVC_MATRIX_BASE": "7662"})
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--trace-movc", "--output-dir", directory],
                capture_output=True, text=True, env=environment, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("matrix donor must match an inventoried original ROM",
                          result.stderr)

    def test_alternative_matrix_donor_bytes_causally_change_cc3(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((REFERENCE, sun, 1, "7662", "8820", "31", 1121),
                 (REFERENCE, sun, 2, "7743", "7620", "2B", 982),
                 (sun, REFERENCE, 1, "7662", "4690", "19", 613),
                 (sun, REFERENCE, 2, "7743", "4690", "19", 613))
        with tempfile.TemporaryDirectory() as directory:
            for firmware, donor, selector, base, lookup, ram48, cc3 in cases:
                with self.subTest(firmware=firmware.name, base=base):
                    output = Path(directory) / firmware.stem / base
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_OVERRIDE_RAM57": str(selector),
                                        "MA17_OVERRIDE_MOVC_MATRIX_BASE": base,
                                        "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(donor),
                                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                                        "MA17_ADC_CH7": "63"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--trace-movc",
                         "--trace-lookup", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    active_bytes, donor_bytes = firmware.read_bytes(), donor.read_bytes()
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(active_bytes).hexdigest())
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(donor_bytes).hexdigest())
                    self.assertEqual(report["movc_matrix_base_hex"], base)
                    reads = [row for row in report["movc_observation"]["reads"]
                             if int(base, 16) <= int(row["mapped"], 16)
                             < int(base, 16) + 225]
                    self.assertTrue(reads)
                    self.assertTrue(all(int(row["value"], 16) ==
                                        active_bytes[int(row["mapped"], 16)]
                                        for row in reads))
                    dominant = max(report["lookup_observation"]["states"],
                                   key=lambda row: row["count"])
                    self.assertEqual(dominant["result_a"] + dominant["result_b"],
                                     lookup)
                    self.assertEqual(report["engine_ram_observation"]["48"][-1]
                                     ["after"], ram48)
                    self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                     cc3)
                    self.assertIn("[MOVC-OVERRIDE] matrix=", (output /
                                  "emulator-trace.log").read_text())

    def test_ram57_counterfactual_selects_three_matrices_and_changes_cc3(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        expected = ((REFERENCE, ("763", "920", "920"),
                     ("59F0", "6E20", "6E20")),
                    (sun, ("727", "815", "675"),
                     ("5530", "6090", "4E90")))
        with tempfile.TemporaryDirectory() as directory:
            for firmware, cc3_values, lookup_values in expected:
                for selector in range(3):
                    with self.subTest(firmware=firmware.name, selector=selector):
                        output = Path(directory) / firmware.stem / str(selector)
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({"MA17_OVERRIDE_RAM57": str(selector),
                                            "MA17_ADC_CH0": "40",
                                            "MA17_ADC_CH6": "95",
                                            "MA17_ADC_CH7": "63"})
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--trace-movc",
                             "--trace-lookup", "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "30",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=40, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertEqual(report["ram57_override_hex"], str(selector))
                        dominant = max(report["lookup_observation"]["states"],
                                       key=lambda row: row["count"])
                        self.assertEqual(dominant["selector"], f"{selector:02X}")
                        self.assertEqual(dominant["result_a"] + dominant["result_b"],
                                         lookup_values[selector])
                        self.assertEqual(str(report["cc3_observation"]
                                             ["iram14_15_median"]), cc3_values[selector])
                        reads = report["movc_observation"]["reads"]
                        start = (0x7581, 0x7662, 0x7743)[selector]
                        self.assertGreater(sum(row["count"] for row in reads
                                               if start <= int(row["mapped"], 16)
                                               < start + 225), 0)

    def test_coolant_adc_fallback_boundaries_match_s88(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        firmware = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        with tempfile.TemporaryDirectory() as directory:
            for adc3, expected, fallback in ((3, "11", True),
                                             (4, "04", False),
                                             (231, "E7", False),
                                             (232, "11", True)):
                with self.subTest(adc3=adc3):
                    output = Path(directory) / str(adc3)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC10_CH3": str(adc3 * 4),
                                        "MA17_ADC_CH7": "63"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "200000", "--seconds", "5",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=15, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    observed = report["sensor_ram_observation"]
                    self.assertEqual(observed["A8"][-1]["after"], f"{adc3:02X}")
                    self.assertEqual(observed["63"][-1]["after"], expected)
                    hits = (output / "pc-hits.txt").read_text().splitlines()
                    self.assertEqual("474E" in hits, fallback)

    def test_coolant_adc_raw_range_and_firmware_fallback_boundaries(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((3, "11", True), (4, "04", False),
                 (231, "E7", False), (232, "11", True))
        with tempfile.TemporaryDirectory() as directory:
            for adc3, processed, fallback in cases:
                with self.subTest(adc3=adc3):
                    output = Path(directory) / str(adc3)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC10_CH3": str(adc3 * 4),
                                        "MA17_ADC_CH7": "63"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "200000", "--seconds", "5",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=15, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    observed = report["sensor_ram_observation"]
                    self.assertEqual(observed["A8"][-1]["after"], f"{adc3:02X}")
                    self.assertEqual(observed["63"][-1]["after"], processed)
                    hits = (output / "pc-hits.txt").read_text().splitlines()
                    self.assertIn("4756", hits)
                    if adc3 != 231:  # E7h equals the initialized RAM value.
                        self.assertEqual(observed["63"][-1]["source_pc"], "4756")
                    self.assertEqual("474E" in hits, fallback)

    def test_air_lookup_716c_is_gated_before_upper_iram_cc_consumer(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for adc3 in (80, 4):
                with self.subTest(adc3=adc3):
                    output = Path(directory) / str(adc3)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                          "MA17_OVERRIDE_", "MA17_TRACE_"))}
                    environment.update({"MA17_ADC_CH3": str(adc3),
                                        "MA17_ADC_CH7": "63",
                                        "MA17_TRACE_AIR_716C_GATE": "1"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    lines = [line for line in (output / "emulator-trace.log")
                             .read_text().splitlines()
                             if line.startswith("[AIR-716C-GATE]")]
                    self.assertTrue(any("PC=3C73" in line for line in lines))
                    self.assertTrue(any("PC=3CB7" in line and "R2=FF" in line
                                        and "F2E=84" in line for line in lines))
                    self.assertTrue(any("PC=397D" in line and "UCC=05" in line
                                        for line in lines))
                    self.assertTrue(any("PC=3CDA" in line and "PSW=02" in line
                                        for line in lines))
                    self.assertTrue(any("PC=3D0B" in line for line in lines))
                    self.assertFalse(any("PC=398D" in line for line in lines))

    def test_post_coolant_curve_744e_is_naturally_read_with_t2i1_clear(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        images = ((REFERENCE, hashlib.sha256(REFERENCE.read_bytes()).hexdigest()),
                  (VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin",
                   "bfa59928ca41695458063835dc1a05a489b9deb5755bb1d7740c22874fdcbe28"))
        with tempfile.TemporaryDirectory() as directory:
            for index, (firmware, digest) in enumerate(images):
                with self.subTest(firmware=firmware.name):
                    output = Path(directory) / str(index)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH7": "63", "MA17_TRACE_LAMBDA": "1"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "1000", "--stop-ticks", "5000000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"], digest)
                    self.assertEqual(report["stop_ticks_observed"], 5000000)
                    reads = report["movc_observation"]["reads"]
                    self.assertGreater(sum(row["count"] for row in reads if
                                           row["pc"] == "532F" and
                                           row["address"] == "744E" and
                                           row["value"] == "15"), 1000)
                    self.assertFalse(any(0x7430 <= int(row["address"], 16)
                                         < 0x743A or
                                         0x7458 <= int(row["address"], 16)
                                         < 0x7462 for row in reads))
                    gates = [line for line in (output / "emulator-trace.log")
                             .read_text().splitlines()
                             if line.startswith("[LAMBDA-GATE]")]
                    self.assertGreater(len(gates), 1000)
                    self.assertTrue(all("T2I1=0" in line for line in gates))

    def test_post_coolant_curve_744e_axis_comes_from_iram63_segment(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for adc2, adc3, ram63, index, fraction, address, value in (
                    (100, 20, "14", "00", "00", "744E", "15"),
                    (100, 80, "50", "03", "20", "7451", "33"),
                    (220, 20, "14", "00", "00", "744E", "15")):
                with self.subTest(adc2=adc2, adc3=adc3):
                    output = Path(directory) / f"{adc2}_{adc3}"
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH2": str(adc2),
                        "MA17_ADC_CH3": str(adc3), "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH7": "63",
                        "MA17_TRACE_POST_COOLANT_AXIS": "1"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["stop_ticks_observed"], 2400000)
                    self.assertTrue(report["post_coolant_axis_trace_enabled"])
                    reads = report["movc_observation"]["reads"]
                    self.assertTrue(any(row["pc"] == "532F" and
                                        row["address"] == address and
                                        row["value"] == value for row in reads))
                    hits = (output / "pc-hits.txt").read_text().splitlines()
                    self.assertNotIn("47A2", hits)
                    self.assertNotIn("47A3", hits)
                    if adc2 == 220:
                        self.assertIn("4793", hits)
                    else:
                        self.assertNotIn("4793", hits)
                    rows = [dict(re.findall(r"(\w+)=(\w+)", line)) for line in
                            (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[POST-COOLANT-AXIS]")]
                    for pc, dptr in (("477F", "73D5"), ("47AC", "7200"),
                                     ("491F", "7018"), ("532F", "744E")):
                        first = next(row for row in rows if row["PC"] == pc)
                        self.assertEqual(first["DPTR"], dptr)
                        self.assertEqual((first["RAM63"], first["R5"],
                                          first["R6"]), (ram63, index, fraction))
                        self.assertEqual(int(first["T2CON"], 16) & 2, 0)
                    segment = next(row for row in rows if row["PC"] == "477F")
                    if adc2 == 220:
                        self.assertGreater(int(segment["RAM62"], 16),
                                           REFERENCE.read_bytes()[0x7264])
                        self.assertEqual(int(segment["F28"], 16) & 0x38, 0)
                        self.assertEqual(int(segment["F29"], 16) & 0x08, 0)
                    else:
                        self.assertLessEqual(int(segment["RAM62"], 16),
                                             REFERENCE.read_bytes()[0x7264])

    def test_coolant_bound_flags_reach_xram91_but_bypass_744e(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for raw_adc3, flag in ((3, 0x10), (232, 0x08)):
                with self.subTest(raw_adc3=raw_adc3):
                    output = Path(directory) / str(raw_adc3)
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH2": "220",
                        "MA17_ADC10_CH3": str(raw_adc3 * 4),
                        "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_POST_COOLANT_AXIS": "1"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["stop_ticks_observed"], 2400000)
                    hits = set((output / "pc-hits.txt").read_text().splitlines())
                    self.assertTrue({"4793", "47A2", "47A3", "490B"} <= hits)
                    self.assertNotIn("491F", hits)
                    self.assertFalse(any(0x7430 <= int(row["address"], 16)
                                         < 0x7462 for row in
                                         report["movc_observation"]["reads"]))
                    fallback = [row for row in
                                report["movc_observation"]["reads"]
                                if row["pc"] == "4912" and
                                row["address"] == "727F" and
                                row["value"] == "2E"]
                    self.assertEqual(len(fallback), 1)
                    self.assertGreater(fallback[0]["count"], 500)
                    rows = [dict(re.findall(r"(\w+)=(\w+)", line)) for line
                            in (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[POST-COOLANT-AXIS]")]
                    before = next(row for row in rows if row["PC"] == "477F")
                    after = next(row for row in rows if row["PC"] == "47AC")
                    self.assertEqual(before["RAM62"], "DC")
                    self.assertEqual(before["RAM63"], "11")
                    self.assertEqual(int(before["F28"], 16) & flag, flag)
                    self.assertEqual((before["X91"], before["X9E"]),
                                     ("34", "78"))
                    self.assertEqual((after["R5"], after["R6"]),
                                     ("08", "30"))

    def test_air_segment_73c0_writes_xram91_before_fault_lookup(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for adc2, packed, index, fraction in (
                    (120, "B0", "04", "B0"),
                    (160, "F1", "05", "F0"),
                    (220, "34", "08", "30")):
                with self.subTest(adc2=adc2):
                    output = Path(directory) / str(adc2)
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH2": str(adc2), "MA17_ADC_CH3": "232",
                        "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_XRAM_F891": "1",
                        "MA17_TRACE_POST_COOLANT_AXIS": "1"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertTrue(report["xram_f891_trace_enabled"])
                    self.assertEqual(report["stop_ticks_observed"], 2400000)
                    self.assertGreater(sum(row["count"] for row in
                                           report["movc_observation"]["reads"]
                                           if row["address"] == "73C0" and
                                           row["value"] == "62"), 500)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    writes = [dict(re.findall(r"(\w+)=(\w+)", line))
                              for line in lines if line.startswith("[F891-WRITE]")
                              and "PC=4608" in line]
                    self.assertEqual(len(writes), 1)
                    self.assertTrue(any(f"value=00->{packed}" in line for line
                                        in lines if line.startswith("[F891-WRITE]")
                                        and "PC=4608" in line))
                    rows = [dict(re.findall(r"(\w+)=(\w+)", line)) for line
                            in lines if line.startswith("[POST-COOLANT-AXIS]")]
                    before = next(row for row in rows if row["PC"] == "477F")
                    after = next(row for row in rows if row["PC"] == "47AC")
                    self.assertLess(int(writes[0]["tick"]), int(before["tick"]))
                    self.assertEqual((before["RAM62"], before["X91"]),
                                     (f"{adc2:02X}", packed))
                    self.assertEqual((after["R5"], after["R6"]),
                                     (index, fraction))

    def test_73c6_width_and_f891_read_have_separate_cc3_effects(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        self.assertEqual(REFERENCE.read_bytes()[0x73C6], 0x0F)
        with tempfile.TemporaryDirectory() as directory:
            for width, read, expected_stored, expected_pair, expected_cc3 in (
                    (None, None, "34", ("08", "30"), 1505),
                    (None, "14", "34", ("08", "10"), 1505),
                    ("1F", None, "14", ("08", "10"), 1491),
                    ("1F", "34", "14", ("08", "30"), 1491)):
                with self.subTest(width=width, read=read):
                    output = Path(directory) / f"{width or 'base'}-{read or 'base'}"
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH2": "220", "MA17_ADC_CH3": "232",
                        "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_XRAM_F891": "1",
                        "MA17_TRACE_POST_COOLANT_AXIS": "1"})
                    if width:
                        environment["MA17_OVERRIDE_MOVC_AT"] = f"52A2:73C6:{width}"
                    if read:
                        environment["MA17_OVERRIDE_XRAM_F891_47A2"] = read
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["xram_f891_47a2_override_hex"], read)
                    self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                     expected_cc3)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    self.assertTrue(any(f"PC=4608 value=00->{expected_stored}" in line
                                        for line in lines if line.startswith("[F891-WRITE]")))
                    rows = [dict(re.findall(r"(\w+)=(\w+)", line)) for line
                            in lines if line.startswith("[POST-COOLANT-AXIS]")
                            and "PC=47AC" in line]
                    self.assertTrue(rows)
                    self.assertEqual((rows[0]["R5"], rows[0]["R6"]),
                                     expected_pair)
                    if read:
                        self.assertTrue(any(f"stored={expected_stored} supplied={read}"
                                            in line for line in lines if line.startswith(
                                                "[F891-READ-OVERRIDE]")))

    def test_73c6_cc3_effect_is_mediated_by_f891_read_at_564a(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for width, read, stored, median in (
                    (None, None, "34", 1505),
                    (None, "14", "34", 1491),
                    ("1F", None, "14", 1491),
                    ("1F", "34", "14", 1505)):
                with self.subTest(width=width, read=read):
                    output = Path(directory) / f"{width or 'base'}-{read or 'base'}"
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH2": "220", "MA17_ADC_CH3": "232",
                        "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_XRAM_F891": "1"})
                    if width:
                        environment["MA17_OVERRIDE_MOVC_AT"] = f"52A2:73C6:{width}"
                    if read:
                        environment["MA17_OVERRIDE_XRAM_F891_564A"] = read
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["xram_f891_564a_override_hex"], read)
                    self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                     median)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    self.assertTrue(any(f"PC=4608 value=00->{stored}" in line
                                        for line in lines if line.startswith("[F891-WRITE]")))
                    self.assertTrue(any(f"PC=564A value={stored}" in line
                                        for line in lines if line.startswith("[F891-READ]")))
                    if read:
                        self.assertTrue(any(f"stored={stored} supplied={read}"
                                            in line for line in lines if line.startswith(
                                                "[F891-READ-OVERRIDE] PC=564A")))

    def test_f891_cc3_effect_uses_129d_caller_of_564a(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for caller, width, supplied, expected, upper87, ram4ab in (
                    ("12A0", None, "14", 1491, "5A", "8A"),
                    ("1552", None, "14", 1505, "5B", "91"),
                    ("15D5", None, "14", 1505, "5B", "91"),
                    ("12A0", "1F", "34", 1505, "5B", "91")):
                with self.subTest(caller=caller, width=width):
                    output = Path(directory) / f"{caller}-{width or 'base'}"
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH2": "220", "MA17_ADC_CH3": "232",
                        "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_XRAM_F891": "1",
                        "MA17_TRACE_129D_PATH": "1",
                        "MA17_OVERRIDE_XRAM_F891_564A": supplied,
                        "MA17_OVERRIDE_XRAM_F891_564A_RETURN": caller})
                    if width:
                        environment["MA17_OVERRIDE_MOVC_AT"] = f"52A2:73C6:{width}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["xram_f891_564a_return_filter_hex"],
                                     caller)
                    self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                     expected)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    self.assertTrue(any(f"return={caller} " in line for line
                                        in lines if line.startswith(
                                            "[F891-READ-OVERRIDE] PC=564A")))
                    self.assertEqual({"12A0", "1552", "15D5"}, {
                        re.search(r"return=([0-9A-F]{4})", line).group(1)
                        for line in lines if line.startswith("[F891-564A-CALLER]")})
                    path = [dict(re.findall(r"(\w+)=(\w+)", line)) for line
                            in lines if line.startswith("[129D-PATH]")
                            and "PC=12D9" in line]
                    self.assertTrue(path)
                    self.assertEqual((path[-1]["UIRAM87"], path[-1]["RAM4A"],
                                      path[-1]["RAM4B"]),
                                     (upper87, ram4ab, ram4ab))
                    downstream = "8F" if upper87 == "5A" else "9D"
                    scheduled = "D3" if upper87 == "5A" else "E1"
                    inputs = [dict(re.findall(r"(\w+)=(\w+)", line))["RAM5A"]
                              for line in lines if line.startswith("[INJECTION-INPUT]")]
                    self.assertGreater(len(inputs), 200)
                    self.assertEqual(Counter(inputs).most_common(1)[0][0],
                                     downstream)
                    for pc, expected_r2 in (("1DD8", downstream),
                                             ("1ED3", scheduled)):
                        samples = [dict(re.findall(r"(\w+)=(\w+)", line))["R2"]
                                   for line in lines if line.startswith(
                                       "[INJECTION-FLOW]") and f"PC={pc} " in line]
                        self.assertGreater(len(samples), 200)
                        self.assertEqual(Counter(samples).most_common(1)[0][0],
                                         expected_r2)

    def test_7426_output_mediates_f891_cc3_effect_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        rom = REFERENCE.read_bytes()
        self.assertEqual(rom[0x7004:0x7006], bytes.fromhex("74 12"))
        self.assertEqual(rom[0x7008:0x700A], bytes.fromhex("74 26"))
        self.assertEqual(rom[0x741B], 0xBE)
        self.assertEqual(rom[0x742F], 0x60)
        with tempfile.TemporaryDirectory() as directory:
            for name, movc, f891, upper87, ram4ab, cc3 in (
                    ("base", None, None, "5B", "91", 1505),
                    ("7426_only", "5333:742F:5A", None, "5A", "91", 1491),
                    ("7412_only", "5333:741B:98", None, "5B", "8A", 1505),
                    ("7426_rescue", "5333:742F:6A", "14", "5B", "8A", 1505)):
                with self.subTest(name=name):
                    output = Path(directory) / name
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH2": "220", "MA17_ADC_CH3": "232",
                        "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_129D_PATH": "1"})
                    if movc:
                        environment["MA17_OVERRIDE_MOVC_AT"] = movc
                    if f891:
                        environment["MA17_OVERRIDE_XRAM_F891_564A"] = f891
                        environment["MA17_OVERRIDE_XRAM_F891_564A_RETURN"] = "12A0"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(rom).hexdigest())
                    self.assertTrue(report["path_129d_trace_enabled"])
                    self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                     cc3)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    path = [dict(re.findall(r"(\w+)=(\w+)", line)) for line
                            in lines if line.startswith("[129D-PATH]")
                            and "PC=12D9" in line]
                    self.assertTrue(path)
                    self.assertEqual((path[-1]["UIRAM87"], path[-1]["RAM4A"],
                                      path[-1]["RAM4B"]),
                                     (upper87, ram4ab, ram4ab))
                    downstream = "8F" if upper87 == "5A" else "9D"
                    scheduled = "D3" if upper87 == "5A" else "E1"
                    inputs = [dict(re.findall(r"(\w+)=(\w+)", line))["RAM5A"]
                              for line in lines if line.startswith("[INJECTION-INPUT]")]
                    self.assertGreater(len(inputs), 200)
                    self.assertEqual(Counter(inputs).most_common(1)[0][0],
                                     downstream)
                    for pc, expected_r2 in (("1DD8", downstream),
                                             ("1ED3", scheduled)):
                        samples = [dict(re.findall(r"(\w+)=(\w+)", line))["R2"]
                                   for line in lines if line.startswith(
                                       "[INJECTION-FLOW]") and f"PC={pc} " in line]
                        self.assertGreater(len(samples), 200)
                        self.assertEqual(Counter(samples).most_common(1)[0][0],
                                         expected_r2)

    def test_7426_cc3_mediation_repeats_in_s88(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        firmware = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        rom = firmware.read_bytes()
        self.assertEqual(rom[0x7008:0x700A], bytes.fromhex("74 26"))
        self.assertEqual(rom[0x742F], 0x60)
        with tempfile.TemporaryDirectory() as directory:
            for name, movc, f891, upper87, ram4ab, cc3, low, r2 in (
                    ("base", None, None, "5B", "91", 1429, 5705, "51"),
                    ("cell", "5333:742F:5A", None, "5A", "91", 1416, 5653, "44"),
                    ("read14", None, "14", "5A", "8A", 1416, 5653, "44"),
                    ("rescue", "5333:742F:6A", "14", "5B", "8A", 1429, 5705, "51")):
                with self.subTest(name=name):
                    output = Path(directory) / name
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH2": "220", "MA17_ADC_CH3": "232",
                        "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_129D_PATH": "1"})
                    if movc:
                        environment["MA17_OVERRIDE_MOVC_AT"] = movc
                    if f891:
                        environment["MA17_OVERRIDE_XRAM_F891_564A"] = f891
                        environment["MA17_OVERRIDE_XRAM_F891_564A_RETURN"] = "12A0"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(rom).hexdigest())
                    self.assertEqual((report["cc3_observation"]["iram14_15_median"],
                                      report["cc3_observation"][
                                          "cc3_pin_model_median_low_width_ticks"]),
                                     (cc3, low))
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    path = [dict(re.findall(r"(\w+)=(\w+)", line)) for line
                            in lines if line.startswith("[129D-PATH]")
                            and "PC=12D9" in line]
                    self.assertTrue(path)
                    self.assertEqual((path[-1]["UIRAM87"], path[-1]["RAM4A"],
                                      path[-1]["RAM4B"]),
                                     (upper87, ram4ab, ram4ab))
                    samples = [dict(re.findall(r"(\w+)=(\w+)", line))["R2"]
                               for line in lines if line.startswith(
                                   "[INJECTION-FLOW]") and "PC=1DD8 " in line]
                    self.assertGreater(len(samples), 200)
                    self.assertEqual(Counter(samples).most_common(1)[0][0], r2)

    def test_post_coolant_727f_fallback_reaches_4d_and_fixed_point(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        self.assertEqual(REFERENCE.read_bytes()[0x7279], 0x19)
        with tempfile.TemporaryDirectory() as directory:
            for supplied, expected_4d, expected_r2 in (
                    (None, "2E", "45"), ("2E", "2E", "45"),
                    ("00", "19", "25"), ("80", "80", "BA")):
                with self.subTest(supplied=supplied):
                    output = Path(directory) / (supplied or "baseline")
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH2": "220", "MA17_ADC_CH3": "232",
                        "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_RAM4D_PATH": "1"})
                    if supplied is not None:
                        environment["MA17_OVERRIDE_MOVC_AT"] = (
                            f"4912:727F:{supplied}")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["stop_ticks_observed"], 2400000)
                    self.assertEqual(report["engine_ram_observation"]["4D"][-1]
                                     ["after"], expected_4d)
                    self.assertEqual(report["cc3_observation"]
                                     ["iram14_15_median"], 1505)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1861)
                    reads = report["movc_observation"]["reads"]
                    self.assertGreater(sum(row["count"] for row in reads
                                           if row["pc"] == "4912" and
                                           row["address"] == "727F" and
                                           row["value"] == "2E"), 500)
                    rows = [dict(re.findall(r"(\w+)=(\w+)", line)) for line
                            in (output / "emulator-trace.log").read_text()
                            .splitlines() if line.startswith("[RAM4D-PATH]")]
                    steady = [row for row in rows if row["PC"] == "233B" and
                              int(row["tick"]) > 100000]
                    self.assertGreater(len(steady), 200)
                    self.assertTrue(all(row["R2"] == expected_r2
                                        for row in steady))
                    self.assertTrue(any(row["PC"] == "2580" and
                                        row["R2"] == expected_r2
                                        for row in rows))

    def test_744e_donor_changes_4d_and_fixed_point_consumer(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        alcohol = VARIANTS / EXPECTED[0]
        s88 = VARIANTS / EXPECTED[2]
        baseline_xram_writes = None
        with tempfile.TemporaryDirectory() as directory:
            for donor, expected_4d, late_r2 in ((None, "19", "2D"),
                                                 (alcohol, "2F", "56"),
                                                 (s88, "19", "2D")):
                with self.subTest(donor=donor):
                    output = Path(directory) / (donor.stem if donor else "baseline")
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH7": "63", "MA17_TRACE_RAM4D_PATH": "1",
                        "MA17_TRACE_CURVE_744E_PATH": "1"})
                    if donor:
                        environment.update({
                            "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(donor),
                            "MA17_OVERRIDE_MOVC_MATRIX_BASE": "744E"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "5000000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["stop_ticks_observed"], 5000000)
                    self.assertEqual(report["movc_matrix_size"], 10 if donor else None)
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(donor.read_bytes()).hexdigest()
                                     if donor else None)
                    self.assertEqual(report["engine_ram_observation"]["4D"][-1]
                                     ["after"], expected_4d)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1861)
                    self.assertEqual(report["cc3_observation"]
                                     ["iram14_15_median"], 625.5)
                    raw = report["movc_observation"]["reads"]
                    self.assertTrue(any(row["address"] == "744E" and
                                        row["value"] == "15" and
                                        row["count"] > 1000 for row in raw))
                    rows = [dict(re.findall(r"(\w+)=(\w+)", line)) for line in
                            (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[RAM4D-PATH]")]
                    inputs = [row for row in rows if row["PC"] == "2320"]
                    outputs = [row for row in rows if row["PC"] == "233B"]
                    self.assertEqual(len(inputs), len(outputs))
                    self.assertGreater(len(inputs), 400)
                    for before, after in zip(inputs, outputs):
                        value, factor = int(before["R2"], 16), int(before["A"], 16)
                        self.assertEqual(int(after["R2"], 16),
                                         min(0xBA, value + factor * value // 128))
                    late = [row for row in outputs if int(row["tick"]) > 1000000]
                    self.assertEqual(late[0]["R2"], late_r2)
                    self.assertTrue(any(row["PC"] == "2580" and
                                        row["P2"] == "F8" and row["R1"] == "42"
                                        for row in rows))
                    xram_writes = [tuple(re.findall(r"(?:PC|addr|value)=(\w+)", line))
                                   for line in (output / "emulator-trace.log")
                                   .read_text().splitlines()
                                   if line.startswith("[CURVE-744E-XRAM]")]
                    self.assertGreater(len(xram_writes), 400)
                    if baseline_xram_writes is None:
                        baseline_xram_writes = xram_writes
                    else:
                        self.assertEqual(xram_writes, baseline_xram_writes)

    def test_744e_ram4d_read_mediates_cc3_pulse_count_at_3000_rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        alcohol = VARIANTS / EXPECTED[0]
        observations = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, donor, supplied in (
                    ("control", False, None),
                    ("donor", True, None),
                    ("control_r2_2f", False, "2F"),
                    ("donor_r2_19", True, "19")):
                with self.subTest(name=name):
                    output = Path(directory) / name
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_",
                                                          "MA17_OVERRIDE_", "MA17_TRACE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH7": "63", "MA17_TRACE_RAM4D_PATH": "1"})
                    if donor:
                        environment.update({
                            "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(alcohol),
                            "MA17_OVERRIDE_MOVC_MATRIX_BASE": "744E"})
                    if supplied:
                        environment["MA17_OVERRIDE_IRAM_READ_AT"] = (
                            f"22F3:4D:{supplied}")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "3000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["engine_ram_observation"]["4D"][-1]
                                     ["after"], "2F" if donor else "19")
                    self.assertEqual(report["movc_matrix_size"], 10 if donor else None)
                    bound_reads = sum(row["count"] for row in
                                      report["movc_observation"]["reads"]
                                      if row["address"] == "7310")
                    cc3 = report["cc3_observation"]
                    edges = [(int(tick), int(value)) for tick, value in re.findall(
                        r"\[CC3-PIN\] tick=(\d+) .*value=([01])",
                        (output / "emulator-trace.log").read_text())]
                    observations[name] = (cc3, edges, bound_reads)
            for name, count, width, reads in (("control", 103, 1129, 123),
                                              ("donor", 228, 1150, 0),
                                              ("control_r2_2f", 228, 1150, 0),
                                              ("donor_r2_19", 103, 1129, 123)):
                cc3, edges, bound_reads = observations[name]
                self.assertEqual(cc3["cc3_pin_model_low_starts"], count)
                self.assertEqual(cc3["cc3_pin_model_median_low_width_ticks"], width)
                self.assertEqual(bound_reads, reads)
                self.assertEqual(len(edges), 2 * count)
            for left, right in (("control", "donor_r2_19"),
                                ("donor", "control_r2_2f")):
                first, second = observations[left][1], observations[right][1]
                self.assertEqual([value for _, value in first],
                                 [value for _, value in second])
                self.assertLessEqual(max(abs(a - b) for (a, _), (b, _) in
                                         zip(first, second)), 2)

    def test_744e_donor_cc3_branch_effect_depends_on_rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        alcohol = VARIANTS / EXPECTED[0]
        expected = {1500: ((51, 121), (51, 121)),
                    2000: ((68, 122), (68, 122)),
                    2500: ((86, 122), (118, 85))}
        with tempfile.TemporaryDirectory() as directory:
            for rpm, arms in expected.items():
                for donor, (pulses, bound_reads) in enumerate(arms):
                    with self.subTest(rpm=rpm, donor=donor):
                        output = Path(directory) / f"{rpm}_{donor}"
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_",
                                                              "MA17_OVERRIDE_",
                                                              "MA17_TRACE_"))}
                        environment.update({
                            "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                            "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                            "MA17_ADC_CH7": "63"})
                        if donor:
                            environment.update({
                                "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(alcohol),
                                "MA17_OVERRIDE_MOVC_MATRIX_BASE": "744E"})
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--trace-movc", "--no-kline-inject",
                             "--crank-immediate", "--rpm", str(rpm),
                             "--stop-ticks", "2400000", "--seconds", "20",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=40, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                        self.assertEqual(report["cc3_observation"]
                                         ["cc3_pin_model_low_starts"], pulses)
                        self.assertEqual(sum(row["count"] for row in
                                             report["movc_observation"]["reads"]
                                             if row["address"] == "7310"), bound_reads)

    def test_744e_f831_comparison_changes_branch_reachability(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        alcohol = VARIANTS / EXPECTED[0]
        expected = (("control", False, None, "22", "54", False, 103, 123),
                    ("donor", True, None, "F8", "7E", True, 228, 0),
                    ("control_f831_7e", False, "7E", "F8", "7E", True, 228, 0),
                    ("donor_f831_36", True, "36", "40", "36", False, 103, 123))
        with tempfile.TemporaryDirectory() as directory:
            for name, donor, supplied, accumulator, b_value, carry, pulses, reads in expected:
                with self.subTest(name=name):
                    output = Path(directory) / name
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_",
                                                          "MA17_OVERRIDE_", "MA17_TRACE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH7": "63", "MA17_TRACE_744E_BRANCH": "1",
                        "MA17_TRACE_XRAM_ADDRESS": "F831"})
                    if donor:
                        environment.update({
                            "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(alcohol),
                            "MA17_OVERRIDE_MOVC_MATRIX_BASE": "744E"})
                    if supplied:
                        environment["MA17_OVERRIDE_XRAM_READ_AT"] = (
                            f"2A8C:F831:{supplied}")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "3000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_low_starts"], pulses)
                    self.assertEqual(sum(row["count"] for row in
                                         report["movc_observation"]["reads"]
                                         if row["address"] == "7310"), reads)
                    hits = set((output / "pc-hits.txt").read_text().splitlines())
                    self.assertEqual("2B38" in hits, bool(reads))
                    self.assertEqual("2B42" in hits, bool(reads))
                    self.assertEqual("2C49" in hits, bool(reads))
                    rows = [dict(re.findall(r"(\w+)=(\w+)", line)) for line in
                            (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[CURVE-744E-BRANCH]")]
                    comparison = next(row for row in rows
                                      if row["PC"] == "2A91" and
                                      int(row["tick"]) > 260000)
                    self.assertEqual((comparison["A"], comparison["B"]),
                                     (accumulator, b_value))
                    self.assertEqual(bool(int(comparison["PSW"], 16) & 0x80), carry)
                    if supplied is None:
                        writes = [line for line in
                                  (output / "emulator-trace.log").read_text().splitlines()
                                  if line.startswith("[XRAM-ADDRESS-WRITE]") and
                                  "PC=2796 addr=F831" in line]
                        self.assertTrue(any("value=07->" +
                                            ("60" if donor else "36") in line
                                            for line in writes))

    def test_744e_donor_delays_guard_without_removing_it(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        alcohol = VARIANTS / EXPECTED[0]
        observations = {}
        with tempfile.TemporaryDirectory() as directory:
            for donor in (False, True):
                with self.subTest(donor=donor):
                    output = Path(directory) / ("donor" if donor else "control")
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_",
                                                          "MA17_OVERRIDE_", "MA17_TRACE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH7": "63", "MA17_TRACE_744E_BRANCH": "1",
                        "MA17_TRACE_XRAM_ADDRESS": "F831",
                        "MA17_TRACE_CC3_DECISION": "1",
                        "MA17_TRACE_CC3_AFTER_TICK": "900000"})
                    if donor:
                        environment.update({
                            "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(alcohol),
                            "MA17_OVERRIDE_MOVC_MATRIX_BASE": "744E"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "3000",
                         "--stop-ticks", "5000000", "--seconds", "40",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=60, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["stop_ticks_observed"], 5000000)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    branch = [dict(re.findall(r"(\w+)=(\w+)", line)) for line in lines
                              if line.startswith("[CURVE-744E-BRANCH]")]
                    decision = [dict(re.findall(r"(\w+)=(\w+)", line)) for line in lines
                                if line.startswith("[CC3-DECISION]")]
                    stages = {pc: int(next(row["tick"] for row in branch
                                           if row["PC"] == pc))
                              for pc in ("2AC7", "2AF9", "2B42", "2C49")}
                    guard_tick = int(next(row["tick"] for row in decision
                                          if int(row["flags26"], 16) & 0x80))
                    last_edge = max(int(match.group(1)) for line in lines
                                    if (match := re.search(
                                        r"^\[CC3-PIN\] tick=(\d+)", line)))
                    reads = sum(row["count"] for row in
                                report["movc_observation"]["reads"]
                                if row["address"] == "7310")
                    pulses = report["cc3_observation"]["cc3_pin_model_low_starts"]
                    threshold_value = "76" if donor else "54"
                    threshold_tick = int(next(re.search(r"tick=(\d+)", line).group(1)
                                              for line in lines
                                              if line.startswith("[XRAM-ADDRESS-WRITE]")
                                              and "PC=2796 addr=F831" in line
                                              and "->" + threshold_value in line))
                    clear_carry_tick = int(next(row["tick"] for row in branch
                                                if row["PC"] == "2A91" and
                                                int(row["tick"]) > 265000 and
                                                not int(row["PSW"], 16) & 0x80))
                    observations[donor] = (stages, guard_tick, last_edge,
                                           reads, pulses, threshold_tick,
                                           clear_carry_tick)
            control, donor = observations[False], observations[True]
            self.assertEqual((control[3], control[4]), (377, 103))
            self.assertEqual((donor[3], donor[4]), (179, 307))
            delays = [donor[0][pc] - control[0][pc]
                      for pc in ("2AC7", "2AF9", "2B42", "2C49")]
            self.assertGreater(min(delays), 2000000)
            self.assertLess(max(delays) - min(delays), 500)
            self.assertGreater(donor[1] - control[1], 2000000)
            self.assertGreater(donor[2] - control[2], 2000000)
            self.assertLess(control[2], control[1])
            self.assertLess(donor[2], donor[1])
            self.assertEqual((control[5], control[6]), (265886, 266070))
            self.assertEqual((donor[5], donor[6]), (2201240, 2201429))
            self.assertLess(control[6], control[0]["2AC7"])
            self.assertLess(donor[6], donor[0]["2AC7"])

    def test_744e_donor_restarts_xram39_nibble_countdown(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        alcohol = VARIANTS / EXPECTED[0]
        with tempfile.TemporaryDirectory() as directory:
            for donor in (False, True):
                with self.subTest(donor=donor):
                    output = Path(directory) / ("donor" if donor else "control")
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_",
                                                          "MA17_OVERRIDE_", "MA17_TRACE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH7": "63", "MA17_TRACE_744E_BRANCH": "1",
                        "MA17_TRACE_XRAM_ADDRESS": "F839"})
                    if donor:
                        environment.update({
                            "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(alcohol),
                            "MA17_OVERRIDE_MOVC_MATRIX_BASE": "744E"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "3000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    writes = [line for line in lines
                              if line.startswith("[XRAM-ADDRESS-WRITE]") and
                              "addr=F839" in line]
                    reset = "PC=2A4B addr=F839 value=06->0F"
                    self.assertEqual(any(reset in line for line in writes), donor)
                    continuation = ("tick=2201473 PC=555B addr=F839 value=0F->0E"
                                    if donor else
                                    "tick=266120 PC=555B addr=F839 value=06->05")
                    self.assertTrue(any(continuation in line for line in writes))
                    zero_return = next(dict(re.findall(r"(\w+)=(\w+)", line))
                                       for line in lines
                                       if line.startswith("[CURVE-744E-BRANCH]")
                                       and "PC=2AB7" in line and " A=00 " in line)
                    self.assertEqual(int(zero_return["tick"]),
                                     2344908 if donor else 317141)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_low_starts"],
                                     228 if donor else 103)

    def test_744e_first_cell_alone_reproduces_long_guard_delay(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        alcohol = VARIANTS / EXPECTED[0]
        observations = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, point in (("full_donor", None),
                                ("first_cell", "532F:744E:2F"),
                                ("second_cell", "5333:744F:36")):
                with self.subTest(name=name):
                    output = Path(directory) / name
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_",
                                                          "MA17_OVERRIDE_", "MA17_TRACE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH7": "63", "MA17_TRACE_744E_BRANCH": "1"})
                    if point:
                        environment["MA17_OVERRIDE_MOVC_AT"] = point
                    else:
                        environment.update({
                            "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(alcohol),
                            "MA17_OVERRIDE_MOVC_MATRIX_BASE": "744E"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "3000",
                         "--stop-ticks", "5000000", "--seconds", "40",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=60, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"], point)
                    self.assertEqual(report["movc_matrix_size"], 10 if not point else None)
                    self.assertEqual(report["stop_ticks_observed"], 5000000)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    edges = [(int(match.group(1)), int(match.group(2)))
                             for line in lines
                             if (match := re.search(
                                 r"^\[CC3-PIN\] tick=(\d+).*value=([01])", line))]
                    stage = int(next(dict(re.findall(r"(\w+)=(\w+)", line))["tick"]
                                     for line in lines
                                     if line.startswith("[CURVE-744E-BRANCH]")
                                     and "PC=2B42" in line))
                    reads = sum(row["count"] for row in
                                report["movc_observation"]["reads"]
                                if row["address"] == "7310")
                    observations[name] = (edges, stage, reads)
            donor, first, second = (observations[name] for name in
                                    ("full_donor", "first_cell", "second_cell"))
            self.assertEqual((len(donor[0]), donor[2]), (614, 179))
            self.assertEqual((len(first[0]), first[2]), (614, 179))
            self.assertEqual((len(second[0]), second[2]), (206, 377))
            self.assertEqual((donor[1], first[1], second[1]),
                             (3174451, 3174449, 1146773))
            self.assertEqual([value for _, value in donor[0]],
                             [value for _, value in first[0]])
            self.assertLessEqual(max(abs(a - b) for (a, _), (b, _) in
                                     zip(donor[0], first[0])), 2)
            self.assertEqual(donor[0][-1][0], first[0][-1][0])

    def test_iram79_7b_curves_are_naturally_read_in_g_and_s88(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        images = (("G", REFERENCE),
                  ("S88", VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"))
        expected = {("532F", "7523", "93"), ("5333", "7524", "A0"),
                    ("532F", "752D", "80"), ("5333", "752E", "86")}
        with tempfile.TemporaryDirectory() as directory:
            for name, firmware in images:
                with self.subTest(rom=name):
                    output = Path(directory) / name
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    environment.update({"MA17_ADC_CH2": "100", "MA17_ADC_CH3": "80",
                                        "MA17_ADC_CH7": "63"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000", "--trace-movc",
                         "--stop-ticks", "1600000", "--seconds", "12",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=20, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    reads = [item for item in report["movc_observation"]["reads"]
                             if 0x750C <= int(item["address"], 16) < 0x753E]
                    self.assertEqual({(item["pc"], item["address"], item["value"])
                                      for item in reads}, expected)
                    self.assertTrue(all(item["count"] > 100 for item in reads))

    def test_iram79_curve_changes_cc3_only_when_ram78_is_nonzero(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        images = (("G_zero", REFERENCE, "00"),
                  ("G", REFERENCE, "80"),
                  ("S88", VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin",
                   "80"))
        with tempfile.TemporaryDirectory() as directory:
            for name, firmware, ram78 in images:
                reports = []
                entries = []
                for override in (False, True):
                    with self.subTest(rom=name, override=override):
                        output = Path(directory) / f"{name}_{int(override)}"
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                              "MA17_TRACE_"))}
                        environment.update({"MA17_ADC_CH2": "100",
                                            "MA17_ADC_CH3": "80",
                                            "MA17_ADC_CH7": "63",
                                            "MA17_OVERRIDE_RAM78": ram78})
                        if override:
                            environment["MA17_OVERRIDE_MOVC_AT"] = "532F:7523:B5"
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000", "--trace-movc",
                             "--stop-ticks", "1600000", "--seconds", "12",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=20, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertEqual(report["ram78_override_hex"], ram78)
                        self.assertEqual(report["movc_override_at_hex"],
                                         "532F:7523:B5" if override else None)
                        self.assertEqual(report["engine_ram_observation"]["79"][0]
                                         ["after"], "B2" if override else "95")
                        raw = [row for row in report["movc_observation"]["reads"]
                               if row["pc"] == "532F" and row["address"] == "7523"]
                        self.assertEqual({row["value"] for row in raw}, {"93"})
                        self.assertGreater(sum(row["count"] for row in raw), 100)
                        log = (output / "emulator-trace.log").read_text()
                        entries.append([int(value, 16) for value in re.findall(
                            r"\[CC3-ENTRY\].*IRAM14_15=([0-9A-F]{4})", log)])
                        reports.append(report)
                self.assertEqual(len(entries[0]), 48)
                self.assertEqual(len(entries[1]), 48)
                if ram78 == "00":
                    self.assertEqual(entries[0], entries[1])
                else:
                    self.assertTrue(all(after > before for before, after in
                                        zip(entries[0], entries[1])))
                self.assertEqual([report["cc3_observation"]["iram14_15_median"]
                                  for report in reports],
                                 [1440, 1440] if ram78 == "00" else [1933, 2018])
                self.assertEqual([report["cc3_observation"]
                                  ["cc3_pin_model_median_low_width_ticks"]
                                  for report in reports],
                                 [5748, 5748] if ram78 == "00" else [7720, 8060])

    def test_ram78_gate_stays_closed_in_two_digital_tps_states(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((120, 95, "03", "04"), (180, 247, "09", "FF"))
        with tempfile.TemporaryDirectory() as directory:
            for adc0, adc6, r1, r7 in cases:
                with self.subTest(adc0=adc0, adc6=adc6):
                    output = Path(directory) / f"{adc0}_{adc6}"
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    environment.update({"MA17_ADC_CH0": str(adc0),
                                        "MA17_ADC_CH6": str(adc6),
                                        "MA17_ADC_CH2": "100", "MA17_ADC_CH3": "80",
                                        "MA17_ADC_CH7": "63",
                                        "MA17_TRACE_RAM78_GATE": "1"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "1600000", "--seconds", "12",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=20, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertTrue(report["ram78_gate_trace_enabled"])
                    self.assertNotIn("78", report["engine_ram_observation"])
                    lines = [line for line in (output / "emulator-trace.log")
                             .read_text().splitlines()
                             if line.startswith("[RAM78-GATE]")]
                    self.assertGreater(len(lines), 300)
                    # The probe also logs intermediate PCs; retain the
                    # original gate-point assertion independently of them.
                    gate_pcs = {"1A3A", "1B34", "1B3D", "1B48"}
                    self.assertEqual({line.split("PC=")[1][:4] for line in lines}
                                     & gate_pcs, gate_pcs)
                    lookup_lines = [line for line in lines if "PC=1A3A" in line]
                    guard_lines = [line for line in lines
                                   if any(f"PC={pc}" in line
                                          for pc in ("1B34", "1B3D", "1B48"))]
                    self.assertTrue(lookup_lines)
                    self.assertNotIn("00", {line.split("R1=")[1][:2]
                                             for line in lookup_lines})
                    self.assertEqual({line.split("R1=")[1][:2] for line in guard_lines},
                                     {r1})
                    self.assertEqual({line.split("R7=")[1][:2] for line in guard_lines},
                                     {r7})

    def test_7e16_path_needs_state_bit_even_when_two_flags_overlap(self):
        emulator = ROOT / "build" / "emu8051-tty"
        if not emulator.exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                  "MA17_TRACE_", "MA17_P4_"))}
            environment.update(
                MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                MA17_ADC10_STEP_CH0="200000:720",
                MA17_ADC10_STEP_CH6="200000:988",
                MA17_ADC_CH2="100", MA17_ADC_CH3="80",
                MA17_ADC_CH7="63", MA17_OVERRIDE_RAM78="80",
                MA17_TRACE_7E16_GATE="1")
            output = Path(directory)
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--firmware", str(REFERENCE), "--trace-movc",
                 "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                 "--stop-ticks", "2400000", "--seconds", "20",
                 "--output-dir", str(output)],
                capture_output=True, text=True, env=environment,
                timeout=30, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((output / "execution.json").read_text())
            self.assertEqual(report["firmware_sha256"],
                             hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
            self.assertEqual(report["emulator_sha256"],
                             hashlib.sha256(emulator.read_bytes()).hexdigest())
            self.assertFalse(any(0x7E16 <= int(row["mapped"], 16) < 0x7E8E
                                 for row in report["movc_observation"]["reads"]))
            lines = [line for line in (output / "emulator-trace.log")
                     .read_text().splitlines()
                     if line.startswith("[MATRIX-7E16-GATE]")]
            gate = [line for line in lines if "PC=3752" in line]
            self.assertTrue(any(int(line.split("F21=")[1][:2], 16) & 0x02 and
                                int(line.split("F2F=")[1][:2], 16) & 0x80
                                for line in gate))
            source = [line for line in lines if "PC=36DE" in line]
            self.assertTrue(source)
            self.assertTrue(all(int(line.split("B=")[1][:2], 16) & 0x20 == 0
                                for line in source))
            self.assertFalse(any("PC=3701" in line or "PC=371D" in line
                                 for line in lines))
            branch = [line for line in lines if "PC=37FB" in line]
            self.assertTrue(branch)
            self.assertTrue(all(int(line.split("B=")[1][:2], 16) & 0x01 == 0
                                for line in branch))
            self.assertFalse(any("PC=3830" in line for line in lines))

    def test_7e16_state_producer_reaches_original_code_at_higher_rpm(self):
        emulator = ROOT / "build" / "emu8051-tty"
        if not emulator.exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for rpm in (1000, 1500):
                with self.subTest(rpm=rpm):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(
                        MA17_P4_6_FORCE_LOW="1", MA17_ADC_CH0="40",
                        MA17_ADC_CH6="95", MA17_ADC10_STEP_CH6="200000:880",
                        MA17_ADC_CH2="100", MA17_ADC_CH3="80",
                        MA17_ADC_CH7="63", MA17_TRACE_7E16_GATE="1")
                    output = Path(directory) / str(rpm)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(REFERENCE), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm", str(rpm),
                         "--stop-ticks", "1600000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["emulator_sha256"],
                                     hashlib.sha256(emulator.read_bytes()).hexdigest())
                    self.assertFalse(any(0x7E16 <= int(row["mapped"], 16) < 0x7E8E
                                         for row in report["movc_observation"]["reads"]))
                    lines = [line for line in (output / "emulator-trace.log")
                             .read_text().splitlines()
                             if line.startswith("[MATRIX-7E16-GATE]")]
                    def at(pc):
                        return [line for line in lines if f"PC={pc}" in line]
                    self.assertEqual(len(at("2E06")), 1)
                    self.assertEqual(at("2E06")[0].split("RAM46=")[1][:2], "2A")
                    self.assertEqual(at("2E06")[0].split("RAM47=")[1][:2],
                                     "28" if rpm == 1000 else "3C")
                    self.assertEqual(len(at("2E1C")), 0 if rpm == 1000 else 1)
                    self.assertEqual(any(int(line.split("B=")[1][:2], 16) & 0x20
                                         for line in at("36DE")), rpm == 1500)
                    if rpm == 1500:
                        self.assertTrue(at("36FF"))
                        self.assertTrue(all(line.split("UC5=")[1][:2] == "53" and
                                            line.split("RAM70=")[1][:2] == "53" and
                                            line.split("A=")[1][:2] == "02"
                                            for line in at("36FF")))
                        self.assertFalse(at("3701"))

    def test_rpm_extremes_keep_ram78_zero_and_lookup_in_bounds(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((300, {("7AB0", "00", "03"), ("7AB0", "2A", "09")},
                  {"1A3A"}),
                 (6000, {("79F0", "2F", "0B"), ("7AB0", "00", "03"),
                         ("7AB0", "2A", "09"), ("7AB0", "2F", "09")},
                  {"1A3A", "1B34", "1B3D", "1B48"}))
        with tempfile.TemporaryDirectory() as directory:
            for rpm, expected_reads, expected_gates in cases:
                with self.subTest(rpm=rpm):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_CH",
                                                          "MA17_ADC10_STEP_CH",
                                                          "MA17_OVERRIDE_", "MA17_TRACE_"))
                                   and key != "MA17_P4_6_FORCE_LOW"}
                    environment.update(MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                                       MA17_ADC_CH3="4", MA17_ADC_CH5="40",
                                       MA17_ADC_CH7="63", MA17_TRACE_RAM78_GATE="1")
                    output = Path(directory) / str(rpm)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         str(rpm), "--stop-ticks", "2400000", "--seconds",
                         "15", "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment, timeout=25)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    rows = [x for x in report["movc_observation"]["reads"]
                            if x["pc"] == "1A38"]
                    self.assertEqual({(x["dptr"], x["acc"], x["value"])
                                      for x in rows}, expected_reads)
                    self.assertTrue(all(int(x["acc"], 16) < 48 and
                                        int(x["value"], 16) > 0 for x in rows))
                    self.assertNotIn("78", report["engine_ram_observation"])
                    log = (output / "emulator-trace.log").read_text()
                    gate_pcs = {"1A3A", "1B34", "1B3D", "1B48"}
                    self.assertEqual({line.split("PC=")[1][:4] for line in
                                      log.splitlines() if line.startswith(
                                          "[RAM78-GATE]")} & gate_pcs,
                                     expected_gates)
                    gate_lines = [line for line in log.splitlines()
                                  if line.startswith("[RAM78-GATE]")]
                    at_lookup = {line.split("R1=")[1][:2] for line in gate_lines
                                 if "PC=1A3A" in line}
                    at_guard = {line.split("R1=")[1][:2] for line in gate_lines
                                if "PC=1B34" in line}
                    self.assertTrue(at_lookup)
                    self.assertTrue(at_guard <= at_lookup)
                    self.assertNotIn("00", at_lookup | at_guard)
                    ram78_reads = re.findall(
                        r"\[INJECTION-FLOW\].* PC=1D4B .*?RAM78=([0-9A-F]{2})",
                        log)
                    self.assertTrue(ram78_reads)
                    self.assertEqual(set(ram78_reads), {"00"})

    def test_r1_lookup_zero_opens_1bfd_without_ram78_at_zero_r6(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (("control", None, False),
                 ("early_7ada", "1A38:7ADA:00", False),
                 ("gate_7adf", "1A38:7ADF:00", True),
                 ("gate_7a1f", "1A38:7A1F:00", True))
        summaries = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, override, gate_open in cases:
                with self.subTest(name=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    environment.update({"MA17_TRACE_RAM78_GATE": "1",
                                        "MA17_ADC_CH0": "180", "MA17_ADC_CH2": "100",
                                        "MA17_ADC_CH3": "4", "MA17_ADC_CH5": "40",
                                        "MA17_ADC_CH6": "247", "MA17_ADC_CH7": "63"})
                    if override:
                        environment["MA17_OVERRIDE_MOVC_AT"] = override
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "6000",
                         "--trace-movc", "--stop-ticks", "2400000",
                         "--seconds", "30", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"], override)
                    raw_reads = {(row["mapped"], row["value"]): row["count"]
                                 for row in report["movc_observation"]["reads"]
                                 if row["pc"] == "1A38"}
                    self.assertEqual(raw_reads.get(("7ADA", "09")), 10)
                    self.assertEqual(raw_reads.get(("7ADF", "09")), 104)
                    self.assertEqual(raw_reads.get(("7A1F", "0B")), 115)
                    log = (output / "emulator-trace.log").read_text()
                    initial = re.findall(
                        r"\[RAM78-GATE\].*?PC=1A3A R1=([0-9A-F]{2})", log)
                    at_guard = re.findall(
                        r"\[RAM78-GATE\].*?PC=1B34 R1=([0-9A-F]{2})", log)
                    at_1bfd = re.findall(
                        r"\[RAM78-GATE\].*?PC=1BFD R1=00 R6=([0-9A-F]{2})", log)
                    self.assertEqual("00" in at_guard, gate_open)
                    self.assertEqual(bool(at_1bfd), gate_open)
                    self.assertEqual(set(at_1bfd), {"00"} if gate_open else set())
                    self.assertEqual("00" in initial, override is not None)
                    self.assertNotIn("78", report["engine_ram_observation"])
                    self.assertEqual(set(re.findall(
                        r"\[RAM78-GATE\].*?RAM78=([0-9A-F]{2})", log)),
                        {"00"})
                    summaries[name] = (
                        report["cc3_observation"]["iram14_15_median"],
                        report["cc3_observation"]["cc3_pin_model_median_low_width_ticks"],
                        report["output_latches"]["P5.0"]["median_low_width_ticks"])
        self.assertEqual(len(set(summaries.values())), 1)

    def test_ram78_r6_gate_reaches_cc3_input_through_1d4b(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (("gate", None, None),
                 ("r6_zero", "00", None),
                 ("r6_one", "01", None),
                 ("consumer_zero", "01", "00"))
        summaries = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, r6, consumer in cases:
                with self.subTest(name=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "180", "MA17_ADC_CH2": "100",
                        "MA17_ADC_CH3": "4", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "247", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_RAM78_GATE": "1",
                        "MA17_OVERRIDE_MOVC_AT": "1A38:7ADF:00"})
                    if r6 is not None:
                        environment["MA17_OVERRIDE_R6_AT_1C19"] = r6
                    if consumer is not None:
                        environment["MA17_OVERRIDE_RAM78"] = consumer
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "6000",
                         "--trace-movc", "--stop-ticks", "2400000",
                         "--seconds", "30", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"],
                                     "1A38:7ADF:00")
                    self.assertEqual(report["r6_1c19_override_hex"], r6)
                    self.assertEqual(report["ram78_override_hex"], consumer)
                    log = (output / "emulator-trace.log").read_text()
                    self.assertIn("PC=1BFD R1=00 R6=00", log)
                    writes = report["engine_ram_observation"].get("78", [])
                    at_consumer = set(re.findall(
                        r"\[INJECTION-FLOW\].* PC=1D4B .*?RAM78=([0-9A-F]{2})",
                        log))
                    if r6 == "01":
                        self.assertIn("[RAM78-R6-OVERRIDE] PC=1C19", log)
                        self.assertTrue(any(row["source_pc"] == "1C36"
                                            for row in writes))
                        self.assertRegex(log, r"\[RAM78-GATE\].*PC=1C34")
                        if consumer is None:
                            self.assertTrue(at_consumer - {"00"})
                        else:
                            self.assertEqual(at_consumer, {"00"})
                    else:
                        self.assertFalse(writes)
                        self.assertEqual(at_consumer, {"00"})
                    summaries[name] = (
                        report["cc3_observation"]["iram14_15_median"],
                        report["cc3_observation"]["cc3_pin_model_paired_pulses"],
                        report["output_latches"]["P5.0"]["median_low_width_ticks"])
        self.assertEqual(summaries["gate"], summaries["r6_zero"])
        self.assertEqual(summaries["gate"], summaries["consumer_zero"])
        self.assertGreater(summaries["r6_one"][0], summaries["gate"][0])
        self.assertLess(summaries["r6_one"][1], summaries["gate"][1])
        self.assertEqual(summaries["r6_one"][2], summaries["gate"][2])

    def test_natural_tps_opening_reaches_ram78_curve_and_consumer(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (("opening", 40, 95, 720, 988, False),
                 ("closing", 180, 247, 160, 380, False),
                 ("opening_zero_consumer", 40, 95, 720, 988, True),
                 ("opening_factor_zero", 40, 95, 720, 988, False),
                 ("opening_factor_ec", 40, 95, 720, 988, False),
                 ("opening_factor_f0", 40, 95, 720, 988, False))
        results = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, adc0, adc6, target0, target6, zero in cases:
                with self.subTest(name=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": str(adc0), "MA17_ADC_CH2": "100",
                        "MA17_ADC_CH3": "4", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": str(adc6), "MA17_ADC_CH7": "63",
                        "MA17_ADC10_STEP_CH0": f"800000:{target0}",
                        "MA17_ADC10_STEP_CH6": f"800000:{target6}",
                        "MA17_TRACE_RAM78_GATE": "1"})
                    if zero:
                        environment["MA17_OVERRIDE_RAM78"] = "00"
                    factor = {"opening_factor_zero": "00",
                              "opening_factor_ec": "EC",
                              "opening_factor_f0": "F0"}.get(name)
                    if factor:
                        environment["MA17_OVERRIDE_MOVC_AT"] = (
                            f"079C:73F4:{factor}")
                    output = Path(directory) / name
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "6000",
                         "--trace-movc", "--stop-ticks", "2400000",
                         "--seconds", "30", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"],
                                     f"079C:73F4:{factor}" if factor else None)
                    self.assertIsNone(report["r6_1c19_override_hex"])
                    log = (output / "emulator-trace.log").read_text()
                    writes = report["engine_ram_observation"].get("78", [])
                    reads = report["movc_observation"]["reads"]
                    if name != "closing":
                        self.assertRegex(log,
                                         r"\[RAM78-GATE\].*PC=1C19 R1=00 R6=FF")
                        self.assertTrue(any(row["source_pc"] == "1C36"
                                            and row["after"] == "FF" for row in writes))
                        self.assertEqual({(row["mapped"], row["value"]): row["count"]
                                          for row in reads if row["pc"] in
                                          {"532F", "5333"} and row["mapped"]
                                          in {"7146", "7147"}},
                                         {("7146", "FF"): 5,
                                          ("7147", "FF"): 5})
                        self.assertTrue(all(int(row["value"], 16) > 0
                                            for row in reads if row["pc"] == "1A38"))
                        if factor:
                            self.assertTrue(any(row["source_pc"] == "07A1"
                                                and row["before"] == "FF"
                                                and row["after"] ==
                                                {"00": "00", "EC": "EB",
                                                 "F0": "EF"}[factor]
                                                for row in writes))
                            self.assertTrue(any(row["pc"] == "079C"
                                                and row["mapped"] == "73F4"
                                                and row["value"] == "EE"
                                                and row["count"] == 110
                                                for row in reads))
                    else:
                        self.assertFalse(writes)
                        self.assertNotIn("PC=1C19 R1=00", log)
                    pairs = re.findall(
                        r"\[INJECTION-FLOW\] tick=(\d+) PC=1DD8 "
                        r"R2=([0-9A-F]{2}) R3=([0-9A-F]{2})", log)
                    nonzero_reads = sum(value != "00" for value in re.findall(
                        r"\[INJECTION-FLOW\].*PC=1D4B.*RAM78=([0-9A-F]{2})",
                        log))
                    results[name] = (
                        {r3 + r2 for tick, r2, r3 in pairs
                         if 817000 <= int(tick) <= 840000},
                        report["cc3_observation"]["iram14_15_median"],
                        {r3 + r2 for tick, r2, r3 in pairs
                         if 890000 <= int(tick) <= 910000}, nonzero_reads)
        self.assertIn("07A4", results["opening"][0])
        self.assertIn("044D", results["opening_zero_consumer"][0])
        self.assertEqual(results["opening"][1],
                         results["opening_zero_consumer"][1])
        self.assertIn("06C5", results["opening"][2])
        self.assertEqual(results["opening_factor_zero"][2], {"044D"})
        self.assertIn("06AF", results["opening_factor_ec"][2])
        self.assertIn("06DF", results["opening_factor_f0"][2])
        self.assertGreater(results["opening"][3],
                           results["opening_factor_zero"][3])

    def test_s88_tps_opening_73f4_factor_reaches_ram78_consumer(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        firmware = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        results = {}
        with tempfile.TemporaryDirectory() as directory:
            for factor in ("EE", "EC", "F0", "00"):
                with self.subTest(factor=factor):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH2": "100",
                        "MA17_ADC_CH3": "4", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                        "MA17_ADC10_STEP_CH0": "800000:720",
                        "MA17_ADC10_STEP_CH6": "800000:988",
                        "MA17_TRACE_RAM78_GATE": "1"})
                    if factor != "EE":
                        environment["MA17_OVERRIDE_MOVC_AT"] = (
                            f"079C:73F4:{factor}")
                    output = Path(directory) / factor
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "6000", "--trace-movc",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    log = (output / "emulator-trace.log").read_text()
                    self.assertRegex(log,
                                     r"\[RAM78-GATE\].*PC=1C19 R1=00 R6=FF")
                    writes = report["engine_ram_observation"].get("78", [])
                    self.assertTrue(any(row["source_pc"] == "1C36"
                                        and row["after"] == "FF" for row in writes))
                    self.assertTrue(any(row["source_pc"] == "07A1"
                                        and row["before"] == "FF"
                                        and row["after"] ==
                                        {"EE": "ED", "EC": "EB",
                                         "F0": "EF", "00": "00"}[factor]
                                        for row in writes))
                    self.assertTrue(any(row["pc"] == "079C"
                                        and row["mapped"] == "73F4"
                                        and row["value"] == "EE"
                                        and row["count"] == 110
                                        for row in report["movc_observation"]["reads"]))
                    values = re.findall(
                        r"\[INJECTION-FLOW\] tick=(\d+) PC=1DD8 "
                        r"R2=([0-9A-F]{2}) R3=([0-9A-F]{2})", log)
                    results[factor] = (
                        {r3 + r2 for tick, r2, r3 in values
                         if 890000 <= int(tick) <= 910000},
                        report["cc3_observation"]["iram14_15_median"],
                        report["output_latches"]["P5.0"]["median_low_width_ticks"])
        self.assertIn("0793", results["EE"][0])
        self.assertIn("077B", results["EC"][0])
        self.assertIn("07B0", results["F0"][0])
        self.assertEqual(results["00"][0], {"04D0"})
        self.assertEqual({value[1:] for value in results.values()},
                         {(340.0, 1843)})

    def test_ram78_tps_step_gate_repeats_across_rpm_and_g_s88(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((1000, 120, 180, ["FF", "FC", "B6", "9A", "7E"], 1),
                 (3000, 180, 247, ["FF"] * 5, 3))
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                for rpm, adc0, adc6, expected_r6, expected_writes in cases:
                    with self.subTest(firmware=firmware.name, rpm=rpm,
                                      adc0=adc0, adc6=adc6):
                        environment = {key: value for key, value in
                                       os.environ.items() if not key.startswith("MA17_")}
                        environment.update({
                            "MA17_ADC_CH0": "40", "MA17_ADC_CH2": "100",
                            "MA17_ADC_CH3": "4", "MA17_ADC_CH5": "40",
                            "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                            "MA17_ADC10_STEP_CH0": f"800000:{adc0 * 4}",
                            "MA17_ADC10_STEP_CH6": f"800000:{adc6 * 4}",
                            "MA17_TRACE_RAM78_GATE": "1"})
                        output = Path(directory) / (
                            f"{firmware.stem}_{rpm}_{adc0}_{adc6}")
                        run = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", str(rpm),
                             "--stop-ticks", "2400000", "--seconds", "30",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=35, check=False)
                        self.assertEqual(run.returncode, 0,
                                         run.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertIsNone(report["movc_override_at_hex"])
                        self.assertIsNone(report["r6_1c19_override_hex"])
                        self.assertIsNone(report["ram78_override_hex"])
                        log = (output / "emulator-trace.log").read_text()
                        gates = re.findall(
                            r"\[RAM78-GATE\].*PC=1C19 R1=([0-9A-F]{2}) "
                            r"R6=([0-9A-F]{2})", log)
                        self.assertEqual(gates, [("00", value)
                                                 for value in expected_r6])
                        writes = [row for row in report[
                            "engine_ram_observation"].get("78", [])
                            if row["source_pc"] == "1C36"]
                        self.assertEqual(len(writes), expected_writes)
                        self.assertEqual(writes[0]["after"], "FF")

    def test_7520_donor_needs_natural_ram78_at_1d4b(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        expected = {REFERENCE: ("06C5", "07DC", "044D", 217.0, 1847),
                    sun: ("0793", "08CC", "04D0", 340.0, 1843)}
        with tempfile.TemporaryDirectory() as directory:
            for firmware, (native, donor_pair, zero_pair,
                           cc3_median, p5_median) in expected.items():
                for donor in (False, True):
                    for zero in (False, True):
                        with self.subTest(firmware=firmware.name,
                                          donor=donor, zero=zero):
                            environment = {key: value for key, value in
                                           os.environ.items()
                                           if not key.startswith("MA17_")}
                            environment.update({
                                "MA17_ADC_CH0": "40", "MA17_ADC_CH2": "100",
                                "MA17_ADC_CH3": "4", "MA17_ADC_CH5": "40",
                                "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                                "MA17_ADC10_STEP_CH0": "800000:720",
                                "MA17_ADC10_STEP_CH6": "800000:988",
                                "MA17_TRACE_RAM78_GATE": "1"})
                            if donor:
                                environment["MA17_OVERRIDE_MOVC_AT"] = (
                                    "532F:7520:6F")
                            if zero:
                                environment["MA17_OVERRIDE_RAM78"] = "00"
                            output = Path(directory) / (
                                f"{firmware.stem}_{int(donor)}_{int(zero)}")
                            run = subprocess.run(
                                [sys.executable,
                                 str(ROOT / "tools" / "trace_ma17.py"),
                                 "--firmware", str(firmware),
                                 "--no-kline-inject", "--crank-immediate",
                                 "--rpm", "6000", "--trace-movc",
                                 "--stop-ticks", "2400000", "--seconds", "30",
                                 "--output-dir", str(output)],
                                capture_output=True, text=True,
                                env=environment, timeout=35, check=False)
                            self.assertEqual(run.returncode, 0,
                                             run.stderr[-1500:])
                            report = json.loads(
                                (output / "execution.json").read_text())
                            self.assertEqual(report["firmware_sha256"],
                                             hashlib.sha256(
                                                 firmware.read_bytes()).hexdigest())
                            self.assertEqual(report["movc_override_at_hex"],
                                             "532F:7520:6F" if donor else None)
                            self.assertEqual(report["ram78_override_hex"],
                                             "00" if zero else None)
                            self.assertEqual(report["engine_ram_observation"][
                                "79"][0]["after"], "6F" if donor else "4D")
                            self.assertTrue(any(
                                row["pc"] == "532F" and row["mapped"] ==
                                "7520" and row["value"] == "4D"
                                for row in report["movc_observation"]["reads"]))
                            log = (output / "emulator-trace.log").read_text()
                            self.assertRegex(log,
                                             r"\[RAM78-GATE\].*PC=1C19 R1=00 R6=FF")
                            pairs = re.findall(
                                r"\[INJECTION-FLOW\] tick=(\d+) PC=1DD8 "
                                r"R2=([0-9A-F]{2}) R3=([0-9A-F]{2})", log)
                            observed = {r3 + r2 for tick, r2, r3 in pairs
                                        if 890000 <= int(tick) <= 910000}
                            self.assertIn(zero_pair if zero else
                                          donor_pair if donor else native, observed)
                            self.assertEqual(report["cc3_observation"][
                                "iram14_15_median"], cc3_median)
                            self.assertEqual(report["output_latches"]["P5.0"][
                                "median_low_width_ticks"], p5_median)

    def test_7520_donor_changes_local_cc3_pulse_via_ram78_at_3000_rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((REFERENCE, False, False, "07FA", 8156),
                 (REFERENCE, True, False, "0947", 9488),
                 (REFERENCE, False, True, "0506", 5132),
                 (REFERENCE, True, True, "0506", 5132),
                 (sun, False, False, "08F0", 9140),
                 (sun, True, False, "0A67", 9885))
        with tempfile.TemporaryDirectory() as directory:
            for firmware, donor, zero, expected_input, expected_width in cases:
                with self.subTest(firmware=firmware.name, donor=donor,
                                  zero_ram78=zero):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH2": "100",
                        "MA17_ADC_CH3": "4", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                        "MA17_ADC10_STEP_CH0": "800000:720",
                        "MA17_ADC10_STEP_CH6": "800000:988",
                        "MA17_TRACE_RAM78_GATE": "1"})
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_AT"] = "532F:7520:6F"
                    if zero:
                        environment["MA17_OVERRIDE_RAM78"] = "00"
                    output = Path(directory) / (
                        f"{firmware.stem}_{int(donor)}_{int(zero)}")
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "3000", "--trace-movc",
                         "--stop-ticks", "1100000", "--seconds", "30",
                         "--output-dir", str(output)], capture_output=True,
                        text=True, env=environment, timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    log = (output / "emulator-trace.log").read_text()
                    entries = re.findall(
                        r"\[CC3-ENTRY\] instr=(\d+) PC=058E .*?"
                        r"IRAM14_15=([0-9A-F]{4})", log)
                    local_inputs = [value for tick, value in entries
                                    if 907000 <= int(tick) < 907200]
                    self.assertEqual(local_inputs, [expected_input])
                    edges = [(int(tick), int(value)) for tick, value in
                             re.findall(r"\[CC3-PIN\] tick=(\d+) .*?"
                                        r"value=(\d)", log)]
                    widths = [next_tick - tick for (tick, value),
                              (next_tick, next_value) in zip(edges, edges[1:])
                              if 907000 <= tick < 907200 and value == 0
                              and next_value == 1]
                    self.assertEqual(len(widths), 1)
                    self.assertLessEqual(abs(widths[0] - expected_width), 2)

    def test_ram78_tps_adc10_boundary_follows_channel6_in_tested_state(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((REFERENCE, 189, 409, False, "2F", "66", "1D", "D1"),
                 (REFERENCE, 190, 410, True, "30", "67", "1E", "E1"),
                 (sun, 189, 409, False, "2F", "66", "1D", "D1"),
                 (sun, 190, 410, True, "30", "67", "1E", "E1"),
                 (REFERENCE, 190, 409, False, "30", "66", "1D", "D1"),
                 (REFERENCE, 189, 410, True, "2F", "67", "1E", "E1"))
        with tempfile.TemporaryDirectory() as directory:
            for firmware, adc0, adc6, opens, ram60, ram66, ram70, ram6a in cases:
                with self.subTest(firmware=firmware.name,
                                  adc0=adc0, adc6=adc6):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC10_CH0": "160", "MA17_ADC10_CH6": "380",
                        "MA17_ADC10_STEP_CH0": f"800000:{adc0}",
                        "MA17_ADC10_STEP_CH6": f"800000:{adc6}",
                        "MA17_ADC_CH2": "100", "MA17_ADC_CH3": "4",
                        "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_RAM78_GATE": "1"})
                    output = Path(directory) / (
                        f"{firmware.stem}_{adc0}_{adc6}")
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    for address, expected in (("60", ram60), ("66", ram66),
                                              ("70", ram70), ("6A", ram6a)):
                        events = report["sensor_ram_observation"].get(
                            address, report["engine_ram_observation"].get(
                                address, []))
                        changed = [row["after"] for row in events
                                   if 800000 <= row["tick"] <= 810000]
                        should_change = (adc0 != 160 if address == "60"
                                         else adc6 != 380)
                        self.assertEqual(bool(changed), should_change)
                        if should_change:
                            self.assertEqual(changed[-1], expected)
                    log = (output / "emulator-trace.log").read_text()
                    entries = re.findall(
                        r"\[RAM78-GATE\].*PC=1C19 R1=00 R6=([0-9A-F]{2})",
                        log)
                    writes = [row for row in report[
                        "engine_ram_observation"].get("78", [])
                        if row["source_pc"] == "1C36"]
                    self.assertEqual(bool(entries), opens)
                    self.assertEqual(bool(writes), opens)
                    if opens:
                        self.assertEqual(len(entries), 5)
                        self.assertEqual(writes[0]["after"], "97")

    def test_temperature_adc10_rounding_and_channel_isolation(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((160, 163, "28", "29"),
                 (163, 160, "29", "28"),
                 (161, 161, "28", "28"),
                 (162, 162, "29", "29"))
        with tempfile.TemporaryDirectory() as directory:
            for adc2, adc3, air, coolant in cases:
                with self.subTest(adc2=adc2, adc3=adc3):
                    output = Path(directory) / f"{adc2}_{adc3}"
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC10_CH2": str(adc2),
                                        "MA17_ADC10_CH3": str(adc3),
                                        "MA17_ADC_CH7": "63"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "200000", "--seconds", "5",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=15, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    observed = report["sensor_ram_observation"]
                    self.assertEqual(observed["62"][-1]["after"], air)
                    self.assertEqual(observed["63"][-1]["after"], coolant)
                    self.assertEqual(observed["62"][-1]["source_pc"], "0744")
                    self.assertEqual(observed["63"][-1]["source_pc"], "4756")

    def test_coolant_segment_movc_result_changes_cc3_without_rom_patch(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                for override, ram4e, ram87, cc3, width in (
                        (False, "23", "1A", 1422, 5677),
                        (True, "F3", "1D", 1498, 5981)):
                    with self.subTest(firmware=firmware.name, override=override):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_ADC10_STEP_CH",
                                                              "MA17_OVERRIDE_", "MA17_TRACE_"))}
                        environment.update({"MA17_ADC_CH2": "100",
                                            "MA17_ADC_CH3": "80",
                                            "MA17_ADC_CH7": "63"})
                        if override:
                            environment["MA17_OVERRIDE_MOVC_AT"] = "52A2:73D9:01"
                        output = Path(directory) / firmware.stem / str(override)
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "25",
                             "--trace-movc", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=35, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["emulator_exit"], 0)
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertEqual(report["adc_input_values"][2:4], [100, 80])
                        self.assertEqual(report["sensor_ram_observation"]
                                         ["63"][-1]["after"], "50")
                        engine = report["engine_ram_observation"]
                        self.assertEqual(engine["4E"][-1]["after"], ram4e)
                        self.assertEqual([row["after"] for row in engine["87"]
                                          if row["source_pc"] == "12CC"][-1], ram87)
                        self.assertEqual(report["cc3_observation"]
                                         ["iram14_15_median"], cc3)
                        self.assertEqual(report["cc3_observation"]
                                         ["cc3_pin_model_median_low_width_ticks"], width)
                        self.assertTrue(any(row["pc"] == "52A2" and
                                            row["mapped"] == "73D9" and
                                            row["value"] == "2A" for row in
                                            report["movc_observation"]["reads"]))
                        self.assertEqual("[MOVC-OVERRIDE] PC=52A2" in
                                         (output / "emulator-trace.log").read_text(),
                                         override)

    def test_coolant_factor_reads_do_not_change_cc3_with_zero_ram78_and_7a(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        substitutions = ((None, None, None),
                         ("079C:73F4:00", "079C", "73F4"),
                         ("07AE:73FE:00", "07AE", "73FE"))
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                for override, pc, address in substitutions:
                    with self.subTest(firmware=firmware.name, override=override):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_ADC10_STEP_CH",
                                                              "MA17_OVERRIDE_", "MA17_TRACE_"))}
                        environment.update(MA17_ADC10_CH2="400", MA17_ADC10_CH3="160",
                                           MA17_ADC10_STEP_CH3="800000:208",
                                           MA17_ADC_CH7="63")
                        if override:
                            environment["MA17_OVERRIDE_MOVC_AT"] = override
                        output = Path(directory) / firmware.stem / (override or "control")
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "15",
                             "--trace-movc", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment, timeout=25)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        engine = report["engine_ram_observation"]
                        self.assertNotIn("78", engine)
                        self.assertNotIn("7A", engine)
                        self.assertEqual(engine["4E"][-1]["after"], "00")
                        self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                         1160)
                        self.assertEqual(report["cc3_observation"]
                                         ["cc3_pin_model_median_low_width_ticks"], 4629)
                        log = (output / "emulator-trace.log").read_text()
                        if override:
                            self.assertIn(f"[MOVC-OVERRIDE] PC={pc} mapped={address}", log)
                            self.assertTrue(any(row["pc"] == pc and
                                                row["mapped"] == address for row in
                                                report["movc_observation"]["reads"]))
                        else:
                            self.assertNotIn("[MOVC-OVERRIDE]", log)

    def test_coolant_ram4f_read_mediates_boundary_cc3_contrast(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((204, None, "33", "42", "77", 1228),
                 (208, None, "11", "00", "34", 1160),
                 (204, "00", "33", "42", "34", 1160),
                 (208, "04", "11", "00", "77", 1228))
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                factor_reads = []
                upper_87 = []
                for adc3, override, ram63, ram4e, ram5a, cc3 in cases:
                    with self.subTest(firmware=firmware.name, adc3=adc3,
                                      override=override):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_ADC10_STEP_CH",
                                                              "MA17_OVERRIDE_", "MA17_TRACE_"))}
                        environment.update(MA17_ADC10_CH2="400", MA17_ADC10_CH3="160",
                                           MA17_ADC10_STEP_CH3=f"800000:{adc3}",
                                           MA17_ADC_CH7="63")
                        if override is not None:
                            environment["MA17_OVERRIDE_RAM4F"] = override
                        output = Path(directory) / firmware.stem / f"{adc3}_{override}"
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "15",
                             "--trace-movc", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment, timeout=25)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertEqual(report["ram4f_override_hex"], override)
                        self.assertEqual(report["sensor_ram_observation"]["63"][-1]
                                         ["after"], ram63)
                        engine = report["engine_ram_observation"]
                        self.assertEqual(engine["4E"][-1]["after"], ram4e)
                        self.assertEqual(engine["5A"][-1]["after"], ram5a)
                        self.assertEqual(engine["5A"][-1]["source_pc"], "1646")
                        self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                         cc3)
                        log = (output / "emulator-trace.log").read_text()
                        self.assertEqual("[RAM4F-OVERRIDE] PC=1588" in log,
                                         override is not None)
                        factor_reads.append([(row["pc"], row["mapped"], row["value"])
                                             for row in report["movc_observation"]["reads"]
                                             if 0x7426 <= int(row["mapped"], 16) < 0x7430])
                        upper_87.append([(row["after"], row["source_pc"])
                                         for row in engine["87"]])
                self.assertTrue(all(reads == factor_reads[0] for reads in factor_reads))
                self.assertTrue(all(values == upper_87[0] for values in upper_87))

    def test_coolant_ram4f_curve_cell_reaches_cc3_with_original_rom(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((204, "532F:74F0:14", "04", "77", 1228),
                 (208, "532F:74EE:10", "00", "34", 1160))
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                for adc3, override, control_4f, control_5a, control_cc3 in cases:
                    for supplied in (False, True):
                        with self.subTest(firmware=firmware.name, adc3=adc3,
                                          supplied=supplied):
                            environment = {key: value for key, value in os.environ.items()
                                           if not key.startswith(("MA17_ADC_CH",
                                                                  "MA17_ADC10_CH",
                                                                  "MA17_ADC10_STEP_CH",
                                                                  "MA17_OVERRIDE_", "MA17_TRACE_"))}
                            environment.update(MA17_ADC10_CH2="400",
                                               MA17_ADC10_CH3="160",
                                               MA17_ADC10_STEP_CH3=f"800000:{adc3}",
                                               MA17_ADC_CH7="63")
                            if supplied:
                                environment["MA17_OVERRIDE_MOVC_AT"] = override
                            output = Path(directory) / firmware.stem / f"{adc3}_{supplied}"
                            result = subprocess.run(
                                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                                 "--firmware", str(firmware), "--no-kline-inject",
                                 "--crank-immediate", "--rpm", "1000",
                                 "--stop-ticks", "2400000", "--seconds", "15",
                                 "--trace-movc", "--output-dir", str(output)],
                                capture_output=True, text=True, env=environment,
                                timeout=25)
                            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                            report = json.loads((output / "execution.json").read_text())
                            self.assertEqual(report["firmware_sha256"],
                                             hashlib.sha256(firmware.read_bytes()).hexdigest())
                            self.assertEqual(report["movc_override_at_hex"],
                                             override if supplied else None)
                            engine = report["engine_ram_observation"]
                            self.assertEqual(engine["4F"][-1]["after"],
                                             "10" if supplied else control_4f)
                            self.assertEqual(engine["5A"][-1]["after"],
                                             "41" if supplied else control_5a)
                            self.assertEqual(report["cc3_observation"]
                                             ["iram14_15_median"],
                                             1433 if supplied else control_cc3)
                            self.assertEqual("[MOVC-OVERRIDE]" in
                                             (output / "emulator-trace.log").read_text(),
                                             supplied)

    def test_coolant_curve_7502_read_is_lookahead_from_74f8(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((160, 80, None, {"74FB", "74FC"}, "08", 1495),
                 (100, 220, None, {"7501", "7502"}, "24", 2678),
                 (100, 220, "5333:7502:FF", {"7501", "7502"}, "24", 2678))
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                for adc2, adc3, override, addresses, ram4f, cc3 in cases:
                    with self.subTest(firmware=firmware.name, adc2=adc2,
                                      adc3=adc3, override=override):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_ADC10_STEP_CH",
                                                              "MA17_OVERRIDE_", "MA17_TRACE_"))}
                        environment.update(MA17_ADC_CH2=str(adc2),
                                           MA17_ADC_CH3=str(adc3), MA17_ADC_CH7="63")
                        if override:
                            environment["MA17_OVERRIDE_MOVC_AT"] = override
                        output = Path(directory) / firmware.stem / f"{adc2}_{adc3}_{override}"
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "15",
                             "--trace-movc", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment, timeout=25)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        reads = [row for row in report["movc_observation"]["reads"]
                                 if 0x74EE <= int(row["mapped"], 16) < 0x750C]
                        self.assertEqual({row["mapped"] for row in reads}, addresses)
                        self.assertEqual({row["dptr"] for row in reads}, {"74F8"})
                        if adc3 == 220:
                            self.assertTrue(any(row["acc"] == "0A" and
                                                row["mapped"] == "7502" for row in reads))
                            self.assertEqual(report["engine_ram_observation"]["4E"][-1]
                                             ["after"], "09")
                        self.assertEqual(report["engine_ram_observation"]["4F"][-1]
                                         ["after"], ram4f)
                        self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                         cc3)
                        self.assertEqual("[MOVC-OVERRIDE] PC=5333 mapped=7502" in
                                         (output / "emulator-trace.log").read_text(),
                                         override is not None)

    def test_p46_low_selects_third_coolant_curve_and_cell_reaches_cc3(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        with tempfile.TemporaryDirectory() as directory:
            for firmware, low_cc3, supplied_cc3 in ((REFERENCE, 516, 705),
                                                     (sun, 596, 820)):
                for low, supplied, expected_4f, expected_cc3 in (
                        (False, False, "08", 1495),
                        (True, False, "07", low_cc3),
                        (True, True, "25", supplied_cc3)):
                    with self.subTest(firmware=firmware.name, low=low,
                                      supplied=supplied):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_ADC10_STEP_CH",
                                                              "MA17_OVERRIDE_", "MA17_TRACE_"))
                                       and key != "MA17_P4_6_FORCE_LOW"}
                        environment.update(MA17_ADC_CH2="160", MA17_ADC_CH3="80",
                                           MA17_ADC_CH7="63")
                        if low:
                            environment["MA17_P4_6_FORCE_LOW"] = "1"
                        if supplied:
                            environment["MA17_OVERRIDE_MOVC_AT"] = "532F:7505:29"
                        output = Path(directory) / firmware.stem / f"{low}_{supplied}"
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "15",
                             "--trace-movc", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment, timeout=25)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertEqual(report["p4_6_force_low_experimental"], low)
                        reads = [row for row in report["movc_observation"]["reads"]
                                 if row["pc"] == "532F" and row["dptr"] == "7502"
                                 and row["mapped"] == "7505"]
                        self.assertEqual(bool(reads), low)
                        if low:
                            self.assertEqual(reads[0]["value"], "07")
                            self.assertGreater(reads[0]["count"], 500)
                        self.assertEqual(report["engine_ram_observation"]["4F"][-1]
                                         ["after"], expected_4f)
                        self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                         expected_cc3)
                        self.assertEqual("[MOVC-OVERRIDE] PC=532F mapped=7505" in
                                         (output / "emulator-trace.log").read_text(),
                                         supplied)

    def test_idle_fault_source_bits_reach_diagnostic_latch(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for tps0, tps6, expected_latch in ((40, 95, "0E"),
                                                (120, 180, "04")):
                with self.subTest(tps=(tps0, tps6)):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))
                                   and key != "MA17_P4_6_FORCE_LOW"}
                    environment.update(MA17_ADC_CH0=str(tps0),
                                       MA17_ADC_CH6=str(tps6),
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH7="63",
                                       MA17_TRACE_IDLE_FAULT="1")
                    output = Path(directory) / f"{tps0}_{tps6}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    sources = [line for line in lines
                               if line.startswith("[IDLE-FAULT-SOURCE]")]
                    latches = [line for line in lines
                               if line.startswith("[IDLE-FAULT-LATCH]")]
                    self.assertTrue(any("PC=316C" in line and "RAM27=00->04" in line
                                        for line in sources))
                    self.assertEqual(any("PC=2B42" in line for line in sources),
                                     expected_latch == "0E")
                    self.assertEqual(any("PC=2B49" in line for line in sources),
                                     expected_latch == "0E")
                    self.assertTrue(any("PC=41E5" in line and
                                        f"->{expected_latch}" in line for line in latches))

    def test_tps_derived_bit_zero_fault_needs_experimental_low_p46(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for low in (False, True):
                with self.subTest(p4_6_low=low):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="40", MA17_ADC_CH6="220",
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH7="63", MA17_TRACE_IDLE_FAULT="1")
                    if low:
                        environment["MA17_P4_6_FORCE_LOW"] = "1"
                    output = Path(directory) / ("low" if low else "high")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["p4_6_force_low_experimental"], low)
                    self.assertEqual(report["sensor_ram_observation"]["70"][-1]
                                     ["after"], "53")
                    self.assertEqual(report["sensor_ram_observation"]["70"][-1]
                                     ["source_pc"], "11C0")
                    pc_hits = (output / "pc-hits.txt").read_text().splitlines()
                    self.assertEqual("29D5" in pc_hits, low)
                    log = (output / "emulator-trace.log").read_text()
                    if low:
                        self.assertIn("PC=29D5 RAM27=08->09", log)
                        self.assertIn("PC=41E5 XRAM4E=00->01", log)
                    else:
                        self.assertIn("29F5", pc_hits)
                        self.assertIn("PC=41E5 XRAM4E=00->04", log)

    def test_idle_fault_xram_read_bits_select_two_error_flags(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for supplied, expected in (("0E", "04"), ("6E", "04"),
                                       ("AE", "06")):
                with self.subTest(supplied=supplied):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))
                                   and key != "MA17_P4_6_FORCE_LOW"}
                    environment.update(MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH7="63", MA17_TRACE_IDLE_FAULT="1",
                                       MA17_OVERRIDE_IDLE_FAULT_READ=supplied)
                    output = Path(directory) / supplied
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "1600000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    log = (output / "emulator-trace.log").read_text()
                    self.assertIn(f"stored=2E supplied={supplied}", log)
                    latches = [line for line in log.splitlines()
                               if line.startswith("[IDLE-FAULT-LATCH]")]
                    self.assertEqual(latches[-1].split("->")[1][:2], expected)
                    self.assertEqual("PC=2B42 RAM27=04->06" in log,
                                     supplied == "AE")
                    self.assertNotIn("PC=2B49 RAM27=06->0E", log)

    def test_idle_fault_7321_bound_blocks_error_path_when_raised(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                              "MA17_TRACE_"))
                       and key != "MA17_P4_6_FORCE_LOW"}
        environment.update(MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                           MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                           MA17_ADC_CH7="63", MA17_TRACE_IDLE_FAULT="1",
                           MA17_OVERRIDE_MOVC_AT="2A7D:7321:FF")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                 "--stop-ticks", "2400000", "--seconds", "30", "--trace-movc",
                 "--output-dir", str(output)],
                capture_output=True, text=True, env=environment,
                timeout=40, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((output / "execution.json").read_text())
            self.assertEqual(report["firmware_sha256"],
                             hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
            reads = [row for row in report["movc_observation"]["reads"]
                     if row["pc"] == "2A7D" and row["mapped"] == "7321"]
            self.assertEqual(len(reads), 1)
            self.assertEqual(reads[0]["value"], "14")
            self.assertGreater(reads[0]["count"], 100)
            log = (output / "emulator-trace.log").read_text()
            self.assertIn("[MOVC-OVERRIDE] PC=2A7D mapped=7321", log)
            self.assertNotIn("[IDLE-FAULT-GATE] tick=", log)
            self.assertNotIn("PC=2B42 RAM27=04->06", log)
            self.assertIn("PC=41E5 XRAM4E=00->04", log)

    def test_7331_movc_reload_changes_f826_without_cc3_inhibit(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        settings = {key: value for key, value in os.environ.items()
                    if not key.startswith("MA17_")}
        settings.update(MA17_TRACE_XRAM_ADDRESS="F826",
                        MA17_TRACE_CC3_DECISION="1",
                        MA17_TRACE_CC3_AFTER_TICK="1600000",
                        MA17_ADC10_CH0="720", MA17_ADC10_CH1="520",
                        MA17_ADC10_CH2="400", MA17_ADC10_CH3="16",
                        MA17_ADC10_CH4="360", MA17_ADC10_CH5="160",
                        MA17_ADC10_CH6="988", MA17_ADC10_CH7="252",
                        MA17_ADC10_STEP_CH0="1200000:160",
                        MA17_ADC10_STEP_CH6="1200000:380")
        first_inhibit = []
        with tempfile.TemporaryDirectory() as directory:
            for value, first_reload in ((None, "32"), ("01", "01")):
                with self.subTest(value=value):
                    environment = dict(settings)
                    if value is not None:
                        environment["MA17_OVERRIDE_MOVC_AT"] = f"2D0A:7331:{value}"
                    output = Path(directory) / (value or "original")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "3000",
                         "--stop-ticks", "3000000", "--seconds", "30",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "2D0A" and row["mapped"] == "7331"]
                    self.assertEqual(len(reads), 1)
                    self.assertEqual(reads[0]["value"], "32")
                    log = (output / "emulator-trace.log").read_text().splitlines()
                    writes = [line for line in log if line.startswith(
                        "[XRAM-ADDRESS-WRITE]") and "PC=2D15" in line]
                    self.assertTrue(writes)
                    self.assertIn(f"value=00->{first_reload}", writes[0])
                    states = [line for line in log if line.startswith(
                        "[CC3-DECISION]") and "PC=2054" in line and
                        int(line.split("flags26=")[1][:2], 16) & 0x80]
                    self.assertTrue(states)
                    first_inhibit.append(states[0].split("tick=")[1].split()[0])
        self.assertEqual(first_inhibit, ["2190344", "2190344"])

    def test_p43_level_is_copied_to_f8e2_status_bit_in_full_fiat_boot(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        settings = {key: value for key, value in os.environ.items()
                    if not key.startswith("MA17_")}
        settings.update(MA17_TRACE_XRAM_ADDRESS="F8E2",
                        MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                        MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                        MA17_ADC_CH7="63")
        reports = []
        with tempfile.TemporaryDirectory() as directory:
            for low, expected in ((False, ["00->57", "57->77"]),
                                  (True, ["00->53", "53->73"])):
                environment = dict(settings)
                if low:
                    environment["MA17_P4_3_FORCE_LOW"] = "1"
                output = Path(directory) / ("p43low" if low else "default")
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                     "--stop-ticks", "2400000", "--seconds", "30",
                     "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=40, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                writes = [line for line in (output / "emulator-trace.log")
                          .read_text().splitlines()
                          if line.startswith("[XRAM-ADDRESS-WRITE]")
                          and "PC=49C8 addr=F8E2" in line]
                self.assertEqual([line.split("value=")[1] for line in writes],
                                 expected)
                hits = (output / "pc-hits.txt").read_bytes()
                reports.append((report, hits))
        self.assertEqual(reports[0][1], reports[1][1])
        for key in ("output_latches", "cc3_observation", "pc_coverage"):
            self.assertEqual(reports[0][0][key], reports[1][0][key])

    def test_mode_flags_7375_are_read_by_three_fiat_consumers(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("MA17_")}
        environment.update(MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                           MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                           MA17_ADC_CH7="63")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                 "--stop-ticks", "2400000", "--seconds", "30",
                 "--trace-movc", "--output-dir", str(output)],
                capture_output=True, text=True, env=environment,
                timeout=40, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((output / "execution.json").read_text())
        self.assertEqual(report["firmware_sha256"],
                         hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
        reads = {row["pc"]: row for row in report["movc_observation"]["reads"]
                 if row["mapped"] == "7375"}
        for pc in ("210C", "233F", "36BB"):
            self.assertIn(pc, reads)
            self.assertEqual((reads[pc]["dptr"], reads[pc]["acc"],
                              reads[pc]["value"]), ("7300", "75", "09"))
            self.assertGreater(reads[pc]["count"], 0)

    def test_f8ef_and_upper_c9_stay_zero_after_fiat_tps_release(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("MA17_")}
        environment.update(MA17_TRACE_XRAM_ADDRESS="F8EF",
                           MA17_TRACE_UPPER_CA_CONSUMER="1",
                           MA17_ADC10_CH0="720", MA17_ADC10_CH1="520",
                           MA17_ADC10_CH2="400", MA17_ADC10_CH3="16",
                           MA17_ADC10_CH4="360", MA17_ADC10_CH5="160",
                           MA17_ADC10_CH6="988", MA17_ADC10_CH7="252",
                           MA17_ADC10_STEP_CH0="1200000:160",
                           MA17_ADC10_STEP_CH6="1200000:380")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--no-kline-inject", "--crank-immediate", "--rpm", "3000",
                 "--stop-ticks", "3000000", "--seconds", "30",
                 "--trace-movc", "--output-dir", str(output)],
                capture_output=True, text=True, env=environment,
                timeout=40, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((output / "execution.json").read_text())
            log = (output / "emulator-trace.log").read_text().splitlines()
            hits = set((output / "pc-hits.txt").read_text().splitlines())
        self.assertEqual(report["firmware_sha256"],
                         hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
        writes = [line.split("value=")[1] for line in log
                  if line.startswith("[XRAM-ADDRESS-WRITE]")
                  and "addr=F8EF" in line]
        self.assertEqual(writes, ["00->55", "55->AA", "AA->00"])
        for pc in ("3607", "360E", "2E3A"):
            self.assertNotIn(pc, hits)
        consumers = [line for line in log
                     if line.startswith("[UPPER-CA-CONSUMER]")
                     and "PC=39B2" in line]
        self.assertGreater(len(consumers), 200)
        self.assertTrue(all("UC9=00" in line for line in consumers))

    def test_f8ef_read_reaches_upper_c9_r2_and_p5_with_p46_low(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        settings = {key: value for key, value in os.environ.items()
                    if not key.startswith("MA17_")}
        settings.update(MA17_P4_6_FORCE_LOW="1",
                        MA17_TRACE_XRAM_ADDRESS="F8EF",
                        MA17_TRACE_XRAM_PC="361A",
                        MA17_TRACE_UPPER_85_86="1",
                        MA17_TRACE_UPPER_CA_CONSUMER="1",
                        MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                        MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                        MA17_ADC_CH7="63")
        reports = []
        with tempfile.TemporaryDirectory() as directory:
            for override in (False, True):
                environment = dict(settings)
                if override:
                    environment["MA17_OVERRIDE_XRAM_READ_AT"] = "361A:F8EF:00"
                output = Path(directory) / ("zero_read" if override else "original")
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--no-kline-inject", "--crank-immediate", "--rpm", "3000",
                     "--stop-ticks", "600000", "--seconds", "30",
                     "--trace-movc", "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=40, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                log = (output / "emulator-trace.log").read_text().splitlines()
                reads = [line for line in log if line.startswith(
                    "[XRAM-PC-READ] PC=361A addr=F8EF")]
                self.assertEqual(len(reads), 7)
                self.assertTrue(all("stored=06 P2=F8 XPAGE=F8" in line
                                    for line in reads))
                writes = [line.split("value=")[1] for line in log
                          if line.startswith("[XRAM-ADDRESS-WRITE]")
                          and "addr=F8EF" in line]
                self.assertEqual(writes, ["00->55", "55->AA", "AA->00",
                                          "00->14", "14->06", "06->00"])
                reads_7375 = [row for row in report["movc_observation"]["reads"]
                              if row["pc"] == "360E" and row["mapped"] == "7375"]
                self.assertEqual(len(reads_7375), 1)
                self.assertEqual(reads_7375[0]["count"], 7)
                c9_writes = [line for line in log if line.startswith(
                    "[UPPER-85-86-READER]") and "PC=3699" in line]
                c9_reads = [line for line in log if line.startswith(
                    "[UPPER-CA-CONSUMER]") and "PC=39B2" in line]
                results = [line for line in log if line.startswith(
                    "[UPPER-CA-CONSUMER]") and "PC=39F4" in line]
                self.assertEqual(sum(" A=3C " in line for line in c9_writes),
                                 0 if override else 7)
                self.assertEqual(sum(" UC9=3C " in line for line in c9_reads),
                                 0 if override else 7)
                self.assertEqual(sum(" A=9B " in line for line in results),
                                 0 if override else 7)
                reports.append(report)
        self.assertEqual(reports[0]["cc3_observation"]["cc3_pin_model_low_starts"],
                         reports[1]["cc3_observation"]["cc3_pin_model_low_starts"])
        for pin in ("P5.0", "P5.1"):
            self.assertEqual(reports[0]["output_latches"][pin]["low_starts"],
                             reports[1]["output_latches"][pin]["low_starts"])
            self.assertNotEqual(reports[0]["output_latches"][pin]
                                ["low_width_histogram"],
                                reports[1]["output_latches"][pin]
                                ["low_width_histogram"])

    def test_7310_movc_bound_changes_rpm_branch_and_cc3_inhibit(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        settings = {key: value for key, value in os.environ.items()
                    if not key.startswith("MA17_")}
        settings.update(MA17_TRACE_CC3_DECISION="1",
                        MA17_TRACE_CC3_AFTER_TICK="1600000",
                        MA17_ADC10_CH0="720", MA17_ADC10_CH1="520",
                        MA17_ADC10_CH2="400", MA17_ADC10_CH3="16",
                        MA17_ADC10_CH4="360", MA17_ADC10_CH5="160",
                        MA17_ADC10_CH6="988", MA17_ADC10_CH7="252",
                        MA17_ADC10_STEP_CH0="1200000:160",
                        MA17_ADC10_STEP_CH6="1200000:380")
        cases = ((1400, None, False, "38"),
                 (1400, "34", True, "38"),
                 (1500, None, True, "3C"),
                 (1500, "3C", False, "3C"))
        with tempfile.TemporaryDirectory() as directory:
            for rpm, override, inhibited, rpm_byte in cases:
                with self.subTest(rpm=rpm, override=override):
                    environment = dict(settings)
                    if override is not None:
                        environment["MA17_OVERRIDE_MOVC_AT"] = (
                            f"2C4B:7310:{override}")
                    output = Path(directory) / f"{rpm}-{override or 'original'}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         str(rpm), "--stop-ticks", "3000000", "--seconds",
                         "30", "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "2C4B" and row["mapped"] == "7310"]
                    self.assertEqual(len(reads), 1)
                    self.assertEqual(reads[0]["value"], "38")
                    log = (output / "emulator-trace.log").read_text().splitlines()
                    decisions = [line for line in log if line.startswith(
                        "[CC3-DECISION]") and "PC=2054" in line]
                    self.assertTrue(decisions)
                    self.assertIn(f"RAM47={rpm_byte}", decisions[-1])
                    active = [line for line in decisions if
                              int(line.split("flags26=")[1][:2], 16) & 0x80]
                    self.assertEqual(bool(active), inhibited)
                    edges = [int(line.split("tick=")[1].split()[0])
                             for line in log if line.startswith("[CC3-PIN]")]
                    self.assertTrue(edges)
                    self.assertEqual(any(tick > 2900000 for tick in edges),
                                     not inhibited)

    def test_7310_guard_depends_on_tps_state_at_fixed_rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        base = {key: value for key, value in os.environ.items()
                if not key.startswith("MA17_")}
        base.update(MA17_TRACE_CC3_DECISION="1",
                    MA17_TRACE_CC3_AFTER_TICK="0",
                    MA17_TRACE_TPS_AFTER_TICK="1100000",
                    MA17_ADC10_CH1="520", MA17_ADC10_CH2="400",
                    MA17_ADC10_CH3="16", MA17_ADC10_CH4="360",
                    MA17_ADC10_CH5="160", MA17_ADC10_CH7="252")
        cases = ((1400, True, False, False, "38"),
                 (1400, True, True, False, "38"),
                 (1500, True, False, True, "3C"),
                 (1500, False, False, False, "3C"),
                 (1500, False, True, False, "3C"),
                 (1600, False, False, False, "40"))
        with tempfile.TemporaryDirectory() as directory:
            for rpm, closed, p46_low, inhibited, rpm_byte in cases:
                with self.subTest(rpm=rpm, closed=closed, p46_low=p46_low):
                    environment = dict(base)
                    environment["MA17_ADC10_CH0"] = "160" if closed else "720"
                    environment["MA17_ADC10_CH6"] = "380" if closed else "988"
                    if p46_low:
                        environment["MA17_P4_6_FORCE_LOW"] = "1"
                    output = Path(directory) / f"{rpm}-{closed}-{p46_low}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         str(rpm), "--stop-ticks", "3000000", "--seconds",
                         "30", "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["rpm_observation"]
                                     ["ram47_changes"][-1]["after"], rpm_byte)
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "2C4B" and row["mapped"] == "7310"]
                    self.assertEqual(bool(reads), closed or p46_low)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    decisions = [line for line in lines
                                 if line.startswith("[CC3-DECISION]")]
                    self.assertTrue(decisions)
                    active = any(int(line.split("flags26=")[1][:2], 16) & 0x80
                                 for line in decisions if "PC=2054" in line)
                    self.assertEqual(active, inhibited)
                    edges = [int(line.split("tick=")[1].split()[0])
                             for line in lines if line.startswith("[CC3-PIN]")]
                    self.assertTrue(edges)
                    self.assertEqual(edges[-1] < 1200000, inhibited)
                    if rpm == 1500 and (closed or p46_low):
                        hits = set((output / "pc-hits.txt").read_text().splitlines())
                        self.assertIn("2C4B", hits)
                        self.assertEqual("2D04" in hits, closed)
                        if closed:
                            self.assertNotIn("11A8", hits)
                            self.assertIn("11D1", hits)
                            self.assertTrue(any(
                                "PC=11D1" in line and "A=1B" in line
                                for line in lines if line.startswith("[TPS-FLOW]")))
                            self.assertTrue(any(
                                "PC=2D04 CY=1" in line and
                                "RAM47=3C" in line and "R2=38" in line
                                for line in decisions))
                            self.assertTrue(any(
                                "PC=2D10 CY=1" in line and
                                "flags26=10" in line for line in decisions))
                        else:
                            self.assertIn("11A8", hits)
                            self.assertIn("11C0", hits)
                            self.assertTrue(any(
                                "PC=1175 R2=B4 R3=1A R4=F7" in line
                                for line in lines if line.startswith("[TPS-FLOW]")))
                            self.assertNotIn("2CD9", hits)
                            self.assertTrue(any(
                                "PC=2D0E CY=0" in line and
                                "RAM70=DF" in line and "R2=38" in line
                                for line in decisions))

    def test_tps_state_can_bypass_7310_before_ram70_comparison(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        base = {key: value for key, value in os.environ.items()
                if not key.startswith("MA17_")}
        base.update(MA17_ADC10_CH1="520", MA17_ADC10_CH2="400",
                    MA17_ADC10_CH3="16", MA17_ADC10_CH4="360",
                    MA17_ADC10_CH5="160", MA17_ADC10_CH7="252",
                    MA17_TRACE_CUTOFF_PATH="1",
                    MA17_TRACE_CC3_AFTER_TICK="1000000")
        with tempfile.TemporaryDirectory() as directory:
            for adc0, adc6, ram70, reaches in ((320, 580, "2C", True),
                                               (400, 680, "34", False)):
                with self.subTest(adc0=adc0, adc6=adc6):
                    environment = dict(base, MA17_ADC10_CH0=str(adc0),
                                       MA17_ADC10_CH6=str(adc6))
                    output = Path(directory) / str(adc0)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "1500", "--stop-ticks", "2000000", "--seconds",
                         "30", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    path = [line for line in lines
                            if line.startswith("[CUTOFF-PATH]")]
                    self.assertTrue(any("PC=2C3C" in line and
                                        f"RAM70={ram70}" in line
                                        for line in path))
                    self.assertEqual(any("PC=2C49" in line for line in path),
                                     reaches)
                    self.assertEqual(any("PC=2D04" in line for line in path),
                                     reaches)
                    self.assertEqual(any("PC=2C3C" in line and
                                         "F24=AA" in line and
                                         "F27=0E" in line for line in path),
                                     reaches)

    def test_ram6f_read_mediates_tps_pre_movc_gate(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        base = {key: value for key, value in os.environ.items()
                if not key.startswith("MA17_")}
        base.update(MA17_ADC10_CH1="520", MA17_ADC10_CH2="400",
                    MA17_ADC10_CH3="16", MA17_ADC10_CH4="360",
                    MA17_ADC10_CH5="160", MA17_ADC10_CH7="252",
                    MA17_TRACE_744E_BRANCH="1",
                    MA17_TRACE_CC3_DECISION="1",
                    MA17_TRACE_CC3_AFTER_TICK="1000000")
        cases = ((320, 580, "84", None, True),
                 (320, 580, "84", "9D", False),
                 (400, 680, "9D", None, False),
                 (400, 680, "9D", "84", True))
        with tempfile.TemporaryDirectory() as directory:
            for adc0, adc6, stored, supplied, gate in cases:
                with self.subTest(adc0=adc0, adc6=adc6, supplied=supplied):
                    environment = dict(base, MA17_ADC10_CH0=str(adc0),
                                       MA17_ADC10_CH6=str(adc6))
                    if supplied:
                        environment["MA17_OVERRIDE_IRAM_READ_AT"] = (
                            f"29A3:6F:{supplied}")
                    output = Path(directory) / f"{adc0}_{supplied or 'base'}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "1500", "--stop-ticks", "2000000", "--seconds",
                         "30", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["iram_read_override_at_hex"],
                                     f"29A3:6F:{supplied}" if supplied else None)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_low_starts"], 51 if gate else 93)
                    hits = set((output / "pc-hits.txt").read_text().splitlines())
                    for pc in ("2AF9", "2B42", "2C49", "2D04"):
                        self.assertEqual(pc in hits, gate, pc)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    branch = [line for line in lines
                              if line.startswith("[CURVE-744E-BRANCH]")]
                    self.assertTrue(any("PC=2A93" in line and
                                        f"R2={supplied or stored}" in line
                                        for line in branch))
                    decisions = [line for line in lines
                                 if line.startswith("[CC3-DECISION]") and
                                 "PC=2054" in line]
                    active = sum(bool(int(line.split("flags26=")[1][:2],
                                          16) & 0x80) for line in decisions)
                    self.assertEqual(active, 81 if gate else 0)

    def test_s88_ram6f_read_repeats_pre_movc_gate(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        firmware = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        gasoline, s88 = REFERENCE.read_bytes(), firmware.read_bytes()
        for start, end in ((0x11C4, 0x11D4), (0x299A, 0x29A8),
                           (0x2A78, 0x2AB4), (0x2AF9, 0x2B4F),
                           (0x2C3C, 0x2D16), (0x1F9B, 0x205C)):
            self.assertEqual(s88[start:end], gasoline[start:end])
        self.assertEqual(s88[0x7310], gasoline[0x7310])
        base = {key: value for key, value in os.environ.items()
                if not key.startswith("MA17_")}
        base.update(MA17_ADC10_CH1="520", MA17_ADC10_CH2="400",
                    MA17_ADC10_CH3="16", MA17_ADC10_CH4="360",
                    MA17_ADC10_CH5="160", MA17_ADC10_CH7="252",
                    MA17_TRACE_CC3_DECISION="1",
                    MA17_TRACE_CC3_AFTER_TICK="1000000")
        with tempfile.TemporaryDirectory() as directory:
            for adc0, adc6, supplied, gate in ((320, 580, None, True),
                                               (320, 580, "9D", False),
                                               (400, 680, None, False),
                                               (400, 680, "84", True)):
                with self.subTest(adc0=adc0, adc6=adc6, supplied=supplied):
                    environment = dict(base, MA17_ADC10_CH0=str(adc0),
                                       MA17_ADC10_CH6=str(adc6))
                    if supplied:
                        environment["MA17_OVERRIDE_IRAM_READ_AT"] = (
                            f"29A3:6F:{supplied}")
                    output = Path(directory) / f"{adc0}_{supplied or 'base'}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1500",
                         "--stop-ticks", "2000000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(s88).hexdigest())
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_low_starts"], 51 if gate else 93)
                    hits = set((output / "pc-hits.txt").read_text().splitlines())
                    for pc in ("2AF9", "2B42", "2C49", "2D04"):
                        self.assertEqual(pc in hits, gate, pc)
                    decisions = [line for line in
                                 (output / "emulator-trace.log").read_text().splitlines()
                                 if line.startswith("[CC3-DECISION]") and
                                 "PC=2054" in line]
                    self.assertEqual(sum(bool(int(line.split("flags26=")[1][:2],
                                                  16) & 0x80)
                                         for line in decisions), 81 if gate else 0)

    def test_ram70_read_at_2cd3_mediates_rpm_guard_but_not_persistence(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        base = {key: value for key, value in os.environ.items()
                if not key.startswith("MA17_")}
        base.update(MA17_TRACE_CC3_DECISION="1",
                    MA17_TRACE_CC3_AFTER_TICK="1000000",
                    MA17_ADC10_CH1="520", MA17_ADC10_CH2="400",
                    MA17_ADC10_CH3="16", MA17_ADC10_CH4="360",
                    MA17_ADC10_CH5="160", MA17_ADC10_CH7="252")
        cases = (("closed", None, 51, True, True),
                 ("closed", "DF", 143, False, False),
                 ("open_p46low", None, 143, False, False),
                 ("open_p46low", "1B", 139, True, True))
        with tempfile.TemporaryDirectory() as directory:
            for state, override, pulse_count, reaches_2d04, active in cases:
                with self.subTest(state=state, override=override):
                    environment = dict(base)
                    closed = state == "closed"
                    environment["MA17_ADC10_CH0"] = "160" if closed else "720"
                    environment["MA17_ADC10_CH6"] = "380" if closed else "988"
                    if not closed:
                        environment["MA17_P4_6_FORCE_LOW"] = "1"
                    if override:
                        environment["MA17_OVERRIDE_IRAM_READ_AT"] = (
                            f"2CD3:70:{override}")
                        environment["MA17_OVERRIDE_IRAM_READ_AFTER_TICK"] = (
                            "1100000")
                    output = Path(directory) / f"{state}-{override or 'base'}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "1500", "--stop-ticks", "3000000", "--seconds",
                         "30", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_low_starts"], pulse_count)
                    self.assertEqual(report["iram_read_override_at_hex"],
                                     f"2CD3:70:{override}" if override else None)
                    hits = set((output / "pc-hits.txt").read_text().splitlines())
                    self.assertEqual("2D04" in hits, reaches_2d04)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    overrides = [line for line in lines
                                 if line.startswith("[IRAM-READ-OVERRIDE]")]
                    self.assertEqual(bool(overrides), override is not None)
                    if override:
                        self.assertIn(f"supplied={override}", overrides[0])
                    decisions = [line for line in lines
                                 if line.startswith("[CC3-DECISION]") and
                                 "PC=2054" in line]
                    active_count = sum(bool(int(line.split("flags26=")[1][:2],
                                                16) & 0x80)
                                       for line in decisions)
                    self.assertEqual(bool(active_count), active)
                    if state == "open_p46low" and override:
                        self.assertEqual(active_count, 8)
                        self.assertTrue(any(
                            "PC=2D0E CY=0" in line and "flags26=90" in line
                            for line in lines if line.startswith("[CC3-DECISION]")
                            and int(line.split("tick=")[1].split()[0]) > 1186000))
                        self.assertTrue(any(
                            "PC=2054" in line and "flags26=00" in line
                            for line in decisions))
                        edges = [int(line.split("tick=")[1].split()[0])
                                 for line in lines if line.startswith("[CC3-PIN]")]
                        self.assertGreater(edges[-1], 2900000)

    def test_ram70_read_pair_controls_guard_persistence_with_p46_low(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        base = {key: value for key, value in os.environ.items()
                if not key.startswith("MA17_")}
        base.update(MA17_P4_6_FORCE_LOW="1", MA17_TRACE_IDLE_FAULT="1",
                    MA17_TRACE_CUTOFF_PATH="1",
                    MA17_TRACE_CC3_DECISION="1",
                    MA17_TRACE_CC3_AFTER_TICK="1000000",
                    MA17_ADC10_CH0="720", MA17_ADC10_CH1="520",
                    MA17_ADC10_CH2="400", MA17_ADC10_CH3="16",
                    MA17_ADC10_CH4="360", MA17_ADC10_CH5="160",
                    MA17_ADC10_CH6="988", MA17_ADC10_CH7="252")
        cases = (("base", None, 143, 0, True),
                 ("gate", "2CD3:70:1B", 139, 8, True),
                 ("fault", "29CE:70:1B", 143, 0, True),
                 ("both", "2CD3:70:1B,29CE:70:1B", 48, 185, False))
        with tempfile.TemporaryDirectory() as directory:
            for name, override, starts, active_count, late_edges in cases:
                with self.subTest(name=name):
                    environment = dict(base)
                    if override:
                        environment["MA17_OVERRIDE_IRAM_READ_AT"] = override
                        environment["MA17_OVERRIDE_IRAM_READ_AFTER_TICK"] = (
                            "1100000")
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "1500", "--stop-ticks", "3000000", "--seconds",
                         "30", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertTrue(report["cutoff_path_trace_enabled"])
                    self.assertEqual(report["iram_read_override_at_hex"],
                                     override)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_low_starts"], starts)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    decisions = [line for line in lines
                                 if line.startswith("[CC3-DECISION]") and
                                 "PC=2054" in line]
                    self.assertEqual(sum(bool(int(line.split("flags26=")[1][:2],
                                                  16) & 0x80)
                                         for line in decisions), active_count)
                    edges = [int(line.split("tick=")[1].split()[0])
                             for line in lines if line.startswith("[CC3-PIN]")]
                    self.assertEqual(edges[-1] > 2900000, late_edges)
                    if name == "gate":
                        self.assertTrue(any(
                            "PC=29D5 RAM27=08->09" in line
                            for line in lines if line.startswith(
                                "[IDLE-FAULT-SOURCE]")))
                        self.assertTrue(any(
                            "PC=2C24" in line and "F27=09" in line
                            for line in lines if line.startswith("[CUTOFF-PATH]")))
                    if name == "both":
                        self.assertTrue(any(
                            "PC=2BFD" in line and "F27=08" in line and
                            "F26=90" in line for line in lines
                            if line.startswith("[CUTOFF-PATH]")))
                        self.assertFalse(any(
                            "PC=29D5" in line for line in lines
                            if line.startswith("[IDLE-FAULT-SOURCE]")))

    def test_s88_ram70_read_pair_repeats_guard_interaction(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        firmware = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        base = {key: value for key, value in os.environ.items()
                if not key.startswith("MA17_")}
        base.update(MA17_P4_6_FORCE_LOW="1", MA17_TRACE_IDLE_FAULT="1",
                    MA17_TRACE_CC3_DECISION="1",
                    MA17_TRACE_CC3_AFTER_TICK="1000000",
                    MA17_ADC10_CH0="720", MA17_ADC10_CH1="520",
                    MA17_ADC10_CH2="400", MA17_ADC10_CH3="16",
                    MA17_ADC10_CH4="360", MA17_ADC10_CH5="160",
                    MA17_ADC10_CH6="988", MA17_ADC10_CH7="252")
        cases = (("base", None, 143, 0, True),
                 ("gate", "2CD3:70:1B", 139, 8, True),
                 ("fault", "29CE:70:1B", 143, 0, True),
                 ("both", "2CD3:70:1B,29CE:70:1B", 48, 186, False))
        with tempfile.TemporaryDirectory() as directory:
            for name, override, starts, active_count, late_edges in cases:
                with self.subTest(name=name):
                    environment = dict(base)
                    if override:
                        environment["MA17_OVERRIDE_IRAM_READ_AT"] = override
                        environment["MA17_OVERRIDE_IRAM_READ_AFTER_TICK"] = (
                            "1100000")
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1500",
                         "--stop-ticks", "3000000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertEqual(report["iram_read_override_at_hex"],
                                     override)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_low_starts"], starts)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    decisions = [line for line in lines
                                 if line.startswith("[CC3-DECISION]") and
                                 "PC=2054" in line]
                    self.assertEqual(sum(bool(int(line.split("flags26=")[1][:2],
                                                  16) & 0x80)
                                         for line in decisions), active_count)
                    edges = [int(line.split("tick=")[1].split()[0])
                             for line in lines if line.startswith("[CC3-PIN]")]
                    self.assertEqual(edges[-1] > 2900000, late_edges)
                    bit_zero_set = any("PC=29D5 RAM27=08->09" in line
                                       for line in lines if line.startswith(
                                           "[IDLE-FAULT-SOURCE]"))
                    self.assertEqual(bit_zero_set, name in ("base", "gate"))

    def test_s88_7310_bound_has_same_branch_response(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        firmware = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        settings = {key: value for key, value in os.environ.items()
                    if not key.startswith("MA17_")}
        settings.update(MA17_TRACE_CC3_DECISION="1",
                        MA17_TRACE_CC3_AFTER_TICK="1600000",
                        MA17_ADC10_CH0="720", MA17_ADC10_CH1="520",
                        MA17_ADC10_CH2="400", MA17_ADC10_CH3="16",
                        MA17_ADC10_CH4="360", MA17_ADC10_CH5="160",
                        MA17_ADC10_CH6="988", MA17_ADC10_CH7="252",
                        MA17_ADC10_STEP_CH0="1200000:160",
                        MA17_ADC10_STEP_CH6="1200000:380")
        with tempfile.TemporaryDirectory() as directory:
            for rpm, override, inhibited in ((1400, None, False),
                                             (1400, "34", True),
                                             (1500, None, True),
                                             (1500, "3C", False)):
                with self.subTest(rpm=rpm, override=override):
                    environment = dict(settings)
                    if override is not None:
                        environment["MA17_OVERRIDE_MOVC_AT"] = (
                            f"2C4B:7310:{override}")
                    output = Path(directory) / f"{rpm}-{override or 'original'}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", str(rpm),
                         "--stop-ticks", "3000000", "--seconds", "30",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "2C4B" and row["mapped"] == "7310"]
                    self.assertEqual(len(reads), 1)
                    self.assertEqual(reads[0]["value"], "38")
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    active = [line for line in lines if line.startswith(
                        "[CC3-DECISION]") and "PC=2054" in line and
                        int(line.split("flags26=")[1][:2], 16) & 0x80]
                    self.assertEqual(bool(active), inhibited)
                    edges = [int(line.split("tick=")[1].split()[0])
                             for line in lines if line.startswith("[CC3-PIN]")]
                    self.assertTrue(edges)
                    self.assertEqual(any(tick > 2900000 for tick in edges),
                                     not inhibited)

    def test_experimental_p46_low_changes_idle_fault_source_path(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for force_low, expected_latch in ((False, "0E"), (True, "08")):
                with self.subTest(force_low=force_low):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))
                                   and key != "MA17_P4_6_FORCE_LOW"}
                    environment.update(MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH7="63", MA17_TRACE_IDLE_FAULT="1")
                    if force_low:
                        environment["MA17_P4_6_FORCE_LOW"] = "1"
                    output = Path(directory) / str(force_low)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "1600000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["p4_6_force_low_experimental"], force_low)
                    log = (output / "emulator-trace.log").read_text()
                    latches = [line for line in log.splitlines()
                               if line.startswith("[IDLE-FAULT-LATCH]")]
                    self.assertEqual(latches[-1].split("->")[1][:2], expected_latch)
                    self.assertEqual("PC=2B38" in log, not force_low)
                    self.assertEqual("PC=2C0C" in log, force_low)
                    self.assertIn("PC=0C85 addr=F847 value=00->80", log)
                    self.assertIn("[IDLE-FAULT-STARTUP] PC=0CB7 addr=F847 value=80", log)
                    self.assertIn("PC=0CAF addr=F83B value=00->32", log)
                    if force_low:
                        self.assertIn("PC=2C1B addr=F83B value=01->00", log)
                        self.assertIn("PC=2D56 addr=F847 value=C4->C6", log)
                        self.assertIn("PC=2C0C RAM27=00->08", log)
                    else:
                        self.assertIn("PC=2D56 addr=F847 value=80->C7", log)

    def test_idle_position_equal_writes_are_visible_with_p47_stimulus(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for force_low in (False, True):
                with self.subTest(p4_7_force_low=force_low):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                                       MA17_ADC_CH2="40", MA17_ADC_CH3="40",
                                       MA17_ADC_CH5="40", MA17_ADC_CH7="63",
                                       MA17_TRACE_IDLE_POSITION_ALL="1")
                    if force_low:
                        environment["MA17_P4_7_FORCE_LOW"] = "1"
                    output = Path(directory) / str(force_low)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "1200000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["p4_7_force_low_experimental"], force_low)
                    writes = [line for line in
                              (output / "emulator-trace.log").read_text().splitlines()
                              if line.startswith("[IDLE-XRAM-ALL]")]
                    repeated = [line for line in writes
                                if "PC=2494 addr=F83D value=07->07" in line]
                    self.assertGreater(len(repeated), 20)
                    self.assertEqual(len(writes), len(repeated) + 4)

    def test_idle_position_gate_has_multiple_active_guards_at_adc3_four(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                              "MA17_TRACE_", "MA17_P4_"))}
        environment.update(MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                           MA17_ADC_CH2="40", MA17_ADC_CH3="4",
                           MA17_ADC_CH5="40", MA17_ADC_CH7="63",
                           MA17_TRACE_IDLE_POSITION_GATE="1")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                 "--stop-ticks", "1200000", "--seconds", "30",
                 "--output-dir", str(output)],
                capture_output=True, text=True, env=environment,
                timeout=40, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((output / "execution.json").read_text())
            self.assertEqual(report["firmware_sha256"],
                             hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
            lines = [line for line in
                     (output / "emulator-trace.log").read_text().splitlines()
                     if line.startswith("[IDLE-POSITION-GATE]")]
            self.assertGreater(len(lines), 20)
            settled = [line for line in lines if "RAM63=04" in line and
                       "RAM47=28" in line]
            self.assertTrue(settled)
            for line in settled:
                self.assertIn("CY=1", line)
                flags = dict(re.findall(r"(F20|F24|F2D)=([0-9A-F]{2})", line))
                self.assertEqual(int(flags["F20"], 16) & 0x08, 0x08)
                self.assertEqual(int(flags["F24"], 16) & 0x10, 0)
                self.assertEqual(int(flags["F2D"], 16) & 0x10, 0)
            pc_hits = (output / "pc-hits.txt").read_text().splitlines()
            self.assertNotIn("23CE", pc_hits)
            self.assertNotIn("23F4", pc_hits)

    def test_79b0_79ba_movc_cells_independently_write_upper_85_86(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for donor in (None, "85", "86"):
                with self.subTest(donor=donor):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "120", "MA17_ADC_CH1": "130",
                        "MA17_ADC_CH2": "100", "MA17_ADC_CH3": "4",
                        "MA17_ADC_CH4": "90", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_UPPER_85_86": "1"})
                    if donor:
                        address = "79B0" if donor == "85" else "79BA"
                        environment["MA17_OVERRIDE_MOVC_AT"] = (
                            f"532F:{address}:40")
                    output = Path(directory) / (donor or "native")
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(REFERENCE), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--trace-movc", "--stop-ticks", "120000",
                         "--seconds", "10", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=20, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertTrue(report["upper_85_86_trace_enabled"])
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "532F" and
                             row["mapped"] in ("79B0", "79BA")]
                    self.assertEqual({row["mapped"] for row in reads},
                                     {"79B0", "79BA"})
                    self.assertTrue(all(row["value"] == "FF" and
                                        row["count"] >= 30 for row in reads))
                    rows = re.findall(r"\[UPPER-85-86\].*",
                                      (output / "emulator-trace.log").read_text())
                    for address in ("85", "86"):
                        selected = [row for row in rows
                                    if f"addr={address}" in row]
                        self.assertGreaterEqual(len(selected), 30)
                        expected = "40" if donor == address else "FF"
                        self.assertTrue(all(f"supplied={expected}" in row
                                            for row in selected))

    def test_74e4_first_cell_reaches_ram49_and_scaled_r2_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for donor, expected49, expected_r2 in (
                    (False, "73", "2F"), (True, "40", "25")):
                with self.subTest(donor=donor):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "120", "MA17_ADC_CH1": "130",
                        "MA17_ADC_CH2": "100", "MA17_ADC_CH3": "4",
                        "MA17_ADC_CH4": "90", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_129D_PATH": "1",
                        "MA17_TRACE_RAM4D_PATH": "1"})
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_AT"] = "12BD:74E4:40"
                    output = Path(directory) / ("donor" if donor else "native")
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(REFERENCE), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000", "--trace-movc",
                         "--stop-ticks", "120000", "--seconds", "10",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=20, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "12BD" and row["mapped"] == "74E4"]
                    self.assertEqual([(row["value"], row["count"])
                                      for row in reads], [("73", 8)])
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    path = [dict(re.findall(r"(\w+)=(\w+)", line))
                            for line in lines if line.startswith("[129D-PATH]")
                            and "PC=12C0" in line]
                    self.assertEqual(len(path), 8)
                    self.assertEqual({row["RAM49"] for row in path}, {expected49})
                    scaled = [dict(re.findall(r"(\w+)=(\w+)", line))
                              for line in lines if line.startswith("[RAM4D-PATH]")
                              and "PC=233B" in line and "RAM4D=19" in line]
                    self.assertEqual(len(scaled), 6)
                    self.assertEqual({row["R2"] for row in scaled}, {expected_r2})

    def test_7ae0_constant_table_reaches_cc3_through_f87f(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (("native", False, False, "04", "77", 1228, 4900),
                 ("donor", True, False, "03", "66", 1211, 4832),
                 ("native_read_ff", False, True, "04", "77", 1228, 4900),
                 ("donor_rescue", True, True, "04", "77", 1228, 4900))
        with tempfile.TemporaryDirectory() as directory:
            for name, donor, rescue, ram4f, ram5a, schedule, width in cases:
                with self.subTest(name=name):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC10_CH2": "400", "MA17_ADC10_CH3": "160",
                        "MA17_ADC10_STEP_CH3": "800000:204",
                        "MA17_ADC_CH7": "63", "MA17_TRACE_XRAM_F87F": "1"})
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_AT"] = "532F:7AE0:80"
                    if rescue:
                        environment["MA17_OVERRIDE_XRAM_READ_AT"] = (
                            "480D:F87F:FF")
                    output = Path(directory) / name
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(REFERENCE), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000", "--trace-movc",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertTrue(report["xram_f87f_trace_enabled"])
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "532F" and row["mapped"] == "7AE0"]
                    self.assertTrue(reads and reads[0]["count"] > 400)
                    self.assertEqual({row["value"] for row in reads}, {"FF"})
                    self.assertEqual(report["engine_ram_observation"]["4F"][-1]
                                     ["after"], ram4f)
                    self.assertEqual(report["engine_ram_observation"]["5A"][-1]
                                     ["after"], ram5a)
                    self.assertEqual(report["cc3_observation"]
                                     ["iram14_15_median"], schedule)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     width)
                    log = (output / "emulator-trace.log").read_text()
                    stored = re.findall(r"\[F87F-TABLE-READ\] "
                                        r"PC=480D stored=([0-9A-F]{2})", log)
                    self.assertEqual(len(stored), 512)
                    self.assertEqual(set(stored),
                                     {"FF", "A0", "80"} if donor else {"FF"})
                    self.assertEqual("[XRAM-READ-OVERRIDE] PC=480D" in log,
                                     rescue)

    def test_forced_7bbe_7c36_donors_reach_p5_through_ram69_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donors = {
            "A": VARIANTS / "tipo 1.6 alcool27c256.bin",
            "S88": VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"}
        cases = (
            ("1", None, None, "66", 5868.0, 5880.5),
            ("1", "A", None, "9A", 5908.0, 5908.0),
            ("1", "S88", None, "6E", 5885.0, 5884.0),
            ("1", None, "9A", "66", 5908.0, 5908.0),
            ("1", "A", "66", "9A", 5868.0, 5879.0),
            ("2", None, None, "66", 5868.0, 5880.0),
            ("2", "S88", None, "6E", 5885.0, 5884.0))
        with tempfile.TemporaryDirectory() as directory:
            for mode, donor, ram69, final69, p50, p51 in cases:
                with self.subTest(mode=mode, donor=donor, ram69=ram69):
                    base = "7BBE" if mode == "1" else "7C36"
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH1": "130",
                        "MA17_ADC_CH2": "100", "MA17_ADC_CH3": "20",
                        "MA17_ADC_CH4": "90", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                        "MA17_OVERRIDE_RAM57": mode})
                    if donor:
                        environment.update({
                            "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(donors[donor]),
                            "MA17_OVERRIDE_MOVC_MATRIX_BASE": base})
                    if ram69:
                        environment["MA17_OVERRIDE_RAM69"] = ram69
                    output = Path(directory) / f"{mode}-{donor}-{ram69}"
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(REFERENCE), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000", "--trace-movc",
                         "--stop-ticks", "2400000", "--seconds", "25",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["ram57_override_hex"], mode)
                    self.assertEqual(report["movc_matrix_size"],
                                     120 if donor else None)
                    reads = sum(row["count"] for row in
                                report["movc_observation"]["reads"]
                                if int(base, 16) <= int(row["mapped"], 16)
                                < int(base, 16) + 120)
                    self.assertEqual(reads, 650)
                    self.assertEqual(report["engine_ram_observation"]["69"][-1]
                                     ["after"], final69)
                    for pin, expected in (("P5.0", p50), ("P5.1", p51)):
                        self.assertEqual(report["output_latches"][pin]
                                         ["median_low_width_ticks"], expected)
                    self.assertEqual("[RAM69-OVERRIDE]" in
                                     (output / "emulator-trace.log").read_text(),
                                     ram69 is not None)

    @unittest.skipUnless(os.environ.get("MA17_RUN_SLOW") == "1",
                         "set MA17_RUN_SLOW=1 for the 12.3M-tick idle step")
    def test_idle_position_r4_change_steps_original_rom_in_both_directions(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for supplied, expected in (("05", "06"), ("09", "08")):
                with self.subTest(r4=supplied):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="120", MA17_ADC_CH6="180",
                                       MA17_ADC_CH3="4", MA17_ADC_CH5="40",
                                       MA17_ADC_CH7="63",
                                       MA17_P4_6_LOW_FROM_TICK="12200000",
                                       MA17_OVERRIDE_IDLE_POSITION_R4=supplied,
                                       MA17_TRACE_IDLE_POSITION_GATE="1",
                                       MA17_TRACE_IDLE_POSITION_ALL="1")
                    output = Path(directory) / supplied
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "12300000", "--seconds", "60",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=75, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["p4_6_low_from_tick_experimental"],
                                     12200000)
                    self.assertEqual(report["idle_position_r4_override_hex"],
                                     supplied)
                    log = (output / "emulator-trace.log").read_text()
                    self.assertIn("PC=23AF CY=0", log)
                    self.assertIn(f"PC=23B1 original=07 supplied={supplied}", log)
                    self.assertIn(f"PC=2494 addr=F83D value=07->{expected}", log)

    def test_ram3d_selector_state_differs_between_adc3_stimuli(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                for adc3 in (4, 80):
                    with self.subTest(firmware=firmware.name, adc3=adc3):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                                  "MA17_ADC10_CH",
                                                                  "MA17_ADC10_STEP_CH",
                                                                  "MA17_OVERRIDE_",
                                                                  "MA17_TRACE_"))
                                       and key != "MA17_P4_6_FORCE_LOW"}
                        environment.update(MA17_ADC_CH3=str(adc3),
                                           MA17_ADC_CH5="40", MA17_ADC_CH7="63",
                                           MA17_TRACE_LAMBDA="1")
                        output = Path(directory) / firmware.stem / str(adc3)
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "1600000", "--seconds", "15",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=25)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        states = set()
                        events = []
                        for line in (output / "emulator-trace.log").read_text().splitlines():
                            if "[LAMBDA-GATE]" not in line or "PC=19B6" not in line:
                                if "[LAMBDA-GATE]" in line:
                                    events.append(line)
                                continue
                            events.append(line)
                            match = re.search(r"RAM3D=([0-9A-F]{2}).*flags2F=([0-9A-F]{2})", line)
                            self.assertIsNotNone(match)
                            states.add((int(match[1], 16), bool(int(match[2], 16) & 0x20)))
                        self.assertIn((1, False), states)
                        if adc3 == 4:
                            self.assertIn((0x4B, True), states)
                            read = next(i for i, line in enumerate(events)
                                        if "PC=1870" in line and "A=4B" in line
                                        and "RAM3D=01" in line and "DPTR=7200" in line)
                            guarded = next(i for i, line in enumerate(events)
                                           if i > read and "PC=1889" in line
                                           and "A=4B" in line and "RAM3D=01" in line
                                           and int(re.search(r"flags2C=([0-9A-F]{2})", line)[1], 16) & 0x10)
                            before = next(i for i, line in enumerate(events)
                                          if i > guarded and "PC=19D9" in line
                                          and "RAM3D=4B" in line
                                          and not int(re.search(r"flags2F=([0-9A-F]{2})", line)[1], 16) & 0x20)
                            after = next(i for i, line in enumerate(events)
                                         if i > before and "PC=19E1" in line
                                         and "RAM3D=4B" in line
                                         and int(re.search(r"flags2F=([0-9A-F]{2})", line)[1], 16) & 0x20)
                            self.assertLess(read, guarded)
                            self.assertLess(guarded, before)
                            self.assertLess(before, after)
                        else:
                            self.assertEqual(states, {(1, False)})

    def test_7221_movc_reload_controls_750c_curve_selection(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                counts = {}
                for supplied in (False, True):
                    with self.subTest(firmware=firmware.name, supplied=supplied):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                                  "MA17_ADC10_CH",
                                                                  "MA17_ADC10_STEP_CH",
                                                                  "MA17_OVERRIDE_",
                                                                  "MA17_TRACE_"))
                                       and key != "MA17_P4_6_FORCE_LOW"}
                        environment.update(MA17_ADC_CH3="4", MA17_ADC_CH5="40",
                                           MA17_ADC_CH7="63", MA17_TRACE_LAMBDA="1")
                        if supplied:
                            environment["MA17_OVERRIDE_MOVC_AT"] = "186F:7221:01"
                        output = Path(directory) / firmware.stem / str(supplied)
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "1600000", "--seconds", "15",
                             "--trace-movc", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=25)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        rows = report["movc_observation"]["reads"]
                        source = [row for row in rows if row["pc"] == "186F"
                                  and row["mapped"] == "7221"]
                        self.assertEqual(len(source), 1)
                        self.assertEqual((source[0]["dptr"], source[0]["acc"],
                                          source[0]["value"]), ("7200", "21", "4B"))
                        self.assertGreater(source[0]["count"], 30)
                        counts[supplied] = {base: sum(row["count"] for row in rows
                                                       if row["pc"] == "532F"
                                                       and row["dptr"] == base)
                                            for base in ("750C", "7520")}
                        log = (output / "emulator-trace.log").read_text()
                        self.assertEqual("[MOVC-OVERRIDE] PC=186F mapped=7221 " in log,
                                         supplied)
                self.assertGreater(counts[False]["750C"], 0)
                self.assertEqual(counts[True]["750C"], 0)
                self.assertLessEqual(abs(counts[False]["750C"] +
                                         counts[False]["7520"] -
                                         counts[True]["7520"]), 1)

    def test_7227_bound_controls_ram3d_reload_and_750c_selection(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                for supplied in (False, True):
                    with self.subTest(firmware=firmware.name, supplied=supplied):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                                  "MA17_ADC10_CH",
                                                                  "MA17_ADC10_STEP_CH",
                                                                  "MA17_OVERRIDE_",
                                                                  "MA17_TRACE_"))
                                       and key != "MA17_P4_6_FORCE_LOW"}
                        environment.update(MA17_ADC_CH3="4", MA17_ADC_CH5="40",
                                           MA17_ADC_CH7="63", MA17_TRACE_LAMBDA="1")
                        if supplied:
                            environment["MA17_OVERRIDE_MOVC_AT"] = "17D5:7227:00"
                        output = Path(directory) / firmware.stem / str(supplied)
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "1600000", "--seconds", "15",
                             "--trace-movc", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=25)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        rows = report["movc_observation"]["reads"]
                        bound = [row for row in rows if row["pc"] == "17D5"
                                 and row["mapped"] == "7227"]
                        self.assertEqual(len(bound), 1)
                        self.assertEqual(bound[0]["value"], "2C")
                        rpm_bound = [row for row in rows if row["pc"] == "17E1"
                                     and row["mapped"] == "7226"]
                        self.assertEqual(bool(rpm_bound), supplied)
                        if supplied:
                            self.assertEqual(rpm_bound[0]["value"], "44")
                        reads_750c = sum(row["count"] for row in rows
                                         if row["pc"] == "532F"
                                         and row["dptr"] == "750C")
                        self.assertEqual(reads_750c > 0, not supplied)
                        log = (output / "emulator-trace.log").read_text()
                        self.assertEqual("[MOVC-OVERRIDE] PC=17D5 mapped=7227 " in log,
                                         supplied)
                        self.assertEqual("PC=186D" in log, not supplied)
                        late = [line for line in log.splitlines()
                                if "[LAMBDA-GATE]" in line and "PC=19B6" in line]
                        self.assertEqual(len(late), 152)
                        self.assertEqual(any("RAM3D=4B" in line for line in late),
                                         not supplied)

    @unittest.skipUnless(os.environ.get("MA17_RUN_SLOW") == "1",
                         "set MA17_RUN_SLOW=1 for the 12M-tick ADC3 boundary")
    def test_7227_boundary_controls_late_lambda_reload(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((44, None, True, "01"), (44, "2B", False, "00"),
                 (45, None, False, "00"), (45, "2D", True, "01"))
        with tempfile.TemporaryDirectory() as directory:
            for adc3, limit, enabled, expected_b in cases:
                with self.subTest(adc3=adc3, limit=limit):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))
                                   and key != "MA17_P4_6_FORCE_LOW"}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH3": str(adc3), "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH7": "63", "MA17_TRACE_LAMBDA": "1"})
                    if limit:
                        environment["MA17_OVERRIDE_MOVC_AT"] = f"17D5:7227:{limit}"
                    output = Path(directory) / f"{adc3}_{limit}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "12000000", "--seconds", "75",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=90, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["stop_ticks_observed"], 12000000)
                    self.assertEqual(report["movc_override_at_hex"],
                                     f"17D5:7227:{limit}" if limit else None)
                    reads = report["movc_observation"]["reads"]
                    bound = [row for row in reads if row["pc"] == "17D5"
                             and row["mapped"] == "7227"]
                    self.assertEqual(len(bound), 1)
                    self.assertEqual(bound[0]["value"], "2C")
                    reloads = sum(row["count"] for row in reads
                                  if row["mapped"] == "7221")
                    self.assertEqual(reloads > 0, enabled)
                    gates = [line for line in (output / "emulator-trace.log")
                             .read_text().splitlines()
                             if line.startswith("[LAMBDA-GATE]")]
                    second_guard = [line for line in gates if "PC=17E8" in line]
                    self.assertGreater(len(second_guard), 100)
                    self.assertEqual({line.split(" B=")[1][:2]
                                      for line in second_guard}, {expected_b})
                    self.assertEqual(any("PC=186D" in line for line in gates),
                                     enabled)

    def test_752a_donor_reaches_cc3_on_natural_tps_release(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor_rom = VARIANTS / "tipo 1.6 alcool27c256.bin"
        for firmware in (REFERENCE, donor_rom):
            self.assertEqual(int.from_bytes(firmware.read_bytes()[0x707C:0x707E],
                                            "big"), 0x752A)
        with tempfile.TemporaryDirectory() as directory:
            for donor, ram7b, final_b, zero_entries, pulses, entry107 in (
                    ("control", "73", "0E", 2, 127, "00CA"),
                    ("cell752b", "93", "12", 12, 117, "0000"),
                    ("cell752c", "76", "0E", 4, 125, "0000"),
                    ("curve", "95", "12", 12, 117, "0000")):
                with self.subTest(donor=donor):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update(
                        MA17_ADC_CH0="180", MA17_ADC_CH1="130",
                        MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                        MA17_ADC_CH4="90", MA17_ADC_CH5="110",
                        MA17_ADC_CH6="247", MA17_ADC_CH7="63",
                        MA17_ADC10_STEP_CH0="3274600:160",
                        MA17_ADC10_STEP_CH6="3274600:380",
                        MA17_TRACE_78XX_PATH="1")
                    if donor == "curve":
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="752A",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor_rom))
                    elif donor == "cell752b":
                        environment["MA17_OVERRIDE_MOVC_AT"] = "532F:752B:95"
                    elif donor == "cell752c":
                        environment["MA17_OVERRIDE_MOVC_AT"] = "5333:752C:9C"
                    output = Path(directory) / str(donor)
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "4000000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_base_hex"],
                                     "752A" if donor == "curve" else None)
                    self.assertEqual(report["engine_ram_observation"]["7B"][-1]
                                     ["after"], ram7b)
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["dptr"] == "752A"]
                    read_count = 797 if donor == "cell752b" else 798
                    self.assertEqual({(row["address"], row["count"])
                                      for row in reads},
                                     {("752B", read_count),
                                      ("752C", read_count)})
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    consumers = [line for line in lines
                                 if line.startswith("[78XX-CONSUMER]")
                                 and "PC=1CB7" in line]
                    self.assertEqual(len(consumers), 386)
                    self.assertEqual(sum("RAM7A=00" not in line
                                         for line in consumers), 69)
                    self.assertIn(f"RAM7A=8C RAM7B={ram7b}", consumers[-1])
                    final = [line for line in lines
                             if line.startswith("[78XX-CONSUMER]")
                             and "PC=1CDF" in line]
                    self.assertIn(f"B={final_b}", final[-1])
                    entries = [line for line in lines
                               if line.startswith("[CC3-ENTRY]")]
                    self.assertEqual(len(entries), 129)
                    self.assertEqual(sum("IRAM14_15=0000" in line
                                         for line in entries), zero_entries)
                    self.assertIn(f"IRAM14_15={entry107}", entries[107])
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_low_starts"], pulses)

    def test_752a_donor_repeats_on_s88_tps_release(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        donor_rom = VARIANTS / "tipo 1.6 alcool27c256.bin"
        with tempfile.TemporaryDirectory() as directory:
            for donor, ram7b, final_b, zeros, pulses in (
                    (False, "73", "0E", 4, 125),
                    (True, "95", "12", 12, 117)):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment.update(
                    MA17_ADC_CH0="180", MA17_ADC_CH1="130",
                    MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                    MA17_ADC_CH4="90", MA17_ADC_CH5="110",
                    MA17_ADC_CH6="247", MA17_ADC_CH7="63",
                    MA17_ADC10_STEP_CH0="3274600:160",
                    MA17_ADC10_STEP_CH6="3274600:380",
                    MA17_TRACE_78XX_PATH="1")
                if donor:
                    environment.update(
                        MA17_OVERRIDE_MOVC_MATRIX_BASE="752A",
                        MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor_rom))
                output = Path(directory) / str(donor)
                run = subprocess.run(
                    [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                     "--firmware", str(sun), "--trace-movc",
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                     "--stop-ticks", "4000000", "--seconds", "30",
                     "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=35, check=False)
                self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(sun.read_bytes()).hexdigest())
                self.assertEqual(report["engine_ram_observation"]["7B"][-1]
                                 ["after"], ram7b)
                lines = (output / "emulator-trace.log").read_text().splitlines()
                consumers = [line for line in lines
                             if line.startswith("[78XX-CONSUMER]")
                             and "PC=1CB7" in line]
                self.assertEqual(sum("RAM7A=00" not in line
                                     for line in consumers), 69)
                self.assertIn(f"RAM7A=8C RAM7B={ram7b}", consumers[-1])
                final = [line for line in lines
                         if line.startswith("[78XX-CONSUMER]")
                         and "PC=1CDF" in line]
                self.assertIn(f"B={final_b}", final[-1])
                entries = [line for line in lines
                           if line.startswith("[CC3-ENTRY]")]
                self.assertEqual(sum("IRAM14_15=0000" in line
                                     for line in entries), zeros)
                self.assertEqual(report["cc3_observation"]
                                 ["cc3_pin_model_low_starts"], pulses)

    def test_750c_curve_natural_read_changes_iram79_without_cc3_effect(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        alcohol = VARIANTS / "tipo 1.6 alcool27c256.bin"
        donor_cell = alcohol.read_bytes()[0x750C]
        self.assertEqual(donor_cell, 0x75)
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                controls = {}
                for supplied in (False, True):
                    with self.subTest(firmware=firmware.name, supplied=supplied):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_ADC10_STEP_CH",
                                                              "MA17_OVERRIDE_", "MA17_TRACE_"))
                                       and key != "MA17_P4_6_FORCE_LOW"}
                        environment.update(MA17_ADC_CH3="4", MA17_ADC_CH5="40",
                                           MA17_ADC_CH7="63")
                        if supplied:
                            environment["MA17_OVERRIDE_MOVC_AT"] = (
                                f"532F:750C:{donor_cell:02X}")
                        output = Path(directory) / firmware.stem / str(supplied)
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "15",
                             "--trace-movc", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment, timeout=25)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertFalse(report["p4_6_force_low_experimental"])
                        reads = [row for row in report["movc_observation"]["reads"]
                                 if row["dptr"] == "750C" and row["pc"] in
                                 ("532F", "5333")]
                        self.assertEqual([(row["pc"], row["acc"], row["mapped"],
                                           row["value"]) for row in reads],
                                         [("532F", "00", "750C", "53"),
                                          ("5333", "01", "750D", "5D")])
                        self.assertEqual(reads[0]["count"], reads[1]["count"])
                        self.assertGreaterEqual(reads[0]["count"], 280)
                        self.assertEqual(report["engine_ram_observation"]["79"][-1]
                                         ["after"], "75" if supplied else "53")
                        cc3 = report["cc3_observation"]
                        observed = (cc3["iram14_15_median"],
                                    cc3["cc3_pin_model_median_low_width_ticks"])
                        if supplied:
                            self.assertEqual(observed, controls[firmware])
                        else:
                            controls[firmware] = observed
                            self.assertEqual(observed, (1170, 4646.5))
                        log = (output / "emulator-trace.log").read_text()
                        b_values = {value for tick, value in re.findall(
                            r"\[INJECTION-INPUT\] tick=(\d+).*? B=([0-9A-F]{2})",
                            log) if int(tick) > 1300000}
                        self.assertEqual(b_values, {"1C" if supplied else "14"})
                        self.assertEqual("[MOVC-OVERRIDE] PC=532F mapped=750C" in log,
                                         supplied)

    def test_750c_curve_changes_cc3_with_supplied_ram78_gate(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((REFERENCE, 1491, 1591, 5934.5, 6347.0, 1861.0),
                 (sun, 1493, 1591, 5938.5, 6346.5, 1921.0))
        with tempfile.TemporaryDirectory() as directory:
            for firmware, native_cc3, donor_cc3, native_width, donor_width, p5 in cases:
                for supplied in (False, True):
                    with self.subTest(firmware=firmware.name, supplied=supplied):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_ADC10_STEP_CH",
                                                              "MA17_OVERRIDE_", "MA17_TRACE_"))
                                       and key != "MA17_P4_6_FORCE_LOW"}
                        environment.update(MA17_ADC_CH3="4", MA17_ADC_CH5="40",
                                           MA17_ADC_CH7="63", MA17_OVERRIDE_RAM78="80")
                        if supplied:
                            environment["MA17_OVERRIDE_MOVC_AT"] = "532F:750C:75"
                        output = Path(directory) / firmware.stem / str(supplied)
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "15",
                             "--trace-movc", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment, timeout=25)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertEqual(report["ram78_override_hex"], "80")
                        reads = [row for row in report["movc_observation"]["reads"]
                                 if row["pc"] == "532F" and row["dptr"] == "750C"]
                        self.assertEqual([(row["mapped"], row["value"]) for row in reads],
                                         [("750C", "53")])
                        self.assertEqual(report["engine_ram_observation"]["79"][-1]
                                         ["after"], "75" if supplied else "53")
                        cc3 = report["cc3_observation"]
                        self.assertEqual(cc3["iram14_15_median"],
                                         donor_cc3 if supplied else native_cc3)
                        self.assertEqual(cc3["cc3_pin_model_median_low_width_ticks"],
                                         donor_width if supplied else native_width)
                        self.assertEqual(report["output_latches"]["P5.0"]
                                         ["median_low_width_ticks"], p5)
                        log = (output / "emulator-trace.log").read_text()
                        self.assertIn("[RAM78-OVERRIDE] PC=1D4B RAM78=80", log)
                        self.assertEqual("[MOVC-OVERRIDE] PC=532F mapped=750C" in log,
                                         supplied)

    def test_temperature_channels_change_cc3_independently_in_g_and_s88(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((100, 80, "64", "50", "40", 1422),
                 (40, 80, "28", "50", "3C", 1336),
                 (100, 40, "64", "28", "40", 1194),
                 (20, 80, "14", "50", "3A", 1304),
                 (80, 80, "50", "50", "3F", 1400),
                 (160, 80, "A0", "50", "42", 1495),
                 (220, 80, "DC", "50", "48", 1616),
                 (100, 20, "64", "14", "40", 1096),
                 (100, 160, "64", "A0", "40", 1945),
                 (100, 220, "64", "DC", "40", 2678))
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                for adc2, adc3, air, coolant, ram48, cc3 in cases:
                    with self.subTest(firmware=firmware.name, adc2=adc2, adc3=adc3):
                        output = Path(directory) / firmware.stem / f"{adc2}_{adc3}"
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({"MA17_ADC_CH2": str(adc2),
                                            "MA17_ADC_CH3": str(adc3),
                                            "MA17_ADC_CH7": "63"})
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "20",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        observed = report["sensor_ram_observation"]
                        self.assertEqual(observed["62"][-1]["after"], air)
                        self.assertEqual(observed["63"][-1]["after"], coolant)
                        self.assertEqual(report["engine_ram_observation"]["48"][-1]
                                         ["after"], ram48)
                        self.assertEqual(report["cc3_observation"]
                                         ["iram14_15_median"], cc3)
                        expected_p5 = 1861 if firmware == REFERENCE else 1921
                        self.assertEqual(report["output_latches"]["P5.0"]
                                         ["median_low_width_ticks"], expected_p5)

    def test_adc2_lookup_reaches_upper_ae_writer_in_fiat(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = {
            "base": (None, None, ("7E", "21")),
            "7100_delta08": (None, "08", ("86", "23")),
            "adc2_200": ("200", None, ("89", "24")),
        }
        matrix_reads = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, (adc2, delta, expected_pair) in cases.items():
                with self.subTest(case=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH7": "63", "MA17_TRACE_UPPER_AE_SOURCE": "1"})
                    if adc2 is not None:
                        environment["MA17_ADC_CH2"] = adc2
                    if delta is not None:
                        environment["MA17_OVERRIDE_MOVC_7100_DELTA"] = delta
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_7100_delta_hex"], delta)
                    matrix_reads[name] = {
                        row["mapped"]: row["count"]
                        for row in report["movc_observation"]["reads"]
                        if 0x7B46 <= int(row["mapped"], 16) < 0x7BBE}
                    self.assertEqual(report["engine_ram_observation"]["69"]
                                     [-1]["after"], "9A")
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1861)
                    log = (output / "emulator-trace.log").read_text()
                    rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)", line))
                            for line in log.splitlines()
                            if line.startswith("[UPPER-AE-SOURCE]")]
                    self.assertEqual(len(rows), 230)
                    pairs = [(row["RAM7C"], row["A"]) for row in rows]
                    self.assertGreaterEqual(pairs.count(expected_pair), 90)
                    self.assertEqual({pair for pair in pairs if pair[0] not in
                                      ("00", "80")},
                                     {expected_pair, {"base": ("7E", "2E"),
                                                      "7100_delta08": ("86", "31"),
                                                      "adc2_200": ("89", "32")}[name]})
        self.assertEqual(sum(matrix_reads["base"].values()), 918)
        self.assertEqual(matrix_reads["base"], matrix_reads["7100_delta08"])
        self.assertEqual(matrix_reads["base"], matrix_reads["adc2_200"])

    def test_adc2_7100_crosses_upper_ae_matrix_segment_in_fiat(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        states = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, adc2, delta in (("adc2_4", "4", None),
                                      ("adc2_100", "100", None),
                                      ("adc2_100_delta_f2", "100", "F2")):
                with self.subTest(case=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH2": adc2,
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_RAM69": "1"})
                    if delta is not None:
                        environment["MA17_OVERRIDE_MOVC_7100_DELTA"] = delta
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_7100_delta_hex"], delta)
                    rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)", line))
                            for line in (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[RAM69-PATH]")]
                    ae = Counter(row["UAE"] for row in rows if row["PC"] == "330D")
                    r2 = Counter(row["R2"] for row in rows if row["PC"] == "3371")
                    cells = Counter()
                    for row in report["movc_observation"]["reads"]:
                        if row["pc"] == "532F" and row["dptr"] == "7B46":
                            cells[row["mapped"]] += row["count"]
                    states[name] = (ae, r2, cells)
                    self.assertEqual(report["engine_ram_observation"]["69"]
                                     [-1]["after"], "9A")
        base = states["adc2_100"]
        shifted = states["adc2_4"]
        self.assertEqual(shifted, states["adc2_100_delta_f2"])
        self.assertEqual(base[0]["21"], 209)
        self.assertEqual(shifted[0]["1D"], 95)
        self.assertEqual(base[1]["96"], 0)
        self.assertEqual(shifted[1]["96"], 95)
        self.assertEqual(base[2]["7B58"], 0)
        self.assertEqual(shifted[2]["7B58"], 95)

    def test_s88_adc2_segment_crossing_reads_equal_matrix_cells(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / EXPECTED[2]
        image = s88.read_bytes()
        self.assertEqual(image[0x7B5A], image[0x7B69])
        self.assertEqual(image[0x7B69], 0x93)
        states = {}
        with tempfile.TemporaryDirectory() as directory:
            for adc2 in (4, 100):
                with self.subTest(adc2=adc2):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH2": str(adc2),
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_RAM69": "1"})
                    output = Path(directory) / str(adc2)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(s88), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(image).hexdigest())
                    rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)", line))
                            for line in (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[RAM69-PATH]")]
                    ae = Counter((row["UAE"], row["UBC"]) for row in rows
                                 if row["PC"] == "330D")
                    r2 = Counter(row["R2"] for row in rows if row["PC"] == "3371")
                    cells = Counter()
                    for row in report["movc_observation"]["reads"]:
                        if row["pc"] == "532F" and row["dptr"] == "7B46":
                            cells[row["mapped"]] += row["count"]
                    states[adc2] = (ae, r2, cells)
                    self.assertEqual(report["engine_ram_observation"]["69"]
                                     [-1]["after"], "95")
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1921)
        self.assertEqual(states[100][0][("1F", "15")], 210)
        self.assertEqual(states[4][0][("1B", "15")], 95)
        self.assertEqual(states[100][2]["7B69"], 209)
        self.assertEqual(states[4][2]["7B5A"], 95)
        self.assertEqual(states[4][1], states[100][1])
        self.assertEqual(states[4][1]["92"], 209)

    def test_7580_and_7b46_factorial_separates_p5_from_cc3(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / EXPECTED[2]
        expected = {
            "control": (False, False, False, "7B67", "97", "9A", "8B", 1861, 2413),
            "matrix": (False, True, False, "7B67", "9F", "A2", "A8", 1861, 2412),
            "selector": (True, False, False, "7B5A", "8A", "8D", "DD", 1921, 1797),
            "both": (True, True, False, "7B5A", "92", "95", "FA", 1921, 1797),
            "s88": (False, False, True, "7B69", "92", "95", "FA", 1921, 2301),
        }
        with tempfile.TemporaryDirectory() as directory:
            for name, (selector, matrix, native_s88, cell, r2, ram69,
                       ram34, p5, cc3) in expected.items():
                with self.subTest(case=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH2": "100",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_RAM69": "1"})
                    if selector:
                        environment["MA17_OVERRIDE_MOVC_7580"] = "25"
                    if matrix:
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(s88)
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7B46"
                    output = Path(directory) / name
                    command = [sys.executable, str(ROOT / "tools" / "trace_ma17.py")]
                    if native_s88:
                        command += ["--firmware", str(s88)]
                    command += ["--no-kline-inject", "--crank-immediate",
                                "--rpm", "1000", "--stop-ticks", "2400000",
                                "--seconds", "20", "--trace-movc",
                                "--output-dir", str(output)]
                    result = subprocess.run(command, capture_output=True,
                                            text=True, env=environment,
                                            timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    active = s88 if native_s88 else REFERENCE
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(active.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_7580_override_hex"],
                                     "25" if selector else None)
                    self.assertEqual(report["movc_matrix_base_hex"],
                                     "7B46" if matrix else None)
                    rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)", line))
                            for line in (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[RAM69-PATH]")]
                    self.assertEqual(Counter(row["R2"] for row in rows
                                             if row["PC"] == "3371")[r2], 209)
                    reads = sum(row["count"] for row in
                                report["movc_observation"]["reads"]
                                if row["pc"] == "532F" and row["dptr"] == "7B46"
                                and row["mapped"] == cell)
                    self.assertEqual(reads, 209)
                    self.assertEqual(report["engine_ram_observation"]["69"]
                                     [-1]["after"], ram69)
                    self.assertEqual(report["engine_ram_observation"]["34"]
                                     [-1]["after"], ram34)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], p5)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"], cc3)

    def test_three_s88_calibrations_match_selected_outputs_at_two_adc2_states(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / EXPECTED[2]
        donor_hash = hashlib.sha256(s88.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            for adc2 in (4, 100):
                signatures = {}
                for native_s88 in (False, True):
                    with self.subTest(adc2=adc2, native_s88=native_s88):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({
                            "MA17_ADC_CH0": "40", "MA17_ADC_CH2": str(adc2),
                            "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                            "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                            "MA17_TRACE_RAM69": "1"})
                        if not native_s88:
                            environment.update({
                                "MA17_OVERRIDE_MOVC_7580": "25",
                                "MA17_OVERRIDE_MOVC_7581_DELTA": "15",
                                "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(s88),
                                "MA17_OVERRIDE_MOVC_MATRIX_BASE": "7B46"})
                        output = Path(directory) / f"adc2_{adc2}_{'s88' if native_s88 else 'g'}"
                        command = [sys.executable,
                                   str(ROOT / "tools" / "trace_ma17.py")]
                        if native_s88:
                            command += ["--firmware", str(s88)]
                        command += ["--no-kline-inject", "--crank-immediate",
                                    "--rpm", "1000", "--stop-ticks", "2400000",
                                    "--seconds", "20", "--trace-movc",
                                    "--output-dir", str(output)]
                        result = subprocess.run(command, capture_output=True,
                                                text=True, env=environment,
                                                timeout=30, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        active = s88 if native_s88 else REFERENCE
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(active.read_bytes()).hexdigest())
                        if not native_s88:
                            self.assertEqual(report["movc_7581_delta_hex"], "15")
                            self.assertEqual(report["movc_matrix_donor_sha256"],
                                             donor_hash)
                        rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)", line))
                                for line in (output / "emulator-trace.log").read_text().splitlines()
                                if line.startswith("[RAM69-PATH]")]
                        ae_bc = Counter((row["UAE"], row["UBC"])
                                        for row in rows if row["PC"] == "330D")
                        r2 = Counter(row["R2"] for row in rows
                                     if row["PC"] == "3371")
                        cells = Counter()
                        for row in report["movc_observation"]["reads"]:
                            if row["pc"] == "532F" and row["dptr"] == "7B46":
                                cells[row["mapped"]] += row["count"]
                        signatures[native_s88] = (
                            ae_bc, r2, cells,
                            report["engine_ram_observation"]["69"][-1]["after"],
                            report["engine_ram_observation"]["34"][-1]["after"],
                            report["output_latches"]["P5.0"]["median_low_width_ticks"],
                            report["cc3_observation"], report["lookup_observation"])
                self.assertEqual(signatures[False], signatures[True])
                self.assertEqual(signatures[True][3:6], ("95", "FA", 1921))
                self.assertEqual(signatures[True][6]
                                 ["cc3_pin_model_median_low_width_ticks"], 2301)

    def test_high_tps_switches_7b46_effect_to_7cae_matrix(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / EXPECTED[2]
        donor_hash = hashlib.sha256(s88.read_bytes()).hexdigest()
        reports = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, base in (("g_7b46", "7B46"), ("g_7cae", "7CAE"),
                               ("s88", None)):
                with self.subTest(case=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "180", "MA17_ADC_CH2": "100",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "247", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_RAM69": "1"})
                    if base is not None:
                        environment.update({
                            "MA17_OVERRIDE_MOVC_7580": "25",
                            "MA17_OVERRIDE_MOVC_7581_DELTA": "15",
                            "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(s88),
                            "MA17_OVERRIDE_MOVC_MATRIX_BASE": base})
                    output = Path(directory) / name
                    command = [sys.executable, str(ROOT / "tools" / "trace_ma17.py")]
                    if base is None:
                        command += ["--firmware", str(s88)]
                    command += ["--no-kline-inject", "--crank-immediate",
                                "--rpm", "1000", "--stop-ticks", "2400000",
                                "--seconds", "20", "--trace-movc",
                                "--output-dir", str(output)]
                    result = subprocess.run(command, capture_output=True,
                                            text=True, env=environment,
                                            timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    active = s88 if base is None else REFERENCE
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(active.read_bytes()).hexdigest())
                    if base is not None:
                        self.assertEqual(report["movc_matrix_donor_sha256"],
                                         donor_hash)
                        self.assertEqual(report["movc_matrix_base_hex"], base)
                    rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)", line))
                            for line in (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[RAM69-PATH]")]
                    r2 = Counter(row["R2"] for row in rows if row["PC"] == "3371")
                    ae_bc = Counter((row["UAE"], row["UBC"]) for row in rows
                                    if row["PC"] == "330D")
                    reads_7cae = sum(row["count"] for row in
                                     report["movc_observation"]["reads"]
                                     if 0x7CAE <= int(row["mapped"], 16) < 0x7D26)
                    reports[name] = (report, r2, ae_bc)
                    self.assertEqual(reads_7cae, 912)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1921)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"], 5512.5)
        original, switched, native = (reports[name] for name in
                                      ("g_7b46", "g_7cae", "s88"))
        self.assertEqual(original[1]["99"], 209)
        self.assertEqual(switched[1]["A1"], 209)
        self.assertEqual(native[1]["A1"], 210)
        self.assertEqual(switched[2], native[2])
        self.assertEqual(original[0]["engine_ram_observation"]["69"][-1]["after"],
                         "A1")
        for report, _, _ in (switched, native):
            self.assertEqual(report["engine_ram_observation"]["69"][-1]["after"],
                             "A5")
            self.assertEqual(report["engine_ram_observation"]["34"][-1]["after"],
                             "34")

    def test_terminal_segment_and_adjacent_curve_are_read_naturally_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(("MA17_ADC_CH", "MA17_OVERRIDE_"))}
            for channel, value in enumerate((40, 130, 100, 80, 90, 110, 95, 63)):
                environment[f"MA17_ADC_CH{channel}"] = str(value)
            environment["MA17_TRACE_RAM69"] = "1"
            output = Path(directory)
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                 "--stop-ticks", "2400000", "--seconds", "20",
                 "--trace-movc", "--output-dir", str(output)],
                capture_output=True, text=True, env=environment,
                timeout=30, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((output / "execution.json").read_text())
            self.assertEqual(report["firmware_sha256"],
                             hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
            reads = {row["mapped"]: row["count"] for row in
                     report["movc_observation"]["reads"]
                     if 0x7F8D <= int(row["mapped"], 16) < 0x7F9D}
            self.assertEqual(reads,
                             {"7F8D": 2, "7F8E": 2, "7F95": 2,
                              "7F97": 1, "7F98": 1})
            rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)", line))
                    for line in (output / "emulator-trace.log").read_text().splitlines()
                    if line.startswith("[RAM69-PATH]") and "PC=3AD2" in line]
            self.assertEqual([row["U83"] for row in rows], ["01", "02"])
            self.assertEqual([row["U8C"] for row in rows], ["9C", "9B"])

    def test_terminal_7f96_movc_changes_natural_ram69_history(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (("native", None, "9B", ["9B", "9A"], 2),
                 ("zero", "3AD2:7F97:00,3AD2:7F98:00", "9C", ["9A"], 3),
                 ("max", "3AD2:7F97:FF,3AD2:7F98:FF", "9A", ["9A"], 1))
        with tempfile.TemporaryDirectory() as directory:
            for name, override, first_u8c, writes, read_count in cases:
                with self.subTest(case=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    for channel, value in enumerate((40, 130, 100, 80,
                                                     90, 110, 95, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment["MA17_TRACE_RAM69"] = "1"
                    if override:
                        environment["MA17_OVERRIDE_MOVC_AT"] = override
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", "1000", "--stop-ticks", "2400000",
                         "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"], override)
                    rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)", line))
                            for line in (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[RAM69-PATH]")]
                    self.assertEqual(sum(row["PC"] == "3AD2" for row in rows),
                                     read_count)
                    first_write = next(row for row in rows
                                       if row["PC"] == "3B06" and
                                       int(row["tick"]) > 280000)
                    self.assertEqual(first_write["U8C"], first_u8c)
                    self.assertEqual([row["after"] for row in
                                      report["engine_ram_observation"]["69"]
                                      if row["source_pc"] == "3B06"], writes)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1861)

    def test_terminal_segment_a_bytes_are_masked_at_natural_g_inputs(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        signatures = []
        with tempfile.TemporaryDirectory() as directory:
            for name, override in (("control", None),
                                   ("header35", "527D:7F8D:35"),
                                   ("finalff", "5289:7F95:FF")):
                with self.subTest(case=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    for channel, value in enumerate((40, 130, 100, 80,
                                                      90, 110, 95, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment["MA17_TRACE_TERMINAL_SEGMENT"] = "1"
                    if override:
                        environment["MA17_OVERRIDE_MOVC_AT"] = override
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate",
                         "--rpm", "1000", "--stop-ticks", "2400000",
                         "--seconds", "20", "--trace-movc",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertTrue(report["terminal_segment_trace_enabled"])
                    self.assertEqual(report["movc_override_at_hex"], override)
                    log = (output / "emulator-trace.log").read_text().splitlines()
                    applied = [line for line in log
                               if line.startswith("[MOVC-OVERRIDE]")]
                    self.assertEqual(len(applied), bool(override))
                    rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)",
                                            line)) for line in log
                            if line.startswith("[TERMINAL-SEGMENT]")]
                    self.assertEqual([row["RAM0F"] for row in rows
                                      if row["PC"] == "3AAD"], ["FE", "FF"])
                    self.assertEqual([row["RAM35"] for row in rows
                                      if row["PC"] == "3AAD"], ["FF", "FF"])
                    self.assertEqual([row["R3"] for row in rows
                                      if row["PC"] == "3AB3"], ["06", "06"])
                    signatures.append(tuple(report[key] for key in (
                        "pc_coverage", "lookup_observation", "cc3_observation",
                        "engine_ram_observation", "output_latches",
                        "movc_observation")))
        self.assertEqual(signatures[0], signatures[1])
        self.assertEqual(signatures[0], signatures[2])

    def test_terminal_segment_access_depends_on_rpm_and_adc0_state_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for rpm, adc0, expected_calls, gate_b in (
                    (750, 4, 0, []), (1000, 4, 2, ["07", "07"]),
                    (1000, 20, 2, ["07", "07"]),
                    (1000, 200, 0, ["0F"])):
                with self.subTest(rpm=rpm, adc0=adc0):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    for channel, value in enumerate((adc0, 130, 100, 80,
                                                      90, 110, 95, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment["MA17_TRACE_TERMINAL_SEGMENT"] = "1"
                    environment["MA17_TRACE_RAM69"] = "1"
                    output = Path(directory) / f"{rpm}_{adc0}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate",
                         "--rpm", str(rpm), "--stop-ticks", "2400000",
                         "--seconds", "20", "--trace-movc",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    gates = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)",
                                             line)) for line in lines
                             if line.startswith("[TERMINAL-GATE]")]
                    self.assertEqual([row["B"] for row in gates], gate_b)
                    sources = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)",
                                               line)) for line in lines
                               if line.startswith("[TERMINAL-SOURCE]")]
                    for gate in gates:
                        preceding = [row for row in sources
                                     if int(row["tick"]) < int(gate["tick"])]
                        self.assertTrue(preceding)
                        source = preceding[-1]
                        self.assertEqual(source["RAM2E"], "84")
                        self.assertEqual(source["RAM28"],
                                         "06" if adc0 == 200 else "00")
                        self.assertEqual(source["C"],
                                         "1" if adc0 == 200 else "0")
                        self.assertEqual(source["U94"], gate["B"])
                    if adc0 == 4:
                        inputs = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)",
                                                  line)) for line in lines
                                  if line.startswith("[RAM69-PATH]")
                                  and "PC=3A04" in line]
                        self.assertGreater(len(inputs), 0)
                        below = sum(int(row["R2"], 16) < int(row["U8C"], 16)
                                    for row in inputs)
                        self.assertEqual(below, expected_calls)
                        if rpm == 750:
                            self.assertTrue(all(row["R2"] == row["U8C"]
                                                for row in inputs))
                    rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)",
                                            line))
                            for line in lines
                            if line.startswith("[TERMINAL-SEGMENT]")]
                    entries = [row for row in rows if row["PC"] == "3AAD"]
                    exits = [row for row in rows if row["PC"] == "3AB3"]
                    self.assertEqual(len(entries), expected_calls)
                    self.assertEqual(len(exits), expected_calls)
                    if expected_calls:
                        self.assertEqual([row["RAM0F"] for row in entries],
                                         ["FE", "FF"])
                        self.assertEqual([row["R3"] for row in exits],
                                         ["06", "06"])

    def test_terminal_segment_natural_rpm_sweep_stays_outside_low_input_range(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for rpm, count, low, high in ((1500, 6, 0xF2, 0xFD),
                                          (2000, 8, 0xE3, 0xFD),
                                          (3000, 11, 0xC3, 0xF9),
                                          (4000, 15, 0xA4, 0xFE)):
                with self.subTest(rpm=rpm):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    for channel, value in enumerate((40, 130, 100, 80,
                                                     90, 110, 95, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment["MA17_TRACE_TERMINAL_SEGMENT"] = "1"
                    if rpm == 4000:
                        environment["MA17_TRACE_RAM69"] = "1"
                    output = Path(directory) / str(rpm)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate",
                         "--rpm", str(rpm), "--stop-ticks",
                         "4000000" if rpm == 4000 else "2400000",
                         "--seconds", "20", "--trace-movc",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)",
                                            line))
                            for line in (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[TERMINAL-SEGMENT]")]
                    entries = [row for row in rows if row["PC"] == "3AAD"]
                    exits = [row for row in rows if row["PC"] == "3AB3"]
                    self.assertEqual((len(entries), len(exits)), (count, count))
                    inputs = [int(row["RAM0F"], 16) for row in entries]
                    self.assertEqual((min(inputs), max(inputs)), (low, high))
                    self.assertTrue(all(row["R3"] == "06" for row in exits))
                    if rpm == 4000:
                        self.assertLess(int(entries[-1]["tick"]), 310000)
                        gate_inputs = [dict(re.findall(
                            r"([A-Za-z0-9_]+)=([A-Za-z0-9_]+)", line))
                            for line in (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[RAM69-PATH]") and "PC=3A04" in line]
                        later = [row for row in gate_inputs
                                 if int(row["tick"]) > int(entries[-1]["tick"])]
                        self.assertEqual(len(later), 362)
                        self.assertTrue(all(row["R2"] == row["U8C"] == "40"
                                            for row in later))

    def test_terminal_segment_iram69_values_change_modeled_p5_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for ram69, expected_width in ((None, 1861), ("7F", 1921),
                                          ("7A", 1863)):
                with self.subTest(ram69=ram69):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    for channel, value in enumerate((40, 130, 100, 80,
                                                      90, 110, 95, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    if ram69:
                        environment["MA17_OVERRIDE_RAM69"] = ram69
                    output = Path(directory) / (ram69 or "control")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate",
                         "--rpm", "1000", "--stop-ticks", "2400000",
                         "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["ram69_override_hex"], ram69)
                    log = (output / "emulator-trace.log").read_text()
                    self.assertEqual("[RAM69-OVERRIDE]" in log, bool(ram69))
                    if ram69:
                        self.assertIn(f"RAM47=28 RAM69={ram69}", log)
                    for channel in ("P5.0", "P5.1"):
                        p5 = report["output_latches"][channel]
                        self.assertGreaterEqual(p5["low_starts"], 30)
                        self.assertEqual(p5["median_period_ticks"], 59400)
                        self.assertEqual(p5["median_low_width_ticks"],
                                         expected_width)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     3041)

    def test_terminal_segment_dual_movc_override_changes_r3_not_p5_median(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (("source28", "527D:7F8D:28", ["00", "00"],
                  ["00", "00"]),
                 ("source28_finalff", "527D:7F8D:28,5289:7F95:FF",
                  ["05", "05"], ["00", "01"]))
        with tempfile.TemporaryDirectory() as directory:
            for name, override, expected_r3, expected_u83 in cases:
                with self.subTest(case=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    for channel, value in enumerate((40, 130, 100, 80,
                                                      90, 110, 95, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment["MA17_TRACE_TERMINAL_SEGMENT"] = "1"
                    environment["MA17_OVERRIDE_MOVC_AT"] = override
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate",
                         "--rpm", "1000", "--stop-ticks", "2400000",
                         "--seconds", "20", "--trace-movc",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"], override)
                    log = (output / "emulator-trace.log").read_text().splitlines()
                    applied = [line for line in log
                               if line.startswith("[MOVC-OVERRIDE]")]
                    self.assertEqual(len(applied), len(override.split(",")))
                    entries = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)",
                                               line)) for line in log
                               if line.startswith("[TERMINAL-SEGMENT]")
                               and "PC=3AAD" in line]
                    self.assertEqual([row["RAM28"] for row in entries],
                                     ["00", "00"])
                    exits = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9]+)",
                                             line)) for line in log
                             if line.startswith("[TERMINAL-SEGMENT]")
                             and "PC=3AB3" in line]
                    self.assertEqual([row["R3"] for row in exits], expected_r3)
                    self.assertEqual([row["U83"] for row in exits], expected_u83)
                    self.assertEqual([row["RAM69"] for row in exits],
                                     ["9C", "9B"])
                    self.assertEqual(report["engine_ram_observation"]["69"][-1]
                                     ["after"], "9A")
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1861)

    def test_high_tps_7cae_donor_matches_selected_outputs_across_rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / EXPECTED[2]
        with tempfile.TemporaryDirectory() as directory:
            for rpm, reads, ram69, ram34, p5, cc3 in (
                    (750, 684, "A5", "17", 1940, 5138),
                    (1500, 912, "9E", "EC", 1765, 5548)):
                reports = []
                for native_s88 in (False, True):
                    with self.subTest(rpm=rpm, native_s88=native_s88):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({
                            "MA17_ADC_CH0": "180", "MA17_ADC_CH2": "100",
                            "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                            "MA17_ADC_CH6": "247", "MA17_ADC_CH7": "63",
                            "MA17_TRACE_RAM69": "1"})
                        if not native_s88:
                            environment.update({
                                "MA17_OVERRIDE_MOVC_7580": "25",
                                "MA17_OVERRIDE_MOVC_7581_DELTA": "15",
                                "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(s88),
                                "MA17_OVERRIDE_MOVC_MATRIX_BASE": "7CAE"})
                        output = Path(directory) / f"rpm{rpm}_{native_s88}"
                        command = [sys.executable,
                                   str(ROOT / "tools" / "trace_ma17.py")]
                        if native_s88:
                            command += ["--firmware", str(s88)]
                        command += ["--no-kline-inject", "--crank-immediate",
                                    "--rpm", str(rpm), "--stop-ticks", "2400000",
                                    "--seconds", "20", "--trace-movc",
                                    "--output-dir", str(output)]
                        result = subprocess.run(command, capture_output=True,
                                                text=True, env=environment,
                                                timeout=30, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        active = s88 if native_s88 else REFERENCE
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(active.read_bytes()).hexdigest())
                        if not native_s88:
                            self.assertEqual(report["movc_matrix_donor_sha256"],
                                             hashlib.sha256(s88.read_bytes()).hexdigest())
                        reads_7cae = sum(row["count"] for row in
                                         report["movc_observation"]["reads"]
                                         if 0x7CAE <= int(row["mapped"], 16) < 0x7D26)
                        self.assertEqual(reads_7cae, reads)
                        self.assertEqual(report["engine_ram_observation"]["69"][-1]
                                         ["after"], ram69)
                        self.assertEqual(report["engine_ram_observation"]["34"][-1]
                                         ["after"], ram34)
                        self.assertEqual(report["output_latches"]["P5.0"]
                                         ["median_low_width_ticks"], p5)
                        self.assertEqual(report["cc3_observation"]
                                         ["cc3_pin_model_median_low_width_ticks"], cc3)
                        reports.append(report)
                for key in ("lookup_observation", "cc3_observation", "pc_coverage"):
                    self.assertEqual(reports[0][key], reports[1][key])

    def test_adc2_table_7100_movc_result_changes_cc3_without_rom_patch(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        reports = {}
        with tempfile.TemporaryDirectory() as directory:
            for delta in (None, "08"):
                output = Path(directory) / (delta or "control")
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                      "MA17_OVERRIDE_"))}
                environment["MA17_ADC_CH7"] = "63"
                if delta:
                    environment["MA17_OVERRIDE_MOVC_7100_DELTA"] = delta
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "1000", "--stop-ticks", "2400000", "--seconds", "20",
                     "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                self.assertEqual(report["movc_7100_delta_hex"], delta)
                self.assertEqual(report["sensor_ram_observation"]["62"][-1]
                                 ["after"], "64")
                reads = [row for row in report["movc_observation"]["reads"]
                         if 0x7100 <= int(row["mapped"], 16) < 0x7109]
                self.assertTrue(reads)
                self.assertTrue(all(int(row["value"], 16) ==
                                    REFERENCE.read_bytes()[int(row["mapped"], 16)]
                                    for row in reads))
                log = (output / "emulator-trace.log").read_text()
                self.assertEqual("[MOVC-OVERRIDE] table=7100..7108 delta=08" in log,
                                 delta is not None)
                reports[delta] = report
        control, changed = reports[None], reports["08"]
        self.assertEqual(control["engine_ram_observation"]["7C"][-1]["after"],
                         "7E")
        self.assertEqual(changed["engine_ram_observation"]["7C"][-1]["after"],
                         "86")
        self.assertEqual((control["engine_ram_observation"]["48"][-1]["after"],
                          changed["engine_ram_observation"]["48"][-1]["after"]),
                         ("40", "44"))
        self.assertEqual((control["cc3_observation"]["iram14_15_median"],
                          changed["cc3_observation"]["iram14_15_median"]),
                         (1422, 1508))
        self.assertEqual((control["cc3_observation"]
                          ["cc3_pin_model_median_low_width_ticks"],
                          changed["cc3_observation"]
                          ["cc3_pin_model_median_low_width_ticks"]),
                         (5677, 6021))

    def test_air_lookup_716f_changes_p5_through_ram69_in_full_fiat_boot(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        reports = {}
        with tempfile.TemporaryDirectory() as directory:
            for override, ram69, label in (
                    (None, None, "control"),
                    ("532F:716F:8E", None, "table"),
                    ("532F:716F:8E", "A2", "table_ram69_a2"),
                    (None, "A5", "control_ram69_a5")):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                      "MA17_TRACE_", "MA17_P4_"))}
                environment.update(MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                                   MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                   MA17_ADC_CH7="63", MA17_TRACE_AIR_716C_GATE="1")
                if override:
                    environment["MA17_OVERRIDE_MOVC_AT"] = override
                if ram69:
                    environment["MA17_OVERRIDE_RAM69"] = ram69
                output = Path(directory) / label
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "1000", "--stop-ticks", "2400000", "--seconds", "20",
                     "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                self.assertGreater(report["air_gate_observation"]["pc_counts"]
                                   .get("398D", 0), 100)
                reads = [row for row in report["movc_observation"]["reads"]
                         if row["pc"] == "532F" and row["address"] == "716F"]
                self.assertEqual(len(reads), 1)
                self.assertEqual(reads[0]["value"], "86")
                log = (output / "emulator-trace.log").read_text()
                self.assertEqual("[MOVC-OVERRIDE] PC=532F mapped=716F "
                                 "original=86 supplied=8E" in log, override is not None)
                reports[label] = (report, log)
        for override, expected, expected_r2 in (
                ("control", "05", "A2"), ("table", "0C", "A9")):
            report, log = reports[override]
            self.assertTrue(any("PC=398D" in line and f"UCC={expected}" in line
                                and f"UC8={expected}" in line
                                for line in log.splitlines()
                                if line.startswith("[AIR-716C-GATE]")))
            self.assertTrue(any("PC=39F4" in line and f"UC8={expected}" in line
                                and "R2=9D" in line and f"A={expected_r2}" in line
                                for line in log.splitlines()
                                if line.startswith("[AIR-716C-GATE]")))
            self.assertEqual(report["cc3_observation"]
                             ["cc3_pin_model_median_low_width_ticks"], 4593)
        for label, expected_write, expected_p5 in (
                ("control", "A2", 1861),
                ("table", "A5", 1921),
                ("table_ram69_a2", "A5", 1861),
                ("control_ram69_a5", "A2", 1921)):
            report, log = reports[label]
            self.assertTrue(any(row["source_pc"] == "3B06" and
                                row["after"] == expected_write
                                for row in report["engine_ram_observation"]["69"]))
            self.assertEqual(report["output_latches"]["P5.0"]
                             ["median_low_width_ticks"], expected_p5)
            self.assertEqual(report["output_latches"]["P5.1"]
                             ["median_low_width_ticks"], expected_p5)
            self.assertEqual(report["cc3_observation"]
                             ["cc3_pin_model_median_low_width_ticks"], 4593)
            self.assertEqual("[RAM69-OVERRIDE]" in log, "ram69" in label)

    def test_air_lookup_716f_p5_effect_varies_with_rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        expected = {750: (1860, 1940, 4641), 1500: (1767, 1805, 5137)}
        with tempfile.TemporaryDirectory() as directory:
            for rpm, (control_width, changed_width, cc3_width) in expected.items():
                for override, width in ((None, control_width),
                                        ("532F:716F:8E", changed_width)):
                    with self.subTest(rpm=rpm, override=override):
                        environment = {
                            key: value for key, value in os.environ.items()
                            if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                   "MA17_TRACE_", "MA17_P4_"))}
                        environment.update(
                            MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                            MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                            MA17_ADC_CH7="63", MA17_TRACE_AIR_716C_GATE="1")
                        if override:
                            environment["MA17_OVERRIDE_MOVC_AT"] = override
                        output = Path(directory) / f"{rpm}_{override or 'control'}"
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--trace-movc", "--no-kline-inject",
                             "--crank-immediate", "--rpm", str(rpm),
                             "--stop-ticks", "2400000", "--seconds", "20",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(REFERENCE.read_bytes())
                                         .hexdigest())
                        self.assertGreater(report["air_gate_observation"]
                                           ["pc_counts"].get("398D", 0), 100)
                        self.assertEqual(report["output_latches"]["P5.0"]
                                         ["median_low_width_ticks"], width)
                        self.assertEqual(report["output_latches"]["P5.1"]
                                         ["median_low_width_ticks"], width)
                        self.assertEqual(report["cc3_observation"]
                                         ["cc3_pin_model_median_low_width_ticks"],
                                         cc3_width)
                        self.assertTrue(any(
                            row["source_pc"] == "3B06" and row["after"] ==
                            ("A5" if override else "A2")
                            for row in report["engine_ram_observation"]["69"]))

    def test_air_lookup_and_7cae_donor_share_ram69_cap(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        for firmware in (REFERENCE, *(VARIANTS / name for name in EXPECTED)):
            self.assertEqual(firmware.read_bytes()[0x72A7], 0xA5, firmware)
        cases = ((1000, False, False, "A2", "A2", 1861, 4593),
                 (1000, True, False, "A9", "A5", 1921, 4593),
                 (1000, False, True, "AA", "A5", 1921, 4593),
                 (1000, True, True, "B1", "A5", 1921, 4593),
                 (1500, False, False, "9C", "9C", 1767, 5137),
                 (1500, True, False, "A3", "A3", 1805, 5137),
                 (1500, False, True, "A4", "A4", 1766, 5137),
                 (1500, True, True, "AB", "A5", 1805, 5137),
                 (2000, False, False, "92", "92", 1805, 5173),
                 (2000, True, False, "99", "99", 1834, 5172),
                 (2000, False, True, "9A", "9A", 1805, 5173),
                 (2000, True, True, "A1", "A1", 1832, 5172))
        with tempfile.TemporaryDirectory() as directory:
            for rpm, air, matrix, upper_8c, ram69, p5_width, cc3_width in cases:
                with self.subTest(rpm=rpm, air=air, matrix=matrix):
                    environment = {
                        key: value for key, value in os.environ.items()
                        if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                               "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(
                        MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                        MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                        MA17_ADC_CH7="63", MA17_TRACE_RAM69="1")
                    if rpm == 1500 and not air:
                        environment["MA17_TRACE_TIMER1_PATH"] = "1"
                    if air:
                        environment["MA17_OVERRIDE_MOVC_AT"] = "532F:716F:8E"
                    if matrix:
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7CAE"
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(donor)
                    output = Path(directory) / f"{rpm}_{air}_{matrix}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", str(rpm),
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes())
                                     .hexdigest())
                    self.assertEqual(report["movc_matrix_size"],
                                     120 if matrix else None)
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(donor.read_bytes()).hexdigest()
                                     if matrix else None)
                    self.assertEqual(report["movc_override_at_hex"],
                                     "532F:716F:8E" if air else None)
                    reads = report["movc_observation"]["reads"]
                    self.assertEqual(sum(row["count"] for row in reads
                                         if 0x7CAE <= int(row["address"], 16)
                                         < 0x7D26), 912)
                    self.assertEqual(sum(row["count"] for row in reads
                                         if row["address"] == "716F"), 11)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], p5_width)
                    self.assertEqual(report["output_latches"]["P5.1"]
                                     ["median_low_width_ticks"], p5_width)
                    widths = report["output_latches"]["P5.0"]
                    histogram = {row["width_ticks"]: row["count"]
                                 for row in widths["low_width_histogram"]}
                    self.assertEqual(sum(histogram.values()),
                                     widths["low_starts"])
                    if rpm == 1500:
                        self.assertGreaterEqual(histogram[p5_width], 48)
                    if rpm == 1500 and not air:
                        trace = (output / "emulator-trace.log").read_text()
                        loads = re.findall(
                            r"\[TIMER1-PATH\].*PC=(0286|0298).*"
                            r"R32_33=([0-9A-F]{4}) R34_35=([0-9A-F]{4})",
                            trace)
                        self.assertEqual(len(loads), 222)
                        self.assertEqual({pc for pc, _, _ in loads},
                                         {"0286", "0298"})
                        self.assertEqual({(a, b) for _, a, b in loads[-20:]},
                                         {("D9FF", "04FF") if matrix else
                                          ("C5FF", "F1FE")})
                        load_ticks = [int(t) for t in re.findall(
                            r"\[TIMER1-PATH\] tick=(\d+) PC=0298", trace)]
                        p5_edges = [(int(t), pc) for t, pc in re.findall(
                            r"\[P5-LATCH\] instr=(\d+) PC=(00A8|0098)",
                            trace)]
                        low_pairs = [(a[0], b[0]) for a, b in
                                     zip(p5_edges, p5_edges[1:])
                                     if a[1] == "00A8" and b[1] == "0098"]
                        delays = []
                        for low, high in low_pairs[-10:]:
                            load = next(t for t in load_ticks if low < t < high)
                            delays.append((load - low, high - load))
                        self.assertEqual(tuple(map(statistics.median,
                                                   zip(*delays))),
                                         (75, 1691) if matrix else (56, 1711))
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     cc3_width)
                    self.assertTrue(any(
                        row["source_pc"] == "3B06" and row["after"] == ram69
                        for row in report["engine_ram_observation"]["69"]))
                    log = (output / "emulator-trace.log").read_text()
                    self.assertTrue(any(
                        f"PC=3B06 A={ram69} B=A5" in line and
                        f"U8C={upper_8c}" in line
                        for line in log.splitlines()
                        if line.startswith("[RAM69-PATH]")))

    def test_rpm2000_7cae_p5_interaction_is_mediated_by_ram69(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((False, None, "99", "9A", 1834),
                 (False, "A1", "99", "A8", 1832),
                 (True, None, "A1", "A8", 1832),
                 (True, "99", "A1", "9A", 1834))
        with tempfile.TemporaryDirectory() as directory:
            for matrix, ram69, native_69, timer34, width in cases:
                with self.subTest(matrix=matrix, ram69=ram69):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH7="63", MA17_TRACE_RAM69="1",
                                       MA17_TRACE_TIMER1_PATH="1",
                                       MA17_OVERRIDE_MOVC_AT="532F:716F:8E")
                    if matrix:
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7CAE"
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(donor)
                    if ram69:
                        environment["MA17_OVERRIDE_RAM69"] = ram69
                    output = Path(directory) / f"{matrix}_{ram69}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", "2000", "--stop-ticks", "2400000",
                         "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["ram69_override_hex"], ram69)
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(donor.read_bytes()).hexdigest()
                                     if matrix else None)
                    self.assertEqual(report["engine_ram_observation"]["69"][-1]["after"],
                                     native_69)
                    self.assertEqual(report["engine_ram_observation"]["34"][-1]["after"],
                                     timer34)
                    for pin in ("P5.0", "P5.1"):
                        self.assertEqual(report["output_latches"][pin]
                                         ["median_low_width_ticks"], width)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"], 5172)
                    trace = (output / "emulator-trace.log").read_text()
                    self.assertEqual("[RAM69-OVERRIDE] RAM47=50" in trace,
                                     ram69 is not None)
                    loads = re.findall(
                        r"\[TIMER1-PATH\] tick=(\d+) PC=(0286|0298).*"
                        r"R32_33=([0-9A-F]{4}) R34_35=([0-9A-F]{4})", trace)
                    self.assertEqual(len(loads), 299)
                    expected_reloads = (("43FF", "A8FF") if timer34 == "A8"
                                        else ("34FF", "9AFF"))
                    self.assertEqual({(a, b) for _, _, a, b in loads[-20:]},
                                     {expected_reloads})
                    load_ticks = [int(t) for t, pc, _, _ in loads if pc == "0298"]
                    edges = [(int(t), pc) for t, pc in re.findall(
                        r"\[P5-LATCH\] instr=(\d+) PC=(00A8|0098)", trace)]
                    low_pairs = [(a[0], b[0]) for a, b in zip(edges, edges[1:])
                                 if a[1] == "00A8" and b[1] == "0098"]
                    self.assertEqual(len(low_pairs), 75)
                    delays = []
                    for low, high in low_pairs[-10:]:
                        load = next(t for t in load_ticks if low < t < high)
                        delays.append((load - low, high - load))
                    self.assertEqual(tuple(map(statistics.median, zip(*delays))),
                                     (156, 1676) if timer34 == "A8"
                                     else (143, 1691))

    def test_s37_s36_7cae_calibration_reaches_shared_ram69_cap(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s37 = VARIANTS / "tipo 1.6 alcool27c256 SUN 37a5.bin"
        s36 = VARIANTS / "tipo 1.6 alcool27c256 SUN 36fd.bin"
        original = REFERENCE.read_bytes()[0x7CAE:0x7D26]
        donor = s37.read_bytes()[0x7CAE:0x7D26]
        self.assertEqual(donor, s36.read_bytes()[0x7CAE:0x7D26])
        self.assertEqual(len(donor), 120)
        self.assertTrue(all((changed - native) & 0xFF == 0x16
                            for native, changed in zip(original, donor)))
        with tempfile.TemporaryDirectory() as directory:
            for rpm, air, upper_8c, p5_width, cc3_width in (
                    (1000, False, "B8", 1921, 4593),
                    (1500, False, "B2", 1805, 5137),
                    (2000, False, "A8", 1834, 5172),
                    (2000, True, "AF", 1834, 5173)):
                with self.subTest(rpm=rpm, air=air):
                    environment = {
                        key: value for key, value in os.environ.items()
                        if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                               "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(
                        MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                        MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                        MA17_ADC_CH7="63", MA17_TRACE_RAM69="1",
                        MA17_OVERRIDE_MOVC_MATRIX_BASE="7CAE",
                        MA17_OVERRIDE_MOVC_MATRIX_ROM=str(s37))
                    if air:
                        environment["MA17_OVERRIDE_MOVC_AT"] = "532F:716F:8E"
                    output = Path(directory) / f"{rpm}_{air}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", str(rpm),
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(s37.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"],
                                     "532F:716F:8E" if air else None)
                    self.assertEqual(sum(row["count"] for row in
                                         report["movc_observation"]["reads"]
                                         if 0x7CAE <= int(row["address"], 16)
                                         < 0x7D26), 912)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], p5_width)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     cc3_width)
                    trace = (output / "emulator-trace.log").read_text()
                    self.assertIn(f"U8C={upper_8c} RAM47=", trace)
                    self.assertTrue(any(
                        f"PC=3B06 A=A5 B=A5" in line and
                        f"U8C={upper_8c}" in line for line in trace.splitlines()))

    def test_s37_s88_rpm2000_p5_difference_is_mediated_by_ram69(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        s37 = VARIANTS / "tipo 1.6 alcool27c256 SUN 37a5.bin"
        cases = ((s88, None, "9A", "17FF", "60FF", 1805, 5173, (85, 1720)),
                 (s88, "A5", "9A", "C5FF", "34FF", 1834, 5172, (40, 1794.5)),
                 (s37, None, "A5", "C5FF", "34FF", 1834, 5172, (40, 1794.5)),
                 (s37, "9A", "A5", "17FF", "60FF", 1805, 5173, (85, 1720)))
        with tempfile.TemporaryDirectory() as directory:
            for donor, supplied, native, reload32, reload34, width, cc3, delays in cases:
                with self.subTest(donor=donor.name, supplied=supplied):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH7="63", MA17_TRACE_RAM69="1",
                                       MA17_TRACE_TIMER1_PATH="1",
                                       MA17_OVERRIDE_MOVC_MATRIX_BASE="7CAE",
                                       MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor))
                    if supplied:
                        environment["MA17_OVERRIDE_RAM69"] = supplied
                    output = Path(directory) / f"{donor.stem}_{supplied}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", "2000", "--stop-ticks", "2400000",
                         "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(donor.read_bytes()).hexdigest())
                    self.assertEqual(report["ram69_override_hex"], supplied)
                    self.assertEqual(report["engine_ram_observation"]["69"][-1]["after"],
                                     native)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], width)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"], cc3)
                    trace = (output / "emulator-trace.log").read_text()
                    loads = re.findall(
                        r"\[TIMER1-PATH\] tick=(\d+) PC=(0286|0298).*"
                        r"R32_33=([0-9A-F]{4}) R34_35=([0-9A-F]{4})", trace)
                    self.assertEqual({(a, b) for _, _, a, b in loads[-20:]},
                                     {(reload32, reload34)})
                    load_ticks = [int(t) for t, pc, _, _ in loads if pc == "0298"]
                    edges = [(int(t), pc) for t, pc in re.findall(
                        r"\[P5-LATCH\] instr=(\d+) PC=(00A8|0098)", trace)]
                    low_pairs = [(a[0], b[0]) for a, b in zip(edges, edges[1:])
                                 if a[1] == "00A8" and b[1] == "0098"]
                    self.assertEqual(len(low_pairs), 75)
                    timings = []
                    for low, high in low_pairs[-10:]:
                        load = next(t for t in load_ticks if low < t < high)
                        timings.append((load - low, high - load))
                    self.assertEqual(tuple(map(statistics.median, zip(*timings))),
                                     delays)

    def test_adc2_switches_7cae_donor_effect_at_2000rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        original = REFERENCE.read_bytes()
        self.assertEqual(original[0x3350:0x3353], bytes.fromhex("20 7A 03"))
        self.assertEqual(original[0x3D0C:0x3D0E], bytes.fromhex("92 7A"))
        self.assertEqual(original[0x709C:0x709E], bytes.fromhex("7B 46"))
        self.assertEqual(original[0x70B6:0x70B8], bytes.fromhex("7C AE"))
        s88 = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        s37 = VARIANTS / "tipo 1.6 alcool27c256 SUN 37a5.bin"
        cases = ((40, None, 912, 6, "94", "94", "17", 1805, 4865),
                 (40, s88, 912, 6, "9C", "9C", "26", 1805, 4865),
                 (40, s37, 912, 6, "AA", "A5", "34", 1834, 4864),
                 (220, None, 0, 918, "92", "92", "51", 1805, 5633),
                 (220, s88, 0, 918, "92", "92", "51", 1805, 5633),
                 (220, s37, 0, 918, "92", "92", "51", 1805, 5633))
        with tempfile.TemporaryDirectory() as directory:
            for adc2, donor, matrix_reads, other_reads, upper, ram69, ram34, p5, cc3 in cases:
                with self.subTest(adc2=adc2, donor=donor.name if donor else None):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="180", MA17_ADC_CH2=str(adc2),
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH6="247", MA17_ADC_CH7="63",
                                       MA17_TRACE_RAM69="1",
                                       MA17_TRACE_MATRIX_PATH="1")
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7CAE"
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(donor)
                    output = Path(directory) / f"{adc2}_{donor.stem if donor else 'G'}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", "2000", "--stop-ticks", "2400000",
                         "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(donor.read_bytes()).hexdigest()
                                     if donor else None)
                    reads = report["movc_observation"]["reads"]
                    self.assertEqual(sum(row["count"] for row in reads
                                         if 0x7CAE <= int(row["address"], 16) < 0x7D26),
                                     matrix_reads)
                    self.assertEqual(sum(row["count"] for row in reads
                                         if 0x7B46 <= int(row["address"], 16) < 0x7BBE),
                                     other_reads)
                    self.assertEqual(report["engine_ram_observation"]["69"][-1]["after"],
                                     ram69)
                    self.assertEqual(report["engine_ram_observation"]["34"][-1]["after"],
                                     ram34)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], p5)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"], cc3)
                    trace = (output / "emulator-trace.log").read_text()
                    self.assertIn(f"U8C={upper} RAM47=", trace)
                    if donor is None:
                        selected = [line for line in trace.splitlines()
                                    if "[MATRIX-SELECTOR]" in line]
                        writes = [line for line in selected if "PC=3D0C" in line]
                        lookups = [line for line in selected if "PC=3356" in line]
                        self.assertGreaterEqual(len(writes), 400)
                        self.assertGreaterEqual(len(lookups), 200)
                        if adc2 == 40:
                            self.assertGreaterEqual(sum("C=1" in line for line in writes), 400)
                            self.assertGreaterEqual(sum("DPTR=70B6" in line
                                                        for line in lookups), 200)
                        else:
                            self.assertTrue(all("C=0" in line for line in writes))
                            self.assertTrue(all("DPTR=709C" in line for line in lookups))

    def test_721d_movc_threshold_controls_matrix_selector_when_guarded(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        original = REFERENCE.read_bytes()
        self.assertEqual(original[0x721D], 0x21)
        cases = ((220, "27", 0x7B46, "709C", True),
                 (220, "28", 0x7CAE, "70B6", True),
                 (40, "00", 0x7CAE, "70B6", False))
        with tempfile.TemporaryDirectory() as directory:
            for adc2, value, selected_base, pointer, override_reached in cases:
                with self.subTest(adc2=adc2, supplied=value):
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="180", MA17_ADC_CH2=str(adc2),
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH6="247", MA17_ADC_CH7="63",
                                       MA17_TRACE_MATRIX_PATH="1",
                                       MA17_OVERRIDE_MOVC_AT=f"3D01:721D:{value}")
                    output = Path(directory) / f"{adc2}_{value}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", "2000", "--stop-ticks", "2400000",
                         "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(original).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"],
                                     f"3D01:721D:{value}")
                    reads = report["movc_observation"]["reads"]
                    selected = sum(row["count"] for row in reads
                                   if selected_base <= int(row["address"], 16)
                                   < selected_base + 120)
                    self.assertGreater(selected, 800)
                    trace = (output / "emulator-trace.log").read_text()
                    self.assertIn(f"PC=3356", trace)
                    self.assertGreater(sum(f"PC=3356" in line and
                                           f"DPTR={pointer}" in line
                                           for line in trace.splitlines()), 200)
                    marker = f"[MOVC-OVERRIDE] PC=3D01 mapped=721D original=21 supplied={value}"
                    self.assertEqual(marker in trace, override_reached)

    def test_721c_72bd_movc_limits_control_matrix_family(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((REFERENCE, 40, "47E9:721C", "27", 0x7B46, "709C", True),
                 (REFERENCE, 40, "47E9:721C", "28", 0x7CAE, "70B6", False),
                 (REFERENCE, 40, "47F1:72BD", "27", 0x7B46, "709C", True),
                 (REFERENCE, 40, "47F1:72BD", "28", 0x7CAE, "70B6", False),
                 (REFERENCE, 220, "47F1:72BD", "DB", 0x7B46, "709C", True),
                 (REFERENCE, 220, "47F1:72BD", "DC", 0x7CAE, "70B6", False),
                 (s88, 220, "47F1:72BD", "DC", 0x7CAE, "70B6", False))
        with tempfile.TemporaryDirectory() as directory:
            for image, adc2, site, value, base, pointer, threshold_reached in cases:
                with self.subTest(image=image.name, adc2=adc2,
                                  site=site, supplied=value):
                    original = image.read_bytes()
                    self.assertEqual((original[0x721C], original[0x72BD]),
                                     (0x7F, 0x7C))
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="180", MA17_ADC_CH2=str(adc2),
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH6="247", MA17_ADC_CH7="63",
                                       MA17_TRACE_MATRIX_PATH="1",
                                       MA17_OVERRIDE_MOVC_AT=f"{site}:{value}")
                    output = Path(directory) / f"{image.stem}_{adc2}_{site[:4]}_{value}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(image), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm", "2000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(original).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"],
                                     f"{site}:{value}")
                    reads = report["movc_observation"]["reads"]
                    self.assertGreater(sum(row["count"] for row in reads
                                           if base <= int(row["address"], 16)
                                           < base + 120), 400)
                    trace = (output / "emulator-trace.log").read_text()
                    marker = (f"[MOVC-OVERRIDE] PC={site[:4]} mapped={site[5:]} "
                              f"original={original[int(site[5:], 16)]:02X} supplied={value}")
                    self.assertIn(marker, trace)
                    selector = [line for line in trace.splitlines()
                                if "[MATRIX-SELECTOR]" in line and "PC=3356" in line]
                    self.assertGreater(sum(f"DPTR={pointer}" in line
                                           for line in selector), 200)
                    threshold_reads = sum(row["count"] for row in reads
                                          if row["pc"] == "3D01" and
                                          row["address"] == "721D")
                    self.assertEqual(threshold_reads > 400, threshold_reached)

    def test_s88_axis_fraction_skips_second_matrix_interpolation_pair(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        image = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        original = image.read_bytes()
        self.assertEqual(original[0x5342:0x5345], bytes.fromhex("BC 00 04"))
        self.assertEqual(original[0x7B31], 0xAF)
        with tempfile.TemporaryDirectory() as directory:
            for supplied, r4, second_pair in ((None, "00", 12),
                                               ("A8", "E0", 229)):
                with self.subTest(supplied=supplied):
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="180", MA17_ADC_CH2="220",
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH6="247", MA17_ADC_CH7="63",
                                       MA17_TRACE_MATRIX_PATH="1")
                    if supplied:
                        environment["MA17_OVERRIDE_MOVC_AT"] = f"5289:7B31:{supplied}"
                    output = Path(directory) / (supplied or "native")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(image), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm", "2000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(original).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"],
                                     f"5289:7B31:{supplied}" if supplied else None)
                    reads = report["movc_observation"]["reads"]
                    counts = {pc: sum(row["count"] for row in reads
                                      if row["pc"] == pc and
                                      0x7B46 <= int(row["address"], 16) < 0x7BBE)
                              for pc in ("532F", "5333", "534B", "5350")}
                    self.assertEqual(counts, {"532F": 230, "5333": 230,
                                              "534B": second_pair,
                                              "5350": second_pair})
                    trace = (output / "emulator-trace.log").read_text()
                    self.assertGreater(sum("PC=3356" in line and
                                           f"R4={r4}" in line and
                                           "UAE=57" in line
                                           for line in trace.splitlines()), 200)
                    if supplied:
                        self.assertIn("[MOVC-OVERRIDE] PC=5289 mapped=7B31 "
                                      "original=AF supplied=A8", trace)

    def test_7580_and_7581_jointly_explain_s88_upper_ae_at_2000rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cells = ((0x532F, 0x7BB6), (0x5333, 0x7BB7),
                 (0x532F, 0x7BA0), (0x5333, 0x7BA1),
                 (0x534B, 0x7BAF), (0x5350, 0x7BB0),
                 (0x532F, 0x7B46), (0x5333, 0x7B47))
        donor_bytes = s88.read_bytes()
        cell_override = ",".join(f"{pc:04X}:{address:04X}:{donor_bytes[address]:02X}"
                                 for pc, address in cells)
        expected = (("g", REFERENCE, False, False, False, False, "4D", "90", 229),
                    ("7580", REFERENCE, True, False, False, False, "4E", "B0", 229),
                    ("7581", REFERENCE, False, True, False, False, "55", "00", 12),
                    ("both", REFERENCE, True, True, False, False, "57", "00", 12),
                    ("triad", REFERENCE, True, True, True, False, "57", "00", 12),
                    ("four", REFERENCE, True, True, True, True, "57", "00", 12),
                    ("s88", s88, False, False, False, False, "57", "00", 12))
        self.assertEqual(REFERENCE.read_bytes()[0x715A:0x7163],
                         s88.read_bytes()[0x715A:0x7163])
        selected_reports = {}
        with tempfile.TemporaryDirectory() as directory:
            for (name, firmware, use_7580, use_7581, use_cells,
                 use_7b45, ae, r4, second) in expected:
                with self.subTest(case=name):
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="180", MA17_ADC_CH2="220",
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH6="247", MA17_ADC_CH7="63",
                                       MA17_TRACE_UPPER_AE_SOURCE="1",
                                       MA17_TRACE_MATRIX_PATH="1")
                    if use_7580:
                        environment["MA17_OVERRIDE_MOVC_7580"] = "25"
                    if use_7581:
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(s88)
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7581"
                    if use_cells:
                        environment["MA17_OVERRIDE_MOVC_AT"] = cell_override
                    if use_7b45:
                        environment["MA17_OVERRIDE_MOVC_7B45"] = "0D"
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm", "2000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"],
                                     cell_override if use_cells else None)
                    self.assertEqual(report["movc_7b45_override_hex"],
                                     "0D" if use_7b45 else None)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    sources = [line for line in lines
                               if "[UPPER-AE-SOURCE]" in line][-200:]
                    selectors = [line for line in lines
                                 if "[MATRIX-SELECTOR]" in line and
                                 "PC=3356" in line][-200:]
                    self.assertEqual(len(sources), 200)
                    self.assertEqual(len(selectors), 200)
                    self.assertTrue(all(f"A={ae}" in line and "RAM7C=8E" in line
                                        for line in sources))
                    self.assertTrue(all(f"UAE={ae}" in line and f"R4={r4}" in line
                                        for line in selectors))
                    reads = report["movc_observation"]["reads"]
                    for pc in ("534B", "5350"):
                        self.assertEqual(sum(row["count"] for row in reads
                                             if row["pc"] == pc and
                                             0x7B46 <= int(row["address"], 16) < 0x7BBE),
                                         second)
                    if name in ("both", "triad", "four", "s88"):
                        self.assertEqual(report["cc3_observation"]
                                         ["iram14_15_median"], 1597)
                        self.assertEqual(report["engine_ram_observation"]["69"][-1]
                                         ["after"], "87" if name == "both" else "8F")
                        self.assertEqual(report["engine_ram_observation"]["34"][-1]
                                         ["after"], "A8" if name == "both" else "B7")
                        self.assertEqual(report["output_latches"]["P5.0"]
                                         ["median_low_width_ticks"],
                                         1819 if name == "both" else 1818)
                        self.assertEqual(report["cc3_observation"]
                                         ["cc3_pin_model_median_low_width_ticks"],
                                         6377 if name in ("both", "triad") else 6376)
                    if name in ("four", "s88"):
                        selected_reports[name] = report
        for field in ("output_latches", "cc3_observation",
                      "engine_ram_observation", "pc_coverage"):
            self.assertEqual(selected_reports["four"][field],
                             selected_reports["s88"][field])

    def test_four_s88_movc_calibrations_match_selected_reports_at_other_rpms(self):
        emulator = ROOT / "build" / "emu8051-tty"
        if not emulator.exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        donor = s88.read_bytes()
        common = ((0x532F, 0x7B46), (0x5333, 0x7B47),
                  (0x532F, 0x7BA0), (0x5333, 0x7BA1),
                  (0x534B, 0x7BAF), (0x5350, 0x7BB0))
        with tempfile.TemporaryDirectory() as directory:
            for rpm, pair in ((1500, ((0x532F, 0x7BB5), (0x5333, 0x7BB6))),
                              (3000, ((0x532F, 0x7BB9), (0x5333, 0x7BBA)))):
                cells = common + pair
                override = ",".join(f"{pc:04X}:{address:04X}:{donor[address]:02X}"
                                    for pc, address in cells)
                reports = {}
                for name, firmware in (("four", REFERENCE), ("s88", s88)):
                    with self.subTest(rpm=rpm, case=name):
                        environment = {key: val for key, val in os.environ.items()
                                       if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                              "MA17_TRACE_", "MA17_P4_"))}
                        environment.update(MA17_ADC_CH0="180", MA17_ADC_CH2="220",
                                           MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                           MA17_ADC_CH6="247", MA17_ADC_CH7="63")
                        if name == "four":
                            environment.update(
                                MA17_OVERRIDE_MOVC_7580="25",
                                MA17_OVERRIDE_MOVC_7B45="0D",
                                MA17_OVERRIDE_MOVC_MATRIX_ROM=str(s88),
                                MA17_OVERRIDE_MOVC_MATRIX_BASE="7581",
                                MA17_OVERRIDE_MOVC_AT=override)
                        output = Path(directory) / str(rpm) / name
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--trace-movc",
                             "--no-kline-inject", "--crank-immediate",
                             "--rpm", str(rpm), "--stop-ticks", "2400000",
                             "--seconds", "20", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertEqual(report["emulator_sha256"],
                                         hashlib.sha256(emulator.read_bytes()).hexdigest())
                        self.assertEqual(report["movc_override_at_hex"],
                                         override if name == "four" else None)
                        reached = {int(row["mapped"], 16) for row in
                                   report["movc_observation"]["reads"]
                                   if 0x7B46 <= int(row["mapped"], 16) < 0x7BBE}
                        self.assertEqual(reached, {address for _, address in cells})
                        reports[name] = report
                for field in ("output_latches", "cc3_observation",
                              "engine_ram_observation", "pc_coverage"):
                    self.assertEqual(reports["four"][field], reports["s88"][field],
                                     (rpm, field))

    def test_7cae_branch_needs_7b46_startup_cells_for_matching_ram_history(self):
        emulator = ROOT / "build" / "emu8051-tty"
        if not emulator.exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        donor = s88.read_bytes()
        main = ((0x532F, 0x7CF9), (0x532F, 0x7D0F),
                (0x5333, 0x7CFA), (0x5333, 0x7D10),
                (0x534B, 0x7D08), (0x534B, 0x7D1E),
                (0x5350, 0x7D09), (0x5350, 0x7D1F))
        startup = ((0x532F, 0x7B46), (0x532F, 0x7B91),
                   (0x5333, 0x7B47), (0x5333, 0x7B92),
                   (0x534B, 0x7BA0), (0x5350, 0x7BA1))
        reports = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, firmware, cells in (("baseline", REFERENCE, ()),
                                          ("main", REFERENCE, main),
                                          ("full", REFERENCE, main + startup),
                                          ("s88", s88, ())):
                with self.subTest(case=name):
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="180", MA17_ADC_CH2="40",
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH6="247", MA17_ADC_CH7="63")
                    if name not in ("baseline", "s88"):
                        environment.update(
                            MA17_OVERRIDE_MOVC_7580="25",
                            MA17_OVERRIDE_MOVC_7B45="0D",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(s88),
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="7581",
                            MA17_OVERRIDE_MOVC_AT=",".join(
                                f"{pc:04X}:{address:04X}:{donor[address]:02X}"
                                for pc, address in cells))
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm", "2000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertEqual(report["emulator_sha256"],
                                     hashlib.sha256(emulator.read_bytes()).hexdigest())
                    reports[name] = report
        for name in ("baseline", "main", "full", "s88"):
            reads = reports[name]["movc_observation"]["reads"]
            self.assertEqual(sum(row["count"] for row in reads
                                 if 0x7CAE <= int(row["mapped"], 16) < 0x7D26),
                             912)
            self.assertEqual(sum(row["count"] for row in reads
                                 if 0x7B46 <= int(row["mapped"], 16) < 0x7BBE),
                             6)
        self.assertEqual(reports["baseline"]["engine_ram_observation"]["69"][-1]
                         ["after"], "94")
        self.assertEqual(reports["main"]["engine_ram_observation"]["69"][-1]
                         ["after"], "9B")
        for field in ("output_latches", "cc3_observation", "pc_coverage"):
            self.assertEqual(reports["main"][field], reports["s88"][field])
        self.assertEqual([key for key in reports["main"]["engine_ram_observation"]
                          if reports["main"]["engine_ram_observation"][key] !=
                          reports["s88"]["engine_ram_observation"][key]], ["A4"])
        for field in ("output_latches", "cc3_observation",
                      "engine_ram_observation", "pc_coverage"):
            self.assertEqual(reports["full"][field], reports["s88"][field])

    def test_7cae_and_startup_donors_repeat_at_1500_and_3000rpm(self):
        emulator = ROOT / "build" / "emu8051-tty"
        if not emulator.exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        donor = s88.read_bytes()
        fields = ("output_latches", "cc3_observation",
                  "engine_ram_observation", "pc_coverage")
        with tempfile.TemporaryDirectory() as directory:
            for rpm in (1500, 3000):
                reports = {}
                cells = ()
                for name, firmware in (("three", REFERENCE),
                                       ("full", REFERENCE), ("s88", s88)):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="180", MA17_ADC_CH2="40",
                                       MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                                       MA17_ADC_CH6="247", MA17_ADC_CH7="63")
                    if name != "s88":
                        environment.update(
                            MA17_OVERRIDE_MOVC_7580="25",
                            MA17_OVERRIDE_MOVC_7B45="0D",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(s88),
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="7581")
                    if name == "full":
                        environment["MA17_OVERRIDE_MOVC_AT"] = ",".join(
                            f"{pc:04X}:{address:04X}:{donor[address]:02X}"
                            for pc, address in cells)
                    output = Path(directory) / f"{rpm}_{name}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm", str(rpm),
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertEqual(report["emulator_sha256"],
                                     hashlib.sha256(emulator.read_bytes()).hexdigest())
                    reports[name] = report
                    if name == "three":
                        reads = report["movc_observation"]["reads"]
                        main = [row for row in reads
                                if 0x7CAE <= int(row["mapped"], 16) < 0x7D26]
                        startup = [row for row in reads
                                   if 0x7B46 <= int(row["mapped"], 16) < 0x7BBE]
                        self.assertEqual(sum(row["count"] for row in main),
                                         480 if rpm == 1500 else 912)
                        self.assertEqual(sum(row["count"] for row in startup), 6)
                        self.assertEqual(len(startup), 6)
                        cells = tuple((int(row["pc"], 16), int(row["mapped"], 16))
                                      for row in main + startup)
                self.assertNotEqual(reports["three"]["engine_ram_observation"],
                                    reports["s88"]["engine_ram_observation"])
                for field in fields:
                    self.assertEqual(reports["full"][field], reports["s88"][field],
                                     (rpm, field))

    def test_a_code_20_byte_regions_have_separate_consumers_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        original_bytes = REFERENCE.read_bytes()
        donor_bytes = donor.read_bytes()
        for start in (0x7895, 0x78BD, 0x7925):
            self.assertTrue(all((changed - native) & 0xFF == 0x28
                                for native, changed in zip(
                                    original_bytes[start:start + 20],
                                    donor_bytes[start:start + 20])))
        cases = ((None, None, "5C", "61"),
                 ("7895", "7080", "5C", "89"),
                 ("78BD", "7084", "5C", "61"),
                 ("7925", "7064", "84", "61"))
        with tempfile.TemporaryDirectory() as directory:
            for base, slot, iram6e, xram01 in cases:
                with self.subTest(base=base):
                    environment = {
                        key: value for key, value in os.environ.items()
                        if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                               "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(
                        MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                        MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                        MA17_ADC_CH7="63", MA17_TRACE_78XX_PATH="1")
                    if base:
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE=base,
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor))
                    output = Path(directory) / (base or "control")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1500",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(original_bytes).hexdigest())
                    self.assertEqual(report["movc_matrix_size"],
                                     20 if base else None)
                    self.assertEqual(report["movc_matrix_pointer_slot_hex"], slot)
                    reads = report["movc_observation"]["reads"]
                    for start, count in ((0x7895, 1780), (0x78BD, 0),
                                         (0x7925, 1780)):
                        self.assertEqual(sum(row["count"] for row in reads
                                             if start <= int(row["address"], 16)
                                             < start + 20), count)
                    trace = (output / "emulator-trace.log").read_text()
                    for pc, expected in (("3DC7", iram6e),
                                         ("3E33", xram01)):
                        rows = [line for line in trace.splitlines()
                                if line.startswith("[78XX-PATH]") and
                                f"PC={pc}" in line]
                        self.assertTrue(rows)
                        self.assertIn(f"A={expected}", rows[-1])
                    if base in (None, "7895"):
                        consumers = [line for line in trace.splitlines()
                                     if line.startswith("[78XX-CONSUMER]")]
                        at_read = [line for line in consumers
                                   if "PC=1CB7" in line]
                        at_result = [line for line in consumers
                                     if "PC=1CDF" in line]
                        self.assertGreater(len(at_read), 200)
                        self.assertIn(f"X01={xram01} XFB=FF RAM7A=00 "
                                      "RAM7B=78", at_read[-1])
                        self.assertIn("RAM7A=00 RAM7B=78 A=00 B=00",
                                      at_result[-1])
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1767)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     5137)

    def test_78bd_natural_adc5_branch_and_donor_reach_f801(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        original_hash = hashlib.sha256(REFERENCE.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            for use_donor, expected in ((False, "72"), (True, "9A")):
                with self.subTest(use_donor=use_donor):
                    environment = {
                        key: value for key, value in os.environ.items()
                        if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                               "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                        MA17_ADC_CH3="4", MA17_ADC_CH5="200",
                        MA17_ADC_CH7="63", MA17_TRACE_78XX_PATH="1")
                    if use_donor:
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="78BD",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor))
                    output = Path(directory) / str(use_donor)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"], original_hash)
                    self.assertEqual(report["movc_matrix_pointer_slot_hex"],
                                     "7084" if use_donor else None)
                    reads = report["movc_observation"]["reads"]
                    self.assertEqual(sum(row["count"] for row in reads
                                         if 0x78BD <= int(row["mapped"], 16)
                                         < 0x78D1), 1736)
                    trace = (output / "emulator-trace.log").read_text()
                    branch = [line for line in trace.splitlines()
                              if line.startswith("[78XX-PATH]") and
                              "PC=3E1A" in line]
                    self.assertEqual(len(branch), 369)
                    writes = [line for line in trace.splitlines()
                              if line.startswith("[78XX-PATH]") and
                              "PC=3E33" in line]
                    self.assertEqual(len(writes), 429)
                    self.assertIn(f"A={expected}", writes[-1])
                    consumers = [line for line in trace.splitlines()
                                 if line.startswith("[78XX-CONSUMER]") and
                                 "PC=1CB7" in line]
                    self.assertGreater(len(consumers), 200)
                    self.assertIn(f"X01={expected} XFB=FF RAM7A=00",
                                  consumers[-1])
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1861)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     2372)

    def test_78bd_donor_reaches_nonzero_iram7a_consumer_after_tps_release(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        reference_hash = hashlib.sha256(REFERENCE.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            for use_donor, expected_x01, expected_b, expected_pulses, \
                    candidate, published in (
                    (False, "72", "0C", 129, "E2", "E2"),
                    (True, "9A", "10", 119, "5A", "00")):
                with self.subTest(use_donor=use_donor):
                    environment = {
                        key: value for key, value in os.environ.items()
                        if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                               "MA17_TRACE_", "MA17_P4_"))}
                    for channel, value in enumerate(
                            (180, 130, 140, 4, 90, 200, 247, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment.update(
                        MA17_ADC10_STEP_CH0="3274600:160",
                        MA17_ADC10_STEP_CH6="3274600:380",
                        MA17_TRACE_78XX_PATH="1")
                    if use_donor:
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="78BD",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor))
                    output = Path(directory) / str(use_donor)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "4000000", "--seconds", "25",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"], reference_hash)
                    reads = report["movc_observation"]["reads"]
                    self.assertEqual(sum(row["count"] for row in reads
                                         if 0x78BD <= int(row["mapped"], 16)
                                         < 0x78D1), 2988)
                    trace = (output / "emulator-trace.log").read_text()
                    consumers = [line for line in trace.splitlines()
                                 if line.startswith("[78XX-CONSUMER]")
                                 and "PC=1CB7" in line]
                    self.assertEqual(len(consumers), 386)
                    self.assertEqual(sum("RAM7A=00" not in line
                                         for line in consumers), 69)
                    self.assertIn(f"X01={expected_x01} XFB=FF "
                                  f"RAM7A=8C RAM7B=66", consumers[-1])
                    final_result = [line for line in trace.splitlines()
                                    if line.startswith("[78XX-CONSUMER]")
                                    and "PC=1CDF" in line]
                    self.assertIn(f"B={expected_b}", final_result[-1])
                    for pc, value in (("1EA9", candidate),
                                      ("1ED3", published)):
                        rows = [line for line in trace.splitlines()
                                if line.startswith("[78XX-MATH]")
                                and f"PC={pc}" in line
                                and 3296000 <= int(line.split("tick=")[1]
                                                   .split()[0]) < 3297000]
                        self.assertEqual(len(rows), 1, (pc, rows))
                        self.assertIn(f"R2={value} R3=00", rows[0])
                        if use_donor and pc == "1ED3":
                            self.assertIn("R4=00", rows[0])
                            self.assertIn("X08=61 XEF=00", rows[0])
                    entries = [line for line in trace.splitlines()
                               if line.startswith("[CC3-ENTRY]")]
                    self.assertEqual(len(entries), 129)
                    self.assertEqual(sum("IRAM14_15=0000" in line
                                         for line in entries[105:115]),
                                     10 if use_donor else 0)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_low_starts"],
                                     expected_pulses)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1921)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     4464)

    def test_7895_donor_reduces_cc3_events_after_tps_release(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        reference_hash = hashlib.sha256(REFERENCE.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            for use_donor, x01, pulses, zero_schedules, candidate, \
                    at_107, at_119 in (
                    (False, "72", 127, 2, "CA", "00CA", "0141"),
                    (True, "9A", 115, 14, "44", "0000", "00D5")):
                with self.subTest(use_donor=use_donor):
                    environment = {
                        key: value for key, value in os.environ.items()
                        if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                               "MA17_TRACE_", "MA17_P4_"))}
                    for channel, value in enumerate(
                            (180, 130, 140, 34, 90, 110, 247, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment.update(
                        MA17_ADC10_STEP_CH0="3274600:160",
                        MA17_ADC10_STEP_CH6="3274600:380",
                        MA17_TRACE_78XX_PATH="1")
                    if use_donor:
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="7895",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor))
                    output = Path(directory) / str(use_donor)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "4000000", "--seconds", "25",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"], reference_hash)
                    reads = report["movc_observation"]["reads"]
                    self.assertEqual(sum(row["count"] for row in reads
                                         if 0x7895 <= int(row["mapped"], 16)
                                         < 0x78A9), 3160)
                    trace = (output / "emulator-trace.log").read_text()
                    consumers = [line for line in trace.splitlines()
                                 if line.startswith("[78XX-CONSUMER]")
                                 and "PC=1CB7" in line]
                    self.assertEqual(len(consumers), 386)
                    self.assertEqual(sum("RAM7A=00" not in line
                                         for line in consumers), 69)
                    self.assertIn(f"X01={x01} XFB=FF RAM7A=8C",
                                  consumers[-1])
                    entries = [line for line in trace.splitlines()
                               if line.startswith("[CC3-ENTRY]")]
                    self.assertEqual(len(entries), 129)
                    self.assertEqual(sum("IRAM14_15=0000" in line
                                         for line in entries[105:]),
                                     zero_schedules)
                    self.assertIn(f"IRAM14_15={at_107}", entries[107])
                    self.assertIn(f"IRAM14_15={at_119}", entries[119])
                    candidate_rows = [line for line in trace.splitlines()
                                      if line.startswith("[78XX-MATH]")
                                      and "PC=1EA9" in line
                                      and 3367000 <= int(line.split("tick=")[1]
                                                         .split()[0]) < 3368000]
                    self.assertEqual(len(candidate_rows), 1)
                    self.assertIn(f"R2={candidate} R3=00",
                                  candidate_rows[0])
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_low_starts"], pulses)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     4404)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1921)

    def test_current_adc_path_blocks_746c_when_ram22_bit5_is_set(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            environment = {
                key: value for key, value in os.environ.items()
                if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                       "MA17_TRACE_", "MA17_P4_"))}
            environment.update(MA17_ADC_CH0="120", MA17_ADC_CH6="180",
                               MA17_ADC_CH7="63", MA17_TRACE_RAM4D_PATH="1")
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--trace-movc", "--no-kline-inject", "--crank-immediate",
                 "--rpm", "1000", "--stop-ticks", "2400000",
                 "--seconds", "20", "--output-dir", directory],
                capture_output=True, text=True, env=environment,
                timeout=30, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((Path(directory) / "execution.json").read_text())
            self.assertEqual(report["firmware_sha256"],
                             hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
            self.assertEqual(report["emulator_sha256"], hashlib.sha256(
                (ROOT / "build" / "emu8051-tty").read_bytes()).hexdigest())
            reads = report["movc_observation"]["reads"]
            self.assertFalse(any(0x746C <= int(row["address"], 16) < 0x7476
                                 for row in reads))
            lines = [line for line in
                     (Path(directory) / "emulator-trace.log").read_text().splitlines()
                     if line.startswith("[RAM4D-CURVE-GATE]")]
            at_mask = [line for line in lines if "PC=220C" in line]
            self.assertGreater(len(at_mask), 200)
            self.assertTrue(all(int(line.split("RAM22=")[1][:2], 16) & 0x20
                                for line in at_mask))
            self.assertFalse(any("PC=4997" in line for line in lines))

    def test_753e_first_cell_donor_changes_xram_f806(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        original = REFERENCE.read_bytes()
        changed_bytes = donor.read_bytes()
        self.assertEqual(original[0x753E:0x7548], bytes(10))
        self.assertEqual(changed_bytes[0x753E:0x7548],
                         bytes([0x22]) + bytes(9))
        with tempfile.TemporaryDirectory() as directory:
            for changed in (False, True):
                environment = {
                    key: value for key, value in os.environ.items()
                    if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                           "MA17_TRACE_", "MA17_P4_"))}
                environment.update(
                    MA17_ADC_CH0="120", MA17_ADC_CH6="95",
                    MA17_ADC_CH3="4", MA17_ADC_CH5="40",
                    MA17_ADC_CH7="63", MA17_TRACE_XRAM_F806="1")
                if changed:
                    environment.update(
                        MA17_OVERRIDE_MOVC_MATRIX_BASE="753E",
                        MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor))
                output = Path(directory) / str(changed)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "1000", "--stop-ticks", "2400000",
                     "--seconds", "20", "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(original).hexdigest())
                reads = report["movc_observation"]["reads"]
                self.assertGreater(sum(row["count"] for row in reads
                                       if row["address"] == "753E"), 200)
                writes = [line for line in
                          (output / "emulator-trace.log").read_text().splitlines()
                          if line.startswith("[F806-WRITE]") and
                          "PC=47E0" in line]
                self.assertEqual(writes[0].split("value=")[1], "FF->00")
                self.assertEqual([line.split("value=")[1] for line in writes[1:]],
                                 ["00->22"] if changed else [])
                xram_reads = [line for line in
                              (output / "emulator-trace.log").read_text().splitlines()
                              if line.startswith("[F806-READ]")]
                self.assertEqual(xram_reads,
                                 ["[F806-READ] PC=55A2 value=55",
                                  "[F806-READ] PC=55A2 value=AA"])
                self.assertEqual(report["output_latches"]["P5.0"]
                                 ["median_low_width_ticks"], 1861)

    def test_7462_mode_two_donor_changes_iram4d(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        with tempfile.TemporaryDirectory() as directory:
            for changed in (False, True):
                environment = {
                    key: value for key, value in os.environ.items()
                    if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                           "MA17_TRACE_", "MA17_P4_"))}
                environment.update(MA17_OVERRIDE_RAM57="2",
                                   MA17_ADC_CH0="120", MA17_ADC_CH6="95",
                                   MA17_ADC_CH7="63")
                if changed:
                    environment.update(
                        MA17_OVERRIDE_MOVC_MATRIX_BASE="7462",
                        MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor))
                output = Path(directory) / str(changed)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "1000", "--stop-ticks", "2400000",
                     "--seconds", "20", "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                self.assertEqual(report["ram57_override_hex"], "2")
                self.assertEqual(report["movc_matrix_base_hex"],
                                 "7462" if changed else None)
                reads = report["movc_observation"]["reads"]
                self.assertEqual(sum(row["count"] for row in reads
                                     if 0x7462 <= int(row["address"], 16)
                                     < 0x746C), 394)
                changes = report["engine_ram_observation"]["4D"]
                self.assertEqual(changes[1]["after"], "3B" if changed else "21")
                self.assertEqual(changes[1]["source_pc"], "49AD")
                self.assertEqual(report["output_latches"]["P5.0"]
                                 ["median_low_width_ticks"], 5908)
                self.assertEqual(report["cc3_observation"]
                                 ["cc3_pin_model_median_low_width_ticks"], 5677)

    def test_7939_donor_reaches_iram5b_only_in_unsaturated_rows(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        original = REFERENCE.read_bytes()
        changed_bytes = donor.read_bytes()
        self.assertEqual([i for i in range(20)
                          if original[0x7939 + i] != changed_bytes[0x7939 + i]],
                         list(range(5)))
        with tempfile.TemporaryDirectory() as directory:
            for changed in (False, True):
                environment = {
                    key: value for key, value in os.environ.items()
                    if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                           "MA17_TRACE_", "MA17_P4_"))}
                environment.update(
                    MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                    MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                    MA17_ADC_CH7="63", MA17_TRACE_78XX_PATH="1")
                if changed:
                    environment.update(
                        MA17_OVERRIDE_MOVC_MATRIX_BASE="7939",
                        MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor))
                output = Path(directory) / str(changed)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "1500", "--stop-ticks", "2400000",
                     "--seconds", "20", "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(original).hexdigest())
                reads = report["movc_observation"]["reads"]
                self.assertGreater(sum(row["count"] for row in reads
                                       if 0x7939 <= int(row["address"], 16)
                                       < 0x794D), 400)
                rows = [line for line in
                        (output / "emulator-trace.log").read_text().splitlines()
                        if line.startswith("[78XX-PATH]") and "PC=3DDC" in line]
                self.assertIn(f"A={'47' if changed else '1F'}", rows[0])
                self.assertIn("A=52", rows[-1])
                self.assertEqual(report["output_latches"]["P5.0"]
                                 ["median_low_width_ticks"], 1767)

    def test_7939_ram5b_consumers_are_gated_at_coolant_four(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        with tempfile.TemporaryDirectory() as directory:
            for changed in (False, True):
                with self.subTest(changed=changed):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    for channel, value in enumerate((180, 130, 100, 4,
                                                     90, 40, 247, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment["MA17_TRACE_RAM5B_GATE"] = "1"
                    environment["MA17_TRACE_78XX_PATH"] = "1"
                    if changed:
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(donor)
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7939"
                    output = Path(directory) / str(changed)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1500",
                         "--stop-ticks", "4000000", "--seconds", "25",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_size"],
                                     20 if changed else None)
                    self.assertTrue(report["ram5b_gate_trace_enabled"])
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"], 5495)
                    log = (output / "emulator-trace.log").read_text().splitlines()
                    gate = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9_]+)",
                                            line)) for line in log
                            if line.startswith("[RAM5B-GATE]")]
                    at_1840 = [row for row in gate if row["PC"] == "1840"]
                    at_18b2 = [row for row in gate if row["PC"] == "18B2"]
                    self.assertEqual(len(at_1840), 115)
                    self.assertTrue(all(int(row["RAM2C"], 16) & 0x80 == 0
                                        for row in at_1840))
                    self.assertEqual(len(at_18b2), 1)
                    self.assertTrue(int(at_18b2[0]["RAM2C"], 16) & 0x10)
                    self.assertLess(int(at_1840[-1]["tick"]),
                                    int(at_18b2[0]["tick"]))
                    self.assertFalse(any(row["PC"] in ("1843", "1846", "1863",
                                                        "18B5") for row in gate))
                    values = [dict(re.findall(r"([A-Za-z0-9_]+)=([A-Za-z0-9_]+)",
                                              line)) for line in log
                              if line.startswith("[78XX-PATH]") and "PC=3DDC" in line]
                    self.assertEqual(values[0]["A"], "47" if changed else "1F")
                    self.assertEqual(values[-1]["A"], "52")

    def test_7939_ram5b_read_mediates_cc3_when_factor_gate_is_open(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        cases = (("control", False, None, "47", 2245, "F4"),
                 ("donor", True, None, "5B", 2265, "F9"),
                 ("control_to_5b", False, "5B", "47", 2265, "F9"),
                 ("donor_to_47", True, "47", "5B", 2245, "F4"))
        with tempfile.TemporaryDirectory() as directory:
            for name, changed, supplied, ram5b, cc3, f80c in cases:
                with self.subTest(name=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    for channel, value in enumerate((40, 130, 100, 200,
                                                     90, 40, 95, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment.update({
                        "MA17_TRACE_RAM5B_GATE": "1",
                        "MA17_OVERRIDE_MOVC_AT": "532F:742D:00,5333:742E:00"})
                    if changed:
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(donor)
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7939"
                    if supplied:
                        environment["MA17_OVERRIDE_RAM5B_READ"] = supplied
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "2000",
                         "--stop-ticks", "4000000", "--seconds", "25",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"],
                                     "532F:742D:00,5333:742E:00")
                    self.assertEqual(report["ram5b_read_override_hex"], supplied)
                    self.assertEqual(report["movc_matrix_size"],
                                     20 if changed else None)
                    if changed:
                        self.assertEqual(report["movc_matrix_donor_sha256"],
                                         hashlib.sha256(donor.read_bytes()).hexdigest())
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"], cc3)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1789)
                    self.assertEqual(report["adaptation_xram_observation"]
                                     ["F80C"][-1]["after"], f80c)
                    log = (output / "emulator-trace.log").read_text()
                    self.assertIn("[MOVC-OVERRIDE] PC=532F mapped=742D", log)
                    self.assertIn("[MOVC-OVERRIDE] PC=5333 mapped=742E", log)
                    self.assertEqual(len(re.findall(
                        rf"\[RAM5B-GATE\].*PC=1863 .*RAM5B={ram5b}", log)), 1)
                    if supplied:
                        self.assertIn(f"[RAM5B-READ-OVERRIDE] PC=1866 "
                                      f"original={ram5b} supplied={supplied}", log)
                    else:
                        self.assertNotIn("[RAM5B-READ-OVERRIDE]", log)

    def test_7939_natural_air_input_boundary_mediates_f80c(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        cases = ((128, False, None, "1A", None, None),
                 (129, False, None, "0A", "1E", "91"),
                 (140, False, None, "0A", "1E", "91"),
                 (140, True, None, "0A", "41", "9A"),
                 (140, False, "41", "0A", "1E", "9A"),
                 (140, True, "1E", "0A", "41", "91"))
        with tempfile.TemporaryDirectory() as directory:
            for adc2, changed, supplied, flags, ram5b, f80c in cases:
                with self.subTest(adc2=adc2, changed=changed,
                                  supplied=supplied):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    for channel, value in enumerate((40, 130, adc2, 34,
                                                     90, 40, 95, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment.update({"MA17_TRACE_RAM5B_GATE": "1",
                                        "MA17_TRACE_7939_INDEX": "1",
                                        "MA17_TRACE_LAMBDA": "1"})
                    if changed:
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(donor)
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7939"
                    if supplied:
                        environment["MA17_OVERRIDE_RAM5B_READ"] = supplied
                    output = Path(directory) / f"{adc2}_{changed}_{supplied}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "4000000", "--seconds", "25",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertIsNone(report["movc_override_at_hex"])
                    self.assertEqual(report["movc_matrix_size"],
                                     20 if changed else None)
                    self.assertEqual(report["ram5b_read_override_hex"], supplied)
                    self.assertTrue(report["matrix_7939_index_trace_enabled"])
                    log = (output / "emulator-trace.log").read_text()
                    at_18b2 = re.findall(
                        r"^\[RAM5B-GATE\].*PC=18B2 RAM2C=([0-9A-F]{2})",
                        log, re.M)
                    self.assertEqual(at_18b2, [flags])
                    at_1863 = re.findall(
                        r"^\[RAM5B-GATE\].*PC=1863 .*RAM5B=([0-9A-F]{2})",
                        log, re.M)
                    self.assertEqual(at_1863, [] if ram5b is None else [ram5b])
                    at_1810 = [line for line in log.splitlines()
                               if line.startswith("[LAMBDA-GATE]")
                               and "PC=1810" in line]
                    self.assertIn(f"RAM62={adc2:02X}", at_1810[-1])
                    self.assertIn("RAM63=22", at_1810[-1])
                    if f80c:
                        self.assertEqual(report["adaptation_xram_observation"]
                                         ["F80C"][-1]["after"], f80c)
                    if adc2 == 140:
                        writers = [line for line in log.splitlines()
                                   if line.startswith("[7939-INDEX]")
                                   and "PC=3DDC " in line
                                   and int(line.split("tick=")[1]
                                               .split()[0]) < 3274617]
                        self.assertTrue(writers)
                        self.assertIn(
                            "R2=3F R3=43 R4=80 R5=00 R6=40 A=41"
                            if changed else
                            "R2=17 R3=25 R4=80 R5=00 R6=40 A=1E",
                            writers[-1])
                        self.assertEqual(report["cc3_observation"]
                                         ["cc3_pin_model_median_low_width_ticks"],
                                         2541)
                        consumed = supplied or ("41" if changed else "1E")
                        r4, r5, diagnostic = {
                            "1E": ("C0", "03", "87"),
                            "41": ("20", "08", "90"),
                        }[consumed]
                        for pc in ("18D9", "1958", "199A", "19D0"):
                            path = [line for line in log.splitlines()
                                    if line.startswith("[RAM5B-GATE]")
                                    and f"PC={pc} " in line
                                    and 3274600 <= int(line.split("tick=")[1]
                                                        .split()[0]) <= 3274700]
                            self.assertEqual(len(path), 1, (pc, path))
                            self.assertIn(f"R4={r4} R5={r5}", path[0])
                            if pc in ("199A", "19D0"):
                                self.assertIn(f"R6={r4} R7={r5}", path[0])
                            if pc == "19D0":
                                self.assertIn(f"A={diagnostic}", path[0])
                    if supplied:
                        self.assertIn(f"[RAM5B-READ-OVERRIDE] PC=1866 "
                                      f"original={ram5b} supplied={supplied}", log)

    @unittest.skipUnless(os.environ.get("MA17_RUN_SLOW") == "1",
                         "set MA17_RUN_SLOW=1 for the 12M-tick 7939h effect")
    def test_7939_natural_gate_reaches_late_cc3_through_ram5b(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        cases = ((False, None, 2726.5, 11528101),
                 (True, None, 2762.5, 10924151),
                 (False, "41", 2762.5, 10924151),
                 (True, "1E", 2726.5, 11528101))
        schedules = {}
        with tempfile.TemporaryDirectory() as directory:
            for changed, supplied, width, ff_tick in cases:
                with self.subTest(changed=changed, supplied=supplied):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    for channel, value in enumerate((40, 130, 140, 34,
                                                     90, 40, 95, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment["MA17_TRACE_RAM5B_GATE"] = "1"
                    if changed:
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(donor)
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7939"
                    if supplied:
                        environment["MA17_OVERRIDE_RAM5B_READ"] = supplied
                    output = Path(directory) / f"{changed}_{supplied}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "12000000", "--seconds", "75",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=90, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["stop_ticks_observed"], 12000000)
                    self.assertEqual(report["movc_matrix_size"],
                                     20 if changed else None)
                    self.assertEqual(report["ram5b_read_override_hex"], supplied)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"], width)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1861)
                    f80c = report["adaptation_xram_observation"]["F80C"]
                    self.assertEqual(f80c[-1]["after"], "FF")
                    self.assertEqual(next(row["tick"] for row in f80c
                                          if row["after"] == "FF"), ff_tick)
                    log = (output / "emulator-trace.log").read_text()
                    self.assertEqual(len(re.findall(
                        r"\[RAM5B-GATE\].*PC=1863 ", log)), 1)
                    schedules[(changed, supplied)] = [
                        int(value, 16) for value in re.findall(
                            r"\[CC3-ENTRY\].*IRAM14_15=([0-9A-F]{4})", log)]
        control = schedules[(False, None)]
        changed = schedules[(True, None)]
        self.assertEqual(len(control), 200)
        self.assertEqual(control[:104], changed[:104])
        self.assertEqual(Counter(b - a for a, b in zip(control[104:],
                                                       changed[104:])),
                         {9: 38, 10: 58})
        self.assertEqual(changed, schedules[(False, "41")])
        self.assertEqual(control, schedules[(True, "1E")])

    @unittest.skipUnless(os.environ.get("MA17_RUN_SLOW") == "1",
                         "set MA17_RUN_SLOW=1 for the 7569h TPS selector")
    def test_iram6f_segment_7569_is_selected_in_corrected_tps_states(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for adc0, adc6, selected in ((40, 180, False),
                                         (40, 216, False),
                                         (40, 217, True),
                                         (40, 220, True),
                                         (180, 247, True)):
                with self.subTest(adc0=adc0, adc6=adc6):
                    environment = {
                        key: value for key, value in os.environ.items()
                        if not key.startswith(("MA17_ADC_CH", "MA17_OVERRIDE_",
                                               "MA17_TRACE_"))
                        and key != "MA17_P4_6_FORCE_LOW"}
                    for channel, value in enumerate((adc0, 130, 140, 34,
                                                     90, 40, adc6, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment["MA17_TRACE_TPS_AFTER_TICK"] = "3000000"
                    if adc6 in (216, 217):
                        environment["MA17_TRACE_MATRIX_PATH"] = "1"
                    output = Path(directory) / f"{adc0}_{adc6}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "4000000", "--seconds", "25",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    log = (output / "emulator-trace.log").read_text()
                    tps = [line for line in log.splitlines()
                           if line.startswith("[TPS-FLOW]") and "PC=115F " in line]
                    self.assertTrue(tps)
                    self.assertIn(f"R4={adc6:02X}", tps[-1])
                    flag = int(re.search(r"RAM2E=([0-9A-F]{2})", tps[-1]).group(1), 16)
                    self.assertEqual(bool(flag & 0x40), selected)
                    if adc6 in (216, 217):
                        matrix = [line for line in log.splitlines()
                                  if line.startswith("[MATRIX-PATH]")
                                  and "PC=137B " in line]
                        self.assertTrue(matrix)
                        self.assertIn("A=" + ("B2 B=E0" if selected else "AE B=00"),
                                      matrix[-1])
                        self.assertIn("pc=532F opcode=93 dptr=" +
                                      ("7617" if selected else "7581") +
                                      " acc=" + ("03" if selected else "99") +
                                      " address=761A", log)
                        self.assertEqual("pc=534B opcode=93 dptr=7617" in log,
                                         selected)
                    reads = {address: next((line for line in log.splitlines()
                                           if line.startswith("[MOVC-SUMMARY] pc=527D ")
                                           and f"address={address} " in line), None)
                             for address in ("755C", "7569")}
                    self.assertIsNotNone(reads["755C"])
                    normal_count = int(re.search(r"count=(\d+)", reads["755C"]).group(1))
                    if selected:
                        self.assertEqual(normal_count, 1)
                        self.assertIsNotNone(reads["7569"])
                        self.assertGreaterEqual(int(re.search(
                            r"count=(\d+)", reads["7569"]).group(1)), 300)
                        self.assertIn("address=756E", log)
                        self.assertIn("address=756F", log)
                    else:
                        self.assertGreaterEqual(normal_count, 300)
                        self.assertIsNone(reads["7569"])

    @unittest.skipUnless(os.environ.get("MA17_RUN_SLOW") == "1",
                         "set MA17_RUN_SLOW=1 for the 7939h RPM/TPS grid")
    def test_7939_native_axis_states_and_direct_byte_bypass(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        cases = ((750, 40, 95, "80", "00", "00", "19", "41", True),
                 (1500, 40, 95, "80", "01", "40", "34", "48", False),
                 (1000, 120, 95, "00", "00", "40", "9B", "9B", True),
                 (1000, 40, 180, "90", "04", "40", "3E", "4B", True),
                 (1000, 120, 180, "90", "04", "40", "3E", "4B", True),
                 (1000, 180, 247, "C0", "0C", "40", "52", "52", True))
        with tempfile.TemporaryDirectory() as directory:
            for rpm, tps0, tps6, r4, r5, r6, g_value, a_value, called in cases:
                for changed in (False, True):
                    with self.subTest(rpm=rpm, tps0=tps0, tps6=tps6,
                                      changed=changed):
                        environment = {
                            key: value for key, value in os.environ.items()
                            if not key.startswith(("MA17_ADC_CH",
                                                   "MA17_OVERRIDE_",
                                                   "MA17_TRACE_"))}
                        for channel, value in enumerate((tps0, 130, 140, 34,
                                                         90, 40, tps6, 63)):
                            environment[f"MA17_ADC_CH{channel}"] = str(value)
                        environment["MA17_TRACE_7939_INDEX"] = "1"
                        environment["MA17_TRACE_RAM5B_GATE"] = "1"
                        if tps6 == 180:
                            environment["MA17_TRACE_TPS_AFTER_TICK"] = "3000000"
                        if changed:
                            environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(donor)
                            environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7939"
                        output = Path(directory) / f"{rpm}_{tps0}_{tps6}_{changed}"
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--no-kline-inject", "--crank-immediate", "--rpm",
                             str(rpm), "--stop-ticks", "4000000", "--seconds",
                             "25", "--trace-movc", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0,
                                         result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(REFERENCE.read_bytes())
                                         .hexdigest())
                        self.assertEqual(report["movc_matrix_size"],
                                         20 if changed else None)
                        self.assertTrue(report["matrix_7939_index_trace_enabled"])
                        log = (output / "emulator-trace.log").read_text()
                        writers = [line for line in log.splitlines()
                                   if line.startswith("[7939-INDEX]")
                                   and "PC=3DDC " in line]
                        self.assertTrue(writers)
                        value = a_value if changed else g_value
                        self.assertIn(f"R4={r4} R5={r5} R6={r6} A={value}",
                                      writers[-1])
                        if tps6 == 180:
                            self.assertIn("RAM70=37 F28=00", writers[-1])
                            self.assertIn("pc=527D opcode=93 dptr=755C "
                                          "acc=00 address=755C", log)
                            tps_lines = [line for line in log.splitlines()
                                         if line.startswith("[TPS-FLOW]")]
                            before_store = [line for line in tps_lines
                                            if "PC=11C4 " in line]
                            quotient = [line for line in tps_lines
                                        if "PC=11D1 " in line]
                            self.assertTrue(before_store)
                            self.assertTrue(quotient)
                            self.assertIn(f"R2={tps0:02X} R3=1A R4=B4",
                                          before_store[-1])
                            self.assertIn("R4=B4 B=02 A=37", quotient[-1])
                        if tps0 == 120 and tps6 == 95:
                            self.assertIn("F28=06", writers[-1])
                        calls = [line for line in log.splitlines()
                                 if line.startswith("[RAM5B-GATE]")
                                 and "PC=1863 " in line]
                        self.assertEqual(len(calls), int(called))
                        if called:
                            self.assertIn(f"RAM5B={value}", calls[0])

    def test_7925_donor_is_bypassed_after_tps_flag_at_120_95(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = VARIANTS / "tipo 1.6 alcool27c256.bin"
        with tempfile.TemporaryDirectory() as directory:
            for changed in (False, True):
                environment = {
                    key: value for key, value in os.environ.items()
                    if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                           "MA17_TRACE_", "MA17_P4_"))}
                environment.update(
                    MA17_ADC_CH0="120", MA17_ADC_CH6="95",
                    MA17_ADC_CH3="4", MA17_ADC_CH5="40",
                    MA17_ADC_CH7="63", MA17_TRACE_78XX_PATH="1")
                if changed:
                    environment.update(
                        MA17_OVERRIDE_MOVC_MATRIX_BASE="7925",
                        MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor))
                output = Path(directory) / str(changed)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject",
                     "--crank-immediate", "--rpm", "1000",
                     "--stop-ticks", "2400000", "--seconds", "20",
                     "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                reads = report["movc_observation"]["reads"]
                self.assertEqual(sum(row["count"] for row in reads
                                     if 0x7925 <= int(row["address"], 16)
                                     < 0x7939), 36)
                self.assertEqual({row["address"]: row["count"] for row in reads
                                  if 0x7294 <= int(row["address"], 16)
                                  < 0x729A}, {"7298": 187, "7299": 42})
                rows = [line for line in
                        (output / "emulator-trace.log").read_text().splitlines()
                        if line.startswith("[78XX-PATH]") and "PC=3DC7" in line]
                self.assertIn(f"A={'42' if changed else '1A'}", rows[0])
                self.assertIn("A=E5", rows[-1])
                self.assertIn("F28=06", rows[-1])
                self.assertEqual(report["output_latches"]["P5.0"]
                                 ["median_low_width_ticks"], 1861)

    def test_adc2_table_7100_intervention_is_homologous_in_s88(self):
        firmware = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        reports = {}
        with tempfile.TemporaryDirectory() as directory:
            for delta in (None, "08"):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                      "MA17_OVERRIDE_"))}
                environment["MA17_ADC_CH7"] = "63"
                if delta:
                    environment["MA17_OVERRIDE_MOVC_7100_DELTA"] = delta
                output = Path(directory) / (delta or "control")
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--firmware", str(firmware), "--trace-movc",
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                     "--stop-ticks", "2400000", "--seconds", "20",
                     "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                reports[delta] = json.loads((output / "execution.json").read_text())
                self.assertEqual(reports[delta]["firmware_sha256"],
                                 hashlib.sha256(firmware.read_bytes()).hexdigest())
        control, changed = reports[None], reports["08"]
        for address, expected in (("7C", ("7E", "86")),
                                  ("48", ("40", "44"))):
            self.assertEqual((control["engine_ram_observation"][address][-1]["after"],
                              changed["engine_ram_observation"][address][-1]["after"]),
                             expected)
        self.assertEqual((control["cc3_observation"]["iram14_15_median"],
                          changed["cc3_observation"]["iram14_15_median"]),
                         (1422, 1508))

    def test_matrix_7581_read_delta_changes_cc3_at_two_tps_states(self):
        cases = ((120, 95, (1422, 5677, "40", "37"),
                  (1422, 5677, "40", "4C")),
                 (40, 95, (763, 3041, "21", "59"),
                  (926, 3693, "28", "6E")),
                 (120, 180, (1314, 5245, "3B", "A1"),
                  (1476, 5893, "42", "B6")))
        with tempfile.TemporaryDirectory() as directory:
            for adc0, adc6, natural, supplied in cases:
                for delta, expected in ((None, natural), ("15", supplied)):
                    with self.subTest(adc0=adc0, adc6=adc6, delta=delta):
                        output = Path(directory) / f"{adc0}_{adc6}_{delta}"
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({"MA17_ADC_CH0": str(adc0),
                                            "MA17_ADC_CH6": str(adc6),
                                            "MA17_ADC_CH7": "63",
                                            "MA17_TRACE_MATRIX_PATH": "1"})
                        if delta:
                            environment["MA17_OVERRIDE_MOVC_7581_DELTA"] = delta
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "20",
                             "--trace-movc", "--trace-lookup", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                        self.assertEqual(report["movc_7581_delta_hex"], delta)
                        raw = [row for row in report["movc_observation"]["reads"]
                               if 0x7581 <= int(row["mapped"], 16) < 0x7662]
                        self.assertGreater(sum(row["count"] for row in raw), 400)
                        image = REFERENCE.read_bytes()
                        self.assertTrue(all(int(row["value"], 16) ==
                                            image[int(row["mapped"], 16)] for row in raw))
                        self.assertEqual(report["cc3_observation"]
                                         ["iram14_15_median"], expected[0])
                        self.assertEqual(report["cc3_observation"]
                                         ["cc3_pin_model_median_low_width_ticks"], expected[1])
                        self.assertEqual(report["engine_ram_observation"]["48"][-1]
                                         ["after"], expected[2])
                        dominant = max(report["lookup_observation"]["states"],
                                       key=lambda row: row["count"])
                        self.assertEqual(dominant["result_a"], expected[3])
                        log = (output / "emulator-trace.log").read_text()
                        self.assertEqual("[MOVC-OVERRIDE] matrix=7581..7661" in log,
                                         delta is not None)
                        if adc6 == 95:
                            path = [dict(field.split("=") for field in line.split()[1:])
                                    for line in log.splitlines()
                                    if line.startswith("[MATRIX-PATH]") and
                                    int(line.split("tick=")[1].split()[0]) > 1000000]
                            flags = [dict(field.split("=") for field in line.split()[1:])
                                     for line in log.splitlines()
                                     if line.startswith("[MATRIX-FLAG]") and
                                     int(line.split("tick=")[1].split()[0]) > 1000000]
                            comparison = [row for row in flags if row["PC"] == "1104"]
                            aggregate = [row for row in flags if row["PC"] == "113C"]
                            self.assertGreater(len(comparison), 100)
                            self.assertEqual({row["B"] for row in aggregate},
                                             {"10" if adc0 == 120 else "00"})
                            self.assertEqual({int(row["PSW"], 16) & 0x80
                                              for row in comparison},
                                             {0x80 if adc0 == 120 else 0})
                            branch = [row for row in path if row["PC"] == "1386"]
                            before_add = [row for row in path if row["PC"] == "14C2"]
                            self.assertGreater(len(branch), 100)
                            self.assertGreater(len(before_add), 100)
                            if adc0 == 120:
                                self.assertTrue(all(row["RAM28"] == "06" for row in branch))
                                indexed = [row for row in path if row["PC"] == "145E"]
                                self.assertGreater(len(indexed), 100)
                                self.assertEqual({row["R5"] for row in indexed}, {"04"})
                                self.assertTrue(all(int(row["RAM27"], 16) & 0x80 == 0
                                                    for row in indexed))
                                self.assertTrue(any(row["pc"] == "1461" and
                                                    row["mapped"] == "7298" and
                                                    row["value"] == "AF" for row in
                                                    report["movc_observation"]["reads"]))
                                self.assertTrue(all((row["R2"], row["R3"]) ==
                                                    ("00", "AF") for row in before_add))
                            else:
                                self.assertTrue(all(row["RAM28"] == "00" for row in branch))
                                self.assertFalse(any(row["PC"] == "145E" for row in path))
                                self.assertFalse(any(row["pc"] == "1461" for row in
                                                     report["movc_observation"]["reads"]))
                                self.assertTrue(all((row["R2"], row["R3"]) ==
                                                    ("F0", expected[3]) for row in before_add))

    def test_s88_matrix_donor_matches_exact_cell_delta_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / EXPECTED[2]
        gasoline_bytes, donor_bytes = REFERENCE.read_bytes(), s88.read_bytes()
        self.assertEqual({(donor_bytes[i] - gasoline_bytes[i]) & 0xFF
                          for i in range(0x7581, 0x7662)}, {0x15})
        reports = []
        with tempfile.TemporaryDirectory() as directory:
            for mode in ("delta", "donor"):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith(("MA17_ADC_CH",
                                                      "MA17_OVERRIDE_"))}
                environment.update({"MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                                    "MA17_ADC_CH7": "63", "MA17_TRACE_MATRIX_PATH": "1"})
                if mode == "delta":
                    environment["MA17_OVERRIDE_MOVC_7581_DELTA"] = "15"
                else:
                    environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(s88)
                    environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7581"
                output = Path(directory) / mode
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                     "--stop-ticks", "2400000", "--seconds", "20",
                     "--trace-movc", "--trace-lookup", "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(gasoline_bytes).hexdigest())
                self.assertEqual(report["stop_ticks_observed"], 2400000)
                if mode == "donor":
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(donor_bytes).hexdigest())
                    self.assertEqual(report["movc_matrix_size"], 225)
                reports.append(report)
        for key in ("cc3_observation", "engine_ram_observation",
                    "lookup_observation", "output_latches", "pc_coverage"):
            self.assertEqual(reports[0][key], reports[1][key], key)
        self.assertEqual(reports[1]["cc3_observation"]["iram14_15_median"], 926)
        self.assertEqual(reports[1]["cc3_observation"]
                         ["cc3_pin_model_median_low_width_ticks"], 3693)

    def test_s88_matrix_donor_is_masked_by_tps_guard(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / EXPECTED[2]
        with tempfile.TemporaryDirectory() as directory:
            for adc6, expected in ((95, ("4C", "40", 1422, 5677, True)),
                                   (180, ("B6", "42", 1476, 5893, False))):
                with self.subTest(adc6=adc6):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "120", "MA17_ADC_CH6": str(adc6),
                        "MA17_ADC_CH7": "63", "MA17_TRACE_MATRIX_PATH": "1",
                        "MA17_OVERRIDE_MOVC_MATRIX_ROM": str(s88),
                        "MA17_OVERRIDE_MOVC_MATRIX_BASE": "7581"})
                    output = Path(directory) / str(adc6)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--trace-movc", "--trace-lookup", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(s88.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_size"], 225)
                    dominant = max(report["lookup_observation"]["states"],
                                   key=lambda row: row["count"])
                    self.assertEqual(dominant["result_a"], expected[0])
                    self.assertEqual(report["engine_ram_observation"]["48"]
                                     [-1]["after"], expected[1])
                    self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                     expected[2])
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     expected[3])
                    self.assertEqual(any(row["mapped"] == "7298" for row in
                                         report["movc_observation"]["reads"]),
                                     expected[4])

    def test_clean_tps_s88_matrix_donors_separate_cc3_and_ram69(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / EXPECTED[2]
        expected = {
            "control": (2460.5, "9A", "8B", None),
            "7581": (2978.5, "9A", "8B", 225),
            "7B46": (2460.5, "A2", "A8", 120),
        }
        timer_offsets = {}
        with tempfile.TemporaryDirectory() as directory:
            for base, (cc3_width, ram69, ram34, size) in expected.items():
                with self.subTest(base=base):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH7": "63", "MA17_TRACE_TIMER1_PATH": "1"})
                    if size is not None:
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(s88)
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = base
                    output = Path(directory) / base
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "4000000", "--seconds", "20",
                         "--trace-movc", "--trace-lookup", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_size"], size)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     cc3_width)
                    self.assertEqual(report["engine_ram_observation"]["69"]
                                     [-1]["after"], ram69)
                    self.assertEqual(report["engine_ram_observation"]["34"]
                                     [-1]["after"], ram34)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 1861)
                    if base in ("control", "7B46"):
                        log = (output / "emulator-trace.log").read_text()
                        lows = [int(m.group(1)) for m in re.finditer(
                            r"^\[P5-LATCH\] instr=(\d+) PC=00A8 .*RAM47=28", log, re.M)]
                        highs = [int(m.group(1)) for m in re.finditer(
                            r"^\[P5-LATCH\] instr=(\d+) PC=0098 .*RAM47=28", log, re.M)]
                        loads = [int(m.group(1)) for m in re.finditer(
                            r"^\[TIMER1-PATH\] tick=(\d+) PC=0298 ", log, re.M)]
                        offsets = []
                        for low in lows:
                            high = next((tick for tick in highs if tick > low), None)
                            load = next((tick for tick in loads if tick > low), None)
                            if high and load and low < load < high and high - low < 5000:
                                offsets.append((load - low, high - load, high - low))
                        self.assertGreaterEqual(len(offsets), 50)
                        timer_offsets[base] = tuple(
                            statistics.median(values) for values in zip(*offsets[-20:]))
        self.assertEqual(timer_offsets,
                         {"control": (375, 1486, 1861),
                          "7B46": (404, 1457, 1861)})

    def test_7b46_timer1_edge_shift_persists_at_750_and_1500_rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / EXPECTED[2]
        expected = {
            (750, "control"): ("9C", "F1", (386, 1477, 1863)),
            (750, "donor"): ("A4", "17", (424, 1439, 1863)),
            (1500, "control"): ("8D", "CA", (17, 1807, 1824)),
            (1500, "donor"): ("95", "DD", (36, 1788, 1824)),
        }
        with tempfile.TemporaryDirectory() as directory:
            for (rpm, kind), (ram69, ram34, median) in expected.items():
                with self.subTest(rpm=rpm, kind=kind):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    for channel, value in enumerate((40, 130, 100, 20,
                                                     90, 40, 95, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment["MA17_TRACE_TIMER1_PATH"] = "1"
                    if kind == "donor":
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(s88)
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7B46"
                    output = Path(directory) / f"{rpm}_{kind}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate",
                         "--rpm", str(rpm), "--stop-ticks", "4000000",
                         "--seconds", "25", "--trace-movc", "--trace-lookup",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_size"],
                                     120 if kind == "donor" else None)
                    self.assertEqual(report["engine_ram_observation"]["69"][-1]["after"],
                                     ram69)
                    self.assertEqual(report["engine_ram_observation"]["34"][-1]["after"],
                                     ram34)
                    log = (output / "emulator-trace.log").read_text()
                    ram47 = {750: "1E", 1500: "3C"}[rpm]
                    lows = [int(m.group(1)) for m in re.finditer(
                        rf"^\[P5-LATCH\] instr=(\d+) PC=00A8 .*RAM47={ram47}",
                        log, re.M)]
                    highs = [int(m.group(1)) for m in re.finditer(
                        rf"^\[P5-LATCH\] instr=(\d+) PC=0098 .*RAM47={ram47}",
                        log, re.M)]
                    loads = [int(m.group(1)) for m in re.finditer(
                        r"^\[TIMER1-PATH\] tick=(\d+) PC=0298 ", log, re.M)]
                    offsets = []
                    for low in lows:
                        high = next((tick for tick in highs if tick > low), None)
                        load = next((tick for tick in loads if tick > low), None)
                        if high and load and low < load < high and high - low < 5000:
                            offsets.append((load - low, high - load, high - low))
                    self.assertGreaterEqual(len(offsets), 40)
                    self.assertEqual(tuple(statistics.median(values)
                                           for values in zip(*offsets[-20:])), median)

    def test_7298_conditional_threshold_changes_cc3_model_without_rom_patch(self):
        cases = ((None, "00", "AF", "40", 1422),
                 ("00", "C0", "37", "14", 499),
                 ("50", "00", "50", "1D", 687),
                 ("C0", "00", "C0", "46", 1554))
        with tempfile.TemporaryDirectory() as directory:
            for supplied, r2, r3, ram48, cc3 in cases:
                with self.subTest(supplied=supplied):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    environment.update({"MA17_ADC_CH0": "120",
                                        "MA17_ADC_CH6": "95",
                                        "MA17_ADC_CH7": "63",
                                        "MA17_TRACE_MATRIX_PATH": "1"})
                    if supplied is not None:
                        environment["MA17_OVERRIDE_MOVC_AT"] = (
                            f"1461:7298:{supplied}")
                    output = Path(directory) / str(supplied)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "25",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "1461" and row["mapped"] == "7298"]
                    self.assertEqual({row["value"] for row in reads}, {"AF"})
                    self.assertGreater(sum(row["count"] for row in reads), 200)
                    log = (output / "emulator-trace.log").read_text()
                    before_add = [dict(field.split("=") for field in line.split()[1:])
                                  for line in log.splitlines()
                                  if line.startswith("[MATRIX-PATH]") and
                                  "PC=14C2" in line and
                                  int(line.split("tick=")[1].split()[0]) > 1000000]
                    self.assertGreater(len(before_add), 100)
                    self.assertEqual({(row["R2"], row["R3"]) for row in before_add},
                                     {(r2, r3)})
                    self.assertEqual(report["engine_ram_observation"]["48"][-1]
                                     ["after"], ram48)
                    self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                     cc3)

    @unittest.skipUnless(os.environ.get("MA17_RUN_SLOW") == "1",
                         "set MA17_RUN_SLOW=1 for the 12M-tick index scan")
    def test_7294_indices_one_through_five_reached_with_adc5_cycle(self):
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                with self.subTest(firmware=firmware.name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                          "MA17_ADC10_STEP_CH",
                                                          "MA17_OVERRIDE_", "MA17_TRACE_"))}
                    environment.update({"MA17_ADC_CH0": "120",
                                        "MA17_ADC_CH6": "95",
                                        "MA17_ADC_CH3": "4",
                                        "MA17_ADC10_CH5": "160",
                                        "MA17_ADC10_STEP_CH5":
                                        "2400000:800,4800000:160,7200000:800,9600000:160",
                                        "MA17_ADC_CH7": "63",
                                        "MA17_TRACE_MATRIX_PATH": "1"})
                    output = Path(directory) / firmware.stem
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "12000000", "--seconds", "90",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=120, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["emulator_exit"], 0)
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    reads = {row["mapped"] for row in
                             report["movc_observation"]["reads"]
                             if row["pc"] == "1461"}
                    self.assertEqual(reads, {f"729{index:X}" for index in
                                             range(5, 10)})
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    state_writes = [line for line in lines
                                    if line.startswith("[MATRIX-STATE-WRITE]")
                                    and "addr=F8A5" in line]
                    self.assertTrue(any("PC=55A1 addr=F8A5 value=00->55" in line
                                        for line in state_writes))
                    self.assertTrue(any("PC=0A51 addr=F8A5 value=AA->00" in line
                                        for line in state_writes))
                    self.assertTrue(any("PC=14B9 addr=F8A5 value=00->04" in line
                                        for line in state_writes))
                    self.assertEqual({re.search(r"PC=([0-9A-F]{4})", line).group(1)
                                      for line in state_writes},
                                     {"55A1", "0A51", "14B9"})
                    pre = [line for line in lines if line.startswith("[MATRIX-PRE]")]
                    self.assertTrue(pre)
                    self.assertIn("R4=00 R5=00 RAM27=04 RAM2C=28 T2CON=85",
                                  pre[0])
                    for line in pre:
                        fields = dict(re.findall(r"(R4|R5|RAM27|RAM2C|T2CON)=([0-9A-F]{2})",
                                                 line))
                        self.assertEqual(len(fields), 5)
                        r4, r5, flag27, guard2c, t2con = (
                            int(fields[key], 16) for key in
                            ("R4", "R5", "RAM27", "RAM2C", "T2CON"))
                        self.assertFalse(r4 == 5 and r5 == 0 and flag27 & 0x80
                                         and not guard2c & 0x20 and not t2con & 0x02)
                    indices = {int(line.split("R5=")[1][:2], 16) for line in lines
                               if line.startswith("[MATRIX-INDEX]")}
                    self.assertEqual(indices, set(range(1, 6)))

    def test_7294_threshold_indices_three_and_five_reached_naturally(self):
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        cases = ((40, "19A6", "05", "7299", 0x80),
                 (200, "19AC", "03", "7297", 0x40))
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                for adc5, transition, index, address, flag in cases:
                    with self.subTest(firmware=firmware.name, adc5=adc5):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_OVERRIDE_",
                                                              "MA17_TRACE_"))}
                        environment.update({"MA17_ADC_CH0": "120",
                                            "MA17_ADC_CH6": "95",
                                            "MA17_ADC_CH3": "4",
                                            "MA17_ADC_CH5": str(adc5),
                                            "MA17_ADC_CH7": "63",
                                            "MA17_TRACE_MATRIX_PATH": "1"})
                        output = Path(directory) / firmware.stem / str(adc5)
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "25",
                             "--trace-movc", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        reads = {row["mapped"] for row in
                                 report["movc_observation"]["reads"]
                                 if row["pc"] == "1461"}
                        self.assertEqual(reads, {"7298", address})
                        lines = (output / "emulator-trace.log").read_text().splitlines()
                        self.assertEqual(sum(line.startswith("[MATRIX-STATE]") and
                                             f"PC={transition}" in line for line in lines), 1)
                        self.assertTrue(any(line.startswith("[MATRIX-INDEX]") and
                                            f"R5={index}" in line for line in lines))
                        indexed = [dict(field.split("=") for field in line.split()[1:])
                                   for line in lines if line.startswith("[MATRIX-PATH]")
                                   and "PC=145E" in line]
                        self.assertTrue(any(row["R5"] == index and
                                            int(row["RAM27"], 16) & flag
                                            for row in indexed))
                        override_env = environment.copy()
                        override_env["MA17_OVERRIDE_MOVC_AT"] = f"1461:{address}:00"
                        changed_output = output / "counterfactual"
                        changed = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "25",
                             "--trace-movc", "--output-dir", str(changed_output)],
                            capture_output=True, text=True, env=override_env,
                            timeout=30, check=False)
                        self.assertEqual(changed.returncode, 0, changed.stderr[-1500:])
                        changed_report = json.loads(
                            (changed_output / "execution.json").read_text())
                        self.assertEqual(changed_report["firmware_sha256"],
                                         report["firmware_sha256"])
                        changed_lines = (changed_output / "emulator-trace.log").read_text()
                        self.assertIn(f"PC=1461 mapped={address}", changed_lines)
                        cutoff = 2000000 if adc5 == 40 else 2300000
                        def post_gate_median(trace_lines):
                            samples = []
                            for line in trace_lines:
                                match = re.search(
                                    r"\[CC3-ENTRY\] instr=(\d+).*IRAM14_15=([0-9A-F]+)",
                                    line)
                                if match and int(match.group(1)) > cutoff:
                                    samples.append(int(match.group(2), 16))
                            self.assertGreaterEqual(len(samples), 4)
                            return statistics.median(samples)
                        original_median = post_gate_median(lines)
                        supplied_median = post_gate_median(changed_lines.splitlines())
                        self.assertGreater(original_median - supplied_median,
                                           1000 if adc5 == 40 else 150)
                        def modeled_low_width(trace_lines):
                            low_start = None
                            widths = []
                            for line in trace_lines:
                                match = re.search(r"\[CC3-PIN\] tick=(\d+).*value=([01])",
                                                  line)
                                if match:
                                    tick = int(match.group(1))
                                    if match.group(2) == "0":
                                        low_start = tick
                                    elif low_start is not None:
                                        if low_start > cutoff:
                                            widths.append(tick - low_start)
                                        low_start = None
                            self.assertGreaterEqual(len(widths), 4)
                            return statistics.median(widths)
                        self.assertGreater(modeled_low_width(lines) -
                                           modeled_low_width(changed_lines.splitlines()),
                                           500)

    def test_rpm_segment_last_byte_reproduces_s88_at_two_rpms(self):
        for rpm, expected_p5, expected_ram31, expected_ram69 in (
                (750, 1937, "0C", "91"), (3000, 1769, "2E", "65")):
            with self.subTest(rpm=rpm), tempfile.TemporaryDirectory() as directory:
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith(("MA17_ADC_CH",
                                                      "MA17_OVERRIDE_"))}
                environment.update({"MA17_ADC_CH1": "130", "MA17_ADC_CH7": "63",
                                    "MA17_OVERRIDE_MOVC_7580": "25"})
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--no-kline-inject", "--crank-immediate", "--rpm", str(rpm),
                     "--stop-ticks", "2400000", "--seconds", "20",
                     "--trace-movc", "--output-dir", directory],
                    capture_output=True, text=True, env=environment,
                    timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((Path(directory) / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                self.assertEqual(report["movc_7580_override_hex"], "25")
                self.assertIsNone(report["movc_7b45_override_hex"])
                self.assertEqual(report["output_latches"]["P5.0"]
                                 ["median_low_width_ticks"], expected_p5)
                for address, expected in (("31", expected_ram31),
                                          ("69", expected_ram69)):
                    self.assertEqual(report["engine_ram_observation"][address][-1]
                                     ["after"], expected)
                self.assertTrue(any(row["pc"] == "5289" and
                                    row["mapped"] == "7580" and row["value"] == "10"
                                    for row in report["movc_observation"]["reads"]))

    def test_original_g_rom_ram31_ram69_factorial_reproduces_s88_p5(self):
        cases = (("59", "9A", 10334), ("50", "9A", 9286),
                 ("59", "89", 10394), ("50", "89", 9346))
        with tempfile.TemporaryDirectory() as directory:
            for ram31, ram69, expected_width in cases:
                with self.subTest(ram31=ram31, ram69=ram69):
                    output = Path(directory) / f"{ram31}_{ram69}"
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC_CH1": "40", "MA17_ADC_CH7": "63",
                                        "MA17_OVERRIDE_RAM31": ram31,
                                        "MA17_OVERRIDE_RAM69": ram69})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["ram31_override_hex"], ram31)
                    self.assertEqual(report["ram69_override_hex"], ram69)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], expected_width)

    def test_two_original_rom_bytes_reproduce_s88_p5_without_rom_patch(self):
        cases = (("05", "10", "5D", "9A", 10800),
                 ("0D", "10", "50", "9A", 9286),
                 ("05", "25", "5D", "89", 10860),
                 ("0D", "25", "50", "89", 9346))
        with tempfile.TemporaryDirectory() as directory:
            for battery_byte, rpm_byte, ram31, ram69, expected_width in cases:
                with self.subTest(battery_byte=battery_byte, rpm_byte=rpm_byte):
                    output = Path(directory) / f"{battery_byte}_{rpm_byte}"
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH1": "40", "MA17_ADC_CH7": "63",
                        "MA17_OVERRIDE_MOVC_7B45": battery_byte,
                        "MA17_OVERRIDE_MOVC_7580": rpm_byte})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_7b45_override_hex"], battery_byte)
                    self.assertEqual(report["movc_7580_override_hex"], rpm_byte)
                    self.assertEqual(report["engine_ram_observation"]["31"][-1]
                                     ["after"], ram31)
                    self.assertEqual(report["engine_ram_observation"]["69"][-1]
                                     ["after"], ram69)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], expected_width)
                    raw_reads = {row["mapped"]: row["value"]
                                 for row in report["movc_observation"]["reads"]
                                 if row["pc"] == "5289" and
                                 row["mapped"] in ("7B45", "7580")}
                    self.assertEqual(raw_reads, {"7B45": "05", "7580": "10"})

    def test_7b45_and_7580_separate_ram31_and_ram69_at_intermediate_adc1(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        s88 = VARIANTS / EXPECTED[2]
        cases = (("g", None, None, "19", "9A", 2909, 5484),
                 ("g_7b45", "0D", None, "18", "9A", 2793, 5484),
                 ("g_both", "0D", "25", "18", "89", 2853, 5476),
                 ("s88", None, None, "18", "89", 2853, 5476))
        with tempfile.TemporaryDirectory() as directory:
            for name, byte_7b45, byte_7580, ram31, ram69, p5, coverage in cases:
                with self.subTest(case=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC_CH1": "80",
                                        "MA17_ADC_CH7": "63"})
                    if byte_7b45:
                        environment["MA17_OVERRIDE_MOVC_7B45"] = byte_7b45
                    if byte_7580:
                        environment["MA17_OVERRIDE_MOVC_7580"] = byte_7580
                    output = Path(directory) / name
                    command = [sys.executable, str(ROOT / "tools" / "trace_ma17.py")]
                    if name == "s88":
                        command += ["--firmware", str(s88)]
                    command += ["--no-kline-inject", "--crank-immediate",
                                "--rpm", "1000", "--stop-ticks", "2400000",
                                "--seconds", "20", "--trace-movc",
                                "--output-dir", str(output)]
                    result = subprocess.run(command, capture_output=True, text=True,
                                            env=environment, timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    active = s88 if name == "s88" else REFERENCE
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(active.read_bytes()).hexdigest())
                    self.assertEqual(report["engine_ram_observation"]["31"][-1]
                                     ["after"], ram31)
                    self.assertEqual(report["engine_ram_observation"]["69"][-1]
                                     ["after"], ram69)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], p5)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"], 5677)
                    self.assertEqual(report["pc_coverage"]["unique"], coverage)
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "5289" and row["mapped"] == "7B45"]
                    self.assertEqual(sum(row["count"] for row in reads), 230)
                    self.assertEqual({row["value"] for row in reads},
                                     {"0D" if name == "s88" else "05"})

    def test_adc1_7b45_row_boundary_changes_ram31_and_p5_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((47, None, "85", "3F", 7306),
                 (47, "0D", "85", "32", 5792),
                 (50, None, "8E", "32", 5792),
                 (50, "0D", "8E", "2E", 5326))
        with tempfile.TemporaryDirectory() as directory:
            for adc1, donor, ratio, ram31, p5 in cases:
                with self.subTest(adc1=adc1, donor=donor):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC_CH1": str(adc1),
                                        "MA17_ADC_CH7": "63"})
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_7B45"] = donor
                    output = Path(directory) / f"{adc1}_{donor}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "1000", "--stop-ticks", "2400000", "--seconds",
                         "20", "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes())
                                     .hexdigest())
                    self.assertEqual(report["sensor_ram_observation"]["61"][-1]
                                     ["after"], f"{adc1:02X}")
                    self.assertEqual(report["sensor_ram_observation"]["64"][-1]
                                     ["after"], "5A")
                    self.assertEqual(report["engine_ram_observation"]["7D"][-1]
                                     ["after"], ratio)
                    self.assertEqual(report["engine_ram_observation"]["31"][-1]
                                     ["after"], ram31)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], p5)
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "5289" and row["mapped"] == "7B45"]
                    self.assertEqual(sum(row["count"] for row in reads), 230)
                    self.assertEqual({row["value"] for row in reads}, {"05"})

    def test_adc4_divisor_changes_7d_axis_and_modeled_p5_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((60, "C8", "1E", 3493),
                 (90, "85", "3F", 7306),
                 (120, "64", "6F", 12869))
        with tempfile.TemporaryDirectory() as directory:
            for adc4, ratio, ram31, p5 in cases:
                with self.subTest(adc4=adc4):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC_CH1": "47",
                                        "MA17_ADC_CH4": str(adc4),
                                        "MA17_ADC_CH7": "63"})
                    output = Path(directory) / str(adc4)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "1000", "--stop-ticks", "2400000", "--seconds",
                         "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes())
                                     .hexdigest())
                    self.assertEqual(report["sensor_ram_observation"]["61"][-1]
                                     ["after"], "2F")
                    divisor_write = report["sensor_ram_observation"]["64"][-1]
                    self.assertEqual(divisor_write["source_pc"], "0744")
                    self.assertEqual(divisor_write["after"], f"{adc4:02X}")
                    self.assertEqual(report["engine_ram_observation"]["7D"][-1]
                                     ["after"], ratio)
                    self.assertEqual(int(ratio, 16), (47 << 8) // adc4)
                    self.assertEqual(report["engine_ram_observation"]["31"][-1]
                                     ["after"], ram31)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], p5)

    def test_adc4_zero_reaches_saturated_7d_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_",
                                              "MA17_OVERRIDE_"))}
        environment.update({"MA17_ADC_CH1": "47", "MA17_ADC10_CH4": "0",
                            "MA17_ADC_CH7": "63"})
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                 "--stop-ticks", "2400000", "--seconds", "20",
                 "--output-dir", directory],
                capture_output=True, text=True, env=environment,
                timeout=30, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((Path(directory) / "execution.json").read_text())
        self.assertEqual(report["firmware_sha256"],
                         hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
        self.assertEqual(report["adc_10bit_input_values"][4], 0)
        self.assertEqual(report["sensor_ram_observation"].get("64", []), [])
        ratio_write = report["engine_ram_observation"]["7D"][-1]
        self.assertEqual((ratio_write["after"], ratio_write["source_pc"]),
                         ("FF", "404B"))
        self.assertEqual(report["engine_ram_observation"]["31"][-1]["after"],
                         "10")
        self.assertEqual(report["output_latches"]["P5.0"]
                         ["median_low_width_ticks"], 1861)

    def test_adc4_p5_width_is_mediated_by_ram31_at_timer1_read(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((60, "1E", 5797), (90, "3F", 6381),
                 (120, "6F", 6605))
        with tempfile.TemporaryDirectory() as directory:
            for adc4, natural31, cc3 in cases:
                with self.subTest(adc4=adc4):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC_CH1": "47",
                                        "MA17_ADC_CH4": str(adc4),
                                        "MA17_ADC_CH7": "63",
                                        "MA17_OVERRIDE_RAM31": "3F"})
                    output = Path(directory) / str(adc4)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "1000", "--stop-ticks", "2400000", "--seconds",
                         "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes())
                                     .hexdigest())
                    self.assertEqual(report["ram31_override_hex"], "3F")
                    self.assertEqual(report["engine_ram_observation"]["31"][-1]
                                     ["after"], natural31)
                    self.assertEqual(report["engine_ram_observation"]["69"][-1]
                                     ["after"], "9A")
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 7306)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     cc3)

    def test_adc4_cc3_width_is_mediated_by_ram7f_at_1e98(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((60, "31", 3493), (90, "7A", 7306),
                 (120, "96", 12869))
        with tempfile.TemporaryDirectory() as directory:
            for adc4, natural7f, p5 in cases:
                with self.subTest(adc4=adc4):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC_CH1": "47",
                                        "MA17_ADC_CH4": str(adc4),
                                        "MA17_ADC_CH7": "63",
                                        "MA17_OVERRIDE_RAM7F_AT_1E98": "7A"})
                    output = Path(directory) / str(adc4)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "1000", "--stop-ticks", "2400000", "--seconds",
                         "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes())
                                     .hexdigest())
                    self.assertEqual(report["ram7f_override_at_1e98_hex"],
                                     "7A")
                    self.assertIn("[RAM7F-OVERRIDE] PC=1E98", (output /
                                  "emulator-trace.log").read_text())
                    self.assertEqual(report["engine_ram_observation"]["7F"][-1]
                                     ["after"], natural7f)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     6381)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], p5)

    def test_7966_movc_cell_reaches_cc3_through_ram7f(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((None, None, "7A", 6381),
                 ("5333:7966:80", None, "8E", 6541),
                 ("5333:7966:80", "7A", "8E", 6381))
        with tempfile.TemporaryDirectory() as directory:
            for index, (donor, forced7f, natural7f, cc3) in enumerate(cases):
                with self.subTest(donor=donor, forced7f=forced7f):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC_CH1": "47",
                                        "MA17_ADC_CH4": "90",
                                        "MA17_ADC_CH7": "63"})
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_AT"] = donor
                    if forced7f:
                        environment["MA17_OVERRIDE_RAM7F_AT_1E98"] = forced7f
                    output = Path(directory) / str(index)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes())
                                     .hexdigest())
                    self.assertEqual(report["movc_override_at_hex"], donor)
                    self.assertEqual(report["ram7f_override_at_1e98_hex"],
                                     forced7f)
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "5333" and row["mapped"] == "7966"]
                    self.assertGreaterEqual(sum(row["count"] for row in reads),
                                            500)
                    self.assertEqual({row["value"] for row in reads}, {"4B"})
                    self.assertEqual(report["engine_ram_observation"]["7F"][-1]
                                     ["after"], natural7f)
                    self.assertEqual(report["engine_ram_observation"]["31"][-1]
                                     ["after"], "3F")
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     cc3)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 7306)

    def test_796e_movc_cell_reaches_cc3_through_upper_iram9d(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((None, None, "80", 6381),
                 ("532F:796E:40", None, "4C", 4177),
                 ("532F:796E:40", "80", "4C", 6381))
        with tempfile.TemporaryDirectory() as directory:
            for index, (donor, forced9d, writer9d, cc3) in enumerate(cases):
                with self.subTest(donor=donor, forced9d=forced9d):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC_CH1": "47",
                                        "MA17_ADC_CH4": "90",
                                        "MA17_ADC_CH7": "63"})
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_AT"] = donor
                    if forced9d:
                        environment["MA17_OVERRIDE_UPPER9D_AT_1E8B"] = forced9d
                    output = Path(directory) / str(index)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0,
                                     result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes())
                                     .hexdigest())
                    self.assertEqual(report["movc_override_at_hex"], donor)
                    self.assertEqual(report["upper9d_override_at_1e8b_hex"],
                                     forced9d)
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "532F" and row["mapped"] == "796E"]
                    self.assertGreaterEqual(sum(row["count"] for row in reads),
                                            500)
                    self.assertEqual({row["value"] for row in reads}, {"80"})
                    writes = [row["after"] for row in
                              report["engine_ram_observation"]["9D"]
                              if row["source_pc"] == "406F"]
                    self.assertEqual(writes[-1], writer9d)
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_median_low_width_ticks"],
                                     cc3)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], 7306)

    @unittest.skipUnless(os.environ.get("MA17_RUN_SLOW") == "1",
                         "set MA17_RUN_SLOW=1 for the 12.3M-tick idle gate")
    def test_74a8_cell_changes_late_idle_position_gate_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for donor, rescue, expected_ram46, expected_carry in (
                    (False, False, "25", "0"),
                    (True, False, "42", "1"),
                    (False, True, "25", "0"),
                    (True, True, "42", "0")):
                with self.subTest(donor=donor, rescue=rescue):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "120", "MA17_ADC_CH1": "130",
                        "MA17_ADC_CH2": "100", "MA17_ADC_CH3": "4",
                        "MA17_ADC_CH4": "90", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "180", "MA17_ADC_CH7": "63",
                        "MA17_P4_6_LOW_FROM_TICK": "12200000",
                        "MA17_TRACE_IDLE_POSITION_GATE": "1"})
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_AT"] = (
                            "532F:74A8:42")
                    if rescue:
                        environment["MA17_OVERRIDE_IRAM_READ_AT"] = (
                            "2307:46:25")
                    output = Path(directory) / f"{donor}_{rescue}"
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(REFERENCE), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--trace-movc", "--stop-ticks", "12300000",
                         "--seconds", "60", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=75, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["iram_read_override_at_hex"],
                                     "2307:46:25" if rescue else None)
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "532F" and
                             row["mapped"] == "74A8"]
                    self.assertEqual([row["value"] for row in reads], ["22"])
                    self.assertGreater(reads[0]["count"], 2000)
                    log = (output / "emulator-trace.log").read_text()
                    gate = [row for row in log.splitlines()
                            if "[IDLE-POSITION-GATE]" in row and
                            "F2D=D1" in row and
                            int(re.search(r"tick=(\d+)", row).group(1)) >
                            12200000]
                    self.assertEqual(len(gate), 1)
                    self.assertIn(f"CY={expected_carry}", gate[0])
                    self.assertIn(f"RAM46={expected_ram46}", gate[0])
                    subb = [row for row in log.splitlines()
                            if "[IDLE-POSITION-SUBB]" in row and
                            "F2D=D1" in row]
                    self.assertEqual(len(subb), 1)
                    self.assertIn("CY=0", subb[0])
                    self.assertEqual("[IDLE-POSITION-STEP]" in log,
                                     not donor or rescue)
                    hits = set((output / "pc-hits.txt").read_text().splitlines())
                    self.assertEqual("231C" in hits, not donor or rescue)
                    overrides = re.findall(
                        r"\[IRAM-READ-OVERRIDE\] PC=2307 addr=46 "
                        r"stored=([0-9A-F]{2}) supplied=25", log)
                    self.assertEqual(overrides[0] if overrides else None,
                                     expected_ram46 if rescue else None)

    def test_74a8_curve_index_tracks_iram63_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for adc3, ram63, index, fraction, result in (
                    (4, "04", "00", "00", "22"),
                    (20, "14", "00", "00", "22"),
                    (40, "28", "01", "B0", "26"),
                    (60, "3C", "02", "90", "29"),
                    (80, "50", "03", "20", "2A"),
                    (100, "64", "03", "A0", "2B"),
                    (130, "82", "04", "A0", "2F"),
                    (160, "A0", "05", "E0", "34"),
                    (175, "AF", "06", "90", "36"),
                    (190, "BE", "07", "50", "39"),
                    (205, "CD", "08", "30", "3D"),
                    (220, "DC", "09", "00", "42")):
                with self.subTest(adc3=adc3):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "120", "MA17_ADC_CH1": "130",
                        "MA17_ADC_CH2": "100", "MA17_ADC_CH3": str(adc3),
                        "MA17_ADC_CH4": "90", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                        "MA17_P4_7_FORCE_LOW": "1",
                        "MA17_TRACE_RAM46_TABLE": "1"})
                    output = Path(directory) / str(adc3)
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(REFERENCE), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--trace-movc", "--stop-ticks", "120000",
                         "--seconds", "10", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=20, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["sensor_ram_observation"]["63"]
                                     [-1]["after"], ram63)
                    reads = report["movc_observation"]["reads"]
                    for pc, address in (("532F", 0x74A8 + int(index, 16)),
                                        ("5333", 0x74A9 + int(index, 16))):
                        self.assertTrue(any(row["pc"] == pc and
                                            row["mapped"] == f"{address:04X}"
                                            for row in reads))
                    log = (output / "emulator-trace.log").read_text()
                    entries = re.findall(r"\[RAM46-TABLE\].*PC=48E9.*", log)
                    writes = re.findall(r"\[RAM46-TABLE\].*PC=48FF.*", log)
                    self.assertGreaterEqual(len(entries), 30)
                    self.assertGreaterEqual(len(writes), 30)
                    self.assertTrue(all(f"R5={index} R6={fraction}" in row
                                        for row in entries))
                    self.assertTrue(all(f"R2={result}" in row
                                        for row in writes))

    def test_74a8_movc_and_p47_gate_ram46_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for p47_low, donor, expected in (
                    (False, False, "25"), (True, False, "22"),
                    (False, True, "42"), (True, True, "42")):
                with self.subTest(p47_low=p47_low, donor=donor):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "120", "MA17_ADC_CH1": "130",
                        "MA17_ADC_CH2": "100", "MA17_ADC_CH3": "4",
                        "MA17_ADC_CH4": "90", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_RAM46_TABLE": "1"})
                    if p47_low:
                        environment["MA17_P4_7_FORCE_LOW"] = "1"
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_AT"] = (
                            "532F:74A8:42")
                    output = Path(directory) / f"{p47_low}_{donor}"
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(REFERENCE), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--trace-movc", "--stop-ticks", "120000",
                         "--seconds", "10", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=20, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertTrue(report["ram46_table_trace_enabled"])
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "532F" and
                             row["mapped"] == "74A8"]
                    self.assertEqual([row["value"] for row in reads], ["22"])
                    self.assertGreaterEqual(reads[0]["count"], 30)
                    log = (output / "emulator-trace.log").read_text()
                    rows = re.findall(r"\[RAM46-TABLE\].*PC=48FF.*", log)
                    self.assertGreaterEqual(len(rows), 30)
                    self.assertEqual(set(re.findall(r"R2=([0-9A-F]{2})",
                                                    "\n".join(rows))),
                                     {expected})
                    self.assertIn("PC=48E9 DPTR=700A", log)
                    self.assertIn("P4_LATCH=", rows[0])

    def test_p47_floor_at_850_rpm_is_masked_at_p53_output(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for p47_low, expected in ((False, "25"), (True, "22")):
                with self.subTest(p47_low=p47_low):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH1": "130",
                        "MA17_ADC_CH2": "100", "MA17_ADC_CH3": "4",
                        "MA17_ADC_CH4": "90", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_RAM46_TABLE": "1",
                        "MA17_TRACE_P53_GATE": "1"})
                    if p47_low:
                        environment["MA17_P4_7_FORCE_LOW"] = "1"
                    output = Path(directory) / str(p47_low)
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(REFERENCE), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "850",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=25, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["rpm_observation"]["ram47_changes"]
                                     [-1]["after"], "22")
                    log = (output / "emulator-trace.log").read_text()
                    writes = re.findall(r"\[RAM46-TABLE\].*PC=48FF.*", log)
                    self.assertGreaterEqual(len(writes), 200)
                    self.assertEqual(set(re.findall(r"R2=([0-9A-F]{2})",
                                                    "\n".join(writes))),
                                     {expected})
                    p53 = re.findall(r"\[P53-GATE\].*PC=2211.*", log)
                    self.assertEqual(len(p53), 230)
                    self.assertTrue(all(int(re.search(r"F22=([0-9A-F]{2})",
                                                      row).group(1), 16) & 0x20
                                        for row in p53))
                    self.assertTrue(all(int(re.search(r"P5_latch=([0-9A-F]{2})",
                                                      row).group(1), 16) & 0x08
                                        for row in p53))

    def test_7302_7309_rpm_branch_tracks_reference_gap(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for rpm, p47_low, reference, measured, reaches_7309 in (
                    (850, False, "25", "22", False),
                    (850, True, "22", "22", True),
                    (900, False, "25", "24", True)):
                with self.subTest(rpm=rpm, p47_low=p47_low):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "120", "MA17_ADC_CH1": "130",
                        "MA17_ADC_CH2": "100", "MA17_ADC_CH3": "4",
                        "MA17_ADC_CH4": "90", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63",
                        "MA17_TRACE_RAM46_TABLE": "1"})
                    if p47_low:
                        environment["MA17_P4_7_FORCE_LOW"] = "1"
                    output = Path(directory) / f"{rpm}_{p47_low}"
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(REFERENCE), "--no-kline-inject",
                         "--crank-immediate", "--rpm", str(rpm),
                         "--trace-movc", "--stop-ticks", "1200000",
                         "--seconds", "15", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=20, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["rpm_observation"]["ram47_changes"]
                                     [-1]["after"], measured)
                    log = (output / "emulator-trace.log").read_text()
                    writes = re.findall(r"\[RAM46-TABLE\].*PC=48FF.*", log)
                    self.assertEqual(set(re.findall(r"R2=([0-9A-F]{2})",
                                                    "\n".join(writes))),
                                     {reference})
                    reads = report["movc_observation"]["reads"]
                    self.assertTrue(any(row["pc"] == "2304" and
                                        row["mapped"] == "7302" for row in reads))
                    self.assertEqual(any(row["pc"] == "2313" and
                                         row["mapped"] == "7309" for row in reads),
                                     reaches_7309)
                    for pc, address in (("2394", "7358"),
                                        ("239D", "7318")):
                        self.assertTrue(any(row["pc"] == pc and
                                            row["mapped"] == address
                                            for row in reads))

    def test_f8a2_counter_gates_79a8_reader_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for adc6, reached in ((95, True), (180, False)):
                with self.subTest(adc6=adc6):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "120", "MA17_ADC_CH1": "130",
                        "MA17_ADC_CH2": "100", "MA17_ADC_CH3": "4",
                        "MA17_ADC_CH4": "90", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": str(adc6), "MA17_ADC_CH7": "63",
                        "MA17_TRACE_XRAM_F8A2": "1"})
                    output = Path(directory) / str(adc6)
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(REFERENCE), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "6000000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertTrue(report["xram_f8a2_trace_enabled"])
                    hits = set((output / "pc-hits.txt").read_text().splitlines())
                    self.assertIn("45F8", hits)
                    self.assertIn("2016", hits)
                    self.assertEqual("142E" in hits, reached)
                    self.assertEqual("204F" in hits, reached)
                    self.assertEqual("2027" in hits, reached)
                    log = (output / "emulator-trace.log").read_text()
                    self.assertEqual("[F8A2-WRITE] tick=5702714 PC=204F "
                                     "value=00->01" in log, reached)
                    self.assertEqual("[F8A2-READ] PC=2016 value=01" in log,
                                     reached)
                    self.assertEqual("PC=2011 C=1 F0=1 F23=2F" in log,
                                     reached)

    def test_79ad_movc_cell_changes_late_cc3_pulse_in_g(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for donor, rescue, expected_pair, expected_width in (
                    (False, False, "3A00", 233),
                    (True, False, "0E00", 57),
                    (False, True, "3A00", 233),
                    (True, True, "3A00", 233)):
                with self.subTest(donor=donor, rescue=rescue):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_ADC_CH0": "120", "MA17_ADC_CH1": "130",
                        "MA17_ADC_CH2": "100", "MA17_ADC_CH3": "4",
                        "MA17_ADC_CH4": "90", "MA17_ADC_CH5": "40",
                        "MA17_ADC_CH6": "95", "MA17_ADC_CH7": "63"})
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_AT"] = "532F:79AD:40"
                    if rescue:
                        environment["MA17_OVERRIDE_XRAM_READ_AT"] = (
                            "2027:F8A3:FF")
                    output = Path(directory) / f"{donor}_{rescue}"
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(REFERENCE), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--trace-movc", "--stop-ticks", "6000000",
                         "--seconds", "30", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"],
                                     "532F:79AD:40" if donor else None)
                    self.assertEqual(report["xram_read_override_at_hex"],
                                     "2027:F8A3:FF" if rescue else None)
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["pc"] == "532F" and row["mapped"] == "79AD"]
                    self.assertEqual([(row["value"], row["count"])
                                      for row in reads], [("FF", 1436)])
                    pc_hits = (output / "pc-hits.txt").read_text().splitlines()
                    self.assertIn("45EF", pc_hits)
                    self.assertIn("45F8", pc_hits)
                    self.assertIn("2027", pc_hits)
                    self.assertIn("2036", pc_hits)
                    log = (output / "emulator-trace.log").read_text()
                    overrides = re.findall(
                        r"\[XRAM-READ-OVERRIDE\] PC=2027 addr=F8A3 "
                        r"stored=([0-9A-F]{2}) supplied=FF", log)
                    self.assertEqual(overrides, ["40" if donor else "FF"]
                                     if rescue else [])
                    pairs = re.findall(r"\[CC3-ENTRY\].*PC=5469.*"
                                       r"R2_R3=([0-9A-F]{4})", log)
                    self.assertEqual(pairs, [expected_pair])
                    edges = [(int(tick), int(value), pc) for tick, pc, value in
                             re.findall(r"\[CC3-PIN\] tick=(\d+) "
                                        r"PC=([0-9A-F]{4}) value=(\d)", log)]
                    widths = [next_tick - tick for (tick, value, pc),
                              (next_tick, next_value, _) in zip(edges, edges[1:])
                              if pc == "54B3" and value == 0 and next_value == 1]
                    self.assertEqual(len(widths), 1)
                    self.assertLessEqual(abs(widths[0] - expected_width), 2)
                    self.assertEqual(report["cc3_observation"][
                        "iram14_15_median"], 1096)
                    self.assertEqual(report["output_latches"]["P5.0"][
                        "median_low_width_ticks"], 1861)

    def test_coolant_adc_crosses_second_lambda_guard_boundary(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for adc3, ram63, bit0, carry in ((43, "2B", 1, 0),
                                             (44, "2C", 1, 0),
                                             (45, "2D", 0, 1)):
                output = Path(directory) / str(adc3)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--seconds", "10", "--stop-ticks", "320000",
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                     "--output-dir", str(output)],
                    capture_output=True, text=True,
                    env={**{key: value for key, value in os.environ.items()
                             if not key.startswith("MA17_ADC_CH")},
                         "MA17_ADC_CH3": str(adc3), "MA17_ADC_CH5": "40",
                         "MA17_ADC_CH7": "63", "MA17_TRACE_LAMBDA": "1"})
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["stop_ticks_observed"], 320000)
                self.assertEqual(report["sensor_ram_observation"]["63"][-1]["after"],
                                 ram63)
                gates = [dict(field.split("=") for field in line.split()[1:])
                         for line in (output / "emulator-trace.log").read_text().splitlines()
                         if line.startswith("[LAMBDA-GATE]") and "PC=17ED" in line]
                self.assertTrue(gates)
                self.assertEqual(int(gates[0]["B"], 16) & 1, bit0)
                self.assertEqual(int(gates[0]["PSW"], 16) >> 7, carry)

    def test_lambda_adc_reaches_iram_but_does_not_open_observed_integrator(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for adc5, expected_iram, flag_bit in ((40, "28", 0x08),
                                                   (200, "C8", 0x00)):
                output = Path(directory) / str(adc5)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--seconds", "15", "--stop-ticks", "2400000",
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                     "--output-dir", str(output)],
                    capture_output=True, text=True,
                    env={**{key: value for key, value in os.environ.items()
                             if not key.startswith("MA17_ADC_CH")},
                         "MA17_ADC_CH5": str(adc5), "MA17_ADC_CH7": "63",
                         "MA17_TRACE_LAMBDA": "1"})
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["stop_ticks_observed"], 2400000)
                self.assertEqual(report["sensor_ram_observation"]["65"][-1]["after"],
                                 expected_iram)
                self.assertEqual(report["adaptation_xram_observation"]["F80C"][-1]["after"],
                                 "80")
                self.assertEqual(set(report["adaptation_xram_observation"]), {"F80C"})
                events = []
                for line in (output / "emulator-trace.log").read_text().splitlines():
                    if line.startswith("[LAMBDA-GATE]"):
                        events.append(dict(field.split("=") for field in
                                           line.split()[1:]))
                steady = [event for event in events if
                          event["PC"] == "1644" and int(event["tick"]) > 1000000]
                self.assertTrue(steady)
                self.assertTrue(all(int(event["flags2C"], 16) & 0x08 == flag_bit
                                    for event in steady))
                integrator = [event for event in events if event["PC"] == "19D0"]
                self.assertTrue(integrator)
                self.assertTrue(all((event["R6"], event["R7"], event["T2I0"],
                                     event["T2I1"]) == ("00", "00", "1", "0")
                                    for event in integrator))

    def test_adc3_extreme_enables_adc5_dependent_xram_and_cc3(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        widths = {}
        with tempfile.TemporaryDirectory() as directory:
            for adc5, expected_final in ((40, "CB"), (200, "68")):
                output = Path(directory) / str(adc5)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--seconds", "15", "--stop-ticks", "2400000",
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                     "--output-dir", str(output)],
                    capture_output=True, text=True,
                    env={**{key: value for key, value in os.environ.items()
                             if not key.startswith("MA17_ADC_CH")},
                         "MA17_ADC_CH3": "4", "MA17_ADC_CH5": str(adc5),
                         "MA17_ADC_CH7": "63", "MA17_TRACE_LAMBDA": "1"})
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads((output / "execution.json").read_text())
                changes = report["adaptation_xram_observation"]["F80C"]
                self.assertGreater(len(changes), 50)
                self.assertEqual(changes[-1]["after"], expected_final)
                self.assertTrue(all(row["source_pc"] == "19D2" for row in
                                    changes[4:]))
                widths[adc5] = report["cc3_observation"][
                    "cc3_pin_model_median_low_width_ticks"]
                gates = [line for line in
                         (output / "emulator-trace.log").read_text().splitlines()
                         if line.startswith("[LAMBDA-GATE]") and "PC=186D" in line]
                self.assertTrue(gates)
        self.assertGreater(widths[40] - widths[200], 250)

    def test_high_tps_lambda_gate_depends_on_adc5_state(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        late_cc3 = {}
        with tempfile.TemporaryDirectory() as directory:
            for adc5, expected_f80c, expected_flag, reaches in (
                    (40, "B0", "2E", True), (200, "80", "0C", False)):
                output = Path(directory) / str(adc5)
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith(("MA17_ADC_CH",
                                                      "MA17_ADC10_",
                                                      "MA17_OVERRIDE_"))}
                environment.update({"MA17_ADC_CH0": "180",
                                    "MA17_ADC_CH6": "247",
                                    "MA17_ADC_CH3": "4",
                                    "MA17_ADC_CH5": str(adc5),
                                    "MA17_ADC_CH7": "63",
                                    "MA17_TRACE_LAMBDA": "1",
                                    "MA17_TRACE_TPS_AFTER_TICK": "1800000",
                                    "MA17_TRACE_CC3_AFTER_TICK": "1800000"})
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                     "--stop-ticks", "2400000", "--seconds", "20",
                     "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["stop_ticks_observed"], 2400000)
                self.assertEqual(report["tps_trace_after_tick"], "1800000")
                self.assertEqual(report["cc3_trace_after_tick"], "1800000")
                self.assertEqual(report["adaptation_xram_observation"]["F80C"]
                                 [-1]["after"], expected_f80c)
                lines = (output / "emulator-trace.log").read_text().splitlines()
                tps = [line for line in lines if line.startswith("[TPS-FLOW]")]
                self.assertTrue(tps)
                self.assertTrue(all(int(line.split("tick=")[1].split()[0])
                                    >= 1800000 for line in tps))
                gate = [line for line in lines if line.startswith("[LAMBDA-GATE]")
                        and "PC=1810 " in line and
                        int(line.split("tick=")[1].split()[0]) > 1800000]
                self.assertTrue(gate)
                self.assertEqual({line.split("flags2F=")[1][:2]
                                  for line in gate}, {expected_flag})
                reached = any(line.startswith("[LAMBDA-GATE]") and
                              "PC=186D " in line and
                              int(line.split("tick=")[1].split()[0]) > 1800000
                              for line in lines)
                self.assertEqual(reached, reaches)
                late_cc3[adc5] = [int(line.split("IRAM14_15=")[1][:4], 16)
                                  for line in lines if line.startswith("[CC3-ENTRY]")
                                  and int(line.split("instr=")[1].split()[0])
                                  > 1800000]
                self.assertGreater(len(late_cc3[adc5]), 15)
        self.assertGreater(statistics.median(late_cc3[40]) -
                           statistics.median(late_cc3[200]), 50)

    def test_tps_step_retains_prior_f889_bit_at_same_raw_inputs(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for stepped, expected_b, expected_28 in (
                    (False, "00", "00"), (True, "10", "06")):
                with self.subTest(stepped=stepped):
                    output = Path(directory) / str(stepped)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC_CH0": "120" if stepped else "180",
                                        "MA17_ADC_CH6": "95" if stepped else "247",
                                        "MA17_ADC_CH3": "4", "MA17_ADC_CH5": "200",
                                        "MA17_ADC_CH7": "63",
                                        "MA17_TRACE_MATRIX_PATH": "1",
                                        "MA17_TRACE_TPS_AFTER_TICK": "1200000"})
                    if stepped:
                        environment["MA17_ADC10_STEP_CH0"] = "1200000:720"
                        environment["MA17_ADC10_STEP_CH6"] = "1200000:988"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "1300000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["stop_ticks_observed"], 1300000)
                    for address, value in (("60", "B4"), ("66", "F7")):
                        self.assertEqual(report["sensor_ram_observation"]
                                         [address][-1]["after"], value)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    writes = [line for line in lines if
                              line.startswith("[MATRIX-XRAM-WRITE]") and
                              "PC=115E addr=F889 value=00->10" in line]
                    self.assertEqual(bool(writes), stepped)
                    state = [dict(field.split("=") for field in line.split()[1:])
                             for line in lines if line.startswith("[TPS-FLOW]")
                             and "PC=1132 " in line]
                    self.assertTrue(state)
                    self.assertEqual({(row["R2"], row["R4"], row["B"],
                                       row["RAM28"]) for row in state},
                                     {("B4", "F7", expected_b, expected_28)})

    def test_clean_tps_step_suspends_and_restores_lambda_route(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_",
                                                  "MA17_OVERRIDE_"))}
            environment.update({"MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                                "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "200",
                                "MA17_ADC_CH7": "63",
                                "MA17_ADC10_STEP_CH0": "1800000:720,3000000:160",
                                "MA17_ADC10_STEP_CH6": "1800000:988,3000000:380",
                                "MA17_TRACE_LAMBDA": "1"})
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                 "--stop-ticks", "5000000", "--seconds", "30",
                 "--output-dir", directory],
                capture_output=True, text=True, env=environment,
                timeout=40, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((Path(directory) / "execution.json").read_text())
            self.assertEqual(report["stop_ticks_observed"], 5000000)
            for address, values in (("60", ("28", "B4", "28")),
                                    ("66", ("5F", "F7", "5F"))):
                self.assertEqual(tuple(event["after"] for event in
                                       report["sensor_ram_observation"][address][-3:]),
                                 values)
            lines = (Path(directory) / "emulator-trace.log").read_text().splitlines()
            gates = [line for line in lines if line.startswith("[LAMBDA-GATE]")]

            def window(pc, start, end):
                return [line for line in gates if f"PC={pc} " in line and
                        start <= int(line.split("tick=")[1].split()[0]) < end]

            for start, end, active in ((1200000, 1800000, True),
                                       (2400000, 3000000, False),
                                       (3600000, 4200000, True)):
                checks = window("1810", start, end)
                self.assertGreater(len(checks), 50)
                self.assertEqual({line.split("flags28=")[1][:2]
                                  for line in checks}, {"00"})
                self.assertEqual(bool(window("186D", start, end)), active)
            self.assertEqual(report["adaptation_xram_observation"]["F80C"]
                             [-1]["after"], "65")

    def test_s88_clean_tps_step_has_same_lambda_gate(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_",
                                                  "MA17_OVERRIDE_"))}
            environment.update({"MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                                "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "200",
                                "MA17_ADC_CH7": "63",
                                "MA17_ADC10_STEP_CH0": "1800000:720,3000000:160",
                                "MA17_ADC10_STEP_CH6": "1800000:988,3000000:380",
                                "MA17_TRACE_LAMBDA": "1"})
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--firmware", str(VARIANTS / EXPECTED[2]),
                 "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                 "--stop-ticks", "5000000", "--seconds", "30",
                 "--output-dir", directory],
                capture_output=True, text=True, env=environment,
                timeout=40, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((Path(directory) / "execution.json").read_text())
            self.assertEqual(report["firmware_sha256"],
                             "bfa59928ca41695458063835dc1a05a489b9deb5755bb1d7740c22874fdcbe28")
            self.assertEqual(report["stop_ticks_observed"], 5000000)
            self.assertEqual(report["adaptation_xram_observation"]["F80C"]
                             [-1]["after"], "65")
            lines = (Path(directory) / "emulator-trace.log").read_text().splitlines()
            for start, end, expected in ((1200000, 1800000, 56),
                                         (2400000, 3000000, 0),
                                         (3600000, 4200000, 59)):
                gates = [line for line in lines if line.startswith("[LAMBDA-GATE]")
                         and "PC=186D " in line and
                         start <= int(line.split("tick=")[1].split()[0]) < end]
                self.assertEqual(len(gates), expected)

    def test_clean_tps_cycle_lambda_gate_depends_on_adc5(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for adc5, high_reaches in ((40, True), (200, False)):
                with self.subTest(adc5=adc5):
                    output = Path(directory) / str(adc5)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": str(adc5),
                        "MA17_ADC_CH7": "63", "MA17_TRACE_LAMBDA": "1",
                        "MA17_ADC10_STEP_CH0": "1800000:720,3000000:160",
                        "MA17_ADC10_STEP_CH6": "1800000:988,3000000:380"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "1000", "--stop-ticks", "5000000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["stop_ticks_observed"], 5000000)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    gates = [line for line in lines if line.startswith("[LAMBDA-GATE]")]

                    def window(pc, start, end):
                        return [line for line in gates if f"PC={pc} " in line and
                                start <= int(line.split("tick=")[1].split()[0]) < end]

                    for start, end, reaches in ((1200000, 1800000, True),
                                                (2400000, 3000000, high_reaches),
                                                (3600000, 4200000, True)):
                        guard = window("1810", start, end)
                        self.assertGreater(len(guard), 50)
                        self.assertEqual({line.split("flags28=")[1][:2]
                                          for line in guard}, {"00"})
                        self.assertEqual(len(window("186D", start, end)) > 50,
                                         reaches)
                    high = window("1810", 2400000, 3000000)
                    self.assertEqual({int(line.split("flags2F=")[1][:2], 16)
                                      & 0x06 for line in high},
                                     {0x06 if high_reaches else 0x04})
                    self.assertEqual({line.split("RAM3C=")[1][:2]
                                      for line in high},
                                     {"00" if high_reaches else "0F"})

    def test_s88_clean_tps_cycle_keeps_lambda_route_with_adc5_40(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_",
                                                  "MA17_OVERRIDE_"))}
            environment.update({
                "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "40",
                "MA17_ADC_CH7": "63", "MA17_TRACE_LAMBDA": "1",
                "MA17_ADC10_STEP_CH0": "1800000:720,3000000:160",
                "MA17_ADC10_STEP_CH6": "1800000:988,3000000:380"})
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--firmware", str(VARIANTS / EXPECTED[2]),
                 "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                 "--stop-ticks", "5000000", "--seconds", "30",
                 "--output-dir", directory],
                capture_output=True, text=True, env=environment,
                timeout=40, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((Path(directory) / "execution.json").read_text())
            self.assertEqual(report["firmware_sha256"],
                             "bfa59928ca41695458063835dc1a05a489b9deb5755bb1d7740c22874fdcbe28")
            self.assertEqual(report["stop_ticks_observed"], 5000000)
            lines = (Path(directory) / "emulator-trace.log").read_text().splitlines()
            high = [line for line in lines if line.startswith("[LAMBDA-GATE]")
                    and 2400000 <= int(line.split("tick=")[1].split()[0])
                    < 3000000]
            guard = [line for line in high if "PC=1810 " in line]
            self.assertGreater(len(guard), 50)
            self.assertGreater(sum("PC=186D " in line for line in high), 50)
            self.assertEqual(sum("PC=1870 " in line for line in high), 59)
            self.assertEqual({line.split("flags28=")[1][:2] for line in guard},
                             {"00"})
            self.assertEqual({int(line.split("flags2F=")[1][:2], 16) & 6
                              for line in guard}, {6})
            self.assertEqual({line.split("RAM3C=")[1][:2] for line in guard},
                             {"00"})

    def test_high_tps_adc5_cycle_reversibly_gates_lambda_route(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((200, "1800000:160,3000000:800", (False, True, False)),
                 (40, "1800000:800,3000000:160", (True, False, True)))
        with tempfile.TemporaryDirectory() as directory:
            for initial, steps, expected in cases:
                with self.subTest(initial_adc5=initial):
                    output = Path(directory) / str(initial)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "180", "MA17_ADC_CH6": "247",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": str(initial),
                        "MA17_ADC_CH7": "63", "MA17_TRACE_LAMBDA": "1",
                        "MA17_ADC10_STEP_CH5": steps})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "1000", "--stop-ticks", "5000000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["stop_ticks_observed"], 5000000)
                    self.assertEqual([event["after"] for event in
                                      report["sensor_ram_observation"]["65"][-3:]],
                                     ["28", "C8", "28"] if initial == 40
                                     else ["C8", "28", "C8"])
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    gates = [line for line in lines if line.startswith("[LAMBDA-GATE]")]
                    windows = ((1200000, 1800000), (2400000, 3000000),
                               (3600000, 4200000))
                    for (start, end), active in zip(windows, expected):
                        window = [line for line in gates if start <= int(
                            line.split("tick=")[1].split()[0]) < end]
                        guard = [line for line in window if "PC=1810 " in line]
                        self.assertGreater(len(guard), 50)
                        self.assertEqual({line.split("flags28=")[1][:2]
                                          for line in guard}, {"00"})
                        self.assertEqual({int(line.split("flags2F=")[1][:2], 16)
                                          & 6 for line in guard},
                                         {6 if active else 4})
                        self.assertEqual(sum("PC=1870 " in line for line in window)
                                         > 50, active)

    def test_rpm_curve_799f_sets_lambda_gate_at_ram6f_boundary(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        self.assertEqual(REFERENCE.read_bytes()[0x799F], 0x81)
        with tempfile.TemporaryDirectory() as directory:
            for value, reaches in (("A6", False), ("A7", True)):
                with self.subTest(curve_return=value):
                    output = Path(directory) / value
                    environment = {key: val for key, val in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({
                        "MA17_ADC_CH0": "180", "MA17_ADC_CH6": "247",
                        "MA17_ADC_CH3": "20", "MA17_ADC_CH5": "200",
                        "MA17_ADC_CH7": "63", "MA17_TRACE_LAMBDA": "1",
                        "MA17_TRACE_AIR_716C_GATE": "1",
                        "MA17_OVERRIDE_MOVC_AT": f"532F:799F:{value}"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject", "--crank-immediate",
                         "--rpm", "1000", "--stop-ticks", "1600000",
                         "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["stop_ticks_observed"], 1600000)
                    self.assertEqual(report["movc_override_at_hex"],
                                     f"532F:799F:{value}")
                    original_reads = [row for row in
                                      report["movc_observation"]["reads"]
                                      if row["pc"] == "532F" and
                                      row["address"] == "799F"]
                    self.assertEqual({row["value"] for row in original_reads},
                                     {"81"})
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    gate = [line for line in lines if line.startswith(
                            "[AIR-716C-GATE]") and "PC=3CB7 " in line and
                            int(line.split("tick=")[1].split()[0]) > 1200000]
                    self.assertGreater(len(gate), 50)
                    self.assertEqual({line.split("RAM6F=")[1][:2]
                                      for line in gate}, {"A7"})
                    self.assertEqual({line.split("R2=")[1][:2]
                                      for line in gate}, {value})
                    reached = sum(line.startswith("[LAMBDA-GATE]") and
                                  "PC=186D " in line and
                                  int(line.split("tick=")[1].split()[0]) > 1200000
                                  for line in lines)
                    self.assertEqual(reached > 30, reaches)
                    self.assertEqual(report["adaptation_xram_observation"]
                                     ["F80C"][-1]["after"] == "80", not reaches)

    def test_rpm_curve_799e_gate_interacts_with_adc5_classifier(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for rpm, expected_r2 in ((750, "72"), (4000, "33")):
                for adc5, expected_flag, reaches in ((40, "0E", True),
                                                      (200, "0C", False)):
                    with self.subTest(rpm=rpm, adc5=adc5):
                        output = Path(directory) / f"{rpm}_{adc5}"
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({
                            "MA17_ADC_CH0": "180", "MA17_ADC_CH6": "247",
                            "MA17_ADC_CH3": "20", "MA17_ADC_CH5": str(adc5),
                            "MA17_ADC_CH7": "63", "MA17_TRACE_LAMBDA": "1",
                            "MA17_TRACE_AIR_716C_GATE": "1"})
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--no-kline-inject", "--crank-immediate", "--rpm",
                             str(rpm), "--stop-ticks", "1800000", "--seconds",
                             "20", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0,
                                         result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["stop_ticks_observed"], 1800000)
                        lines = (output / "emulator-trace.log").read_text().splitlines()
                        def late(line):
                            return (1200000 <= int(line.split("tick=")[1]
                                                    .split()[0]) < 1800000)
                        curve = [line for line in lines if line.startswith(
                                 "[AIR-716C-GATE]") and "PC=3CB7 " in line
                                 and late(line)]
                        self.assertGreater(len(curve), 100)
                        self.assertEqual({line.split("R2=")[1][:2]
                                          for line in curve}, {expected_r2})
                        self.assertEqual({line.split("RAM6F=")[1][:2]
                                          for line in curve}, {"A7"})
                        guards = [line for line in lines if line.startswith(
                                  "[LAMBDA-GATE]") and "PC=1810 " in line
                                  and late(line)]
                        self.assertGreater(len(guards), 50)
                        self.assertEqual({int(line.split("flags2F=")[1][:2], 16)
                                          & 0x06 for line in guards},
                                         {int(expected_flag, 16) & 0x06})
                        reached = sum(line.startswith("[LAMBDA-GATE]") and
                                      "PC=186D " in line and late(line)
                                      for line in lines)
                        self.assertEqual(reached > 50, reaches)
                        self.assertEqual(report["adaptation_xram_observation"]
                                         ["F80C"][-1]["after"] == "80", not reaches)

    def test_low_tps_without_fault_flags_reaches_lambda_correction(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        late_cc3 = {}
        with tempfile.TemporaryDirectory() as directory:
            for adc5, expected_f80c in ((40, "A8"), (200, "57")):
                output = Path(directory) / str(adc5)
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith(("MA17_ADC_CH",
                                                      "MA17_ADC10_",
                                                      "MA17_OVERRIDE_"))}
                environment.update({"MA17_ADC_CH0": "40",
                                    "MA17_ADC_CH6": "95",
                                    "MA17_ADC_CH3": "20",
                                    "MA17_ADC_CH5": str(adc5),
                                    "MA17_ADC_CH7": "63",
                                    "MA17_TRACE_LAMBDA": "1",
                                    "MA17_TRACE_CC3_AFTER_TICK": "1800000"})
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                     "--stop-ticks", "4000000", "--seconds", "30",
                     "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=40, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["stop_ticks_observed"], 4000000)
                self.assertEqual(report["cc3_trace_after_tick"], "1800000")
                self.assertEqual(report["sensor_ram_observation"]["63"][-1]
                                 ["after"], "14")
                self.assertEqual(report["adaptation_xram_observation"]["F80C"]
                                 [-1]["after"], expected_f80c)
                lines = (output / "emulator-trace.log").read_text().splitlines()
                gates = [line for line in lines if
                         line.startswith("[LAMBDA-GATE]") and "PC=1810 " in line
                         and int(line.split("tick=")[1].split()[0]) > 1800000]
                self.assertGreater(len(gates), 50)
                self.assertEqual({line.split("flags28=")[1][:2]
                                  for line in gates}, {"00"})
                self.assertGreater(sum(line.startswith("[LAMBDA-GATE]")
                                       and "PC=186D " in line for line in lines), 250)
                late_cc3[adc5] = [int(line.split("IRAM14_15=")[1][:4], 16)
                                  for line in lines if line.startswith("[CC3-ENTRY]")
                                  and int(line.split("instr=")[1].split()[0])
                                  > 1800000]
                self.assertGreater(len(late_cc3[adc5]), 70)
        self.assertGreater(statistics.median(late_cc3[40]) -
                           statistics.median(late_cc3[200]), 40)

    def test_lambda_adc5_thresholds_and_neutral_intervals(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        # SAB80C517A ADDATH holds the high eight ADC bits. The older
        # emulator accidentally added one from the ADDATL start byte.
        cases = ((109, "6D", "CB", 1, 1),
                 (110, "6E", "80", 0, 1),
                 (134, "86", "80", 0, 1),
                 (135, "87", "80", 1, 0),
                 (153, "99", "80", 1, 0),
                 (154, "9A", "6A", 0, 0))
        with tempfile.TemporaryDirectory() as directory:
            for adc5, ram65, f80c, bit2c3, bit2f1 in cases:
                with self.subTest(adc5=adc5):
                    output = Path(directory) / str(adc5)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC_CH3": "4",
                                        "MA17_ADC_CH5": str(adc5),
                                        "MA17_ADC_CH7": "63",
                                        "MA17_TRACE_LAMBDA": "1"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["sensor_ram_observation"]["65"][-1]
                                     ["after"], ram65)
                    self.assertEqual(report["adaptation_xram_observation"]
                                     ["F80C"][-1]["after"], f80c)
                    steady = [dict(field.split("=") for field in line.split()[1:])
                              for line in (output / "emulator-trace.log")
                              .read_text().splitlines()
                              if line.startswith("[LAMBDA-GATE]") and
                              "PC=1644" in line and
                              int(line.split("tick=")[1].split()[0]) > 1000000]
                    self.assertTrue(steady)
                    self.assertEqual((int(steady[-1]["flags2C"], 16) >> 3) & 1,
                                     bit2c3)
                    self.assertEqual((int(steady[-1]["flags2F"], 16) >> 1) & 1,
                                     bit2f1)

    def test_temperature_adc10_low_bits_round_into_sensor_ram(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        # Original ROM 0716h..071Bh rotates ADDATL.7 into bit 0 and adds
        # ADDATH, so 10-bit values with low bits 2/3 round upward.
        with tempfile.TemporaryDirectory() as directory:
            for adc10, expected in ((160, "28"), (161, "28"),
                                    (162, "29"), (163, "29")):
                with self.subTest(adc10=adc10):
                    output = Path(directory) / str(adc10)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_CH"))}
                    environment.update({"MA17_ADC10_CH2": str(adc10),
                                        "MA17_ADC10_CH3": str(adc10),
                                        "MA17_ADC_CH7": "63"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "400000", "--seconds", "8",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=20, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    for address in ("62", "63"):
                        self.assertEqual(report["sensor_ram_observation"]
                                         [address][-1]["after"], expected)

    def test_adc10_step_reaches_firmware_on_next_temperature_conversion(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                  "MA17_ADC10_STEP_CH",
                                                  "MA17_OVERRIDE_", "MA17_TRACE_"))}
            environment.update({"MA17_ADC10_CH2": "400",
                                "MA17_ADC10_STEP_CH2": "200000:163",
                                "MA17_ADC_CH7": "63"})
            output = Path(directory)
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                 "--stop-ticks", "400000", "--seconds", "8",
                 "--output-dir", str(output)],
                capture_output=True, text=True, env=environment,
                timeout=20, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((output / "execution.json").read_text())
            self.assertEqual(report["firmware_sha256"],
                             hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
            self.assertEqual(report["adc_10bit_step_values"][2],
                             {"tick": 200000, "value": 163})
            conversions = [row for row in report["sensor_ram_observation"]["62"]
                           if row["source_pc"] == "0744"]
            self.assertEqual([row["after"] for row in conversions], ["64", "29"])
            self.assertGreater(conversions[-1]["tick"], 200000)

    def test_staggered_air_and_coolant_adc_steps_stay_on_separate_channels(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                with self.subTest(firmware=firmware.name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                          "MA17_ADC10_STEP_CH",
                                                          "MA17_OVERRIDE_", "MA17_TRACE_"))}
                    environment.update({"MA17_ADC10_CH2": "160",
                                        "MA17_ADC10_CH3": "160",
                                        "MA17_ADC10_STEP_CH2": "200000:163",
                                        "MA17_ADC10_STEP_CH3": "400000:163",
                                        "MA17_ADC_CH7": "63"})
                    output = Path(directory) / firmware.stem
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "700000", "--seconds", "12",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=20, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["emulator_exit"], 0)
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    observations = report["sensor_ram_observation"]
                    air = [row for row in observations["62"]
                           if row["source_pc"] == "0744"]
                    raw_coolant = [row for row in observations["A8"]
                                   if row["source_pc"] == "0744"]
                    coolant = [row for row in observations["63"]
                               if row["source_pc"] == "4756"]
                    self.assertEqual([row["after"] for row in air], ["28", "29"])
                    self.assertEqual([row["after"] for row in raw_coolant],
                                     ["28", "29"])
                    self.assertEqual([row["after"] for row in coolant],
                                     ["28", "29"])
                    self.assertTrue(200000 < air[-1]["tick"] < 400000)
                    self.assertTrue(400000 < raw_coolant[-1]["tick"] <=
                                    coolant[-1]["tick"])

    def test_air_adc_step_changes_cc3_schedule_and_modeled_pulse(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (("G down", REFERENCE, 400, 160, "64", "28", "3C",
                  1440, 1352, 1336, 5749, 5333),
                 ("G up", REFERENCE, 160, 400, "28", "64", "40",
                  1352, 1440, 1422, 5397, 5677),
                 ("S88 down", VARIANTS /
                  "tipo 1.6 alcool27c256 SUN 8817.bin", 400, 160,
                  "64", "28", "3C", 1440, 1352, 1336, 5749, 5333))
        with tempfile.TemporaryDirectory() as directory:
            for (name, firmware, initial, stepped, old_ram, new_ram,
                 new_ram48, before_raw, interim_raw, after_raw,
                 before_width, after_width) in cases:
                with self.subTest(name=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_CH",
                                                          "MA17_ADC10_STEP_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    environment.update({"MA17_ADC10_CH2": str(initial),
                                        "MA17_ADC10_STEP_CH2": f"800000:{stepped}",
                                        "MA17_ADC_CH7": "63"})
                    output = Path(directory) / name.replace(" ", "_")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "1600000", "--seconds", "25",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    samples = [row for row in report["sensor_ram_observation"]["62"]
                               if row["source_pc"] == "0744"]
                    self.assertEqual([row["after"] for row in samples],
                                     [old_ram, new_ram])
                    self.assertGreater(samples[-1]["tick"], 800000)
                    self.assertIn(new_ram48, [row["after"] for row in
                                                  report["engine_ram_observation"]["48"]])
                    ram5a = [row for row in report["engine_ram_observation"]["5A"]
                             if row["tick"] > 800000]
                    self.assertTrue(any(816900 <= row["tick"] <= 817100 and
                                        row["after"] ==
                                        ("04" if stepped == 160 else "5C")
                                        for row in ram5a))
                    self.assertTrue(any(1070000 <= row["tick"] <= 1090000 and
                                        row["after"] ==
                                        ("F4" if stepped == 160 else "4A")
                                        for row in ram5a))
                    if stepped == 160:
                        self.assertTrue(any(1083000 <= row["tick"] <= 1084000
                                            and row["after"] == "04" and
                                            row["source_pc"] == "1644"
                                            for row in report["engine_ram_observation"]["59"]))
                    self.assertTrue(any(1072500 <= row["tick"] <= 1073500
                                        and row["before"] == "1A" and
                                        row["after"] == "18" and
                                        row["source_pc"] == "155B"
                                        for row in report["engine_ram_observation"]["87"]))
                    log = (output / "emulator-trace.log").read_text()
                    entries = [(int(tick), int(value, 16)) for tick, value in
                               re.findall(r"\[CC3-ENTRY\] instr=(\d+).*?"
                                          r"IRAM14_15=([0-9A-F]{4})", log)]
                    for low, high, expected in ((400000, 800000, before_raw),
                                                (820000, 1060000, interim_raw),
                                                (1100000, 1500000, after_raw)):
                        values = [value for tick, value in entries
                                  if low <= tick < high]
                        self.assertGreater(len(values), 5)
                        self.assertEqual(set(values), {expected})
                    edges = [(int(tick), int(value)) for tick, value in
                             re.findall(r"\[CC3-PIN\] tick=(\d+).*?value=(\d)",
                                        log)]
                    for low, high, expected in ((400000, 800000, before_width),
                                                (1100000, 1500000, after_width)):
                        widths = [edges[index + 1][0] - tick
                                  for index, (tick, value) in
                                  enumerate(edges[:-1])
                                  if value == 0 and low <= tick < high and
                                  edges[index + 1][1] == 1]
                        self.assertGreater(len(widths), 5)
                        self.assertLessEqual(abs(statistics.median(widths) -
                                                 expected), 1)

    def test_air_adc_step_cc3_late_change_has_constant_adc_control(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                  "MA17_ADC10_STEP_CH",
                                                  "MA17_OVERRIDE_", "MA17_TRACE_"))}
            environment.update({"MA17_ADC10_CH2": "400", "MA17_ADC_CH7": "63"})
            output = Path(directory)
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                 "--stop-ticks", "1600000", "--seconds", "25",
                 "--output-dir", str(output)],
                capture_output=True, text=True, env=environment,
                timeout=30, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((output / "execution.json").read_text())
            self.assertEqual(report["firmware_sha256"],
                             hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
            self.assertEqual([row["after"] for row in
                              report["sensor_ram_observation"]["62"]
                              if row["source_pc"] == "0744"], ["64"])
            decay = [row for row in report["engine_ram_observation"]["87"]
                     if row["before"] == "1A" and row["after"] == "18"]
            self.assertEqual(len(decay), 1)
            self.assertEqual(decay[0]["source_pc"], "155B")
            self.assertTrue(1072500 <= decay[0]["tick"] <= 1073500)
            log = (output / "emulator-trace.log").read_text()
            entries = [(int(tick), int(value, 16)) for tick, value in
                       re.findall(r"\[CC3-ENTRY\] instr=(\d+).*?"
                                  r"IRAM14_15=([0-9A-F]{4})", log)]
            self.assertEqual({value for tick, value in entries
                              if 800000 <= tick < 1060000}, {1440})
            self.assertEqual({value for tick, value in entries
                              if 1100000 <= tick < 1500000}, {1422})

    def test_air_adc_step_after_87_decay_isolates_cc3_change(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (("G down", REFERENCE, 400, 160, "28", "3C", 1422,
                  1336, 5677, 5333),
                 ("S88 down", VARIANTS /
                  "tipo 1.6 alcool27c256 SUN 8817.bin", 400, 160,
                  "28", "3C", 1422, 1336, 5677, 5333),
                 ("G up", REFERENCE, 160, 400, "64", "40", 1336,
                  1422, 5333, 5677))
        with tempfile.TemporaryDirectory() as directory:
            for (name, firmware, initial, stepped, ram62, ram48,
                 before_raw, after_raw, before_width, after_width) in cases:
                with self.subTest(name=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_CH",
                                                          "MA17_ADC10_STEP_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    environment.update({"MA17_ADC10_CH2": str(initial),
                                        "MA17_ADC10_STEP_CH2": f"1200000:{stepped}",
                                        "MA17_ADC_CH7": "63"})
                    output = Path(directory) / name.replace(" ", "_")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "1900000", "--seconds", "25",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    sensor = [row for row in report["sensor_ram_observation"]["62"]
                              if row["source_pc"] == "0744"]
                    self.assertEqual(sensor[-1]["after"], ram62)
                    self.assertTrue(1200000 < sensor[-1]["tick"] < 1210000)
                    iram48 = report["engine_ram_observation"]["48"][-1]
                    self.assertEqual(iram48["after"], ram48)
                    self.assertTrue(1210000 < iram48["tick"] < 1220000)
                    decays = [row for row in report["engine_ram_observation"]["87"]
                              if row["before"] == "1A" and row["after"] == "18"]
                    self.assertEqual(len(decays), 1)
                    self.assertLess(decays[0]["tick"], 1200000)
                    log = (output / "emulator-trace.log").read_text()
                    entries = [(int(tick), int(value, 16)) for tick, value in
                               re.findall(r"\[CC3-ENTRY\] instr=(\d+).*?"
                                          r"IRAM14_15=([0-9A-F]{4})", log)]
                    edges = [(int(tick), int(value)) for tick, value in
                             re.findall(r"\[CC3-PIN\] tick=(\d+).*?value=(\d)",
                                        log)]
                    for lo, hi, raw, width in ((1100000, 1200000, before_raw,
                                                before_width),
                                               (1230000, 1800000, after_raw,
                                                after_width)):
                        values = [value for tick, value in entries
                                  if lo <= tick < hi]
                        self.assertGreaterEqual(len(values), 3)
                        self.assertEqual(set(values), {raw})
                        widths = [edges[index + 1][0] - tick
                                  for index, (tick, value) in
                                  enumerate(edges[:-1])
                                  if value == 0 and lo <= tick < hi and
                                  edges[index + 1][1] == 1]
                        self.assertGreaterEqual(len(widths), 3)
                        self.assertLessEqual(abs(statistics.median(widths) -
                                                 width), 1)

    def test_coolant_adc_step_changes_cc3_after_87_decay(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (REFERENCE, sun):
                observations = {}
                for stepped in (False, True):
                    with self.subTest(firmware=firmware.name, stepped=stepped):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_ADC10_STEP_CH",
                                                              "MA17_OVERRIDE_",
                                                              "MA17_TRACE_"))}
                        environment.update({"MA17_ADC10_CH2": "400",
                                            "MA17_ADC10_CH3": "320",
                                            "MA17_ADC_CH7": "63"})
                        if stepped:
                            environment["MA17_ADC10_STEP_CH3"] = "1200000:160"
                        output = Path(directory) / firmware.stem / str(stepped)
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "1900000", "--seconds", "25",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertEqual(report["sensor_ram_observation"]["62"][-1]
                                         ["after"], "64")
                        coolant = [row for row in
                                   report["sensor_ram_observation"]["63"]
                                   if row["source_pc"] == "4756"]
                        self.assertEqual([row["after"] for row in coolant],
                                         ["50", "28"] if stepped else ["50"])
                        if stepped:
                            self.assertTrue(1200000 < coolant[-1]["tick"] <
                                            1220000)
                        decays = [row for row in
                                  report["engine_ram_observation"]["87"]
                                  if row["before"] == "1A" and
                                  row["after"] == "18"]
                        self.assertEqual(len(decays), 1)
                        self.assertLess(decays[0]["tick"], 1200000)
                        log = (output / "emulator-trace.log").read_text()
                        entries = [(int(tick), int(value, 16)) for tick, value in
                                   re.findall(r"\[CC3-ENTRY\] instr=(\d+).*?"
                                              r"IRAM14_15=([0-9A-F]{4})", log)]
                        edges = [(int(tick), int(value)) for tick, value in
                                 re.findall(r"\[CC3-PIN\] tick=(\d+).*?"
                                            r"value=(\d)", log)]
                        windows = []
                        for lo, hi in ((1100000, 1200000),
                                       (1230000, 1800000)):
                            values = [value for tick, value in entries
                                      if lo <= tick < hi]
                            widths = [edges[index + 1][0] - tick
                                      for index, (tick, value) in
                                      enumerate(edges[:-1])
                                      if value == 0 and lo <= tick < hi and
                                      edges[index + 1][1] == 1]
                            self.assertGreaterEqual(len(values), 3)
                            self.assertGreaterEqual(len(widths), 3)
                            windows.append((set(values), statistics.median(widths)))
                        observations[stepped] = windows
                before, after = observations[True]
                control_before, control_after = observations[False]
                self.assertEqual(before[0], {1422})
                self.assertEqual(control_before[0], {1422})
                self.assertEqual(control_after[0], {1422})
                self.assertEqual(after[0], {1326})
                self.assertLessEqual(abs(after[1] - 5293), 1)
                self.assertLessEqual(abs(control_after[1] - 5677), 1)

    def test_coolant_upward_step_crosses_firmware_jump_limit(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        # 160/4=28h. The ROM compares the upward delta with 0Ch at 4671h.
        cases = ((204, "33", "33", False, None, True),
                 (208, "34", "11", True, None, False),
                 (212, "35", "11", True, None, False),
                 (204, "33", "33", False, "468A:7265:50", False))
        with tempfile.TemporaryDirectory() as directory:
            for adc10, raw, processed, fallback, override, reads_7266 in cases:
                with self.subTest(adc10=adc10, override=override):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_CH",
                                                          "MA17_ADC10_STEP_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    environment.update({"MA17_ADC10_CH2": "400",
                                        "MA17_ADC10_CH3": "160",
                                        "MA17_ADC10_STEP_CH3":
                                        f"1200000:{adc10}",
                                        "MA17_ADC_CH7": "63"})
                    if override:
                        environment["MA17_OVERRIDE_MOVC_AT"] = override
                    environment["MA17_TRACE_COOLANT_GATE"] = "1"
                    output = Path(directory) / f"{adc10}_{override or 'control'}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "1450000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=25, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["sensor_ram_observation"]["A8"]
                                     [-1]["after"], raw)
                    self.assertEqual(report["sensor_ram_observation"]["63"]
                                     [-1]["after"], processed)
                    self.assertEqual("474E" in
                                     (output / "pc-hits.txt").read_text(), fallback)
                    reads = report["movc_observation"]["reads"]
                    self.assertTrue(any(row["pc"] == "468A" and
                                        row["address"] == "7265" and
                                        row["value"] == "31" for row in reads))
                    self.assertEqual(any(row["pc"] == "46AB" and
                                         row["address"] == "7266" and
                                         row["value"] == "1E" for row in reads),
                                     reads_7266)
                    gate = [line for line in
                            (output / "emulator-trace.log").read_text().splitlines()
                            if line.startswith("[COOLANT-GATE]") and
                            f"A8={raw}" in line and
                            int(line.split("tick=")[1].split()[0]) > 1200000]
                    self.assertTrue(any("PC=465D" in line for line in gate))
                    self.assertTrue(any("PC=4756" in line and
                                        f"F28={'26' if fallback else '06'}" in line
                                        for line in gate))
                    self.assertEqual(any("PC=467C" in line for line in gate),
                                     not fallback)

    def test_two_coolant_steps_expose_guarded_7267_to_7269_reads(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        steps = [{"tick": 1200000, "value": 204},
                 {"tick": 1450000, "value": 224}]
        sun = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
        with tempfile.TemporaryDirectory() as directory:
            for firmware, override in ((firmware, override)
                                       for firmware in (REFERENCE, sun)
                                       for override in (False, True)):
                with self.subTest(firmware=firmware.name, override=override):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_CH",
                                                          "MA17_ADC10_STEP_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    environment.update({"MA17_ADC10_CH2": "400",
                                        "MA17_ADC10_CH3": "160",
                                        "MA17_ADC10_STEP_CH3":
                                        "1200000:204,1450000:224",
                                        "MA17_ADC_CH7": "63",
                                        "MA17_TRACE_COOLANT_GATE": "1"})
                    if override:
                        environment["MA17_OVERRIDE_MOVC_AT"] = "46AB:7266:01"
                    output = Path(directory) / firmware.stem / str(override)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "3000000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertTrue(report["coolant_gate_trace_enabled"])
                    self.assertEqual(report["adc_10bit_step_sequences"][3], steps)
                    self.assertEqual(report["adc_10bit_step_values"][3], steps[0])
                    self.assertEqual(report["sensor_ram_observation"]["A8"]
                                     [-1]["after"], "38")
                    self.assertEqual(report["sensor_ram_observation"]["63"]
                                     [-1]["after"], "32" if override else "38")
                    reads = report["movc_observation"]["reads"]
                    addresses = {row["address"] for row in reads
                                 if row["address"] in
                                 ("7265", "7266", "7267", "7268", "7269")}
                    self.assertEqual(addresses,
                                     {"7265", "7266", "7267", "7268", "7269"}
                                     if override else {"7265", "7266"})
                    log = (output / "emulator-trace.log").read_text()
                    expected_decay = "00" if override else "1D"
                    self.assertIn("[COOLANT-DECAY]", log)
                    self.assertIn(f"PC=3286 addr=F8D7 value={expected_decay}", log)
                    initial = "01" if override else "1E"
                    self.assertIn(f"PC=3286 addr=F8D7 value={initial}->"
                                  f"{expected_decay}", log)
                    self.assertEqual("PC=46E6" in log, override)
                    if override:
                        self.assertIn("original=1E supplied=01", log)
                        self.assertRegex(log, r"\[COOLANT-GATE\].*"
                                              r"PC=4756 R2=38 R3=32 R5=17 R6=03")

    def test_adc_step_sequence_rejects_invalid_order_and_length(self):
        cases = ("120:200,100:100", "120:200,",
                 ",".join(f"{tick}:100" for tick in range(1, 10)))
        with tempfile.TemporaryDirectory() as directory:
            for index, setting in enumerate(cases):
                with self.subTest(setting=setting):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_ADC10_STEP_CH")}
                    environment["MA17_ADC10_STEP_CH3"] = setting
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--stop-ticks", "1000",
                         "--output-dir", str(Path(directory) / str(index))],
                        capture_output=True, text=True, env=environment,
                        timeout=5, check=False)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("MA17_ADC10_STEP_CH3", result.stderr)
        if (ROOT / "build" / "emu8051-tty").exists():
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith("MA17_ADC10_STEP_CH")}
            environment.update({"MA17_ADC10_STEP_CH3": "-1:160",
                                "MA17_STOP_TICKS": "20000"})
            result = subprocess.run(
                [str(ROOT / "build" / "emu8051-tty"), str(REFERENCE), "--8052"],
                capture_output=True, text=True, env=environment,
                timeout=5, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid MA17_ADC10_STEP_CH3", result.stderr)

    @unittest.skipUnless(os.environ.get("MA17_RUN_SLOW") == "1",
                         "set MA17_RUN_SLOW=1 for the 68M-tick natural path")
    def test_original_coolant_counter_reaches_7267_to_7269(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                              "MA17_ADC10_STEP_CH", "MA17_OVERRIDE_",
                                              "MA17_TRACE_"))}
        environment.update({"MA17_ADC10_CH2": "400",
                            "MA17_ADC10_CH3": "160",
                            "MA17_ADC10_STEP_CH3": "1200000:204,1450000:224",
                            "MA17_ADC_CH7": "63",
                            "MA17_TRACE_COOLANT_GATE": "1"})
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--trace-movc", "--no-kline-inject", "--crank-immediate",
                 "--rpm", "1000", "--stop-ticks", "68000000",
                 "--seconds", "150", "--output-dir", directory],
                capture_output=True, text=True, env=environment,
                timeout=160, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            report = json.loads((Path(directory) / "execution.json").read_text())
            self.assertEqual(report["firmware_sha256"],
                             hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
            self.assertIsNone(report["movc_override_at_hex"])
            self.assertEqual(report["stop_ticks_observed"], 68000000)
            coolant = report["sensor_ram_observation"]["63"][-1]
            self.assertEqual((coolant["before"], coolant["after"],
                              coolant["source_pc"]), ("38", "32", "4756"))
            self.assertTrue(67000000 < coolant["tick"] < 68000000)
            reads = {row["address"]: row["count"] for row in
                     report["movc_observation"]["reads"]
                     if row["address"] in ("7267", "7268", "7269")}
            self.assertEqual(reads, {"7267": 1, "7268": 1, "7269": 1})
            log = (Path(directory) / "emulator-trace.log").read_text()
            self.assertIn("PC=3286 addr=F8D7 value=0F->0E", log)
            self.assertIn("PC=476E addr=F8D7 value=0E->0F", log)

    def test_iram87_gate_tables_are_read_in_g_and_s88(self):
        for name, firmware in (("G", REFERENCE),
                               *((name, VARIANTS / name) for name in EXPECTED)):
            with self.subTest(rom=name):
                image = firmware.read_bytes()
                self.assertEqual(image[0x70D8:0x70DC],
                                 bytes.fromhex("79 CE 79 D8"))
                self.assertEqual(image[0x79CE:0x79D8],
                                 bytes.fromhex("FB F8 F3 EE EC E9 E4 DF DA D7"))
                self.assertEqual(image[0x79D8:0x79E0],
                                 bytes.fromhex("FF FF FF FF FF DA A6 5A"))
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for name, firmware in (("G", REFERENCE),
                                   ("S88", VARIANTS /
                                    "tipo 1.6 alcool27c256 SUN 8817.bin")):
                with self.subTest(trace=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_CH",
                                                          "MA17_ADC10_STEP_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    environment.update({"MA17_ADC10_CH2": "400",
                                        "MA17_ADC_CH7": "63",
                                        "MA17_TRACE_LAMBDA": "1"})
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000", "--trace-movc",
                         "--stop-ticks", "1600000", "--seconds", "25",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertTrue(any(row["after"] == "A0" and
                                        row["source_pc"] == "125E"
                                        for row in report["engine_ram_observation"]["6A"]))
                    self.assertTrue(any(row["before"] == "1A" and
                                        row["after"] == "18" and
                                        row["source_pc"] == "155B"
                                        for row in report["engine_ram_observation"]["87"]))
                    reads = {(row["pc"], row["mapped"], row["value"]):
                             row["count"] for row in
                             report["movc_observation"]["reads"]}
                    self.assertGreater(reads.get(("532F", "79D1", "EE"), 0), 0)
                    self.assertGreater(reads.get(("5333", "79D2", "EC"), 0), 0)
                    self.assertGreater(reads.get(("1576", "79D9", "FF"), 0), 100)
                    log = (output / "emulator-trace.log").read_text()
                    self.assertRegex(log, r"\[LAMBDA-GATE\].*PC=155A.*"
                                          r"RAM87=1A A=EE B=1A")
                    self.assertRegex(log, r"\[LAMBDA-GATE\].*PC=155B.*"
                                          r"RAM87=1A A=2C B=18")

    def test_79d8_movc_result_changes_cc3_without_rom_patch(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (("G", REFERENCE, 1286, 1427, 5133, 5697),
                 ("S88", VARIANTS /
                  "tipo 1.6 alcool27c256 SUN 8817.bin", 1596, 1774,
                  6373, 7085))
        with tempfile.TemporaryDirectory() as directory:
            for (name, firmware, original_raw, supplied_raw, original_width,
                 supplied_width) in cases:
                observations = []
                for override in (False, True):
                    with self.subTest(rom=name, override=override):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_ADC10_STEP_CH",
                                                              "MA17_OVERRIDE_",
                                                              "MA17_TRACE_"))}
                        environment.update({"MA17_ADC_CH0": "180",
                                            "MA17_ADC_CH6": "247",
                                            "MA17_ADC10_CH2": "400",
                                            "MA17_ADC_CH7": "63"})
                        if override:
                            environment["MA17_OVERRIDE_MOVC_AT"] = "1576:79DF:FF"
                        output = Path(directory) / f"{name}_{int(override)}"
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000", "--trace-movc",
                             "--stop-ticks", "1600000", "--seconds", "25",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0,
                                         result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertEqual(report["movc_override_at_hex"],
                                         "1576:79DF:FF" if override else None)
                        reads = [row for row in report["movc_observation"]["reads"]
                                 if row["pc"] == "1576"]
                        self.assertEqual({(row["mapped"], row["value"])
                                          for row in reads}, {("79DF", "5A")})
                        self.assertGreater(sum(row["count"] for row in reads), 100)
                        self.assertTrue(any(row["after"] == "07" for row in
                                            report["engine_ram_observation"]["6A"]))
                        log = (output / "emulator-trace.log").read_text()
                        if override:
                            self.assertIn("PC=1576 mapped=79DF "
                                          "original=5A supplied=FF", log)
                        entries = [(int(tick), int(value, 16)) for tick, value in
                                   re.findall(r"\[CC3-ENTRY\] instr=(\d+).*?"
                                              r"IRAM14_15=([0-9A-F]{4})", log)]
                        raw = [value for tick, value in entries
                               if 400000 <= tick < 800000]
                        edges = [(int(tick), int(value)) for tick, value in
                                 re.findall(r"\[CC3-PIN\] tick=(\d+).*?"
                                            r"value=(\d)", log)]
                        widths = [edges[index + 1][0] - tick
                                  for index, (tick, value) in
                                  enumerate(edges[:-1])
                                  if value == 0 and 400000 <= tick < 800000 and
                                  edges[index + 1][1] == 1]
                        self.assertGreater(len(raw), 10)
                        self.assertGreater(len(widths), 10)
                        self.assertEqual(set(raw),
                                         {supplied_raw if override else original_raw})
                        self.assertLessEqual(abs(statistics.median(widths) -
                                                 (supplied_width if override else
                                                  original_width)), 1)
                        observations.append(report)
                baseline, supplied = observations
                self.assertEqual(baseline["engine_ram_observation"]["48"],
                                 supplied["engine_ram_observation"]["48"])
                self.assertEqual(baseline["engine_ram_observation"]["87"],
                                 supplied["engine_ram_observation"]["87"])
                self.assertNotEqual(baseline["engine_ram_observation"]["5A"],
                                    supplied["engine_ram_observation"]["5A"])

    def test_point_movc_override_requires_trace_and_fixed_hex_format(self):
        for specification, arguments, message in (
                ("1576:79DF:FF", [], "requires --trace-movc"),
                ("1576:79DF:XYZ", ["--trace-movc"],
                 "must be PC:ADDRESS:VALUE")):
            with self.subTest(specification=specification, arguments=arguments):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_OVERRIDE_")}
                environment["MA17_OVERRIDE_MOVC_AT"] = specification
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     *arguments], capture_output=True, text=True,
                    env=environment, timeout=10, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_79d8_indices_five_six_seven_are_reached_by_adc_pairs(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((60, "15", "05", "79DD", "DA"),
                 (100, "06", "06", "79DE", "A6"),
                 (180, "07", "07", "79DF", "5A"))
        with tempfile.TemporaryDirectory() as directory:
            for name, firmware in (("G", REFERENCE),
                                   ("S88", VARIANTS /
                                    "tipo 1.6 alcool27c256 SUN 8817.bin")):
                for adc0, ram6a, index, address, byte in cases:
                    with self.subTest(rom=name, adc0=adc0):
                        environment = {key: value for key, value in
                                       os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_CH",
                                                              "MA17_ADC10_STEP_CH",
                                                              "MA17_OVERRIDE_",
                                                              "MA17_TRACE_"))}
                        environment.update({"MA17_ADC_CH0": str(adc0),
                                            "MA17_ADC_CH6": "247",
                                            "MA17_ADC10_CH2": "400",
                                            "MA17_ADC_CH7": "63"})
                        output = Path(directory) / f"{name}_{adc0}"
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000", "--trace-movc",
                             "--stop-ticks", "500000", "--seconds", "25",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0,
                                         result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes()).hexdigest())
                        self.assertEqual(report["engine_ram_observation"]["6A"]
                                         [-1]["after"], ram6a)
                        reads = [row for row in
                                 report["movc_observation"]["reads"]
                                 if row["pc"] == "1576"]
                        self.assertEqual({(row["acc"], row["mapped"],
                                           row["value"]) for row in reads},
                                         {(index, address, byte)})
                        self.assertGreater(sum(row["count"] for row in reads),
                                           20)

    def test_coolant_adc_opens_flag_selected_matrix_path(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        # These are raw digital stimuli, not calibrated temperatures. ADC2
        # holds the 22h.6 state; ADC3 crosses the ROM[721Dh] comparison.
        with tempfile.TemporaryDirectory() as directory:
            for adc3, expected_ram63, matrix_access in (
                    (80, "50", False), (20, "14", True)):
                with self.subTest(adc3=adc3):
                    output = Path(directory) / str(adc3)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_ADC10_CH",
                                                          "MA17_OVERRIDE_",
                                                          "MA17_TRACE_"))}
                    environment.update({"MA17_ADC_CH0": "180",
                                        "MA17_ADC_CH2": "220",
                                        "MA17_ADC_CH3": str(adc3),
                                        "MA17_ADC_CH6": "247",
                                        "MA17_ADC_CH7": "63",
                                        "MA17_TRACE_AIR_716C_GATE": "1"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "400000", "--seconds", "8",
                         "--trace-movc", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=20, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    self.assertEqual(report["sensor_ram_observation"]["63"][-1]
                                     ["after"], expected_ram63)
                    gate = report["air_gate_observation"]
                    self.assertGreater(gate["2e6_set_at_3cb7"], 0)
                    self.assertGreater(gate["r2_below_6f_at_3cb7"], 0)
                    self.assertEqual(gate["carry_set_at_3d0c"] > 0,
                                     matrix_access)
                    reads = sum(entry["count"] for entry in
                                report["movc_observation"]["reads"]
                                if 0x7CAE <= int(entry["address"], 16) < 0x7D26)
                    self.assertEqual(reads > 0, matrix_access)

    def test_lambda_bound_countdowns_reach_first_reload_in_full_firmware(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for adc5 in (40, 200):
                with self.subTest(adc5=adc5):
                    output = Path(directory) / str(adc5)
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC_CH",
                                                          "MA17_OVERRIDE_"))}
                    environment.update({"MA17_ADC_CH3": "4",
                                        "MA17_ADC_CH5": str(adc5),
                                        "MA17_ADC_CH7": "63",
                                        "MA17_TRACE_LAMBDA_BOUNDS": "1"})
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "3200000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertTrue(report["lambda_bound_trace_enabled"])
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
                    if adc5 == 40:
                        control_env = dict(environment)
                        control_env.pop("MA17_TRACE_LAMBDA_BOUNDS")
                        control = Path(directory) / "control"
                        control_run = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "3200000", "--seconds", "20",
                             "--output-dir", str(control)],
                            capture_output=True, text=True, env=control_env,
                            timeout=30, check=False)
                        self.assertEqual(control_run.returncode, 0,
                                         control_run.stderr[-1500:])
                        baseline = json.loads((control / "execution.json").read_text())
                        for key in ("pc_coverage", "cc3_observation",
                                    "adaptation_xram_observation",
                                    "sensor_ram_observation", "engine_ram_observation"):
                            self.assertEqual(report[key], baseline[key], key)
                    changes = report["lambda_bound_xram_observation"]
                    for address, initial, after, decrement_pc, reload_pc in (
                            ("F8E8", "0A", "09", "16EA", None),
                            ("F8E9", "1E", "1E", "16D8", "16DE"),
                            ("F8EA", "0F", "0E", "16CC", None),
                            ("F8EB", "1E", "1E", "16BA", "16C0")):
                        with self.subTest(adc5=adc5, address=address):
                            events = changes[address]
                            self.assertTrue(any(row["after"] == initial and
                                                row["tick"] < 10000 for row in events))
                            self.assertEqual(events[-1]["after"], after)
                            self.assertEqual(events[-1]["source_pc"],
                                             decrement_pc if reload_pc is None else reload_pc)
                            self.assertTrue(3100000 < events[-1]["tick"] < 3150000)
                            if reload_pc:
                                self.assertTrue(any(row["before"] == "01" and
                                                    row["after"] == "00" and
                                                    row["source_pc"] == decrement_pc
                                                    for row in events))

    def test_lambda_xram_read_probe_preserves_boot_self_test(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for adc5, expected_final, expected_width in ((40, "CB", 4646.5),
                                                         (200, "68", 4333)):
                for override in (False, True):
                    with self.subTest(adc5=adc5, override=override):
                        output = Path(directory) / f"{adc5}_{override}"
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({"MA17_ADC_CH3": "4",
                                            "MA17_ADC_CH5": str(adc5),
                                            "MA17_ADC_CH7": "63",
                                            "MA17_TRACE_LAMBDA": "1",
                                            "MA17_TRACE_XRAM_F80C": "1"})
                        if override:
                            environment["MA17_OVERRIDE_XRAM_F80C"] = "80"
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "2400000", "--seconds", "20",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["adaptation_xram_observation"]["F80C"]
                                         [-1]["after"], expected_final)
                        self.assertEqual(report["cc3_observation"]
                                         ["cc3_pin_model_median_low_width_ticks"],
                                         expected_width)
                        lines = (output / "emulator-trace.log").read_text().splitlines()
                        reads = [line for line in lines if line.startswith("[XRAM-READ]")]
                        self.assertEqual(len(reads), 1)
                        self.assertIn("PC=55A2 addr=F80C stored=55", reads[0])
                        self.assertFalse(any(line.startswith("[XRAM-OVERRIDE]")
                                             for line in lines))
                        writes = [dict(field.split("=") for field in line.split()[1:])
                                  for line in lines if line.startswith("[LAMBDA-GATE]")
                                  and "PC=19D0" in line and
                                  int(line.split("tick=")[1].split()[0]) > 1200000]
                        self.assertGreater(len(writes), 100)
                        for row in writes:
                            word = (int(row["R7"], 16) << 8) | int(row["R6"], 16)
                            signed = word - 0x10000 if word & 0x8000 else word
                            encoded = max(0, min(255, 128 + (signed >> 7)))
                            self.assertEqual(int(row["A"], 16), encoded,
                                             (adc5, row["tick"]))

    def test_injection_flow_pairs_deduplicate_delayed_ticks(self):
        rows = [{"tick": tick, "pc": pc, "r2r3": value,
                 "ram63": "29", "ram78": "F3"}
                for tick, pc, value in
                ((1, "1DD8", "1234"), (2, "1DD8", "1234"),
                 (5, "1E02", "1234"), (6, "1E02", "1234"),
                 (101, "1DD8", "1234"), (105, "1E02", "2234"))]
        result = summarize_injection_flow(rows)
        self.assertEqual(result["stage_samples"], {"1DD8": 2, "1E02": 2})
        self.assertEqual(result["paired_checks"], 2)
        self.assertEqual(result["unchanged_r2r3_pairs"], 1)
        self.assertEqual(result["changed_r2r3_pairs"], 1)

    def test_trace_stops_at_exact_emulated_tick(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--seconds", "10", "--stop-ticks", "100000",
                 "--no-kline-inject", "--crank-immediate", "--output-dir", directory],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((Path(directory) / "execution.json").read_text())
            self.assertEqual(report["stop_ticks_target"], 100000)
            self.assertEqual(report["stop_ticks_observed"], 100000)
            self.assertEqual(report["emulator_exit"], 0)
            flow = report["injection_flow_observation"]
            self.assertGreater(flow["paired_checks"], 0)
            self.assertEqual(flow["paired_checks"],
                             flow["unchanged_r2r3_pairs"] + flow["changed_r2r3_pairs"])

    def test_movc_trace_records_actual_rom_reads(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--trace-movc", "--trace-lookup", "--seconds", "10",
                 "--stop-ticks", "600000",
                 "--no-kline-inject",
                 "--crank-immediate", "--output-dir", directory],
                capture_output=True, text=True,
                env={**{key: value for key, value in os.environ.items()
                         if not key.startswith("MA17_ADC_CH")}, "MA17_ADC_CH1": "40"})
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((Path(directory) / "execution.json").read_text())
            observed = report["movc_observation"]
            self.assertTrue(observed["enabled"])
            lookup = report["lookup_observation"]
            self.assertTrue(lookup["enabled"])
            self.assertGreater(lookup["total_calls"], 0)
            self.assertEqual(sum(row["count"] for row in lookup["states"]),
                             lookup["total_calls"])
            self.assertGreater(observed["total_reads"], 100)
            self.assertEqual({row["opcode"] for row in observed["reads"]}, {"83", "93"})
            rom = REFERENCE.read_bytes()
            for row in observed["reads"]:
                self.assertEqual(int(row["value"], 16), rom[int(row["mapped"], 16)])
            self.assertTrue(any(row["pc"] == "5289" and row["address"] == "7B45"
                                for row in observed["reads"]))
            cells = {(row["pc"], int(row["mapped"], 16) - 0x7ED9)
                     for row in observed["reads"] if row["dptr"] == "7ED9"}
            self.assertTrue({("532F", 3), ("5333", 4), ("534B", 13),
                             ("5350", 14)} <= cells)
            self.assertEqual(REFERENCE.read_bytes()[0x7B32 + 1] *
                             REFERENCE.read_bytes()[0x7B3E + 1], 60)

    def test_trace_rejects_different_code_prefix(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
             "--firmware", str(VARIANTS / EXPECTED[0])],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identical code prefix", result.stderr)

    def test_sun8817_changes_emulated_p5_width(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        values = []
        lookup_results = []
        with tempfile.TemporaryDirectory() as directory:
            for index, firmware in enumerate((REFERENCE, VARIANTS / EXPECTED[2])):
                output = Path(directory) / str(index)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--firmware", str(firmware), "--seconds", "15",
                     "--stop-ticks", "2400000", "--trace-lookup",
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                     "--output-dir", str(output)],
                    capture_output=True, text=True,
                    env={key: value for key, value in os.environ.items()
                         if not key.startswith("MA17_ADC_CH")})
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(firmware.read_bytes()).hexdigest())
                self.assertGreaterEqual(report["output_latches"]["P5.0"]["low_starts"], 3)
                self.assertEqual(report["stop_ticks_observed"], 2400000)
                self.assertEqual(report["wheel_observation"]["complete_revolutions"], 39)
                self.assertEqual(report["engine_ram_observation"].get("57", []), [])
                self.assertEqual({row["selector"] for row in
                                  report["lookup_observation"]["states"]}, {"00"})
                values.append(report["output_latches"]["P5.0"]["median_low_width_ticks"])
                steady = max((row for row in report["lookup_observation"]["states"]
                              if row["rpm"] == "28" and row["load"] == "27"),
                             key=lambda row: row["count"])
                lookup_results.append((steady["r5"], steady["r6"],
                                       steady["result_a"], steady["result_b"]))
        self.assertAlmostEqual(values[0], 1861, delta=2)
        self.assertAlmostEqual(values[1], 1921, delta=2)
        self.assertGreater(values[1] - values[0], 50)
        self.assertEqual(lookup_results, [("30", "00", "37", "C0"),
                                          ("32", "10", "41", "C0")])


if __name__ == "__main__":
    unittest.main()
