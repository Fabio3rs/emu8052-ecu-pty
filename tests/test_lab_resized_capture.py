"""Capture the live original-ROM session at a requested window size."""

import csv
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time
import zlib


binary, rom, image_path = sys.argv[1:4]
width, height = map(int, sys.argv[4:6]) if len(sys.argv) >= 6 else (900, 620)
radial_mode = sys.argv[6] if len(sys.argv) >= 7 else ""
view_keys = {"radial": 1, "radial-help": 1,
             "axial-14": 2, "axial-23": 3}.get(radial_mode, 0)
radial_view = view_keys > 0 or radial_mode == "radial-click"
expected_view = ("RADIAL" if radial_mode.startswith("radial") else
                 "AXIAL 1/4" if radial_mode == "axial-14" else "AXIAL 2/3")
image = Path(image_path)
image.unlink(missing_ok=True)
environment = os.environ.copy()
environment["SDL_AUDIODRIVER"] = "dummy"
inspect_scope = radial_mode.startswith("scope-freeze") or radial_mode == "scope-export-tps"
stop_tick = ("8000000" if radial_mode in
             ("scope-trigger-spark14", "scope-trigger-single-tps",
              "scope-navigation", "digital-navigation") else
             "10000000" if radial_mode in
             ("scope-card-tps", "scope-card-fuel", "layout-drag",
              "scope-divider") else
             "6000000" if radial_mode in
             ("digital-zoom",) else
             "2000000" if radial_mode == "digital-idle-cursors" else
             "800000" if radial_mode in
             ("matrix-stopped", "matrix-idle", "matrix-replay-load") else
             "3000000" if inspect_scope or radial_mode in
             ("scope-trigger-single-tps", "scope-trigger-spark14",
              "scope-adc-fault", "scope-adc-bat-lambda", "scope-adc-therm",
              "scope-thermal", "scope-battery", "scope-idle",
             "scope-fit-idle",
              "digital-cursors",
              "matrix-high-load",
              "audio-fast")
             else "1500000")
command = [binary, rom, "--live", "--auto-start", "--bench-preset",
           "--window-frames", "240000",
           "--capture-tick", stop_tick, "--stop-ticks", stop_tick,
           "--screenshot", str(image)]
if radial_mode.startswith("ui-scale-"):
    command.extend(["--ui-scale",
                    radial_mode.removeprefix("ui-scale-").split("-", 1)[0]])
if radial_mode in ("stopped", "matrix-stopped", "matrix-replay-load",
                   "matrix-high-load"):
    command.remove("--auto-start")
if radial_mode in ("matrix-replay-load", "digital-idle-cursors"):
    command.extend(["--replay-controls",
                    str(Path(__file__).resolve().parent / "data/lab_control_replay.txt")])
    if radial_mode == "digital-idle-cursors":
        command.remove("--auto-start")
if radial_mode == "matrix-high-load":
    command.extend(["--replay-controls",
                    str(Path(__file__).resolve().parent / "data/lab_control_high_load.txt")])
if radial_mode == "scope-adc-fault":
    command.extend(["--tps1-high-tick", "500000",
                    "--tps1-restore-tick", "900000"])
if radial_mode == "scope-adc-bat-lambda":
    command.extend(["--lambda-stuck-mv", "4000",
                    "--lambda-stuck-tick", "500000",
                    "--lambda-restore-tick", "900000"])
if radial_mode == "scope-adc-therm":
    command.extend(["--ect-open-tick", "500000",
                    "--ect-restore-tick", "900000"])
if radial_mode == "scope-battery":
    command.extend(["--battery-mv", "12000"])
if radial_mode == "coolant-underrange":
    command.extend(["--coolant-c", "0"])

with tempfile.TemporaryFile(mode="w+") as log:
    process = subprocess.Popen(command, env=environment, stdout=log,
                               stderr=subprocess.STDOUT)
    try:
        window = ""
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline and process.poll() is None:
            found = subprocess.run(["xdotool", "search", "--name",
                                    "SEVEL MA1.7"], text=True,
                                   capture_output=True)
            if found.returncode == 0 and found.stdout.strip():
                window = found.stdout.splitlines()[-1]
                break
            time.sleep(0.05)
        assert window, "Lab window did not appear"
        resize_deadline = time.monotonic() + 2.0
        while True:
            resized = subprocess.run(
                ["xdotool", "windowsize", window, str(width), str(height)],
                capture_output=True)
            if resized.returncode == 0:
                break
            if process.poll() is not None or time.monotonic() >= resize_deadline:
                raise subprocess.CalledProcessError(
                    resized.returncode, resized.args, output=resized.stdout,
                    stderr=resized.stderr)
            time.sleep(0.05)
        subprocess.run(["xdotool", "windowmove", window, "0", "0"],
                       check=True, capture_output=True)
        if radial_mode == "audio-fast":
            subprocess.run(["xdotool", "key", "--window", window, "equal"],
                           check=True, capture_output=True)
        if radial_mode in ("layout-analysis", "layout-mechanics"):
            assert (width, height) == (1920, 1080)
            key = "ctrl+5" if radial_mode.endswith("analysis") else "ctrl+6"
            subprocess.run(["xdotool", "key", "--window", window, key],
                           check=True, capture_output=True)
        if radial_mode == "scope-divider":
            assert (width, height) == (1920, 1080)
            divider_y = 720
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            "850", "636", "mousedown", "1"],
                           check=True, capture_output=True)
            time.sleep(0.08)
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            "850", str(divider_y), "mouseup", "1"],
                           check=True, capture_output=True)
            scene_left = width * 0.24
            scene_width = width * (0.66 - 0.24)
            tps_x = round(scene_left + 21 + 1.5 * (scene_width - 42) / 11)
            tps_y = height - 8 - 26
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(tps_x), str(tps_y), "click", "1"],
                           check=True, capture_output=True)
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                if "| TPS SCOPE |" in title:
                    break
                time.sleep(0.05)
            assert "| TPS SCOPE |" in title, title
        if radial_mode == "layout-drag":
            assert (width, height) == (1920, 1080)
            for start_x, end_x in ((461, 560), (1267, 1150)):
                subprocess.run(["xdotool", "mousemove", "--window", window,
                                str(start_x), "500", "mousedown", "1"],
                               check=True, capture_output=True)
                time.sleep(0.08)
                subprocess.run(["xdotool", "mousemove", "--window", window,
                                str(end_x), "500"],
                               check=True, capture_output=True)
                time.sleep(0.08)
                subprocess.run(["xdotool", "mouseup", "1"],
                               check=True, capture_output=True)
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            "850", "104", "click", "1"],
                           check=True, capture_output=True)
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                if "| RADIAL |" in title:
                    break
                time.sleep(0.05)
            assert "| RADIAL |" in title, title
            for click_x, click_y, expected in (
                    (320, 660, "| GEAR 1 |"),
                    (760, 990, "| TPS SCOPE |")):
                subprocess.run(["xdotool", "mousemove", "--window", window,
                                str(click_x), str(click_y), "click", "1"],
                               check=True, capture_output=True)
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline and process.poll() is None:
                    title = subprocess.run(["xdotool", "getwindowname", window],
                                           text=True, capture_output=True,
                                           check=True).stdout
                    if expected in title:
                        break
                    time.sleep(0.05)
                assert expected in title, title
        if radial_mode in ("ui-scale-200-details", "ui-scale-200-ignition"):
            assert (width, height) == (1280, 720)
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            "1055" if radial_mode.endswith("details") else
                            "1190", "38", "click", "1"],
                           check=True, capture_output=True)
        if radial_mode == "ui-scale-200-view":
            logical_width = width // 2
            click_x = round((logical_width * 0.66 - 90) * 2)
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(click_x), "156", "click", "1"],
                           check=True, capture_output=True)
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                if "| RADIAL |" in title:
                    break
                time.sleep(0.05)
            assert "| RADIAL |" in title, title
        if radial_mode == "fit-click":
            scene_x = width * (0.0 if width < 1100 else 0.24)
            pane_width = width * (0.66 if width < 1100 else 0.42) * 0.5
            zoom_x = round(scene_x + pane_width * 0.5)
            zoom_y = round(max(130, height * 0.22))
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(zoom_x), str(zoom_y), "click", "--repeat", "2",
                            "--delay", "80", "4"],
                           check=True, capture_output=True)
            if width < 1280 or height < 720:
                fit_x, fit_y = round(width * 0.66 - 37), 78
            else:
                scale = min(2.0, max(1.0, min(width / 1280,
                                                height / 720)))
                fit_x = round(width * 0.66 - 268 * scale)
                fit_y = round((64 if height < 900 else 82) + 15 * scale)
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(fit_x), str(fit_y), "click", "1"],
                           check=True, capture_output=True)
        if (radial_mode in ("gear-shift", "gear-tooltip", "gear-compact-900",
                            "gear-compact-1000") or
                radial_mode.endswith("-gear-shift")):
            assert ((width >= 1100 and height >= 700) or
                    (radial_mode == "gear-compact-900" and
                     (width, height) == (900, 620)) or
                    (radial_mode == "gear-compact-1000" and
                     (width, height) == (1000, 600)))
            for _ in range(2):
                subprocess.run(["xdotool", "key", "--window", window, "e"],
                               check=True, capture_output=True)
            if radial_mode == "gear-compact-900":
                click_x, click_y = 227, 77
            elif radial_mode == "gear-compact-1000":
                click_x, click_y = 313, 105
            elif radial_mode.startswith("ui-scale-"):
                ui_scale = int(radial_mode.split("-", 3)[2]) / 100
                logical_width = round(width / ui_scale)
                scene_width = logical_width * 0.66
                button_width = (scene_width - 180) / 5
                mute_right = 16 + 3 * (button_width + 6) + button_width
                left = mute_right + 6
                right = scene_width - 8
                click_x = round((left + 0.88 * (right - left)) * ui_scale)
                click_y = round(102 * ui_scale)
            else:
                click_x = round(width * 0.24 * 0.5)
                scale = min(2.0, max(1.0, min(width / 1280, height / 720)))
                top = 410 * scale + 8
                bottom = height - 340
                if bottom - top < 64:
                    top, bottom = height - 92, height - 8
                click_y = round(top + (bottom - top) * 0.26)
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(click_x), str(click_y), "click", "1"],
                           check=True, capture_output=True)
            deadline = time.monotonic() + 2.0
            title = ""
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                if "| GEAR 3 |" in title:
                    break
                time.sleep(0.05)
            assert "| GEAR 3 |" in title, title
        if radial_mode in ("scope-card-tps", "scope-card-fuel"):
            assert width >= 1100, "Scope cards need the desktop layout"
            panel_height = max(248, height * 0.40)
            rows = 2 if panel_height >= 360 else 1
            columns = (11 + rows - 1) // rows
            cell = (width * 0.42 - 42) / columns
            index = 1 if radial_mode == "scope-card-tps" else 5
            column, row = index % columns, index // columns
            click_x = round(width * 0.24 + 21 + (column + 0.5) * cell)
            click_y = round(height - 8 - (rows - row) * 52 + 24)
            expected_scope = ("TPS" if radial_mode == "scope-card-tps"
                              else "FUEL")
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(click_x), str(click_y), "click", "1"],
                           check=True, capture_output=True)
            deadline = time.monotonic() + 2.0
            title = ""
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                if f"| {expected_scope} SCOPE |" in title:
                    break
                time.sleep(0.05)
            assert f"| {expected_scope} SCOPE |" in title, title
        if radial_mode == "scope-maximize":
            assert width >= 1100, "Maximize test needs the desktop layout"
            subprocess.run(["xdotool", "key", "--window", window, "z"],
                           check=True, capture_output=True)
            deadline = time.monotonic() + 2.0
            title = ""
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                if "| LAMBDA SCOPE MAX |" in title:
                    break
                time.sleep(0.05)
            assert "| LAMBDA SCOPE MAX |" in title, title
            click_x = round(width * 0.66 - 58)
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(click_x), "110", "click", "1"],
                           check=True, capture_output=True)
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                if "| LAMBDA SCOPE |" in title:
                    break
                time.sleep(0.05)
            assert "| LAMBDA SCOPE |" in title, title
            subprocess.run(["xdotool", "key", "--window", window, "z"],
                           check=True, capture_output=True)
        if radial_mode == "digital-zoom":
            subprocess.run(["xdotool", "windowmove", window, "0", "0"],
                           check=True, capture_output=True)
            subprocess.run(["xdotool", "key", "--window", window, "a"],
                           check=True, capture_output=True)
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            "800", "980"],
                           check=True, capture_output=True)
            time.sleep(0.2)
            for _ in range(6):
                subprocess.run(["xdotool", "click", "4"],
                               check=True, capture_output=True)
                time.sleep(0.05)
        if radial_mode in ("digital-events", "digital-cursors",
                           "digital-idle-cursors", "digital-navigation"):
            assert (width, height) == (1920, 1080) or (
                radial_mode == "digital-navigation" and
                (width, height) == (1280, 720))
            subprocess.run(["xdotool", "key", "--window", window, "a"],
                           check=True, capture_output=True)
        if radial_mode == "digital-cursors":
            deadline = time.monotonic() + 6.0
            match = None
            title = ""
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                match = re.search(r"\| tick (\d+) \|", title)
                if match and int(match[1]) >= 2200000:
                    break
                time.sleep(0.05)
            assert match and int(match[1]) >= 2200000, title
            for x, button in ((900, "1"), (1050, "3")):
                subprocess.run(["xdotool", "mousemove", "--window", window,
                                str(x), "710", "click", button],
                               check=True, capture_output=True)
        if radial_mode == "digital-idle-cursors":
            deadline = time.monotonic() + 6.0
            match = None
            title = ""
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                match = re.search(r"\| tick (\d+) \|", title)
                if match and int(match[1]) >= 1200000:
                    break
                time.sleep(0.05)
            assert match and int(match[1]) >= 1200000, title
            subprocess.run(["xdotool", "key", "--window", window, "space"],
                           check=True, capture_output=True)
            time.sleep(0.1)
            title = subprocess.run(["xdotool", "getwindowname", window],
                                   text=True, capture_output=True,
                                   check=True).stdout
            paused_tick = re.search(r"\| tick (\d+) \|", title)
            assert paused_tick, title
            time.sleep(0.1)
            again = subprocess.run(["xdotool", "getwindowname", window],
                                   text=True, capture_output=True,
                                   check=True).stdout
            assert f"| tick {paused_tick[1]} |" in again, again
            for edge_tick, button in ((500000, "1"), (900000, "3")):
                match = re.search(r"\| tick (\d+) \|", title)
                assert match, title
                x = round(626 + (edge_tick - (int(match[1]) - 1980000)) *
                          617 / 1980000)
                subprocess.run(["xdotool", "mousemove", "--window", window,
                                str(x), "985", "click", button],
                               check=True, capture_output=True)
            subprocess.run(["xdotool", "key", "--window", window, "c"],
                           check=True, capture_output=True)
            time.sleep(0.1)
            subprocess.run(["xdotool", "key", "--window", window, "x"],
                           check=True, capture_output=True)
            time.sleep(0.1)
            subprocess.run(["xdotool", "key", "--window", window, "c"],
                           check=True, capture_output=True)
            time.sleep(0.1)
            subprocess.run(["xdotool", "key", "--window", window, "space"],
                           check=True, capture_output=True)
        scope_keys = {"scope-tps": 1, "scope-thermal": 2,
                      "scope-intake": 3, "scope-engine": 4,
                      "scope-fuel": 5, "scope-adc-fault": 6,
                      "scope-adc-bat-lambda": 7,
                      "scope-adc-therm": 8, "scope-battery": 9,
                      "scope-idle": 10, "scope-fit-idle": 10,
                      "scope-freeze-tps": 1,
                      "scope-export-tps": 1, "scope-trigger-wait-tps": 1,
                      "scope-trigger-single-tps": 1}
        if radial_mode in scope_keys:
            for _ in range(scope_keys[radial_mode]):
                subprocess.run(["xdotool", "key", "--window", window, "g"],
                               check=True, capture_output=True)
            expected_scope = ("ADC TPS" if radial_mode == "scope-adc-fault"
                              else "ADC BAT/LAMBDA" if radial_mode ==
                                   "scope-adc-bat-lambda"
                              else "ADC IAT/ECT" if radial_mode ==
                                   "scope-adc-therm"
                              else "IDLE" if radial_mode == "scope-fit-idle"
                              else "TPS" if radial_mode.endswith("-tps")
                              else radial_mode.removeprefix("scope-").upper())
            deadline = time.monotonic() + 2.0
            title = ""
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                if f"| {expected_scope} SCOPE |" in title:
                    break
                time.sleep(0.05)
            assert f"| {expected_scope} SCOPE |" in title, title
            if radial_mode == "scope-battery":
                subprocess.run(["xdotool", "key", "--window", window, "d"],
                               check=True, capture_output=True)
            if radial_mode in ("scope-adc-fault", "scope-adc-bat-lambda",
                               "scope-adc-therm", "scope-thermal",
                               "scope-battery", "scope-idle",
                               "scope-fit-idle"):
                deadline = time.monotonic() + 5.0
                while time.monotonic() < deadline and process.poll() is None:
                    title = subprocess.run(["xdotool", "getwindowname", window],
                                           text=True, capture_output=True,
                                           check=True).stdout
                    match = re.search(r"\| tick (\d+) \|", title)
                    if match and int(match[1]) >= 1200000:
                        break
                    time.sleep(0.05)
                assert match and int(match[1]) >= 1200000, title
                if radial_mode == "scope-fit-idle":
                    fit_button = {(1920, 1080): (1130, 646),
                                  (1280, 720): (708, 430),
                                  (900, 620): (457, 370)}
                    assert (width, height) in fit_button
                    click_x, click_y = fit_button[(width, height)]
                    subprocess.run(["xdotool", "mousemove", "--window", window,
                                    str(click_x), str(click_y), "click", "1"],
                                   check=True, capture_output=True)
                subprocess.run(["xdotool", "key", "--window", window, "c"],
                               check=True, capture_output=True)
            if radial_mode == "scope-trigger-wait-tps":
                for _ in range(2):
                    subprocess.run(["xdotool", "key", "--window", window, "t"],
                                   check=True, capture_output=True)
            if radial_mode == "scope-trigger-single-tps":
                subprocess.run(["xdotool", "mousemove", "--window", window,
                                "950", "900"], check=True, capture_output=True)
                subprocess.run(["xdotool", "click", "4"],
                               check=True, capture_output=True)
                for _ in range(3):
                    subprocess.run(["xdotool", "key", "--window", window, "t"],
                                   check=True, capture_output=True)
                deadline = time.monotonic() + 3.0
                reached = False
                while time.monotonic() < deadline and process.poll() is None:
                    title = subprocess.run(["xdotool", "getwindowname", window],
                                           text=True, capture_output=True,
                                           check=True).stdout
                    tick = re.search(r"\| tick (\d+) \|", title)
                    if tick and int(tick[1]) >= 700000:
                        reached = True
                        break
                    time.sleep(0.05)
                assert reached, title
                subprocess.run(["xdotool", "mousemove", "--window", window,
                                "420", "115", "click", "1"],
                               check=True, capture_output=True)
        if radial_mode == "scope-trigger-spark14":
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            "950", "900"], check=True, capture_output=True)
            subprocess.run(["xdotool", "click", "4"],
                           check=True, capture_output=True)
            subprocess.run(["xdotool", "key", "--window", window,
                            "t", "t", "t", "u", "u", "u", "u", "u"],
                           check=True, capture_output=True)
        navigation_live_tick = None
        if radial_mode in ("scope-navigation", "digital-navigation"):
            scope_x = round(width * (0.24 + 0.42 * 0.55))
            scope_y = (height - 180 if radial_mode == "digital-navigation" else
                       round(height - max(248, height * 0.40) - 12 + 90))
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                tick = re.search(r"\| tick (\d+) \|", title)
                if tick and int(tick[1]) >= 2000000:
                    navigation_live_tick = int(tick[1])
                    break
                time.sleep(0.05)
            assert navigation_live_tick is not None, title
            if radial_mode == "digital-navigation":
                subprocess.run(["xdotool", "mousemove", "--window", window,
                                str(scope_x), str(scope_y), "mousedown", "2",
                                "mousemove", str(scope_x + 60), str(scope_y),
                                "mouseup", "2"],
                               check=True, capture_output=True)
                time.sleep(0.1)
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                assert "| FROZEN @" in title, title
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(scope_x), str(scope_y), "click", "4"],
                           check=True, capture_output=True)
            if radial_mode == "digital-navigation":
                subprocess.run(["xdotool", "key", "--window", window, "c"],
                               check=True, capture_output=True)
                time.sleep(0.1)
            subprocess.run(["xdotool", "mousedown", "2", "mousemove",
                            str(scope_x + 100), str(scope_y), "mouseup", "2"],
                           check=True, capture_output=True)
            subprocess.run(["xdotool", "key", "--window", window, "c"],
                           check=True, capture_output=True)
            deadline = time.monotonic() + 8.0
            restored_tick = None
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                tick = re.search(r"\| tick (\d+) \|", title)
                if tick and int(tick[1]) >= 6000000:
                    restored_tick = int(tick[1])
                    break
                time.sleep(0.05)
            assert restored_tick is not None, title
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(scope_x), str(scope_y), "click", "--repeat", "2",
                            "--delay", "50", "1"],
                           check=True, capture_output=True)
            subprocess.run(["xdotool", "key", "--window", window, "c"],
                           check=True, capture_output=True)
        frozen_tick = None
        if inspect_scope:
            deadline = time.monotonic() + 3.0
            match = None
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                match = re.search(r"\| tick (\d+) \|", title)
                if match and int(match[1]) >= 500000:
                    break
                time.sleep(0.05)
            assert match and int(match[1]) >= 500000, title
            subprocess.run(["xdotool", "key", "--window", window, "x"],
                           check=True, capture_output=True)
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                match = re.search(r"\| FROZEN @(\d+) \|", title)
                if match:
                    frozen_tick = int(match[1])
                    break
                time.sleep(0.05)
            assert frozen_tick is not None, title
            for x_position, button in ((800, "1"), (1060, "3")):
                subprocess.run(["xdotool", "mousemove", "--window", window,
                                str(x_position), "880", "click", button],
                               check=True, capture_output=True)
            if radial_mode == "scope-export-tps":
                subprocess.run(["xdotool", "key", "--window", window, "c"],
                               check=True, capture_output=True)
        if radial_view:
            if radial_mode == "radial-click":
                if width < 1280 or height < 720:
                    click_x = round(width * 0.66 - 90)
                    click_y = 78
                else:
                    scale = min(2.0, max(1.0, min(width / 1280,
                                                    height / 720)))
                    click_x = round(width * 0.66 - 164 * scale)
                    click_y = round((64 if height < 900 else 82) + 15 * scale)
                subprocess.run(
                    ["xdotool", "mousemove", "--window", window,
                     str(click_x), str(click_y), "click", "1"],
                    check=True, capture_output=True)
            else:
                for _ in range(view_keys):
                    subprocess.run(["xdotool", "key", "--window", window, "v"],
                                   check=True, capture_output=True)
            deadline = time.monotonic() + 2.0
            title = ""
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                if f"| {expected_view} |" in title:
                    break
                time.sleep(0.05)
            assert f"| {expected_view} |" in title, title
        if radial_mode == "radial-help":
            subprocess.run(["xdotool", "key", "--window", window, "h"],
                           check=True, capture_output=True)
        hover_x, hover_y = ((1440, 900) if radial_mode == "fuel-tooltip"
                            else (1550, 650) if radial_mode == "throttle-tooltip"
                            else (click_x, click_y) if radial_mode == "gear-tooltip"
                            else (4, 4))
        subprocess.run(["xdotool", "mousemove", "--window", window,
                        str(hover_x), str(hover_y)],
                       check=True, capture_output=True)
        assert process.wait(timeout=60) == 0
        log.seek(0)
        output = log.read()
        if radial_mode.startswith("matrix-"):
            image.with_suffix(".log").write_text(output)
        if radial_mode in ("layout-analysis", "layout-mechanics"):
            mode = 1 if radial_mode.endswith("analysis") else 2
            assert f"[LAB-LAYOUT] source=mode mode={mode} saved=0" in output
        if radial_mode == "scope-divider":
            assert re.search(r"\[LAB-LAYOUT\] left=0\.240 right=0\.660 "
                             r"scope=0\.32[0-9] saved=0", output), output[-1200:]
        if radial_mode == "layout-drag":
            dividers = re.findall(
                r"\[LAB-LAYOUT\] left=([\d.]+) right=([\d.]+)", output)
            assert dividers, output[-1200:]
            assert abs(float(dividers[0][0]) - 560 / width) < 0.01
        if radial_mode in ("ui-scale-200-details", "ui-scale-200-ignition"):
            page = 1 if radial_mode.endswith("details") else 2
            assert f"[LAB-INSTRUMENT-TAB] page={page}" in output, output[-1000:]
        if radial_mode == "fit-click":
            fit = re.search(r"\[LAB-VIEW-FIT\] zoom_before=([\d.]+) "
                            r"tick=(\d+)", output)
            assert fit and float(fit[1]) > 0.85, output[-1200:]
        if radial_mode == "digital-zoom":
            assert re.search(r"\[LAB-CAPTURE\].*digital_span_ticks=9900", output), (
                output[-1000:])
        if radial_mode == "digital-idle-cursors":
            frozen = re.search(r"\[LAB-SCOPE-FREEZE\] mode=digital end=(\d+)",
                               output)
            assert frozen and int(frozen[1]) < int(stop_tick), output[-1600:]
            saved = re.findall(r"\[LAB-SCOPE-CSV\] saved=(\S+) group=-1 "
                               r"first=500000 last=900000", output)
            assert len(saved) == 2, output[-1600:]
            lines = Path(saved[1]).read_text().splitlines()
            assert "# format=sevel-ma17-digital-scope-v1" in lines
            assert "# selection_first_tick=500000" in lines
            assert "# selection_last_tick=900000" in lines
            assert f"# view_last_tick={frozen[1]}" in lines
            assert "# visible_channel_mask=1111" in lines
            assert "# exported_channels=all_retained_digital_sources" in lines
            assert any(line.startswith("# rom_fnv64=") for line in lines)
            rows = list(csv.DictReader(line for line in lines
                                       if not line.startswith("#")))
            assert rows[0]["tick"] == "500000" and rows[-1]["tick"] == "900000"
            assert any(row["kind"] == "injector_pin" for row in rows)
            assert [(row["tick"], row["state"])
                    for row in rows if row["kind"] == "idle_contact_sample"] == [
                        ("500000", "open"), ("900000", "closed")]
            assert saved[1].endswith(".csv")
            assert Path(saved[1][:-4] + ".png").is_file()
        if radial_mode == "scope-trigger-wait-tps":
            assert "[LAB-TRIGGER] mode=2 group=1 channel=0" in output
            assert "[LAB-TRIGGER] waiting group=1 channel=0 level=2.500" in output
        if radial_mode == "scope-trigger-single-tps":
            armed = re.search(r"\[LAB-TRIGGER\] mode=[123] group=1 channel=0 "
                              r".*armed=(\d+)", output)
            matched = re.search(r"\[LAB-TRIGGER\] single tick=(\d+) end=(\d+) "
                                r"group=1 channel=0", output)
            assert armed and matched, "\n".join(
                line for line in output.splitlines()
                if "[LAB-TRIGGER]" in line) + output[-500:]
            assert int(armed[1]) <= int(matched[1])
            assert 0 < int(matched[1]) < int(matched[2]) < int(stop_tick)
        if radial_mode == "scope-trigger-spark14":
            armed = re.search(r"\[LAB-TRIGGER\] mode=3 group=0 channel=1 "
                              r"source=3 .*armed=(\d+)", output)
            matched = re.search(r"\[LAB-TRIGGER\] single tick=(\d+) end=(\d+) "
                                r"group=0 channel=1 source=3", output)
            assert armed and matched, output[-1500:]
            assert int(armed[1]) <= int(matched[1]) < int(matched[2]) < int(stop_tick)
        if radial_mode in ("scope-navigation", "digital-navigation"):
            saved = re.findall(r"\[LAB-SCOPE-CSV\] saved=(\S+)", output)
            assert len(saved) == (3 if radial_mode == "digital-navigation"
                                  else 2), (len(saved), [line for line in
                output.splitlines() if "[LAB-SCOPE-CSV]" in line])
            comments = Path(saved[0]).read_text().splitlines()
            first = int(next(row.split("=", 1)[1] for row in comments
                             if row.startswith("# view_first_tick=")))
            last = int(next(row.split("=", 1)[1] for row in comments
                            if row.startswith("# view_last_tick=")))
            assert last - first == 990000, (first, last)
            assert last < navigation_live_tick, (last, navigation_live_tick)
            if radial_mode == "digital-navigation":
                panned = Path(saved[1]).read_text().splitlines()
                panned_last = int(next(row.split("=", 1)[1] for row in panned
                                       if row.startswith("# view_last_tick=")))
                assert panned_last < last, (panned_last, last)
            restored = Path(saved[-1]).read_text().splitlines()
            restored_first = int(next(row.split("=", 1)[1] for row in restored
                                      if row.startswith("# view_first_tick=")))
            restored_last = int(next(row.split("=", 1)[1] for row in restored
                                     if row.startswith("# view_last_tick=")))
            expected_restored_span = (1980000 if radial_mode ==
                                      "digital-navigation" else 5 * 990000)
            assert restored_last - restored_first == expected_restored_span, (
                restored_first, restored_last, restored_tick, saved)
            assert restored_last >= restored_tick
        state = re.search(r"\[LAB-STATE\].*cc3=(\d+) burns=(\d+)", output)
        assert state, "final Lab state missing"
        if radial_mode.startswith("matrix-"):
            matrix_state = re.search(
                r"\[LAB-STATE\] tick=(\d+) rpm=([0-9.]+)", output)
            expected_tick = 3000000 if radial_mode == "matrix-high-load" else 800000
            assert matrix_state and int(matrix_state[1]) == expected_tick
            rpm = float(matrix_state[2])
            if radial_mode == "matrix-stopped":
                assert rpm == 0.0
            elif radial_mode == "matrix-high-load":
                assert 0.0 < rpm < 8000.0, rpm
            else:
                assert 300.0 < rpm < 1500.0, rpm
        if radial_mode in ("stopped", "matrix-stopped"):
            assert int(state[1]) == 0 and int(state[2]) == 0, state[0]
        else:
            assert int(state[1]) > 0 and int(state[2]) > 0, state[0]
        if frozen_tick is not None:
            final_tick = re.search(r"\[LAB-STATE\] tick=(\d+)", output)
            assert final_tick and int(final_tick[1]) > frozen_tick, (
                frozen_tick, final_tick[0] if final_tick else output[-500:])
        if radial_mode == "scope-thermal":
            saved = re.search(r"\[LAB-SCOPE-CSV\] saved=(\S+) group=(\d+) "
                              r"first=(\d+) last=(\d+)", output)
            assert saved and saved[2] == "2", output[-1000:]
            lines = Path(saved[1]).read_text().splitlines()
            assert any("ect_physical|ECT PHYSICAL|C|" in line for line in lines)
            assert any("iat_physical|IAT PHYSICAL|C|" in line for line in lines)
            data = list(csv.DictReader(line for line in lines
                                       if not line.startswith("#")))
            assert len(data) > 10
            assert {"ect_physical_C", "iat_physical_C", "thermostat_%",
                    "fan_on_sampled"} <= set(data[0])
            assert any(row["ect_physical_C"] and row["iat_physical_C"] and
                       float(row["ect_physical_C"]) >
                       float(row["iat_physical_C"]) for row in data)
            assert any(row["fan_on_sampled"] == "0" for row in data)
        if radial_mode in ("scope-idle", "scope-fit-idle"):
            saved = re.search(r"\[LAB-SCOPE-CSV\] saved=(\S+) group=(\d+) "
                              r"first=(\d+) last=(\d+)", output)
            assert saved and saved[2] == "10", output[-1000:]
            lines = Path(saved[1]).read_text().splitlines()
            assert any("idle_stem|HASTE|mm|candidate idle-actuator bridge"
                       in line for line in lines)
            data = list(csv.DictReader(line for line in lines
                                       if not line.startswith("#")))
            assert len(data) > 10
            assert {"idle_stem_mm", "idle_contact_state"} <= set(data[0])
            assert any(row["idle_stem_mm"] for row in data)
            assert any(row["idle_contact_state"] in ("0", "1")
                       for row in data)
            if radial_mode == "scope-fit-idle":
                fitted = re.search(r"\[LAB-SCOPE-Y\] group=10 tick=(\d+) "
                                   r"min=([-\d.]+) max=([-\d.]+)", output)
                assert fitted, output[-1000:]
                fit_tick = int(fitted[1])
                lower, upper = float(fitted[2]), float(fitted[3])
                assert lower < upper and upper - lower < 40, fitted[0]
                fitted_values = [float(row["idle_stem_mm"]) for row in data
                                 if row["idle_stem_mm"] and
                                 int(row["tick"]) <= fit_tick]
                assert fitted_values, fitted[0]
                assert lower < min(fitted_values) <= max(fitted_values) < upper
        if radial_mode == "scope-battery":
            saved = re.search(r"\[LAB-SCOPE-CSV\] saved=(\S+) group=(\d+) "
                              r"first=(\d+) last=(\d+)", output)
            assert saved and saved[2] == "9", output[-1000:]
            lines = Path(saved[1]).read_text().splitlines()
            assert any("battery_supply|BATTERY SUPPLY|V|" in line
                       for line in lines)
            data = list(csv.DictReader(line for line in lines
                                       if not line.startswith("#")))
            assert len(data) > 10
            assert {"battery_supply_V", "adc1_battery_pin_V", "adc1_count",
                    "adc1_conversion_tick", "adc1_age_ms"} <= set(data[0])
            raw_bytes = {f"rom_iram_{address:02x}_u8"
                         for address in range(0x60, 0x68)}
            assert raw_bytes <= set(data[0])
            assert any(all(0 <= int(row[name]) <= 255 for name in raw_bytes)
                       for row in data)
            assert any(row["battery_supply_V"] and
                       abs(float(row["battery_supply_V"]) - 12.0) < 0.01
                       for row in data)
            assert any(row["adc1_battery_pin_V"] and
                       abs(float(row["adc1_battery_pin_V"]) - 3.12) < 0.05
                       for row in data)
        if radial_mode == "scope-adc-fault":
            saved = re.search(r"\[LAB-SCOPE-CSV\] saved=(\S+) group=(\d+) "
                              r"first=(\d+) last=(\d+)", output)
            assert saved and saved[2] == "6", output[-1000:]
            lines = Path(saved[1]).read_text().splitlines()
            data = list(csv.DictReader(line for line in lines
                                       if not line.startswith("#")))
            assert len(data) > 10
            assert {"adc0_tps2_pin_V", "adc6_tps1_pin_V", "adc0_count",
                    "adc0_conversion_tick", "adc0_age_ms", "adc6_count",
                    "adc6_conversion_tick", "adc6_age_ms"} <= set(data[0])
            assert any(row["adc6_tps1_pin_V"] and
                       float(row["adc6_tps1_pin_V"]) > 4.9 for row in data)
            assert any(row["adc6_tps1_pin_V"] and
                       float(row["adc6_tps1_pin_V"]) < 2.0 for row in data)
            assert all(int(row["adc6_conversion_tick"]) <= int(row["tick"])
                       for row in data if row["adc6_conversion_tick"])
        if radial_mode in ("scope-adc-bat-lambda", "scope-adc-therm"):
            saved = re.search(r"\[LAB-SCOPE-CSV\] saved=(\S+) group=(\d+) "
                              r"first=(\d+) last=(\d+)", output)
            group = 7 if radial_mode == "scope-adc-bat-lambda" else 8
            assert saved and int(saved[2]) == group, output[-1000:]
            lines = Path(saved[1]).read_text().splitlines()
            data = list(csv.DictReader(line for line in lines
                                       if not line.startswith("#")))
            channels = (1, 5) if group == 7 else (2, 3)
            assert len(data) > 10
            for channel in channels:
                name = f"adc{channel}"
                assert {f"{name}_count", f"{name}_conversion_tick",
                        f"{name}_age_ms"} <= set(data[0])
                assert any(row[f"{name}_count"] for row in data)
                assert all(int(row[f"{name}_conversion_tick"]) <= int(row["tick"])
                           for row in data if row[f"{name}_conversion_tick"])
            fault_channel = 5 if group == 7 else 3
            pin = f"adc{fault_channel}_" + (
                "lambda_pin_V" if group == 7 else "ect_pin_V")
            assert any(row[pin] and 500000 <= int(row["tick"]) < 900000
                       and float(row[pin]) > 3.9 for row in data)
            restored_maximum = 3.0 if group == 7 else 1.0
            assert any(row[pin] and int(row["tick"]) >= 900000
                       and float(row[pin]) < restored_maximum for row in data)
        if radial_mode == "scope-export-tps":
            saved = re.search(r"\[LAB-SCOPE-CSV\] saved=(\S+) group=(\d+) "
                              r"first=(\d+) last=(\d+)", output)
            assert saved and saved[2] == "1", output[-1000:]
            csv_path = Path(saved[1])
            lines = csv_path.read_text().splitlines()
            assert lines[0] == "# format=sevel-ma17-scope-v1"
            assert any(line.startswith("# rom_fnv64=") for line in lines)
            assert any(line.startswith("# scenario_arg_0=") for line in lines)
            assert "# trigger_mode=off" in lines
            metadata = dict(line[2:].split("=", 1) for line in lines
                            if line.startswith("# ") and "=" in line)
            assert metadata["sample_policy"] == (
                "retained_snapshots_and_archive_extrema")
            assert int(metadata["gaps_over_250ms"]) >= 0
            assert int(metadata["raw_evicted_total"]) >= 0
            assert int(metadata["archive_evicted_total"]) >= 0
            data = list(csv.DictReader(line for line in lines
                                       if not line.startswith("#")))
            assert len(data) > 10
            assert int(metadata["retained_sample_count"]) == len(data)
            assert set(data[0]) == {"tick", "time_s", "tps_track1_V",
                                    "tps_track2_V", "throttle_angle_deg"}
            ticks = [int(row["tick"]) for row in data]
            assert ticks == sorted(set(ticks))
            assert (int(saved[3]), int(saved[4])) == (ticks[0], ticks[-1])
            assert (int(metadata["selection_first_tick"]),
                    int(metadata["selection_last_tick"])) == (
                        ticks[0], ticks[-1])
            assert all(abs(float(row["time_s"]) - int(row["tick"]) / 990000)
                       < 1e-9 for row in (data[0], data[-1]))
            assert any(row["tps_track1_V"] for row in data)
            panel_png = csv_path.with_suffix(".png")
            panel_bytes = panel_png.read_bytes()
            assert panel_bytes.startswith(b"\x89PNG\r\n\x1a\n")
            panel_width, panel_height = struct.unpack(">II", panel_bytes[16:24])
            assert (panel_width, panel_height) == (774, 432)
            offset = 8
            chunks = []
            while offset < len(panel_bytes):
                length = struct.unpack_from(">I", panel_bytes, offset)[0]
                kind = panel_bytes[offset + 4:offset + 8]
                payload = panel_bytes[offset + 8:offset + 8 + length]
                crc = struct.unpack_from(">I", panel_bytes,
                                         offset + 8 + length)[0]
                assert crc == zlib.crc32(kind + payload) & 0xffffffff
                chunks.append((kind, payload))
                offset += length + 12
            assert offset == len(panel_bytes)
            text_chunks = [payload for kind, payload in chunks if kind == b"tEXt"]
            assert len(text_chunks) == 1
            keyword, panel_metadata = text_chunks[0].split(b"\0", 1)
            assert keyword == b"SEVEL Scope"
            for expected in (b"# rom_fnv64=", b"# scenario_arg_0=",
                             b"# channel_0=tps_track1", b"# selection_first_tick=",
                             b"# view_last_tick=", b"# trigger_mode=off"):
                assert expected in panel_metadata, expected
            compressed_panel = b"".join(payload for kind, payload in chunks
                                        if kind == b"IDAT")
            panel_scanlines = zlib.decompress(compressed_panel)
            assert len(panel_scanlines) == panel_height * (panel_width * 4 + 1)
            previous = bytearray(panel_width * 4)
            purple = orange = 0
            for row in range(panel_height):
                stride = panel_width * 4 + 1
                encoded = panel_scanlines[row * stride + 1:(row + 1) * stride]
                pixels = bytearray(panel_width * 4)
                for index, byte in enumerate(encoded):
                    left = pixels[index - 4] if index >= 4 else 0
                    above = previous[index]
                    upper_left = previous[index - 4] if index >= 4 else 0
                    predictors = (0, left, above, (left + above) // 2)
                    filter_kind = panel_scanlines[row * stride]
                    if filter_kind == 4:
                        estimate = left + above - upper_left
                        choices = (left, above, upper_left)
                        predictor = min(choices, key=lambda value: abs(estimate - value))
                    else:
                        assert filter_kind < 4
                        predictor = predictors[filter_kind]
                    pixels[index] = (byte + predictor) & 255
                if 30 < row < panel_height - 40:
                    for x in range(140, panel_width - 40):
                        red, green, blue = pixels[x * 4:x * 4 + 3]
                        purple += red >= 170 and blue >= 190 and blue > green + 35
                        orange += red >= 200 and 120 <= green <= 220 and blue < 150
                previous = pixels
            assert purple > 50 and orange > 50, (purple, orange)
        header = image.read_bytes()[:24]
        assert header.startswith(b"\x89PNG\r\n\x1a\n"), header
        size = struct.unpack(">II", header[16:24])
        assert size == (width, height), size
        data = image.read_bytes()
        assert data[24:26] == b"\x08\x06", data[24:26]
        cursor = 8
        compressed = bytearray()
        while cursor < len(data):
            length = struct.unpack(">I", data[cursor:cursor + 4])[0]
            kind = data[cursor + 4:cursor + 8]
            if kind == b"IDAT":
                compressed.extend(data[cursor + 8:cursor + 8 + length])
            cursor += length + 12
        scanlines = zlib.decompress(compressed)
        stride = width * 4 + 1
        assert len(scanlines) == stride * height
        if radial_mode == "ui-scale-200" and (width, height) == (1280, 720):
            # The scope heading must stop before the FIT Y button at x=500.
            previous = bytearray(width * 4)
            title_pixels = 0
            overlap_pixels = 0
            for row in range(529):
                filter_kind = scanlines[row * stride]
                encoded = scanlines[row * stride + 1:(row + 1) * stride]
                pixels = bytearray(width * 4)
                for index, byte in enumerate(encoded):
                    left = pixels[index - 4] if index >= 4 else 0
                    above = previous[index]
                    upper_left = previous[index - 4] if index >= 4 else 0
                    if filter_kind == 4:
                        guess = left + above - upper_left
                        predictor = min((left, above, upper_left),
                                        key=lambda value: abs(guess - value))
                    else:
                        assert filter_kind < 4
                        predictor = (0, left, above,
                                     (left + above) // 2)[filter_kind]
                    pixels[index] = (byte + predictor) & 255
                if 500 <= row < 529:
                    title_pixels += sum(
                        pixels[4 * x + 1] >= 130 and
                        pixels[4 * x + 2] >= 150 for x in range(40, 260))
                    overlap_pixels += sum(
                        pixels[4 * x + 1] >= 130 and
                        pixels[4 * x + 2] >= 150 for x in range(460, 500))
                previous = pixels
            assert title_pixels > 100 and overlap_pixels == 0, (
                "scope heading overlaps FIT Y", title_pixels, overlap_pixels)
        if radial_mode == "coolant-underrange":
            assert (width, height) in ((1920, 1080), (900, 620))
            if width == 1920:
                marker_rows, marker_columns = range(285, 306), range(15, 75)
                value_columns = range(180, 275)
            else:
                marker_rows, marker_columns = range(292, 310), range(598, 632)
                value_columns = range(644, 702)
            previous = bytearray(width * 4)
            low_pixels = 0
            value_pixels = 0
            lambda_top_pixels = 0
            lambda_bottom_pixels = 0
            for row in range(610 if width == 900 else 310):
                kind = scanlines[row * stride]
                encoded = scanlines[row * stride + 1:(row + 1) * stride]
                pixels = bytearray(width * 4)
                for index, byte in enumerate(encoded):
                    left = pixels[index - 4] if index >= 4 else 0
                    above = previous[index]
                    upper_left = previous[index - 4] if index >= 4 else 0
                    if kind == 4:
                        estimate = left + above - upper_left
                        predictor = min((left, above, upper_left),
                                        key=lambda value: abs(estimate - value))
                    else:
                        assert kind < 4
                        predictor = (0, left, above,
                                     (left + above) // 2)[kind]
                    pixels[index] = (byte + predictor) & 255
                if row in marker_rows:
                    low_pixels += sum(
                        pixels[4 * x] >= 190 and pixels[4 * x + 1] < 120
                        and pixels[4 * x + 2] < 120
                        for x in marker_columns)
                    value_pixels += sum(
                        min(pixels[4 * x:4 * x + 3]) >= 190
                        for x in value_columns)
                if width == 900 and 556 <= row < 574:
                    lambda_top_pixels += sum(
                        pixels[4 * x] >= 190 and pixels[4 * x + 1] < 120
                        and pixels[4 * x + 2] < 120
                        for x in range(598, 631))
                if width == 900 and 591 <= row < 610:
                    lambda_bottom_pixels += sum(
                        pixels[4 * x] >= 190 and pixels[4 * x + 1] < 120
                        and pixels[4 * x + 2] < 120
                        # The donor-width needle reaches the right edge here.
                        for x in range(598, 615))
                previous = pixels
            assert low_pixels > 8 and value_pixels > 15, (
                "coolant LOW marker or numeric value missing",
                low_pixels, value_pixels)
            if width == 900:
                assert lambda_top_pixels > 20 and lambda_bottom_pixels < 12, (
                    "lambda LOW marker overlaps its numeric value",
                    lambda_top_pixels, lambda_bottom_pixels)
        # A resize must produce a cleared frame, not a transparent new area.
        previous_alpha = 0
        for row in range(height):
            filter_kind = scanlines[row * stride]
            encoded_alpha = scanlines[row * stride + 4]
            if filter_kind in (0, 1):
                alpha = encoded_alpha
            elif filter_kind in (2, 4):
                alpha = (encoded_alpha + previous_alpha) % 256
            elif filter_kind == 3:
                alpha = (encoded_alpha + previous_alpha // 2) % 256
            else:
                raise AssertionError(f"unsupported PNG filter {filter_kind}")
            assert alpha == 255, (row, alpha)
            previous_alpha = alpha
        if radial_mode in ("fuel-tooltip", "throttle-tooltip"):
            assert (width, height) == (1920, 1080)
            previous = bytearray(width * 4)
            cyan = 0
            first_row, last_row = ((910, 925) if radial_mode == "fuel-tooltip"
                                   else (655, 730))
            for row in range(last_row):
                kind = scanlines[row * stride]
                encoded = scanlines[row * stride + 1:(row + 1) * stride]
                pixels = bytearray(width * 4)
                for index, byte in enumerate(encoded):
                    left = pixels[index - 4] if index >= 4 else 0
                    above = previous[index]
                    upper_left = previous[index - 4] if index >= 4 else 0
                    if kind == 4:
                        estimate = left + above - upper_left
                        predictor = min((left, above, upper_left),
                                        key=lambda value: abs(estimate - value))
                    else:
                        assert kind < 4
                        predictor = (0, left, above, (left + above) // 2)[kind]
                    pixels[index] = (byte + predictor) & 255
                if first_row <= row < last_row:
                    cyan += sum(tuple(pixels[4 * x:4 * x + 3]) ==
                                (99, 211, 220) for x in range(1350, 1910))
                previous = pixels
            assert cyan > 100, ("tooltip border missing", radial_mode, cyan)
        if radial_mode == "scope-battery" and (width, height) == (900, 620):
            previous = bytearray(width * 4)
            status_text = 0
            status_overflow = 0
            for row in range(341):
                kind = scanlines[row * stride]
                encoded = scanlines[row * stride + 1:(row + 1) * stride]
                pixels = bytearray(width * 4)
                for index, byte in enumerate(encoded):
                    left = pixels[index - 4] if index >= 4 else 0
                    above = previous[index]
                    upper_left = previous[index - 4] if index >= 4 else 0
                    if kind == 4:
                        estimate = left + above - upper_left
                        predictor = min((left, above, upper_left),
                                        key=lambda value: abs(estimate - value))
                    else:
                        assert kind < 4
                        predictor = (0, left, above, (left + above) // 2)[kind]
                    pixels[index] = (byte + predictor) & 255
                if 43 <= row < 55:
                    status_text += sum(min(pixels[4 * x:4 * x + 3]) > 100
                                       for x in range(500, 570))
                    status_overflow += sum(min(pixels[4 * x:4 * x + 3]) > 100
                                           for x in range(580, 594))
                previous = pixels
            assert status_text > 20 and status_overflow == 0, (
                "compact status crosses into gauges", status_text,
                status_overflow)
            assert tuple(previous[25 * 4:25 * 4 + 3]) == (58, 93, 104), (
                "KEY button obscured by compact inspector",
                tuple(previous[25 * 4:25 * 4 + 3]))
        if frozen_tick is not None or radial_mode in (
                "scope-trigger-single-tps", "scope-trigger-spark14",
                "digital-events", "digital-cursors", "digital-idle-cursors"):
            previous = bytearray(width * 4)
            cursor_row = None
            digital_cursor_row = None
            region_counts = {"longitudinal": 0, "profile_cyan": 0,
                             "profile_pink": 0, "scope_trace": 0,
                             "trigger_marker": 0, "spark": 0, "burn": 0}
            for row in range(height if radial_mode in
                             ("digital-events", "digital-cursors",
                              "digital-idle-cursors") else 901):
                filter_kind = scanlines[row * stride]
                encoded = scanlines[row * stride + 1:(row + 1) * stride]
                pixels = bytearray(width * 4)
                for index, byte in enumerate(encoded):
                    left = pixels[index - 4] if index >= 4 else 0
                    above = previous[index]
                    upper_left = previous[index - 4] if index >= 4 else 0
                    if filter_kind == 0:
                        predictor = 0
                    elif filter_kind == 1:
                        predictor = left
                    elif filter_kind == 2:
                        predictor = above
                    elif filter_kind == 3:
                        predictor = (left + above) // 2
                    else:
                        guess = left + above - upper_left
                        distances = (abs(guess - left), abs(guess - above),
                                     abs(guess - upper_left))
                        predictor = (left, above, upper_left)[distances.index(
                            min(distances))]
                    pixels[index] = (byte + predictor) & 255
                previous = pixels
                if radial_mode == "digital-events" and 1020 <= row < 1040:
                    for x in range(625, 1244):
                        color = tuple(pixels[4 * x:4 * x + 3])
                        region_counts["spark"] += color in (
                            (99, 211, 220), (249, 190, 96))
                        region_counts["burn"] += color == (184, 210, 140)
                if row % 8 == 4:
                    for x in range(470, 1250, 4):
                        red, green, blue = pixels[4 * x:4 * x + 3]
                        if 100 <= row < 600:
                            if (x < 840 and min(red, green, blue) >= 190
                                    and max(red, green, blue) - min(red, green, blue) < 28):
                                region_counts["longitudinal"] += 1
                            if (x >= 850 and 70 <= red <= 160
                                    and 140 <= green <= 230 and 160 <= blue <= 240
                                    and blue > red + 30):
                                region_counts["profile_cyan"] += 1
                            if (x >= 850 and red >= 160 and 70 <= green <= 180
                                    and 110 <= blue <= 215 and red > green + 35):
                                region_counts["profile_pink"] += 1
                        elif 650 <= row < 900 and red >= 130 and blue >= 160 \
                                and blue > green + 20:
                            region_counts["scope_trace"] += 1
                    if radial_mode in ("scope-trigger-single-tps",
                                       "scope-trigger-spark14") and 660 <= row < 900:
                        for x in range(650, 1200):
                            if tuple(pixels[4 * x:4 * x + 3]) == (175, 203, 111):
                                region_counts["trigger_marker"] += 1
                if row == 800:
                    cursor_row = pixels
                if row == 930 and radial_mode in (
                        "digital-cursors", "digital-idle-cursors"):
                    digital_cursor_row = pixels
            if radial_mode in ("digital-cursors", "digital-idle-cursors"):
                assert digital_cursor_row is not None
                markers = []
                for color in ((249, 190, 96), (99, 211, 220)):
                    positions = [x for x in range(625, 1240)
                                 if tuple(digital_cursor_row[4 * x:
                                                             4 * x + 3]) == color]
                    assert positions, color
                    markers.append(positions[0])
                assert abs(markers[0] - markers[1]) > 20, markers
            if radial_mode == "digital-events":
                assert region_counts["spark"] > 5, region_counts
                assert region_counts["burn"] > 5, region_counts
                print(f"[LAB-DIGITAL-EVENTS] {region_counts}")
            else:
                assert cursor_row is not None
                assert region_counts["longitudinal"] > 20, region_counts
                assert region_counts["profile_cyan"] > 20, region_counts
                assert region_counts["profile_pink"] > 20, region_counts
                assert region_counts["scope_trace"] > 3, region_counts
                if radial_mode in ("scope-trigger-single-tps", "scope-trigger-spark14"):
                    assert region_counts["trigger_marker"] > 12, region_counts
                elif radial_mode not in ("digital-cursors", "digital-idle-cursors"):
                    for expected_x, color in ((800, (249, 190, 96)),
                                              (1060, (99, 211, 220))):
                        assert any(tuple(cursor_row[4 * x:4 * x + 3]) == color
                                   for x in range(expected_x - 6, expected_x + 7)), (
                                       expected_x, color)
        print(f"[LAB-RESIZE] png={image} size={size} "
              f"cc3={state[1]} burns={state[2]}")
    except Exception:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        log.seek(0)
        print(log.read()[-3000:], file=sys.stderr)
        raise
