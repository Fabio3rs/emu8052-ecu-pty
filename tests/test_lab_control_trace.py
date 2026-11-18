#!/usr/bin/env python3
"""Exercise a saved MA1.7 control trace without SDL."""

import array
import pathlib
import subprocess
import sys
import wave


binary, rom, trace, output_dir = sys.argv[1:]
output_dir = pathlib.Path(output_dir)
svg = output_dir / "sevel-control-replay.svg"
wav = output_dir / "sevel-control-replay.wav"
saved = output_dir / "sevel-control-replay-controls.txt"
result = subprocess.run(
    [
        binary,
        rom,
        "--headless",
        "--capture-tick",
        "1200000",
        "--replay-controls",
        trace,
        "--save-controls",
        str(saved),
        "--capture-svg",
        str(svg),
        "--capture-wav",
        str(wav),
        "--idle-contact-p46",
        "--idle-bridge-p15-p16",
        "--adc7-mv",
        "1232",
    ],
    capture_output=True,
    text=True,
    timeout=30,
)
assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
assert "[LAB-REPLAY] tick=1200000 controls=7 events=" in result.stdout
assert saved.read_bytes() == pathlib.Path(trace).read_bytes()
assert "<path " in svg.read_text() and "<polygon" not in svg.read_text()
with wave.open(str(wav), "rb") as audio:
    assert audio.getframerate() == 44100
    assert audio.getnchannels() == 1 and audio.getsampwidth() == 2
    samples = array.array("h", audio.readframes(audio.getnframes()))
assert len(samples) > 50000
assert any(samples)
assert all(sample not in (-32768, 32767) for sample in samples)
rom_bytes = pathlib.Path(rom).read_bytes()
rom_hash = 14695981039346656037
for byte in rom_bytes:
    rom_hash = ((rom_hash ^ byte) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
scenario_args = ["--idle-contact-p46", "--idle-bridge-p15-p16",
                 "--adc7-mv", "1232", "--starter-ticks", "495000"]
trace_v2 = output_dir / "sevel-control-replay-v2.txt"
trace_v2.write_text(
    "sevel-ma17-controls-v2\n"
    f"rom {len(rom_bytes)} {rom_hash:x}\n"
    f"args {len(scenario_args)}\n"
    + "".join(f'arg "{arg}"\n' for arg in scenario_args)
    + "controls\n" + "\n".join(pathlib.Path(trace).read_text().splitlines()[1:])
    + "\n"
)
replay_v2 = [binary, rom, "--headless", "--capture-tick", "1200000",
             "--replay-controls", str(trace_v2), "--capture-svg", str(svg),
             *scenario_args]
matched = subprocess.run(replay_v2, capture_output=True, text=True,
                         timeout=30)
assert matched.returncode == 0, matched.stdout[-2000:] + matched.stderr[-2000:]
wrong_scenario = replay_v2.copy()
wrong_scenario[-3] = "1233"
rejected = subprocess.run(wrong_scenario, capture_output=True, text=True,
                          timeout=5)
assert rejected.returncode == 2
assert "physical scenario differs" in rejected.stderr
changed_rom = bytearray(rom_bytes)
changed_rom[0] ^= 1
wrong_rom = output_dir / "sevel-control-replay-wrong-rom.bin"
wrong_rom.write_bytes(changed_rom)
wrong_rom_args = replay_v2.copy()
wrong_rom_args[1] = str(wrong_rom)
rejected_rom = subprocess.run(wrong_rom_args, capture_output=True, text=True,
                              timeout=5)
assert rejected_rom.returncode == 2
assert "ROM or physical scenario differs" in rejected_rom.stderr
invalid_stop = subprocess.run(
    [binary, rom, "--headless", "--capture-tick", "1200000",
     "--replay-controls", trace, "--capture-svg", str(svg),
     "--stop-ticks", "1200001"],
    capture_output=True,
    text=True,
    timeout=5,
)
assert invalid_stop.returncode == 2
assert "stop tick must equal capture tick" in invalid_stop.stderr
print(f"[LAB-TRACE] controls=7 samples={len(samples)} nonzero=yes clipped=0")
