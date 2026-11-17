"""Query the original ROM over the Lab's live PTY while its window runs."""

from collections import deque
import json
import os
from pathlib import Path
import queue
import re
import signal
import subprocess
import sys
import threading
import time


xvfb, binary, rom = sys.argv[1:4]
client = Path(__file__).resolve().parents[1] / "test_pty.py"
command = [
    xvfb, "-a", binary, rom, "--live", "--auto-start", "--bench-preset",
    "--no-audio", "--physical-pty-realtime", "--ect-open-tick", "2000000",
    "--ect-restore-tick", "15000000", "--load-step-tick", "800000",
    "--load-nm", "24", "--stop-ticks", "25000000", "--window-frames", "1800",
]
environment = os.environ.copy()
environment["SDL_AUDIODRIVER"] = "dummy"
process = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, bufsize=1,
                           start_new_session=True)
pty = queue.Queue()
emulator_pid = queue.Queue()
diagnostic_ready = threading.Event()
clock_samples = []
lines = deque(maxlen=100)
kline_events = deque(maxlen=40)


def read_output():
    for line in process.stdout:
        lines.append(line)
        if any(tag in line for tag in ("5-BAUD", "PTY-TX", "P4.5")):
            kline_events.append(line)
        if "PTY pronto em:" in line:
            match = re.search(r"/dev/pts/\d+", line)
            if match:
                pty.put(match.group())
        if "Send SIGUSR1 to inject 5-baud init:" in line:
            match = re.search(r"kill -USR1 (\d+)", line)
            if match:
                emulator_pid.put(int(match.group(1)))
        if line.startswith('{"type":"diagnostic"'):
            sample = json.loads(line)
            clock_samples.append((sample["tick"], time.monotonic()))
            if sample["tick"] >= 2970000 and sample["f84f"] & 8:
                diagnostic_ready.set()


reader = threading.Thread(target=read_output, daemon=True)
reader.start()
try:
    path = pty.get(timeout=6)
    assert diagnostic_ready.wait(timeout=18), "ECT bank was not published"
    assert len(clock_samples) >= 2, "no CPU clock samples"
    tick_delta = clock_samples[-1][0] - clock_samples[0][0]
    time_delta = clock_samples[-1][1] - clock_samples[0][1]
    assert tick_delta > 0 and time_delta > 0, clock_samples
    measured_rate = round(tick_delta / time_delta)
    os.kill(emulator_pid.get(timeout=6), signal.SIGUSR1)
    result = subprocess.run(
        [sys.executable, str(client), path, "--faults-once",
         "--expect-fault-triplet=020A1E", "--skip-5baud",
         f"--cpu-ticks-per-second={measured_rate}"], env=environment,
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, (result.stdout[-2000:] + result.stderr[-500:] +
                                    "\nK-Line events:\n" +
                                    "".join(kline_events)[-4000:])
    assert "[ECU-ERROR] Pacote de erro: 02 0A 1E" in result.stdout
    print(f"[LAB-KLINE] pty={path} cpu={measured_rate} ticks/s "
          "published_f84f=08 query=02 0A 1E")
except Exception:
    print("".join(lines)[-3000:], file=sys.stderr)
    raise
finally:
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    reader.join(timeout=1)
