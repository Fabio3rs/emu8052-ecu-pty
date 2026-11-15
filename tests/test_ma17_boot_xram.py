"""Trace the original ROM tail bytes copied to XRAM during Fiat boot."""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "FiatTipo_MA17_dump_27c256.bin"
S88 = ROOT / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 8817.bin"
DESTINATIONS = ("F80F", "F81E", "F849", "F84A", "F863",
                "F864", "F83F", "F84D", "F88F", "F8DE")


class BootXramTraceTests(unittest.TestCase):
    def run_trace(self, firmware, output, trace, adc0=40, adc3=80,
                  adc6=95, rpm=1000):
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("MA17_")}
        environment.update({
            "MA17_ADC_CH0": str(adc0), "MA17_ADC_CH6": str(adc6),
            "MA17_ADC_CH2": "220", "MA17_ADC_CH3": str(adc3),
            "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63"})
        if trace:
            environment["MA17_TRACE_BOOT_XRAM_FIELDS"] = "1"
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
             "--firmware", str(firmware), "--no-kline-inject",
             "--crank-immediate", "--rpm", str(rpm),
             "--stop-ticks", "2400000", "--seconds", "30",
             "--output-dir", str(output)],
            capture_output=True, text=True, env=environment,
            timeout=40, check=False)
        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
        report = json.loads((output / "execution.json").read_text())
        self.assertEqual(report["firmware_sha256"],
                         hashlib.sha256(firmware.read_bytes()).hexdigest())
        events = []
        for line in (output / "emulator-trace.log").read_text().splitlines():
            if line.startswith("[BOOT-XRAM-"):
                kind = line.split("]", 1)[0][1:]
                fields = dict(re.findall(r"(\w+)=(\w+)", line))
                events.append((kind, fields))
        return report, events

    def test_boot_copies_and_later_guard_reads_original_bytes(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            cases = ((G, 40, 80, 95, 1000),
                     (S88, 40, 80, 95, 1000),
                     (G, 180, 232, 247, 4000))
            for firmware, adc0, adc3, adc6, rpm in cases:
                with self.subTest(firmware=firmware.name, rpm=rpm):
                    output = Path(directory) / firmware.stem / str(rpm) / "trace"
                    report, events = self.run_trace(
                        firmware, output, True, adc0, adc3, adc6, rpm)
                    self.assertEqual(report["emulator_exit"], 0)
                    self.assertTrue(report["boot_xram_fields_trace_enabled"])
                    keys = [(kind, row["PC"], row["addr"])
                            for kind, row in events]
                    self.assertEqual(len(keys), len(set(keys)))
                    self.assertTrue(all(row["addr"] in DESTINATIONS
                                        for _, row in events))
                    rom_tail = firmware.read_bytes()[0x7FF6:0x8000]
                    for address, original in zip(DESTINATIONS, rom_tail):
                        writes = [row for kind, row in events
                                  if kind == "BOOT-XRAM-WRITE" and
                                  row["PC"] == "0AAB" and row["addr"] == address]
                        self.assertEqual(len(writes), 1)
                        self.assertEqual(int(writes[0]["value"], 16), original)
                    guard = {row["addr"]: row["stored"] for kind, row in events
                             if kind == "BOOT-XRAM-READ" and row["PC"] == "5896"}
                    self.assertEqual(guard, {
                        address: f"{original:02X}" for address, original in
                        zip(DESTINATIONS[1:], rom_tail[1:])})
                    changed = {"F80F", "F81E", "F83F", "F84D", "F88F", "F8DE"}
                    self.assertEqual({row["addr"] for kind, row in events
                                      if kind == "BOOT-XRAM-READ" and
                                      row["addr"] in changed and
                                      row["PC"] not in ("55A2", "5896", "092E")}, set())
                    if firmware == G and rpm == 1000:
                        control, no_events = self.run_trace(
                            firmware, Path(directory) / firmware.stem / "control", False)
                        self.assertFalse(no_events)
                        self.assertFalse(control["boot_xram_fields_trace_enabled"])
                        for key in ("output_latches", "cc3_observation",
                                    "engine_ram_observation", "pc_coverage"):
                            self.assertEqual(report[key], control[key])


if __name__ == "__main__":
    unittest.main()
