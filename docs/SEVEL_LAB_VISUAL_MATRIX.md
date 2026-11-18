# SEVEL Lab visual comparison matrix

## Current five-state batch — 2026-11-18

NativeLab `p_cb3092e6c577` captured all five states at 1920×1080 in isolated
Xvfb displays (two concurrent workers). All five scripts passed. Each new
log's complete `[LAB-STATE]` line exactly matches its historical before log,
including physical RPM, RAM47, state/event hashes and zero overflow.

| State | Tick | Physical RPM | Current artifact |
| --- | ---: | ---: | --- |
| Key off | 800000 | 0 | [PNG](../.work/gui-review/states-20261118/stopped.png) |
| Warm bench candidate idle | 800000 | 939.609808 | [PNG](../.work/gui-review/states-20261118/idle-fixed.png) |
| Replayed 24 Nm | 800000 | 654.545794 | [PNG](../.work/gui-review/states-20261118/replay-load.png) |
| Replayed 60 Nm / 25 mm cable | 3000000 | 768.165537 | [PNG](../.work/gui-review/states-20261118/high-load.png) |
| Paused replay | 1500000 | 997.653527 | [PNG](../.work/gui-review/states-20261118/paused.png) |

All five images were inspected: both mechanical views, piston orientation,
gauges, out-of-range lambda text, replay-disabled controls, selected KEY/PAUSE
inversion and scope labels remain visible. P1.1 dial values still differ
from physical RPM and are explicitly marked as a hypothesis; this batch
does not validate the electrical tachometer mapping.

Inspection found START's HOLD annotation crossing its 40 px button border
because the old vertical offsets scaled independently of button height.
Both text positions now derive from button height. NativeLab
`p_9332a92aedc0` rebuilt and refreshed only the affected idle cell as
`idle-fixed.png`; visual inspection confirms HOLD is inside the border.
The other four images retain the pre-fix annotation and are not claimed
as pixel-exact captures of that final two-line position adjustment.
Final binary SHA-256:
`d860b50666ca920b339caa24860d6d2d3c1a6f829b926339f41ee04c5bbb5384`.
Final idle PNG SHA-256:
`60793a9f2a46d1487caddee7fa039c4b01261fa1426a66e3e403908d93b3f37d`.
Each PNG has a sibling log. This batch covers these five Full HD states;
it does not replace the remaining DPI/interaction/fidelity acceptance work.

## Historical comparison batch

NativeLab captures use the original Fiat Tipo MA1.7 ROM and the same
1920×1080 output size within each pair. `Before` is an earlier Lab GUI
capture; `current` is the present renderer. These files are local review
artifacts under `.work/` or `build-lab/`, not source assets.

| Scenario | Tick | Before | Current | Matched observation |
| --- | ---: | --- | --- | --- |
| Key off, engine stopped | 800,000 | [PNG](../.work/gui-review/matrix-stopped-1920x1080-t800000.png) | [PNG](../.work/gui-review/current-matrix-stopped-1920x1080.png) | CC3 0, burns 0; state `d1e2718727fb3e75` |
| Warm candidate bench idle | 800,000 | [PNG](../.work/gui-review/matrix-idle-1920x1080-t800000.png) | [PNG](../.work/gui-review/current-matrix-idle-1920x1080.png) | CC3 15, burns 13; state `d27a762aedb47d83` |
| Replayed 24 N·m load | 800,000 | [PNG](../.work/gui-review/matrix-replay-load-1920x1080-t800000.png) | [PNG](../.work/gui-review/current-matrix-replay-load-1920x1080.png) | CC3 10, burns 8; state `8340eaa036338ea4` |
| Replayed 60 N·m load and 25 mm pedal | 3,000,000 | [PNG](../.work/gui-review/matrix-high-load-1920x1080-t3000000.png) | [PNG](../.work/gui-review/current-high-load-1920x1080-t3000000.png) | CC3 59, burns 57; state `6f7b4dab705d0aba`, events `115c372e42957327` |
| Paused replay | 1,500,000 | [PNG](../.work/gui-review/matrix-paused-replay-1920x1080.png) | [PNG](../.work/gui-review/current-matrix-paused-replay-1920x1080.png) | CC3 30, burns 28; state `7b1a245fae2c534f`, events `be5cbae7309133bf` |

All five current PNGs and their `.log` files were refreshed in NativeLab.
The paused before/current pair uses the same replay fixture. All five pairs
have an identical full `[LAB-STATE]` line,
including tick, RPM, ROM state hash, event hash and overflow. The high-load
[log](../.work/gui-review/current-high-load-1920x1080-t3000000.log)
reports RPM `768.16553665648814`; the other state hashes appear in the
table. An RGB comparison of all five pairs found zero changed pixels in the
mechanical area `(462,90)–(1265,635)`.
Their dial and text changes therefore do not alter the rendered engine
poses in these fixed-tick captures.

All four capture scripts passed at 1920×1080 after the latest TBI validity,
scope navigation and gauge-label changes. The stopped and high-load current
frames were inspected for both engine views, gauge labels and analog traces.
`LabCapture.PausedReplay1920x1080` also passed. The paused pair's
[before log](../.work/gui-review/matrix-paused-replay-1920x1080.log) and
[current log](../.work/gui-review/current-matrix-paused-replay-1920x1080.log)
both report tick 1,500,000, RPM `997.65352684061327`, 175 events and
overflow zero, alongside the hashes in the table.

For the donor composition reference, compare the
[Open Engine Sim 1920×1080 frame](../.work/donor-gl-current-1920x1080.png)
with the [current Lab frame](../build-lab/sevel-1920x1080.png). They show
different engines and physical states, so this is a layout and visual-language
comparison only.

The [digital contact cursor capture](../build-lab/sevel-digital-idle-cursors-1920x1080.png)
uses the original ROM and the existing pedal replay. Its `IDLE SAMP` readout
marks the first observed OPEN/CLOSED snapshots at 0.505051 s and 0.909091 s;
the displayed difference is 404.040 ms. This is an interaction check, not a
same-scenario before/after pair.

The [Full HD digital navigation capture](../build-lab/sevel-digital-navigation-1920x1080.png)
and [1280×720 capture](../build-lab/sevel-digital-navigation-1280x720.png)
show the restored live view after a middle-button history drag and centered
wheel zoom. Their tests export separate CSVs before and after panning and
verify that the end tick moves backward without changing the ROM session.

Reproduce the stopped/idle/replay/high-load frames with
`tests/test_lab_resized_capture.py` and the corresponding `matrix-*` mode.
`LabCapture.PausedReplay1920x1080` refreshes the paused frame. NativeLab
passed five focused stopped, Full HD, high-load and paused-replay capture
tests after the current GUI changes.
