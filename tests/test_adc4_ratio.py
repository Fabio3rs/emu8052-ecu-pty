"""An assumed ADC4 board voltage reaches the Fiat ROM ratio path."""

import os
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "990000", "--adc7-mv", "1232"]
environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def run(options):
    result = subprocess.run(base + options, env=environment, text=True,
                            capture_output=True, timeout=20, check=True)
    adc = re.search(r"\[PHYSICAL-ADC4\] ram61=(\d+) ram64=(\d+) "
                    r"ram7d=(\d+)", result.stdout)
    crank = re.search(r"\[PHYSICAL-CRANK\] .*?rpm=([\d.]+)", result.stdout)
    assert adc and crank, result.stdout[-2000:]
    return tuple(map(int, adc.groups())), float(crank.group(1))


default, default_rpm = run([])
zero, zero_rpm = run(["--adc4-mv", "0"])
high, high_rpm = run(["--adc4-mv", "4000"])

assert default == (166, 90, 255), default
assert zero == (166, 0, 255), zero
assert high == (166, 205, (166 << 8) // 205), high
assert abs(default_rpm - zero_rpm) < 0.001
assert high_rpm > default_rpm + 50.0, (default_rpm, high_rpm)

for options in (["--adc4-mv", "-1"], ["--adc4-mv", "5001"]):
    result = subprocess.run(base + options, env=environment, text=True,
                            capture_output=True, timeout=5)
    assert result.returncode == 2, options

result = subprocess.run([binary, firmware, "--adc4-mv", "4000"],
                        env=environment, text=True, capture_output=True,
                        timeout=5)
assert result.returncode == 2
