#!/usr/bin/env python3
"""PtyBridge.LoopbackEcho: two programs talking over 127.0.0.1.

`emu8051-tty` exposes its 4800 8N1 PTY; `socat` bridges that PTY to a TCP
listener bound to the loopback interface; this script is the TCP client. The
harness echoes every received byte (half-duplex K-line echo), so each byte sent
over the socket must come back unchanged through the whole chain:

    client --TCP 127.0.0.1--> socat --PTY--> emu8051-tty --echo--> back

Usage: test_pty_loopback_bridge.py <emu8051-tty> <rom.bin>
Skips (exit 77) when socat is missing.
"""
import re
import shutil
import signal
import socket
import subprocess
import sys
import time


def free_loopback_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def main() -> int:
    binary, rom = sys.argv[1:3]
    if not shutil.which("socat"):
        print("SKIP: socat not installed")
        return 77

    emu = bridge = client = None
    try:
        emu = subprocess.Popen([binary, rom], stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True)
        pty = None
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and pty is None:
            line = emu.stdout.readline()
            if not line:
                break
            found = re.search(r"PTY pronto em: (\S+)", line)
            pty = found[1] if found else None
        assert pty, "emu8051-tty never reported its PTY"

        port = free_loopback_port()
        bridge = subprocess.Popen(
            ["socat", f"TCP-LISTEN:{port},bind=127.0.0.1,reuseaddr",
             f"{pty},raw,echo=0"], stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                client = socket.create_connection(("127.0.0.1", port), timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        assert client, "could not connect to the loopback bridge"
        assert client.getpeername()[0] == "127.0.0.1"
        client.settimeout(3)

        # 0x7F and 0x55 stress the alternating pattern; 0x10 is the K-line
        # ECU address used by the slow-init.
        for value in (0x55, 0x10, 0x7F):
            client.sendall(bytes([value]))
            echoed = client.recv(1)
            assert echoed == bytes([value]), (hex(value), echoed)
        print(f"loopback echo ok via {pty} on 127.0.0.1:{port}")
        return 0
    finally:
        if client:
            client.close()
        if bridge:
            bridge.terminate()
            bridge.wait(timeout=5)
        if emu:
            emu.send_signal(signal.SIGINT)
            try:
                emu.wait(timeout=10)
            except subprocess.TimeoutExpired:
                emu.kill()


if __name__ == "__main__":
    sys.exit(main())
