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


binary, firmware = sys.argv[1:3]
client = Path(__file__).resolve().parent.parent / "test_pty.py"
base = [binary, firmware, "--physical-crank", "--physical-pty-realtime",
        "--starter-ticks", "495000", "--stop-ticks", "25000000",
        "--adc7-mv", "1232", "--idle-bridge-p15-p16",
        "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
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


# Circuit and ADC7 bindings remain conditional; replies come from the ROM.
run_fault(["--ect-open-tick", "2000000", "--ect-restore-tick", "15000000"],
          2970000, "020A1E", "f84f", starter_ticks=20000000)
run_fault(["--ect-open-tick", "2000000", "--ect-restore-tick", "15000000"],
          2970000, "020A1E", "f84f")
run_fault(["--ect-open-tick", "2000000", "--ect-restore-tick", "8000000"],
          9900000, "020A9E", "f85f")
run_fault(["--tps1-high-tick", "10000000", "--tps1-restore-tick", "20000000"],
          10890000, "011A1B", "f84e")
run_fault(["--tps1-high-tick", "2000000", "--tps1-restore-tick", "8000000"],
          9900000, "011A9B", "f85e")
# TPS2 ADC0 returns to its physical voltage, but this ROM still publishes
# the present 0602h status in the same boot.
run_fault(["--tps2-high-tick", "2000000", "--tps2-restore-tick", "8000000"],
          9900000, "02061E", "f84f", 4)
run_fault(["--pedal-step-tick", "10000000", "--pedal-release-tick", "20000000",
           "--pedal-mm", "8"], 11880000, "02041E", "f84e", 2,
          ("011A1B",))
run_fault(["--pedal-step-tick", "10000000", "--pedal-release-tick", "12000000",
           "--pedal-mm", "8"], 12870000, "02049E", "f85e", 2,
          ("011A9B",))
