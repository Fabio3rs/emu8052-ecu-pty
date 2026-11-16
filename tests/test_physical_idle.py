"""Conditional Fiat P1.5/P1.6-to-DC idle actuator loop."""

import json
import os
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "4000000", "--adc7-mv", "1232"]
invalid = subprocess.run(base + ["--idle-contact-p46"],
                         env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                         text=True, capture_output=True, timeout=5)
assert invalid.returncode == 2
invalid_p43 = subprocess.run(
    base + ["--idle-contact-p43"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=5)
assert invalid_p43.returncode == 2
invalid_reverse = subprocess.run(
    base + ["--idle-bridge-reverse"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=5)
assert invalid_reverse.returncode == 2
for extra in (["--idle-motor-speed-mm-s", "50"],
              ["--idle-bridge-p15-p16", "--idle-motor-speed-mm-s", "0"],
              ["--idle-bridge-p15-p16", "--idle-motor-speed-mm-s", "101"]):
    invalid_speed = subprocess.run(
        base + extra, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        text=True, capture_output=True, timeout=5)
    assert invalid_speed.returncode == 2
conflicting = subprocess.run(
    base + ["--idle-bridge-p15-p16", "--idle-contact-p46",
            "--idle-contact-p46-high-closed"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=5)
assert conflicting.returncode == 2
conflicting_pins = subprocess.run(
    base + ["--idle-bridge-p15-p16", "--idle-contact-p43",
            "--idle-contact-p46"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=5)
assert conflicting_pins.returncode == 2
invalid_stop = subprocess.run(
    base + ["--idle-bridge-p15-p16", "--idle-min-stop-mrad", "61"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=5)
assert invalid_stop.returncode == 2


def run(extra):
    result = subprocess.run(base + extra,
                            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                            text=True, capture_output=True, timeout=20,
                            check=True)
    output = result.stdout
    edges = [json.loads(line) for line in output.splitlines()
             if line.startswith('{"type":"bridge_candidate"')]
    states = [json.loads(line) for line in output.splitlines()
              if line.startswith('{"type":"idle_actuator"')]
    tps = re.search(r"\[PHYSICAL-TPS\] ([^\n]+)", output)
    crank = re.search(r"\[PHYSICAL-CRANK\] [^\n]*rpm=([0-9.]+)", output)
    diag = re.search(r"\[PHYSICAL-DIAG\] ([^\n]+)", output)
    assert edges and tps and crank and diag, output[-2000:]
    summary = dict(part.split("=") for part in tps.group(1).split())
    summary["rpm"] = crank.group(1)
    summary.update(("diag_" + key, value) for key, value in
                   (part.split("=") for part in diag.group(1).split()))
    releases = [json.loads(line) for line in output.splitlines()
                if line.startswith('{"type":"pedal_release"')]
    if releases:
        summary["release_contact"] = releases[-1]["contact"]
    return edges, states, summary


raw_edges, _, raw_tps = run([])
edges, states, idle_tps = run(["--idle-bridge-p15-p16"])
high_edges, high_states, high_tps = run(
    ["--idle-bridge-p15-p16", "--idle-contact-p46-high-closed"])
repeat_edges, repeat_states, repeat_tps = run(["--idle-bridge-p15-p16"])
pedal_edges, pedal_states, _ = run([
    "--idle-bridge-p15-p16", "--pedal-step-tick", "800000", "--pedal-mm", "8"])
contact_edges, contact_states, contact_tps = run(
    ["--idle-bridge-p15-p16", "--idle-contact-p46"])
_, reverse_states, reverse_tps = run(
    ["--idle-bridge-p15-p16", "--idle-contact-p46",
     "--idle-bridge-reverse"])
p43_edges, p43_states, p43_tps = run(
    ["--idle-bridge-p15-p16", "--idle-contact-p43"])
repeat_contact_edges, repeat_contact_states, repeat_contact_tps = run(
    ["--idle-bridge-p15-p16", "--idle-contact-p46"])
_, half_contact_states, half_contact_tps = run([
    "--idle-bridge-p15-p16", "--idle-contact-p46",
    "--fluid-step-ticks", "495"])
open_edges, open_states, open_tps = run([
    "--idle-bridge-p15-p16", "--idle-contact-p46",
    "--pedal-step-tick", "800000", "--pedal-mm", "8"])
_, recovered_states, recovered_tps = run([
    "--idle-bridge-p15-p16", "--idle-contact-p46",
    "--pedal-step-tick", "800000", "--pedal-mm", "8",
    "--pedal-release-tick", "2000000"])
_, hot_states, hot_tps = run([
    "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90"])
_, hot_five_states, hot_five_tps = run([
    "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
    "--idle-min-stop-mrad", "5"])
_, hot_ten_states, hot_ten_tps = run([
    "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
    "--idle-min-stop-mrad", "10"])

assert edges == repeat_edges and states == repeat_states
assert (high_edges, high_states, high_tps) == (edges, states, idle_tps)
assert idle_tps == repeat_tps and edges[:3] == raw_edges[:3]
assert any(edge["p15"] == 1 and edge["p16"] == 0 for edge in edges)
assert any(edge["p15"] == 0 and edge["p16"] == 1 and
           edge["tick"] > 1000000 for edge in edges)
assert states[0]["stop_rad"] > 0.069813
assert states[0]["ram60"] > int(raw_tps["ram60"])
assert states[0]["ram66"] > int(raw_tps["ram66"])
assert states[-1]["contact"] and float(idle_tps["angle_rad"]) > 0.069813
assert pedal_edges[0] == edges[0]
assert not pedal_states[0]["contact"]
assert pedal_states[-1]["stop_rad"] < pedal_states[0]["stop_rad"]
assert pedal_states[-1]["angle_rad"] == pedal_states[0]["angle_rad"]
assert pedal_states[-1]["ram60"] == pedal_states[0]["ram60"]
assert contact_tps["diag_f84e"] == "0"
assert reverse_tps["diag_f84e"] == "8"
assert reverse_states[-1]["contact"]
assert reverse_states[-1]["stop_rad"] < contact_states[-1]["stop_rad"]
assert p43_edges and p43_states[-1]["contact"]
assert p43_tps["diag_f84e"] == p43_tps["diag_ram27"] == "6"
assert (contact_edges, contact_states, contact_tps) == (
    repeat_contact_edges, repeat_contact_states, repeat_contact_tps)
assert abs(float(contact_tps["rpm"]) - float(half_contact_tps["rpm"])) < 1.0
assert abs(contact_states[-1]["stop_rad"] -
           half_contact_states[-1]["stop_rad"]) < 0.00002
assert half_contact_tps["diag_f84e"] == "0"
assert idle_tps["diag_f84e"] != contact_tps["diag_f84e"]
assert contact_states[-1]["contact"]
assert contact_states[-1]["ram60"] > states[-1]["ram60"]
assert sum(edge["p15"] == 0 and edge["p16"] == 1
           for edge in contact_edges) > 10
assert sum(edge["p15"] == 1 and edge["p16"] == 0
           for edge in contact_edges) > 10
assert not open_states[-1]["contact"]
assert open_tps["diag_f84e"] != "0"
assert open_states[-1]["angle_rad"] > contact_states[-1]["angle_rad"]
assert open_edges[0] == contact_edges[0]
assert recovered_tps["release_contact"]
assert recovered_tps["diag_f84e"] == "0"
assert recovered_states[-1]["contact"]
assert recovered_states[-1]["angle_rad"] == recovered_states[-1]["stop_rad"]
assert recovered_states[-1]["ram60"] < open_states[-1]["ram60"]
assert hot_states[-1]["stop_rad"] == 0.04
assert int(hot_tps["ram60"]) < 40 and int(hot_tps["ram66"]) < 95
assert hot_tps["diag_f84e"] == "8"
assert hot_five_states[-1]["stop_rad"] == 0.005
assert hot_ten_states[-1]["stop_rad"] == 0.01
assert hot_five_tps["diag_f84e"] == "0"
assert hot_ten_tps["diag_f84e"] == "0"
assert hot_ten_tps["ram6f"] == "65"
assert float(hot_five_tps["rpm"]) < float(hot_ten_tps["rpm"])


def summary_with_trace(trace):
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    if trace:
        environment["MA17_TRACE_PC"] = "1"
    result = subprocess.run(
        base[:5] + ["--stop-ticks", "2000000", "--adc7-mv", "1232",
                    "--idle-bridge-p15-p16", "--idle-contact-p46"],
        env=environment, text=True, capture_output=True, timeout=20,
        check=True)
    return [line for line in result.stdout.splitlines()
            if line.startswith("[PHYSICAL-")]


assert summary_with_trace(False) == summary_with_trace(True)


def published_faults(min_stop_mrad):
    result = subprocess.run(
        base + ["--idle-bridge-p15-p16", "--idle-contact-p46",
                "--coolant-c", "90", "--idle-min-stop-mrad", min_stop_mrad],
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
             "MA17_TRACE_PC": "1", "MA17_TRACE_IDLE_PUBLISH": "1"},
        text=True, capture_output=True, timeout=25, check=True)
    rows = [dict(re.findall(r"(PC|RAM27|F884|R7|F84E)=([0-9A-F]+)", line))
            for line in result.stderr.splitlines()
            if line.startswith("[IDLE-PUBLISH]") and "PC=41E5" in line]
    assert rows and all(row["R7"] == row["F84E"] for row in rows)
    return rows


assert all(row["F84E"] == "00" for row in published_faults("5"))
ten_rows = published_faults("10")
assert all(row["F84E"] == "00" for row in ten_rows)
assert ten_rows[0]["RAM27"] == ten_rows[0]["F884"] == "04"
assert all(row["RAM27"] == row["F884"] == "00"
           for row in ten_rows[1:])


def pedal_at_speed(speed):
    result = subprocess.run(
        [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
         "--stop-ticks", "13000000", "--adc7-mv", "1232",
         "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
         "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
         "--load-step-tick", "800000", "--load-nm", "24",
         "--lambda-adc-gain", "5", "--pedal-step-tick", "10000000",
         "--pedal-release-tick", "12000000", "--pedal-mm", "8",
         "--idle-motor-speed-mm-s", str(speed)],
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
             "MA17_TRACE_PC": "1", "MA17_TRACE_IDLE_F839": "1"},
        text=True, capture_output=True, timeout=45, check=True)
    edges = [json.loads(line) for line in result.stdout.splitlines()
             if line.startswith('{"type":"bridge_candidate"')]
    contacts = [json.loads(line) for line in result.stdout.splitlines()
                if line.startswith('{"type":"idle_contact"')]
    diagnostics = [json.loads(line) for line in result.stdout.splitlines()
                   if line.startswith('{"type":"diagnostic"')]
    return edges, contacts, diagnostics, result.stderr


slow_edges, slow_contacts, slow_diagnostics, slow_trace = pedal_at_speed(40)
fast_edges, fast_contacts, fast_diagnostics, fast_trace = pedal_at_speed(50)
assert not any(10000000 < edge["tick"] < 12000000 and edge["contact"]
               for edge in slow_edges)
assert any(10000000 < edge["tick"] < 12000000 and edge["contact"]
           for edge in fast_edges)
assert not any(10000000 < event["tick"] < 12000000 and event["closed"]
               for event in slow_contacts)
assert any(10000000 < event["tick"] < 12000000 and event["closed"]
           for event in fast_contacts)
assert any(10000000 < event["tick"] < 12000000 and not event["closed"]
           for event in fast_contacts)
assert any(10000000 < item["tick"] < 12000000 and item["f84e"] == 10
           for item in slow_diagnostics)
assert all(item["f84e"] == 0 for item in fast_diagnostics)
def pedal_resets(trace):
    return [int(match[1]) for match in re.finditer(
        r"\[IDLE-F839\] tick=(\d+) value=[0-9A-F]{2}->0F "
        r"source_PC=2A4B", trace)
        if 10000000 < int(match[1]) < 12000000]


assert not pedal_resets(slow_trace)
assert pedal_resets(fast_trace)
closed_tick = next(event["tick"] for event in fast_contacts
                   if 10000000 < event["tick"] < 12000000 and event["closed"])
open_tick = next(event["tick"] for event in fast_contacts
                 if event["tick"] > closed_tick and not event["closed"])
assert closed_tick < pedal_resets(fast_trace)[0] < open_tick
