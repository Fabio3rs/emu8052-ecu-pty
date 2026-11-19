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
coil_output, coil_fault = capture(
    "audio-coil-fault", 12000000,
    ("--coil-channel", "0", "--coil-disconnect-tick", "10000000"))
key_output, key_off = capture(
    "audio-key-off", 2000000, ("--replay-controls", key_off_trace))
running_key_off_trace = str(
    Path(key_off_trace).with_name("lab_running_key_off_controls.txt"))
stop_output, stopped = capture(
    "audio-running-stop", 12000000,
    ("--replay-controls", running_key_off_trace))
restart_trace = str(
    Path(key_off_trace).with_name("lab_running_restart_controls.txt"))
restart_output, restarted = capture(
    "audio-running-restart", 16000000,
    ("--replay-controls", restart_trace))

idle_rpm, idle_events = rpm_and_events(idle_output)
repeat_rpm, repeat_events = rpm_and_events(repeat_output)
pedal_rpm, pedal_events = rpm_and_events(pedal_output)
coil_rpm, coil_events = rpm_and_events(coil_output)
stop_state = re.search(r"\[LAB-STATE\] tick=12000000 rpm=([0-9.]+) "
                       r".* events=(\d+) event_hash=[0-9a-f]+ overflow=(\d+)",
                       stop_output)
assert stop_state and int(stop_state[3]) == 0, stop_output[-2000:]
stop_rpm, stop_events = float(stop_state[1]), int(stop_state[2])
assert idle == repeat and idle_rpm == repeat_rpm
assert ((output_dir / "sevel-audio-idle.wav").read_bytes() ==
        (output_dir / "sevel-audio-idle-repeat.wav").read_bytes())
assert idle_events == repeat_events > 0 and pedal_events > 0
assert pedal_rpm > idle_rpm + 100.0
assert coil_events > 0 and coil_rpm < idle_rpm - 300.0
pre_step = 10000000 * 44100 // 990000
end = 12000000 * 44100 // 990000
assert idle[:pre_step] == pedal[:pre_step]
assert idle[pre_step:end] != pedal[pre_step:end]
assert max(map(abs, idle)) < 32767 and max(map(abs, pedal)) < 32767
idle_energy = sum(sample * sample for sample in idle[pre_step:end])
pedal_energy = sum(sample * sample for sample in pedal[pre_step:end])
assert pedal_energy > idle_energy * 1.3
assert coil_fault[:pre_step] == idle[:pre_step]
assert coil_fault[pre_step:end] != idle[pre_step:end]
assert sum(sample * sample for sample in coil_fault[pre_step:end]) < (
    idle_energy * 0.8)
assert max(map(abs, coil_fault)) < 32767
assert "[LAB-REPLAY] tick=2000000 controls=1 events=0" in key_output
assert not any(key_off)
assert "[LAB-REPLAY] tick=12000000 controls=2" in stop_output
assert stop_events > 0 and stop_rpm < 1.0
assert stopped[:pre_step] == idle[:pre_step]
assert any(stopped[9 * 44100:pre_step])
assert not any(stopped[11 * 44100:])
restart_state = re.search(
    r"\[LAB-STATE\] tick=16000000 rpm=([0-9.]+) .* "
    r"events=(\d+) event_hash=[0-9a-f]+ overflow=(\d+)", restart_output)
assert restart_state and int(restart_state[3]) == 0, restart_output[-2000:]
# The restarted engine is running 4 s after a 24 N-m load step (12 M ticks):
# the idle recovery from that step takes ~13 s simulated with friction and
# pumping drag (445 rpm here, 900 rpm once the actuator has caught up), where
# the old engine held >700. Running and not stalled is the requirement.
assert 300.0 < float(restart_state[1]) < 1100.0
assert int(restart_state[2]) > 0
pre_off = 3000000 * 44100 // 990000
assert restarted[:pre_off] == idle[:pre_off]
assert not any(restarted[4 * 44100:8 * 44100])
assert any(restarted[9 * 44100:10 * 44100])
print(f"[LAB-ROM-AUDIO] idle_rpm={idle_rpm:.1f} pedal_rpm={pedal_rpm:.1f} "
      f"energy_ratio={math.sqrt(pedal_energy / idle_energy):.2f} "
      "repeat=exact key_off=silent running_stop=silent_tail "
      "restart=audible_pcm coil_fault=lower_energy clipped=0")
