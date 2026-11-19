"""Single source of the SEVEL bench preset shared by the Python tests.

BENCH_LEAK_MM2: closed-throttle air leak of the warm bench preset (the idle
actuator is the variable throttle stop, driven by the ROM; this leak is the
fixed part of the closed-throttle area). Chosen by scanning 3..10 mm2 with the
calibrated plant (eta_v(N, p_m), eta_i ~0.36, FMEP ~1.1 bar) and the ROM:
3 mm2 starves the warm idle (525 rpm in test_physical_idle); 6 mm2 idles right but
the ROM closes the lambda loop only after ~12 M ticks (rich ramp 0.87 -> 1.0), which
breaks every ROM-timing window; 7 mm2 closes it by ~5 M ticks; 8 mm2 by ~2-3 M ticks
with a 900-975 rpm hot idle tracking the ROM target (925) and lambda 0.95-1.03.
The old simplified plant used 8-9 mm2.
Keep equal to the value in apps/sevel-ma17-lab/main.cpp.
LLM-written (Claude).
"""
BENCH_LEAK_MM2 = 8
