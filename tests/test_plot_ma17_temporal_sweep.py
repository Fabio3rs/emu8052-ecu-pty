"""Synthetic rendering regression for the Fiat temporal sweep plot."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PYTHON = Path("/usr/bin/python3")


class TemporalSweepPlotTests(unittest.TestCase):
    def test_two_matched_runs_render_png_and_svg(self):
        if not SYSTEM_PYTHON.exists():
            self.skipTest("system Python is unavailable")
        dependency = subprocess.run(
            [str(SYSTEM_PYTHON), "-c", "import matplotlib"],
            capture_output=True, text=True, check=False)
        if dependency.returncode:
            self.skipTest("system matplotlib is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for name, steps, width in (("sweep", [{"tick": 1000, "value": 180}], 450),
                                       ("control", [], 400)):
                run = base / name
                run.mkdir()
                report = {"firmware_sha256": "synthetic-matched-rom",
                          "stop_ticks_observed": 2000, "crank_target_rpm": 1000,
                          "oscillator_hz": 11880000,
                          "machine_cycles_per_second": 990000,
                          "adc_10bit_input_values": [160] * 8,
                          "adc_10bit_step_sequences": [[] for _ in range(8)]}
                report["adc_10bit_step_sequences"][3] = steps
                (run / "execution.json").write_text(json.dumps(report))
                (run / "emulator-trace.log").write_text(
                    f"[CC3-PIN] tick=1200 PC=05D5 value=0 shadow=0\n"
                    f"[CC3-PIN] tick={1200 + width} PC=1708 value=1 shadow=1\n")
            environment = os.environ.copy()
            environment["MPLCONFIGDIR"] = str(base / "mpl")
            prefix = base / "figure"
            result = subprocess.run(
                [str(SYSTEM_PYTHON),
                 str(ROOT / "tools" / "plot_ma17_temporal_sweep.py"),
                 str(base / "sweep"), str(base / "control"),
                 "--output-prefix", str(prefix)],
                capture_output=True, text=True, env=environment,
                timeout=20, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertGreater(prefix.with_suffix(".png").stat().st_size, 1000)
            self.assertGreater(prefix.with_suffix(".svg").stat().st_size, 1000)

            control_path = base / "control" / "execution.json"
            control = json.loads(control_path.read_text())
            control["machine_cycles_per_second"] = 1980000
            control_path.write_text(json.dumps(control))
            mismatch = subprocess.run(
                [str(SYSTEM_PYTHON),
                 str(ROOT / "tools" / "plot_ma17_temporal_sweep.py"),
                 str(base / "sweep"), str(base / "control"),
                 "--output-prefix", str(prefix)],
                capture_output=True, text=True, env=environment,
                timeout=20, check=False)
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertIn("same positive machine-cycle clock rate", mismatch.stderr)

    def test_phase_factorial_renders_matched_event_deltas(self):
        if not SYSTEM_PYTHON.exists():
            self.skipTest("system Python is unavailable")
        dependency = subprocess.run(
            [str(SYSTEM_PYTHON), "-c", "import matplotlib"],
            capture_output=True, text=True, check=False)
        if dependency.returncode:
            self.skipTest("system matplotlib is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for name, delay in (("reference", 0), ("donor", 5)):
                run = base / name
                run.mkdir()
                (run / "execution.json").write_text(json.dumps({
                    "stop_ticks_observed": 2000, "crank_target_rpm": 1000,
                    "machine_cycles_per_second": 990000}))
                (run / "emulator-trace.log").write_text(
                    f"[CC3-PIN] tick={1200 + delay} PC=05D5 value=0 shadow=0\n"
                    f"[CC3-PIN] tick={1600 + delay} PC=1708 value=1 shadow=1\n")
            environment = os.environ.copy()
            environment["MPLCONFIGDIR"] = str(base / "mpl")
            prefix = base / "phase"
            result = subprocess.run(
                [str(SYSTEM_PYTHON),
                 str(ROOT / "tools" / "plot_ma17_phase_factorial.py"),
                 str(base / "reference"),
                 "--arm", f"donor={base / 'donor'}",
                 "--output-prefix", str(prefix)],
                capture_output=True, text=True, env=environment,
                timeout=20, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertGreater(prefix.with_suffix(".png").stat().st_size, 1000)
            self.assertGreater(prefix.with_suffix(".svg").stat().st_size, 1000)

            donor_path = base / "donor" / "execution.json"
            donor = json.loads(donor_path.read_text())
            donor["machine_cycles_per_second"] = 1980000
            donor_path.write_text(json.dumps(donor))
            mismatch = subprocess.run(
                [str(SYSTEM_PYTHON),
                 str(ROOT / "tools" / "plot_ma17_phase_factorial.py"),
                 str(base / "reference"),
                 "--arm", f"donor={base / 'donor'}",
                 "--output-prefix", str(prefix)],
                capture_output=True, text=True, env=environment,
                timeout=20, check=False)
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertIn("unmatched machine-cycle clock rate", mismatch.stderr)


if __name__ == "__main__":
    unittest.main()
