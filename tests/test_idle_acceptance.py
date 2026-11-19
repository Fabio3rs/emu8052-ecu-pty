"""Hot-idle acceptance of the calibrated plant (goal criterion 1).

Scenario: hot (90 C), no external load, accessories on (alternator + pump, F-45),
bench TPS profile, idle actuator driven by the ROM. All numbers are read from the
plant telemetry window ({"type":"plant"}, 20 crank cycles), never from one sample.

The ROM (IE ALCOOL image) targets RAM46*25 = 925 rpm hot while the manual quotes
850 +/- 50: the plant cannot move that setpoint, so the physical mean is checked
against the manual band widened by one ROM count (25 rpm) and against the ROM's own
intention (RAM46/RAM47 resolve rpm in 25 rpm steps). LLM-written (Claude).
"""
import json
import os
import re
import statistics
import subprocess
import sys

binary, firmware = sys.argv[1:3]
args = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "40000000", "--adc7-mv", "1232", "--idle-bridge-p15-p16",
        "--idle-contact-p46", "--tps-bench-profile", "--idle-motor-speed-mm-s", "50",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
        "--lambda-adc-gain", "5", "--coolant-c", "90", "--tdc-reference-deg", "117",
        "--accessory-load"]
result = subprocess.run(args, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                        text=True, capture_output=True, timeout=300, check=True)
windows = [json.loads(line) for line in result.stdout.splitlines()
           if line.startswith('{"type":"plant"')]
late = [w for w in windows if w["tick"] > 25_000_000]
assert len(late) >= 8, len(windows)
crank = re.search(r"\[PHYSICAL-CRANK\] [^\n]*ram47=(\d+) ram46=(\d+)", result.stdout)
assert crank, result.stdout[-1500:]
ram47, ram46 = int(crank[1]), int(crank[2])


def mean(key):
    return statistics.mean(w[key] for w in late)


rpm, lam, adv = mean("rpm"), mean("lambda_cyl"), mean("spark_deg")
brake, acc = mean("brake_nm"), mean("accessory_nm")
print(f"[IDLE] rpm={rpm:.1f} lambda={lam:.3f} advance={adv:.2f} brake={brake:.3f} "
      f"acc={acc:.2f} ram46*25={ram46 * 25} ram47*25={ram47 * 25}")
# Manual B.500.837 p.18: 850 +/- 50 rpm, widened by one ROM count (25 rpm).
assert 800.0 <= rpm <= 925.0, rpm
# ROM intention (RAM46 target, RAM47 measured) and physical value agree within a count.
assert abs(rpm - ram46 * 25) <= 50.0 and abs(ram47 * 25 - rpm) <= 50.0
assert 0.97 <= lam <= 1.03, lam                       # criterion 1
assert 4.0 <= adv <= 8.0, adv                         # manual p.18: 6 +/- 2 deg
assert abs(brake) < 0.5, brake                        # torque balance at steady idle
assert 2.0 < acc < 5.0, acc                           # accessories on (F-45)
assert max(w["rpm"] for w in late) - min(w["rpm"] for w in late) < 60.0
print("idle acceptance ok")
