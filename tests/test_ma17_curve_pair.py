"""Digital interaction of Fiat 7520h/752Ah curves at modeled CC3/P1.3."""

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
G = ROOT / "FiatTipo_MA17_dump_27c256.bin"
A = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin"
TRACE = ROOT / "tools/trace_ma17.py"
EMULATOR = ROOT / "build/emu8051-tty"


class CurvePairTests(unittest.TestCase):
    def test_two_tps_steps_make_both_multiply_factors_nonzero(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        expected = {
            "control": ("5C", "73", 2, 127, 1278, "B4", "24"),
            "7520": ("7E", "73", 2, 127, 1342, "FC", "27"),
            "752a": ("5C", "95", 12, 117, 1326, "B4", "C8"),
            "both": ("7E", "95", 10, 119, 1367, "FC", "CA"),
        }
        donor_bytes = A.read_bytes()
        self.assertEqual(donor_bytes[0x7521:0x7523], bytes.fromhex("7C 95"))
        self.assertEqual(int.from_bytes(donor_bytes[0x707C:0x707E], "big"),
                         0x752A)
        with tempfile.TemporaryDirectory() as directory:
            for arm, (ram79, ram7b, zeros, pulses, median,
                      math_a, candidate) in expected.items():
                with self.subTest(arm=arm):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH1="130",
                        MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                        MA17_ADC_CH4="90", MA17_ADC_CH5="110",
                        MA17_ADC_CH6="95", MA17_ADC_CH7="63",
                        MA17_ADC10_STEP_CH0="800000:720,3274600:160",
                        MA17_ADC10_STEP_CH6="800000:988,3274600:380",
                        MA17_TRACE_78XX_PATH="1", MA17_TRACE_RAM78_GATE="1")
                    if arm in ("7520", "both"):
                        environment["MA17_OVERRIDE_MOVC_AT"] = (
                            "532F:7521:7C,5333:7522:95")
                    if arm in ("752a", "both"):
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="752A",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(A))
                    output = Path(directory) / arm
                    run = subprocess.run(
                        [sys.executable, str(TRACE), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate",
                         "--rpm", "1000", "--stop-ticks", "4000000",
                         "--seconds", "30", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        cwd=ROOT, timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(G.read_bytes()).hexdigest())
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["dptr"] in ("7520", "752A")]
                    self.assertEqual({(row["address"], row["count"])
                                      for row in reads},
                                     {(address, 795) for address in
                                      ("7521", "7522", "752B", "752C")})
                    changes = report["engine_ram_observation"]
                    self.assertEqual(changes["79"][-1]["after"], ram79)
                    self.assertEqual(changes["7B"][-1]["after"], ram7b)
                    first_7a_tick = changes["7A"][0]["tick"]
                    ram78 = "00"
                    for change in changes["78"]:
                        if change["tick"] > first_7a_tick:
                            break
                        ram78 = change["after"]
                    self.assertEqual(ram78, "0C")
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    math = next(line for line in lines
                                if line.startswith("[78XX-MATH]")
                                and "PC=1D57" in line
                                and int(re.search(r"tick=(\d+)", line)[1])
                                > first_7a_tick)
                    self.assertIn(f"A={math_a}", math)
                    gate = next(line for line in lines
                                if line.startswith("[78XX-MATH]")
                                and "PC=1EA9" in line
                                and 3590000 < int(re.search(r"tick=(\d+)", line)[1])
                                < 3600000)
                    self.assertIn(f"R2={candidate} R3=00", gate)
                    entries = [line for line in lines
                               if line.startswith("[CC3-ENTRY]")]
                    self.assertEqual(len(entries), 131)
                    self.assertEqual(sum("IRAM14_15=0000" in line
                                         for line in entries), zeros)
                    if arm in ("752a", "both"):
                        restored = "0000" if arm == "752a" else "00CA"
                        self.assertTrue(all(f"IRAM14_15={restored}" in
                                            entries[index] for index in (117, 118)))
                    cc3 = report["cc3_observation"]
                    self.assertEqual(cc3["cc3_pin_model_low_starts"], pulses)
                    self.assertEqual(cc3["iram14_15_median"], median)

    def test_s88_pair_stays_below_original_cc3_bound(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        s88 = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin"
        self.assertEqual(G.read_bytes()[0x7218:0x721A], bytes.fromhex("00 C8"))
        self.assertEqual(s88.read_bytes()[0x7218:0x721A],
                         bytes.fromhex("00 C8"))
        expected = {
            "control": (1566, 2, 127, "18"),
            "7520": (1642, 2, 127, "1B"),
            "752a": (1606, 12, 117, "C1"),
            "both": (1698, 12, 117, "C3"),
        }
        with tempfile.TemporaryDirectory() as directory:
            for arm, (median, zeros, pulses, candidate) in expected.items():
                with self.subTest(arm=arm):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH1="130",
                        MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                        MA17_ADC_CH4="90", MA17_ADC_CH5="110",
                        MA17_ADC_CH6="95", MA17_ADC_CH7="63",
                        MA17_ADC10_STEP_CH0="800000:720,3274600:160",
                        MA17_ADC10_STEP_CH6="800000:988,3274600:380",
                        MA17_TRACE_78XX_PATH="1", MA17_TRACE_RAM78_GATE="1")
                    if arm in ("7520", "both"):
                        environment["MA17_OVERRIDE_MOVC_AT"] = (
                            "532F:7521:7C,5333:7522:95")
                    if arm in ("752a", "both"):
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="752A",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(A))
                    output = Path(directory) / arm
                    run = subprocess.run(
                        [sys.executable, str(TRACE), "--firmware", str(s88),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "4000000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        cwd=ROOT, timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(s88.read_bytes()).hexdigest())
                    changes = report["engine_ram_observation"]
                    first_7a_tick = changes["7A"][0]["tick"]
                    previous_78 = [row["after"] for row in changes["78"]
                                   if row["tick"] < first_7a_tick]
                    self.assertEqual(previous_78[-1], "0C")
                    reads = [row for row in report["movc_observation"]["reads"]
                             if row["dptr"] in ("7520", "752A")]
                    count = 794 if arm == "752a" else 793
                    self.assertEqual({row["count"] for row in reads}, {count})
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    gate = next(line for line in lines
                                if line.startswith("[78XX-MATH]")
                                and "PC=1EA9" in line
                                and 3590000 < int(re.search(r"tick=(\d+)", line)[1])
                                < 3600000)
                    self.assertIn(f"R2={candidate} R3=00", gate)
                    entries = [line for line in lines
                               if line.startswith("[CC3-ENTRY]")]
                    self.assertEqual(len(entries), 131)
                    self.assertEqual(sum("IRAM14_15=0000" in line
                                         for line in entries), zeros)
                    cc3 = report["cc3_observation"]
                    self.assertEqual(cc3["cc3_pin_model_low_starts"], pulses)
                    self.assertEqual(cc3["iram14_15_median"], median)

    def test_s88_7580_byte_restores_late_cc3_intervals(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        s88 = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin"
        self.assertEqual(G.read_bytes()[0x7580], 0x10)
        self.assertEqual(s88.read_bytes()[0x7580], 0x25)
        self.assertEqual(G.read_bytes()[0x7B45], 0x05)
        self.assertEqual(s88.read_bytes()[0x7B45], 0x0D)
        expected = {
            "original": ("C3", 12, 117, "0000", 1698, "95"),
            "g7580": ("EA", 8, 121, "00EA", 1506, "A2"),
            "g7b45": ("C3", 12, 117, "0000", 1698, "95"),
            "g7581": ("A4", 16, 113, "0000", 1552, "95"),
            "g7580_g7581": ("CA", 10, 119, "00CA", 1367, "A2"),
            "g_fiat_both": ("CA", 10, 119, "00CA", 1367, "9A"),
        }
        schedules = {}
        with tempfile.TemporaryDirectory() as directory:
            for arm, (candidate, zeros, starts, interval,
                      median, ram69) in expected.items():
                with self.subTest(arm=arm):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH1="130",
                        MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                        MA17_ADC_CH4="90", MA17_ADC_CH5="110",
                        MA17_ADC_CH6="95", MA17_ADC_CH7="63",
                        MA17_ADC10_STEP_CH0="800000:720,3274600:160",
                        MA17_ADC10_STEP_CH6="800000:988,3274600:380",
                        MA17_TRACE_78XX_PATH="1",
                        MA17_OVERRIDE_MOVC_AT=(
                            "532F:7521:7C,5333:7522:95,"
                            "532F:752B:95,5333:752C:9C"))
                    if arm == "g7580":
                        environment["MA17_OVERRIDE_MOVC_7580"] = "10"
                    if arm == "g7b45":
                        environment["MA17_OVERRIDE_MOVC_7B45"] = "05"
                    if "g7581" in arm:
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="7581",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(G))
                    if arm == "g7580_g7581":
                        environment["MA17_OVERRIDE_MOVC_7580"] = "10"
                    if arm == "g_fiat_both":
                        environment.pop("MA17_OVERRIDE_MOVC_7580", None)
                    output = Path(directory) / arm
                    firmware = G if arm == "g_fiat_both" else s88
                    run = subprocess.run(
                        [sys.executable, str(TRACE), "--firmware", str(firmware),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "4000000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        cwd=ROOT, timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    gate = next(line for line in lines
                                if line.startswith("[78XX-MATH]")
                                and "PC=1EA9" in line
                                and 3590000 < int(re.search(r"tick=(\d+)", line)[1])
                                < 3600000)
                    self.assertIn(f"R2={candidate} R3=00", gate)
                    entries = [line for line in lines
                               if line.startswith("[CC3-ENTRY]")]
                    schedules[arm] = [re.search(r"IRAM14_15=([0-9A-F]{4})",
                                                line)[1] for line in entries]
                    self.assertEqual(len(entries), 131)
                    self.assertEqual(sum("IRAM14_15=0000" in line
                                         for line in entries), zeros)
                    self.assertTrue(all(f"IRAM14_15={interval}" in
                                        entries[index] for index in (117, 118)))
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_low_starts"], starts)
                    self.assertEqual(report["cc3_observation"]
                                     ["iram14_15_median"], median)
                    self.assertEqual(report["engine_ram_observation"]
                                     ["69"][-1]["after"], ram69)
        self.assertEqual(schedules["g7580_g7581"],
                         schedules["g_fiat_both"])

    def test_s88_7580_and_7581_match_g_cc3_entries_at_other_rpms(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        s88 = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin"
        expected = {
            1500: (196, 15, 179, 1311, 181),
            3000: (200, 0, 356, 1326, 197),
        }
        with tempfile.TemporaryDirectory() as directory:
            for rpm, (samples, zeros, starts, median,
                      native_differences) in expected.items():
                schedules = {}
                for arm, firmware in (("s88", s88), ("donor", s88),
                                      ("g", G)):
                    with self.subTest(rpm=rpm, arm=arm):
                        environment = {key: value for key, value in
                                       os.environ.items()
                                       if not key.startswith("MA17_")}
                        environment.update(
                            MA17_ADC_CH0="40", MA17_ADC_CH1="130",
                            MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                            MA17_ADC_CH4="90", MA17_ADC_CH5="110",
                            MA17_ADC_CH6="95", MA17_ADC_CH7="63",
                            MA17_ADC10_STEP_CH0="800000:720,3274600:160",
                            MA17_ADC10_STEP_CH6="800000:988,3274600:380",
                            MA17_OVERRIDE_MOVC_AT=(
                                "532F:7521:7C,5333:7522:95,"
                                "532F:752B:95,5333:752C:9C"))
                        if arm == "donor":
                            environment.update(
                                MA17_OVERRIDE_MOVC_7580="10",
                                MA17_OVERRIDE_MOVC_MATRIX_BASE="7581",
                                MA17_OVERRIDE_MOVC_MATRIX_ROM=str(G))
                        output = Path(directory) / f"{rpm}_{arm}"
                        run = subprocess.run(
                            [sys.executable, str(TRACE), "--firmware",
                             str(firmware), "--trace-movc", "--no-kline-inject",
                             "--crank-immediate", "--rpm", str(rpm),
                             "--stop-ticks", "4000000", "--seconds", "30",
                             "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            cwd=ROOT, timeout=35, check=False)
                        self.assertEqual(run.returncode, 0,
                                         run.stderr[-1500:])
                        report = json.loads((output / "execution.json")
                                            .read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(firmware.read_bytes())
                                         .hexdigest())
                        lines = (output / "emulator-trace.log")
                        schedules[arm] = [
                            re.search(r"IRAM14_15=([0-9A-F]{4})", line)[1]
                            for line in lines.read_text().splitlines()
                            if line.startswith("[CC3-ENTRY]")]
                        self.assertEqual(len(schedules[arm]), samples)
                        if arm != "s88":
                            cc3 = report["cc3_observation"]
                            self.assertEqual(schedules[arm].count("0000"),
                                             zeros)
                            self.assertEqual(cc3["cc3_pin_model_low_starts"],
                                             starts)
                            self.assertEqual(cc3["iram14_15_median"],
                                             median)
                self.assertEqual(schedules["donor"], schedules["g"])
                self.assertEqual(sum(a != b for a, b in
                                     zip(schedules["s88"], schedules["g"])),
                                 native_differences)


if __name__ == "__main__":
    unittest.main()
