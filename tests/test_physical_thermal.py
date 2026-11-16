"""Original Fiat ROM reads battery and thermistors from thermal state."""

import json
import os
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "2000000"]


def run(extra):
    result = subprocess.run(base + extra,
                            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                            text=True, capture_output=True, timeout=20,
                            check=True)
    output = result.stdout + result.stderr
    samples = [json.loads(line) for line in output.splitlines()
               if line.startswith('{"type":"thermal"')]
    assert [sample["tick"] for sample in samples] == [990000, 1980000]
    final = re.search(r"\[PHYSICAL-THERMAL\] ([^\n]+)", output)
    assert final, output[-2000:]
    fields = dict(part.split("=") for part in final.group(1).split())
    return samples, fields


cold_samples, cold = run([])
hot_samples, hot = run(["--coolant-c", "90"])
fault_samples, recovered = run(["--coolant-c", "90",
                                "--ect-open-tick", "800000",
                                "--ect-restore-tick", "1200000"])
assert cold["ram61"] == hot["ram61"] == "166"
assert cold["ram62"] == "124" and cold["ram63"] == "117"
assert int(hot["ram62"]) < int(cold["ram62"])
assert int(hot["ram63"]) < int(cold["ram63"])
assert hot_samples[1]["air_c"] > hot_samples[0]["air_c"]
assert hot_samples[1]["iat_c"] < hot_samples[1]["air_c"]
assert hot_samples[1]["wall_c"] > hot_samples[1]["air_c"]
assert hot_samples[1]["ect_c"] > hot_samples[1]["iat_c"]
assert hot_samples[1]["adc2_v"] < hot_samples[0]["adc2_v"]
assert cold_samples[0]["adc3_v"] > hot_samples[0]["adc3_v"]
assert fault_samples[0]["adc3_v"] == 5.0
assert fault_samples[0]["adc3_upper"] == 255
assert fault_samples[0]["ram63"] != 255  # ROM elaborates the sample.
assert fault_samples[1]["adc3_upper"] == hot_samples[1]["adc3_upper"]
assert recovered["ram63"] == hot["ram63"]
