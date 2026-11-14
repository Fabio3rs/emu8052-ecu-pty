"""Regressions for exact code-span alignment across shifted ROM layouts."""

import random
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from align_ma17_variants import align, unique_windows


class AlignMa17VariantsTests(unittest.TestCase):
    def test_ram57_direct_zero_initializers_align_across_six_roms(self):
        names = ("tipo 1.6 alcool27c256.bin",
                 "tipo 1.6 alcool27c256+1.5bar.bin",
                 "tipo 1.6 alcool27c256 SUN 8817.bin",
                 "tipo 1.6 alcool27c256 SUN 37a5.bin",
                 "tipo 1.6 alcool27c256 SUN 36fd.bin")
        images = [ROOT / "FiatTipo_MA17_dump_27c256.bin",
                  *(ROOT / "firmwares_modificados_ma17_tipo" / name
                    for name in names)]
        for image in images:
            with self.subTest(image=image.name):
                rom = image.read_bytes()
                sites = [offset for offset in range(len(rom))
                         if rom.startswith(b"\x75\x57\x00", offset)]
                expected_second = (0x3B94 if image == images[0] or
                                   "SUN 8817" in image.name else 0x3BC2)
                self.assertEqual(sites, [0x0B0F, expected_second])

    def test_coolant_adc_validation_relocates_without_changing_logic(self):
        reference = (ROOT / "FiatTipo_MA17_dump_27c256.bin").read_bytes()
        start, end = 0x4629, 0x4759
        anchor = reference[start:0x4648]
        jump_offsets = (0x464E, 0x465A, 0x4675, 0x4683, 0x4694,
                        0x4699, 0x46B3, 0x46B6, 0x46C3)
        names = ("tipo 1.6 alcool27c256.bin",
                 "tipo 1.6 alcool27c256+1.5bar.bin",
                 "tipo 1.6 alcool27c256 SUN 8817.bin",
                 "tipo 1.6 alcool27c256 SUN 37a5.bin",
                 "tipo 1.6 alcool27c256 SUN 36fd.bin")
        for name in names:
            with self.subTest(variant=name):
                image = (ROOT / "firmwares_modificados_ma17_tipo" / name).read_bytes()
                positions = [offset for offset in range(len(image))
                             if image.startswith(anchor, offset)]
                self.assertEqual(len(positions), 1)
                variant_start = positions[0]
                self.assertIn(variant_start, (0x4629, 0x46E6))
                delta = variant_start - start
                normalized = bytearray(image[variant_start:variant_start + end - start])
                for address in jump_offsets:
                    variant_address = address + delta
                    self.assertEqual(reference[address], image[variant_address])
                    self.assertEqual(reference[address], 0x02)  # LJMP addr16
                    target = int.from_bytes(reference[address + 1:address + 3], "big")
                    relocated = int.from_bytes(image[variant_address + 1:
                                                     variant_address + 3], "big")
                    self.assertTrue(start <= target < end)
                    self.assertEqual(relocated, target + delta)
                    relative = address - start
                    normalized[relative + 1:relative + 3] = reference[
                        address + 1:address + 3]
                self.assertEqual(normalized, reference[start:end])
                self.assertEqual(image[0x4645 + delta:0x4647 + delta],
                                 b"\xb4\x04")
                self.assertEqual(image[0x4651 + delta:0x4653 + delta],
                                 b"\xb4\xe8")

    def test_lambda_secondary_guard_homology_in_six_original_roms(self):
        reference = (ROOT / "FiatTipo_MA17_dump_27c256.bin").read_bytes()
        variants = {
            "tipo 1.6 alcool27c256.bin": 0x1C,
            "tipo 1.6 alcool27c256+1.5bar.bin": 0x1C,
            "tipo 1.6 alcool27c256 SUN 8817.bin": 0,
            "tipo 1.6 alcool27c256 SUN 37a5.bin": 0x1C,
            "tipo 1.6 alcool27c256 SUN 36fd.bin": 0x1C,
        }
        for name, delta in variants.items():
            with self.subTest(variant=name):
                image = (ROOT / "firmwares_modificados_ma17_tipo" / name).read_bytes()
                self.assertEqual(len(image), len(reference))
                # DPTR=7200h setup and the two MOVC threshold comparisons.
                self.assertEqual(reference[0x16EB:0x1702],
                                 image[0x16EB + delta:0x1702 + delta])
                self.assertEqual(reference[0x17C2:0x1810],
                                 image[0x17C2 + delta:0x1810 + delta])
                self.assertEqual(image[0x7226:0x7228], b"\x44\x2c")

    def test_unique_shifted_code_span(self):
        reference = random.Random(417).randbytes(512)
        variant = b"\xff" * 10 + reference[:502]
        result = align(reference, variant, set(range(502)), set(range(10, 512)),
                       window=16, min_span=64, limit=512)
        self.assertEqual(result["matched_span_bytes"], 502)
        self.assertEqual(result["delta_anchor_counts"], {"10": 487})
        self.assertEqual(result["spans"], [{
            "reference_start": "0x0000", "reference_end_exclusive": "0x01F6",
            "variant_start": "0x000A", "variant_end_exclusive": "0x0200",
            "delta": 10, "bytes": 502}])

    def test_repeated_bytes_and_noncode_are_not_anchors(self):
        image = b"\xaa" * 256
        self.assertEqual(unique_windows(image, set(range(256)), 16, 256), {})
        self.assertEqual(align(image, image, set(), set(), window=16,
                               min_span=64, limit=256)["spans"], [])

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            align(b"abc", b"abc", set(), set(), window=1)
        with self.assertRaises(ValueError):
            align(b"abc", b"abc", set(), set(), window=4, min_span=3)


if __name__ == "__main__":
    unittest.main()
