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
