#!/usr/bin/env python3
"""Compare a PTY handshake with the same session followed by frame 38h."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time


ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "FiatTipo_MA17_dump_27c256.bin"
EMULATOR = ROOT / "build/emu8051-tty"
CLIENT = ROOT / ".venv/bin/python"
P5 = re.compile(r"^\[P5-LATCH\] instr=(\d+) .* value=([0-9A-F]{2}) "
                r".* RAM69=([0-9A-F]{2}) .* RAM32_33=([0-9A-F]{4}) "
                r"RAM34_35=([0-9A-F]{4})")


def summarize(lines, window):
    edges = []
    timer1 = []
    for line in lines:
        match = P5.match(line)
        if match:
            edges.append((int(match[1]), int(match[2], 16), *match.groups()[2:]))
        match = re.match(r"^\[TIMER1-PATH\] tick=(\d+) PC=([0-9A-F]{4}) "
                         r".* R32_33=([0-9A-F]{4}) R34_35=([0-9A-F]{4})", line)
        if match and window[0] <= int(match[1]) < window[1]:
            timer1.append(match.groups())
    selected = [edge for edge in edges if window[0] <= edge[0] < window[1]]
    result = {"p5_latch_events": len(selected),
              "ram69_values": sorted({edge[2] for edge in selected}),
              "timer_reload_pairs": sorted({f"{edge[3]}/{edge[4]}"
                                            for edge in selected}),
              "timer1_path_events": len(timer1),
              "timer1_pcs": sorted({row[1] for row in timer1}),
              "timer1_ram_pairs": sorted({f"{row[2]}/{row[3]}" for row in timer1})}
    for bit in (0, 1):
        lows = [edge[0] for edge in selected if not edge[1] & (1 << bit)]
        result[f"p5_{bit}_low_edge_periods"] = sorted({right - left
            for left, right in zip(lows, lows[1:])})
        widths = {}
        low = None
        previous = None
        for edge in edges:
            state = bool(edge[1] & (1 << bit))
            if previous is not None and state != previous:
                if not state:
                    low = edge
                elif low is not None and window[0] <= low[0] < window[1]:
                    widths.setdefault(low[2], []).append(edge[0] - low[0])
                    low = None
            previous = state
        result[f"p5_{bit}_low_widths_by_ram69"] = {
            key: sorted(set(values)) for key, values in sorted(widths.items())}
    return result


def validate(report):
    """Check the observed digital contrast without assigning physical pins."""
    control = report["control"]
    framed = report["frame38"]
    restored = report["frame38_ram69_read_9a"]
    errors = []
    for name, arm in (("control", control), ("frame38", framed),
                      ("frame38_ram69_read_9a", restored)):
        if not arm["window"]["p5_latch_events"] or not arm["window"]["timer1_path_events"]:
            errors.append(f"{name}: missing P5 or Timer1 trace")
    if any("PC=5091 R2=38 RAM2B=30" in event for event in control["serial38_events"]):
        errors.append("control: unexpectedly entered frame 38h branch")
    for name, arm in (("frame38", framed), ("frame38_ram69_read_9a", restored)):
        if not any("PC=5091 R2=38 RAM2B=30" in event for event in arm["serial38_events"]):
            errors.append(f"{name}: frame 38h branch was not reached")
        if not any("->80 source_PC=3B06" in event for event in arm["ram69_changes"]):
            errors.append(f"{name}: native RAM69h=80h producer was not seen")
    if not any("80->9A source_PC=043B" in event for event in restored["ram69_changes"]):
        errors.append("restored: RAM69h override at PC043Bh was not seen")
    base = set(control["window"]["timer_reload_pairs"])
    changed = set(framed["window"]["timer_reload_pairs"])
    if not base or not changed > base:
        errors.append("frame38: no additional Timer1/P5 reload pair")
    if set(restored["window"]["timer_reload_pairs"]) != base:
        errors.append("restored: Timer1/P5 reload pairs differ from control")
    for bit in (0, 1):
        key = f"p5_{bit}_low_edge_periods"
        periods = control["window"][key]
        changed_periods = framed["window"][key]
        restored_periods = restored["window"][key]
        if not periods or not changed_periods or not restored_periods:
            errors.append(f"P5.{bit}: missing edge periods")
            continue
        baseline = periods[len(periods) // 2]
        if not (min(changed_periods) < baseline - 500 and
                max(changed_periods) > baseline + 500):
            errors.append(f"P5.{bit}: frame 38h phase contrast missing")
        if any(abs(period - baseline) > 200 for period in restored_periods):
            errors.append(f"P5.{bit}: restored edge period differs from control")
    return errors


def run(mode, rpm, ticks, delay, window, ram69_override=None):
    environment = os.environ.copy()
    environment.update(MA17_TRACE_PC="1", MA17_TRACE_SERIAL38="1",
                       MA17_TRACE_TIMER1_PATH="1", MA17_CRANK_RPM=str(rpm),
                       MA17_STOP_TICKS=str(ticks))
    if ram69_override is not None:
        environment["MA17_OVERRIDE_RAM69"] = ram69_override
    process = subprocess.Popen([str(EMULATOR), str(ROM), "--8052"], cwd=ROOT,
                               env=environment, text=True, bufsize=1,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = []

    def collect():
        for line in process.stderr:
            if line.startswith(("[P5-LATCH]", "[SERIAL38-PATH]",
                                "[TIMER1-PATH]")) or (
                                    line.startswith("[ENGINE-RAM]") and
                                    "addr=69" in line):
                lines.append(line.rstrip())

    reader = threading.Thread(target=collect, daemon=True)
    reader.start()
    try:
        pty = None
        for line in process.stdout:
            match = re.search(r"PTY pronto em: (/dev/pts/\d+)", line)
            if match:
                pty = match[1]
                break
        if pty is None:
            raise RuntimeError("emulator did not announce a PTY")
        time.sleep(delay)
        client = subprocess.run([str(CLIENT), str(ROOT / "test_pty.py"), pty,
                                 "--frame38-probe" if mode == "frame38" else
                                 "--handshake-only"], cwd=ROOT, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=45, check=False)
        process.wait(timeout=90)
        reader.join(timeout=2)
        if process.returncode or client.returncode:
            raise RuntimeError(f"{mode}: emulator={process.returncode}, "
                               f"client={client.returncode}; "
                               f"{client.stdout.splitlines()[-5:]}")
        return {"client_exit": client.returncode,
                "emulator_exit": process.returncode,
                "ram69_override_at_043b": ram69_override,
                "client_frame_ids": re.findall(r"FRAME_ID: 0x([0-9A-F]{2})",
                                               client.stdout),
                "serial38_events": [line for line in lines
                                    if line.startswith("[SERIAL38-PATH]") and
                                    ("PC=5091" in line or "PC=5096" in line)],
                "ram69_changes": [line for line in lines
                                  if line.startswith("[ENGINE-RAM]")],
                "window": summarize(lines, window)}
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpm", type=int, default=1000)
    parser.add_argument("--ticks", type=int, default=25000000)
    parser.add_argument("--client-delay", type=float, default=5.0)
    parser.add_argument("--window", type=int, nargs=2, default=(8000000, 10000000))
    parser.add_argument("--output", type=Path, default=ROOT / "build/ma17-analysis/variants/serial38_probe.json")
    args = parser.parse_args()
    if args.rpm <= 0 or args.ticks <= 0 or args.client_delay < 0 or not 0 <= args.window[0] < args.window[1] <= args.ticks:
        parser.error("require positive RPM/ticks and a valid analysis window")
    report = {"rom_sha256": hashlib.sha256(ROM.read_bytes()).hexdigest(),
              "emulator_sha256": hashlib.sha256(EMULATOR.read_bytes()).hexdigest(),
              "rpm": args.rpm, "stop_ticks": args.ticks,
              "client_delay_seconds": args.client_delay,
              "window_ticks": args.window,
              "control": run("handshake_only", args.rpm, args.ticks,
                             args.client_delay, args.window),
              "frame38": run("frame38", args.rpm, args.ticks,
                             args.client_delay, args.window),
              "frame38_ram69_read_9a": run("frame38", args.rpm, args.ticks,
                                           args.client_delay, args.window, "9A")}
    report["validation_errors"] = validate(report)
    report["validation_pass"] = not report["validation_errors"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), **{
        key: report[key]["window"] for key in
        ("control", "frame38", "frame38_ram69_read_9a")}}))
    if report["validation_errors"]:
        raise SystemExit("serial38 validation failed: " + "; ".join(report["validation_errors"]))


if __name__ == "__main__":
    main()
