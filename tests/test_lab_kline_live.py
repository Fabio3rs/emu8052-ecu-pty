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
diagnostic_ready = threading.Event()
lines = deque(maxlen=100)


def read_output():
    for line in process.stdout:
        lines.append(line)
        if "PTY pronto em:" in line:
            match = re.search(r"/dev/pts/\d+", line)
            if match:
                pty.put(match.group())
        if line.startswith('{"type":"diagnostic"'):
            sample = json.loads(line)
            if sample["tick"] >= 2970000 and sample["f84f"] & 8:
                diagnostic_ready.set()


reader = threading.Thread(target=read_output, daemon=True)
reader.start()
try:
    path = pty.get(timeout=6)
    assert diagnostic_ready.wait(timeout=18), "ECT bank was not published"
    result = subprocess.run(
        [sys.executable, str(client), path, "--faults-once",
         "--expect-fault-triplet=020A1E"], env=environment,
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-500:]
    assert "[ECU-ERROR] Pacote de erro: 02 0A 1E" in result.stdout
    print(f"[LAB-KLINE] pty={path} published_f84f=08 query=02 0A 1E")
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
