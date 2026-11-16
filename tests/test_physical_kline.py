"""Exercise the original ROM's K-Line fault replies during physical faults."""

import json
import os
from pathlib import Path
import queue
import re
import signal
import subprocess
import sys
import threading


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
              additional_triplets=()):
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    proc = subprocess.Popen(
        base + fault_options, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        bufsize=1)
    pty = queue.Queue()
    ready = threading.Event()
    samples = []

    def stdout_reader():
        for line in proc.stdout:
            if "PTY pronto em:" in line:
                match = re.search(r"/dev/pts/\d+", line)
                if match:
                    pty.put(match.group())
            if line.startswith('{"type":"diagnostic"'):
                sample = json.loads(line)
                samples.append(sample)
                if sample["tick"] >= query_tick:
                    ready.set()

    def stderr_reader():
        for _ in proc.stderr:
            pass

    threads = [threading.Thread(target=stdout_reader, daemon=True),
               threading.Thread(target=stderr_reader, daemon=True)]
    for thread in threads:
        thread.start()
    try:
        path = pty.get(timeout=6)
        assert ready.wait(timeout=18), "physical diagnostic sample timed out"
        result = subprocess.run(
            [sys.executable, str(client), path, "--faults-once",
             "--expect-fault-triplet=" + triplet], env=env,
            capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-500:]
        for expected in (triplet, *additional_triplets):
            assert "[ECU-ERROR] Pacote de erro: " + " ".join(
                expected[index:index + 2] for index in range(0, 6, 2)) in result.stdout
        assert any(sample["tick"] >= query_tick and sample[bank] & mask
                   for sample in samples), samples[-3:]
        print(f"K-Line FC={triplet}, {bank} mask={mask}, PTY handshake and 07h passed")
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
