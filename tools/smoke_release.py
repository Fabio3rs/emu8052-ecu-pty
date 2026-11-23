#!/usr/bin/env python3
"""Check an installed Linux GUI release from an unrelated working directory.

The only firmware used here is a temporary, generated 8051 SJMP $ loop. It is
never placed in the install prefix and does not represent the Fiat ECU ROM.
These checks exercise distribution and startup, not physical-model accuracy.
"""

import argparse
import csv
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


PROGRAMS = ("emu8051-tty", "sevel-dyno", "sevel-ma17-lab", "sevel-cad-check")
NOTICES = (
    "LICENSE.txt", "emu8051_LICENSE.txt", "OpenEngineSim_LICENSE.txt",
    "SDL3_LICENSE.txt", "DejaVu_LICENSE.txt", "Silkscreen_LICENSE.txt",
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def nonempty(path):
    require(path.is_file() and path.stat().st_size > 0, f"Missing or empty file: {path}")


def run(command, *, cwd, env, timeout=60):
    try:
        result = subprocess.run(
            [str(part) for part in command], cwd=cwd, env=env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Timed out after {timeout}s: {command[0]}") from error
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(map(str, command))}\n"
            + result.stdout[-12000:]
        )
    return result.stdout


def check(prefix, require_cad=False):
    prefix = prefix.resolve(strict=True)
    binary_dir = prefix / "bin"
    assets = binary_dir / "assets"
    for name in PROGRAMS:
        executable = binary_dir / name
        nonempty(executable)
        require(os.access(executable, os.X_OK), f"Not executable: {executable}")
    for name in NOTICES:
        nonempty(prefix / "share/licenses/emu8052-ecu-pty" / name)
    for name in ("README.md", "RELEASING.md"):
        nonempty(prefix / "share/doc/emu8052-ecu-pty" / name)
    for name in (
        "authored_meshes.obj.zlib.b64", "slkscr.ttf.zlib.b64",
        "DejaVuSansMono-Bold.ttf.zlib.b64", "DejaVu_LICENSE.txt",
        "Kottke Silkscreen License.txt", "SDL3_LICENSE.txt", "OpenEngineSim_LICENSE.txt",
        "lab-data/MA17_CALIBRATION_CATALOG.json", "lab-data/dyno_wot_e0.csv",
        "lab-data/dyno/rom/sweep_tdc117.csv", "lab-data/dyno/rom/sweep_tdc120.csv",
        "lab-data/dyno/rom/sweep_tdc123.csv",
    ):
        nonempty(assets / name)
    for shader in ("engine_sim", "sevel_cad"):
        for stage in ("vertex", "fragment"):
            for kind in ("spv", "dxil", "msl"):
                nonempty(assets / "shaders" / f"{shader}.{stage}.{kind}")

    with tempfile.TemporaryDirectory(prefix="sevel-release-smoke-") as temporary:
        work = Path(temporary).resolve()
        require(prefix != work and prefix not in work.parents,
                "Smoke work directory must be outside the installed prefix")
        # Ignore developer overrides so source/build directories cannot supply
        # missing runtime data or libraries during the relocation checks.
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("SEVEL_") and key not in ("LD_LIBRARY_PATH", "LD_PRELOAD")
        }
        env.update({
            "SDL_VIDEODRIVER": "dummy", "SDL_RENDER_DRIVER": "software",
            "SDL_AUDIODRIVER": "dummy", "XDG_CONFIG_HOME": str(work / "config"),
            "XDG_DATA_HOME": str(work / "data"),
        })
        if sys.platform.startswith("linux"):
            require(shutil.which("ldd") is not None, "ldd is required for Linux runtime checks")
            for name in PROGRAMS:
                output = run(["ldd", binary_dir / name], cwd=work, env=env)
                require("not found" not in output, f"Missing shared library for {name}:\n{output}")

        firmware = work / "synthetic-sjmp.bin"
        firmware.write_bytes(bytes((0x80, 0xFE)) + bytes(32766))
        run([binary_dir / "emu8051-tty", firmware, "--physical-crank",
             "--starter-ticks", "1000", "--stop-ticks", "10000"],
            cwd=work, env=env)
        dyno_csv = work / "dyno.csv"
        run([
            binary_dir / "sevel-dyno", "--rpm-min", "2000", "--rpm-max", "2000",
            "--cycles", "20", "--out", dyno_csv,
        ], cwd=work, env=env)
        with dyno_csv.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        require(len(rows) == 1, "Plant dyno did not produce its single requested row")
        for field in ("rpm", "torque_nm", "power_kw"):
            require(math.isfinite(float(rows[0][field])), f"Invalid dyno field: {field}")

        svg = work / "headless.svg"
        run([
            binary_dir / "sevel-ma17-lab", firmware, "--headless",
            "--starter-ticks", "1000", "--capture-tick", "10000", "--capture-svg", svg,
        ], cwd=work, env=env)
        nonempty(svg)
        require(ET.parse(svg).getroot().tag.endswith("svg"), "Headless capture is not SVG")

        screenshot = work / "software.png"
        output = run([
            binary_dir / "sevel-ma17-lab", firmware, "--no-cad",
            "--starter-ticks", "1000", "--capture-tick", "10000", "--window-frames", "2",
            "--screenshot", screenshot,
        ], cwd=work, env=env)
        nonempty(screenshot)
        data = screenshot.read_bytes()
        require(data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24,
                "GUI screenshot is not PNG; build the release with PNG support")
        width, height = struct.unpack(">II", data[16:24])
        require(width >= 320 and height >= 240, "GUI screenshot dimensions are invalid")
        require("renderer=software" in output, "GUI smoke did not use its software renderer")

        cad = assets / "sevel-cad"
        pointer = cad / "current.json"
        if require_cad:
            nonempty(pointer)
        if pointer.is_file():
            run([binary_dir / "sevel-cad-check", cad], cwd=work, env=env, timeout=180)
            print("PASS: installed CAD manifest, meshes, paths and hashes")
        print("PASS: installed executables, libraries, licenses, assets, headless SVG and software PNG")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, required=True, help="Installed Runtime prefix")
    parser.add_argument("--require-cad", action="store_true", help="Require a validated CAD registry")
    args = parser.parse_args()
    try:
        check(args.prefix, args.require_cad)
    except (OSError, RuntimeError, ValueError, KeyError, ET.ParseError) as error:
        parser.exit(1, f"Release smoke failed: {error}\n")


if __name__ == "__main__":
    main()
