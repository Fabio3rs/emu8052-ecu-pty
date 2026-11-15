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
INJECTION_FLOW = re.compile(
    r"^\[INJECTION-FLOW\] tick=(\d+) PC=([0-9A-F]{4}) "
    r"R2=([0-9A-F]{2}) R3=([0-9A-F]{2}) RAM63=([0-9A-F]{2}) "
    r"RAM78=([0-9A-F]{2}) RAM48=([0-9A-F]{2}) DPTR=([0-9A-F]{4}) "
    r"PSW=([0-9A-F]{2}) FLAGS25=([0-9A-F]{2}) FLAGS2E=([0-9A-F]{2})$")
FAULT_XRAM = re.compile(r"^\[FAULT-XRAM\] tick=(\d+) addr=([0-9A-Fa-f]{4}) "
                         r"value=([0-9A-Fa-f]{2})->([0-9A-Fa-f]{2}) "
                         r"source_PC=([0-9A-Fa-f]{4})")
ADAPT_XRAM = re.compile(r"^\[ADAPT-XRAM\] tick=(\d+) addr=([0-9A-Fa-f]{4}) "
                         r"value=([0-9A-Fa-f]{2})->([0-9A-Fa-f]{2}) "
                         r"source_PC=([0-9A-Fa-f]{4})")
LAMBDA_BOUND_XRAM = re.compile(r"^\[LAMBDA-BOUND-XRAM\] tick=(\d+) "
                               r"addr=(F8E[89AB]) "
                               r"value=([0-9A-F]{2})->([0-9A-F]{2}) "
                               r"source_PC=([0-9A-F]{4})$")
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
MOVC = re.compile(r"^\[MOVC-SUMMARY\] pc=([0-9A-F]{4}) opcode=(83|93) "
                  r"dptr=([0-9A-F]{4}) acc=([0-9A-F]{2}) "
                  r"address=([0-9A-F]{4}) mapped=([0-9A-F]{4}) "
                  r"value=([0-9A-F]{2}) count=(\d+)$")
MOVC_BUCKET = re.compile(r"^\[MOVC-BUCKET\] start=(\d+) "
                         r"address=([0-9A-F]{4}) count=(\d+)$")
INDIRECT_IRAM = re.compile(
    r"^\[INDIRECT-IRAM-READ\] pc=([0-9A-F]{4}) opcode=([0-9A-F]{2}) "
    r"address=([0-9A-F]{2}) value=([0-9A-F]{2}) "
    r"count=(\d+) first_tick=(\d+)$")
TRACE_STOP = re.compile(r"^\[TRACE-STOP\] ticks=(\d+)$")
LOOKUP = re.compile(r"^\[LOOKUP-SUMMARY\] rpm=([0-9A-F]{2}) load=([0-9A-F]{2}) "
                    r"selector=([0-9A-F]{2}) flags=([0-9A-F]{2}) "
                    r"r0=([0-9A-F]{2}) r4=([0-9A-F]{2}) r5=([0-9A-F]{2}) "
                    r"r6=([0-9A-F]{2}) result_a=([0-9A-F]{2}) "
                    r"result_b=([0-9A-F]{2}) count=(\d+)$")
EVENTS = ("[RESET_0 ENTRY", "[ISR-TF0]", "[SIGUSR1]", "[K-LINE]",
          "[5-BAUD", "[UART", "[S0CON-WRITE]", "[CRANK-EDGE]",
          "[CRANK-POLL]", "[CRANK-LOOP-RESTART]", "[ISR-IEX3]",
          "[PORT-EDGE]", "[P5-LATCH]", "[CC3-ENTRY]", "[CC3-DECISION]",
          "[CC3-GATE]",
          "[CC3-GATE-WRITE]", "[P1.3-SHADOW]", "[CC3-MATCH-CANDIDATE]",
          "[CC3-PIN]", "[CRANK-REV]", "[KLINE-PAGE]")
RPM_PCS = (0x01AB, 0x01AE, 0x0DEE, 0x0EA5, 0x565A, 0x566C)


def summarize_injection_flow(events):
    unique = []
    for event in events:
        if (unique and event["pc"] == unique[-1]["pc"] and
                event["tick"] - unique[-1]["tick"] <= 2):
            continue  # A delayed instruction can appear on adjacent pre-tick probes.
        unique.append(event)
    stages = collections.Counter(event["pc"] for event in unique)
    pairs = []
    pending = None
    for event in unique:
        if event["pc"] == "1DD8":
            pending = event
        elif event["pc"] == "1E02" and pending is not None:
            if 0 <= event["tick"] - pending["tick"] <= 100:
                pairs.append({"entry_tick": pending["tick"],
                              "entry_r2r3": pending["r2r3"],
                              "exit_r2r3": event["r2r3"],
                              "ram63": pending["ram63"],
                              "ram78": pending["ram78"]})
            pending = None
    return {"stage_samples": dict(stages), "paired_checks": len(pairs),
            "unchanged_r2r3_pairs": sum(p["entry_r2r3"] == p["exit_r2r3"]
                                        for p in pairs),
            "changed_r2r3_pairs": sum(p["entry_r2r3"] != p["exit_r2r3"]
                                      for p in pairs),
            "first_pairs": pairs[:3], "last_pairs": pairs[-3:]}


def parse_ram69_producer(line):
    """Read a G/S88 pre-tick sample at the lower IRAM[69h] writer."""
    if not line.startswith("[RAM69-PATH]") or "PC=3B06" not in line:
        return None
    try:
        fields = dict(token.split("=", 1) for token in line.split()[1:])
        return {key: f"{int(fields[key], 16):02X}" for key in
                ("U8C", "RAM47", "RAM69", "flags2B")}
    except (KeyError, ValueError) as error:
        raise ValueError("invalid RAM69 producer trace") from error


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
    parser.add_argument("--firmware", type=Path,
                        default=ROOT / "FiatTipo_MA17_dump_27c256.bin",
                        help="Fiat gasoline ROM or a byte-identical-code calibration variant")
    parser.add_argument("--trace-movc", action="store_true",
                        help="aggregate executed MOVC reads by PC, input and ROM address")
    parser.add_argument("--movc-bucket-ticks", type=int,
                        help="also aggregate MOVC ROM addresses by emulated tick window")
    parser.add_argument("--trace-lookup", action="store_true",
                        help="aggregate 137Bh matrix lookup inputs and A/B results")
    parser.add_argument("--stop-ticks", type=int,
                        help="stop after this many emulated ticks; --seconds is a wall timeout")
    args = parser.parse_args()
    if args.movc_bucket_ticks is not None and (
            not args.trace_movc or args.movc_bucket_ticks <= 0):
        parser.error("--movc-bucket-ticks requires --trace-movc and a positive count")
    if ("MA17_OVERRIDE_MOVC_7B45" in os.environ or
            "MA17_OVERRIDE_MOVC_7580" in os.environ or
            "MA17_OVERRIDE_MOVC_7581_DELTA" in os.environ or
            "MA17_OVERRIDE_MOVC_7100_DELTA" in os.environ or
            "MA17_OVERRIDE_MOVC_AT" in os.environ or
            "MA17_OVERRIDE_MOVC_MATRIX_ROM" in os.environ or
            "MA17_OVERRIDE_MOVC_MATRIX_BASE" in os.environ) and not args.trace_movc:
        parser.error("MOVC override requires --trace-movc")
    firmware = args.firmware.resolve()
    reference = (ROOT / "FiatTipo_MA17_dump_27c256.bin").read_bytes()
    candidate = firmware.read_bytes()
    if len(candidate) != len(reference) or candidate[:0x7580] != reference[:0x7580]:
        parser.error("--firmware requires 32768 bytes and identical code prefix "
                     "through 0x757F; other revisions need a validated hardware profile")
    firmware_hash = hashlib.sha256(candidate).hexdigest()
    point_override = os.environ.get("MA17_OVERRIDE_MOVC_AT")
    if point_override is not None and not re.fullmatch(
            r"[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{2}"
            r"(?:,[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{2})*",
            point_override):
        parser.error("MA17_OVERRIDE_MOVC_AT must be "
                     "PC:ADDRESS:VALUE[,PC:ADDRESS:VALUE...] in hex")
    matrix_source = os.environ.get("MA17_OVERRIDE_MOVC_MATRIX_ROM")
    matrix_base = os.environ.get("MA17_OVERRIDE_MOVC_MATRIX_BASE")
    if (matrix_source is None) != (matrix_base is None):
        parser.error("matrix donor requires both ROM and BASE")
    matrix_donor_hash = None
    matrix_slot = None
    matrix_size = None
    if matrix_source is not None:
        layouts = {"743A": (0x7020, 10), "7444": (0x7022, 10),
                   "744E": (0x7018, 10), "7462": (0x701C, 10),
                   "746C": (0x702A, 10), "752A": (0x707C, 10),
                   "753E": (0x703C, 10),
                   "7581": (0x7048, 225), "7662": (0x704A, 225),
                   "7743": (0x704C, 225), "7B46": (0x709C, 120),
                   "7BBE": (0x709E, 120), "7C36": (0x70A0, 120),
                   "7CAE": (0x70B6, 120),
                   "7D26": (0x70B8, 120), "7D9E": (0x70BA, 120),
                   "7E16": (0x70CE, 120),
                   "7895": (0x7080, 20), "78BD": (0x7084, 20),
                   "7925": (0x7064, 20), "7939": (0x7066, 20),
                   "7ED9": (0x70A2, 60),
                   "7F15": (0x70A4, 60), "7F51": (0x70A6, 60)}
        matrix_base = matrix_base.upper()
        if matrix_base not in layouts:
            parser.error("matrix donor BASE must name a verified ROM table")
        matrix_slot, matrix_size = layouts[matrix_base]
        donor = Path(matrix_source).resolve().read_bytes()
        if len(donor) != len(candidate):
            parser.error("matrix donor requires a 32768-byte ROM")
        matrix_donor_hash = hashlib.sha256(donor).hexdigest()
        known_images = [ROOT / "FiatTipo_MA17_dump_27c256.bin",
                        *(ROOT / "firmwares_modificados_ma17_tipo").glob("*.bin")]
        known_hashes = {hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in known_images if path.stat().st_size == 32768}
        if matrix_donor_hash not in known_hashes:
            parser.error("matrix donor must match an inventoried original ROM")
        for image in (candidate, donor):
            if int.from_bytes(image[matrix_slot:matrix_slot + 2], "big") != int(
                    matrix_base, 16):
                parser.error("matrix donor pointer differs from selected matrix")
    if not 300 <= args.rpm <= 6000:
        parser.error("--rpm must be between 300 and 6000")
    if args.seconds <= 0 or (not args.no_kline_inject and
                             not 0 < args.inject_after < args.seconds):
        parser.error("require positive --seconds and 0 < --inject-after < --seconds")
    if args.stop_ticks is not None and (args.stop_ticks <= 0 or
                                        not args.no_kline_inject):
        parser.error("--stop-ticks requires a positive value and --no-kline-inject")
    ram57_override = os.environ.get("MA17_OVERRIDE_RAM57")
    if ram57_override is not None and not re.fullmatch(r"[012]", ram57_override):
        parser.error("MA17_OVERRIDE_RAM57 must be hexadecimal 0, 1 or 2")
    ram78_override = os.environ.get("MA17_OVERRIDE_RAM78")
    if ram78_override is not None and not re.fullmatch(
            r"[0-9A-Fa-f]{1,2}", ram78_override):
        parser.error("MA17_OVERRIDE_RAM78 must be one or two hex digits")
    r6_1c19_override = os.environ.get("MA17_OVERRIDE_R6_AT_1C19")
    if r6_1c19_override is not None and not re.fullmatch(
            r"[0-9A-Fa-f]{2}", r6_1c19_override):
        parser.error("MA17_OVERRIDE_R6_AT_1C19 must be two hex digits")
    ram4f_override = os.environ.get("MA17_OVERRIDE_RAM4F")
    if ram4f_override is not None and not re.fullmatch(
            r"[0-9A-Fa-f]{1,2}", ram4f_override):
        parser.error("MA17_OVERRIDE_RAM4F must be one or two hex digits")
    ram7f_override = os.environ.get("MA17_OVERRIDE_RAM7F_AT_1E98")
    if ram7f_override is not None and not re.fullmatch(
            r"[0-9A-Fa-f]{2}", ram7f_override):
        parser.error("MA17_OVERRIDE_RAM7F_AT_1E98 must be two hex digits")
    upper9d_override = os.environ.get("MA17_OVERRIDE_UPPER9D_AT_1E8B")
    if upper9d_override is not None and not re.fullmatch(
            r"[0-9A-Fa-f]{2}", upper9d_override):
        parser.error("MA17_OVERRIDE_UPPER9D_AT_1E8B must be two hex digits")
    ram6e_read_override = os.environ.get("MA17_OVERRIDE_RAM6E_READ")
    if ram6e_read_override is not None and not re.fullmatch(
            r"[0-9A-Fa-f]{2}", ram6e_read_override):
        parser.error("MA17_OVERRIDE_RAM6E_READ must be two hex digits")
    idle_r4_override = os.environ.get("MA17_OVERRIDE_IDLE_POSITION_R4")
    if idle_r4_override is not None and not re.fullmatch(
            r"[0-9A-Fa-f]{2}", idle_r4_override):
        parser.error("MA17_OVERRIDE_IDLE_POSITION_R4 must be two hex digits")
    p4_6_force_low = os.environ.get("MA17_P4_6_FORCE_LOW")
    if p4_6_force_low not in (None, "1"):
        parser.error("MA17_P4_6_FORCE_LOW must be 1 when set")
    p4_6_low_from_tick = os.environ.get("MA17_P4_6_LOW_FROM_TICK")
    if p4_6_low_from_tick is not None and not re.fullmatch(
            r"[0-9]+", p4_6_low_from_tick):
        parser.error("MA17_P4_6_LOW_FROM_TICK must be a nonnegative integer")
    if p4_6_force_low and p4_6_low_from_tick is not None:
        parser.error("choose one P4.6 low stimulus")
    p4_7_force_low = os.environ.get("MA17_P4_7_FORCE_LOW")
    if p4_7_force_low not in (None, "1"):
        parser.error("MA17_P4_7_FORCE_LOW must be 1 when set")
    p4_3_force_low = os.environ.get("MA17_P4_3_FORCE_LOW")
    if p4_3_force_low not in (None, "1"):
        parser.error("MA17_P4_3_FORCE_LOW must be 1 when set")
    trace_cc3_decision = os.environ.get("MA17_TRACE_CC3_DECISION")
    if trace_cc3_decision not in (None, "1"):
        parser.error("MA17_TRACE_CC3_DECISION must be 1 when set")
    if os.environ.get("MA17_ZERO_UPPER_CA_AT_39B2") not in (None, "1"):
        parser.error("MA17_ZERO_UPPER_CA_AT_39B2 must be 1 when set")
    if os.environ.get("MA17_CLEAR_RAM2C_BIT7_ONCE_AT_1840") not in (None, "1"):
        parser.error("MA17_CLEAR_RAM2C_BIT7_ONCE_AT_1840 must be 1 when set")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    log = output / "emulator-trace.log"
    command = [str(ROOT / "build" / "emu8051-tty"), str(firmware), "--8052"]
    emulator_sha256 = hashlib.sha256(Path(command[0]).read_bytes()).hexdigest()
    environment = os.environ.copy()
    environment["MA17_TRACE_PC"] = "1"
    environment["MA17_CRANK_RPM"] = str(args.rpm)
    environment.pop("MA17_TRACE_MOVC", None)
    environment.pop("MA17_MOVC_BUCKET_TICKS", None)
    environment.pop("MA17_TRACE_LOOKUP", None)
    environment.pop("MA17_STOP_TICKS", None)
    if args.trace_movc:
        environment["MA17_TRACE_MOVC"] = "1"
    if args.movc_bucket_ticks is not None:
        environment["MA17_MOVC_BUCKET_TICKS"] = str(args.movc_bucket_ticks)
    if args.trace_lookup:
        environment["MA17_TRACE_LOOKUP"] = "1"
    if args.stop_ticks is not None:
        environment["MA17_STOP_TICKS"] = str(args.stop_ticks)
    adc_10bit_input_values = [value * 4 for value in
                              (120, 130, 100, 80, 90, 110, 95, 105)]
    adc_10bit_step_values = [None] * 8
    adc_10bit_step_sequences = [[] for _ in range(8)]
    for channel in range(8):
        key = f"MA17_ADC_CH{channel}"
        if key in environment:
            setting = environment[key]
            if not re.fullmatch(r"[0-9]+", setting) or not 4 <= int(setting) <= 247:
                parser.error(f"{key} must be a decimal value from 4 to 247")
            adc_10bit_input_values[channel] = int(setting) * 4
        key = f"MA17_ADC10_CH{channel}"
        if key in environment:
            setting = environment[key]
            if not re.fullmatch(r"[0-9]+", setting) or not 0 <= int(setting) <= 1023:
                parser.error(f"{key} must be a decimal value from 0 to 1023")
            adc_10bit_input_values[channel] = int(setting)
        key = f"MA17_ADC10_STEP_CH{channel}"
        if key in environment:
            items = environment[key].split(",")
            if len(items) > 8:
                parser.error(f"{key} supports at most 8 steps")
            previous_tick = 0
            for item in items:
                match = re.fullmatch(r"([0-9]+):([0-9]+)", item)
                if not match or not previous_tick < int(match[1]) <= \
                        (1 << 64) - 1 or not 0 <= int(match[2]) <= 1023:
                    parser.error(f"{key} must contain ascending tick:value "
                                 "steps with 10-bit values")
                step = {"tick": int(match[1]), "value": int(match[2])}
                adc_10bit_step_sequences[channel].append(step)
                previous_tick = step["tick"]
            adc_10bit_step_values[channel] = adc_10bit_step_sequences[channel][0]
    adc_input_values = [value >> 2 for value in adc_10bit_input_values]
    adc7_input_value = adc_input_values[7]
    if args.crank_immediate:
        environment["MA17_CRANK_IMMEDIATE"] = "1"
    with log.open("w") as stream:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stream,
                                   stderr=subprocess.STDOUT, env=environment)
        try:
            if args.stop_ticks is not None:
                process.wait(timeout=args.seconds)
            elif args.no_kline_inject:
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
    adaptation_xram_changes = collections.defaultdict(list)
    lambda_bound_xram_changes = collections.defaultdict(list)
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
    movc_reads = []
    movc_buckets = []
    indirect_iram_reads = []
    lookup_rows = []
    injection_flow_events = []
    air_gate_pcs = collections.Counter()
    air_gate_counts = collections.Counter()
    ram69_producer_samples = []
    ram69_path_log_events = 0
    observed_stop_ticks = None
    for number, line in enumerate(log.read_text(errors="replace").splitlines(), 1):
        if line.startswith("[RAM69-PATH]"):
            ram69_path_log_events += 1
            try:
                producer = parse_ram69_producer(line)
            except ValueError as error:
                raise RuntimeError(f"invalid RAM69 trace at log line {number}") from error
            if producer is not None:
                ram69_producer_samples.append(producer)
        stopped = TRACE_STOP.fullmatch(line)
        if stopped:
            observed_stop_ticks = int(stopped.group(1))
        if line.startswith("[AIR-716C-GATE]"):
            try:
                fields = dict(part.split("=", 1) for part in line.split()[1:])
                pc = fields["PC"]
                psw = int(fields["PSW"], 16)
                flags2e = int(fields["F2E"], 16)
                ram6f = int(fields["RAM6F"], 16)
                r2 = int(fields["R2"], 16)
            except (KeyError, ValueError) as error:
                raise RuntimeError(f"invalid air gate at log line {number}") from error
            air_gate_pcs[pc] += 1
            if pc == "3CB7":
                air_gate_counts["2e6_set_at_3cb7"] += bool(flags2e & 0x40)
                air_gate_counts["r2_below_6f_at_3cb7"] += r2 < ram6f
            elif pc == "3D0C":
                air_gate_counts["carry_set_at_3d0c"] += bool(psw & 0x80)
        if line.startswith("[INJECTION-FLOW]"):
            match = INJECTION_FLOW.fullmatch(line)
            if not match:
                raise RuntimeError(f"invalid injection flow at log line {number}")
            tick, pc, r2, r3, ram63, ram78, ram48, dptr, psw, flags25, flags2e = match.groups()
            injection_flow_events.append({"tick": int(tick), "pc": pc,
                                          "r2r3": r2 + r3, "ram63": ram63,
                                          "ram78": ram78, "ram48": ram48,
                                          "dptr": dptr, "psw": psw,
                                          "flags25": flags25, "flags2e": flags2e})
        if line.startswith("[LOOKUP-SUMMARY]"):
            match = LOOKUP.fullmatch(line)
            if not match:
                raise RuntimeError(f"invalid lookup summary at log line {number}")
            fields = ("rpm", "load", "selector", "flags", "r0", "r4", "r5",
                      "r6", "result_a", "result_b")
            lookup_rows.append({**dict(zip(fields, match.groups()[:-1])),
                                "count": int(match.group(11))})
        if line.startswith("[MOVC-SUMMARY]"):
            match = MOVC.fullmatch(line)
            if not match:
                raise RuntimeError(f"invalid MOVC summary at log line {number}")
            pc, opcode, dptr, acc, address, mapped, value, count = match.groups()
            if int(mapped, 16) >= len(candidate) or candidate[int(mapped, 16)] != int(value, 16):
                raise RuntimeError(f"MOVC read differs from ROM at log line {number}")
            movc_reads.append({"pc": pc, "opcode": opcode, "dptr": dptr,
                               "acc": acc, "address": address, "mapped": mapped,
                               "value": value, "count": int(count)})
        if line.startswith("[MOVC-BUCKET]"):
            match = MOVC_BUCKET.fullmatch(line)
            if not match:
                raise RuntimeError(f"invalid MOVC bucket at log line {number}")
            start, address, count = match.groups()
            if int(address, 16) >= len(candidate):
                raise RuntimeError(f"MOVC bucket outside ROM at log line {number}")
            movc_buckets.append({"start_tick": int(start), "address": address,
                                 "count": int(count)})
        if line.startswith("[INDIRECT-IRAM-READ]"):
            match = INDIRECT_IRAM.fullmatch(line)
            if not match:
                raise RuntimeError(f"invalid indirect IRAM summary at log line {number}")
            pc, opcode, address, value, count, first_tick = match.groups()
            indirect_iram_reads.append({"pc": pc, "opcode": opcode,
                                        "address": address, "value": value,
                                        "count": int(count),
                                        "first_tick": int(first_tick)})
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
        adapt_xram = ADAPT_XRAM.match(line)
        if adapt_xram:
            tick, address, before, after, source_pc = adapt_xram.groups()
            adaptation_xram_changes[address].append({
                "tick": int(tick), "before": before, "after": after,
                "source_pc": source_pc})
        if line.startswith("[LAMBDA-BOUND-XRAM]"):
            match = LAMBDA_BOUND_XRAM.fullmatch(line)
            if not match:
                raise RuntimeError(f"invalid lambda bound XRAM at log line {number}")
            tick, address, before, after, source_pc = match.groups()
            lambda_bound_xram_changes[address].append({
                "tick": int(tick), "before": before, "after": after,
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
    if args.trace_movc and not movc_reads:
        raise RuntimeError("MOVC tracing was enabled but no reads were recorded")
    if args.movc_bucket_ticks is not None and (
            not movc_buckets or
            sum(row["count"] for row in movc_buckets) !=
            sum(row["count"] for row in movc_reads)):
        raise RuntimeError("MOVC bucket totals disagree with detailed reads")
    output_latches = {}
    for channel in (0, 1):
        periods = [b - a for a, b in zip(p5_starts[channel], p5_starts[channel][1:])]
        output_latches[f"P5.{channel}"] = {
            "low_starts": len(p5_starts[channel]),
            "median_period_ticks": statistics.median(periods) if periods else None,
            "median_low_width_ticks": (statistics.median(p5_widths[channel])
                                       if p5_widths[channel] else None),
            "low_width_histogram": [
                {"width_ticks": width, "count": count}
                for width, count in sorted(collections.Counter(
                    p5_widths[channel]).items())]}
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
        if inventory["rom_sha256"] != hashlib.sha256(reference).hexdigest():
            raise RuntimeError("inventory hash does not match firmware")
        observed_functions = [
            {"address": item["address"], "ida_name": item["name"],
             "semantic_alias": item.get("semantic_alias")}
            for item in inventory["functions"] if int(item["address"], 16) in pc_hits]
    if args.stop_ticks is not None and observed_stop_ticks != args.stop_ticks:
        raise RuntimeError(f"emulator stopped at {observed_stop_ticks} ticks; "
                           f"expected {args.stop_ticks}")
    report = {"firmware_origin": ("Fiat Tipo Bosch Monomotronic MA1.7" if
                                  candidate == reference else
                                  "experimental Fiat code-prefix variant"),
              "firmware_path": str(firmware),
              "firmware_sha256": firmware_hash,
              "emulator_sha256": emulator_sha256,
              "hardware_profile": "Fiat Tipo 11.88 MHz; P4 K-line; P1.0 crank",
              "oscillator_hz": 11880000,
              "machine_cycles_per_second": 990000,
              "p4_6_force_low_experimental": p4_6_force_low == "1",
              "p4_6_low_from_tick_experimental": (
                  None if p4_6_low_from_tick is None else int(p4_6_low_from_tick)),
              "p4_7_force_low_experimental": p4_7_force_low == "1",
              "p4_3_force_low_experimental": p4_3_force_low == "1",
              "upper_ca_zero_at_39b2_experimental":
                  environment.get("MA17_ZERO_UPPER_CA_AT_39B2") == "1",
              "ram2c_bit7_clear_once_at_1840_experimental":
                  environment.get("MA17_CLEAR_RAM2C_BIT7_ONCE_AT_1840") == "1",
              "ram5b_write_trace_after_tick":
                  environment.get("MA17_TRACE_RAM5B_WRITE_AFTER_TICK"),
              "emulator_exit": process.returncode,
              "duration_seconds": None if args.stop_ticks is not None else args.seconds,
              "wall_timeout_seconds": args.seconds if args.stop_ticks is not None else None,
              "stop_ticks_target": args.stop_ticks,
              "stop_ticks_observed": observed_stop_ticks,
              "crank_target_rpm": args.rpm,
              "timebase": "emulated machine-cycle ticks",
              "rpm_selector_override_hex": environment.get(
                  "MA17_OVERRIDE_RPM_SELECTOR"),
              "ram69_override_hex": environment.get("MA17_OVERRIDE_RAM69"),
              "ram31_override_hex": environment.get("MA17_OVERRIDE_RAM31"),
              "ram57_override_hex": ram57_override,
              "ram78_override_hex": ram78_override.upper()
              if ram78_override is not None else None,
              "r6_1c19_override_hex": r6_1c19_override.upper()
              if r6_1c19_override is not None else None,
              "ram4f_override_hex": ram4f_override.upper()
              if ram4f_override is not None else None,
              "ram7f_override_at_1e98_hex": ram7f_override.upper()
              if ram7f_override is not None else None,
              "upper9d_override_at_1e8b_hex": upper9d_override.upper()
              if upper9d_override is not None else None,
              "idle_position_r4_override_hex": idle_r4_override.upper()
              if idle_r4_override is not None else None,
              "movc_7b45_override_hex": environment.get("MA17_OVERRIDE_MOVC_7B45"),
              "movc_7580_override_hex": environment.get("MA17_OVERRIDE_MOVC_7580"),
              "movc_7581_delta_hex": environment.get("MA17_OVERRIDE_MOVC_7581_DELTA"),
              "movc_7100_delta_hex": environment.get("MA17_OVERRIDE_MOVC_7100_DELTA"),
              "movc_override_at_hex": point_override.upper()
              if point_override is not None else None,
              "movc_matrix_base_hex": matrix_base,
              "movc_matrix_pointer_slot_hex": (f"{matrix_slot:04X}"
                                               if matrix_slot is not None else None),
              "movc_matrix_size": matrix_size,
              "movc_matrix_donor_sha256": matrix_donor_hash,
              "matrix_path_trace_enabled": "MA17_TRACE_MATRIX_PATH" in environment,
              "xram_f80c_override_hex": environment.get("MA17_OVERRIDE_XRAM_F80C"),
              "xram_read_override_at_hex": environment.get(
                  "MA17_OVERRIDE_XRAM_READ_AT"),
              "xram_f80c_trace_enabled": "MA17_TRACE_XRAM_F80C" in environment,
              "xram_f891_trace_enabled": "MA17_TRACE_XRAM_F891" in environment,
              "xram_f802_trace_enabled": "MA17_TRACE_XRAM_F802" in environment,
              "xram_f8a2_trace_enabled": "MA17_TRACE_XRAM_F8A2" in environment,
              "xram_f88e_trace_enabled": "MA17_TRACE_XRAM_F88E" in environment,
              "xram_f8f2_trace_enabled": "MA17_TRACE_XRAM_F8F2" in environment,
              "xram_trace_address_hex": environment.get("MA17_TRACE_XRAM_ADDRESS"),
              "xram_trace_pc_hex": environment.get("MA17_TRACE_XRAM_PC"),
              "xram_f87f_trace_enabled": "MA17_TRACE_XRAM_F87F" in environment,
              "iram_read_override_at_hex": environment.get(
                  "MA17_OVERRIDE_IRAM_READ_AT"),
              "iram_read_override_after_tick": environment.get(
                  "MA17_OVERRIDE_IRAM_READ_AFTER_TICK"),
              "ram46_table_trace_enabled": "MA17_TRACE_RAM46_TABLE" in environment,
              "upper_85_86_trace_enabled": "MA17_TRACE_UPPER_85_86" in environment,
              "boot_xram_fields_trace_enabled":
                  "MA17_TRACE_BOOT_XRAM_FIELDS" in environment,
              "xram_f891_47a2_override_hex": environment.get(
                  "MA17_OVERRIDE_XRAM_F891_47A2"),
              "xram_f891_564a_override_hex": environment.get(
                  "MA17_OVERRIDE_XRAM_F891_564A"),
              "xram_f891_564a_return_filter_hex": environment.get(
                  "MA17_OVERRIDE_XRAM_F891_564A_RETURN"),
              "path_129d_trace_enabled": "MA17_TRACE_129D_PATH" in environment,
              "lambda_bound_trace_enabled": "MA17_TRACE_LAMBDA_BOUNDS" in environment,
              "coolant_gate_trace_enabled": "MA17_TRACE_COOLANT_GATE" in environment,
              "post_coolant_axis_trace_enabled":
              "MA17_TRACE_POST_COOLANT_AXIS" in environment,
              "curve_799e_boundary_trace_enabled":
              "MA17_TRACE_799E_BOUNDARY" in environment,
              "ram78_gate_trace_enabled": "MA17_TRACE_RAM78_GATE" in environment,
              "terminal_segment_trace_enabled":
              "MA17_TRACE_TERMINAL_SEGMENT" in environment,
              "ram31_gate_trace_enabled": "MA17_TRACE_RAM31_GATE" in environment,
              "ram5b_gate_trace_enabled": "MA17_TRACE_RAM5B_GATE" in environment,
              "matrix_7939_index_trace_enabled": "MA17_TRACE_7939_INDEX" in environment,
              "ram5b_read_override_hex": environment.get("MA17_OVERRIDE_RAM5B_READ"),
              "ram6e_read_override_hex": ram6e_read_override,
              "tps_trace_after_tick": environment.get("MA17_TRACE_TPS_AFTER_TICK"),
              "trace_78xx_after_tick": environment.get(
                  "MA17_TRACE_78XX_AFTER_TICK"),
              "pc_trace_window": environment.get("MA17_TRACE_PC_WINDOW"),
              "ram4d_path_trace_enabled": "MA17_TRACE_RAM4D_PATH" in environment,
              "cc3_trace_after_tick": environment.get("MA17_TRACE_CC3_AFTER_TICK"),
              "cc3_decision_trace_enabled": trace_cc3_decision == "1",
              "cutoff_path_trace_enabled": "MA17_TRACE_CUTOFF_PATH" in environment,
              "adc_10bit_input_values": adc_10bit_input_values,
              "adc_10bit_step_values": adc_10bit_step_values,
              "adc_10bit_step_sequences": adc_10bit_step_sequences,
              "adc_input_values": adc_input_values,
              "adc7_input_value": adc7_input_value,
              "injection_signal_sent": not args.no_kline_inject,
              "crank_immediate": args.crank_immediate,
              "movc_observation": {
                  "enabled": args.trace_movc,
                  "distinct_read_states": len(movc_reads),
                  "total_reads": sum(row["count"] for row in movc_reads),
                  "reads": movc_reads,
                  "bucket_ticks": args.movc_bucket_ticks,
                  "buckets": movc_buckets},
              "indirect_iram_observation": {
                  "target_address": environment.get(
                      "MA17_TRACE_INDIRECT_IRAM_ADDRESS"),
                  "total_reads": sum(row["count"] for row in indirect_iram_reads),
                  "reads": indirect_iram_reads},
              "lookup_observation": {
                  "enabled": args.trace_lookup,
                  "total_calls": sum(row["count"] for row in lookup_rows),
                  "states": lookup_rows},
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
              "injection_flow_observation": summarize_injection_flow(
                  injection_flow_events),
              "air_gate_observation": {
                  "enabled": "MA17_TRACE_AIR_716C_GATE" in environment,
                  "observed_events": sum(air_gate_pcs.values()),
                  "sample_limit": 3000,
                  "sample_limit_reached": sum(air_gate_pcs.values()) >= 3000,
                  "pc_counts": dict(air_gate_pcs),
                  **{key: air_gate_counts[key] for key in
                     ("2e6_set_at_3cb7", "r2_below_6f_at_3cb7",
                      "carry_set_at_3d0c")}},
              "ram69_producer_observation": {
                  "enabled": "MA17_TRACE_RAM69" in environment,
                  "samples_at_3b06": len(ram69_producer_samples),
                  "path_log_events": ram69_path_log_events,
                  "sample_limit_reached": ram69_path_log_events >= 2000,
                  "flag_bit4_set_samples": sum(
                      bool(int(row["flags2B"], 16) & 0x10)
                      for row in ram69_producer_samples),
                  "flag_values": sorted({row["flags2B"] for row in
                                         ram69_producer_samples}),
                  "output_values": sorted({row["RAM69"] for row in
                                           ram69_producer_samples}),
                  "rpm_bytes": sorted({row["RAM47"] for row in
                                       ram69_producer_samples})},
              "fault_xram_observation": dict(fault_xram_changes),
              "adaptation_xram_observation": dict(adaptation_xram_changes),
              "lambda_bound_xram_observation": dict(lambda_bound_xram_changes),
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
                       "injection_flow_observation",
                       "cc3_observation", "kline_page_observation",
                       "pc_hits_file", "firmware_sha256",
                       "log_file")}, indent=2))


if __name__ == "__main__":
    main()
