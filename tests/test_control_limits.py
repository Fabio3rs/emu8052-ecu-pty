"""One source of control limits (GOAL_DYNO_ROM 4): full-open pedal -> 90 deg, 300 N.m reaches the
plant, and --load-nm never touches leak or accessories. LLM-written (Claude)."""
import json
import math
import os
import re
import subprocess
import sys

binary, rom = sys.argv[1:3]
env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
base = [binary, rom, "--physical-crank", "--starter-ticks", "495000", "--stop-ticks", "3000000",
        "--adc7-mv", "1232", "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "14", "--lambda-adc-gain", "5"]


def run(extra, expect_rc=0):
    r = subprocess.run(base + extra, env=env, text=True, capture_output=True, timeout=120)
    assert r.returncode == expect_rc, (extra, r.returncode, r.stderr[-300:])
    return r.stdout


# CLI path: full-open pedal reaches 90 degrees
out = run(["--pedal-step-tick", "1000000", "--pedal-full-open", "--pedal-rise-ticks", "200000"])
ev = [json.loads(l) for l in out.splitlines() if l.startswith('{"type":"pedal"')]
assert ev and abs(ev[-1]["angle_rad"] - math.pi / 2) < 1e-5, ev
assert abs(ev[-1]["pull_m"] - (0.001 + 0.025 * math.pi / 2)) < 1e-6
# beyond the travel is rejected, fractional mm accepted
run(["--pedal-step-tick", "1000000", "--pedal-mm", "40.5"], expect_rc=2)
run(["--pedal-step-tick", "1000000", "--pedal-mm", "40.2"])
# 300 N.m is accepted by the CLI and reaches the plant (stall under 300 N.m)
out = run(["--load-step-tick", "1000000", "--load-nm", "300"])
loads = [json.loads(l) for l in out.splitlines() if l.startswith('{"type":"load_step"')]
assert loads and loads[-1]["torque_nm"] == 300.0, loads
run(["--load-step-tick", "1000000", "--load-nm", "401"], expect_rc=2)


def final_rpm(text):
    return float(re.search(r"\[PHYSICAL-CRANK\] ticks=\d+ rpm=([\d.]+)", text).group(1))


# the plant response, not just the event: 300 N.m stalls the engine, 10 N.m does not
light = run(["--load-step-tick", "1000000", "--load-nm", "10"])
assert final_rpm(out) == 0.0 and final_rpm(light) > 300.0, (final_rpm(out), final_rpm(light))
# --load-nm changes neither the leak nor the accessories
a = run(["--load-step-tick", "1000000", "--load-nm", "10"])
b = run(["--load-step-tick", "1000000", "--load-nm", "200"])
def intake(t):
    return re.search(r"\[PHYSICAL-INTAKE\] ([^\n]+)", t).group(1)
for key in ("leak", "accessor"):
    fa = [p for p in intake(a).split() if key in p]
    fb = [p for p in intake(b).split() if key in p]
    assert fa == fb, (key, fa, fb)
print("control limits ok")
