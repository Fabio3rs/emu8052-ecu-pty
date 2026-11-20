"""Check that UI scale survives a restart outside ROM and replay state."""

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


binary, rom = sys.argv[1:3]


def wait_for_window(process):
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and process.poll() is None:
        found = subprocess.run(["xdotool", "search", "--name", "FIAT TIPO"],
                               text=True, capture_output=True)
        if found.returncode == 0 and found.stdout.strip():
            return found.stdout.splitlines()[-1]
        time.sleep(0.05)
    raise AssertionError("Lab window did not appear")


def run_with_keys(environment, keys, extra=(), drags=(), scope_drag=False,
                  wheels=(), clicks=(), camera_drags=(), screenshot=None,
                  key_delay=0.08):
    if screenshot:
        screenshot.unlink(missing_ok=True)
    process = subprocess.Popen(
        [binary, rom, "--live", "--bench-preset", "--no-audio", *extra,
         *(["--screenshot", str(screenshot)] if screenshot else [])],
        env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        window = wait_for_window(process)
        for key in keys:
            subprocess.run(["xdotool", "key", "--window", window, key],
                           check=True, capture_output=True)
            time.sleep(key_delay)
        for start_x, end_x in drags:
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(start_x), "400", "mousedown", "1"],
                           check=True, capture_output=True)
            time.sleep(0.08)
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(end_x), "400", "mouseup", "1"],
                           check=True, capture_output=True)
            time.sleep(0.08)
        if scope_drag:
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            "600", "420", "mousedown", "1"],
                           check=True, capture_output=True)
            time.sleep(0.08)
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            "600", "470", "mouseup", "1"],
                           check=True, capture_output=True)
            time.sleep(0.08)
        for x, y, button in (*wheels, *clicks):
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(x), str(y), "click", str(button)],
                           check=True, capture_output=True)
            time.sleep(0.08)
        for start_x, end_x in camera_drags:
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(start_x), "250", "mousedown", "2"],
                           check=True, capture_output=True)
            time.sleep(0.08)
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(end_x), "275", "mouseup", "2"],
                           check=True, capture_output=True)
            time.sleep(0.08)
        if screenshot:
            subprocess.run(["xdotool", "key", "--window", window, "F12"],
                           check=True, capture_output=True)
            deadline = time.monotonic() + 5.0
            while not screenshot.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            assert screenshot.exists(), screenshot
        subprocess.run(["xdotool", "key", "--window", window, "Escape"],
                       check=True, capture_output=True)
        output, _ = process.communicate(timeout=12)
        assert process.returncode == 0, output[-1200:]
        return output
    finally:
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=5)


with tempfile.TemporaryDirectory(prefix="sevel-ui-prefs-") as directory:
    environment = os.environ.copy()
    environment["XDG_DATA_HOME"] = directory
    environment["SDL_AUDIODRIVER"] = "dummy"

    first = run_with_keys(environment, ["ctrl+3"])
    assert "[LAB-UI-SCALE] source=key percent=200 saved=1" in first, first[-1200:]
    files = list(Path(directory).rglob("presentation.txt"))
    assert len(files) == 1, files
    assert files[0].read_text().split()[:11] == "v11 200 0.24 0.66 0 -1 1 0 4950000 1980000 15".split()

    override = run_with_keys(environment, [], ["--ui-scale", "100"])
    assert "[LAB-UI-SCALE] source=prefs" not in override, override[-1200:]
    assert files[0].read_text().split()[:11] == "v11 200 0.24 0.66 0 -1 1 0 4950000 1980000 15".split()

    second = run_with_keys(environment, ["ctrl+0"])
    assert "[LAB-UI-SCALE] source=prefs percent=200" in second, second[-1200:]
    assert "[LAB-UI-SCALE] source=key percent=0 saved=1" in second, second[-1200:]
    assert files[0].read_text().split()[:11] == "v11 0 0.24 0.66 0 -1 1 0 4950000 1980000 15".split()

    dragged = run_with_keys(environment, [], drags=((307, 380), (845, 925)))
    assert "[LAB-LAYOUT] left=" in dragged, dragged[-1200:]
    saved = files[0].read_text().split()
    assert saved[:2] == ["v11", "0"]
    assert abs(float(saved[2]) - 380 / 1280) < 0.01, saved
    assert abs(float(saved[3]) - 925 / 1280) < 0.01, saved

    restored = run_with_keys(environment, [])
    assert (f"[LAB-LAYOUT] source=prefs left={float(saved[2]):.3f} "
            f"right={float(saved[3]):.3f}") in restored, restored[-1200:]
    reset = run_with_keys(environment, ["ctrl+r"])
    assert "[LAB-LAYOUT] source=reset left=0.240 right=0.660 mode=0 saved=1" in reset, (
        [line for line in reset.splitlines() if "[LAB-LAYOUT]" in line])
    assert files[0].read_text().split()[:11] == "v11 0 0.24 0.66 0 -1 1 0 4950000 1980000 15".split()

    raised_scope = run_with_keys(environment, [], scope_drag=True)
    assert "[LAB-LAYOUT] left=0.240 right=0.660 scope=" in raised_scope
    saved_scope = files[0].read_text().split()
    assert abs(float(saved_scope[5]) - 238 / 720) < 0.01, saved_scope
    scope_reload = run_with_keys(environment, [])
    assert f"scope={float(saved_scope[5]):.3f}" in scope_reload
    run_with_keys(environment, ["ctrl+r"])
    assert files[0].read_text().split()[:11] == "v11 0 0.24 0.66 0 -1 1 0 4950000 1980000 15".split()

    analysis = run_with_keys(environment, ["ctrl+5"])
    assert "[LAB-LAYOUT] source=mode mode=1 saved=1" in analysis
    assert files[0].read_text().split()[:11] == "v11 0 0.24 0.66 1 -1 1 0 4950000 1980000 15".split()
    analysis_reload = run_with_keys(environment, [])
    assert "[LAB-LAYOUT] source=prefs left=0.240 right=0.660 mode=1" in analysis_reload
    mechanics = run_with_keys(environment, ["ctrl+6"])
    assert "[LAB-LAYOUT] source=mode mode=2 saved=1" in mechanics
    assert files[0].read_text().split()[:11] == "v11 0 0.24 0.66 2 -1 1 0 4950000 1980000 15".split()
    run_with_keys(environment, ["ctrl+r"])
    assert files[0].read_text().split()[:11] == "v11 0 0.24 0.66 0 -1 1 0 4950000 1980000 15".split()

    files[0].write_text("v4 0 0.24 0.66 9 -1\n")
    invalid = run_with_keys(environment, [])
    assert "[LAB-LAYOUT] source=prefs left=0.240 right=0.660 mode=0" in invalid

    files[0].write_text("v4 0 0.24 0.66 0 1.2\n")
    invalid_scope = run_with_keys(environment, [])
    assert "mode=0 scope=-1.000" in invalid_scope

    files[0].write_text("v3 150 0.3 0.7 2\n")
    prior_mode = run_with_keys(environment, [])
    assert "[LAB-LAYOUT] source=prefs left=0.300 right=0.700 mode=2 scope=-1.000" in prior_mode

    files[0].write_text("v2 150 0.3 0.7\n")
    previous = run_with_keys(environment, [])
    assert "[LAB-UI-SCALE] source=prefs percent=150" in previous
    assert "[LAB-LAYOUT] source=prefs left=0.300 right=0.700 mode=0" in previous

    files[0].write_text("v1 150\n")
    legacy = run_with_keys(environment, [])
    assert "[LAB-UI-SCALE] source=prefs percent=150" in legacy

    files[0].write_text("v4 0 0.24 0.66 0 -1\n")
    analog_choice = run_with_keys(environment, ["g"],
                                  wheels=((600, 600, 4),))
    assert "[LAB-SCOPE-PREF] saved=1 analog=1 group=1 analog_span=990000" in analog_choice
    assert files[0].read_text().split()[6:11] == [
        "1", "1", "990000", "1980000", "15"], files[0].read_text()

    digital_choice = run_with_keys(environment, ["a"],
                                   wheels=((600, 600, 4),),
                                   clicks=((350, 500, 1),))
    assert "[LAB-SCOPE-PREF] saved=1 analog=0 group=1" in digital_choice
    assert files[0].read_text().split()[6:11] == [
        "0", "1", "990000", "990000", "14"], files[0].read_text()
    scope_choice_reload = run_with_keys(environment, [])
    assert ("[LAB-SCOPE-PREF] source=prefs analog=0 group=1 "
            "analog_span=990000 digital_span=990000 mask=14") in scope_choice_reload

    files[0].write_text("v5 0 0.24 0.66 0 -1 1 0 4950000 1980000 16\n")
    invalid_channels = run_with_keys(environment, [])
    assert "[LAB-SCOPE-PREF] source=prefs analog=1 group=0" in invalid_channels

    files[0].write_text("v5 0 0.24 0.66 0 -1 1 0 4950000 1980000 15\n")
    run_with_keys(environment, [], wheels=((440, 250, 4), (710, 250, 5)),
                  camera_drags=((440, 470), (710, 730)))
    camera = files[0].read_text().split()
    assert camera[0] == "v11" and camera[11:13] == ["1", "0"], camera
    assert float(camera[21]) > 0 and float(camera[22]) > 0, camera
    assert float(camera[13]) > float(camera[16]), camera
    assert float(camera[14]) > 0 and float(camera[17]) > 0, camera
    assert float(camera[15]) > 0 and float(camera[18]) > 0, camera
    reopened = run_with_keys(environment, [])
    assert "[LAB-CAMERA-PREF] restored view=0" in reopened, reopened[-1200:]
    run_with_keys(environment, ["v"])
    assert files[0].read_text().split()[12] == "1"
    assert "[LAB-CAMERA-PREF] restored view=1" in run_with_keys(environment, [])

    font_capture = Path(binary).parent / "sevel-font110-1280x720.png"
    larger_font = run_with_keys(environment, ["ctrl+9"], screenshot=font_capture)
    assert "[LAB-FONT] percent=110 saved=1" in larger_font
    assert font_capture.stat().st_size > 10000
    # A.6: the face identity is recorded in the PNG metadata.
    png_bytes = font_capture.read_bytes()
    assert b"SEVEL Font\x00Silkscreen sha256=201df110e8dd8f19da40e5ad953b25bcac34dcb1bd14c7b8e02c9ce0b5ac0ca3" in png_bytes
    assert files[0].read_text().split()[19] == "110"
    run_with_keys(environment, [])
    assert files[0].read_text().split()[19] == "110"
    normal_font = run_with_keys(environment, ["ctrl+7"])
    assert "[LAB-FONT] percent=100 saved=1" in normal_font
    assert files[0].read_text().split()[19] == "100"

    imperial_capture = Path(binary).parent / "sevel-imperial-1280x720.png"
    imperial = run_with_keys(environment, ["ctrl+u"],
                             screenshot=imperial_capture)
    assert "[LAB-UNITS] mode=imperial saved=1" in imperial
    assert files[0].read_text().split()[20] == "1"
    assert imperial_capture.stat().st_size > 10000
    run_with_keys(environment, [])
    assert files[0].read_text().split()[20] == "1"
    thermal_capture = Path(binary).parent / "sevel-imperial-thermal-1280x720.png"
    thermal_output = run_with_keys(environment, ["g", "g", "c"],
                                   screenshot=thermal_capture, key_delay=0.25)
    assert thermal_capture.stat().st_size > 10000
    csv_match = re.search(r"\[LAB-SCOPE-CSV\] saved=(\S+) group=2", thermal_output)
    assert csv_match, thermal_output[-1200:]
    csv_lines = Path(csv_match[1]).read_text().splitlines()
    assert "# data_units=canonical_metric" in csv_lines
    assert "# view_units=imperial" in csv_lines
    assert any(line.startswith("# channel_0=ect_physical|ECT PHYSICAL|C|")
               for line in csv_lines)
    metric = run_with_keys(environment, ["ctrl+u"])
    assert "[LAB-UNITS] mode=metric saved=1" in metric
    assert files[0].read_text().split()[20] == "0"
    compact_capture = Path(binary).parent / "sevel-imperial-200-1280x720.png"
    compact_units = run_with_keys(environment, ["ctrl+u"],
                                  extra=("--ui-scale", "200"),
                                  screenshot=compact_capture)
    assert "[LAB-UNITS] mode=imperial saved=1" in compact_units
    assert "[LAB-CAMERA-PREF] fitted view=1" in compact_units
    assert compact_capture.stat().st_size > 10000
    run_with_keys(environment, ["ctrl+u"])
    assert files[0].read_text().split()[20] == "0"

    legacy_camera = files[0].read_text().split()[:19]
    files[0].write_text(" ".join(["v6", *legacy_camera[1:]]) + "\n")
    run_with_keys(environment, [])
    migrated_camera = files[0].read_text().split()
    assert migrated_camera[0] == "v11" and migrated_camera[12] == legacy_camera[12]
    assert migrated_camera[19] == "100"
    assert float(migrated_camera[21]) > 0 and float(migrated_camera[22]) > 0

    invalid_font = files[0].read_text().split()
    invalid_font[19] = "999"
    files[0].write_text(" ".join(invalid_font) + "\n")
    run_with_keys(environment, [])
    assert files[0].read_text().split()[19] == "100"

    legacy_font = files[0].read_text().split()[:20]
    files[0].write_text(" ".join(["v7", *legacy_font[1:]]) + "\n")
    run_with_keys(environment, [])
    assert files[0].read_text().split()[20] == "0"

    legacy_units = files[0].read_text().split()[:21]
    files[0].write_text(" ".join(["v8", *legacy_units[1:]]) + "\n")
    migrated = run_with_keys(environment, [])
    assert "[LAB-CAMERA-PREF] fitted" in migrated
    assert files[0].read_text().split()[0] == "v11"

    invalid_units = files[0].read_text().split()
    invalid_units[20] = "2"
    files[0].write_text(" ".join(invalid_units) + "\n")
    run_with_keys(environment, [])
    assert files[0].read_text().split()[20] == "0"

    # Font choice persists; the default is the embedded face and an invalid
    # token falls back to defaults instead of selecting a system font.
    saved_font = files[0].read_text().split()
    assert saved_font[0] == "v11" and saved_font[23] == "embedded", saved_font
    saved_font[23] = "comic-sans"
    files[0].write_text(" ".join(saved_font) + "\n")
    font_log = run_with_keys(environment, [])
    assert "face=Silkscreen" in font_log and "/usr/share/fonts" not in font_log
    assert files[0].read_text().split()[23] == "embedded"

    # T1: the P key switches the colour theme and persists it (field 24 of v11).
    assert files[0].read_text().split()[24] == "lab"
    run_with_keys(environment, ["p"])
    assert files[0].read_text().split()[0] == "v11"
    assert files[0].read_text().split()[24] == "oes", files[0].read_text()
    run_with_keys(environment, [])                       # reopening keeps it
    assert files[0].read_text().split()[24] == "oes"
    run_with_keys(environment, ["p"])
    assert files[0].read_text().split()[24] == "lab"
    print("theme key ok")
