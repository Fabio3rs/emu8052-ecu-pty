"""Regression checks for the paired PTY trace summarizer."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from probe_ma17_serial38 import summarize, validate  # noqa: E402


class Serial38ProbeTests(unittest.TestCase):
    def test_three_arm_validation_detects_lost_ram69_mediation(self):
        def arm(periods, reload_pairs, serial=(), changes=()):
            return {"serial38_events": list(serial), "ram69_changes": list(changes),
                    "window": {"p5_latch_events": 4, "timer1_path_events": 4,
                               "timer_reload_pairs": reload_pairs,
                               "p5_0_low_edge_periods": periods,
                               "p5_1_low_edge_periods": periods}}

        branch = ["[SERIAL38-PATH] PC=5091 R2=38 RAM2B=30"]
        producer = ["[ENGINE-RAM] value=9A->80 source_PC=3B06"]
        report = {
            "control": arm([59400], ["12FE/8BFF"]),
            "frame38": arm([57915, 59400, 60885],
                           ["12FE/8BFF", "2FFE/A8FF"], branch, producer),
            "frame38_ram69_read_9a": arm(
                [59399, 59401], ["12FE/8BFF"], branch,
                producer + ["[ENGINE-RAM] value=80->9A source_PC=043B"])}
        self.assertEqual(validate(report), [])
        report["frame38_ram69_read_9a"]["window"]["timer_reload_pairs"].append(
            "2FFE/A8FF")
        self.assertIn("restored: Timer1/P5 reload pairs differ from control",
                      validate(report))

    def test_p5_width_and_period_keep_ram69_and_reload_context(self):
        def edge(tick, value, ram69, pair):
            first, second = pair.split("/")
            return (f"[P5-LATCH] instr={tick} PC=0273 value={value} "
                    f"RAM47=28 source_PC=0271 RAM69={ram69} "
                    f"RAM36_37=011D RAM32_33={first} RAM34_35={second}")

        lines = [edge(90, "03", "9A", "12FE/8BFF"),
                 edge(100, "02", "9A", "12FE/8BFF"),
                 edge(110, "03", "9A", "12FE/8BFF"),
                 edge(160, "02", "80", "2FFE/A8FF"),
                 edge(171, "03", "80", "2FFE/A8FF"),
                 edge(190, "01", "80", "2FFE/A8FF"),
                 edge(203, "03", "80", "2FFE/A8FF"),
                 "[TIMER1-PATH] tick=195 PC=0298 TCON=15 TMOD=11 "
                 "TL1=FF TH1=2F P5=01 F2A=00 RAM30=00 "
                 "R32_33=2FFE R34_35=A8FF"]
        result = summarize(lines, (90, 220))
        self.assertEqual(result["p5_0_low_edge_periods"], [60])
        self.assertEqual(result["p5_0_low_widths_by_ram69"],
                         {"80": [11], "9A": [10]})
        self.assertEqual(result["p5_1_low_widths_by_ram69"], {"80": [13]})
        self.assertEqual(result["timer_reload_pairs"],
                         ["12FE/8BFF", "2FFE/A8FF"])
        self.assertEqual(result["timer1_path_events"], 1)
        self.assertEqual(result["timer1_pcs"], ["0298"])
        self.assertEqual(result["timer1_ram_pairs"], ["2FFE/A8FF"])


if __name__ == "__main__":
    unittest.main()
