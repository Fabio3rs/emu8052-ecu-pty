#!/usr/bin/env python3
"""Trace the Fiat Tipo 27C256 MA1.7 ROM with its 11.88 MHz PTY profile.

The Renault Clio MA1.7 has a different hardware revision and is not a valid
target for this clock, crank input or port mapping.
"""

import argparse
import bisect
import collections
import hashlib
import json
import os
import re
import signal
import statistics
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build" / "ma17-analysis"
PC = re.compile(r"\bPC=0x([0-9A-Fa-f]{4})\b")
RAM47 = re.compile(r"^\[RAM_47\] 0x([0-9A-Fa-f]{2}) → 0x([0-9A-Fa-f]{2}) \(PC=0x([0-9A-Fa-f]{4})\)")
RAM_C4 = re.compile(r"^\[RAM_C4\] State: 0x([0-9A-Fa-f]{2}) → 0x([0-9A-Fa-f]{2}) "
                    r"\(PC=0x([0-9A-Fa-f]{4})\)")
SENSOR_RAM = re.compile(r"^\[SENSOR-RAM\] tick=(\d+) addr=([0-9A-Fa-f]{2}) "
                        r"value=([0-9A-Fa-f]{2})->([0-9A-Fa-f]{2}) "
                        r"source_PC=([0-9A-Fa-f]{4})")
ENGINE_RAM = re.compile(r"^\[ENGINE-RAM\] tick=(\d+) addr=([0-9A-Fa-f]{2}) "
                        r"value=([0-9A-Fa-f]{2})->([0-9A-Fa-f]{2}) "
                        r"source_PC=([0-9A-Fa-f]{4})")
FAULT_XRAM = re.compile(r"^\[FAULT-XRAM\] tick=(\d+) addr=([0-9A-Fa-f]{4}) "
                         r"value=([0-9A-Fa-f]{2})->([0-9A-Fa-f]{2}) "
                         r"source_PC=([0-9A-Fa-f]{4})")
P5_LATCH = re.compile(r"^\[P5-LATCH\] instr=(\d+) PC=([0-9A-Fa-f]{4}) "
                      r"value=([0-9A-Fa-f]{2}) RAM47=([0-9A-Fa-f]{2}) "
                      r"source_PC=([0-9A-Fa-f]{4})")
P11_LATCH = re.compile(r"^\[P1\.1-LATCH\] instr=(\d+) source_PC=([0-9A-Fa-f]{4}) "
                       r"value=([01]) RAM47=([0-9A-Fa-f]{2})")
CC3_ENTRY = re.compile(r"^\[CC3-ENTRY\] instr=(\d+) PC=([0-9A-Fa-f]{4}) "
                       r"flags2B=([0-9A-Fa-f]{2})")
CC3_INPUT = re.compile(r"^\[CC3-ENTRY\].*PC=([0-9A-Fa-f]{4}) "
                       r"flags2B=([0-9A-Fa-f]{2}) flags26=([0-9A-Fa-f]{2}) "
                       r"IRAM14_15=([0-9A-Fa-f]{4})")
CC3_GATE = re.compile(r"^\[CC3-GATE\] instr=(\d+) P2=([0-9A-Fa-f]{2}) "
                      r"XPAGE=([0-9A-Fa-f]{2}) ACC=([0-9A-Fa-f]{2})")
KLINE_PAGE = re.compile(r"^\[KLINE-PAGE\] instr=(\d+) P2=([0-9A-Fa-f]{2}) "
                        r"XPAGE=([0-9A-Fa-f]{2})")
P13_EDGE = re.compile(r"^\[P1\.3-SHADOW\] tick=(\d+) 0x([0-9A-Fa-f]{2}) "
                      r"→ 0x([0-9A-Fa-f]{2}).*source_PC=([0-9A-Fa-f]{4})")
CC3_MATCH = re.compile(r"^\[CC3-MATCH-CANDIDATE\] tick=(\d+) PC=([0-9A-Fa-f]{4}) "
                       r"T2=([0-9A-Fa-f]{4}) shadow_P1_3=([01])")
CC3_PIN = re.compile(r"^\[CC3-PIN\] tick=(\d+) PC=([0-9A-Fa-f]{4}) "
                     r"value=([01]) shadow=([01])")
CRANK_REV = re.compile(r"^\[CRANK-REV\] rpm=(\d+) teeth=(\d+) gaps=(\d+) "
                       r"ticks_per_tooth=(\d+)")
EVENTS = ("[RESET_0 ENTRY", "[ISR-TF0]", "[SIGUSR1]", "[K-LINE]",
          "[5-BAUD", "[UART", "[S0CON-WRITE]", "[CRANK-EDGE]",
          "[CRANK-POLL]", "[CRANK-LOOP-RESTART]", "[ISR-IEX3]",
          "[PORT-EDGE]", "[P5-LATCH]", "[CC3-ENTRY]", "[CC3-GATE]",
          "[CC3-GATE-WRITE]", "[P1.3-SHADOW]", "[CC3-MATCH-CANDIDATE]",
          "[CC3-PIN]", "[CRANK-REV]", "[KLINE-PAGE]")
RPM_PCS = (0x01AB, 0x01AE, 0x0DEE, 0x0EA5, 0x565A, 0x566C)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=5.5)
    parser.add_argument("--inject-after", type=float, default=1.0)
    parser.add_argument("--no-kline-inject", action="store_true",
                        help="observe crank input without the 5-baud SIGUSR1 stimulus")
    parser.add_argument("--crank-immediate", action="store_true",
                        help="start 60-2 input at boot instead of after five seconds")
    parser.add_argument("--rpm", type=int, default=1000,
                        help="60-2 crankshaft target RPM (300-6000)")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT,
                        help="directory for the trace log and execution report")
    args = parser.parse_args()
    if not 300 <= args.rpm <= 6000:
        parser.error("--rpm must be between 300 and 6000")
    if args.seconds <= 0 or (not args.no_kline_inject and
                             not 0 < args.inject_after < args.seconds):
        parser.error("require positive --seconds and 0 < --inject-after < --seconds")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    log = output / "emulator-trace.log"
    command = [str(ROOT / "build" / "emu8051-tty"),
               str(ROOT / "FiatTipo_MA17_dump_27c256.bin"), "--8052"]
    environment = os.environ.copy()
    environment["MA17_TRACE_PC"] = "1"
    environment["MA17_CRANK_RPM"] = str(args.rpm)
    adc_input_values = [120, 130, 100, 80, 90, 110, 95, 105]
    for channel in range(8):
        key = f"MA17_ADC_CH{channel}"
        if key not in environment:
            continue
        setting = environment[key]
        if not re.fullmatch(r"[0-9]+", setting) or not 4 <= int(setting) <= 247:
            parser.error(f"{key} must be a decimal value from 4 to 247")
        adc_input_values[channel] = int(setting)
    adc7_input_value = adc_input_values[7]
    if args.crank_immediate:
        environment["MA17_CRANK_IMMEDIATE"] = "1"
    with log.open("w") as stream:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stream,
                                   stderr=subprocess.STDOUT, env=environment)
        try:
            if args.no_kline_inject:
                time.sleep(args.seconds)
            else:
                time.sleep(args.inject_after)
                if process.poll() is not None:
                    raise RuntimeError(f"emulator stopped early: {process.returncode}")
                process.send_signal(signal.SIGUSR1)
                time.sleep(args.seconds - args.inject_after)
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    counts = collections.Counter()
    examples = {}
    pcs = set()
    pc_hits = set()
    pc_coverage = {}
    crank_started = False
    ram47_changes = []
    sensor_ram_changes = collections.defaultdict(list)
    engine_ram_changes = collections.defaultdict(list)
    fault_xram_changes = collections.defaultdict(list)
    capture_state_changes = collections.Counter()
    first_capture_state_changes = []
    p5_starts = {0: [], 1: []}
    p5_widths = {0: [], 1: []}
    p5_low_since = {0: None, 1: None}
    p5_sequence = []
    p11_low_starts = []
    p11_low_widths = []
    p11_low_since = None
    p11_source_counts = collections.Counter()
    p5_source_counts = collections.Counter()
    previous_p5_value = None
    cc3_entries = []
    cc3_scheduling_inputs = []
    cc3_scheduling_entries = []
    cc3_gate_reads = []
    kline_page_samples = []
    p13_low_starts = []
    p13_low_widths = []
    p13_low_since = None
    p13_source_counts = collections.Counter()
    cc3_matches = []
    cc3_pin_edges = []
    crank_revolutions = []
    for number, line in enumerate(log.read_text(errors="replace").splitlines(), 1):
        if "Startup delay complete - Beginning pulse injection" in line:
            crank_started = True
        ram47 = RAM47.match(line)
        sensor_ram = SENSOR_RAM.match(line)
        if sensor_ram:
            tick, address, before, after, source_pc = sensor_ram.groups()
            sensor_ram_changes[address].append({"tick": int(tick),
                                                "before": before, "after": after,
                                                "source_pc": source_pc})
        engine_ram = ENGINE_RAM.match(line)
        if engine_ram:
            tick, address, before, after, source_pc = engine_ram.groups()
            engine_ram_changes[address].append({"tick": int(tick),
                                                "before": before, "after": after,
                                                "source_pc": source_pc})
        fault_xram = FAULT_XRAM.match(line)
        if fault_xram:
            tick, address, before, after, source_pc = fault_xram.groups()
            fault_xram_changes[address].append({"tick": int(tick),
                                                "before": before, "after": after,
                                                "source_pc": source_pc})
        if ram47:
            before, after, pc = ram47.groups()
            ram47_changes.append({"before": before, "after": after,
                                  "next_pc": pc, "log_line": number})
        state = RAM_C4.match(line)
        if state:
            before, after, next_pc = (value.upper() for value in state.groups())
            capture_state_changes[(before, after, next_pc)] += 1
            if len(first_capture_state_changes) < 20:
                first_capture_state_changes.append({"before": before, "after": after,
                                                    "next_pc": next_pc,
                                                    "log_line": number})
        p5 = P5_LATCH.match(line)
        if p5:
            instruction, _, latch, rpm_byte, source_pc = p5.groups()
            instruction, latch, rpm_byte = int(instruction), int(latch, 16), int(rpm_byte, 16)
            if 0 < rpm_byte < 0xFF:
                for channel in (0, 1):
                    if (previous_p5_value is not None and
                            (previous_p5_value ^ latch) & (1 << channel)):
                        edge = "low" if not latch & (1 << channel) else "high"
                        p5_source_counts[(channel, edge, source_pc)] += 1
                    if not latch & (1 << channel) and p5_low_since[channel] is None:
                        p5_low_since[channel] = instruction
                        p5_starts[channel].append(instruction)
                        p5_sequence.append((instruction, channel))
                    elif latch & (1 << channel) and p5_low_since[channel] is not None:
                        p5_widths[channel].append(instruction - p5_low_since[channel])
                        p5_low_since[channel] = None
            previous_p5_value = latch
        p11 = P11_LATCH.match(line)
        if p11:
            instruction, source_pc, level, rpm_byte = p11.groups()
            instruction, level, rpm_byte = int(instruction), int(level), int(rpm_byte, 16)
            if 0 < rpm_byte < 0xFF:
                p11_source_counts[("low" if level == 0 else "high", source_pc)] += 1
                if level == 0:
                    p11_low_starts.append(instruction)
                    p11_low_since = instruction
                elif p11_low_since is not None:
                    p11_low_widths.append(instruction - p11_low_since)
                    p11_low_since = None
        cc3 = CC3_ENTRY.match(line)
        if cc3:
            instruction, pc, flags = cc3.groups()
            cc3_entries.append({"instr": int(instruction), "pc": pc,
                                "guard_2b5_set": bool(int(flags, 16) & 0x20)})
        cc3_input = CC3_INPUT.match(line)
        if cc3_input:
            pc, flags2b, flags26, raw = cc3_input.groups()
            value = int(raw, 16)
            if (pc.upper() == "058E" and not int(flags2b, 16) & 0x20 and
                    not int(flags26, 16) & 0x80 and value >= 0x000D):
                cc3_scheduling_inputs.append(value)
                cc3_scheduling_entries.append((int(cc3.group(1)), value))
        gate = CC3_GATE.match(line)
        if gate:
            instruction, p2, xpage, value = gate.groups()
            cc3_gate_reads.append({"instr": int(instruction), "p2": p2,
                                   "xpage": xpage, "value": value})
        page = KLINE_PAGE.match(line)
        if page:
            instruction, p2, xpage = page.groups()
            kline_page_samples.append({"instr": int(instruction),
                                       "p2": p2, "xpage": xpage})
        p13 = P13_EDGE.match(line)
        if p13:
            instruction, before, after, source_pc = p13.groups()
            instruction, before, after = int(instruction), int(before, 16), int(after, 16)
            p13_source_counts[("low" if after == 0 else "high", source_pc)] += 1
            if before == 1 and after == 0:
                p13_low_since = instruction
                p13_low_starts.append(instruction)
            elif before == 0 and after == 1 and p13_low_since is not None:
                p13_low_widths.append(instruction - p13_low_since)
                p13_low_since = None
        match = CC3_MATCH.match(line)
        if match:
            tick, _, _, shadow = match.groups()
            cc3_matches.append((int(tick), int(shadow)))
        pin = CC3_PIN.match(line)
        if pin:
            tick, _, value, _ = pin.groups()
            cc3_pin_edges.append((int(tick), int(value)))
        revolution = CRANK_REV.match(line)
        if revolution:
            rpm, teeth, gaps, interval = map(int, revolution.groups())
            crank_revolutions.append((rpm, teeth, gaps, interval))
        if line.startswith("[PC-HIT] "):
            pc_hits.add(int(line.split()[1], 16))
        if line.startswith("[PC-COVERAGE]"):
            pc_coverage = {key: int(value) for key, value in
                           re.findall(r"(\w+)=(\d+)", line)}
        match = PC.search(line)
        if match:
            pcs.add(match.group(1).upper())
        for event in EVENTS:
            if event in line:
                counts[event] += 1
                examples.setdefault(event, {"line": number, "text": line[:200]})
    if pc_coverage.get("unique") != len(pc_hits):
        raise RuntimeError("PC summary and hit list disagree")
    output_latches = {}
    for channel in (0, 1):
        periods = [b - a for a, b in zip(p5_starts[channel], p5_starts[channel][1:])]
        output_latches[f"P5.{channel}"] = {
            "low_starts": len(p5_starts[channel]),
            "median_period_ticks": statistics.median(periods) if periods else None,
            "median_low_width_ticks": (statistics.median(p5_widths[channel])
                                       if p5_widths[channel] else None)}
    half_periods = [later[0] - earlier[0] for earlier, later in
                    zip(p5_sequence, p5_sequence[1:])]
    output_latches["sequence"] = {
        "alternating": (len(p5_sequence) > 1 and all(
            earlier[1] != later[1] for earlier, later in
            zip(p5_sequence, p5_sequence[1:]))),
        "median_between_channels_ticks": (statistics.median(half_periods)
                                          if half_periods else None)}
    output_latches["source_pcs"] = [
        {"channel": f"P5.{channel}", "edge": edge, "pc": pc, "count": count}
        for (channel, edge, pc), count in sorted(p5_source_counts.items())]
    p11_periods = [b - a for a, b in zip(p11_low_starts, p11_low_starts[1:])]
    p13_periods = [b - a for a, b in zip(p13_low_starts, p13_low_starts[1:])]
    cc3_pin_lows = [tick for tick, value in cc3_pin_edges if value == 0]
    cc3_pin_periods = [b - a for a, b in zip(cc3_pin_lows, cc3_pin_lows[1:])]
    cc3_after_p5_offsets = []
    for (p5_tick, _), (next_p5_tick, _) in zip(p5_sequence, p5_sequence[1:]):
        index = bisect.bisect_left(cc3_pin_lows, p5_tick)
        if index < len(cc3_pin_lows) and cc3_pin_lows[index] < next_p5_tick:
            cc3_after_p5_offsets.append(cc3_pin_lows[index] - p5_tick)
    cc3_pin_low_widths = [later[0] - earlier[0] for earlier, later in
                          zip(cc3_pin_edges, cc3_pin_edges[1:])
                          if earlier[1] == 0 and later[1] == 1]
    cc3_width_errors = []
    for index, (entry_tick, raw) in enumerate(cc3_scheduling_entries):
        next_entry = (cc3_scheduling_entries[index + 1][0]
                      if index + 1 < len(cc3_scheduling_entries) else float("inf"))
        low_tick = next((tick for tick, level in cc3_pin_edges
                         if entry_tick <= tick < next_entry and level == 0), None)
        high_tick = next((tick for tick, level in cc3_pin_edges
                          if low_tick is not None and low_tick < tick < next_entry
                          and level == 1), None)
        if low_tick is not None and high_tick is not None:
            cc3_width_errors.append(high_tick - low_tick - 4 * raw)
    (output / "pc-hits.txt").write_text(
        "".join(f"{address:04X}\n" for address in sorted(pc_hits)))
    inventory_file = OUTPUT / "inventory.json"
    observed_functions = []
    if inventory_file.exists():
        inventory = json.loads(inventory_file.read_text())
        firmware_hash = hashlib.sha256(
            (ROOT / "FiatTipo_MA17_dump_27c256.bin").read_bytes()).hexdigest()
        if inventory["rom_sha256"] != firmware_hash:
            raise RuntimeError("inventory hash does not match firmware")
        observed_functions = [
            {"address": item["address"], "ida_name": item["name"],
             "semantic_alias": item.get("semantic_alias")}
            for item in inventory["functions"] if int(item["address"], 16) in pc_hits]
    report = {"firmware_origin": "Fiat Tipo Bosch Monomotronic MA1.7",
              "hardware_profile": "Fiat Tipo 11.88 MHz; P4 K-line; P1.0 crank",
              "emulator_exit": process.returncode,
              "duration_seconds": args.seconds,
              "crank_target_rpm": args.rpm,
              "timebase": "emulated machine-cycle ticks",
              "adc_input_values": adc_input_values,
              "adc7_input_value": adc7_input_value,
              "injection_signal_sent": not args.no_kline_inject,
              "crank_immediate": args.crank_immediate,
              "event_counts": dict(counts), "first_examples": examples,
              "distinct_pc_values_in_log": len(pcs),
              "observed_reset_entry": counts["[RESET_0 ENTRY"] > 0,
              "observed_timer0_interrupt": counts["[ISR-TF0]"] > 0,
              "observed_injection_start": counts["[SIGUSR1]"] > 0,
              "rpm_observation": {
                  "crank_scheduler_started": crank_started,
                  "ram47_changes": ram47_changes,
                  "pc_hits": {f"0x{address:04X}": address in pc_hits
                              for address in RPM_PCS}},
              "sensor_ram_observation": dict(sensor_ram_changes),
              "engine_ram_observation": dict(engine_ram_changes),
              "fault_xram_observation": dict(fault_xram_changes),
              "capture_state_observation": {
                  "ram_c4_transition_count": sum(capture_state_changes.values()),
                  "transitions": [
                      {"before": before, "after": after, "next_pc": next_pc,
                       "count": count}
                      for (before, after, next_pc), count in
                      sorted(capture_state_changes.items())],
                  "first_events": first_capture_state_changes},
              "wheel_observation": {
                  "complete_revolutions": len(crank_revolutions),
                  "teeth_per_revolution": sorted({row[1] for row in crank_revolutions}),
                  "gaps_per_revolution": sorted({row[2] for row in crank_revolutions}),
                  "ticks_per_tooth": sorted({row[3] for row in crank_revolutions})},
              "output_latches": output_latches,
              "cc3_p5_phase_observation": {
                  "paired_half_cycles": len(cc3_after_p5_offsets),
                  "cc3_low_after_p5_low_median_ticks": (
                      statistics.median(cc3_after_p5_offsets)
                      if cc3_after_p5_offsets else None),
                  "cc3_low_after_p5_low_min_ticks": min(cc3_after_p5_offsets, default=None),
                  "cc3_low_after_p5_low_max_ticks": max(cc3_after_p5_offsets, default=None)},
              "p1_1_observation": {
                  "low_starts": len(p11_low_starts),
                  "median_period_ticks": statistics.median(p11_periods) if p11_periods else None,
                  "median_low_width_ticks": (statistics.median(p11_low_widths)
                                             if p11_low_widths else None),
                  "source_pcs": [
                      {"edge": edge, "pc": pc, "count": count}
                      for (edge, pc), count in sorted(p11_source_counts.items())]},
              "kline_page_observation": {
                  "entry_samples": len(kline_page_samples),
                  "p2_values": sorted({item["p2"] for item in kline_page_samples}),
                  "xpage_values": sorted({item["xpage"] for item in kline_page_samples})},
              "cc3_observation": {
                  "entry_samples": len(cc3_entries),
                  "guarded_entry_samples": sum(item["guard_2b5_set"]
                                               for item in cc3_entries),
                  "entry_pcs": sorted({item["pc"] for item in cc3_entries}),
                  "iram14_15_scheduling_samples": len(cc3_scheduling_inputs),
                  "iram14_15_min": min(cc3_scheduling_inputs, default=None),
                  "iram14_15_median": (statistics.median(cc3_scheduling_inputs)
                                         if cc3_scheduling_inputs else None),
                  "iram14_15_max": max(cc3_scheduling_inputs, default=None),
                  "gate_read_samples": len(cc3_gate_reads),
                  "gate_values": sorted({item["value"] for item in cc3_gate_reads}),
                  "p1_3_shadow_edges": counts["[P1.3-SHADOW]"],
                  "p1_3_shadow_source_pcs": [
                      {"edge": edge, "pc": pc, "count": count}
                      for (edge, pc), count in sorted(p13_source_counts.items())],
                  "p1_3_shadow_low_starts": len(p13_low_starts),
                  "p1_3_shadow_median_period_ticks": (statistics.median(p13_periods)
                                                       if p13_periods else None),
                  "p1_3_shadow_median_low_width_ticks": (statistics.median(p13_low_widths)
                                                          if p13_low_widths else None),
                  "cc3_pin_model_edges": len(cc3_pin_edges),
                  "cc3_pin_model_low_starts": len(cc3_pin_lows),
                  "cc3_pin_model_median_period_ticks": (statistics.median(cc3_pin_periods)
                                                         if cc3_pin_periods else None),
                  "cc3_pin_model_median_low_width_ticks": (statistics.median(cc3_pin_low_widths)
                                                            if cc3_pin_low_widths else None),
                  "cc3_pin_model_paired_pulses": len(cc3_width_errors),
                  "cc3_pin_model_width_minus_4x_raw_median_ticks": (
                      statistics.median(cc3_width_errors) if cc3_width_errors else None),
                  "cc3_pin_model_width_minus_4x_raw_range_ticks": (
                      [min(cc3_width_errors), max(cc3_width_errors)]
                      if cc3_width_errors else None),
                  "compare_match_candidates": len(cc3_matches),
                  "shadow_values_at_match": sorted({shadow for _, shadow in
                                                    cc3_matches})},
              "pc_coverage": pc_coverage,
              "observed_ida_function_count": len(observed_functions),
              "observed_ida_functions": observed_functions,
              "pc_hits_file": os.path.relpath(output / "pc-hits.txt", ROOT),
              "log_file": os.path.relpath(log, ROOT)}
    (output / "execution.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in
                      ("emulator_exit", "adc7_input_value", "crank_target_rpm",
                       "pc_coverage",
                       "observed_ida_function_count",
                       "rpm_observation", "capture_state_observation",
                       "sensor_ram_observation",
                       "wheel_observation", "output_latches", "p1_1_observation",
                       "cc3_p5_phase_observation",
                       "cc3_observation", "kline_page_observation",
                       "pc_hits_file",
                       "log_file")}, indent=2))


if __name__ == "__main__":
    main()
