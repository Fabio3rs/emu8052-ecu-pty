"""Binary round-trip regressions for the MCS-51 toolchain."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "roundtrip_8051.py"


class RoundtripTests(unittest.TestCase):
    def run_roundtrip(self, firmware, *options):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(firmware), "--output-dir", directory,
                 *options], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads((Path(directory) / "report.json").read_text())
            rebuilt = next(Path(directory).glob("*.rebuilt.bin")).read_bytes()
            assembly = next(p for p in Path(directory).glob("*.asm")
                            if not p.name.endswith(".disasm51.asm")).read_text()
            self.assertEqual(rebuilt, firmware.read_bytes())
            self.assertEqual(report["mismatched_bytes"], 0)
            self.assertTrue(report["sha256_equal"])
            self.assertEqual(report["original_size"], report["rebuilt_size"])
            self.assertEqual(report["original_sha256"], hashlib.sha256(rebuilt).hexdigest())
            self.assertGreater(report["code_bytes"], 0)
            return report, assembly

    def test_fiat_tipo_ma17(self):
        report, assembly = self.run_roundtrip(ROOT / "FiatTipo_MA17_dump_27c256.bin")
        self.assertEqual(report["original_size"], 32768)
        self.assertGreater(report["code_bytes"], 20000)
        self.assertIn("djnz 6Bh", assembly)
        self.assertIn("S0RELL DATA 0AAh", assembly)

    def test_renault_clio_ma17(self):
        firmware = ROOT / "Renault_Clio_1.6__0261204510_1037355887_Bosch_1997_.ori"
        report, _ = self.run_roundtrip(firmware)
        self.assertEqual(report["original_size"], 65536)
        self.assertGreater(report["code_bytes"], 20000)

    def test_branches_data_and_erased_tail(self):
        rom = bytearray([0xFF] * 64)
        rom[:3] = bytes([0x02, 0x00, 0x10])  # LJMP 0010h
        rom[0x10:0x19] = bytes([0x74, 0x03, 0xB4, 0x03, 0x02,
                                0xD8, 0xFE, 0x01, 0x20])
        rom[0x20:0x24] = bytes([0x11, 0x30, 0x80, 0xFE])  # ACALL, SJMP
        rom[0x30] = 0x22  # RET; final byte of ROM stays erased
        with tempfile.TemporaryDirectory() as directory:
            firmware = Path(directory) / "branches.bin"
            firmware.write_bytes(rom)
            report, assembly = self.run_roundtrip(firmware)
        self.assertEqual(report["original_size"], 64)
        self.assertIn("ajmp", assembly)
        self.assertIn("acall", assembly)
        self.assertIn("cjne", assembly)
        self.assertIn("djnz", assembly)
        self.assertIn("db 0FFh", assembly)

    def test_indirect_big_endian_words(self):
        rom = bytearray([0xFF] * 64)
        rom[:3] = bytes([0x02, 0x00, 0x10])
        rom[0x10:0x14] = bytes([0x90, 0x00, 0x20, 0x73])  # DPTR; JMP @A+DPTR
        rom[0x20:0x24] = bytes([0x00, 0x30, 0x00, 0x34])
        rom[0x30] = rom[0x34] = 0x22
        with tempfile.TemporaryDirectory() as directory:
            firmware = Path(directory) / "indirect.bin"
            firmware.write_bytes(rom)
            report, assembly = self.run_roundtrip(firmware, "--indirect", "0x20:0x24")
        self.assertEqual(report["original_size"], 64)
        self.assertIn("dw", assembly)
        self.assertIn("jmp @A + DPTR", assembly)

    def test_page_jump_and_mov_direct_operand_order(self):
        rom = bytearray([0xFF] * 0x830)
        rom[:3] = bytes([0x02, 0x07, 0xFE])
        rom[0x7FE:0x800] = bytes([0x01, 0x12])  # AJMP 0812h, next page
        rom[0x812:0x817] = bytes([0x85, 0x20, 0x21, 0x80, 0xFE])
        with tempfile.TemporaryDirectory() as directory:
            firmware = Path(directory) / "page.bin"
            firmware.write_bytes(rom)
            _, assembly = self.run_roundtrip(firmware)
        self.assertIn("mov 21h, 20h", assembly)
        self.assertIn("ajmp", assembly)

    def test_disassembler_offset_maps_absolute_target_to_rom(self):
        with tempfile.TemporaryDirectory() as directory:
            firmware = Path(directory) / "mapped.bin"
            firmware.write_bytes(bytes([0x02, 0x01, 0x06, 0xFF, 0xFF, 0xFF, 0x22]))
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(ROOT / "disasm51" / "src")
            result = subprocess.run(
                [str(ROOT / ".venv" / "bin" / "disasm51"), "--offset", "0x100",
                 str(firmware)], capture_output=True, text=True, env=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("jump_0006:", result.stdout)
        self.assertIn("ljmp jump_0006", result.stdout)


if __name__ == "__main__":
    unittest.main()
