#!/usr/bin/env python3
"""UI-37 audit: inspector fields whose meaning is still a candidate must say so.

Source-level audit (the inspector is drawn as pixels): every row in
CANDIDATE_LABELS must appear in SdlDisplay.cpp, and the unmarked forms that
were replaced must not come back.
"""
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()
CANDIDATE_LABELS = {
    "phase? %s/720": "TDC phase uses EmulatorSnapshot::tdc_phase_rad, a candidate reference",
    "lamp candidate %s": "lamp output pin meaning is a candidate",
    "P1.1? %s": "P1.1 pulse reading is a candidate, not a fixed-ratio tachometer",
    "RAM27/28 %02X/%02X": "raw retained ROM fault bytes, shown as RAM addresses",
}
FORBIDDEN = {
    "phase~%s": "unmarked use of the candidate TDC reference",
    "RPM P1.1?\"": "P1.1 must not be a main pointer title (UI-15)",
}
missing = [label for label in CANDIDATE_LABELS if label not in source]
present = [label for label in FORBIDDEN if label in source]
assert not missing, f"inspector labels missing: {missing}"
assert not present, f"unmarked/forbidden labels present: {present}"
print(f"[LAB-INSPECTOR-AUDIT] {len(CANDIDATE_LABELS)} candidate labels present, "
      f"{len(FORBIDDEN)} forbidden forms absent")
