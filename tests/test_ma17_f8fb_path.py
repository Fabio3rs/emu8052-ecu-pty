"""Original-ROM F8:FBh consumer during a modeled TPS release."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROMS = (
    ROOT / "FiatTipo_MA17_dump_27c256.bin",
    ROOT / "firmwares_modificados_ma17_tipo" /
    "tipo 1.6 alcool27c256 SUN 8817.bin",
)
MOVC_ZERO = ",".join(
    f"{pc}:{address}:00" for pc, address in (
        ("532F", "78E5"), ("532F", "78E9"), ("532F", "78F1"),
        ("5333", "78E6"), ("5333", "78EA"), ("5333", "78F2"),
        ("534B", "78E9"), ("534B", "78F5"),
        ("5350", "78EA"), ("5350", "78F6")))


class F8fbPathTests(unittest.TestCase):
    def test_f8fb_read_controls_nonzero_ram7a_multiply_result(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for rom in ROMS:
                observations = {}
                for arm in ("native", "read00", "movc00"):
                    with self.subTest(rom=rom.name, arm=arm):
                        environment = {
                            key: value for key, value in os.environ.items()
                            if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                   "MA17_TRACE_", "MA17_P4_"))
                        }
                        environment.update({
                            f"MA17_ADC_CH{channel}": str(value)
                            for channel, value in enumerate(
                                (180, 130, 140, 4, 90, 200, 247, 63))
                        })
                        environment.update(
                            MA17_ADC10_STEP_CH0="3274600:160",
                            MA17_ADC10_STEP_CH6="3274600:380",
                            MA17_TRACE_78XX_PATH="1")
                        if arm == "read00":
                            environment["MA17_OVERRIDE_XRAM_READ_AT"] = \
                                "1CC5:F8FB:00"
                        if arm == "movc00":
                            environment["MA17_OVERRIDE_MOVC_AT"] = MOVC_ZERO
                        output = Path(directory) / f"{rom.stem}-{arm}"
                        command = [sys.executable,
                                   str(ROOT / "tools" / "trace_ma17.py")]
                        if arm == "movc00":
                            command.append("--trace-movc")
                        result = subprocess.run(
                            command + ["--firmware", str(rom), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "1000",
                             "--stop-ticks", "4000000", "--seconds", "25",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0,
                                         result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(rom.read_bytes()).hexdigest())
                        trace = (output / "emulator-trace.log").read_text()
                        entries = [line for line in trace.splitlines()
                                   if line.startswith("[78XX-CONSUMER]")
                                   and "PC=1CB7" in line]
                        exits = [line for line in trace.splitlines()
                                 if line.startswith("[78XX-CONSUMER]")
                                 and "PC=1CDF" in line
                                 and "RAM7A=00" not in line]
                        self.assertEqual(len(entries), 386)
                        self.assertEqual(len(exits), 69)
                        values = [int(re.search(r" B=([0-9A-F]{2})", line)
                                      .group(1), 16) for line in exits]
                        if arm != "native":
                            self.assertEqual(set(values), {0})
                        if arm == "read00":
                            self.assertIn("[XRAM-READ-OVERRIDE] PC=1CC5 "
                                          "addr=F8FB stored=FF supplied=00", trace)
                        elif arm == "movc00":
                            self.assertIn("[MOVC-OVERRIDE] PC=532F "
                                          "mapped=78F1 original=FF supplied=00",
                                          trace)
                            self.assertIn("XFB=00 RAM7A=8C", entries[-1])
                        else:
                            self.assertEqual((min(values), max(values)),
                                             (0x0C, 0x16))
                        cc3_entry = next(
                            line for line in trace.splitlines()
                            if line.startswith("[CC3-ENTRY]")
                            and int(re.search(r"instr=(\d+)", line)
                                    .group(1)) >= 3300000)
                        raw_interval = int(re.search(
                            r"IRAM14_15=([0-9A-F]{4})", cc3_entry)
                            .group(1), 16)
                        edges = [line for line in trace.splitlines()
                                 if line.startswith("[CC3-PIN]")
                                 and 3315000 <= int(re.search(
                                     r"tick=(\d+)", line).group(1)) < 3320000]
                        self.assertEqual(len(edges), 2)
                        self.assertIn("value=0", edges[0])
                        self.assertIn("value=1", edges[1])
                        width = (int(re.search(r"tick=(\d+)", edges[1]).group(1))
                                 - int(re.search(r"tick=(\d+)", edges[0]).group(1)))
                        observations[arm] = (report, raw_interval, width)
                expected = (0x00E2, 0x0265) if rom == ROMS[0] else \
                    (0x00DA, 0x0248)
                self.assertEqual((observations["native"][1],
                                  observations["read00"][1]), expected)
                self.assertEqual(observations["movc00"][1:],
                                 observations["read00"][1:])
                self.assertGreater(observations["read00"][2]
                                   - observations["native"][2], 1000)
                self.assertEqual({row[0]["cc3_observation"]
                                  ["cc3_pin_model_low_starts"]
                                  for row in observations.values()}, {129})


if __name__ == "__main__":
    unittest.main()
