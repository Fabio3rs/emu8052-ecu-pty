"""Regressions for MA1.7 variant inventory and byte interval reporting."""

import ast
import copy
import hashlib
import json
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
                                   catalog_candidate_tables, catalog_diagnostics,
                                   catalog_matrix_deltas,
                                   catalog_pointer_regions, compare, decode_xxd,
                                   expand_curated_catalog,
                                   inventory, write_matrix_heatmap)
from trace_ma17 import summarize_injection_flow


class CompareVariantsTests(unittest.TestCase):
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
            start = int(table["start"], 16)
            end = int(table["end_exclusive"], 16)
            self.assertGreater(end, start)
            for name, image in images.items():
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

    def test_curated_catalog_covers_changed_pointer_data_before_rom_tail(self):
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
        self.assertFalse({address for address in changed - covered
                          if address < 0x7F9D})
        self.assertEqual(len(changed - covered), 87)
        self.assertEqual(min(changed - covered), 0x7F9F)

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
                self.assertIn(reference.split(" (", 1)[0], known,
                              (table["id"], reference))

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
                    self.assertEqual({line.split("PC=")[1][:4] for line in lines},
                                     {"1B34", "1B3D", "1B48"})
                    self.assertEqual({line.split("R1=")[1][:2] for line in lines},
                                     {r1})
                    self.assertEqual({line.split("R7=")[1][:2] for line in lines},
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

    def test_rpm_extremes_keep_ram78_zero_and_lookup_in_bounds(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = ((300, {("7AB0", "00", "03"), ("7AB0", "2A", "09")},
                  set()),
                 (6000, {("79F0", "2F", "0B"), ("7AB0", "00", "03"),
                         ("7AB0", "2A", "09"), ("7AB0", "2F", "09")},
                  {"1B34", "1B3D", "1B48"}))
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
                    self.assertEqual({line.split("PC=")[1][:4] for line in
                                      log.splitlines() if line.startswith(
                                          "[RAM78-GATE]")}, expected_gates)
                    ram78_reads = re.findall(
                        r"\[INJECTION-FLOW\].* PC=1D4B .*?RAM78=([0-9A-F]{2})",
                        log)
                    self.assertTrue(ram78_reads)
                    self.assertEqual(set(ram78_reads), {"00"})

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
