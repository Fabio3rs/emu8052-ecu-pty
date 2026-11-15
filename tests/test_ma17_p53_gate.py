"""Exercise original Fiat P4.7/P5.3 instructions without assigning ECU pins."""

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
ROM = ROOT / "FiatTipo_MA17_dump_27c256.bin"
EMULATOR = ROOT / "build/emu8051-tty"


def gate_rows(force_low, adc0=None, adc6=None):
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("MA17_",))}
    environment.update(MA17_CRANK_IMMEDIATE="1", MA17_CRANK_RPM="1000",
                       MA17_STOP_TICKS="2400000", MA17_ADC_CH7="63",
                       MA17_TRACE_PC="1", MA17_TRACE_P53_GATE="1")
    if force_low:
        environment["MA17_P4_7_FORCE_LOW"] = "1"
    if adc0 is not None:
        environment["MA17_ADC_CH0"] = str(adc0)
    if adc6 is not None:
        environment["MA17_ADC_CH6"] = str(adc6)
    result = subprocess.run([str(EMULATOR), str(ROM), "--8052"], cwd=ROOT,
                            env=environment, text=True, capture_output=True,
                            timeout=30, check=False)
    if result.returncode:
        raise AssertionError(result.stderr[-1500:])
    rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([0-9A-F]+)", line))
            for line in result.stderr.splitlines()
            if line.startswith("[P53-GATE]")]
    return rows, result.stderr


class P53GateTests(unittest.TestCase):
    def test_p46_and_adc2_open_late_26d8_branch(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        self.assertEqual(ROM.read_bytes()[0x733B], 0x28)
        observations = {}
        with tempfile.TemporaryDirectory() as directory:
            for adc2 in (160, 20):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment.update(
                    MA17_ADC_CH0="100", MA17_ADC_CH6="155",
                    MA17_ADC_CH2=str(adc2), MA17_ADC_CH3="80",
                    MA17_ADC_CH5="40", MA17_ADC_CH7="63",
                    MA17_P4_6_LOW_FROM_TICK="10600000",
                    MA17_TRACE_RAM4D_BRANCH="1")
                output = Path(directory) / str(adc2)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "3000", "--stop-ticks", "15000000",
                     "--seconds", "90", "--output-dir", str(output)],
                    cwd=ROOT, env=environment, text=True,
                    capture_output=True, timeout=100, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(ROM.read_bytes()).hexdigest())
                rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([0-9A-F]+)", line))
                        for line in (output / "emulator-trace.log").read_text().splitlines()
                        if line.startswith("[RAM4D-BRANCH]")]
                observations[adc2] = (report, rows)
        for adc2, expected_62h in ((160, "A0"), (20, "14")):
            report, rows = observations[adc2]
            opened = [row for row in rows if row["PC"] == "2653"
                      and int(row["tick"]) >= 10600000
                      and int(row["F2F"], 16) & 0x11 == 0x11]
            self.assertGreater(len(opened), 400)
            self.assertEqual({row["RAM62"] for row in opened}, {expected_62h})
            self.assertEqual({row["UA8"] for row in opened}, {"50"})
            reads = [row for row in report["movc_observation"]["reads"]
                     if row["dptr"] == "746C"]
            self.assertEqual({row["address"] for row in reads}, {"746F"})
        high = observations[160][1]
        low = observations[20][1]
        self.assertFalse(any(row["PC"] == "26D8" for row in high))
        self.assertGreater(sum(row["PC"] == "26D8" for row in low), 90)

    def test_746c_downstream_division_is_reached_without_output_change(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        donor_rom = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin"
        traces = []
        with tempfile.TemporaryDirectory() as directory:
            for donor in (False, True):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment.update(MA17_ADC_CH0="100", MA17_ADC_CH6="155",
                                   MA17_ADC_CH3="20", MA17_ADC_CH5="40",
                                   MA17_ADC_CH7="63",
                                   MA17_TRACE_RAM4D_DOWNSTREAM="1")
                if donor:
                    environment.update(
                        MA17_OVERRIDE_MOVC_MATRIX_BASE="746C",
                        MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor_rom))
                output = Path(directory) / str(donor)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "3000", "--stop-ticks", "15000000",
                     "--seconds", "90", "--output-dir", str(output)],
                    cwd=ROOT, env=environment, text=True,
                    capture_output=True, timeout=100, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(ROM.read_bytes()).hexdigest())
                self.assertEqual(sum(row["count"] for row in
                                     report["movc_observation"]["reads"]
                                     if row["address"] == "746C"), 820)
                pc_hits = set((output / "pc-hits.txt").read_text().splitlines())
                self.assertIn("25ED", pc_hits)
                self.assertIn("26C5", pc_hits)
                self.assertNotIn("26D8", pc_hits)
                rows = [dict(re.findall(r"([A-Za-z0-9_]+)=([0-9A-F]+)", line))
                        for line in (output / "emulator-trace.log").read_text().splitlines()
                        if line.startswith("[RAM4D-DOWNSTREAM]")]
                traces.append((report, rows))
        for pc in ("25ED", "2606"):
            control = [row for row in traces[0][1] if row["PC"] == pc]
            donated = [row for row in traces[1][1] if row["PC"] == pc]
            self.assertEqual([row["tick"] for row in control],
                             [row["tick"] for row in donated])
            self.assertGreater(sum(a["R3"] != b["R3"]
                                   for a, b in zip(control, donated)), 400)
            self.assertEqual([row["A"] for row in control],
                             [row["A"] for row in donated])
        for field in ("cc3_observation", "output_latches"):
            self.assertEqual(traces[0][0][field], traces[1][0][field])

    def test_delayed_746c_first_cell_donor_reaches_iram4d(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        donor_rom = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin"
        self.assertEqual(ROM.read_bytes()[0x746C:0x7476], bytes([0x0F]) * 10)
        self.assertEqual(donor_rom.read_bytes()[0x746C:0x7476],
                         bytes([0x29]) + bytes([0x0F]) * 9)
        samples = []
        first_downstream = []
        late_cc3_widths = []
        with tempfile.TemporaryDirectory() as directory:
            for donor in (False, True):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment.update(MA17_ADC_CH0="100", MA17_ADC_CH6="155",
                                   MA17_ADC_CH3="20", MA17_ADC_CH5="40",
                                   MA17_ADC_CH7="63",
                                   MA17_TRACE_IDLE_FAULT="1",
                                   MA17_TRACE_P53_GATE="1",
                                   MA17_TRACE_RAM4D_PATH="1")
                if donor:
                    environment.update(
                        MA17_OVERRIDE_MOVC_MATRIX_BASE="746C",
                        MA17_OVERRIDE_MOVC_MATRIX_ROM=str(donor_rom))
                output = Path(directory) / str(donor)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                     "--trace-movc", "--no-kline-inject", "--crank-immediate",
                     "--rpm", "1000", "--stop-ticks", "15000000",
                     "--seconds", "90", "--output-dir", str(output)],
                    cwd=ROOT, env=environment, text=True,
                    capture_output=True, timeout=100, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(ROM.read_bytes()).hexdigest())
                self.assertEqual(report["movc_matrix_base_hex"],
                                 "746C" if donor else None)
                self.assertEqual(sum(row["count"] for row in
                                     report["movc_observation"]["reads"]
                                     if row["address"] == "746C"), 922)
                log = (output / "emulator-trace.log").read_text()
                self.assertNotIn("[IDLE-FAULT-READ-OVERRIDE]", log)
                self.assertFalse(any(line.startswith("[IDLE-FAULT-GATE]")
                                     and "PC=2B38" in line
                                     for line in log.splitlines()))
                self.assertEqual(sum(line.startswith("[P53-GATE]") and
                                     "PC=21CA" in line for line in log.splitlines()),
                                 440)
                samples.append([
                    (int(match.group(1)), match.group(2))
                    for line in log.splitlines()
                    if line.startswith("[RAM4D-PATH]") and "PC=233B" in line
                    for match in [re.search(
                        r"tick=(\d+).*RAM4D=([0-9A-F]{2})", line)]
                    if match])
                first_downstream.append(next(
                    re.search(r"\bA=([0-9A-F]{2})", line).group(1)
                    for line in log.splitlines()
                    if line.startswith("[RAM4D-PATH]") and "PC=2593" in line
                    and int(re.search(r"tick=(\d+)", line).group(1)) >= 10515000))
                edges = [(int(match.group(1)), int(match.group(2)))
                         for line in log.splitlines()
                         if line.startswith("[CC3-PIN]")
                         for match in [re.search(
                             r"tick=(\d+).*value=(\d)", line)] if match]
                late_cc3_widths.append([
                    next_tick - tick for (tick, value), (next_tick, next_value)
                    in zip(edges, edges[1:])
                    if tick >= 10500000 and value == 0 and next_value == 1])
        self.assertEqual([tick for tick, _ in samples[0]],
                         [tick for tick, _ in samples[1]])
        changed = [(before, after) for (_, before), (_, after)
                   in zip(*samples) if before != after]
        self.assertGreater(len(changed), 100)
        self.assertEqual(set(changed), {("28", "42")})
        self.assertEqual(first_downstream, ["2C", "49"])
        self.assertEqual(len(late_cc3_widths[0]), 152)
        self.assertEqual(late_cc3_widths[0], late_cc3_widths[1])

    def test_coherent_tps_uses_alternate_bit225_blocking_path(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        rows, stderr = gate_rows(False, adc0=40, adc6=95)
        self.assertIn("[TRACE-STOP] ticks=2400000", stderr)
        stage = lambda pc: [row for row in rows if row["PC"] == pc]
        self.assertEqual(len(stage("21C6")), 230)
        self.assertEqual(len(stage("21CA")), 0)
        self.assertEqual(len(stage("21C2")), 209)
        self.assertEqual(sum(int(row["F2E"], 16) & 1 != 0
                             for row in stage("216A")), 21)
        self.assertTrue(all(row["F28"] == "00" for row in stage("21C6")))
        # SAB80C517 upper IRAM @A6h is a counter here, not SFR A6h.
        # After startup, upper @9Eh.6 and nonzero @A6h bypass 2174h.
        self.assertTrue(all(int(row["U9E"], 16) & 0x40
                            and int(row["UA6"], 16) > 0
                            for row in stage("21C2")))
        self.assertEqual(min(int(row["UA6"], 16)
                             for row in stage("21C2")), 0x50)
        self.assertEqual(sum(bool(int(row["F2D"], 16) & 0x20)
                             for row in stage("21C2")), 20)
        self.assertTrue(all(int(row["F22"], 16) & 0x20
                            for row in stage("220F")))

    def test_p47_input_changes_gate_state_but_bit225_blocks_p53(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        original_hash = hashlib.sha256(ROM.read_bytes()).hexdigest()
        for force_low in (False, True):
            with self.subTest(p4_7_force_low=force_low):
                rows, stderr = gate_rows(force_low)
                self.assertIn("[TRACE-STOP] ticks=2400000", stderr)
                stages = {pc: [row for row in rows if row["PC"] == pc]
                          for pc in ("2202", "2206", "220C", "220F", "2211")}
                self.assertGreater(len(stages["220F"]), 200)
                self.assertTrue(all(len(stage) == len(stages["220F"])
                                    for stage in stages.values()))
                self.assertTrue(all(row["DPTR"] == "7200" and
                                    row["A"] == "0E" for row in stages["2206"]))
                self.assertTrue(all(bool(int(row["PSW"], 16) & 0x20) != force_low
                                    for row in stages["2202"]))
                self.assertTrue(all(int(row["F22"], 16) & 0x20
                                    for row in stages["220C"]))
                self.assertTrue(all(not (int(row["PSW"], 16) & 0x80)
                                    for row in stages["220C"]))
                self.assertTrue(all(int(row["P5_latch"], 16) & 0x08
                                    for row in stages["2211"]))
        self.assertEqual(hashlib.sha256(ROM.read_bytes()).hexdigest(),
                         original_hash)


if __name__ == "__main__":
    unittest.main()
