"""Verify the candidate warm bench starts, burns and captures its final frame."""

from pathlib import Path
import re
import struct
import subprocess
import sys


binary, rom, xvfb, output_dir = sys.argv[1:]
output_dir = Path(output_dir)
svg = output_dir / "sevel-bench-preset.svg"
png = output_dir / "sevel-bench-preset.png"
trace = output_dir / "sevel-bench-preset-controls.txt"
replay_svg = output_dir / "sevel-bench-preset-replay.svg"
tick = "3000000"


def run(argv):
    result = subprocess.run(argv, text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout[-2500:] + result.stderr[-2500:]
    assert "[LAB-BENCH] candidate warm bindings enabled" in result.stdout
    return result.stdout


headless = run([binary, rom, "--headless", "--verbose", "--bench-preset",
                "--capture-tick", tick, "--capture-svg", str(svg)])
assert "<path " in svg.read_text() and "<polygon" not in svg.read_text()
pulses = [int(value) for value in re.findall(r"cc3_pulses=(\d+)", headless)]
burns = [int(value) for value in re.findall(r'"burns":(\d+)', headless)]
assert pulses and pulses[-1] > 0 and burns and burns[-1] > 0
capture = re.search(r"\[LAB-CAPTURE\] tick=3000000 rpm=([\d.]+)", headless)
assert capture, headless[-2500:]

live = run([xvfb, "-a", binary, rom, "--live", "--bench-preset",
            "--auto-start", "--no-audio", "--stop-ticks", tick,
            "--capture-tick", tick, "--window-frames", "400",
            "--screenshot", str(png), "--save-controls", str(trace)])
image = png.read_bytes()
assert image[:8] == b"\x89PNG\r\n\x1a\n"
assert struct.unpack(">II", image[16:24]) == (1280, 720)
state = re.search(r"\[LAB-STATE\] tick=3000000 rpm=([\d.]+) .*"
                  r"cc3=(\d+) burns=(\d+) .*overflow=(\d+)", live)
assert state, live[-2500:]
assert abs(float(state[1]) - float(capture[1])) < 0.001
assert int(state[2]) == pulses[-1] and int(state[3]) > 0
assert int(state[4]) == 0
saved = trace.read_text()
assert saved.startswith("sevel-ma17-controls-v2\n")
assert 'arg "--adc7-mv"\narg "1232"' in saved
replayed = run([binary, rom, "--headless", "--bench-preset",
                "--capture-tick", tick, "--capture-svg", str(replay_svg),
                "--replay-controls", str(trace)])
replay_state = re.search(r"^\[LAB-STATE\] .+$", replayed, re.MULTILINE)
live_state = re.search(r"^\[LAB-STATE\] .+$", live, re.MULTILINE)
assert replay_state and live_state and replay_state[0] == live_state[0]
print(f"[LAB-BENCH-TEST] rpm={state[1]} cc3={state[2]} "
      f"burns={state[3]} png={png}")
