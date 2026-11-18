"""Compare candidate tachometer telemetry with independent CPU latch tracing."""

import os
import math
import re
import subprocess
import sys

runner, rom = sys.argv[1:3]
env = dict(os.environ, MA17_TRACE_PORT_LATCHES="1")
result = subprocess.run([runner, rom], env=env, text=True,
                        capture_output=True, timeout=30, check=True)
trace = result.stdout + result.stderr
edges = [tuple(map(int, match)) for match in re.findall(
    r"\[PORT-LATCH\] tick=(\d+) pc=[0-9A-F]+ port=90 bit=1 "
    r"high=(\d) ram47=(\d+)", trace)]
assert len(edges) >= 4, "missing independent P1.1 edge trace"
assert all(a[0] < b[0] and a[1] != b[1]
           for a, b in zip(edges, edges[1:])), "unordered/repeated latch edges"
rises = [tick for tick, high, _ in edges if high]
assert len(rises) >= 2
telemetry = re.search(r"tachometer P1.1 candidate: pulses=(\d+) rpm=([\d.]+)",
                      trace)
assert telemetry, "missing snapshot tachometer result"
assert int(telemetry[1]) == len(rises), "snapshot lost or fabricated rising edges"
period = rises[-1] - rises[-2]
expected = 30.0 * 990000.0 / period
assert abs(float(telemetry[2]) - expected) <= 0.00051
print(f"P1.1: {len(rises)} rises, period={period} ticks, rpm={expected:.6f}")
print(f"RAM47 at last rise={edges[-1][2]}; this test verifies the observer, "
      "not the P1.1-to-tachometer wiring or pulses/revolution hypothesis.")
observations = [(int(tick), float(angle)) for tick, angle in re.findall(
    r"\[P11-OBS\] tick=(\d+) high=1 angle=([\d.]+)", trace)]
assert [tick for tick, _ in observations] == rises
for (start, angle0), (end, angle1) in zip(observations, observations[1:]):
    assert angle1 > angle0
    print(f"ticks {start}..{end}: {(angle1-angle0)/(2*math.pi):.6f} "
          "physical revolutions per P1.1 rising edge (direct observation)")
