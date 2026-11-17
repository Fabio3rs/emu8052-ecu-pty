"""Compare offline donor-synth WAVs driven by the original Fiat ROM."""

import array
import math
from pathlib import Path
import re
import subprocess
import sys
import wave


binary, rom, key_off_trace, output_dir = sys.argv[1:5]
output_dir = Path(output_dir)
physical_options = [
    "--adc7-mv", "1232", "--idle-bridge-p15-p16", "--idle-contact-p46",
    "--coolant-c", "90", "--idle-min-stop-mrad", "5",
    "--throttle-leak-mm2", "9", "--load-step-tick", "800000",
    "--load-nm", "24", "--lambda-adc-gain", "5",
]


def capture(name, tick, extra=()):
    path = output_dir / f"sevel-{name}.wav"
    command = [binary, rom, "--headless", "--capture-tick", str(tick),
               "--capture-wav", str(path), *physical_options, *extra]
    result = subprocess.run(command, text=True, capture_output=True,
                            timeout=30)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    with wave.open(str(path), "rb") as audio:
        assert (audio.getnchannels(), audio.getsampwidth(),
                audio.getframerate()) == (1, 2, 44100)
        samples = array.array("h", audio.readframes(audio.getnframes()))
    if sys.byteorder != "little":
        samples.byteswap()
    assert abs(len(samples) - tick * 44100 / 990000) < 16
    return result.stdout, samples


def rpm_and_events(output):
    match = re.search(r"\[LAB-CAPTURE\] tick=12000000 rpm=([0-9.]+) "
                      r"ram47=\d+ .*events=(\d+) event_overflow=(\d+)",
                      output)
    assert match, output[-2000:]
    assert int(match[3]) == 0
    return float(match[1]), int(match[2])


idle_output, idle = capture("audio-idle", 12000000)
repeat_output, repeat = capture("audio-idle-repeat", 12000000)
pedal_output, pedal = capture(
    "audio-pedal", 12000000, ("--pedal-step-tick", "10000000",
                                "--pedal-mm", "8"))
key_output, key_off = capture(
    "audio-key-off", 2000000, ("--replay-controls", key_off_trace))

idle_rpm, idle_events = rpm_and_events(idle_output)
repeat_rpm, repeat_events = rpm_and_events(repeat_output)
pedal_rpm, pedal_events = rpm_and_events(pedal_output)
assert idle == repeat and idle_rpm == repeat_rpm
assert ((output_dir / "sevel-audio-idle.wav").read_bytes() ==
        (output_dir / "sevel-audio-idle-repeat.wav").read_bytes())
assert idle_events == repeat_events > 0 and pedal_events > 0
assert pedal_rpm > idle_rpm + 100.0
pre_step = 10000000 * 44100 // 990000
end = 12000000 * 44100 // 990000
assert idle[:pre_step] == pedal[:pre_step]
assert idle[pre_step:end] != pedal[pre_step:end]
assert max(map(abs, idle)) < 32767 and max(map(abs, pedal)) < 32767
idle_energy = sum(sample * sample for sample in idle[pre_step:end])
pedal_energy = sum(sample * sample for sample in pedal[pre_step:end])
assert pedal_energy > idle_energy * 1.3
assert "[LAB-REPLAY] tick=2000000 controls=1 events=0" in key_output
assert not any(key_off)
print(f"[LAB-ROM-AUDIO] idle_rpm={idle_rpm:.1f} pedal_rpm={pedal_rpm:.1f} "
      f"energy_ratio={math.sqrt(pedal_energy / idle_energy):.2f} "
      "repeat=exact key_off=silent clipped=0")
