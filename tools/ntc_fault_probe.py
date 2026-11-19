"""Force a voltage on the coolant (ADC3) or air (ADC2) NTC input of the ROM and report which fault
bit (XRAM 4Eh-50h) and which IRAM (62h/63h) react; decodes the fault index with the ROM tables 5720h
and 6E27h. LLM-written (Claude)."""
import json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROM = sys.argv[2]
BIN = sys.argv[1]
OUT = sys.argv[3]
rom = Path(ROM).read_bytes()
BASE = ["--physical-crank", "--starter-ticks", "495000", "--stop-ticks", "24000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--tps-bench-profile", "--idle-motor-speed-mm-s", "50",
        "--idle-min-stop-mrad", "5", "--lambda-adc-gain", "5", "--dyno-scenario"]
tmp = tempfile.mkdtemp()
NAMES = {0x0402: "idle switch", 0x1A01: "idle actuator", 0x3102: "mixture", 0x1902: "?", 0x0602: "TPS",
         0x0A02: "coolant temp (fiat-tipo.ru)", 0x0B02: "air temp (fiat-tipo.ru)"}


def case(c):
    name, extra = c
    st = os.path.join(tmp, name + ".bin")
    r = subprocess.run([BIN, ROM, *BASE, *extra], env={"PATH": os.environ["PATH"], "MA17_XRAM_STATE_FILE": st},
                       capture_output=True, text=True, timeout=900)
    th = [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{"type":"thermal"')]
    d = open(st, "rb").read()[8:]
    bits = []
    for k in range(24):
        if d[0x4E + k // 8] >> (k % 8) & 1:
            r3 = k + 1
            e = 0x6E27 + 3 * r3
            code = rom[e] | rom[e + 1] << 8
            bits.append(f"F8{0x4E + k // 8:02X}.{k % 8}->R3={r3}:{code:04X}/{rom[e + 2]:02X}({NAMES.get(code, '?')})")
    return dict(case=name, ram62=th[-1]["ram62"], ram63=th[-1]["ram63"], adc2_v=th[-1]["adc2_v"], adc3_v=th[-1]["adc3_v"],
                faults=bits, counters=d[0x51:0x5C].hex(" "))


cases = [("base", [])]
for v in (0.0, 0.1, 0.2, 0.3, 0.5, 4.5, 4.8, 5.0):
    cases.append((f"ect_{v}V", ["--exp", "ntc_force_tick=8000000", "--exp", f"ect_force_v={v}"]))
    cases.append((f"air_{v}V", ["--exp", "ntc_force_tick=8000000", "--exp", f"air_force_v={v}"]))
with ThreadPoolExecutor(8) as ex:
    rows = list(ex.map(case, cases))
json.dump(rows, open(OUT, "w"), indent=1)
for r in rows:
    print(r["case"].ljust(10), "62h", str(r["ram62"]).rjust(3), "63h", str(r["ram63"]).rjust(3), r["faults"])
