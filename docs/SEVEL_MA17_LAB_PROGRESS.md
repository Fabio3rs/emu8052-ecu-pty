# SEVEL MA1.7 Lab: execution ledger

## Baseline and provenance (2026-11-16)

| Item | Observed state | Reproduction / acceptance |
| --- | --- | --- |
| Destination | HEAD `3d8cbf37dacae1807b9a08354968698a71df4da4`; tracked tree clean before work | `git rev-parse HEAD; git status --short --untracked-files=no` |
| ROM | Local `FiatTipo_MA17_dump_27c256.bin`, SHA-256 `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`; ignored, never copy into Lab | `sha256sum FiatTipo_MA17_dump_27c256.bin` |
| Donor | `open-engine-sim` HEAD `1e226ee7bfbeb1d5012c7696aee82a57355df281`, MIT; submodules csv-io, Piranha, solver present | Inspect source and individual asset licenses before import |
| Reference | `engine-sim` HEAD `85f7c3b959a908ed5232ede4f1a4ac7eafe6b630`; comparison only | No build dependency on reference checkout |
| CLI baseline | CMake configuration succeeded with GTest; initial build failed at `tests/intake_fuel_test.cpp:456` under GCC 13 `-Werror=dangling-else`; braces added, subsequent build passed | `cmake -S . -B .work/baseline -DENABLE_TESTS=ON`; `cmake --build .work/baseline --parallel "$(nproc)"` |
| Tests | 229/230 passed under `-j 24`; `PhysicalDiagnostics.KlineFaultHistory` timed out waiting for K-Line `0x55` under load, then passed alone in 94.86 s. After adding geometry tests, 233/233 passed under `-j 4` in 236.10 s | `ctest --test-dir .work/baseline --output-on-failure -j 4` |
| NativeLab | Server cwd is this workspace; donor checkout is absent in its mount namespace. Temporary ignored copy at `.work/open-engine-sim` is visible | `.work/` is for intermediate copies and builds only |
| Donor build | Core and visualization libraries compiled. GCC desktop failed in Piranha; Clang desktop built with staged SDL3 3.2.8 source. Donor test target had unresolved GoogleTest symbols. `shadercross` absent, so shader generation was skipped | `.work/donor-clang-build/engine-sim-desktop` built under NativeLab |
| Donor runtime | `xvfb-run -a .work/donor-clang-build/engine-sim-desktop` exits 1: Vulkan reports no DRI3 presentation, then SDL GPU reports no supported backend | Use recording renderer or viable software/offscreen path for Lab captures; do not claim GUI image from this run |
| Lab regression | 264/264 CTest cases passed with the candidate bench preset and final-tick screenshot, `-j 4`, 262.38 s. The subsequent manual-start test passed alone; the now-265-case full suite has not been rerun after adding that test | `ctest --test-dir .work/lab-build --output-on-failure -j 4`; focused `-R 'LabSession.BenchPreset|LabControls.ManualBenchStart'` |
| Optional builds | Lab without GUI and original CLI without Lab compiled after TPS changes. Headless replay then built without SDL3 (verified by `ldd`) and generated SVG/WAV from the original ROM and saved controls | `.work/headless-lab-build/sevel-ma17-lab ... --headless --capture-tick 1200000 --replay-controls tests/data/lab_control_replay.txt --capture-svg .work/sevel-headless-replay.svg --capture-wav .work/sevel-headless-replay.wav` |
| Release build | `-DCMAKE_BUILD_TYPE=Release -DENABLE_TESTS=OFF -DENABLE_SEVEL_MA17_LAB=ON -DENABLE_SEVEL_MA17_LAB_GUI=OFF` built both the original CLI and Lab. Original-ROM replay at tick 1,200,000 matched debug state/event fingerprints; SVG had 94 polygons and the WAV had 53,459 mono 44.1 kHz frames, 29,643 nonzero samples, peak 25,798 | `.work/release-lab-build/sevel-ma17-lab FiatTipo_MA17_dump_27c256.bin --headless --capture-tick 1200000 --replay-controls tests/data/lab_control_replay.txt --capture-svg .work/release-lab-build/sevel-release.svg --capture-wav .work/release-lab-build/sevel-release.wav --idle-contact-p46 --idle-bridge-p15-p16 --adc7-mv 1232` |

## Vertical slices

| Slice | State | Files / dependency | Next executable check / acceptance |
| --- | --- | --- | --- |
| A. Graphics and audio transplant | Partial: donor `Renderer`/math, `Shaders` CPU state, original `SdlGpuRenderer` and shader assets, adapted `Gauge` and `Oscilloscope` state, `GeometryGenerator`, `AuthoredMeshLibrary`, authored OBJ, Silkscreen font and synthesizer/filter subset imported; Lab target builds with optional SDL3 | `third_party/open-engine-sim/`, CMake, notices | Merge donor GPU drawing with the primary UI and reuse more donor UI classes; Xvfb GPU success remains unverified |
| B. SEVEL mechanics | Partial: slider-crank plus SOHC shaft and eight valves from manual timing; the longitudinal view uses donor geometry and piston, rod, head and valve meshes, with crank throws drawn from SEVEL poses | `SevelGeometry`, `SevelValves`, `SevelSegments`, `DonorScene`, recording renderer | Improve visual polish; 0.14 m rod and 7 mm valve lift are drawing estimates only |
| C. Live MA1.7 session | Partial: original ROM runs in one worker, bounded recent-event vector ring, snapshots, pause/speed/pedal/load/starter/key controls, tick-target command queue, text control traces and replay test; v2 traces record ROM fingerprint and physical arguments, with v1 compatibility; GUI/headless state and event fingerprints match across audio and frame pacing; key-off freezes the CPU while crank, thermal state, intake film/vapor and exhaust continue to evolve; key-on reboots with retained XRAM; long key-off, starter and return-to-idle scenario passes | `SimSession`, observer callbacks, mutex; PTY retained | Validate more restart temperatures |
| D. Instruments and controls | Partial: three SDL3 software dials instantiate adapted donor `Gauge` objects for spring-damped needle state and use donor radial mapping; three-channel ECU oscilloscope instantiates adapted donor `Oscilloscope` rings and uses its `GeometryGenerator` path algorithm, with the last complete high-pulse width measured from event ticks; its CC3/P5 channel labels now toggle trace visibility; donor Silkscreen font labels the gauges, trends and scope; bounded five-second RPM/lambda snapshot trends, modeled TPS pair, lambda voltage, applied pedal/load, modeled fuel film/vapor, candidate lamp panel and donor-inspired 1–3–4–2 combustion indicators; keyboard and nine visible mouse controls adapted from donor `UiButton`, initialized from physical snapshots until the user overrides them; mouse wheel zoom and middle-button pan on a clipped mechanical view | `SdlDisplay.cpp`, `LabButtons.hpp`, `LabInstruments.cpp`, `DonorScene.cpp`, `EmulatorSnapshot.hpp`, `gauge.cpp`, `oscilloscope.cpp` | Improve sensor/status legibility and UI class reuse |
| E. Event-driven audio | Partial: donor Synthesizer receives combustion events; offline WAV and live SDL3 stream with mute and gain controls; separate PCM worker suspends on pause/key-off/>1×, bounds catch-up to recent 0.25 s and prebuffers 50 ms; 1× simulation uses an absolute wall-clock deadline with pause/speed rebasing; sliding event window stays aligned by absolute index; complete donor IR archived losslessly and 2048 exact PCM frames used at runtime; original-ROM idle/pedal/key-off WAV scenarios pass | `LiveAudio`, `StreamingAudio`, `SevelImpulse`, `WavWriter`, `SimSession`, audio tests | Validate real device playback and remaining queue starvation |
| F. Integration and polish | Partial: direct PNG screenshot under Xvfb and SDL dummy audio exercised; SDL selects the main 2D renderer with software fallback, and the optional donor GPU second window remains independent; headless and GUI Release builds pass with original-ROM replay/capture; README added | `.work/lab-build/sevel-live-audio.png`, `.work/release-lab-build/sevel-release-gui.png`, `.work/release-lab-build/sevel-release.wav` (ignored artifacts) | Verify GPU and audible playback on hardware; improve GUI usability and donor UI reuse |

## Immediate next slice

Next executable check: launch the Lab with one explicit candidate bench preset
and the original ROM, capture at a fixed tick, and require nonzero CC3 pulses,
burns and a PNG from the same run. Then repeat the preset headlessly and check
that recorded scenario metadata remains replayable. Keep the raw physical
scenario available when the preset is omitted.
This check now passes as `LabSession.BenchPreset`: at tick 3,000,000 the warm
candidate preset produced 130 CC3 pulses, 128 burns, 1,912.655 rpm and zero
event overflow. Headless and Xvfb GUI agreed on RPM and pulse count; the live
state/event fingerprints matched a fresh headless replay from its saved v2
control trace. The GUI saved a 1280×720 final-tick PNG after a shutdown-frame
fix. The image was inspected; it shows the running scene, instruments, traces
and four combustion indicators. At tick 12,000,000 without resistant load the
preset ran at 1,507 rpm, so it is a functional warm bench profile, not a
validated 850 rpm idle calibration. Load remains under user control.
The window now displays `WARM BENCH / CANDIDATE I/O` while the preset is
active. `LabControls.ManualBenchStart` used Xvfb/xdotool to click KEY, hold
START across 650,000 simulation ticks, then release it. The original ROM
burned fuel by tick 4,000,000, and a headless replay of the saved manual
control trace matched the GUI's complete state and event fingerprints.

Expand the live window from a schematic into a useful laboratory. Import the
donor's reusable UI or geometry components where dependency review permits.
The candidate-lamp panel, modeled TPS pair and saved control traces are now
available. Preserve the sole physical crank and ECU event stream. A replay
from recorded applied ticks reproduces the final physics state and ECU events
in a fresh session.

The user manual data source is `docs/SEVEL_COSIM_PROGRESS.md` (Fiat Tipo B.500.837, VIII/1993). Rod length, deck and outer dimensions remain unknown; any drawing parameter must be named `visual_estimate` and excluded from physics.

## Current executable proof

Configure with `cmake -S . -B .work/lab-build -DENABLE_TESTS=ON
-DENABLE_SEVEL_MA17_LAB=ON -DENABLE_SEVEL_MA17_LAB_GUI=ON
-DSDL3_DIR=$PWD/.work/donor-clang-build/_deps/sdl3-build` for the locally
staged SDL3 build, or let CMake fetch pinned SDL3 release 3.2.8. Build with
`cmake --build .work/lab-build --parallel 4`. The CLI-only default leaves
`ENABLE_SEVEL_MA17_LAB=OFF` and does not need SDL3.

Run `sevel-ma17-lab FiatTipo_MA17_dump_27c256.bin --live` for the SDL3 software
window. It begins with the key off: K turns it on, then S holds the starter.
Space pauses; arrows adjust pedal; L toggles a 24 Nm load; +/- changes
simulation rate; M mutes and brackets change volume; Esc closes. The mouse
wheel zooms the mechanical scene, middle-button drag pans it, and R resets the
view. `--auto-start` uses the earlier 495,000-tick starter demo. Live mode
defaults to a practical
1,000,000,000,000-tick ceiling; `--stop-ticks` can override it.
`--headless --capture-tick 10000000 --capture-svg .work/sevel.svg
--capture-wav .work/sevel.wav` writes geometry and WAV without opening SDL.
With SDL3 and libpng, `--screenshot .work/sevel-lab.png --window-frames 4`
writes a real 1280×720 window frame; CTest registers an Xvfb screenshot test
when both dependencies are available.
The original ROM remains ignored and local; the app does not package it.

NativeLab/Xvfb with SDL dummy output captured `.work/sevel-live-warm.png`
after tick 10 million under the documented warm scenario flags. The frame
showed about 826 rpm, 266 CC3 pulses, 264 burns, lambda 0.93 and three ECU
pin traces. The offline WAV has 445,459 mono 16-bit samples at 44.1 kHz,
0 clipped samples after gain adjustment and the short impulse; the original ROM run ended at
821.758 rpm. SDL dummy verifies queueing but cannot prove audible hardware
playback. The donor desktop SDL_GPU backend could not present under Xvfb due
missing DRI3, so the Lab uses SDL3's software renderer.

A second screenshot, `.work/sevel-lab.png`, shows the SOHC and valve timing
at exactly tick 10 million. The live warm-session test reproduces the headless
snapshot at that tick: 821.758 rpm, RAM `47h` = 32 and 266 CC3 pulses. The
audio and scene tests passed again after the latest buffer and valve changes.
After formatting and the PNG path, the focused Lab/SEVEL group passed 11/11.
The SDL window now generates its 47 mechanical strokes with the original donor
`GeometryGenerator::generateLine2d`; a Lab test compares the bounds of every
stroke against the prior scene across four crank phases. The focused donor,
scene, geometry and SDL screenshot group passed 6/6.
The key control was tested in `LabSession.PauseAndControls`: CPU PC and
fuel/burn counters remain still with the key off while crank RPM falls, then
the CPU resumes after key-on. The ignition and injector stages clear electrical
charge without restoring deliberately disconnected circuits. NativeLab/Xvfb
captured `.work/sevel-manual-start.png` with key off, zero RPM and no ECU pulses;
this verifies startup presentation, while the session test verifies transitions.
`LabSession.ControlReplay` runs two sequential sessions in one process using
the recorded applied ticks; exact RPM, angle, RAM 47h, PC, CC3/burn counts and
event identities matched. Resetting the global tick and PTY/UART run state
fixed the first replay failure. `LabAudio.EventDrivenWav` now compares a
sliding event window against continuous rendering. The GUI shows the count of
older events discarded from its bounded 65,536-event window.
The event window now uses a reserved `std::vector` as a circular buffer, so
the simulation callback does not allocate while appending events. A replay
test with capacity eight forced wraparound and matched its ordered tail and
overflow count against the full trace. Session, audio, mouse and replay checks
passed 5/5 after the change. The mutex still protects the simulation writer
and multiple GUI/audio readers.
`LabSession.GuiAudioFrameDeterminism` replays the same seven commands to tick
1,200,000 in headless mode and in three Xvfb GUI runs: 8 ms frames without
audio, 32 ms frames without audio and 32 ms frames with SDL dummy audio. All
four runs matched the complete snapshot fingerprint `8bbbb831e4070919`, the
ordered 127-event fingerprint `e195a0444ed3bc06`, zero overflow, 1,160.328
rpm, RAM `47h` = 47, 26 CC3 pulses and 24 burns. The focused GUI/audio/capture
group passed 9/9. This compares software and dummy-device execution on one
host; physical audio output remains unverified.
The SDL3 live audio worker is exercised under NativeLab/Xvfb with the dummy
device: `LabAudio.LiveDummyStream` observed 102 real CC3 pulses, zero dropped
samples and zero stream write errors. `LabAudio.PauseSpeedAndKey` verified worker
transitions and clean shutdown. The dummy run still observed 159 empty input
queue checks over 180 frames; that is a queue observation, not a verified
hardware underrun count. Playback starts after a 50 ms buffer and pauses above
1× rather than forcing the ECU clock to follow the device. Audible hardware
playback remains unverified.
The original relative wait added each 500-tick batch's full virtual duration
after its CPU work. In matched 180-frame NativeLab/Xvfb runs with SDL dummy,
9.09 s of wall time produced 5.71 million ticks and 372 empty-queue checks;
absolute-deadline pacing produced 9.07 million ticks in 9.21 s with 20 checks.
Five focused pause, replay, determinism and audio tests passed. These numbers
measure this host and dummy device only; a real sound device is unverified.
The headless Lab target rebuilt and `LabSession.HeadlessControlReplay` passed
after the pacing change.
After camera and instrument changes, the focused scene, PNG capture and
session-control checks passed 4/4. The PNG shows the candidate-lamp panel and
modeled TPS1/TPS2 voltages. A new session assertion confirms both modeled TPS
tracks rise with pedal input. The complete 248-case suite then passed under
NativeLab with the SDL dummy audio and Xvfb PNG checks enabled.
The instrument labels now use the packaged donor Silkscreen font instead of
SDL's debug font. NativeLab/Xvfb captured
`.work/lab-build/sevel-live-audio.png` with the live 749 rpm snapshot, three
ECU traces and the updated labels; the PNG and SDL dummy audio tests passed
2/2. This confirms rendering and queueing on the dummy device, not speaker
output.
The text control trace records applied key, starter, pedal and load commands
with exact ticks and 17-digit values. The original-ROM replay test loaded a
saved file and matched state/events, while an Xvfb GUI replay saved a
byte-identical seven-command trace and produced a live screenshot at tick
117,000. A no-SDL headless replay generated `.work/sevel-headless-replay.svg`
and `.work/sevel-headless-replay.wav`: 127 events, 53,459 mono frames at
44.1 kHz, 29,632 nonzero samples and zero clipped samples after reducing the
synthesizer gain to 0.08. New v2 traces embed the ROM size, a 64-bit FNV-1a
content fingerprint and the physical arguments, excluding the capture stop
tick. Replay rejects mismatches before starting; legacy v1 traces remain
readable and preserve their original format when saved again.
The live SDL screenshot `.work/lab-build/sevel-live-audio.png` now shows an RPM
and lambda trend panel built from recent snapshots alongside the three ECU pin
traces. The graph stores at most 600 copied points and only draws on windows
at least 1000×690. The focused PNG, SDL dummy audio and headless replay checks
passed 3/3 after the graph change; the 249-case full suite passed immediately
before it.
The ECU pin traces now use the donor Oscilloscope's `startPath` and
`generatePathSegment` geometry method through the unmodified donor generator.
The live PNG under Xvfb shows CC3 and both P5 traces after the change; the
focused SDL PNG and dummy-audio checks passed 2/2. The original pin-event
window is unchanged, and oversized traces retain an SDL line fallback.
The authored OBJ exported from the donor's `art/assets.blend` is now packaged
losslessly as zlib/Base64 in the Lab source tree; its decoded SHA-256 matches
the donor's original 918,973-byte file. `AuthoredMeshLibrary` loads it from an
in-memory stream. The SDL window initially drew donor piston, connecting rod
and crankshaft meshes at the four physical crank poses on top of the existing
SOHC/valve scene. The Xvfb screenshot `.work/lab-build/sevel-window.png` was
visually inspected: all four donor crank forms and pistons were visible at
tick 1,485,000. The mesh decode, donor scene (including imported triangle
counts) and PNG checks passed 6/6. The headless Lab and scene test also build
without SDL3 or ZLIB. The complete GUI-enabled CTest suite then passed
252/252 in NativeLab (227.44 s, four jobs).
The donor `Crankshaft` mesh was subsequently removed from the longitudinal
scene after comparing its planar coordinates and the fork's journal-angle,
depth-layer rendering. It is an axial silhouette, so repeating it beneath
each side-by-side cylinder gave the wrong projection. The continuous shaft
and four crank throws remain tied to the SEVEL poses. The updated 1280×720
PNG was inspected; the donor scene and bench-preset checks passed 5/5.
The same projection correction places each crank journal and rod on its
cylinder's longitudinal screen-space axis; the radial horizontal motion now
represents hidden depth. A scene test checks this at 90° crank angle, and the
updated bench-preset PNG was visually inspected. The focused scene, donor and
bench tests passed 7/7.
The complete GUI-enabled CTest suite then passed 266/266 under NativeLab in
259.30 s with four jobs after both projection corrections.
Two labeled axial insets now render the donor `Crankshaft` silhouette for the
1/4 and 2/3 pairs at opposite angles, driven by the same crank snapshot. The
updated 1280×720 bench PNG was inspected; a geometry test confirms the two
mesh transforms are opposed. SDL now chooses the primary 2D renderer and
logs its name, falling back to software on initialization failure. The Lab
also logs the opened SDL audio stream and driver. Focused axial, PNG, bench,
dummy-audio and GPU-fallback checks passed 5/5. Xvfb does not verify hardware
GPU presentation or audible playback; README includes a hardware run path.
The resized 900×620 capture and live mouse-control checks also passed 2/2
after SDL renderer selection changed. The last complete 266-case suite predates
the new axial test and renderer-selection change.
The complete GUI-enabled suite subsequently passed 267/267 with four jobs.
The oscilloscope's CC3, P5.0 and P5.1 legends now toggle each trace without
affecting ROM control replay. The GUI rebuilt, and focused capture, mouse
control and resized-window checks passed 3/3. Hardware presentation and
audible playback still await the owner's native display and sound test.
The donor `CylinderHead` mesh now sits behind the eight valve strokes at a
drawing-only scale. The updated screenshot was visually inspected; the head
and SOHC strokes remain visible. Focused scene and PNG checks passed 4/4.
The donor `Valve` mesh now renders for each of the eight valves. Each uses the
existing SEVEL timing lift and drawing scale, leaving the single schematic
camshaft visible. The triangle-count test and PNG capture passed 4/4; the
updated frame was inspected under Xvfb.
The donor's Silkscreen TTF is packaged losslessly, with its own redistribution
license copied beside the GUI asset. A new FreeType glyph-run renderer replaces
SDL debug text in the status panel; the Xvfb screenshot was visually checked.
The mesh, font-byte, scene, PNG and SDL dummy-audio checks passed 8/8 after
font integration. The headless Lab still configures and builds without the
GUI-only FreeType and ZLIB dependencies.
Recent combustion and misfire events now produce brief amber/red markers over
the corresponding cylinder in the live scene. They read the retained event
window and do not alter ECU pulse widths or simulation state. The live SDL
dummy-audio screenshot `.work/lab-build/sevel-live-audio.png` visibly shows
three combustion markers at tick 633,500. Focused scene, capture and audio
checks passed 6/6; a new scene test checks marker geometry and misfire color.
The SDL window now has a nine-button control strip below the engine. Its frame,
fill and hover/held states adapt the donor `UiButton` styling; the same
`SimSession` command path serves keyboard and mouse. The Xvfb screenshot
`.work/lab-build/sevel-live-audio.png` shows the strip. A real Xvfb/xdotool
click test saved `.work/lab-build/sevel-mouse-controls.txt` with key-on,
momentary starter, 1 mm pedal and 24 Nm load at applied ticks. `LabControls`
and the PNG/audio checks passed 3/3. Pause, speed and mute clicks were sent in
that test; the saved physical-control trace does not record wall-time actions.
The complete GUI-enabled suite passed 256/256 under NativeLab with four jobs
in 234.19 s after adding the button bar. A separate Xvfb replay test then
clicked all five physical buttons and confirmed its saved trace remained
byte-identical to `tests/data/lab_control_replay.txt` (1/1 pass). That test was
registered after the 256-case full run.
An Xvfb resize check captured a 900×620 PNG after changing the live window
size. The first capture exposed clipped status and lamp text; compact status
strings and a shorter lamp label now fit at that size. The resized frame was
visually inspected, and the resize, default PNG and both mouse tests passed
4/4 after the layout fix. The 256-case full run predates the two added
replay/resize tests and the compact text change.
The starter now releases on SDL window focus loss as well as mouse/key release,
so a lost release event cannot hold the virtual starter on. Build and the
mouse/replay/resize checks passed 3/3 after this guard.

The complete MIT donor `smooth_39.wav` is now archived losslessly in the Lab
tree. Runtime convolution uses its first 2048 exact PCM frames, containing
99.69% of the source energy. The 128-frame version contained only 0.0027%.
The audio target rebuilt, focused audio/PNG tests passed 4/4, and the offline
44.1 kHz WAV had 4410 frames, 3877 nonzero samples, peak 8552 and no clipped
samples. Real speaker playback remains unverified.
The complete 258-case CTest suite passed in 239.37 s after this change.
The donor `Shaders` CPU state module is now imported unchanged and supplies
object transforms and colors to all mechanical scene submissions. The target
built and the focused donor scene, SDL PNG and dummy-audio checks passed 6/6.
At that stage, the SDL software backend still lacked the donor's compiled GPU shaders.
Three live RPM/TPS/lambda dials now instantiate an adapted donor `Gauge` class
for needle dynamics. Its dependency on the donor application/UI tree was
removed; SDL still draws the radial geometry. Focused donor Gauge/scene, PNG
capture and dummy-audio checks passed 7/7. The captured 1280×720 PNG was
visually inspected with all three gauges present.
The live three-channel ECU trace now instantiates the adapted donor
`Oscilloscope` sample ring. Its raw arrays were replaced by `std::vector`;
the donor path generator still draws the resulting points. Focused donor
instrument/scene, PNG capture and dummy-audio checks passed 8/8, and the
captured PNG still shows all three ECU channels.
The full 260-case CTest suite passed in 238.39 s after both donor instrument
adapters were connected to the live display.
The original donor `SdlGpuRenderer` now compiles in an isolated GUI target.
HLSL/MSL sources and losslessly packaged SPIR-V/DXIL binaries are staged beside
the Lab executable; SHA-256 checks confirm the restored files match the fork.
`--live --gpu-preview` renders a second mechanical scene from the same
snapshot when SDL GPU initializes. NativeLab/Xvfb reported `No supported
SDL_GPU backend found!`; the primary software window still captured a visually
inspected 1280×720 PNG and the process exited 0. The focused GPU fallback,
software PNG and dummy-audio CTest cases passed 3/3. Successful GPU presentation
on a real device remains unverified.

The original-ROM audio scenario test runs the known physical idle setup twice,
then repeats it with an 8 mm pedal step at tick 10,000,000. The two idle WAVs
are byte-identical; the pedal WAV matches idle before the step and differs
after it. At tick 12,000,000, idle reached 962.6 rpm and pedal reached
1217.7 rpm. The post-step PCM RMS ratio was 1.50, with no clipped samples or
event overflow. A control trace switching the key off at tick zero produced
zero events and a silent WAV through tick 2,000,000. The focused
`LabAudio.OriginalRomScenarios` CTest passed in 23.60 s under NativeLab.
This verifies deterministic offline synthesis and control response; audible
playback on physical hardware remains unverified.
The oscilloscope now reports the last complete high interval for CC3, P5.0 and
P5.1 in milliseconds, using the 990,000-tick/s ROM clock. `H --` means no
complete rise/fall pair is available in the retained events. The GUI target
built, `LabCapture.SdlSoftwarePng` passed, and the 1280×720 PNG was visually
inspected. These are electrical high intervals; pin-function interpretations
remain candidates.
The snapshot now carries actual cable pull and applied resistant torque, so
the live pedal and LOAD controls follow command-line physical scenarios until
the user changes them. `LabSession.PauseAndControls`,
`LabControls.MouseButtonBar` and `LabCapture.SdlSoftwarePng` passed 3/3. A
NativeLab/Xvfb original-ROM run with an 8 mm pedal step and 24 Nm load at tick
100,000 produced a visually inspected live PNG at tick 633,500 showing
`pedal 8.0 mm`, `applied load 24 Nm` and LOAD selected. GUI, headless Lab and
CLI-only targets rebuilt successfully. The full 262-case suite passed in
244.58 s after the snapshot change. A follow-up session assertion also passed
with a command-line 8 mm pedal step and 24 Nm load.
The key-off path previously returned before thermal, intake and exhaust steps,
freezing coolant and fuel film while the crank coasted. An original-ROM
session now tests 3 million ticks of running and 5 million ticks after key-off:
coolant fell from 90.116 to 90.077 °C and modeled manifold film from
0.000013993 kg to zero, while PC, injection count and burn count stayed fixed.
The test failed before the fix and passed after it. Six focused GUI/session,
audio, replay and PNG checks plus the headless replay passed. A 1280×720
Xvfb capture at tick 3,000,000 shows the modeled 20.4 mg film and 66.4 mg
vapor readouts. GUI, headless Lab and CLI-only targets rebuilt. The complete
262-case suite passed in 254.66 s after this physics change.
The same session test now cycles the key on after the five-million-tick
cooldown. With the 24 Nm load removed during cranking, the original ROM resumes
injector pulses and combustion. Reapplying 24 Nm after the engine catches
brought the motor to 812 rpm at tick 15,500,000 in the focused CTest run; the
test requires 700–1100 rpm and zero event overflow. The load must be released
for this modeled starter to overcome resistance. This is a simulated bench
sequence, not a measured vehicle restart.
The donor's `FiringOrderDisplay` ring-and-light design now appears below the
mechanical scene in SEVEL 1–3–4–2 order. The lights use actual combustion and
misfire events from the recent event buffer, with red for misfire; drawing does
not advance simulation state. The donor contains one planar authored OBJ and
no separate 3D asset. GUI build and both focused Xvfb capture/live dummy-audio
tests passed 2/2. `.work/lab-build/sevel-live-audio.png` was visually inspected
at 1280×720 with the new indicators and a running original-ROM session. A GUI
Release build also passed; its Xvfb capture at tick 1,485,000 is
`.work/release-lab-build/sevel-release-gui.png`. After the paired-spark label
was added, focused capture and mode-determinism checks passed 2/2, and the
live dummy-audio test passed 1/1. The most recent complete suite before this
presentation-only patch was 263/263.

### Wasted-spark secondary circuit: evidence and model boundary

The SEVEL drawing now distinguishes **burns** (one compression cylinder per
event) from the **1/4 and 2/3 spark pairs**. The P5-to-pair binding remains a
candidate because the actual wiring has not been measured. The Lab's
`Ma17IgnitionStage` models primary-command charge duration and a normalized
spark strength; it does not calculate secondary voltage, plug-gap breakdown,
arc current or a voltage trace. Therefore the P5 oscilloscope is a command
trace, not a high-voltage measurement. The physically useful next model would
need per-gap pressure, temperature, gap and polarity, coil energy/impedance,
plus measurements of the actual coil and leads before assigning volts.

Experimental work by [Pashley et al. (SAE 2000-01-0245)](https://saemobilus.sae.org/papers/ignition-system-measurement-techniques-correlations-breakdown-arc-voltages-currents-2000-01-0245)
correlates breakdown with gap, gas composition, temperature and pressure, and
reports a separate, flow-dependent discharge voltage. [Lee et al. (SAE
2005-01-0231)](https://saemobilus.sae.org/papers/voltage-energy-deposition-characteristics-spark-ignition-systems-2005-01-0231)
measured distinct breakdown, arc and glow phases at 1–18 atm: the voltage falls
after breakdown but the conducting gap retains a finite voltage, not a zero-volt
short. [Irimescu et al. (SAE 2022-32-0009)](https://iris.polito.it/handle/11583/2974581)
distinguished compression from exhaust wasted sparks using secondary-current
duration, checked against pressure, in a small single-cylinder engine. These
papers support the qualitative model, not numerical calibration for this ECU.
The owner-supplied Bosch Motorsport [Double Fire Coil 2x2 datasheet](../Double_Fire_Coil_2x2_Datasheet_0221503407.pdf)
(part `0 221 503 407`, 2015; SHA-256
`faf64e0ad2166ded6f405f903676bbe7c4e2f6ff3867f364d19a1d89edef233a`)
describes two ECU power stages and a 3-pin low-voltage connector: pin 1 coil 2,
pin 2 battery, pin 3 coil 1. It lists 500 mΩ primary resistance with wire,
13.3 kΩ secondary resistance, 8 A maximum primary current, up to 70 mJ spark
energy, and a 35 kV maximum specified at a 1 MΩ/10 pF test load. Its dwell
table gives 2.4 ms to 5 A at 12 V and 1.9 ms at 14 V, explicitly without loom
resistance; Bosch says to verify dwell by measuring current. The exact coil
part installed on the Fiat Tipo is unconfirmed, so these values are a reference
for a possible future parameter set, not MA1.7 calibration. The table's 8 A
row reports 38.6 kV while the headline limit says 35 kV under a stated load;
we will not turn either number into a simulated secondary voltage without
resolving the test conditions.

## Temporary donor build reproduction

From this workspace, copy the local donor without Git or build caches into
`.work/open-engine-sim/`, and copy its cached SDL3 3.2.8 source into
`.work/sdl3-src/`. Both paths are ignored by Git. Then configure the copied
fork with Clang, `ENGINE_SIM_BUILD_DESKTOP=ON`,
`ENGINE_SIM_BUILD_SCRIPTING=ON`, `BUILD_TESTING=OFF`,
`ENGINE_SIM_FETCH_SDL3=ON` and
`FETCHCONTENT_SOURCE_DIR_SDL3=$PWD/.work/sdl3-src`; build with
`cmake --build .work/donor-clang-build --parallel 8` inside NativeLab.
The 8-job limit was used while the emulator suite ran concurrently.
