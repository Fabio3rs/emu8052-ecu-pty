"""Start the original-ROM warm bench with the visible key and starter buttons."""

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


binary, rom, output_dir = sys.argv[1:]
trace = Path(output_dir) / "sevel-manual-bench-controls.txt"
svg = Path(output_dir) / "sevel-manual-bench-replay.svg"
trace.unlink(missing_ok=True)
command = [binary, rom, "--live", "--bench-preset", "--no-audio",
           "--stop-ticks", "4000000", "--window-frames", "1000",
           "--save-controls", str(trace)]


def xdotool(*args):
    return subprocess.run(["xdotool", *args], check=True, text=True,
                          capture_output=True).stdout.strip()


with tempfile.TemporaryFile(mode="w+") as log:
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    try:
        window = ""
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline and process.poll() is None:
            found = subprocess.run(["xdotool", "search", "--name",
                                    "SEVEL MA1.7"], text=True,
                                   capture_output=True)
            if found.returncode == 0 and found.stdout.strip():
                window = found.stdout.splitlines()[-1]
                break
            time.sleep(0.05)
        assert window, "Lab window did not appear"

        def current_tick():
            title = xdotool("getwindowname", window)
            match = re.search(r"tick (\d+)", title)
            assert match, title
            return int(match[1])

        xdotool("mousemove", "--window", window, "65", "522")
        xdotool("click", "1")  # key on
        start_tick = current_tick()
        xdotool("mousemove", "--window", window, "170", "522")
        xdotool("mousedown", "1")
        deadline = time.monotonic() + 12.0
        while current_tick() < start_tick + 650000:
            assert time.monotonic() < deadline and process.poll() is None
            time.sleep(0.05)
        xdotool("mouseup", "1")
        assert process.wait(timeout=30) == 0
        log.seek(0)
        live = log.read()
        live_state = re.search(r"^\[LAB-STATE\] .+$", live, re.MULTILINE)
        assert live_state and "tick=4000000 " in live_state[0]
        burns = re.search(r"burns=(\d+)", live_state[0])
        assert burns and int(burns[1]) > 0, live[-2500:]
        saved = trace.read_text()
        assert " key 1\n" in saved and " starter 1\n" in saved
        assert " starter 0\n" in saved
        replay = subprocess.run(
            [binary, rom, "--headless", "--bench-preset", "--capture-tick",
             "4000000", "--capture-svg", str(svg), "--replay-controls",
             str(trace)], text=True, capture_output=True, timeout=30)
        replay_state = re.search(r"^\[LAB-STATE\] .+$", replay.stdout,
                                 re.MULTILINE)
        assert replay.returncode == 0 and replay_state, replay.stdout[-2500:]
        assert replay_state[0] == live_state[0]
        print(f"[LAB-MANUAL-START] burns={burns[1]} replay=matched")
    except Exception:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        log.seek(0)
        print(log.read()[-2500:], file=sys.stderr)
        raise
