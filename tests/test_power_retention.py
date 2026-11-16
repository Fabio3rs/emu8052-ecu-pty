"""Key-cycle candidate preserves XRAM; explicit snapshots cross processes."""

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


binary, firmware = sys.argv[1:3]
command = [binary, firmware, "--physical-crank", "--starter-ticks", "50000",
           "--stop-ticks", "300000"]


with tempfile.TemporaryDirectory() as directory:
    state = Path(directory) / "ecu.xram"
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                   "MA17_XRAM_STATE_FILE": str(state),
                   "MA17_WARM_REBOOT_TICK": "100000",
                   "MA17_TRACE_PC": "1"}

    def run():
        return subprocess.run(command, env=environment, text=True,
                              capture_output=True, timeout=15)

    first = run()
    assert first.returncode == 0, first.stderr[-2000:]
    assert "[XRAM-STATE] fresh file:" in first.stderr
    assert re.search(r"\[WARM-REBOOT\] tick=100000 "
                     r"xram_f8ff=([0-9A-F]{2}) retained=\1 pc=0000",
                     first.stderr)
    assert "[RESET_0 ENTRY #2]" in first.stderr
    snapshot = bytearray(state.read_bytes())
    assert len(snapshot) == 8 + 1024 and snapshot[:8] == b"MA17XRM1"

    snapshot[8 + 0x3FE] = 0xA5  # FBFE: outside boot's observed writes.
    state.write_bytes(snapshot)
    second = run()
    assert second.returncode == 0, second.stderr[-2000:]
    assert "[XRAM-STATE] loaded:" in second.stderr
    assert state.read_bytes()[8 + 0x3FE] == 0xA5

    state.write_bytes(b"invalid")
    invalid = run()
    assert invalid.returncode == 2
    assert "invalid or unreadable state file" in invalid.stderr
