#!/usr/bin/env python3
"""LabCapture.PtraceTrace: run the Lab capture under strace (ptrace) and check
its observable system behaviour.

  * the capture finishes (exit 0) and writes the requested PNG;
  * the ROM given on the command line is actually opened;
  * the Lab never creates an internet socket (AF_INET/AF_INET6): it is a
    local simulator and must not talk to the network.

Usage: test_lab_ptrace_trace.py <sevel-ma17-lab> <rom.bin>
Skips (exit 77) when strace is missing or ptrace is not permitted.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    binary, rom = sys.argv[1:3]
    strace = shutil.which("strace")
    if not strace:
        print("SKIP: strace not installed")
        return 77

    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        env = dict(os.environ)
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "SDL_RENDER_DRIVER", "SEVEL_FONT"):
            env.pop(name, None)
        env.update(SDL_VIDEODRIVER="offscreen", XDG_DATA_HOME=str(work))
        png = work / "out.png"
        trace = work / "trace.txt"
        done = subprocess.run(
            [strace, "-f", "-o", str(trace),
             "-e", "trace=openat,socket,connect,bind",
             binary, rom, "--capture-tick", "1485000", "--window-frames", "2",
             "--screenshot", str(png)],
            env=env, capture_output=True, text=True, timeout=180)
        output = done.stdout + done.stderr
        if "Operation not permitted" in output and not trace.exists():
            print("SKIP: ptrace not permitted")
            return 77
        assert done.returncode == 0, output[-1500:]
        assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "no PNG written"

        lines = trace.read_text(errors="replace").splitlines()
        rom_name = Path(rom).name
        assert any("openat" in line and rom_name in line and "ENOENT" not in line
                   for line in lines), "ROM was never opened"
        internet = [line for line in lines
                    if re.search(r"socket\(AF_INET6?\b", line)]
        assert not internet, f"Lab opened an internet socket: {internet[:3]}"
        print(f"ptrace ok: {len(lines)} traced calls, no AF_INET sockets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
