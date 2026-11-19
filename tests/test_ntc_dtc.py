"""Exercise the original ROM's K-Line fault replies during physical faults."""

import json
import os
from collections import deque
from pathlib import Path
import queue
import re
import signal
import subprocess
import sys
import threading
import time
from sevel_preset import BENCH_LEAK_MM2


binary, firmware = sys.argv[1:3]
client = Path(__file__).resolve().parent.parent / "test_pty.py"
base = [binary, firmware, "--physical-crank", "--physical-pty-realtime",
        "--starter-ticks", "495000", "--stop-ticks", "25000000",
        "--adc7-mv", "1232", "--idle-bridge-p15-p16",
        "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", str(BENCH_LEAK_MM2),
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5"]


def run_fault(fault_options, query_tick, triplet, bank, mask=8,
              additional_triplets=(), starter_ticks=None):
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    command = base.copy()
    if starter_ticks is not None:
        command[command.index("--starter-ticks") + 1] = str(starter_ticks)
    proc = subprocess.Popen(
        command + fault_options, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        bufsize=1)
    pty = queue.Queue()
    ready = threading.Event()
    samples = []
    clock_samples = []
    emulator_log = deque(maxlen=200)

    def stdout_reader():
        for line in proc.stdout:
            if "PTY pronto em:" in line:
                match = re.search(r"/dev/pts/\d+", line)
                if match:
                    pty.put(match.group())
            if line.startswith('{"type":"diagnostic"'):
                sample = json.loads(line)
                samples.append(sample)
                clock_samples.append((sample["tick"], time.monotonic()))
                if sample["tick"] >= query_tick:
                    ready.set()

    def stderr_reader():
        for line in proc.stderr:
            if any(tag in line for tag in ("K-LINE", "P4.5", "PTY-TX", "DECODER")):
                emulator_log.append(line)

    threads = [threading.Thread(target=stdout_reader, daemon=True),
               threading.Thread(target=stderr_reader, daemon=True)]
    for thread in threads:
        thread.start()
    try:
        path = pty.get(timeout=6)
        assert ready.wait(timeout=18), "physical diagnostic sample timed out"
        assert len(clock_samples) >= 2, "no CPU clock samples"
        tick_delta = clock_samples[-1][0] - clock_samples[0][0]
        time_delta = clock_samples[-1][1] - clock_samples[0][1]
        assert tick_delta > 0 and time_delta > 0, clock_samples
        measured_rate = round(tick_delta / time_delta)
        proc.send_signal(signal.SIGUSR1)
        result = subprocess.run(
            [sys.executable, str(client), path, "--faults-once",
             "--expect-fault-triplet=" + triplet,
             f"--cpu-ticks-per-second={measured_rate}",
             "--skip-5baud"], env=env,
            capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, (result.stdout[-2000:] +
                                        result.stderr[-500:] +
                                        "\nEmulator log:\n" +
                                        "".join(emulator_log)[-6000:])
        for expected in (triplet, *additional_triplets):
            assert "[ECU-ERROR] Pacote de erro: " + " ".join(
                expected[index:index + 2] for index in range(0, 6, 2)) in result.stdout
        assert any(sample["tick"] >= query_tick and sample[bank] & mask
                   for sample in samples), samples[-3:]
        print(f"K-Line FC={triplet}, {bank} mask={mask}, "
              f"CPU={measured_rate} ticks/s, PTY handshake and 07h passed")
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        for thread in threads:
            thread.join(timeout=1)


# Sensor identity check (CURVES_STUDY): the ROM's own K-line DTC for each NTC input fault.
# ADC3/IRAM 63h = coolant -> 0A02 ; ADC2/IRAM 62h = air -> 0B02 (status 1E = open, 1D = short to GND).
run_fault(["--ect-open-tick", "2000000", "--ect-restore-tick", "15000000"],
          2970000, "020A1E", "f84f")
run_fault(["--exp", "ntc_force_tick=2000000", "--exp", "ect_force_v=0.0"],
          2970000, "020A1D", "f84f", 0x10)
run_fault(["--exp", "air_open_tick=2000000"], 2970000, "020B1E", "f84f", 0x40)
run_fault(["--exp", "ntc_force_tick=2000000", "--exp", "air_force_v=0.0"],
          2970000, "020B1D", "f84f", 0x80)
