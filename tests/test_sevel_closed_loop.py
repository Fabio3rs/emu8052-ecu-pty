"""Conditional 20 s Fiat ROM feedback through the physical lambda input."""

import json
import os
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "20000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
        "--load-step-tick", "800000", "--load-nm", "24"]


def run(extra):
    result = subprocess.run(
        base + extra, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        text=True, capture_output=True, timeout=40, check=True)
    lines = result.stdout.splitlines()
    samples = [json.loads(line) for line in lines
               if line.startswith('{"type":"lambda"')]
    edges = [json.loads(line) for line in lines
             if line.startswith('{"type":"cc3_pin"')]
    idle_state = [json.loads(line) for line in lines
                  if line.startswith('{"type":"idle_state_raw"')]

    def summary(name):
        match = re.search(rf"\[PHYSICAL-{name}\] ([^\n]+)", result.stdout)
        assert match, result.stdout[-2000:]
        return dict(part.split("=") for part in match.group(1).split())

    assert len(samples) == 20
    return (samples, edges, idle_state, summary("CRANK"),
            summary("INTAKE"), summary("DIAG"))


# Gain 5 and the electrical ADC7 value are test hypotheses, not board measurements.
nominal, edges, idle_state, crank, intake, diag = run(["--lambda-adc-gain", "5"])
rich, _, _, _, rich_intake, rich_diag = run(["--lambda-adc-gain", "1"])
fault, _, _, _, fault_intake, fault_diag = run(
    ["--lambda-adc-gain", "5", "--lambda-stuck-mv", "4000",
     "--lambda-stuck-tick", "10000000", "--lambda-restore-tick", "14000000"])

assert 700 < float(crank["rpm"]) < 1200
assert abs(int(crank["ram47"]) * 25 - float(crank["rpm"])) < 60
assert int(intake["cc3_pulses"]) > 500
assert sum(e["tick"] > 15000000 and not e["high"] for e in edges) > 100
assert all(d["ram27"] == d["f84e"] == "0"
           for d in (diag, rich_diag, fault_diag))
assert any(s["pc"] == 0x0C85 and s["after"] == 0x80 for s in idle_state)
# Fiat 2D21h..2D56h copies source bits into F847h; bit 6 follows RAM24h.7.
for state in (s for s in idle_state if s["pc"] == 0x2D56):
    assert bool(state["after"] & 0x40) == bool(state["ram24"] & 0x80)
    assert bool(state["after"] & 0x01) == bool(state["ram27"] & 0x02)
    assert bool(state["after"] & 0x02) == bool(state["ram27"] & 0x08)
assert int(diag["f847"]) & 0x3F == 0

late = nominal[9:]
assert all(s["valid"] for s in late)
assert min(s["physical"] for s in late) < 0.95
assert max(s["physical"] for s in late) > 1.02
assert max(s["voltage_v"] for s in late) - min(s["voltage_v"] for s in late) > 0.2
assert rich[-1]["physical"] < 0.8
assert float(rich_intake["injected_kg"]) > 1.2 * float(intake["injected_kg"])

assert nominal[:10] == fault[:10]
assert all(s["adc5_pin_v"] == 4.0 for s in fault[10:14])
assert fault[13]["physical"] > nominal[13]["physical"] + 0.1
assert fault[-1]["adc5_pin_v"] < 4.0
assert abs(fault[-1]["physical"] - nominal[-1]["physical"]) < 0.05
assert abs(fault[-1]["physical"] - 1.0) < 0.1
assert float(fault_intake["injected_kg"]) < float(intake["injected_kg"])

# A larger cable step reaches a guarded ROM path; the electrical gain remains
# a scenario assumption. The smaller 4 mm step does not suspend this path.
pedal_result = subprocess.run(
    base + ["--lambda-adc-gain", "5", "--pedal-step-tick", "10000000",
            "--pedal-release-tick", "12000000", "--pedal-mm", "8"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
         "MA17_TRACE_PC": "1", "MA17_TRACE_LAMBDA_ROUTE": "1",
         "MA17_TRACE_IDLE_F839": "1",
         "MA17_TRACE_IDLE_PEDAL_GATE": "1",
         "MA17_TRACE_TPS_AFTER_TICK": "10000000"},
    text=True, capture_output=True, timeout=60, check=True)
pedal_lines = pedal_result.stdout.splitlines()
pedal_lambda = [json.loads(line) for line in pedal_lines
                if line.startswith('{"type":"lambda"')]
pedal_events = [json.loads(line) for line in pedal_lines
                if line.startswith('{"type":"pedal"') or
                line.startswith('{"type":"pedal_release"')]
pedal_diagnostics = [json.loads(line) for line in pedal_lines
                     if line.startswith('{"type":"diagnostic"')]
def lambda_route(trace):
    return [(int(match.group(1)), match.group(2),
             int(match.group(3), 16))
            for line in trace.splitlines()
            if (match := re.search(
                r"\[LAMBDA-ROUTE\] tick=(\d+) PC=([0-9A-F]+) "
                r"RAM28=[0-9A-F]+ RAM2F=[0-9A-F]+ RAM3C=([0-9A-F]+)",
                line))]


def blocked_lambda_guards(entries, start=10000000, end=12000000):
    return [entry for index, entry in enumerate(entries[:-1])
            if start <= entry[0] < end and entry[1] == "1810"
            and (entries[index + 1][1] != "186D" or
                 entries[index + 1][0] - entry[0] > 10)]


route = lambda_route(pedal_result.stderr)
f839 = [(int(match[1]), match[2], match[3], match[4])
        for line in pedal_result.stderr.splitlines()
        if (match := re.search(
            r"\[IDLE-F839\] tick=(\d+) value=([0-9A-F]{2})->"
            r"([0-9A-F]{2}) source_PC=([0-9A-F]{4})", line))]


def route_window(start, end, pc):
    return [entry for entry in route
            if start <= entry[0] < end and entry[1] == pc]


assert pedal_lambda[:10] == nominal[:10]
assert pedal_events[0]["type"] == "pedal" and not pedal_events[0]["contact"]
assert pedal_events[1]["type"] == "pedal_release" and pedal_events[1]["contact"]
assert pedal_lambda[11]["physical"] > 1.2
assert abs(pedal_lambda[-1]["physical"] - 1.0) < 0.15
guard_during = route_window(10000000, 12000000, "1810")
correction_during = route_window(10000000, 12000000, "186D")
guard_after = route_window(12000000, 14000000, "1810")
correction_after = route_window(12000000, 14000000, "186D")
assert len(guard_during) > 180
assert 0 < len(correction_during) < len(guard_during) - 40
assert any(entry[2] > 0 for entry in guard_during)
assert len(correction_after) >= len(guard_after) - 2
blocked = blocked_lambda_guards(route)
assert len(blocked) == 66
assert 11000000 < blocked[0][0] < 11030000
assert 11670000 < blocked[-1][0] < 11700000
assert blocked[1][2] == 15 and blocked[-1][2] == 1
assert correction_during[-1][0] > blocked[-1][0]

# A shorter press lets the ROM's countdown continue after cable release.
short_pedal = subprocess.run(
    base + ["--lambda-adc-gain", "5", "--pedal-step-tick", "10000000",
            "--pedal-release-tick", "11000000", "--pedal-mm", "8"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
         "MA17_TRACE_PC": "1", "MA17_TRACE_LAMBDA_ROUTE": "1"},
    text=True, capture_output=True, timeout=60, check=True)
short_route = lambda_route(short_pedal.stderr)
after_release_countdown = [entry for entry in short_route
                           if 11000000 < entry[0] < 11250000 and
                           entry[1] == "1810" and entry[2] > 0]
assert [entry[2] for entry in after_release_countdown][0] == 15
assert [entry[2] for entry in after_release_countdown][-1] == 1
assert 11000000 < after_release_countdown[0][0]
assert after_release_countdown[-1][0] < 11200000
assert any(entry[1] == "186D" and
           after_release_countdown[-1][0] < entry[0] < 11250000
           for entry in short_route)

# Holding ADC5 constant leaves this pedal-triggered guard window in place.
fixed_pedal = subprocess.run(
    base + ["--lambda-adc-gain", "5", "--pedal-step-tick", "10000000",
            "--pedal-release-tick", "12000000", "--pedal-mm", "8",
            "--lambda-stuck-tick", "2000000", "--lambda-stuck-mv", "2960"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
         "MA17_TRACE_PC": "1", "MA17_TRACE_LAMBDA_ROUTE": "1"},
    text=True, capture_output=True, timeout=60, check=True)
fixed_blocked = blocked_lambda_guards(lambda_route(fixed_pedal.stderr))
assert len(fixed_blocked) == len(blocked)
assert abs(fixed_blocked[0][0] - blocked[0][0]) < 1000
assert abs(fixed_blocked[-1][0] - blocked[-1][0]) < 1000
assert "ram27=0 f84e=0" in pedal_result.stdout
assert any(10000000 < sample["tick"] < 12000000 and
           sample["ram27"] == sample["f84e"] == 10
           for sample in pedal_diagnostics)
assert all(sample["ram27"] == sample["f84e"] == 0 and
           sample["f85e"] == 10 for sample in pedal_diagnostics
           if sample["tick"] >= 13000000)
assert any(10000000 < tick < 10200000 and (old, new, pc) ==
           ("0F", "0E", "555B") for tick, old, new, pc in f839)
assert any(10900000 < tick < 11100000 and (old, new, pc) ==
           ("2F", "2E", "555B") for tick, old, new, pc in f839)
assert any(12000000 < tick < 12100000 and (old, new, pc) ==
           ("2E", "0F", "2A4B") for tick, old, new, pc in f839)
bridge_edges = [json.loads(line) for line in pedal_lines
                if line.startswith('{"type":"bridge_candidate"')]
idle_faults = [json.loads(line) for line in pedal_lines
               if line.startswith('{"type":"idle_fault_raw"')]
extend = next(edge for edge in bridge_edges
              if 10000000 <= edge["tick"] < 12000000 and
              edge["p15"] == 1 and edge["p16"] == 0)
coast = next(edge for edge in bridge_edges
             if edge["tick"] > extend["tick"] and
             edge["p15"] == edge["p16"] == 0)
countdown_end = next(tick for tick, old, new, pc in f839
                     if (old, new, pc) == ("2F", "2E", "555B") and
                     10000000 < tick < 12000000)
fault_bit_one = next(event for event in idle_faults
                     if event["pc"] == 0x2B42 and
                     10000000 < event["tick"] < 12000000)
assert extend["tick"] < coast["tick"] < countdown_end
assert 0 < fault_bit_one["tick"] - countdown_end < 20
gate_line = next(line for line in pedal_result.stderr.splitlines()
                 if "[IDLE-PEDAL-GATE]" in line and "PC=2B31" in line)
gate_fields = dict(re.findall(
    r"(?:^| )(R2|R3|F839|A|PSW|F83E)=([0-9A-F]{2})", gate_line))
gate_tick = int(re.search(r"tick=(\d+)", gate_line).group(1))
assert countdown_end < gate_tick < fault_bit_one["tick"]
assert gate_fields["R2"] == gate_fields["R3"]
assert gate_fields["A"] == "0D"
assert int(gate_fields["PSW"], 16) & 0x80 == 0
assert int(gate_fields["F83E"], 16) > 0
assert int(gate_fields["F839"], 16) & 0xE0 == 0x20

# A shorter touch ends before the candidate idle fault is published.
short_touch = subprocess.run(
    base + ["--lambda-adc-gain", "5", "--pedal-step-tick", "10000000",
            "--pedal-release-tick", "11000000", "--pedal-mm", "8"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=40, check=True)
short_diagnostics = [json.loads(line) for line in short_touch.stdout.splitlines()
                     if line.startswith('{"type":"diagnostic"')]
short_faults = [json.loads(line) for line in short_touch.stdout.splitlines()
                if line.startswith('{"type":"idle_fault_raw"')]
assert len(short_diagnostics) == 20
assert any(event["ram27"] == 10 and event["f84e"] == 0
           for event in short_faults)
assert any(event["tick"] > 11000000 and event["ram27"] == 0
           for event in short_faults)
assert all(sample["f84e"] == sample["f85e"] == 0
           for sample in short_diagnostics)

# Original Fiat 2A9Eh compares the raw R2 input with A6h, carry set.
# The wide pedal step takes the reset path; this is not a calibrated angle.
wide_base = base.copy()
wide_base[wide_base.index("--stop-ticks") + 1] = "15000000"
wide_touch = subprocess.run(
    wide_base + ["--lambda-adc-gain", "5", "--pedal-step-tick", "10000000",
                 "--pedal-release-tick", "12000000", "--pedal-mm", "12"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
         "MA17_TRACE_PC": "1", "MA17_TRACE_IDLE_PEDAL_GATE": "1",
         "MA17_TRACE_LAMBDA_ROUTE": "1",
         "MA17_TRACE_TPS_AFTER_TICK": "10000000"},
    text=True, capture_output=True, timeout=60, check=True)
assert "PC=2A9E P46=1" in wide_touch.stderr
assert re.search(r"PC=2A9E .*R2=B8 .*A=A6", wide_touch.stderr)
assert re.search(r"PC=2A45 .*R2=B8 .*F839=0F", wide_touch.stderr)
assert not re.search(r"\[IDLE-PEDAL-GATE\].*PC=2B38", wide_touch.stderr)
mid_compare = re.search(r"PC=2A9E .*R2=([0-9A-F]{2}) .*A=A6",
                        pedal_result.stderr)
assert mid_compare and int(mid_compare[1], 16) <= 0xA5
assert re.search(rf"PC=2AB3 .*R2={mid_compare[1]}", pedal_result.stderr)


def produced_ram6f(result):
    flow = re.search(r"\[TPS-FLOW\] tick=(\d+) PC=11CC .*"
                     r"R4=([0-9A-F]{2}) .*A=([0-9A-F]{2})", result.stderr)
    assert flow
    samples = [json.loads(line) for line in result.stdout.splitlines()
               if line.startswith('{"type":"tps_ram"') and
               10000000 <= json.loads(line)["tick"] <= int(flow[1])]
    ram66 = samples[-1]["ram66"]
    assert ram66 == int(flow[2], 16)
    assert int(flow[3], 16) == ram66 - 0x0D
    return int(flow[3], 16)


assert produced_ram6f(pedal_result) == int(mid_compare[1], 16)
assert produced_ram6f(wide_touch) == 0xB8
wide_diagnostics = [json.loads(line) for line in wide_touch.stdout.splitlines()
                    if line.startswith('{"type":"diagnostic"')]
assert all(sample["f84e"] == sample["f85e"] == 0
           for sample in wide_diagnostics)

# A larger cable step leaves a post-release lambda guard window without
# the candidate idle DTC. Fixed ADC5 keeps a shorter window, so TPS alone
# does not determine its duration in this conditional electrical profile.
wide_blocked = blocked_lambda_guards(
    lambda_route(wide_touch.stderr), 12000000, 14000000)
assert len(wide_blocked) > 30
assert 12700000 < wide_blocked[0][0] < 12800000
assert 13100000 < wide_blocked[-1][0] < 13200000
fixed_wide = subprocess.run(
    wide_base + ["--lambda-adc-gain", "5", "--pedal-step-tick", "10000000",
                 "--pedal-release-tick", "12000000", "--pedal-mm", "12",
                 "--lambda-stuck-tick", "2000000", "--lambda-stuck-mv", "2960"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
         "MA17_TRACE_PC": "1", "MA17_TRACE_LAMBDA_ROUTE": "1"},
    text=True, capture_output=True, timeout=60, check=True)
fixed_wide_blocked = blocked_lambda_guards(
    lambda_route(fixed_wide.stderr), 12000000, 14000000)
assert len(fixed_wide_blocked) > 15
assert 12700000 < fixed_wide_blocked[0][0] < 12800000
assert wide_blocked[-1][0] - fixed_wide_blocked[-1][0] > 100000


def cc3_starts(result, start, end):
    edges = [json.loads(line) for line in result.stdout.splitlines()
             if line.startswith('{"type":"cc3_pin"')]
    return [event["tick"] for event in edges if not event["high"]
            and start <= event["tick"] < end]


# The extra correction delay coexists with the ROM's CC3 scheduling gap.
# This is a conditional output-pin observation, not injector polarity proof.
assert not cc3_starts(wide_touch, 12800000, 13000000)
assert cc3_starts(fixed_wide, 12800000, 13000000)
assert cc3_starts(wide_touch, 13000000, 13200000)


def intake_at_cut(tick):
    scenario = wide_base.copy()
    scenario[scenario.index("--stop-ticks") + 1] = str(tick)
    result = subprocess.run(
        scenario + ["--lambda-adc-gain", "5", "--pedal-step-tick", "10000000",
                    "--pedal-release-tick", "12000000", "--pedal-mm", "12"],
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        text=True, capture_output=True, timeout=40, check=True)
    match = re.search(r"\[PHYSICAL-INTAKE\] ([^\n]+)", result.stdout)
    assert match
    return {key: float(value) for key, value in
            (part.split("=") for part in match[1].split())}


before_cut = intake_at_cut(12800000)
after_cut = intake_at_cut(13000000)
assert before_cut["cc3_pulses"] == after_cut["cc3_pulses"]
assert before_cut["on_ticks"] == after_cut["on_ticks"]
assert before_cut["injected_kg"] == after_cut["injected_kg"]
assert after_cut["delivered_kg"] > before_cut["delivered_kg"] + 2e-5
for state in (before_cut, after_cut):
    assert abs(state["injected_kg"] - state["delivered_kg"] -
               state["film_kg"] - state["vapor_kg"]) < 3e-9

# A stronger parked acceleration exercises a longer post-release ROM guard.
# The 24 N m load and all electrical bindings remain scenario assumptions.
strong_base = base.copy()
strong_base[strong_base.index("--stop-ticks") + 1] = "18000000"
strong_touch = subprocess.run(
    strong_base + ["--lambda-adc-gain", "5", "--pedal-step-tick", "10000000",
                   "--pedal-release-tick", "12000000", "--pedal-mm", "40"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
         "MA17_TRACE_PC": "1", "MA17_TRACE_LAMBDA_ROUTE": "1"},
    text=True, capture_output=True, timeout=60, check=True)
strong_route = lambda_route(strong_touch.stderr)
strong_blocked = blocked_lambda_guards(strong_route, 12000000, 14000000)
strong_windows = []
for entry in strong_blocked:
    if not strong_windows or entry[0] - strong_windows[-1][-1][0] > 20000:
        strong_windows.append([])
    strong_windows[-1].append(entry)
strong_window = max(strong_windows, key=len)
assert len(strong_window) > 90
assert 12600000 < strong_window[0][0] < 12800000
assert 13600000 < strong_window[-1][0] < 13800000
assert strong_window[-1][0] > wide_blocked[-1][0] + 400000
assert any(tick > 14000000 and pc == "186D"
           for tick, pc, _ in strong_route)
strong_starts = cc3_starts(strong_touch, 12000000, 15000000)
strong_gaps = [later - earlier for earlier, later in
               zip(strong_starts, strong_starts[1:])]
assert 800000 < max(strong_gaps) < 1000000
assert "ram27=0 f84e=0" in strong_touch.stdout

# With no external load the same cable release starts a much longer CC3
# pause. Count gaps crossing the release tick; filtering starts after it
# would hide the cut and mislabel the lean exhaust as lambda regulation.
unloaded_base = strong_base.copy()
step = unloaded_base.index("--load-step-tick")
del unloaded_base[step:step + 4]
unloaded_base[unloaded_base.index("--stop-ticks") + 1] = "20000000"
unloaded_touch = subprocess.run(
    unloaded_base + ["--lambda-adc-gain", "5", "--pedal-step-tick",
                     "10000000", "--pedal-release-tick", "12000000",
                     "--pedal-mm", "40"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=60, check=True)
unloaded_starts = cc3_starts(unloaded_touch, 0, 20000000)
unloaded_gap = max((later - earlier, earlier, later) for earlier, later in
                   zip(unloaded_starts, unloaded_starts[1:]))
assert unloaded_gap[0] > 6000000
assert 12000000 < unloaded_gap[1] < 13000000
assert unloaded_gap[2] > 19000000
unloaded_lambda = [json.loads(line) for line in unloaded_touch.stdout.splitlines()
                   if line.startswith('{"type":"lambda"')]
assert unloaded_lambda[17]["oxygen_equivalent"] > 4.9
assert unloaded_lambda[19]["physical"] < 0.8
