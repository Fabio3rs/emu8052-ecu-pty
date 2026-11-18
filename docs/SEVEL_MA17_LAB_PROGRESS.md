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
| Donor runtime | Original SDL_GPU desktop exits 1 under Xvfb: Vulkan needs DRI3. A temporary build of the fork's existing OpenGL ES renderer produced complete GUI frames at 1920×1080 and 3440×1440 with Mesa software rendering | `.work/donor-gl-1920x1080.png`, `.work/donor-gl-3440x1440.png`; this validates the temporary GL path, not SDL_GPU presentation |
| Lab regression | After the live SDL audio shortfall counter, 276/276 CTest cases passed in NativeLab with `-j 2`, 488.64 s; original-ROM, audio, GUI, K-Line, Full HD and ultrawide checks passed. A final overflow-safe counter edit was rebuilt and its four affected tests passed 4/4 | `cmake --build .work/lab-build --parallel 4`; `ctest --test-dir .work/lab-build --output-on-failure -j 2` |
| Optional builds | Lab without GUI and original CLI without Lab compiled after TPS changes. Headless replay then built without SDL3 (verified by `ldd`) and generated SVG/WAV from the original ROM and saved controls | `.work/headless-lab-build/sevel-ma17-lab ... --headless --capture-tick 1200000 --replay-controls tests/data/lab_control_replay.txt --capture-svg .work/sevel-headless-replay.svg --capture-wav .work/sevel-headless-replay.wav` |
| Release build | `-DCMAKE_BUILD_TYPE=Release -DENABLE_TESTS=OFF -DENABLE_SEVEL_MA17_LAB=ON -DENABLE_SEVEL_MA17_LAB_GUI=OFF` built both the original CLI and Lab. Original-ROM replay at tick 1,200,000 matched debug state/event fingerprints; SVG had 94 polygons and the WAV had 53,459 mono 44.1 kHz frames, 29,643 nonzero samples, peak 25,798 | `.work/release-lab-build/sevel-ma17-lab FiatTipo_MA17_dump_27c256.bin --headless --capture-tick 1200000 --replay-controls tests/data/lab_control_replay.txt --capture-svg .work/release-lab-build/sevel-release.svg --capture-wav .work/release-lab-build/sevel-release.wav --idle-contact-p46 --idle-bridge-p15-p16 --adc7-mv 1232` |

## Vertical slices

| Slice | State | Files / dependency | Next executable check / acceptance |
| --- | --- | --- | --- |
| A. Graphics and audio transplant | Partial: donor `Renderer`/math, `Shaders` CPU state, adapted `SdlGpuRenderer` and shader assets, adapted `Gauge` and `Oscilloscope` state, `GeometryGenerator`, `AuthoredMeshLibrary`, authored OBJ, Silkscreen font and synthesizer/filter subset imported; Lab target builds with optional SDL3; offscreen SDL_GPU scene readback passes | `third_party/open-engine-sim/`, CMake, notices | Merge donor GPU drawing with the primary UI and reuse more donor UI classes; verify presentation on hardware |
| B. SEVEL mechanics | Partial: slider-crank plus SOHC shaft and eight valves from manual timing; the longitudinal view uses donor geometry with piston and valve meshes, while the four-section and focused axial views use donor crank, rod, piston, head and valve meshes; all poses follow the physical SEVEL crank | `SevelGeometry`, `SevelValves`, `SevelSegments`, `DonorScene`, recording renderer | Improve visual polish; 0.14 m rod and 7 mm valve lift are drawing estimates only |
| C. Live MA1.7 session | Partial: original ROM runs in one worker, bounded recent-event vector ring, snapshots, pause/speed/pedal/load/starter/key controls, tick-target command queue, text control traces and replay test; v2 traces record ROM fingerprint and physical arguments, with v1 compatibility; GUI/headless state and event fingerprints match across audio and frame pacing; key-off freezes the CPU while crank, thermal state, intake film/vapor and exhaust continue to evolve; key-on reboots with retained XRAM; long key-off, starter and return-to-idle scenario passes | `SimSession`, observer callbacks, mutex; PTY retained | Validate more restart temperatures |
| D. Instruments and controls | Partial: three SDL3 software dials instantiate adapted donor `Gauge` objects for spring-damped needles, sweep and major/minor ticks; three-channel ECU oscilloscope instantiates adapted donor `Oscilloscope` rings and uses its `GeometryGenerator` path algorithm, with the last complete high-pulse width measured from event ticks; its CC3/P5 channel labels toggle trace visibility; donor Silkscreen font labels the gauges, trends and scope; bounded five-second RPM/lambda snapshot trends, modeled TPS pair, lambda voltage, applied pedal/load, modeled fuel film/vapor, candidate lamp panel and donor-inspired 1–3–4–2 combustion indicators; keyboard and nine visible mouse controls adapted from donor `UiButton`, initialized from physical snapshots until the user overrides them; mouse wheel zoom and middle-button pan on a clipped mechanical view, with four selectable mechanical views | `SdlDisplay.cpp`, `LabButtons.hpp`, `LabInstruments.cpp`, `DonorScene.cpp`, `EmulatorSnapshot.hpp`, `gauge.cpp`, `oscilloscope.cpp` | Improve sensor/status legibility and UI class reuse |
| E. Event-driven audio | Partial: donor Synthesizer receives combustion events; offline WAV and live SDL3 stream with mute and gain controls; separate PCM worker suspends on pause/key-off/>1×, bounds catch-up to recent 0.25 s and prebuffers 50 ms; a queued backlog of 0.5 s is cleared so current events replace stale playback; 1× simulation uses an absolute wall-clock deadline with pause/speed rebasing; sliding event window stays aligned by absolute index; complete donor IR archived losslessly and 2048 exact PCM frames used at runtime; original-ROM idle/pedal/key-off WAV scenarios pass | `LiveAudio`, `StreamingAudio`, `SevelImpulse`, `WavWriter`, `SimSession`, audio tests | Validate real device playback and remaining queue starvation |
| F. Integration and polish | Partial: main-window PNG and offscreen SDL_GPU scene PNG captured; SDL dummy audio exercised; SDL selects the main 2D renderer with software fallback, and the optional donor GPU second window remains independent; headless and GUI Release builds pass with original-ROM replay/capture; README added | `.work/lab-build/sevel-offscreen-gpu-main-gpu.png`, `.work/release-lab-build/sevel-release-gui.png`, `.work/release-lab-build/sevel-release.wav` (ignored artifacts) | Verify GPU presentation and audible playback on hardware; improve GUI usability and donor UI reuse |

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
Space pauses; arrows adjust pedal; L toggles the selected load; +/- changes
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
The GUI now shows internal `RAM27/28`, raw published `F84E–F850`, raw history
`F85E–F860` and the candidate lamp as separate observations. The new XRAM
bytes come from the same simulation-thread snapshot and enter its diagnostic
state fingerprint. A NativeLab/Xvfb original-ROM run with the candidate bench
preset opened ECT at tick 10,000,000 and restored it at 14,000,000. At tick
15,500,000, `.work/lab-build/sevel-ect-history.png` visibly showed
`RAM27/28=08/00`, published `08/00/00`, history `00/08/00` and lamp off.
The final tick-16,000,000 console trace reported the same banks. GUI bench,
replay, 900×620 and Full HD checks passed 4/4; the original CLI rebuilt and
`PhysicalDiagnostics.RawFaultBanks` passed after the snapshot change. The
headless Lab rebuilt without SDL3 and its control-replay check passed.

On 2026-11-17, a fresh GUI-only configure/build in `.work/fresh-gui-build`
passed with the local SDL3 3.2.8 build. A 180-frame NativeLab/Xvfb run of
the original ROM with dummy audio, `--auto-start` and `--bench-preset`
captured `.work/fresh-gui-build/verify.png` and exited with zero event
overflow, audio drops and audio write errors. The GUI executable now copies
shared SDL3 beside itself on Linux and uses `$ORIGIN` in its RUNPATH. A copy
of the executable, assets and SDL3 library in `.work/relocation-check/` ran
for 60 frames with `LD_LIBRARY_PATH` unset and captured `verify.png`; `ldd`
resolved SDL3 from that copied directory. This checks relocation on the
NativeLab host, not compatibility with other Linux distributions.

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
The SDL3 documentation confirms `SDL_GetAudioStreamQueued` counts input bytes
and `SDL_ClearAudioStream` removes pending data. The worker now pauses and
clears a 44,100-byte (0.5 s mono S16) backlog, counts discarded samples, then
prebuffers current PCM before resuming. A focused dummy-device test forced a
paused-device backlog and observed recovery; `LabAudio.PauseSpeedAndKey` and
`LabAudio.LiveDummyStream` passed 2/2, and the original-ROM session
determinism check passed. A real device may have additional hardware latency.
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
The GUI now exposes a direct 0–25 mm pedal slider on the right panel; the
mouse-control test verifies a dragged value reaches the saved physical
command trace. The 900×620 status overlay was shortened to avoid covering
the engine. NativeLab/Xvfb captures passed at 900×620, 1920×1080 and
3440×1440; the corresponding ignored PNGs are in `.work/lab-build/`.
The donor desktop build still fails to present under Xvfb because SDL_GPU's
Vulkan backend reports missing DRI3. A temporary `.work/open-engine-sim/`
copy ran with `SDL_VIDEODRIVER=offscreen` and yielded a 640×540 mechanical
scene readback at `.work/donor-scene.png`. Its full swapchain/UI readback was
white in this backend, so this artifact supports a mechanical-scene
comparison only, not a comparison of the donor's complete desktop UI.
Rechecked the unmodified donor with `LIBGL_ALWAYS_SOFTWARE=1` under Xvfb:
it still exits 1 because Vulkan reports no DRI3 presentation and SDL_GPU
finds no supported backend. In the temporary offscreen copy, disabling the
UI pass preserves the mechanical scene, while drawing just its first
one-pixel border turns exactly the upper half of the readback white. This
isolates the invalid full-frame capture to the offscreen UI path; it does
not establish what the GUI would look like on a real GPU.
The later Xvfb/OpenGL ES captures in the temporary donor build do show the
complete GUI; they use the fork's web renderer and are documented below.
Visual inspection confirms the donor scene is an axial view of a V engine,
whereas the Lab's main scene is a simultaneous front view of four inline
cylinders. The Lab's separate 1/4 and 2/3 axial icons are the comparable
orientation cues; the main scenes cannot be overlaid cylinder for cylinder.
The Lab now has a drag-capable volume slider between the RPM and TPS/LAM
gauges, sharing the keyboard volume and mute gain. Its 900×620, 1920×1080
and 3440×1440 captures were inspected after the change; four focused Xvfb
capture and mouse-control tests passed.
The fork's `CrankshaftObject` applies each journal angle as a rotation around
the shaft axis. The Lab's paired axial silhouettes follow that same transform
with 180° separation. They now remain visible as compact 1/4 and 2/3 panels
at 900×620, where they previously disappeared; the refreshed small-window
and Full HD captures were inspected, and both resize checks passed.
The longitudinal scene projects crank-pin lateral motion into depth, so its
rods appear vertical while the axial panels show shaft rotation. A new
720° kinematic regression checks every degree: each rod remains 0.14 m long
(a drawing estimate), its angled endpoint reaches the piston pin, cylinders
1/4 and 2/3 remain in phase within each pair, and the cycle seam matches.
The focused `SevelGeometry.*` group passed 4/4 in NativeLab.
The candidate-lamp and warm-bench panels now scale with the same GUI factor
as the text and gauges. The refreshed bench, 900×620, Full HD and ultrawide
captures were inspected; four focused CTest cases passed after the change.
The Xvfb mouse-control test now clicks the live volume slider, saves a PNG,
and checks the filled and unfilled bar pixels with a standard-library PNG
decoder. Its capture shows `VOLUME 25%` while physical controls still reach
the ROM session; `LabControls.MouseButtonBar` passed. A fresh dummy-audio
run observed 16 empty stream-queue checks, zero dropped samples and zero
write errors over 180 frames; this does not measure speaker underruns.
The complete GUI-enabled suite passed 269/269 in 270.68 s with four jobs
after the volume and panel changes. The Lab now converts mouse coordinates
through SDL3's renderer API for scaled windows. Scrolling over the scope
changes its visible span between 0.25 and 4 s; scrolling elsewhere still
zooms the engine. A live Xvfb capture visibly shows the 1 s scope and ECU
edges; focused mouse, Full HD capture and GUI/audio determinism tests passed
3/3 after the change.
The paired axial crank panels now grow with the GUI scale in Full HD and
ultrawide while retaining compact 64 px panels at 900×620. Refreshed PNGs at
all three sizes were inspected; the focused bench and resize group passed 4/4.
The Lab's Silkscreen text now scales with the window (capped at 2×) for
status, controls, pedal and gauges; the three scope selectors expand with
their labels so clicks still match the visible regions. The resize capture
waits until tick 1,500,000 after the window change and checks decoded PNG
alpha on every row, catching a previously observed partial transparent
frame. Five focused GUI/bench checks passed with three jobs, and the
900×620, 1920×1080 and 3440×1440 captures were visually inspected.
The complete GUI-enabled NativeLab suite then passed 269/269 with four jobs
in 268.75 seconds after these layout and capture changes.
The three resize captures now run the original ROM with automatic starter and
the warm candidate preset. The test requires nonzero CC3 pulses and burns in
the final state as well as a fully opaque PNG at the requested size. Under
NativeLab/Xvfb the 900×620, 1920×1080 and 3440×1440 tests passed 3/3 in
11.84 seconds. Full HD and ultrawide captures at tick 1,500,000 were visually
inspected: both show the running engine, around 1,530 rpm, 48 CC3 pulses,
41 burns and populated ECU traces. This replaces the earlier key-off resize
images; Xvfb still cannot validate hardware GPU presentation or audible sound.
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

On 2026-11-17, the current donor checkout at
`1e226ee7bfbeb1d5012c7696aee82a57355df281` was copied without Git or
build caches into `.work/donor-current-src/`. NativeLab configured and built
its `engine-sim-desktop` target in `.work/donor-current-build/` with Clang,
Ninja, scripting and the cached SDL3 3.2.8. The binary exited under Xvfb:
Vulkan reported no DRI3 support and SDL reported no supported GPU backend.
An earlier comparison used the donor's versioned
`docs/public/screenshots/screenshot_v01.png`; it depicts a Kohler V2 and
cannot validate SEVEL four-cylinder geometry. A later temporary build of
the fork's existing WebGL/OpenGL ES renderer under Xvfb generated complete
live GUI frames at `.work/donor-gl-1920x1080.png` and
`.work/donor-gl-3440x1440.png`. Those frame-30 captures show the fork's
GM LS example at 0 rpm, so they validate its layout and mechanical drawing
path but do not prove running-engine animation or the original SDL_GPU path.
This diagnostic copy changes only `.work/open-engine-sim/`: its desktop
target links `GLESv2` and uses the existing `WebGlRenderer`, the SDL window
requests OpenGL ES 3, and a temporary `glReadPixels` hook writes PPM at a
chosen frame. Build it with the cached SDL3 configuration:

```sh
cmake -S .work/open-engine-sim -B .work/donor-gl-build -DCMAKE_CXX_COMPILER=/home/fabio/.llvm/toolchains/llvmorg-23.1.2/bin/clang++ -DENGINE_SIM_BUILD_DESKTOP=ON -DENGINE_SIM_BUILD_SCRIPTING=ON -DBUILD_TESTING=OFF -DSDL3_DIR="$PWD/.work/donor-clang-build/_deps/sdl3-build"
cmake --build .work/donor-gl-build --target engine-sim-desktop --parallel 8
xvfb-run -a -s '-screen 0 1920x1080x24' env SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1 ENGINE_SIM_GL_FRAME=30 ENGINE_SIM_GL_CAPTURE="$PWD/.work/donor-gl-1920x1080.ppm" .work/donor-gl-build/engine-sim-desktop
xvfb-run -a -s '-screen 0 3440x1440x24' env SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1 ENGINE_SIM_GL_WIDTH=3440 ENGINE_SIM_GL_HEIGHT=1440 ENGINE_SIM_GL_FRAME=30 ENGINE_SIM_GL_CAPTURE="$PWD/.work/donor-gl-3440x1440.ppm" .work/donor-gl-build/engine-sim-desktop
```

Pillow converted the PPM readbacks to PNG for inspection. The temporary
hook is a capture aid, not part of the vendored product renderer.
Compared with the Lab's captures at the same resolutions, the donor has a
dense grid of bright instrument borders around a central V-engine view;
the Lab allocates its wider inline-four scene, MA1.7 controls and ECU traces
to separate regions. Both layouts occupy the Full HD and ultrawide frames.
The radial cylinder plane in the donor remains a different view from the
Lab's main shaft-longitudinal view; the Lab's radial selector and axial
1/4–2/3 icons are the relevant orientation comparisons.
The Lab's ultrawide view
now uses its spare lower scene area for coolant, load and fuel-film gauges,
all read from the simulation snapshot; both large capture tests passed 2/2.
`LabKline.LivePtyFaultQuery` also passed with a published ECT fault bank and
the original ROM's `02 0A 1E` K-Line response in the live GUI process.

The donor's `CrankshaftObject` renders one radial silhouette per journal,
rotated by `getRodJournalAngle(i)`. Its `ConnectingRodObject` and
`CylinderHeadObject` also use the radial cylinder plane. The Lab previously
overlaid their authored meshes on the longitudinal four-cylinder view, making
rod-end rings and a stretched head appear at the wrong orientation. That view
now uses the existing projected rod and SOHC head geometry, plus donor piston
and valve sections; the donor crank silhouette remains in the separate 1/4
and 2/3 axial panels. Both 1920×1080 and 3440×1440 captures were inspected
after the correction, and five `DonorScene` tests plus the two captures passed
7/7. The small axial panels show the crank throws in shaft mode.
The full NativeLab suite passed 271/271 in 272.63 s after this correction.

The V key or the clickable selector above the motor now switches the main
viewport to four juxtaposed radial sections.
Each section uses the donor crank, rod-end and piston meshes, while the rod
shank connects `CylinderPose`'s crank and wrist-pin positions. The crank mesh
rotates with the physical crank angle; the rod-end mesh follows its computed
tilt. Section spacing is an isolated visual layout estimate of 0.12 m and is
not presented as Fiat cylinder spacing. The small axial panels hide in radial
mode. NativeLab/Xvfb captures at 1920×1080 and 3440×1440 were inspected and
their tests passed 2/2. `LabControls.RadialViewMouse` also passed under Xvfb,
confirming that the selector changes the live window view. The donor desktop
binary was run again under 1920×1080 Xvfb and exited before window creation:
Vulkan reported missing DRI3 and SDL3 found no GPU backend. Its versioned
Kohler V2 screenshot remains the donor visual reference, not a live capture.
`DonorScene.RadialRodFollowsCrankAndOpposedPairs`
passed at TDC, 90° and 720°; this rendering does not advance the ROM or motor.
The radial scene now uses the same timestamped combustion/misfire afterglow as
the longitudinal scene. The rebuilt radial renderer and GUI passed the focused
geometry, 1920×1080, 3440×1440 and mouse-selector tests 4/4. Immediately
before this change, the full GUI CTest suite passed 275/275 in 267.07 s with
four jobs; that full run used the prior binary.
Hardware GPU and audible output remain for direct validation.

The ignition stage now emits a separate `Spark` event only when a connected
coil releases sufficient modeled charge. It carries the candidate 1/4 or 2/3
pair after the optional channel swap. The firing-order panel gives both
cylinders a short cyan ring at the same tick; the existing burn/misfire marker
remains tied to the compression cylinder and actual fuel event. This represents
simultaneous wasted-spark electrodes, not measured plug voltage or pressure.
The original-ROM `LabSession.PauseAndControls`, GUI/audio frame determinism,
both 1920×1080 captures and coil-binding unit test passed 5/5 after this
change; the headless CLI and Lab targets also rebuilt successfully.
The related ignition-stage/combustion, replay and live K-Line tests passed
13/13 under NativeLab.
The combustion/misfire afterglow was shortened from 150 to 50 ms, and the
stage-spark ring from 50 to 25 ms. At about 1,500 rpm, firing events are roughly
20 ms apart; the old 150 ms marker made all four cylinders look active at once.
The new 1920×1080 and 3440×1440 shaft/radial screenshots were visually checked:
recent burn markers no longer fill all four cylinders. All four capture tests
passed 4/4 after the adjustment. Electrical pulses retain their original
timestamp and width.
The full-suite GUI capture initially failed under four-way load because its
240-frame limit closed the window before tick 1,500,000. Raising the frame
limit alone let the live session run until the script's wall-time timeout.
The capture harness now sets `--stop-ticks 1500000` alongside
`--capture-tick 1500000`; all four large captures passed concurrently 4/4,
and the complete rebuilt suite then passed 275/275.
The firing-order panel now derives its P5.0/P5.1-to-pair labels from recent
successful `Spark` events, so the text reflects the active candidate coil swap
instead of assuming a fixed mapping. The 1920×1080 and 3440×1440 shaft and
radial captures were inspected after this change; all four capture tests plus
GUI/audio frame determinism passed 5/5. The rendering reads event copies and
does not alter the simulation tick stream.
The shaft and radial scenes now draw a separate cyan spark glyph at both
cylinders of the active 1/4 or 2/3 pair. The glyph consumes the existing
timestamped `Spark` event afterglow; a yellow/red combustion marker still
belongs only to the compression cylinder. The new geometry test checks both
spark gaps and one burn in the shaft view; the radial mesh test checks the
additional pair. A NativeLab build and 11 focused donor-scene/Full HD/
ultrawide capture tests passed. Visual inspection of the 1,500,000-tick
captures confirmed simultaneous cyan marks on cylinders 2/3. The radial
symbols were moved clear of the cylinder labels after the first screenshot.
The MA1.7 status overlay now has a bounded dark panel and distinct muted
colors for operating state, ECU pins and diagnostic banks. The panel uses four
lines at 900×620 and six at larger sizes, with its lower edge above the
mechanical scene. A NativeLab rebuild and six Xvfb capture/view-control tests
passed, covering 900×620, 1920×1080 and 3440×1440 in shaft and radial modes.
The resulting PNGs were inspected for legibility and overlap. This is a GUI
presentation change; it does not read or mutate ECU state beyond the existing
snapshot.
The LOAD button now acts as a 0–60 Nm horizontal control when clicked or
dragged, while the L key still toggles the previous nonzero setting (24 Nm
initially). Its label and fill bar show the requested torque; the ultrawide
load gauge uses the same 60 Nm scale. Mouse commands continue through
`SimSession::set_load` and the applied-tick trace. The NativeLab mouse test
recorded about 8 and 50 Nm from one drag and verified the later screenshot's
filled bar. Seven GUI control/layout tests passed with two parallel workers;
the session pause, replay and headless replay tests passed 3/3. A four-worker
run had one Xvfb window disappear before ultrawide resize; that test passed
alone and in the subsequent two-worker group.
The audio diagnostics now separate queued samples intentionally discarded on
key-off, pause or >1× (`mode skip`) from samples lost when the worker catches
up or clears a lagging playback queue (`lag`). The worker counts a mode skip
only after `SDL_ClearAudioStream` succeeds. In the Xvfb mouse-control capture
after speed and mute changes, the GUI showed `lag 0`, `mode skip 2704`, and
`empty 0`. The dummy stream, forced mode transition/backlog, GUI/audio
determinism and mouse-control tests passed 4/4 after the change; a separate
dummy run confirmed zero mode skips during uninterrupted playback. The
`empty` counter remains an observation of SDL's input queue, not a measured
hardware underrun. The last complete suite was 276/276 before this diagnostic
split; the focused tests cover its affected path. The forced transition test
also passed five consecutive NativeLab repetitions.
The live stream now registers SDL3's get callback solely to count the
approximate S16 samples requested while playback is active and unavailable
from the stream (`need`); it never synthesizes PCM on the audio callback.
Callback removal is idempotent across explicit stop and destruction. The
first run exposed a use-after-free when removal happened twice; after that
fix, the four affected NativeLab tests passed 4/4. The dummy-audio GUI run
reported `need=732` at shutdown and its 1280×720 PNG remained legible.
Because SDL can overestimate requested bytes, this is a stream shortfall
estimate, not a verified speaker underrun count.
The full NativeLab suite passed 276/276 in 488.64 seconds with two jobs after
the callback change. An overflow-safe conversion in the callback was rebuilt;
the four affected audio, GUI and mouse tests passed again on that final binary.
The optional SDL_GPU scene preview had a hidden stage mismatch: radial and
axial donor submissions used stage zero, while the donor GPU renderer filters
for `Shaders::SceneStage`. The recording renderer now counts scene-stage draw
calls, and the donor-scene tests require every shaft, radial and axial draw
to carry that stage. The Lab rebuilt and the seven donor-scene tests, both
radial Full HD/ultrawide captures, and the GPU fallback check passed 10/10.
The radial 1920×1080 PNG was inspected again; this Xvfb result validates the
software path and geometry, while actual GPU presentation still awaits the
owner's hardware check.
The view selector is now clickable at the compact 900×620 size. It sits in
the gap between the RPM gauge and volume control, rather than over the
cylinders; the V key remains available. A new Xvfb mouse test clicked it and
captured `.work/lab-build/sevel-radial-mouse-compact.png`, which was inspected.
The resized capture, existing Full HD mouse control, and all four Full HD/
ultrawide shaft and radial captures passed 7/7 after the change.
`SimSession::step_ticks` now advances an exact number of machine-cycle ticks
while paused, including a pause before the first batch. The worker chooses
partial batches without changing the CLI's normal 500-tick batch size.
The session test stepped 7 and 1,203 ticks, held the resulting snapshot still,
then matched PC, RAM47, event counts, RPM and crank angle against a continuous
run stopped at the same tick. The GUI's `.` key requests 9,900 ticks (10 ms)
while paused; the Xvfb mouse/keyboard test checked the title's exact tick
change. Pause/control, replay, GUI/audio determinism and mouse tests passed
4/4 after this addition.
The paused-at-start test also covers cancellation without executing a batch.
A starter-held sequence with a 7-tick first batch then 500,003 more ticks
matched continuous execution at tick 500,010; starter lookahead now uses the
normal batch size so a short step cannot release it early.
Paused sessions can now advance by exact milliseconds or to the first event
of a requested type within a tick limit. Event callbacks shorten the current
batch at the event's real tick, and the next snapshot remains there until
another command arrives. The original-ROM test stopped on an ignition pin,
matched PC, RAM47, injector/burn counts, RPM and crank angle against a
continuous run at that event tick, then advanced 3 ms (2,970 ticks) and
exercised a three-tick event limit. The GUI's `,` key seeks the next ignition
pin edge with a one-second virtual limit; its Xvfb test also covers a stopped
engine where the limit is reached without a new edge. The session and GUI
mouse tests passed after these changes.
The three core `SimSession` tests were moved outside the GUI-only CMake block,
so a headless build registers pause/control, warm-scenario and replay tests
without SDL. An isolated `.work/asan-lab-build` with the repository's
`ENABLE_SANITIZERS=ON` built the pause and replay targets; both passed under
ASan/UBSan after the pause test's wall-time wait was raised from 5 to 30 s
for instrumented execution. `ldd` found ASan and UBSan but no SDL dependency.
The sanitizer build exposed one `-Werror=sign-conversion` in optional port
latch logging; an explicit unsigned conversion fixed it. A separate TSan
headless build compiled, but its runtime aborted before the ROM started with
`FATAL: ThreadSanitizer: unexpected memory mapping`, both as PIE and non-PIE.
No TSan race conclusion can be drawn from this NativeLab environment.
After the CMake relocation and port-log cast, the normal GUI build completed
and the complete NativeLab suite passed 277/277 with `ctest --test-dir
.work/lab-build --output-on-failure -j 2` in 477.14 seconds. This includes
the new compact radial selector, paused stepping, GUI/Xvfb captures, audio
dummy, K-Line and the original emulator regressions.
An isolated `.work/asan-gui-build` then compiled the SDL Lab and live-audio
test with `ENABLE_SANITIZERS=ON`. The first Xvfb runs exited at LeakSanitizer
shutdown because `/opt/amdgpu/lib/x86_64-linux-gnu/libGLX_mesa.so.0` retained
108,124 bytes in 481 allocations; no invalid-access or UBSan report appeared.
With `.work/lsan-mesa.supp` containing only `leak:libGLX_mesa.so.0`, the PNG,
SDL dummy stream, pause/speed/key audio, mouse controls, and 1920×1080 and
3440×1440 captures passed 6/6 under ASan/UBSan. The sanitized build also
exposed signed arithmetic warnings in the packaged mesh Base64 decoder;
explicit unsigned conversion fixed them. The normal build's three mesh/font
asset tests passed 3/3 after that edit. This tests Xvfb and SDL's dummy audio
device, not a physical GPU or speaker.

The Lab now has the donor's fullscreen control pattern: F and F11 call SDL3's
`SDL_SetWindowFullscreen`, and a visible F: FULL button sits beside the view
selector at 1280×720 and larger. The button is omitted in the compact layout.
The NativeLab build and four Xvfb capture/layout tests passed after this
change, including 900×620, 1920×1080, 3440×1440 and radial mouse selection.
The new Full HD screenshot was visually checked for button placement. A
separate Xvfb/xfwm4 geometry probe did not establish a reliable fullscreen
round trip: X11 window IDs and window-size reporting changed asynchronously
after the keystrokes. The actual fullscreen transition still needs a desktop
hardware check.

The `SimSession` worker now shortens a batch when a queued control targets a
tick inside the normal 500-tick batch. This also applies while stepping a
paused session, so an already scheduled control is applied at its requested
tick instead of the following batch boundary. The ROM replay test now starts
the starter at tick 50,007 and checks the recorded applied tick; the paused
session test applies load at tick 500,007 during a 500,003-tick step and
compares its final state with a continuous run. `LabSession.ControlReplay`,
`HeadlessControlReplay` and `PauseAndControls` passed after the change. A live
command submitted after its target tick remains recorded at the real later
application tick. Pause, resume and step requests themselves still need to
enter the replay trace.
The corresponding headless `LabSession.ControlReplay` and
`PauseAndControls` tests also passed 2/2 under ASan/UBSan.

Pause, resume, exact-tick steps and event-bounded steps now use the same
applied-tick trace as physical controls. Live actions are recorded when the
worker reaches a batch boundary or while it is stopped on the condition
variable; replay applies the typed commands without wall-time waits. The
six event types are supported. Existing v1/v2 trace headers remain readable.
A replay test schedules pause at tick 50,000, steps seven ticks and resumes at
50,007. The live session test records pause, two tick steps, ignition and
combustion event steps, and resume, then replays that history to the same
PC, RAM47, injector/burn counts, RPM and crank angle. The Xvfb mouse test
also saves the GUI trace and replays it headless to a byte-identical trace
and identical state/event fingerprints at the GUI's final tick. Focused
normal tests passed 5/5; the two headless session tests passed 2/2 under
ASan/UBSan. Steps larger than 2^53−1 ticks are rejected because the trace's
numeric value field cannot represent them exactly.
The worker also releases a paused snapshot at its configured `--stop-ticks`
boundary, because the emulator checks that stop condition after the snapshot
callback. A replay ending paused at exactly tick 50,000 now finishes normally;
`LabSession.ControlReplay` covers this case.
After the terminal-pause fix, both session tests passed again under
ASan/UBSan (2/2).

The complete pre-change NativeLab CTest suite passed 277/277. A fresh build
of the fork's existing OpenGL ES desktop host captured its frame 30 at
1920×1080 and 3440×1440 under Xvfb software rendering in
`.work/donor-gl-current-*.png`. The captures show the donor's GM LS V engine
at 0 rpm and were compared with the Lab's shaft and radial captures; they
establish layout and mesh orientation, not running SEVEL animation or GPU
hardware behavior. The Lab's radial view now reuses the donor's `CylinderHead`
and `Valve` meshes alongside its crank, rod and piston meshes. The head meshes
form a continuous inline silhouette, and the valves follow SEVEL phases.
Full HD and ultrawide radial captures were inspected after adjusting the tall
window framing to keep crankweights above the lower gauges. The nine focused
donor scene/capture tests passed; both capture tests passed again after the
final framing adjustment. Software Xvfb remains the only visual backend
verified here; the user will check hardware graphics and audio.
The radial scene test also checks that the first intake valve visibly moves
down at its opening phase relative to the closed phase.

The primary SDL3 window now submits the software scene in ordered batches of
2,730 triangles using per-vertex color, instead of one `SDL_RenderGeometry`
call per triangle. The radial scene contains about 75,552 triangles at the
tested phase. All four Full HD/ultrawide shaft and radial capture tests passed
after this change; the Full HD radial mechanical crop kept the exact SHA-256
`c8f67fd35f4197ede6bd40dca28e291a0737b1990a145e8d96b053cddfa94620`.
This verifies image equivalence for that captured state, not a hardware FPS
gain. SDL3 documents sequential triangles when the index array is null.

At 900×620, the radial head update placed the lower crankweights behind the
button bar. The radial camera now scales and shifts only for windows shorter
than Full HD; the new compact screenshot leaves the controls clear. The
compact mouse-selection test and both large radial captures passed 3/3.
The Full HD radial mechanical crop retained its prior SHA-256.

The 1280×720 default window revealed a separate overlap: radial crankweights
entered the combustion strip, and the view selector covered the rightmost
head. Its camera now fits the motor above that strip. In wide layouts, the
view selector and fullscreen buttons use free space inside the status panel.
The new `LabControls.RadialViewMouseDefault` test clicks the moved selector
and captures the original-ROM session. It passed with six existing compact,
Full HD and ultrawide radial/shaft captures and mouse tests (7/7). The
1280×720 and Full HD PNGs were visually inspected.

The fork's temporary OpenGL ES desktop build under NativeLab/Xvfb produced
complete Full HD and ultrawide frames in `.work/donor-gl-current-*.png`.
Comparison with the refreshed Lab captures in `.work/lab-build/sevel-*.png`
confirms that the donor example shows a V engine in an axial plane; the Lab's
wide inline-four image is longitudinal. The Lab's separate axial 1/4 and 2/3
icons are the corresponding crank orientation cues. In the fork,
`CrankshaftObject` rotates the `Crankshaft` mesh by each rod-journal angle;
the Lab gives its two paired silhouettes opposite angles. Both interfaces
fit 1920×1080 and 3440×1440, but the donor's original SDL_GPU desktop
backend still cannot present under Xvfb because Vulkan needs DRI3.

The visual valve phase now follows the physical combustion reference in the
snapshot. Its default 120° crank-angle offset is a candidate reference, not
an experimentally established installation angle. Before this edit the
valves used a fixed zero offset while the physical model used 120°.
The pre-edit NativeLab suite passed 278/278 in 488.79 s. After rebuilding,
19 focused session, valve, donor-scene and Full HD/ultrawide capture tests
passed. The refreshed Full HD shaft and ultrawide radial PNGs were visually
inspected; hardware GPU and audible sound remain for the owner's test.

The same candidate combustion TDC reference now offsets the visual crank
angle for the shaft view, imported radial crank/rod/piston meshes, and 1/4
versus 2/3 axial icons. The preceding valve correction alone had left those
mechanical poses at the raw 60−2 angle, 120° away from the physical firing
TDC in the default candidate setup. The unchanged kinematic helper still
defines cylinder-1 TDC at its own zero input; renderers convert the physical
angle before calling it. Tests compare the complete shaft scene at raw 120°
with reference 120° against zero/zero, check the radial segment geometry at
570°/120° against 450°/zero, and verify the axial crank mesh at reference
TDC. NativeLab rebuilt successfully and 17 focused geometry, valve, donor
scene, Full HD and ultrawide capture tests passed. The refreshed Full HD
shaft and ultrawide radial screenshots were visually inspected. The 120°
installation angle remains a candidate, not a measured SEVEL datum.
The 1280×720 and 900×620 radial selector/capture checks then passed 5/5;
both refreshed PNGs were inspected and the moved crankweights remain clear
of the control strip.

The GUI-enabled NativeLab suite passed 279/279 in 493.04 s after the crank
reference correction. The combustion-order and candidate wasted-spark strip
now grows with the UI scale at Full HD; in ultrawide mode its scale is capped
at 1.2 so the extra coolant, load and fuel-film gauge labels stay visible
above it. The primary GUI rebuilt, six default/Full HD/ultrawide capture
tests passed, and the ultrawide capture passed again after the final cap.
The Full HD and ultrawide PNGs were visually inspected. The full 279-case
run predates this presentation-only strip adjustment.

An isolated Release build with `ENABLE_TESTS=OFF`, Lab enabled and Lab GUI
disabled compiled both `emu8051-tty` and `sevel-ma17-lab` after the phase
changes. `ldd` lists no SDL, PNG or graphics library for either binary. The
original-ROM v1 control replay to tick 1,200,000 produced the same debug and
Release `[LAB-STATE]`: 1160.328140616394 rpm, RAM47=47, 26 CC3 pulses,
24 burns, state fingerprint `62e768b1cc6093d9`, 151 events, event hash
`937ec22a520b2776` and zero overflow. Both SVG files have SHA-256
`3b37e678e6d9320bd9e296a5178c91e10207bb623820befa7bc03313593ea872`;
both WAV files have SHA-256
`a3598cada4004d4f000ceb8c96d86e5ebc1de47258209c1de31786a1d878e8f1`.
Artifacts are ignored under `.work/release-headless-build/` and
`.work/lab-build/`.

The donor SDL_GPU preview now bounds its scene texture and blit rectangle by
the actual swapchain width and height returned by
[`SDL_WaitAndAcquireGPUSwapchainTexture`](https://wiki.libsdl.org/SDL3/SDL_WaitAndAcquireGPUSwapchainTexture),
instead of trusting the window-size request during resize. It also cancels
the command buffer on transfer-map or
copy-pass failure, skips a frame if target textures cannot be created, and
reports a runtime GPU error before closing only the preview window. The SDL3
GPU API documents the returned swapchain dimensions, a possible null texture
when minimized, and the requirement to
[`submit`](https://wiki.libsdl.org/SDL3/SDL_SubmitGPUCommandBuffer) or cancel
a command buffer on the acquisition thread. NativeLab rebuilt the GPU target;
its GPU fallback and primary SDL capture tests passed 2/2. Xvfb still cannot exercise an
acquired Vulkan swapchain, so successful hardware GPU presentation remains
unverified.

The radial view now draws a single schematic shaft behind its four imported
crank-journal silhouettes. This makes the common axis visible while preserving
the opposite 1/4 and 2/3 crank poses and keeping radial meshes out of the
longitudinal shaft view. NativeLab rebuilt the GUI; eight donor-scene tests and
the Full HD and ultrawide radial Xvfb captures passed 10/10. The refreshed
Full HD capture was inspected visually. The section spacing remains a labeled
visual estimate, not a measured SEVEL crankshaft dimension.

The GPU preview now also stops on a failed SDL render-pass creation. SDL3's
[`SDL_BeginGPURenderPass`](https://wiki.libsdl.org/SDL3/SDL_BeginGPURenderPass)
returns a pass handle, and its `LOAD` operation is undefined before texture
contents are written. After acquiring a swapchain texture, the failed frame
is submitted rather than canceled, as required by
[`SDL_WaitAndAcquireGPUSwapchainTexture`](https://wiki.libsdl.org/SDL3/SDL_WaitAndAcquireGPUSwapchainTexture).
The main software window remains available; hardware GPU presentation is
still unverified under Xvfb.

After the radial common-shaft drawing and GPU render-pass guards, the complete
GUI-enabled NativeLab suite passed 279/279 in 493.80 s with
`ctest --test-dir .work/lab-build --output-on-failure -j 2`. This includes
original-ROM, K-Line/PTY, physical long-run, audio, donor-scene and Xvfb
capture tests.
The Xvfb tests still exercise SDL software rendering and GPU fallback, not
hardware GPU presentation or audible speaker output.

Donor mesh orientation was checked against `Crankshaft::getRodJournalPositionLocal`
and `CrankshaftObject::render`: a zero-angle donor journal points along +X.
The SEVEL kinematic angle starts along +Y, so the radial and axial crank mesh
rotations now convert between those references; the rod mesh rotation also
uses the inverse sign of the kinematic angle. Recording-renderer tests compare
actual crank and rod mesh vertices with their expected positions at TDC and
quarter-turn. The GUI rebuilt, those two geometry tests and all four Full HD
and ultrawide radial/shaft captures passed 6/6. The refreshed Full HD radial
PNG was inspected: rod big ends now sit over the journal artwork. The earlier
279/279 complete suite predates this orientation correction.

The GUI-enabled ASan/UBSan build compiled the corrected scene and Lab. The
two donor mesh orientation tests passed with leak checking enabled; the Full
HD Xvfb capture then exited on a LeakSanitizer report of 108,124 bytes in
481 allocations rooted in Mesa `libGLX_mesa.so`. Repeating the same three
tests with `LSAN_OPTIONS=detect_leaks=0` passed 3/3, so this run checked
address/undefined behavior in the Lab but did not validate GUI process leak
freedom. The acoustic path remains event driven: `StreamingAudio` adds input
pressure only for timestamped `Combustion` events with positive burned fuel;
it does not synthesize from the displayed RPM.

The current Release GUI build (`.work/release-lab-build/sevel-ma17-lab`) was
rebuilt after the crank/rod orientation and GPU error-path changes. NativeLab
Xvfb with SDL dummy audio ran the original ROM and warm candidate bench to
tick 1,500,000, saving `current-gui.png`; the inspected 1280×720 frame shows
the live four-cylinder scene, controls and ECU traces. The final state was
1,514.722 rpm, RAM47=59, 42 CC3 pulses, 40 burns, 247 events, zero event
overflow and zero audio write errors. A matching Release headless run reported
the same RPM, RAM47 and event count, and generated `current-state.svg` plus
`current-audio.wav`. The WAV has 66,821 mono S16 frames at 44.1 kHz, 46,172
nonzero samples and peak magnitude 14,546. The Release executable resolves
`libSDL3.so.0` from its own build directory; `assets/` is alongside it. A
separate Release `--gpu-preview` Xvfb run fell back after the expected missing
DRI3 backend and still captured `current-gpu-fallback.png` with zero event
overflow. These artifacts remain ignored under `.work/`; hardware playback
and GPU presentation still require the owner's test.

The complete GUI-enabled NativeLab suite was rerun after the crank/rod mesh
orientation correction and the Release smoke: 279/279 CTest cases passed in
493.32 s with `ctest --test-dir .work/lab-build --output-on-failure -j 2`.
This supersedes the earlier full-suite result that predated the orientation
change. The Xvfb backend still does not exercise hardware GPU presentation
or audible speaker playback.

The refreshed radial captures were inspected at 900×620, 1280×720,
1920×1080 and 3440×1440. At each size the crank, rods, pistons and valves
remain within the engine scene, and the control row and scope remain visible.
The compact frame ends the engine drawing above its controls. These visual
checks support the current framing only; the owner's hardware test remains
needed for actual GPU presentation and audible output.

The 900×620 status row now abbreviates the existing sensor values so modeled
TPS1/TPS2 voltages remain visible beside RPM, throttle angle, lambda and
coolant temperature. NativeLab rebuilt the GUI and
`LabControls.RadialViewMouseCompact` passed 1/1; its refreshed PNG was
inspected to confirm the line fits above the mechanical view. The sensor
values still come from the simulation snapshot.

The original-ROM offline audio test now replays a running engine with key-off
at tick 10,000,000 and captures through tick 12,000,000. The scenario reached
0 rpm after 266 CC3 pulses and 264 burns. Its WAV matches the idle WAV before
key-off, has nonzero samples immediately before key-off, and has only zero
samples from virtual second 11 onward. `LabAudio.OriginalRomScenarios` passed
1/1 under NativeLab (32.46 s). This verifies event-driven cessation in WAV;
physical speaker playback remains untested.

A second original-ROM replay switches the key off at tick 3,000,000, waits
five million ticks, then switches it on and holds the starter for 495,000
ticks. The WAV matches the idle scenario before key-off, is silent from
virtual seconds 4–8, and has nonzero PCM again during seconds 9–10. At tick
16,000,000 the engine was at 809.878 rpm with 378 CC3 pulses, 396 burns and
zero event overflow. `LabAudio.OriginalRomScenarios` passed with this added
case in 41.69 s. The Release GUI was rebuilt and its 900×620 radial Xvfb
capture passed with 42 CC3 pulses and 40 burns.

The live SDL dummy-audio test now covers key-off followed by key-on and a
starter press in the same `SimSession`. It waits for both the stream device to
pause and its queued input to clear at key-off, then for the audio worker and
stream device to resume at key-on. `LabAudio.PauseSpeedAndKey` passed three
consecutive NativeLab runs (0.83 s each). This verifies stream transitions on
the dummy driver; physical-device latency and audible playback remain open.

The live audio worker reads the latest snapshot and event window under
separate locks. Events can be appended during a simulation batch before its
new snapshot is published. On audio startup/resume, the worker now seeks to
the first event after the snapshot tick instead of the end of the newer event
window, preserving events that arrived between those reads. Debug and Release
GUI targets rebuilt; `LabAudio.LiveDummyStream` and
`LabAudio.PauseSpeedAndKey` passed 2/2 on rerun. One earlier combined CTest
invocation stalled during `PauseSpeedAndKey` and was terminated after two
minutes; a standalone run and the bounded combined rerun passed. The exact
cause of that isolated stall remains undetermined.

The SDL dummy pause/key test then passed ten consecutive bounded runs without
reproducing that stall. The original-ROM WAV scenarios now also disconnect
candidate coil channel 0 at tick 10,000,000. The fault and idle WAVs are
sample-identical before disconnection; during ticks 10–12 million, the fault
WAV differs and carries 38.6% of the idle signal energy. At tick 12 million
the fault run was at 259.401 rpm versus over 900 rpm in the idle reference,
with zero event overflow. `LabAudio.OriginalRomScenarios` passed 1/1 in
47.56 s. This checks the modeled electrical fault's effect on combustion
audio, without claiming a measured SEVEL timbre or verified coil pinout.

After the live-audio event-window correction and added ROM audio scenarios,
the complete GUI-enabled NativeLab suite passed 279/279 in 513.27 s with
`ctest --test-dir .work/lab-build --output-on-failure -j 2 --timeout 180`.
This run includes original CLI/physical tests, PTY/K-Line, donor geometry,
SDL dummy audio and Xvfb capture tests. Hardware GPU presentation and
speaker playback remain outside Xvfb's verification scope.

The live window now offers an H-key control guide and a visible `H: HELP`
hint in the status panel. Its seven lines cover ignition, starter, pedal,
load, pause/step, speed, sound, view navigation, scope and fullscreen inputs.
The guide was captured and visually inspected at 900×620, 1920×1080 and
3440×1440 under NativeLab/Xvfb. After adding the hint, the compact, Full HD
and ultrawide radial capture tests passed 3/3; Debug and Release GUI targets
built. The prior 279/279 suite predates only this presentation change.

The help guide is now centered within the mechanical scene and, when the
button bar is visible, positioned above it. Refreshed 900×620, Full HD and
ultrawide Xvfb frames were inspected: the compact guide no longer covers the
buttons or right-hand gauges. All three capture commands exited successfully
with 42 CC3 pulses and 40 burns; the Release GUI target was rebuilt again.

Fresh NativeLab/Xvfb builds of the fork's existing OpenGL ES path captured
complete Full HD and 3440×1440 GUI frames in `.work/donor-gl-verify-*.png`.
They show the donor's dense gauge graduations around an axial V-engine scene;
the Lab's four inline radial sections and MA1.7 controls serve a different
mechanical layout. The donor frame is at 0 rpm, so it cannot validate running
animation. The Lab's three main dials now use the transplanted `Gauge` sweep
and minor/major tick settings, with brighter outlines for readability. A new
Full HD radial frame at `.work/lab-build/sevel-gauge-1920x1080.png` was
visually inspected; six focused compact, Full HD and ultrawide capture tests
passed. These captures use software rendering, not hardware SDL_GPU.

The V key and view selector now cycle through shaft, four-section radial,
focused axial 1/4 and focused axial 2/3 views. The focused views reuse the
same donor crank, rod, piston, head and valve meshes and physical SEVEL pose,
showing cylinder 1 or 2 as the representative of each crank pair. A new
`DonorScene.FocusedAxialSectionKeepsPhysicalPairPhases` test confirms the
1/4 match and 180-degree 2/3 opposition; the existing four-section test still
passes. Original-ROM Xvfb captures at Full HD, ultrawide and a manually
checked 900×620 focused frame show the complete assembly clear of controls.
Seven focused radial/axial mouse and capture tests passed after framing.
The focused views depict a selected radial section viewed along the shaft;
they do not claim to show four cylinders separately from one physical axial
camera position.
After the focused-view change, the GUI Release target built and the complete
NativeLab CTest suite passed 282/282 in 514.08 s with `-j 2 --timeout 180`.
This includes the original CLI/physical suite, ROM audio scenarios, K-Line,
donor scene tests and all registered Xvfb captures. The help text was then
updated to retain the `R RESET` hint; no simulation behavior changed.

Two separate original-ROM/Xvfb live captures at ticks 1,500,000 and 1,550,000
use the same warm candidate bench preset and the primary SDL software window:
`.work/lab-build/sevel-motion-1500000.png` and
`.work/lab-build/sevel-motion-1550000.png`. Visual inspection shows cylinders
1/4 rise while 2/3 fall, with the paired axial crank silhouettes rotating.
The ROM-driven CC3 count advances 42 to 44, combustion count 40 to 42, RPM
1514.72 to 1537.86, and physical angle 137.839 to 145.917 rad. A Pillow
comparison found 36,604 changed RGB pixels (15.0%) in the mechanical crop
`(120,120)-(850,455)`. This is evidence of state-dependent frames at two
virtual ticks, not a frame-rate or audible-playback measurement.
The new `LabCapture.PhysicalMotion` CTest repeats these runs under Xvfb,
compares only the mechanical viewport in BMP readbacks (without Pillow),
requires advancing CC3 and combustion counts, and passed with the same
36,604/244,550 changed pixels. It is registered only for GUI-enabled builds.
The donor GPU notice was also corrected to describe its local failure-reporting
and swapchain-size changes; the GPU file hashes still match the reuse ledger.

The live status now calls SDL's cumulative, approximate stream-request
shortfall `short~`, and wide windows place `STREAM SHORT~` and dropped
playback samples above the volume slider. The first Full HD capture exposed
an overlap with the TPS gauge; moving the readout above the slider cleared
it. The GUI target rebuilt and `LabCapture.Axial14` and
`LabCapture.Axial23` passed 2/2 under NativeLab/Xvfb. Their refreshed
1920×1080 and 3440×1440 PNGs were visually checked against the fork's
temporary OpenGL ES captures. The fork shows its GM LS V-engine example at
0 rpm, while the original-ROM Lab captures show the running SEVEL's two
crank-pair axial sections at 1,515 rpm.

The live status now also displays `phase~` in 0–719° of the 720° cycle,
relative to the snapshot's candidate firing-TDC offset. It uses the same
physical crank snapshot as the valve and mechanical drawings; the readout
does not establish the actual sensor-wheel installation angle. The GUI
target built and compact 900×620, Full HD radial and ultrawide radial Xvfb
captures passed 3/3 after the change. All three images were checked for
status placement; the captured original-ROM state reads phase~577/720.

SDL's GPU API requires a window to be claimed before it can be released from
the device. The imported GPU renderer now tracks that successful claim so a
failed initialization cannot attempt to unclaim an unrelated window. The GUI
target rebuilt, and `LabCapture.GpuPreviewFallback` plus
`LabCapture.SdlSoftwarePng` passed 2/2. A direct NativeLab/Xvfb run reported
`No supported SDL_GPU backend found!` and retained the primary OpenGL SDL
renderer. This verifies fallback, not the new claimed-window branch or GPU
presentation on hardware. SDL 3.4 adds `SDL_CreateGPURenderer`, which can
accept an existing GPU device; the pinned 3.2.8 build lacks it. Same-window
integration still needs an explicit composition path for the mechanical scene
and the controls, followed by a hardware presentation check.

The live audio worker now publishes the recent PCM peak after a successful
SDL stream enqueue and clears it on pause, key-off or faster-than-1× mode.
The wide GUI shows that peak above its volume control, while the shutdown log
reports the maximum raw S16 amplitude. The original-ROM dummy-device test
passed with CC3=230 and maximum peak 14,496/32,768; its 1280×720 capture
visibly showed an 18.6% recent peak during cranking. The key-off smoke test
now checks that the recent peak returns to zero and passed. This confirms
sample generation and queueing in NativeLab, not audible hardware playback.
The Debug and Release GUI targets built, and refreshed Full HD and ultrawide
radial captures passed 2/2 and were visually checked for meter placement.

The worker snapshot now carries the candidate P1.5/P1.6 idle-bridge latch
bits, modeled actuator stem, idle contact and motor connection. Wide GUI
status rows display these values as `IAC?`, `STEM~`, `CT` and optional `DISC`.
The GUI and session-smoke targets built, `LabSession.PauseAndControls` passed,
and compact, Full HD and ultrawide radial capture tests passed 3/3 under
NativeLab/Xvfb. The Full HD and ultrawide images were inspected for text
placement. This exposes the modeled ECU-to-idle-actuator path without treating
the candidate electrical mapping as a confirmed pinout.

The current fork's temporary OpenGL ES desktop build also produced fresh
frame-30 Xvfb captures at 1920×1080 and 3440×1440 in
`.work/donor-gl-verify-*.png`. Side-by-side visual inspection with the Lab's
`.work/lab-build/sevel-radial-*.png` confirms that the donor's GM LS V-engine
example is drawn in its axial plane, while the Lab shows the inline-four
longitudinal crank layout with paired 1/4 and 2/3 crankweights. Both layouts
remain readable at these resolutions. The donor capture is at 0 rpm and the
Lab capture near 1,515 rpm, so piston phases are not directly comparable.
The donor's original SDL_GPU desktop backend still cannot present under this
Xvfb host because its Vulkan path needs DRI3.

After exposing the idle bridge state in snapshots, the complete GUI-enabled
NativeLab suite passed 283/283 in 513.16 s with two jobs and a 180 s per-test
timeout. The GUI Release target built. The wide status row now explicitly
prints `IAC? NO BINDING` when the candidate P1.5/P1.6 bridge is disabled,
instead of leaving that state unlabelled. The Debug and Release GUI targets
rebuilt; `LabCapture.SdlSoftwarePng` and `LabCapture.Radial1920x1080` passed
2/2. The raw-scenario 1280×720 PNG was inspected and the new label fits the
status panel. These two focused captures validate the final label edit;
the 283-case run used the pre-edit GUI binary.

The live window now accepts F12 for a full-window capture at the currently
displayed snapshot tick, including while the ROM worker is paused. It chooses
an unused tick/index filename in the working directory and logs the saved path;
PNG is used when compiled in, BMP otherwise. The new Xvfb/xdo test sends
Space then F12 to the running original-ROM Lab and checks PNG signature,
1280×720 dimensions and the capture log. `LabCapture.F12Live` passed 1/1
under NativeLab. Capture happens on the SDL UI thread after drawing and does
not enqueue a simulation command.

The SDL event loop now keeps preview-window mouse movement and clicks away
from the main controls while allowing a left-button release from either
window to end a held starter or slider drag. It explicitly captures the mouse
only while START is held and releases capture on button-up or focus loss;
[SDL_CaptureMouse](https://wiki.libsdl.org/SDL3/SDL_CaptureMouse) documents
this short drag use, automatic capture, and automatic release on lost focus.
The GUI rebuilt and `LabCapture.GpuPreviewFallback`,
`LabCapture.F12Live`, and `LabControls.MouseButtonBar` passed 3/3 in
NativeLab/Xvfb. The actual second-window release path still needs hardware
validation because the local Xvfb host cannot create the SDL_GPU preview.

An `SDL_VIDEODRIVER=offscreen` NativeLab run did create the donor GPU preview
with the packaged shaders. Across 180 frames of the original-ROM warm bench,
it exited without `SDL GPU preview stopped`, reached tick 5,569,500 with 208
CC3 pulses, 282 burns and zero event overflow. The primary SDL window saved
an inspected 1280×720 PNG. `LabCapture.GpuOffscreen` now repeats this path,
requiring GPU initialization, no runtime GPU error, ROM-driven CC3/burns,
zero overflow and a valid primary PNG; it passed in 5.71 s. The test returns
CTest SKIP when the offscreen backend is unavailable. At this stage the test
exercised GPU device, shader and render-pass operation without reading back
the GPU scene; the later scene-capture check is documented below. Neither
test establishes display presentation on hardware.

That PNG exposed an overlap in the default 1280×720 status panel: the view
buttons covered the end of the candidate idle-actuator readout. The buttons
now sit at 64 px in shorter windows and 82 px from 900 px height upward.
The 1280×720 and 1920×1080 captures were visually inspected after this
adjustment; both keep the status text and buttons clear. Five focused default,
Full HD, ultrawide, mouse-selector and SDL capture tests passed 5/5, and the
Debug and Release GUI targets built.

The donor OpenGL ES desktop target rebuilt under NativeLab, and its existing
frame-30 Xvfb captures at `.work/donor-gl-verify-1920x1080.png` and
`.work/donor-gl-verify-3440x1440.png` were compared with the Lab's radial
captures. The donor image shows its GM LS V-engine in the axial plane; the
Lab image shows all four SEVEL cylinders along the crankshaft. This is a
layout and orientation comparison, since the donor frame is at 0 rpm and
the Lab frame is near 1,515 rpm. Both are readable at Full HD and ultrawide.

An offscreen SDL_GPU scene readback exposed a stale donor vertex SPIR-V:
it contained only `modelViewProjection`, whereas the donor HLSL and renderer
use `transform`, `cameraView`, and `projection`. Recompiling the unchanged
donor HLSL with glslangValidator restored the intended scale. The captured
960×640 GPU scene now spans the four-cylinder layout instead of a small
centered image. `LabCapture.GpuOffscreen` checks the scene dimensions and
foreground extent. This still does not validate presentation on a physical
display.

The full 285-case GUI build suite then returned 283 PASS and two failures.
`LabCapture.GpuOffscreen` sampled one piston-phase-dependent pixel, and
`LabCapture.Radial3440x1440` could reach its 2,400-frame limit before
`xdotool` resized the window under concurrent load. The GPU check now
measures the foreground scene bounds, and the resize harness has a generous
frame cap while the target tick remains its exit condition. The two failed
cases plus Full HD layout passed 3/3 on rerun; all ten affected resize,
radial, axial and mouse-view cases passed 10/10. The Release GUI target also
rebuilt, and an original-ROM offscreen GPU run captured a 960×640 scene with
foreground bounds `(121,135)–(838,505)`, 135 CC3 pulses, 189 burns and zero
event overflow. The complete GUI build suite then passed 285/285 in 520.33 s
with two CTest jobs and no skips.

The new GPU readback also rebuilt in the existing `ENABLE_SANITIZERS=ON`
GUI tree. `LabCapture.GpuOffscreen` passed under ASan/UBSan with lavapipe
selected by `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json` and
`ASAN_OPTIONS=detect_leaks=0:halt_on_error=1`. With leak detection enabled,
the same offscreen run exited at shutdown with 3,136 bytes in four allocations
reported from Vulkan/DRM libraries, including
`/opt/amdgpu/lib/x86_64-linux-gnu/libdrm.so.2`; no invalid-access or UBSan
report appeared before exit. The leak status of the GPU driver stack remains
unresolved; disabling LSan for this focused run does not claim a leak-free
application.

## Delivery evidence audit (2026-11-17)

| Requirement | Current evidence | Status / limit |
| --- | --- | --- |
| Optional product and original CLI | `ENABLE_SEVEL_MA17_LAB` builds `sevel-ma17-lab`; GUI-off and Lab-off builds succeeded; the GUI build passed 285/285 CTest cases | Verified on NativeLab Linux; no required donor checkout at runtime |
| Original MA1.7 ROM and one physical worker | `SimSession` owns one `run_cli` worker; `LabSession.GuiAudioFrameDeterminism`, `WarmScenarioDeterminism`, `ControlReplay` and `LabSession.HeadlessControlReplay` passed | Original 32 KiB ROM stays ignored by Git; electrical mappings marked candidate |
| Four-cylinder SEVEL mechanics | `SevelGeometry` and `SevelValves` tests cover PMS/PMI, opposed 1/4 and 2/3 pins, 720° repeat, manual valve windows and firing order; `DonorScene` tests cover imported meshes and selected axial/radial views | Rod, pitch, outer head and valve lift are `visual_estimate`, not Fiat dimensions |
| Interface and controls | Original-ROM Xvfb PNGs at 1280×720, 1920×1080 and 3440×1440 were inspected; mouse, fullscreen, F12, view selection, motion, button bar and K-Line tests passed | GPU scene pixels passed offscreen readback; physical monitor presentation remains for owner test |
| ECU events and diagnostics | CC3, P5.0/P5.1, paired spark glow, candidate lamp, raw fault banks and event overflow come from worker snapshots/events; `LabKline.LivePtyFaultQuery` passed | Candidate pins and lamp are observations, not proven wiring |
| Audio from physical combustion | `LabAudio.EventDrivenWav`, `OriginalRomScenarios`, `LiveDummyStream`, `PauseSpeedAndKey` passed. Inspected WAVs: idle 534,550 frames/513,547 nonzero; pedal 534,550/513,607; key-off 89,096/0, all mono 44.1 kHz | Timbre is an acoustic approximation; audible speaker output remains for owner test |
| Donor provenance and offline assets | `THIRD_PARTY_NOTICES.md`, `SEVEL_LAB_REUSE.md`, vendored MIT sources, font license, hash-checked shader/font/mesh restoration | Vertex SPIR-V regenerated from unchanged donor HLSL; DXIL runtime was not tested here |
| Memory and concurrency checks | ASan/UBSan GPU offscreen and six earlier GUI/audio tests passed with scoped driver leak handling; TSan binary could not start under this NativeLab memory map | No TSan race conclusion; Vulkan/DRM shutdown leak report is unresolved |

Reproduce the GUI build and run with the commands in `README.md`. The local ROM
is `FiatTipo_MA17_dump_27c256.bin` (SHA-256
`a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`);
it is not packaged. Review the Full HD and ultrawide Lab captures at
`.work/lab-build/sevel-radial-{1920x1080,3440x1440}.png`, the offscreen GPU
capture at `.work/release-lab-build/gpu-check-gpu.png`, and the WAVs at
`.work/lab-build/sevel-audio-{idle,pedal,key-off}.wav`. These `.work/` files
are local ignored artifacts, so recreate them before sharing a release.

The asynchronous live GUI previously treated `--capture-tick` as a lower
bound: a request for tick 1,500,000 produced both PNGs at tick 1,529,000 in
one offscreen run. `SimSession` now clips a batch at the capture target and
retains that worker snapshot until the UI renders it, without pausing the
simulation. Automatic main-window capture logs the actual tick; the GPU
capture logs the same tick. `LabCapture.GpuOffscreen` now requires both logs
to report exactly 1,500,000. It and four session/determinism tests passed
5/5; the Release GUI rebuilt and independently produced matching main/GPU
PNGs at exactly tick 1,500,000. The GUI-off Lab rebuilt, and its
`LabSession.PauseAndControls` case passed. The 285/285 full-suite result above
predated this exact-capture edit. The rebuilt GUI suite then passed 285/285
again in 506.78 s with two CTest jobs. The updated GPU capture also passed
under ASan/UBSan with lavapipe and `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1`;
the external Vulkan/DRM leak limitation described above still applies.

F12 now uses the same GPU readback helper as automatic capture. When the
optional preview is active, a manual main-window PNG is accompanied by a
`-gpu.png` scene file at the displayed tick. The Debug and Release GUI targets
rebuilt. The filename selection checks both the main and GPU scene paths to
avoid overwriting an existing companion image. After that check, the three
focused capture tests passed 3/3 and Debug and Release rebuilt again; the
updated offscreen GPU path also passed under ASan/UBSan with the
documented driver-leak setting. Xvfb cannot open the interactive GPU preview,
so the combined F12+GPU keyboard path awaits the owner's hardware test. The
complete rebuilt GUI suite then passed 285/285 in 509.60 s with two CTest jobs
after the capture-helper and filename changes.

Lifecycle audit found that calling `SimSession::start()` twice could assign a
new `std::thread` to a joinable worker and terminate the process. The session
now rejects duplicate starts and starts after stop with `std::logic_error`.
`LabSession.PauseAndControls` exercises the duplicate-start case and passed
1/1; the Debug and Release Lab targets rebuilt. The 285/285 suite above
predates this local lifecycle guard.

To check packaged asset lookup independently of the working directory, the
Release binary was launched through NativeLab with `env -C /tmp`, an absolute
ROM path, `SDL_VIDEODRIVER=offscreen`, lavapipe and `--live --gpu-preview
--no-audio --window-frames 4`. It exited 0, reported `renderer=opengl` and
`preview_ready=1`, and loaded shaders from the build tree's `assets/shaders`.
The Lab's mesh and font loaders also completed before the preview log. This
verifies runtime lookup relative to the executable; the donor checkout was
not renamed or unmounted for this run.

The GUI-disabled Lab and Lab-disabled original CLI configurations rebuilt
after the session lifecycle guard. The GUI-disabled `lab_session_smoke`
target also rebuilt, and its `LabSession.PauseAndControls` test passed 1/1.

The analog scope now shows six live miniature traces above the selected
full-size graph. Clicking a miniature selects its group and resets the
trigger channel to that group's first signal. The strip is omitted when the
scope panel is under 248 px high, preserving the compact trace area. NativeLab
built with `--parallel "$(nproc)"`; 11 selected capture/control/scope tests and
the new `LabControls.ScopeCardTps1920x1080` click test passed. Captures at
1920×1080 and 2560×1440 show the selected card and the graph without overlap.

The analog analysis panel can now expand to the center's available height
with `Z` or its header button and return to the normal two-view layout with
the same controls. In expanded mode, the panel starts at y=100 px; its
coordinates, group selectors, traces, zoom anchor and cursor hit tests use
the expanded bounds. The NativeLab 1920×1080 capture is
`build-lab/sevel-scope-maximized-1920x1080.png`. Its automated test toggled
by key, restored by button, and expanded again before capture. The focused
NativeLab build and five tests passed, including the piston orientation and
normal 1920×1080 and 3440×1440 layouts.

The seventh analog group, `ADC TPS`, plots the last completed ADC0/TPS2 and
ADC6/TPS1 conversion voltages. `AdcObservation` carries the driven voltage,
10-bit count and conversion tick into each snapshot; it keeps these separate
from the pre-fault TPS circuit model. The archive retains both sides of a
large ADC-pin voltage jump. NativeLab built with `--parallel "$(nproc)"` and
passed `LabRunner.AdcFaultTelemetry`, `LabRunner.OriginalRomSnapshot`,
`LabCapture.AdcTpsFault1920x1080` and
`LabSession.WarmScenarioDeterminism` (4/4). In
`build-lab/sevel-adc-tps-fault-1920x1080.png`, the lower trace shows the
temporary 5 V TPS1 pin fault and its recovery. The upper trace has no fault.
The ADC TPS CSV additionally records each channel's 10-bit count, conversion
tick and observation age. `LabCapture.AdcTpsFault1920x1080` checks the high
fault value, recovery and timestamp ordering; the existing TPS CSV test also
passed in NativeLab (2/2 focused tests).

The added Fiat manual scans in `PhotosECU/` confirm the corrected piston
silhouette, 86.4 × 67.4 mm geometry, 1–3–4–2 firing order, five gearbox
ratios and the differential. `docs/SEVEL_TIPO_16_SPECS.md` now identifies
the exact source images and corrects piston clearance and ABNT peak units.
The scanned CEE graph is a visual reference for a later vector trace; its
curve has not been digitized or used as live torque or power telemetry.
For a first approximate gearbox version, use the individual five ratios
from `manual_cambio.png` and the 63/16 differential from
`manual_cambio_2.png`, then calculate total ratios directly. The printed
total-ratio table disagrees for 3rd–5th; the current road-speed display is
still scenario input and no gear/clutch dynamics are yet implemented.
`SevelTransmission.hpp` now holds the ratios and a tested total-ratio
calculation. The Lab adapts the donor `LoadSimulationCluster` gear card with
up/down click zones; `Q`/`E` select neutral through fifth. At 1920×1080 the
card fits above the combustion strip, and `LabControls.GearWidget1920x1080`
verified keyboard and pointer selection. The selected ratio is explicitly
marked `REF`; the card does not yet transmit torque or drive vehicle speed.

The digital ECU scope now has four independently selectable lanes. CC3,
P5.0 and P5.1 still use recorded pin events; `IDLE SW SAMP` reads the
physical contact from retained snapshots and breaks its trace at missing
throttle data or gaps over 250 ms. NativeLab's
`LabCapture.DigitalZoom1920x1080` passed, and the resulting image
`build-lab/sevel-digital-zoom-1920x1080.png` was inspected for lane spacing
and label legibility. This capture shows the contact closed throughout;
the step on a change has not yet received a dedicated image test.
The digital plot now marks relative time on its X axis. A pin lane without
retained events shows `NO EDGE` instead of a fabricated low trace, and a
lane with its first retained event inside the window starts there rather
than at the left edge. NativeLab rebuilt and passed the digital-zoom and
1920×1080 layout captures (2/2); the zoom capture was inspected again.

The analog scope heading now chooses a shorter measured layout when its
full text would reach the panel edge. At 1280×720 the group, time window,
point count, effective rate and live/history state remain visible. The
navigation capture test now clicks inside the actual plot bounds; its old
coordinate landed in the preview strip, so its double-click reset never
executed. NativeLab passed the corrected navigation tests at 1280×720 and
1920×1080 (2/2), and the new 1280×720 capture was inspected.

The instrument profile now distinguishes a channel without a valid current
reading from a quantity not published by the model. Defined gauges render
`--` and report `MISSING` in the tooltip when unavailable; VE still renders
`N/D`. NativeLab built with `--parallel "$(nproc)"` and passed the compact
button-bar and 1920×1080 layout captures (2/2); the latter was inspected.

The digital ECU scope now plots timestamped spark-pair chevrons, combustion
squares and misfire crosses in a separate event strip on taller panels.
The pin traces remain electrical high/low intervals; the event shapes do
not infer dwell or injector opening. NativeLab rebuilt with `nproc` and
passed both digital captures (2/2). The new
`build-lab/sevel-digital-events-1920x1080.png` was inspected, and its test
checks the spark and combustion colors in the event region.

The analog scope now exposes two more pairs of last completed ADC
conversions: ADC1 battery divider with ADC5 conditioned lambda, and ADC2
IAT with ADC3 ECT NTC. The preview cards, group key, labels and CSV
columns use the same group mapping. The archive preserves both sides of
large jumps on all six identified ADC channels. NativeLab captures at
1920×1080 show temporary ADC5 and ADC3 fault stimuli and recovery; both
tests check the recorded pin voltage, 10-bit count, conversion tick and
age in the CSV. Export filenames now include the group to separate
parallel captures.

The Thermal scope now overlays physical coolant ECT and air-sensor IAT
temperatures on a shared °C axis, while thermostat opening and a sampled
fan-state step track remain below. `EmulatorSnapshot::intake_air_c` only reads the
existing `ThermalState::air_sensor_c()`; it does not change sensor or engine
physics. The archive retains IAT extrema. NativeLab passed
`LabCapture.thermalScope1920x1080`, the ADC2/3 fault capture, the gear-card
capture and warm-scenario determinism (4/4). The thermal CSV test checks
both physical temperature columns, their distinct live readings and the
sampled fan column;
`build-lab/sevel-thermal-scope-1920x1080.png` was inspected. ADC2/3
voltages remain in their separate conversion scope.

The Battery scope separates the physical sensor-circuit supply voltage
from the last ADC1 conversion after its modeled divider. Both have distinct
axes, source labels and CSV columns; ADC1 also retains count, conversion
tick and age. The ten preview cards remain visible at 1920×1080. A
12.0 V scenario produced 12.00 V supply and about 3.12 V at ADC1 in
`build-lab/sevel-battery-scope-1920x1080.png`; the NativeLab capture,
thermal capture, ADC battery/lambda capture and warm determinism passed
4/4. A 14.5 V test scenario hit the existing idle-actuator 12.5 V drive
limit before the Lab window opened; this validation therefore used 12.0 V
and did not change the actuator model.

The snapshot now also copies raw ECU lower-RAM bytes 60h–67h without
assigning sensor meanings. The debug inspector prints their addresses and
hex values; ADC-group CSV exports each byte as a separate unsigned column
alongside the last conversion's pin voltage, count, tick and age. This
keeps ROM-processed state distinct from the harness ADC observation.
NativeLab rebuilt with `nproc` and passed the battery, ADC TPS-fault,
ADC battery/lambda and warm-determinism tests (4/4). The battery capture
test checks all eight raw columns have bounded byte values.

The debug view now keeps the status bar at two lines and places ECU details
in a framed, opaque inspector inside the mechanical column. The candidate
lamp indicator moved into its title. Its raw IRAM row remains legible at
1280×720 and 1920×1080; the redundant RPM/lambda trend overlay was removed
because those signals already have dedicated scopes. NativeLab passed both
debug captures and the 1280×720 scope-navigation test (3/3); the two debug
PNGs were visually inspected for text and gauge overlap.

The 900×620 debug capture exposed a compact-only overlap: the inspector
covered the KEY/START/pedal/load/pause/speed/mute button row. It now anchors
above the same button rectangle used for hit testing and ends before the
analog panel. `LabCapture.BatteryDebugCompact900x620` checks a decoded
button pixel against its active fill, so another overlay cannot silently
hide KEY. NativeLab passed this capture and compact view selection (2/2);
`build-lab/sevel-battery-debug-900x620.png` was inspected after the fix.

The UI-43 state matrix now has four original-ROM captures at 1280×720 in
`.work/gui-review/`. `stopped-1280x720-t800000.png` uses `--live
--bench-preset` with the key off and reports 0 rpm/0 burns. The
`auto-1280x720-t800000.png` uses `--auto-start` and reports 940 rpm/13
burns. `replay-load-1280x720-t800000.png` uses the checked-in
`tests/data/lab_control_replay.txt`: at the same tick it shows 24 N·m
applied load, pedal command, disabled replay controls, 655 rpm and eight
burns. Each has a matching `.log` with `[LAB-CAPTURE] tick=800000` and
`[LAB-STATE]` fingerprints. All three PNGs were visually inspected.
`paused-1280x720-f12.png` was captured after automatic start at tick
1,522,000, with key on and about 1000 rpm. The F12 test now waits for an
active motor, verifies that the paused tick stays fixed and waits for the
PNG's complete IEND chunk before copying it. It passed in NativeLab.
These initially established the before state. The matched after captures
for the lambda-validity change are listed below. Other resolutions and
independent UI scale choices still need a controlled matrix.
An attempted match for `.work/current-baseline.png` at tick 148,000
produced 254 rpm with the bench preset and 253 rpm without it, while the
unlabeled old image shows 433 rpm. The tick and resolution alone therefore
do not establish a like-for-like scenario comparison.

The gear card, left pedal/volume sliders and header help/debug hitboxes
now read column edges from `LabLayout` instead of repeating 24%/66%
width calculations in `SdlDisplay.cpp`. NativeLab rebuilt with `nproc`;
mouse button bar, fullscreen return, gear selection and radial view mouse
tests passed 4/4. The refreshed 3440×1440 original-ROM capture at
`.work/gui-review/current-3440x1440.png` passed its capture check and was
visually inspected; the gear card fits between TBI and the combustion strip.

Lambda validity now follows delivery of the first exhaust packet to the
existing `ExhaustLambda` model. The new read-only observation flag travels
through `EmulatorSnapshot`; the gauge and analog scope show `--`/a gap
before that event instead of reporting the model's default λ=5.0 as a
measurement. The oxygen-sensor voltage remains a separate modeled channel
and still shows its pre-arrival 0.45 V baseline. NativeLab rebuilt with
`nproc` and passed ten focused exhaust, scope, capture and determinism tests.
At 1280×720, `stopped-lambda-validity-1280x720.png` shows no lambda value,
while `idle-lambda-validity-1280x720.png` shows a live λ≈1.24 at tick
1,500,000. Both images were inspected; no exhaust dynamics were changed.

For UI-43, `.work/gui-review/` now contains these before/after PNG pairs
from the original ROM. Each pair is 1280×720 at the same 100% GUI scale;
the first three have identical `[LAB-STATE]` fingerprints in their logs.
Names in the table are relative to that directory.

| State | Before PNG | After PNG | Tick | Changed RGB pixels |
| --- | --- | --- | ---: | ---: |
| Key off, stopped | `stopped-1280x720-t800000.png` | `stopped-lambda-validity-1280x720.png` | 800,000 | 792 |
| Auto-start, idle | `auto-1280x720-t800000.png` | `after-auto-1280x720-t800000.png` | 800,000 | 215 |
| Pedal 8 mm and load 24 N·m, control replay | `replay-load-1280x720-t800000.png` | `after-replay-load-1280x720-t800000.png` | 800,000 | 384 |
| Paused after auto-start, F12 | `paused-1280x720-f12.png` | `after-paused-1280x720-f12.png` | 1,522,000 | 195 |

The stopped pair changes the lambda panel from the initial 5.0 value to
`--` and removes the unsupported trace; the other pairs retain their
live values. Remaining pixel differences include visual needle smoothing
and capture-time UI state. The paused pair has the same displayed tick,
but the F12 test does not export a full physical-state fingerprint.

The compact 900×620 layout was checked after the lambda-validity change.
`LabCapture.StoppedCompact900x620` captures the original ROM with the key
off and verifies 0 CC3 pulses and 0 burns; the header now uses the same
exhaust-sample validity as the gauge and shows `LAM --`. That capture
exposed overlapping scope text: the two retention counters sat on the
second signal label. On panels below 280 px high they now share a short
line inside the first track. NativeLab rebuilt with `nproc` and passed
the stopped compact, battery/debug compact and Full HD layout captures
3/3. The refreshed `build-lab/sevel-stopped-900x620.png` was inspected;
the lambda, retention and SONDA V labels occupy separate rows.

The two mechanical cameras now fit recorded donor triangles independently
over 16 sampled crank phases instead of using height-dependent zoom and pan
corrections. The same target rectangle is used after resize, focus selection
and `R` view reset; compact framing leaves room for shaft-detail lines above
the head and the control row below the crank. The projection retains one
pixels-per-metre factor for both axes. NativeLab rebuilt with 24 jobs and
passed 14 focused motion, capture, fullscreen and view-selection checks;
the 900×620, 1280×720, 1920×1080 and 3440×1440 captures were inspected.
The fit samples visual poses only and never modifies the running snapshot.
`LabCapture.PhysicalMotion` now captures eight original-ROM ticks from
1,500,000 to 2,150,000 (about 131 ms at the configured tick rate). Besides
checking motion and rising combustion/injection counters, it checks that
bright mechanical pixels remain clear of all four viewport edges in both
views. NativeLab passed this expanded test in 16.63 s. This samples a little
over two revolutions near 1000 rpm; it is not a proof for every continuous
phase or manual zoom position.

The camera reset is also exposed as a `FIT` button beside the view selector.
In the compact layout both buttons moved from the right gauge column into
the free mechanical control row. The same rectangles drive drawing and
mouse hit testing. Two new NativeLab tests zoom with the wheel, click `FIT`
and verify the reset handler at 900×620 and 1920×1080; the compact view
selector and fullscreen return tests also passed (5/5). Both `FIT` captures
were inspected for overlap and framing.

The ignition cluster now separates three existing event classes. Four
numbered discs respond only to combustion outcomes, with a red `!` on a
misfire; pair rows show ECU `PIN` edges and ignition-stage `SPK` events
independently. The display afterglow does not alter their recorded timestamps
or electrical widths. NativeLab rebuilt with 24 jobs, passed the compact and
Full HD captures plus the physical-motion test (4/4), and both ignition
panels were inspected for legibility.

The fuel card now uses `--` when its defined mass or pulse channels lack a
valid reading; `N/D` remains for undefined quantities such as volumetric
efficiency. Its accumulated mass, vapor, film and pulse rows have separate
profile IDs and source tooltips. The tooltips render after the neighboring
gauges so their text remains visible. NativeLab passed the stopped compact,
Full HD and new fuel-tooltip captures (3/3); the tooltip screenshot shows
`FUEL FILM [MG]`, `INTAKE MANIFOLD MODEL`, validity and snapshot tick.

The donor-style gear selector now remains visible at 1280×720 below the
volume bar; mouse shift tests pass there and at 1920×1080. Its N/1–5 state
and total ratio remain visual references without drivetrain coupling.
The compact 150% and 200% layouts now show a horizontal `GEAR N–5 REF`
selector beside the second button row. It shares the desktop selector's
state and click handling; NativeLab captured both compact sizes and passed
all four gear widget tests, including the original 1280×720 and 1920×1080
cards.
An original-ROM NativeLab capture starting at 0 °C demonstrates the coolant
gauge below its 50 °C minimum: the numeric 0.2 °C remains visible while the
needle stops at the scale end and a red `LOW` marker appears. The marker was
enlarged, and `LabCapture.CoolantUnderrange1920x1080` checks that both marker
and numeric glyphs remain present in the captured panel.

`--ui-scale 100|150|200` now configures SDL logical presentation separately
from physical scenario arguments. Layout and hit tests use the logical size;
SDL converts pointer events. The 1920×1080 200% compact layout places the
essential controls above both mechanical views. At 1280×720, 150% and 200%
use a two-row control strip and a compact single-channel scope preview with
`Z:MAX`; the trace still comes from timestamped history. NativeLab passed
the nine capture jobs spanning 1280×720, 1920×1080, 3440×1440 and all three
scales, plus a 200% mouse click that switched to the radial view. A separate
NativeLab 200% test entered fullscreen with F11, captured 1920×1080, returned
to 1280×720, captured again and clicked the scaled view selector. Captures
are in `build-lab/sevel-ui-scale-*.png`. These jobs verify execution and
capture, not a full visual acceptance. Selected signals, cameras, units,
free resize under explicit scale and scope maximize require further validation.

The 1280×720/150–200% right cluster now switches between three compact tabs.
`VITAL` gives RPM, coolant and lambda full-width donor-style dials;
`DATA` lists sonde voltage, manifold pressure, air flow, integrated
injected mass, film, vapor and pulse count with the existing source tooltips.
`IGNITION` reuses the four combustion discs and two PIN/SPK pair rows.
Both views retain the same snapshot and validity flags. NativeLab passed the
200% vital/data/ignition click and capture checks (3/3); the resulting
`build-lab/sevel-ui-scale-200-details-1280x720.png` and ignition capture
were inspected for legibility. Other secondary channels remain pending.

UI scale is now saved in SDL's per-user `presentation.txt` with a versioned,
validated value. Ctrl+1/2/3 selects 100/150/200%; Ctrl+0 restores automatic
scale. An explicit `--ui-scale` is a launch override, and finite-frame captures
ignore saved scale unless the flag is provided. The new NativeLab preference
test used an isolated XDG directory, verified save/reload/reset across
processes, confirmed that a CLI override does not replace the saved value,
and verified that an invalid value falls back to automatic scale.
Camera positions and alternate units are not saved yet.

The desktop column dividers are now draggable. `LabLayout` keeps their shared
boundaries and enforces 220 px for controls, 360 px for mechanics/scope and
280 px for instruments; the button bar receives the same left width for
drawing and hit testing. A 1920×1080 mouse test moved both dividers, clicked
the relocated view selector and captured the result. NativeLab built with
`--parallel 24`; the new drag test and existing donor-style gear widget test
passed 2/2 under the existing graphical test runner. The captured layout was
inspected. NativeLab's direct process currently has no `DISPLAY` or Wayland
display and SDL reports no video device, so direct-desktop validation remains
pending.

The presentation preference now stores UI scale and both desktop divider
fractions in `v4` format. The loader accepts the older scale-only `v1` format,
validates all values and falls back to the usable default on invalid input.
Divider release saves the new proportions; Ctrl+R restores 24/42/34 without
changing the saved scale, while plain R still fits the mechanical camera.
Finite-frame captures ignore saved proportions for reproducibility. NativeLab
built with 24 workers, and the preference, drag and donor-style gear tests
passed 3/3. The preference test covered separate launches, CLI scale override,
divider save/reload/reset, malformed proportions and legacy v1 loading.

The divider interaction test now also clicks the gear card and TPS
oscilloscope preview after resizing both columns. It verifies the relocated
view selector, gear `1` and TPS group in the window title. NativeLab passed
the extended 1920×1080 run; its tick 6,000,000 PNG shows both views, the
selected gear and TPS graph inside their resized panels.

UI-09 now has Bench, Analysis and Mechanics desktop compositions. Ctrl+4/5/6
selects them; Analysis reserves 56% of the height for the scope, Mechanics
reserves 25%, and Bench retains the existing adaptive 40% layout. Both engine
views stay present. The selected mode is saved in the `v4` presentation file,
while `v1` and `v2` remain readable. Ctrl+R resets the mode and dividers.
The status bar identifies the active UI mode separately from the BENCH
scenario label. NativeLab built with 24 workers; mode persistence and two
1920×1080 capture tests passed 3/3. The Analysis and Mechanics PNGs in
`build-lab/` were inspected for motor and scope clipping.

The horizontal divider between mechanics and scope is now draggable in the
desktop layout. It keeps at least 180 px for the scope and roughly 300 px for
the two mechanical viewports; the shared `LabLayout` rectangle drives both
scope drawing and channel hit testing. Its height fraction persists in `v4`
preferences. Selecting a preset or Ctrl+R clears the custom height. NativeLab
built with 24 workers; the preference test and 1920×1080 divider capture
passed 2/2. The capture was inspected with both engine views and TPS scope
inside their resized regions. `v1`, `v2` and `v3` preferences remain readable.

The `v5` presentation preference now also stores analog/digital scope choice,
selected analog group, the two time-window lengths and the four digital
visibility bits. They are read on interactive startup and saved on clean exit;
finite-frame capture runs keep deterministic defaults. The NativeLab
preference test changed the analog group and both time windows with GUI input,
hid one digital channel, restarted the process and verified every restored
value. An invalid channel mask fell back to defaults. That test passed, as
did the horizontal/vertical divider and 200% GUI capture regressions (4/4).
`v1` through `v4` files remain readable. Unit and font preferences remain
pending.

The `v6` presentation preference stores the active mechanical view and each
camera's zoom and pan separately. Pan is saved as a fraction of its viewport;
the first frame fits the engine before restoring the saved camera. Ctrl+R
clears the saved camera through the normal fit path. NativeLab built with 24
workers and the preference test verified distinct zoom/pan for both views,
restart restoration and the active view (1/1). The donor gear card had already
been adapted from `LoadSimulationCluster::drawCurrentGear`,
`drawGearChevron` and `onMouseClick`; its N–5 selection remains a local GUI
reference, without importing donor clutch or transmission physics.

The `v7` presentation preference adds an independent 100/105/110% text size
selected by Ctrl+7/8/9. `FontRenderer` applies the factor to glyph drawing
and text measurement together, so centered labels use the same width as the
visible text. A 130% trial capture exposed header overlap at 1280×720; the
range was reduced, and the four axial cylinder labels now cap their width
against the projected cylinder pitch. NativeLab built with 24 workers and
passed preference, default radial view and 1280×720 capture tests (3/3).
The inspected `build-lab/sevel-font110-1280x720.png` keeps the header and
cylinder labels separate. `v1` through `v6` files remain readable. Unit
selection still needs implementation.

After the font change, NativeLab reran the nine 100/150/200% captures at
1280×720, 1920×1080 and 3440×1440; all passed. The 1280×720 150/200%
and 3440×1440 200% PNGs were inspected for motor clipping, gauge visibility
and header overlap. These checks cover the fixed capture states; they do not
prove every interactive resize or every signal extreme.

The remaining unit preference spans the coolant/speed/pressure gauges,
compact cards, tooltips, status text, scope axes and export metadata. Keep
the published snapshot and SEVEL metric profile as canonical values. The
implementation sequence is: (1) define validated display conversions and
persist a unit choice; (2) route all display and export surfaces through
those conversions; (3) validate round-trip preference, scale labels and
captures in the existing resolution matrix. Changing only a gauge's number
would make its scale and tooltip disagree with the displayed unit.

The `v8` presentation preference adds metric/imperial units with Ctrl+U.
`DisplayUnits` converts value, dial range, bands and tooltip unit together;
the original SEVEL profile and snapshot remain metric. The left coolant,
right coolant/speed/manifold gauges, compact data card, status ECT, thermal
and intake scopes, cursor values and trigger readout use the selected view
units. Scope CSV keeps the original metric values and channel units, adding
`data_units=canonical_metric` and `view_units` metadata. NativeLab built with
24 workers; the preference round-trip and invalid-unit recovery test passed,
as did four focused metric capture/export regressions. The inspected
`build-lab/sevel-imperial-1280x720.png` and
`build-lab/sevel-imperial-thermal-1280x720.png` show F, MPH, inHg and the
thermal scope's converted axes without visible clipping at that size.

The 1280×720 capture at 200% UI scale exposed an interaction with saved
cameras: a zoom from the 100% logical viewport enlarged the motor over the
control row. `v9` preferences now record pane width and scene height and
restore pan/zoom only for compatible viewports at the same UI scale. A CLI
scale override leaves the saved camera untouched; the new viewport uses its
automatic fit. The compact radial overview omits individual cylinder labels
when they collide with its subtitle. NativeLab rebuilt with 24 workers;
preference migration (`v1`–`v8`), camera restoration/fit, unit toggle and
CSV checks passed. The inspected `build-lab/sevel-imperial-200-1280x720.png`
shows both mechanical views inside their panels without the earlier overlap.
The default metric 100/150/200% capture matrix at 1280×720, 1920×1080 and
3440×1440 was then rerun under NativeLab after the `v9` change (9/9).

Scope CSV and its paired PNG metadata now include exported sample count,
retained-history gaps over 250 ms, cumulative raw/archive eviction counts,
and the archive sampling policy. This makes sparse long-window exports
distinguishable from uninterrupted raw history. NativeLab passed the TPS CSV,
thermal scope and preference/imperial CSV checks (3/3).

For UI-43, the donor's `.work/donor-gl-current-1920x1080.png` and the
Lab's `build-lab/sevel-stopped-after-1920x1080.png` permit a 1920×1080
layout comparison with both engines stopped. They do not represent the
same engine or physical scenario. The Lab capture at tick 1,500,000 uses
the original Fiat Tipo ROM and reports 0 rpm and 0 burns. The comparison
exposed a display-only error: a tiny negative modeled intake flow rounded
to `-0.0 g/s` while the gauge also showed `LOW`. The compact DATA card
and desktop air-flow dial now normalize magnitudes below 0.05 g/s to zero
at their displayed 0.1 g/s precision; the raw snapshot and scope keep the
model value. A same-scenario before/after PNG comparison changed 893 RGB
pixels, confined to `(1596,873)-(1796,885)` in the air-flow panel. NativeLab
built with 24 workers, captured both states, and passed the stopped compact
and 200% details capture tests (2/2).

The 1920×1080 stopped comparison also showed a red `! MISS` label with no
misfire event. The ignition panel now displays that warning only while a
recent misfire pulse is visible; otherwise it shows a muted `MISS` legend.
The original-ROM stopped capture reports 0 burns, and the controlled PNG
comparison changes only 94 pixels within `(1861,23)-(1900,29)` in that
label. NativeLab rebuilt with 24 workers and passed the stopped compact,
200% details and combustion/misfire scene tests (3/3).

UI-43 now also has a 1920×1080 original-ROM state matrix in
`.work/gui-review/`, with a PNG and execution log per row:

| State | PNG stem | Tick | RPM | CC3 / burns |
| --- | --- | ---: | ---: | ---: |
| Key off | `matrix-stopped-1920x1080-t800000` | 800,000 | 0 | 0 / 0 |
| Auto-start idle | `matrix-idle-1920x1080-t800000` | 800,000 | 940 | 15 / 13 |
| Replay: pedal 8 mm, load 24 N·m | `matrix-replay-load-1920x1080-t800000` | 800,000 | 655 | 10 / 8 |
| Paused after auto-start | `matrix-paused-1920x1080-f12` | 1,574,500 | 1011 | 40 / 38 |

The first three logs reproduce the exact physical-state and event hashes
of their 1280×720 counterparts, so changing resolution did not change the
simulation at that tick. The paused capture uses F12 after checking that
the tick remains fixed; its tick differs from the older 1280×720 paused
image and is not a before/after pair. The 1920×1080 idle, replay and
paused PNGs were visually inspected for both engine views, gauges and
scope. NativeLab passed all four captures and the existing compact/F12
regressions (2/2). More scenarios are still needed for the full UI-43/44
matrix, especially high load and continuous resize.

The high-load replay fixture `tests/data/lab_control_high_load.txt` holds
25 mm pedal pull and 60 N·m applied load, both within the existing GUI
control range. At tick 3,000,000 the original-ROM capture reports 768 rpm,
59 CC3 events and 57 burns; the lambda and sensor-voltage traces show the
rich transition. The before/after pair
`matrix-high-load[-after]-1920x1080-t3000000.png` and matching logs are in
`.work/gui-review/`. Both runs have identical physical-state and event
hashes. The replay pedal bar now labels its displayed 25 mm value alongside
`REPLAY`, while the TBI panel separately shows the applied cable position.
The updated label was visually checked at 1920×1080 and 1280×720. NativeLab
built with 24 workers; replay mouse lock, gear card and stopped compact
regressions passed (3/3). The later resize and deterministic pause checks
are recorded below.

`LabControls.ResizeSweep` now exercises one live original-ROM window through
1280×720, 1440×810, 1600×900, 1920×1080, 900×620 and back to 1280×720,
with six intermediate window sizes between each stop. It saves a PNG at
each stop and checks its complete dimensions. At 1920×1080 it clicks the
radial-view selector; after returning it clicks the axial selector and the
first-gear card, checking the resulting window title. The 1920×1080,
900×620 and returned 1280×720 captures were visually inspected: both
mechanical views, scope and gauges stay inside their panels. The test's
first implementation blocked when its unread ROM stdout pipe filled; a
temporary log file removed that test-harness stall. NativeLab then passed
the resize sweep twice and the fullscreen return test once. The compact
900×620 layout now also has a visible gear card between the shortened volume
bar and the pedal command. It uses the same selected N–5 state and click
handler as the larger cards; the narrow label shows the gear and `REF` between
its two arrows. The 900×620 stopped and shifted PNGs were inspected, and the
new pointer test selects third gear after two Q/E steps. NativeLab rebuilt
with 24 workers and passed all five gear-card sizes plus the live resize
sweep (6/6). The deterministic paused pair is recorded below.

The same horizontal gear card also fits the 900–1099 px compact range below
620 px height. Above 900 px width, the volume bar now leaves room beside the
pedal bar and the card derives its rectangle from those two controls. The
1000×600 original-ROM capture shows `3 REF` with separate arrows after two
keyboard upshifts and one pointer click. NativeLab passed the 900×620 and
1000×600 gear hitbox checks plus the resize sweep (3/3).

`tests/data/lab_pause_capture.txt` pauses the original ROM at exactly tick
1,500,000. The F12 helper now accepts that replay, checks that the tick
stays fixed, and captures the paused window. At both 1280×720 and 1920×1080,
`.work/gui-review/matrix-paused-replay[-after]-<size>.png` and their logs
form same-resolution, same-scenario before/after pairs. All four logs have
physical-state hash `7b1a245fae2c534f` and event hash
`be5cbae7309133bf` (998 rpm, 30 CC3 events, 28 burns). The header now
says `PAUSED REPLAY` when both conditions hold; the disabled pedal bar still
identifies replay separately. Other changed pixels include gauge-needle
animation at capture time, so the full PNGs are not bitwise-equal outside
the header. NativeLab built with 24 workers and passed both deterministic
paused captures, the normal F12 capture and replay mouse lock (4/4).

At 900×620, the original-ROM 0 °C capture exposed an overlap between the
lambda dial's `LOW` marker and its numeric value. Short dials now place the
larger range marker below the title while taller dials retain the bottom
position. `LabCapture.CoolantUnderrange900x620` checks that the coolant marker
and number remain visible and that the lambda marker stays above its value;
the existing 1920×1080 under-range check also passes. Both captures and the
24-worker build ran through NativeLab.

The 3440×1440 original-ROM high-load replay now has a permanent NativeLab
capture test. At tick 3,000,000 it shows 60 N·m applied load, 25 mm pedal
command, 59 CC3 events and 57 burns. The captured frame was inspected at
100% UI scale: both engine views, the gear card, gauges and lambda scope stay
within their panels, and the `REPLAY` label is visible. The separate 200%
3440×1440 bench capture also passed after the dial-marker change. Registering
the high-load CTest exposed a replay-fixture path relative to the caller's
working directory; the capture script now resolves both replay fixtures
relative to itself, and the CTest passes from `build-lab`.

Axial focus now carries into the analysis context: the scope heading says
`CYL 1 VIEW` or `CYL 2 VIEW`, and the matching cylinder receives a second
outline in the 1–3–4–2 combustion strip. These are view indicators; scope
channels and event timestamps are unchanged. Original-ROM NativeLab captures
for axial 1/4 at 1920×1080 and axial 2/3 at 3440×1440 were inspected, and
both tests plus the compact coolant under-range regression passed (3/3).

The debug row now uses `--` for unavailable pedal, load, film or vapor
channels instead of presenting their fallback numbers as live measurements.
At 1280×720, the donor-style gear card previously covered part of the audio
diagnostics below the volume bar. The audio labels now fit on either side of
that card; the original-ROM debug capture was inspected after the change.
NativeLab built with 24 workers and `LabCapture.BatteryDebug1280x720` passed.
The donor `LoadSimulationCluster` also has a clutch-pressure gauge, but this
Lab has no clutch-pressure signal or modeled clutch state to drive it yet.

Hovering over the donor-style N–5 card now shows the selected Fiat manual
ratio, 63/16 final drive and their recomputed product. The tooltip marks the
selection as a reference and states that road speed is scenario input; it
does not imply a working clutch or torque transfer. The original-ROM
third-gear capture at `build-lab/sevel-gear-tooltip-1920x1080.png` was
inspected, and the new NativeLab capture test plus both existing 1920×1080
and 1280×720 gear-card interaction tests passed (3/3).

The adjacent donor clutch gauge is now represented on Full HD and wider
bench layouts with its original 0–100 tick scheme. It displays `N/D` without
a needle because no SEVEL clutch pressure or coupling state is published; a
hover tooltip names that missing source. NativeLab built with 24 workers and
passed the 1920×1080 gear and tooltip captures and the 3440×1440 high-load
capture (3/3). Both screen sizes were visually inspected for overlap.

The ECU inspector's CC3/injector count, burn count and crank phase now honor
producer availability. Missing counts and invalid phase display `--` instead
of a plausible zero; finite phase still uses the shared 720-degree reference.
NativeLab rebuilt with 24 workers and the 1280×720 debug capture passed.

The 1280×720 compact capture at 200% UI scale exposed the volume label
touching the slider fill. Short volume bars now use a smaller label placed
higher inside their rectangle; their fill and hitbox are unchanged. NativeLab
built with 24 workers, passed the 100%, 150% and 200% captures (3/3), and
all three refreshed PNGs were visually inspected.

The full NativeLab UI-scale capture matrix now passes at 1280×720,
1920×1080 and 3440×1440, each at 100%, 150% and 200% (9/9). The refreshed
1280×720 triplet and the 150%/200% desktop and ultrawide captures were
visually inspected. The 1920×1080 200% capture confirms the compact gear
card beside volume and pedal; the 3440×1440 200% capture keeps both engine
views and the right instruments inside the window. These checks cover fixed
capture sizes; free resize and fullscreen are tracked separately.

The audio slider now distinguishes key-off, simulation pause and suspended
playback above 1× instead of labeling all three conditions `PAUSED`. A
NativeLab original-ROM capture at
`build-lab/sevel-audio-fast-1920x1080.png` shows `SUSP>1X 100%` at 2×;
`LabCapture.AudioFast1920x1080` and the existing audio pause/speed/key test
passed (2/2). No audio worker, synthesis or simulation timing changed.

The tachometer now calls the adapted donor `Gauge` for its gamma sweep and
major/minor tick decisions, using the Fiat 0–8000 rpm, 1000/200 rpm profile.
Its needle is the donor's constant-width line geometry (4 px in the normal
window) with the existing value and availability contract. The 1920×1080
and 1280×720 original-ROM captures were inspected; NativeLab built with 24
workers and passed both captures plus the two donor-gauge tests (4/4).
Other dials still use the SDL adaptation pending the component migration.
The same needle was checked at 200% UI scale in 1280×720 and 3440×1440
NativeLab captures; both tests passed and the refreshed PNGs show the pointer
inside the tachometer at each logical size.

The gear card retains the donor's title/body proportions and now fits its
24/64 px text, 0.28 chevrons and 3 px strokes to the available bands. The
original-ROM gear mouse tests passed at seven desktop and compact sizes.
The remaining profile dials now use donor `Gauge` sweep, tick and needle
geometry with their SEVEL scales; the unavailable clutch dial uses the donor
upper arc. NativeLab built with 24 workers and passed the Full HD, both
200% UI and coolant underrange captures. The compact coolant test's needle
mask was narrowed to exclude the now wider donor-style lambda needle.

The gauge cards now scale their titles and numeric values with the space
available, up to 24.5 px for a principal reading in the normal 1920×1080
layout. Value baselines move upward with font size so units stay inside the
card. NativeLab rebuilt with 24 workers and passed the 1920×1080, 1280×720,
200% UI and both coolant-underrange captures (6/6); the Full HD PNG was
inspected for dial text and divider overlap.

The donor `LabeledGauge` band/radius math now lives in a backend-neutral
layout component used by the SEVEL dials. The existing donor gear widget is
also backed by a shared layout for its title, arrows, number and click zones;
the compact horizontal variant remains a SEVEL adaptation. Neither component
imports donor drivetrain physics. NativeLab built with 24 workers, passed the
eight gearbox tests plus Full HD and 200% UI captures (10/10), and the Full HD
gear tooltip PNG was visually inspected.

The `Gauge` adapter now derives major ticks from the major/minor interval
ratio. Independent rounding of converted Imperial steps could otherwise
erase principal marks on MPH and inHg dials. NativeLab reported 24 CPUs,
built with 24 workers, and passed the UI preference round-trip plus Full HD
and 200% captures (3/3). The refreshed Imperial PNG was inspected with F,
MPH and inHg scales visible.

`docs/SEVEL_LAB_VISUAL_MATRIX.md` now indexes five 1920×1080 Lab
before/current pairs: stopped, warm idle, replayed 24 N·m, replayed
60 N·m with pedal, and paused replay. The current high-load frame was
captured at tick 3,000,000; its direct NativeLab run matched the earlier
ROM state and event fingerprints. Four other current frames were checked
for dimensions and CC3/burn counts. Five focused capture tests passed,
including the compact stopped and 3440×1440 high-load layouts.

The analog scope header now prefixes its displayed cadence with `SNAP`:
its Hz figure comes from retained snapshot intervals and is not a sensor
or ECU channel update frequency. The 200% compact header keeps the short
group name and LIVE/HIST state when the full heading does not fit.
NativeLab rebuilt with 24 workers and passed Full HD, 200% compact,
thermal-scope and TPS CSV captures (4/4); after the compact fallback fix,
the three affected image captures passed again (3/3) and were inspected.

ADC last-conversion voltage traces now use zero-order hold in the main
scope, compact trace and group miniatures. The fault fixture's 5 V interval
appears as a rectangle with vertical entry/exit rather than an invented
ramp; invalid readings and intervals over 250 ms still split the trace.
NativeLab rebuilt with 24 workers and passed the three ADC fault/group
captures plus Full HD and 200% compact captures (5/5). The ADC TPS fault
PNG was inspected after the change.

ADC scope legends now report `AGE` in milliseconds from each channel's
last conversion tick to the displayed snapshot tick. This makes the
snapshot-positioned step explicit while the CSV continues to carry the
exact conversion timestamp. NativeLab rebuilt with 24 workers and passed
the three ADC group captures plus the 200% compact capture (4/4); the
ADC TPS fault PNG was inspected for label fit and separate channel ages.

The SEVEL dial adapter now positions titles and numeric values from the
donor-derived `LabeledGaugeLayout` bands, alongside its existing radius and
needle geometry. NativeLab reported 24 CPUs, rebuilt with 24 workers, and
passed five Full HD, compact and 200% capture tests (5/5). The refreshed
1920×1080 PNG was inspected for title/value clearance.

The analog A/B cursor difference row now includes each channel's displayed
unit, including unit conversions selected in the UI. NativeLab reported 24
CPUs, rebuilt with 24 workers, and passed the five TPS, frozen-scope and
scope-navigation captures (5/5). The frozen Full HD PNG shows the voltage
difference beside its original-sample time difference; a missing lambda
sample remains `N/D` instead of producing a fabricated delta.

The four Full HD before/current matrix scenarios were refreshed with the
current renderer in NativeLab (4/4). Stopped, idle, replayed load and high-load
CC3/burn counts matched their earlier scenario logs. The high-load state and
event hashes were unchanged, and all four before/current mechanical crops
remain pixel-identical. The high-load current PNG was visually inspected.

The right-panel throttle bar now uses the donor `RightGaugeCluster` control
rectangle proportions instead of a fixed 12 px stripe. Its fill still reads
the published SEVEL pedal position; the separate command slider and mouse
semantics are unchanged. NativeLab reported 24 CPUs, rebuilt with 24 workers,
and passed Full HD, compact stopped, 200% UI and 3440×1440 high-load captures
(4/4). The refreshed Full HD PNG was inspected for the bar's fit and clearance.

The whole right instrument cluster now reads one backend-neutral layout
extracted from the donor `RightGaugeCluster` and `AfrCluster`. It assigns the
tachometer, speed/coolant, ignition, throttle, sensor pair, fuel and three
intake cells. The former 48/52 sensor/fuel split is now the donor's equal
half split. NativeLab built with 24 workers and passed Full HD, compact,
200% UI, 3440×1440 high-load and fuel-tooltip captures (5/5); the refreshed
Full HD PNG was inspected for cell fit and label clearance.

The debug status no longer labels the published injector-pulse count as
`CC3`; it now says `INJ PULSES`, leaving `CC3` for the electrical pin scope.
NativeLab reported 24 CPUs, rebuilt with 24 workers, and passed both battery
debug captures plus Full HD (3/3). The 900×620 and 1280×720 debug PNGs were
inspected for the longer label's fit.

The donor-derived gear card now shows an ideal wheel RPM reference computed
from published crank RPM and the Fiat gear and final-drive ratios. Neutral
is undefined; missing or nonfinite crank RPM produces `--` rather than a
plausible zero. The tooltip states the engaged-clutch assumption and keeps
scenario road speed separate. This is kinematic presentation only; clutch,
wheel speed and crank load remain uncoupled. NativeLab built with `nproc`
workers and passed the two transmission calculations plus the Full HD gear
widget and tooltip captures (4/4). The refreshed tooltip PNG was inspected.

The analog scope now uses the donor `Grid` to place its focused plot above
group previews. A tall panel uses two rows; the drawing
and click selection share the same cells. The plot bands and cursor/footer
positions follow the new focus rectangle, preventing traces and labels from
crossing into the previews. The 1280×720 layout condenses retention counters
to one line. NativeLab rebuilt with `nproc` workers and passed scope-card
selection on both rows, drag and resize interactions, frozen scope, 720p,
compact and ultrawide captures. The Full HD TPS/FUEL and 1280×720 PNGs were
visually inspected. Xvfb tests now move the resized window to `(0,0)` so its
lower cards remain reachable by mouse on a same-size virtual screen.

The left TBI card now spaces its three measurement rows and gear reference
from its own height; their hover regions follow the same row positions.
This keeps the gear text above the lower border at 1280×720 and at Full HD
without reducing the font. NativeLab rebuilt with `nproc` workers and passed
the 1280×720, 1920×1080 and 3440×1440 captures (3/3); the first two PNGs
were inspected for the TBI border clearance.

The analog scope now has an `IDLE` group for the candidate idle-actuator stem
in mm and the sampled physical idle contact in a separate state lane. The
contact is drawn as a held step, including every retained transition within
one screen column; unavailable producer samples remain gaps. Its CSV exports
both source channels with IDs and provenance. The stem's -10 to 30 mm display
range is a laboratory scale, not an asserted actuator stroke. NativeLab built
with `nproc` and passed the new Full HD capture/CSV test plus the existing TPS
scope test (2/2). Additional 1280×720 and 900×620 live-ROM captures passed;
all three `IDLE` PNGs were inspected for card fit and trace visibility.

The focused analog scope now has a manual `FIT Y` button and `O` shortcut.
It computes padded per-band limits from valid samples in the visible tick
window once, then holds those limits until `Y:RESET`, another fit, a group
change or a unit change. A sampled state lane keeps its fixed 0–1 scale.
NativeLab built with `nproc` and passed the Full HD idle-fit, idle-fixed and
TPS scope captures (3/3). The fitted idle PNG was inspected: its stem axis
shows about 6.1–9.3 mm and its sampled contact axis remains 0–1. The fit
capture test clicks the visible button and checks the logged fitted range.
The same button now has NativeLab click/CSV checks at 1280×720 and 900×620.
All three sizes passed (3/3); each fitted interval contains every valid
exported stem sample up to its recorded fit tick, and the 720p and compact
PNGs were inspected for button and trace clearance.

The 100 ms scope archive now includes the candidate idle-stem position in
its extrema selection. It also retains samples on both sides of availability
and finite-value transitions so a short invalid interval is not hidden by
the long-window reduction. The original-ROM archive determinism test now
checks the stem's early minimum and maximum alongside RPM, lambda, TPS,
coolant, manifold pressure and fuel film. NativeLab built with `nproc` and
passed that test and the Full HD idle-scope capture (2/2).

The same archive now preserves valid ADC0/1/2/3/5/6 pin-voltage extrema
within each 100 ms block and both sides of a transition to or from a stale
or unavailable conversion. The original-ROM determinism test compares each
channel's early minimum and maximum conversion against retained history,
including the original conversion tick. NativeLab built with `nproc` and
passed the extended archive test (1/1). A held conversion can be attached to
several snapshots, so the test accepts any retained snapshot carrying that
same conversion and voltage.

The archive's lambda-extrema selection now uses the scope's full validity
condition: crank available and first exhaust sample received. Earlier
pre-exhaust lambda values cannot consume extrema slots or appear as valid
long-window readings. Sensor voltage keeps its separate crank-based validity.
The original-ROM archive determinism test checks the valid lambda extrema;
NativeLab rebuilt the Lab and test with `nproc` and passed it alongside the
Full HD idle-scope capture (2/2).

The donor-style right throttle card now has separate source/validity tooltips
for the physical angle, cable position, candidate idle stem and sampled idle
contact. Their hit regions follow the donor throttle-control rectangle and
the two SEVEL detail rows. A Full HD capture exposed a draw-order issue:
later manifold/air gauges covered the tooltip text. The tooltip pass now
runs after all right-hand gauges. NativeLab rebuilt with `nproc`, passed the
fuel and new throttle-tooltip captures (2/2), and the final PNG was visually
inspected with its complete source and validity text visible.

Analog cursor rows now distinguish missing samples from undefined channels:
they show `--` for a missing reading and for its unavailable two-cursor
difference. NativeLab rebuilt the Lab with `nproc`; the Full HD idle and TPS
scope captures passed (2/2). A dedicated cursor-value fixture is still
required to verify the numerical readout against known source samples.

The analog cursor now searches only samples inside the visible time window,
so an adjacent hidden sample cannot suppress a valid edge reading. The
selection helper returns a source index and keeps the original 250 ms gap
limit and earlier-sample tie rule. A fixture checks known timestamps and TPS
values, window edges, empty gaps, and A/B difference; NativeLab built both
the GUI and test binary with `nproc`, then passed that fixture and the idle
and TPS scope captures (3/3). A separate rendering assertion is still needed
for the formatted units and `--` text in the PNG readout.

Frozen and panned analog scopes now take legend values, ADC sample age and
fan/idle contact labels from the last valid source sample at the displayed
end tick, within the existing 250 ms gap limit. The live snapshot is used
only while following live time. A Full HD frozen TPS capture exposed A/B
readout text over the preview cards; the scope reserves a dedicated footer
and uses one preview row in medium-height panels. The updated Full HD PNG
was inspected with A/B, delta, time and previews separated. NativeLab built
with `nproc` and passed six focused freeze, CSV, preview/card and compact
scope tests (6/6). The card-click fixture now derives its target from the
same 11-card grid rather than assuming ten cards.
The 1280×720 idle scope fit capture also passed and was inspected: its
single-row group selector remains inside the panel below the plot.

Analog A/B and delta strings now share pure formatting functions with a
known-value fixture for timestamps, units, two-decimal values, missing
channels and signed differences. CSV selection now uses the same snapped
source ticks shown by the cursor lines; the real-ROM TPS export test asserts
that both boundary ticks are present as first/last data rows and in CSV
metadata. NativeLab built the GUI and unit binary with `nproc` and passed
the two cursor fixtures plus the Full HD frozen and CSV captures (4/4).

The ECU digital pin lanes now report low interval, rise-to-rise period and
duty when a complete rise–fall–rise cycle is retained. The high label uses
that same cycle; an isolated high pulse is still shown without inventing a
period. The measurement helper reads exact `EmulatorEvent.tick` edges in the
visible window, independent of minimum pulse width in pixels. A synthetic
one-tick pulse fixture checks high/low/period/duty and incomplete cycles.
NativeLab built with `nproc`; the digital zoom/events captures and fixture
passed (3/3), and the Full HD digital screenshot was inspected.

Digital A/B cursors now snap to retained CC3 and ignition-pin edges within
12 display pixels. The lines, HIGH/LOW state, exact event tick and A/B time
difference use the original event timestamps, even when the visible pulse
has a minimum pixel width. The idle-contact lane now snaps to the first
valid snapshot observing a contact transition, with its readout marked
`IDLE SAMP`. Missing samples and gaps above 250 ms prevent a transition
from being inferred. Synthetic pin-edge and sampled-contact fixtures plus a
live-ROM Full HD pin-click capture passed in NativeLab with `nproc`; the
capture was inspected.

The Open Engine Sim gear card was already adapted through
`gear_card_layout.h`: its title, chevrons, number and click regions match
the donor's proportions. The Fiat N–5 ratios and 63/16 final drive appear
in its tooltip; the adjacent donor-style clutch gauge still reads `N/D`.
The donor's transmission solver uses a clutch torque constraint and vehicle
equivalent inertia `mass * (tire_radius / (differential * gear_ratio))²`.
Those inputs and a coupled vehicle state are not yet present in the SEVEL
session, so the current ideal wheel RPM remains a labeled kinematic
reference. The donor gear tooltip capture passed alongside the digital
cursor capture in NativeLab.

The original-ROM replay with pedal commands at ticks 500,000 and 900,000
now has a dedicated Full HD digital-contact capture. Two real GUI clicks on
the sampled contact lane produced `IDLE SAMP` cursors on the first observing
snapshots at ticks 500,000 and 900,000: 0.505051 s OPEN and 0.909091 s CLOSED.
The screenshot shows the 404.040 ms difference and both cursor lines without
changing replay controls or electrical edge data. NativeLab passed
`LabCapture.DigitalIdleCursors1920x1080` (1/1); its PNG was inspected.

The same real-ROM replay now exports the digital A/B selection through `C`.
Its CSV contains the original pin/marker event ticks and sampled idle-contact
transitions, sorted by tick and bounded by the selected 500,000–900,000 ticks.
The header records the 990 kHz clock, sources, ROM/scenario, selection and
visible ranges, and event overflow; the cropped PNG embeds that header.
NativeLab passed the record-selection fixture and replay export capture
(2/2). The CSV's 56 records and cropped PNG were inspected.

`X` now freezes the digital scope independently of simulation pause. The Lab
retains the event window, contact snapshot window, source tick, event-base
index and overflow count at capture time. Digital cursor clicks and CSV/PNG
export read that same retained window; another `X` resumes live following.
The replay GUI test exported both live and frozen selections at ticks
500,000–900,000, then advanced the motor to tick 2,000,000 with the scope
still marked `FROZEN`. Its Full HD screenshot was inspected in NativeLab.

The digital scope now uses its drawn time axis for pointer-centered wheel
zoom. The first zoom retains the available event and sampled-contact window;
middle-button drag pans within that retained interval, `X` returns to live
following, and a double-click restores the default two-second span. The
first middle-button drag from a live scope also captures the available
window before panning. Both navigation capture tests assert the `FROZEN`
title before applying wheel zoom, so this entry path is covered. The
original-ROM digital-navigation captures at 1920×1080 and 1280×720 checked
the one-second zoomed interval, an earlier end tick after panning, and the
restored two-second live interval through three CSV exports. NativeLab also passed the
existing digital zoom and cursor captures after this change. The exported
PNG was visually inspected.

The digital scope heading now spells out `LIVE X:FREEZE` or
`FROZEN X:LIVE`, matching the analog scope's acquisition state while the
separate `PAUSE` motor control remains visible at left. Both navigation
captures passed after this change; the 1280×720 heading was inspected.

The TBI panels now use `--` for an unavailable candidate actuator stem,
matching the stem profile tooltip's `MISSING` state. The right throttle
drawing evaluates angle, cable, stem and idle contact separately; an absent
angle or cable no longer erases a valid contact or stem reading. NativeLab
built with `nproc` and passed Full HD layout, compact stopped and throttle
tooltip captures (3/3); the refreshed tooltip PNG was inspected.

UI-27/45 now has a direct source-series cadence check. The original-ROM
warm scenario replays to 1.5 s without polling and with snapshot consumers
at 8 ms and 32 ms intervals. All 3,000 retained sample ticks, physical
signals, ADC conversion observations and 181 digital event timestamps match
exactly. The existing GUI frame-delay/audio test also passed at 8/32 ms;
NativeLab built the determinism executable with `nproc` and passed both
tests (2/2). This verifies acquisition independence from consumer polling
for this scenario; longer archive and reset paths have separate tests.
The decimator fixture also now covers a nonfinite sample, a long gap and
a nonmonotonic tick reset in one source sequence; its selected indices keep
the peak and each segment boundary. Both decimation tests passed in NativeLab.

UI-43's four 1920×1080 original-ROM scenario pairs were refreshed after the
recent TBI, scope and label work. Stopped/key-off, idle, 24 N·m replay and
60 N·m/25 mm replay each passed the capture script. For every pair, the
complete `[LAB-STATE]` line is identical before/current, and an RGB compare
finds zero changed pixels in the mechanical crop `(462,90)–(1265,635)`.
The stopped and high-load frames were inspected; the paused replay capture
also passed and was inspected. The paused before/after logs likewise match
in full at tick 1,500,000, with state `7b1a245fae2c534f` and event hash
`be5cbae7309133bf`; its mechanical crop has zero changed RGB pixels.
`docs/SEVEL_LAB_VISUAL_MATRIX.md` links all five matched pairs.

UI-44's presentation pass covered the 3×3 matrix of 1280×720, 1920×1080
and 3440×1440 at 100%, 150% and 200%, plus the live resize sweep and both
fullscreen/return paths. NativeLab passed all 12 targeted tests after the
scope heading fix. At 1280×720 and 200%, the analog title had extended under
FIT Y; it now falls back to `LAMBDA LIVE` within the available heading area.
The refreshed PNG was inspected. One ultrawide capture initially lost an
`xdotool windowsize` race, passed alone, and passed in the rerun; the capture
script now retries that window-manager operation for up to two seconds.

The donor transmission and vehicle formulas were checked again: engaged-gear
equivalent inertia is `mass * (tire_radius / (diff_ratio * gear_ratio))²`;
vehicle speed follows the virtual shaft energy and mass. The Fiat ratio
products and ideal wheel RPM are already shown as a reference. A tire radius,
clutch torque state and coupled vehicle inertia are still required before
these donor equations can drive the SEVEL road-speed gauge; it remains labeled
as a scenario input.

The gear tooltip now also computes ideal road speed from wheel RPM and
`2π × 0.29 m` rolling circumference. The 0.29 m radius is explicitly an
estimate because the available Fiat manual lacks a tire specification;
the tooltip labels both this assumption and engaged clutch. It does not
replace the scenario road-speed gauge. NativeLab passed three transmission
tests, the Full HD gear tooltip capture and the 1280×720 200% capture (5/5);
the refreshed gear tooltip PNG was inspected.

The 1280×720/200% screenshot test now checks the analog heading region:
it requires visible title pixels and no title pixels in the FIT Y button's
reserved strip. NativeLab passed this region check. In the 38-test scope
suite, 37 passed initially; the divider test exposed a stale click coordinate
from the old two-row card grid. After dragging to a 348 px scope, the grid
becomes one row, so its TPS card click now uses the resulting cell center.
That test passed alone, and its Full HD PNG was inspected with TPS selected
and both engine views visible. This was a test-hitbox correction; the
renderer and physical state were not changed.

The ECU inspector now repeats `STALE` in its title when the live snapshot
stops advancing while debug is open. The title fits within the space before
the lamp candidate label. NativeLab rebuilt with `nproc` and passed the
1280×720 and compact 900×620 debug captures (2/2); both PNGs were inspected.

UI-44 found a compact status-line overflow in the 900×620 debug capture:
`SOUND ON` crossed the header's right border toward the instrument column.
The shared status drawer now fits row 1 to the header's available width.
NativeLab rebuilt with `nproc` and passed compact stopped/debug, Full HD and
1280×720/200% captures (4/4). The compact debug PNG was inspected. Its test
now checks visible status text and zero bright text pixels in the gap before
the instrument column; the refreshed test passed separately (1/1).

UI-06 removed the remaining `0.24`/`0.66` column calculations from the
button rectangles. Their drawing and hit testing now read the corresponding
`LabLayout` bounds at desktop and compact sizes. The button geometry test
target links SDL3 for that shared header. Its old visibility expectations
and an empty-space probe were updated to the current compact button row;
the UI-preferences test now clicks the CC3 selector in its visible digital
lane. NativeLab rebuilt with `nproc`. The button and preferences tests passed
individually (2/2); six other focused mouse, replay, fit and capture tests
passed after the production edit.

The candidate tachometer now reads P1.1 rising-edge periods, independently
of physical RPM; the inspector compares physical RPM, RAM47*25, RAM46*25
and P1.1 with its pulse count. The cable acceleration investigation reached
about 5,044 RPM and found variable revolutions per P1.1 edge, so wiring and
pulses/revolution remain unverified (see `.work/P11_TACOMETRO_INVESTIGACAO.md`).

Gauge needles and tick marks now call the incorporated OES
`GeometryGenerator::generateLine2d`; the extra central square and duplicate
SDL major-tick strokes were removed. The shared line adapter reuses one
geometry buffer within each dial and applies the donor width fields.
NativeLab passed five DonorGauge tests, including mathematical label-layout
and needle-width checks at 100/150/200%. A batched presentation run passed
all nine resolution/scale captures and both debug captures (11/11).
The 1280x720/200% and 900x620 debug PNGs were inspected: the new needle/ticks
render, both engine views remain present, and the RPM comparison fits the
inspector. This is not a fresh acceptance of all 46 requirements; other
interaction/backend checks and donor component work remain open.
