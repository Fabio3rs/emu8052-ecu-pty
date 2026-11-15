"""Original-ROM ADC2 boundaries in the Fiat 716Ch/C8h/7E16h path."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "FiatTipo_MA17_dump_27c256.bin"
A = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin"


def trace(raw, donor=False, matrix_gate=False):
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                          "MA17_TRACE_", "MA17_P4_",
                                          "MA17_ZERO_"))}
    environment.update(
        MA17_ADC_CH0="40", MA17_ADC_CH6="95",
        MA17_ADC10_STEP_CH0="1350000:720",
        MA17_ADC10_STEP_CH6="200000:880,1350000:988",
        MA17_ADC_CH2=str(raw), MA17_ADC_CH3="80", MA17_ADC_CH7="63",
        MA17_P4_6_FORCE_LOW="1", MA17_TRACE_AIR_716C_GATE="1",
        MA17_TRACE_UPPER_CA_CONSUMER="1")
    if matrix_gate:
        environment["MA17_TRACE_MATRIX_PATH"] = "1"
    if donor:
        environment.update(MA17_OVERRIDE_MOVC_MATRIX_ROM=str(A),
                           MA17_OVERRIDE_MOVC_MATRIX_BASE="7E16")
    with tempfile.TemporaryDirectory() as directory:
        run = subprocess.run(
            [sys.executable, str(ROOT / "tools/trace_ma17.py"),
             "--firmware", str(G), "--trace-movc", "--no-kline-inject",
             "--crank-immediate", "--rpm", "1500", "--stop-ticks",
             "2200000", "--seconds", "20", "--output-dir", directory],
            capture_output=True, text=True, env=environment,
            timeout=30, check=False)
        if run.returncode:
            raise AssertionError(run.stderr[-1500:])
        output = Path(directory)
        return (json.loads((output / "execution.json").read_text()),
                (output / "emulator-trace.log").read_text())


def samples(log, prefix, pc):
    return [dict(field.split("=", 1) for field in line.split()[1:])
            for line in log.splitlines()
            if line.startswith(prefix) and f"PC={pc}" in line and
            int(line.split("tick=")[1].split()[0]) >= 1400000]


def original_716c_output(raw):
    """Evaluate the 5314h/532Fh packed-index path using original ROM bytes."""
    packed = ((raw << 4) | (raw >> 4)) & 0xFF
    rotated = (packed >> 1) | ((packed & 1) << 7)
    index, fraction = rotated & 7, rotated & 0xF8
    first, second = G.read_bytes()[0x716C + index:0x716E + index]
    signed_difference = ((second - first + 128) & 0xFF) - 128
    result = (first + signed_difference * fraction // 256) & 0xFF
    return index, fraction, result ^ 0x80


class Adc2ClampBoundaryTests(unittest.TestCase):
    def test_716c_output_crosses_zero_before_selector_flag_changes(self):
        if not (ROOT / "build/emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        expected = {
            (122, False): ("01", 25, 1802.5),
            (122, True): ("01", 43, 1793.5),
            (123, False): ("00", 43, 1784),
            (123, True): ("00", 54, 1784),
        }
        for (raw, donor), (clamp, wins, p5_width) in expected.items():
            with self.subTest(raw=raw, donor=donor):
                self.assertEqual(original_716c_output(raw),
                                 (3, 0xD0 if raw == 122 else 0xD8,
                                  int(clamp, 16)))
                report, log = trace(raw, donor)
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(G.read_bytes()).hexdigest())
                self.assertEqual(report["movc_matrix_donor_sha256"],
                                 hashlib.sha256(A.read_bytes()).hexdigest()
                                 if donor else None)
                self.assertEqual(report["sensor_ram_observation"]["62"][-1]
                                 ["after"], f"{raw:02X}")
                reads = {(r["mapped"], r["value"], r["count"])
                         for r in report["movc_observation"]["reads"]
                         if 0x716C <= int(r["mapped"], 16) < 0x717B}
                self.assertEqual(reads, {("716F", "86", 10),
                                         ("7170", "80", 10)})
                at_397d = samples(log, "[AIR-716C-GATE]", "397D")
                at_39b2 = samples(log, "[UPPER-CA-CONSUMER]", "39B2")
                self.assertGreater(len(at_397d), 50)
                self.assertGreater(len(at_39b2), 50)
                self.assertEqual({(r["UCC"], r["F2F"]) for r in at_397d},
                                 {(clamp, "DE")})
                self.assertEqual({(r["UC8"], r["B"]) for r in at_39b2},
                                 {(clamp, clamp)})
                self.assertEqual(sum(int(r["UCA"], 16) > int(r["B"], 16)
                                     for r in at_39b2), wins)
                self.assertEqual(report["output_latches"]["P5.1"]
                                 ["median_low_width_ticks"], p5_width)
                self.assertEqual(report["cc3_observation"]
                                 ["cc3_pin_model_median_low_width_ticks"], 5969)

    def test_72bd_flag_boundary_is_distinct_from_c8_zero(self):
        image = G.read_bytes()
        self.assertEqual((image[0x72BD], image[0x721D]), (0x7C, 0x21))
        for raw, bit6, carry, second_reads in ((124, 0, "1", 0),
                                                (125, 1, "0", 153)):
            with self.subTest(raw=raw):
                self.assertEqual(original_716c_output(raw)[2], 0)
                report, log = trace(raw, matrix_gate=True)
                reads = [r for r in report["movc_observation"]["reads"]
                         if r["pc"] == "3D01" and r["mapped"] == "721D"]
                self.assertEqual(sum(r["count"] for r in reads), second_reads)
                selector = samples(log, "[MATRIX-SELECTOR]", "3D0C")
                self.assertGreater(len(selector), 100)
                self.assertEqual({((int(r["RAM22"], 16) >> 6) & 1,
                                   r["C"]) for r in selector}, {(bit6, carry)})
                at_39b2 = samples(log, "[UPPER-CA-CONSUMER]", "39B2")
                self.assertGreater(len(at_39b2), 50)
                self.assertEqual({r["UC8"] for r in at_39b2}, {"00"})


if __name__ == "__main__":
    unittest.main()
