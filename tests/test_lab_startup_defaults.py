"""Exercise live startup without a CAD package and compare quiet/verbose physics."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


binary, rom = map(Path, sys.argv[1:])
with tempfile.TemporaryDirectory() as work:
    root = Path(work)
    exe = root / binary.name
    shutil.copy2(binary, exe)
    assets = root / "assets"
    assets.mkdir()
    for asset in (binary.parent / "assets").iterdir():
        if asset.name != "sevel-cad":
            (assets / asset.name).symlink_to(asset.resolve())
    library = binary.parent / "libSDL3.so.0"
    if library.exists():
        (root / library.name).symlink_to(library.resolve())
    env = dict(os.environ, XDG_DATA_HOME=work, SDL_AUDIODRIVER="dummy")
    env.pop("SEVEL_LAB_FPS", None)

    def run(*options):
        result = subprocess.run(
            [exe, rom, "--auto-start", "--no-audio", "--window-frames", "10000",
             "--stop-ticks", "1200000", *options],
            capture_output=True, text=True, env=env, timeout=30)
        log = result.stdout + result.stderr
        assert result.returncode == 0, log[-2500:]
        state = next(line for line in result.stdout.splitlines()
                     if line.startswith("[LAB-STATE] tick=1200000 "))
        return log, state

    quiet, state = run()
    assert "[LAB-BENCH]" in quiet and "using classic view" in quiet
    assert "[DEBUG]" not in quiet and '"type":"ignition_pin"' not in quiet
    assert "[LAB-FPS]" not in quiet

    verbose, replayed_state = run("--verbose")
    assert state == replayed_state and '"type":"ignition_pin"' in verbose

    raw, _ = run("--no-cad", "--no-bench-preset")
    assert "[LAB-BENCH]" not in raw and "[LAB-CAD]" not in raw

    package = assets / "sevel-cad"
    package.mkdir()
    (package / "current.json").write_text("{}")
    broken, broken_state = run()
    assert "classic view" in broken and broken_state == state
