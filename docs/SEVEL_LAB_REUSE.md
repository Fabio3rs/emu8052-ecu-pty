# SEVEL Lab donor reuse

The presentation donor is the local `open-engine-sim` checkout at commit
`1e226ee7bfbeb1d5012c7696aee82a57355df281`. Its root license is MIT;
the original Ange Yaghi copyright and license text are in
`third_party/open-engine-sim/LICENSE`. The local upstream `engine-sim` checkout
at `85f7c3b959a908ed5232ede4f1a4ac7eafe6b630` is a comparison source,
not a build dependency. No proprietary community-edition files are imported.

The donor checkout currently has local changes in
`assets/shaders/engine_sim.vertex.spv`, `src/desktop_main.cpp` and
`src/sdl_gpu_renderer.cpp`. Their working-tree SHA-256 values are
`9d61d719d3366b118158fb14c2325ca0ef4b1c38e57f7306b0f1c590e7d09c8b`,
`24fea13743a6005dfdec53c43e460bf24935a168e476b2a6529ffb5978662ca9`
and `541599fe5e62584782f10dfd1dd2ebe6916d0a64fbfeb136b74a8e6d6f7c0bd6`
respectively. The imported shader and renderer adaptations are itemized
below; `desktop_main.cpp` is not imported. The local `SDL_shadercross`
checkout is at `1ff05bec573988a98ef9e0260b4da44f512b8367`.

| Donor path | Local path | License | Modification | SHA-256 |
| --- | --- | --- | --- | --- |
| `include/renderer.h` | `third_party/open-engine-sim/include/renderer.h` | MIT | None | `60729e83c038d4510ce9f01180b562049d72cb05ed91d36c9d50e3107e5bf8` |
| `include/render_math.h` | `third_party/open-engine-sim/include/render_math.h` | MIT | None | `4fe33a3c8cc39bdf1011032257f83504da0838f8a6fb89a91d1f3d884e6270dd` |
| `include/shaders.h` | `third_party/open-engine-sim/include/shaders.h` | MIT | None | `494f7f024b749c1073d2148b821ecab0e1ccfbd3e27c7fa9c3e331f59fb27629` |
| `src/shaders.cpp` | `third_party/open-engine-sim/src/shaders.cpp` | MIT | None | `37bf29a66304f6608bf871bcc70541e22426b65052096cb3803d631f0709288d` |
| `include/sdl_gpu_renderer.h` | `third_party/open-engine-sim/include/sdl_gpu_renderer.h` | MIT | Added runtime failure query, claimed-window state and scene readback for the Lab preview | Donor `4120785969dbfa2fdfb6ac565872191f9b0845356ba6eb8f4f78b5f8f250ce0e`; local `bba4add4d78f36918235010fe207585026b53df50b2592aa4ed1e135514469d4` |
| `src/sdl_gpu_renderer.cpp` | `third_party/open-engine-sim/src/sdl_gpu_renderer.cpp` | MIT | Bound blit to acquired swapchain size; report GPU failures; release a window only after a successful claim; read back the scene texture | Donor `d2ea282d5d5e8e6abca5d4ba60c166adec731163f64106478191b52196ce293c`; local `38e433a301a4aa10a180a5691c2e1385048cc0c4df8657fcb28c0d952fff139f` |
| `assets/shaders/engine_sim.hlsl` | `third_party/open-engine-sim/assets/shaders/engine_sim.hlsl` | MIT | None | `1b2a84ac016479f75778f01ab05ef0c0000b99fca1017e587de9965183d69a8f` |
| `assets/shaders/engine_sim.vertex.msl` | `third_party/open-engine-sim/assets/shaders/engine_sim.vertex.msl` | MIT | None | `0163ffae0eafd4056401409201208430135b522ed2be562aaea673b503b78146` |
| `assets/shaders/engine_sim.fragment.msl` | `third_party/open-engine-sim/assets/shaders/engine_sim.fragment.msl` | MIT | None | `e874caa51e8bf19ec95d3532501e1858e13ad2f968af6cd7b16a9a0f23228424` |
| `assets/shaders/engine_sim.vertex.spv` | `third_party/open-engine-sim/assets/shaders/engine_sim.vertex.spv.zlib.b64` | MIT | Recompiled donor HLSL with `glslangValidator -D -V -S vert -e VSMain --hlsl-iomap`; donor binary had one matrix while source and renderer use three; zlib/Base64 packaging | Donor SPV `09b1c962916c34b8d22b06c7df24b58d86738b84c4ab97f1dc9ab8f00f8a0d09`; local SPV `9d61d719d3366b118158fb14c2325ca0ef4b1c38e57f7306b0f1c590e7d09c8b`; packaged `43f5ad9f34de29f22bf7c623f0f32c6fbe14b718f3b7b4c510501596775b1849` |
| `assets/shaders/engine_sim.fragment.spv` | `third_party/open-engine-sim/assets/shaders/engine_sim.fragment.spv.zlib.b64` | MIT | Lossless packaging | Original `4215c56147a961db40eaf6919bbe0179832710760f4f296c4ba509ebcfc05416`; packaged `1b3a72bb2ab86be8c250e64d8699006a3c6bf12e687e93918d381e6b48386179` |
| `assets/shaders/engine_sim.vertex.dxil` | `third_party/open-engine-sim/assets/shaders/engine_sim.vertex.dxil.zlib.b64` | MIT | Lossless packaging | Original `ce436be92359fbd138f83e6bcac54cabdcbf3cb7c160137966faa585f46bb856`; packaged `e7e3a028885fb0084c4c8264d819b8c7f13c2d43e738be0c8b9a243a40e49c56` |
| `assets/shaders/engine_sim.fragment.dxil` | `third_party/open-engine-sim/assets/shaders/engine_sim.fragment.dxil.zlib.b64` | MIT | Lossless packaging | Original `98d403c25debde264e1d813eaed13c52b077a445cced82ba29cb0f770b5fe0bc`; packaged `3d860ba212677ce72564c8f3b80fc9ac099f28f73685bccc2d42c45cada9acde` |
| `include/geometry_generator.h` | `third_party/open-engine-sim/include/geometry_generator.h` | MIT | None | `d67a1b18780184d1ce4647579add8e1df10002db50519aff05034c060443f14b` |
| `src/geometry_generator.cpp` | `third_party/open-engine-sim/src/geometry_generator.cpp` | MIT | None | `dc3cb427f25746bce23a317d3b6f7f92a8d12bf78cda53a851172524e2a360f0` |
| `include/authored_mesh_library.h` | `third_party/open-engine-sim/include/authored_mesh_library.h` | MIT | Added `std::istream` overload | Donor `d1e5fe18ebcd39020d021f8aba23e5c36f1c4e4e63953e662547af1f7bb54e7a`; local `3181d0eabb68902e6bcc33ec52ce852a6cb1ecf3cd12722648fecfaaf83d53b7` |
| `src/authored_mesh_library.cpp` | `third_party/open-engine-sim/src/authored_mesh_library.cpp` | MIT | Existing path loader delegates to stream loader | Donor `f5faa26edcb2eb9c41f25f3b11b636bcf6bd9ce9e8bdf2c9c027395591ff51cd`; local `9a6e4a25a91c0267d8ceaca94abaf833a118e3fd993bf225cb0d41a7b577af96` |
| `assets/authored_meshes.obj` | `third_party/open-engine-sim/assets/authored_meshes.obj.zlib.b64` | MIT | Lossless zlib/Base64 packaging | Original OBJ `11d20cad19829f0635d3f8cb3b6d22c4d7cb34f36efedafe9fd9d1950773dbe9`; packaged text `d6c3c267beccc0afa50f8babec630df1eda998a55f510bd40ce261da19513971` |
| `assets/fonts/slkscr.ttf` | `third_party/open-engine-sim/assets/fonts/slkscr.ttf.zlib.b64` | Kottke Silkscreen license (included) | Lossless zlib/Base64 packaging; FreeType rasterization in the Lab | Original TTF `201df110e8dd8f19da40e5ad953b25bcac34dcb1bd14c7b8e02c9ce0b5ac0ca3`; packaged text `8d76d812ce3c04f4c2863119076e7332425f2ab1b51a782def922da9dd320971` |
| `assets/fonts/Kottke Silkscreen License.txt` | Same path under `third_party/open-engine-sim/` | Kottke Silkscreen license | Text preserved; final newline normalized | Donor `80a34fc68913c469af72872ee0e4e0b3ef101597740677fdcdcdfcb3606f9bea`; local `56a4c34eea1ee84b245ac5be7d1f9e6fac2929e17413c9c0f7469d7ee283656a` |
| `include/function.h` | `third_party/open-engine-sim/include/function.h` | MIT | None | `810cd11349d1ad43f67af1fff0bdd097420930c96b1c86644aa0849fa567d817` |
| `src/function.cpp` | `third_party/open-engine-sim/src/function.cpp` | MIT | None | `14bfc824be9505ba84f8c49492429a3aaff97694edfd1a9482add00f5c576490` |
| `include/gaussian_filter.h` | `third_party/open-engine-sim/include/gaussian_filter.h` | MIT | Removed unused solver includes | Donor `b3d0698a358c2949b25d8f7f6a22d97ab632a622aaabcd1bdaf3b0f44ac97cdd`; local `c3c98fd0d07b72ed98d21dbeedab89324d1a8a32eea9fe7319df6bb06dcc3dd2` |
| `src/gaussian_filter.cpp` | `third_party/open-engine-sim/src/gaussian_filter.cpp` | MIT | None | `c66a3e7a3f017dfb2ca5f15977a0e80a9bc213eaeed9a289182a31f2b184d437` |
| `include/ui_math.h` | `third_party/open-engine-sim/include/ui_math.h` | MIT | None | `c31bb925952d35d28117ae508c286b62bb8b3076f6102ad632b1f13342d72847` |
| `src/ui_math.cpp` | `third_party/open-engine-sim/src/ui_math.cpp` | MIT | None | `c672704bf936f23fddb7c13bc86734ed4765a45cf46d52ff55bb2932f05df0c5` |
| `include/filter.h` | `third_party/open-engine-sim/include/filter.h` | MIT | None | `e0a60775cdb57a5948e71298a33aca26bbd81973b4b28da7afabcc23c3f11c2f` |
| `include/constants.h` | `third_party/open-engine-sim/include/constants.h` | MIT | None | `8117063bfe8d22bcf89bc43a25d07aad639ec13495cfbb49240169007514a6d8` |
| `include/low_pass_filter.h` | `third_party/open-engine-sim/include/low_pass_filter.h` | MIT | None | `35fe7b9556e47e1cf71244d26bf340b034acb16ee75a515750821393c37ecd2b` |
| `include/convolution_filter.h` | `third_party/open-engine-sim/include/convolution_filter.h` | MIT | None | `e5660e1ec8bdd785bbef43cca72cd55c9002b4ac917edcf343f65a46f4796fce` |
| `include/derivative_filter.h` | `third_party/open-engine-sim/include/derivative_filter.h` | MIT | None | `a153a30359507360ac96f4f66565c5baad140a570241cdb9287159e86ea759f9` |
| `include/leveling_filter.h` | `third_party/open-engine-sim/include/leveling_filter.h` | MIT | Removed unused include | `12efb8d3d78d99435835f0c8725c9170cdb7117fd30449535ccd2194b85eefd5` |
| `include/jitter_filter.h` | `third_party/open-engine-sim/include/jitter_filter.h` | MIT | None | `1ee35dac18ad3998032f765529139ad2607ab066bf9fd9d514f4393510c2d429` |
| `include/utilities.h` | `third_party/open-engine-sim/include/utilities.h` | MIT | None | `d0620173dd694393927837947d5456b6be45a790680be5ccad189e1145c7bed1` |
| `include/butterworth_low_pass_filter.h` | `third_party/open-engine-sim/include/butterworth_low_pass_filter.h` | MIT | None | `7897b861fa93831757e1e7addffa4c6d20eac195b50225f3c838903101326269` |
| `include/spsc_audio_ring.h` | `third_party/open-engine-sim/include/spsc_audio_ring.h` | MIT | None | `c7d059c85bd0095a0a6ebdf59288f93ed3e9af355fcc5f8db8bd56a96697919d` |
| `include/ring_buffer.h` | `third_party/open-engine-sim/include/ring_buffer.h` | MIT | Replaced unused include | `b80249327ec5968af4fe365867bec7b537222eb0c279ab2df5a0bdce91dcbdb1` |
| `include/synthesizer.h` | `third_party/open-engine-sim/include/synthesizer.h` | MIT | None | `bf88f52fd05109a6380c6a6ac1c2c72cf4ddf1066b79e3a04d2c07f7b8bec644` |
| `src/filter.cpp` | `third_party/open-engine-sim/src/filter.cpp` | MIT | None | `3254a23a6dc3434e12070f59fbd9001c10225416e59134ed007289e482b453b1` |
| `src/low_pass_filter.cpp` | `third_party/open-engine-sim/src/low_pass_filter.cpp` | MIT | None | `5aca5778e9e15db5e1c76a4098b91cf4eb6146416d46b36ed54ebb137d101324` |
| `src/convolution_filter.cpp` | `third_party/open-engine-sim/src/convolution_filter.cpp` | MIT | None | `0b4263c336133800267f1d43f462d88ca6a44510390b0db13dd365307d2a3b13` |
| `src/derivative_filter.cpp` | `third_party/open-engine-sim/src/derivative_filter.cpp` | MIT | None | `e3a28fdb9b21ec1affac6121245afb8b66bb62db16a75fa0a82aa8db77b46fda` |
| `src/leveling_filter.cpp` | `third_party/open-engine-sim/src/leveling_filter.cpp` | MIT | None | `15ed4a87dc2ab4be3e748ae459d0b83e4dc05335161f08e03a177e4f41f47eb9` |
| `src/jitter_filter.cpp` | `third_party/open-engine-sim/src/jitter_filter.cpp` | MIT | Fixed array destruction; added `<cstring>` | `d6928569af9758a78ebb9bb1d9879a29d439782310bb2caebd334d0f4a3b68dc` |
| `src/synthesizer.cpp` | `third_party/open-engine-sim/src/synthesizer.cpp` | MIT | Free transfer buffers | `9daf3b88e2ea0032d7af704c520f0dc9baf243c6a0abc7bb27f56ddaad1766b6` |
| `include/gauge.h` | `third_party/open-engine-sim/include/gauge.h` | MIT | Retained donor configuration and `std::vector<Band>`; removed application-bound rendering, added bounded band access and reusable sweep/tick queries | Donor `97c1289d779da8da6662e287fc59d238336592894c7efa7594e9667afd57e981`; local `d0bf330b5ec7256b4d2150495b644cda00f639a08ca896f3db077ef6e15278c1` |
| `src/gauge.cpp` | `third_party/open-engine-sim/src/gauge.cpp` | MIT | Retained constructor and spring update; extracted donor gamma/sweep and major/minor tick decisions for the SDL dial; guarded zero range and bounded frame delta | Donor `b8df51e45a9da4b8d71784c1b0d53a6bfcdc2ae97107c93964bc4850c526b9dc`; local `88d8ee818d99d36c6634d646606db99a80aafc5bbc7ad36dd858459b9855d87f` |
| `src/gauge.cpp` (radial ticks and needle) | `src/lab/LabInstruments.cpp` | MIT | All profile dials now use the adapted donor sweep, tick visibility/length and constant-width needle; the tachometer keeps its persistent `Gauge` and the other dials build geometry from their SEVEL scales. The clutch keeps the donor's 0.8π–0.2π arc and displays `N/D` | Donor `b8df51e45a9da4b8d71784c1b0d53a6bfcdc2ae97107c93964bc4850c526b9dc` |
| `src/labeled_gauge.cpp` (`LabeledGauge::render` bands and radii) | `third_party/open-engine-sim/include/labeled_gauge_layout.h`, `src/lab/LabInstruments.cpp` | MIT | Extracted title, gauge and value bands, center offset, radius and needle proportions into backend-neutral layout; SEVEL labels and values use those bands in the SDL adapter | Donor `efbfd64c015a9cf7424e180d9437428cc44dd37ea334359388ec3c9837661340` |
| `include/oscilloscope.h` | `third_party/open-engine-sim/include/oscilloscope.h` | MIT | Removed application-bound render methods; replaced raw point arrays with a bounded `std::vector` ring and ordered-point accessor | Donor `c7823144db2db9a307041af83359b698814346e097ccadbb4590d875a35a6d43`; local `ecd3da6e3966d0c993f146e1a6a5a1ac81ceb3d5d89f9f3de565f6518b02f5ee` |
| `src/oscilloscope.cpp` | `third_party/open-engine-sim/src/oscilloscope.cpp` | MIT | Retained sample-window and dynamic range logic; replaced raw arrays with `std::vector`, removed GPU rendering and added ordered-point output for the Lab | Donor `10d6d0a80903631f5c84a208e7af057607c61283ac0a3904c796895af744c334`; local `ff0897176b67bd32bac23a71fc7c6ac417b7da2cf15ec622ff6aa75432a52685` |
| `src/oscilloscope.cpp` (path algorithm) | `src/lab/LabInstruments.cpp` | MIT | Adapted `startPath`/`generatePathSegment` through the unmodified donor `GeometryGenerator`; event traces remain tick-based and use `std::vector` storage | Donor `10d6d0a80903631f5c84a208e7af057607c61283ac0a3904c796895af744c334` |
| `src/ui_button.cpp` (frame/hover/held design) | `apps/sevel-ma17-lab/SdlDisplay.cpp`, `include/lab/LabButtons.hpp` | MIT | Adapted button drawing and hit testing to SDL3 software renderer and the Lab's command queue; no donor UI runtime copied | Donor `81192da119c73446ab5ae340a7731f87ef10db604ba2c93110fb3dff4babc48d` |
| `src/firing_order_display.cpp` (circular cylinder indicator) | `apps/sevel-ma17-lab/SdlDisplay.cpp` | MIT | Adapted the donor's ring-and-light presentation to a fixed SEVEL 1–3–4–2 strip; brightness comes from actual recent combustion/misfire events, without importing donor engine state | Donor `34d6326043d9da2a316da3f387a9947b60cb126cc2e4ea8962dc0c9a24124f85` |
| `src/load_simulation_cluster.cpp` (`drawCurrentGear`, `drawGearChevron`, `onMouseClick`, clutch gauge profile) | `apps/sevel-ma17-lab/SdlDisplay.cpp`, `src/lab/LabInstruments.cpp` | MIT | Adapted donor gear card and clutch gauge layout to SDL3. The full card now follows donor title/body font sizes (24/64 px, fitted to the available bands), 0.28 chevron width and 3 px strokes; compact layouts retain the horizontal N–5 card. The adjacent clutch scale shows `N/D` without a needle. The gear tooltip displays Fiat manual ratios and an ideal speed reference with an explicitly estimated 0.29 m tire radius; neither donor transmission solver nor clutch state is imported | Donor `fff1235c0f6d5804114e24b5f3ec8477e2d68e6edeffe36404b156397532fe6e` |
| `src/load_simulation_cluster.cpp` (`drawCurrentGear` bands and `drawGearChevron` size) | `third_party/open-engine-sim/include/gear_card_layout.h`, `apps/sevel-ma17-lab/SdlDisplay.cpp` | MIT | Extracted the donor's 0.86/0.62/0.22 vertical divisions, 0.28 chevron size and clickable up/down regions; SDL flips the donor Y axis and keeps a horizontal control for compact windows | Donor `fff1235c0f6d5804114e24b5f3ec8477e2d68e6edeffe36404b156397532fe6e` |
| `src/right_gauge_cluster.cpp` (cell hierarchy and `throttleControlBounds`), `src/afr_cluster.cpp` (upper/lower split) | `third_party/open-engine-sim/include/right_gauge_layout.h`, `src/lab/LabInstruments.cpp` | MIT | Extracted the donor's half-panel cells, three stacked intake gauges, equal AFR/fuel widths, upper/lower sensor cells and proportional throttle-control rectangle; SDL flips Y and supplies SEVEL values | Donor right cluster `1255cd5bc817534c3eb3eca20841ac43d3bc2a844c296ba57932bf01310aefc4`; AFR cluster `f5571f93b14592cd2f08ef4542923c17f366cf4a6021a4cd351cf7523cf02139` |
| `assets/es/sound-library/smooth/smooth_39.wav` | `third_party/open-engine-sim/assets/smooth_39.wav.zlib.b64` | MIT (donor root) | Complete WAV, losslessly packaged with zlib/Base64 | Original WAV `75de9db47063395665d36b6d4232f477aae385feaa9ba158353fbdaf122db5cc`; packaged text `f64df2895813394ec2a5b4d248474f38f74da2fbe031495f5d8bcbfc63f47496` |
| `assets/es/sound-library/smooth/smooth_39.wav` (first 2048 PCM frames) | `include/lab/SevelImpulse.hpp` | MIT (donor root) | Exact PCM samples in `std::array`; runtime convolution gain is configured separately | Local text `c925313058584b5656eef3f5cd7fbfc26566675f5ea953a63f56eb831dc70159` |

The renderer and math headers provide a backend-neutral drawing contract. The
donor `Shaders` state now supplies object transforms and colors for mechanical
draw submissions. The original SDL GPU backend and compiled shaders are built
for an opt-in second-window scene preview. Xvfb cannot present that desktop
preview without DRI3; an SDL offscreen window with lavapipe produced and
validated the GPU scene PNG. Physical-monitor presentation awaits owner testing.
The unmodified donor `GeometryGenerator::generateLine2d` builds each mechanical
stroke in the SDL3 window from the same SEVEL poses used by the headless scene.
`DonorScene` owns generator cleanup and the Lab test compares all 47 stroke
bounds across four crank phases. The
audio subset builds as `open-engine-sim-audio`; `AcousticAdapter` feeds it from
real MA1.7/SEVEL combustion events for offline WAV and SDL3 live playback.
The 2048-frame donor-derived impulse retains 99.69% of the complete WAV's
sample energy and is convolved at 35% mix. The complete source is archived
losslessly above. This is an acoustic effect, not a Fiat exhaust measurement.
The Lab instantiates three adapted donor `Gauge` objects for needle state;
the P1.1 candidate tachometer selects a 200 ms exponential display filter,
while the other objects retain the donor spring dynamics. The SDL dial now
uses the incorporated `GeometryGenerator::generateLine2d` for the needle,
as in donor `Gauge::render`, instead of constructing a separate quadrilateral.
The tick marks also use that generator and the donor major/minor width fields,
replacing the SDL one-pixel lines and offset duplicate for major marks.
One generator buffer is reused across ticks and the needle within each dial.
Colored dial bands and ignition rings now use the incorporated
`GeometryGenerator::generateRing2d`, including the donor five-pixel edge
limit, instead of the former fixed subdivision mesh. The SDL adapter reflects
the donor Y axis around the dial center; tiny rings clamp the edge limit to
keep the donor arcsine defined. Radius, band width and angular endpoints are
covered at 100/150/200% by `DonorGauge.GeneratedBandsPreserveRadiiAndAngularEndpoints`.
Validation on 2026-11-18: NativeLab process `p_20a995139474` built with
`--parallel "$(nproc)"` and passed all six `DonorGauge.*` tests. The incorporated
and donor `geometry_generator.cpp` match SHA-256
`dc3cb427f25746bce23a317d3b6f7f92a8d12bf78cda53a851172524e2a360f0`.
This proves reuse and geometric invariants.
The profile now also carries the donor band width, radial offset and angular
shortening fields. `RightGaugeCluster`'s 3 px width / 6 px outer offset and
tachometer ±1 degree endpoint adjustments are applied by the SDL adapter;
SEVEL thresholds and colors remain explicit profile values.
NativeLab process `p_260d3b57f94f` rebuilt and passed six `DonorGauge.*` plus
11 `LabCapture.UiScale*` / `LabCapture.BatteryDebug*` tests (27.75 s).
Inspection of 1280×720 and 3440×1440 at 200%, plus 900×620 debug, confirmed
the bands are separated from the tick endpoints without visible clipping.
This is the band/layout batch evidence, not completion of UI-40 or the full
interaction, physical-state, backend and sanitizer acceptance matrix.
The extra central square has been removed to match the donor. Needle width
scales with UI DPI; mathematical tests cover endpoints and perpendicular
width at three angles and 100/150/200%. Visual acceptance awaits the batched
presentation pass. The
three ECU channels instantiate the adapted donor `Oscilloscope` ring to order
event samples and render them with the donor's geometry path generator.
Oversized traces retain the SDL line fallback.
The GUI decodes the donor's authored OBJ beside the executable and renders
its piston and connecting rod meshes from the SEVEL crank poses. The donor's
`Crankshaft` mesh is an axial silhouette: the fork draws it once per rod
journal at that journal's angle and uses depth layers. The Lab's four-cylinder
longitudinal view instead draws one continuous shaft with crank throws from
the SEVEL poses; repeating the axial mesh under each cylinder was incorrect.
In this projection the crank's radial horizontal motion is depth, so the
journals and rods stay on each cylinder's screen-space axis while their
vertical coordinates follow the physical crank angle.
Two small, labeled axial panels draw the imported `Crankshaft` mesh for the
1/4 and 2/3 journal pairs at opposite physical phases. The focused axial
views additionally reuse the donor crank, rod, piston, head and valve meshes
for cylinder 1 or 2 as the representative of each crank pair. All views use
the same physical snapshot.
The radial view repeats the donor `CylinderHead` mesh at each cylinder section
and places two donor `Valve` meshes above each bore. Their lifts follow the
documented SEVEL timing. The longitudinal view keeps its donor valve meshes
and schematic single camshaft; neither view runs the donor's valvetrain.
The status panel uses the donor's unmodified Silkscreen font bytes. The Lab
decodes them beside the executable and rasterizes glyph runs with FreeType;
`FontRenderer` is new Lab code, not the donor `TextRenderer` implementation.
The control bar adapts the donor `UiButton` frame, fill and hover/held colors.
Nine SDL3 buttons call the same `SimSession` commands as keyboard controls;
the starter button is momentary and replay locks physical inputs.
The firing-order strip adapts the donor's circular combustion indicator and
lights cylinders in SEVEL 1–3–4–2 order from the emulator event stream. It
shows recent misfires in red. The donor asset inventory contains one planar OBJ
with the eight named meshes listed above; it has no separate 3D model file.
The shapes are planar; their scales are drawing estimates only. The packaged
asset decoded to 918,973 bytes with the original OBJ hash above. The SDL3 GPU
renderer and remaining donor UI classes remain pending for the primary window.
Each later import needs its transitive dependencies, license review and hash.

## GUI component boundary after the dual-view layout

The donor's `LabeledGauge` directly inherits `UiElement` and calls
`EngineSimApplication` drawing and child-element APIs. Its
`RightGaugeCluster` also owns donor `Engine` and `Simulator` pointers and
reads donor fuel, manifold and AFR state. Importing those classes as live
widgets would pull the donor solver across the presentation boundary. The
SEVEL SDL renderer instead uses the copied `Gauge` state, donor radial-tick
geometry and donor label/frame proportions, with all values and scales from
`SevelInstrumentProfile` and `EmulatorSnapshot`. `oscilloscope.cpp` and
`GeometryGenerator` are copied, built and used by the digital pin traces;
the new analog scope currently draws timestamped SDL lines with fixed units.
The unused `draw_lab_gauge` software path was removed; the visible analog
instruments use `draw_profile_dial` and one SEVEL profile. This remains an
SDL adaptation of donor gauge geometry, not the donor `Gauge::render` or
`LabeledGauge::render` transplanted unchanged; its band and radius math is
extracted into `labeled_gauge_layout.h` and used by the SDL dial renderer.
The donor `desktop_application.cpp`, `labeled_gauge.cpp`,
`right_gauge_cluster.cpp` (apart from its throttle control bounds),
`engine_view.cpp` and
`oscilloscope_cluster.cpp` remain reference files in the preserved checkout,
not falsely listed as imported production modules. Their composition and
focus behavior still require further adaptation for the requested UI.

The analog scope now uses the copied `ui_math.h::Grid` directly for preview
placement and follows the focus-above-previews arrangement of donor
`src/oscilloscope_cluster.cpp::render` (checkout
`1e226ee7bfbeb1d5012c7696aee82a57355df281`, SHA-256
`2d45315af8d654078dfe9637a5e779f20bd7f785466482eebc93569cb39cff52`).
Its SDL adapter in `LabInstruments.cpp` uses six columns and two rows for
eleven SEVEL groups at 360 px or taller, or eleven columns and one row from
248 to 359 px; below 248 px the preview cards are hidden. Plotting and mouse
selection share the resulting rectangles in both visible arrangements.
The donor `oscilloscope_cluster.cpp` source itself remains outside production
because its `EngineSimApplication` and simulator references are not read-only
SEVEL adapters.

The current channel-to-reading-point inventory and remaining validity gaps
are in [SEVEL_LAB_CHANNEL_MAP.md](SEVEL_LAB_CHANNEL_MAP.md).

### Drivetrain formula extraction (2026-11-18)

`include/engine/SevelTransmission.hpp` now owns the Fiat ratios and kinematic
reference; the Lab header is a compatibility alias to the physical namespace.
It also adapts OES `Transmission::changeGear`'s reflected inertia
`I = mass * (radius / (gear * differential))²` and
`Vehicle::linearForceToVirtualTorque`'s force conversion. The latter is
algebraically reduced to `torque = force * radius / overall_ratio` and keeps
the force sign. Neutral/invalid inputs return no connected load.

Donor revision: `1e226ee7bfbeb1d5012c7696aee82a57355df281`, MIT.
Source hashes: `src/transmission.cpp`
`d38e781c22bf9f37e50b4024f12a1d319b677a31b6db175fcc0e8dfcb43cc0e4`;
`src/vehicle.cpp`
`ef068dcc94623e901cee5e86b107cc5fa911fa1794dc23f8fa811e996ae95ba4`.
NativeLab `p_bd6ae678f0a4` built with nproc and passed five
`SevelTransmission.*` tests, including equality of linear/rotational energy
and power in all five forward gears. The 1000 kg test mass is a fixture,
not a Fiat calibration. Runtime clutch/vehicle integration remains unfinished;
the speed gauge still observes the scenario input.

The physical ratio API now uses -1 for reverse, 0 for neutral and 1..5 for
forward gears. Reverse preserves positive reflected inertia, reverses wheel
speed and transforms signed road force with the signed ratio. This differs
deliberately from the donor's unsigned square-root conversion, which cannot
represent reverse direction. The GUI selector still exposes N–5 only.
NativeLab `p_55592c8b1128` rebuilt and passed six `SevelTransmission.*` tests;
energy/power identities now include reverse, and overflow of the negative
speed result is rejected. No new runtime vehicle behavior is claimed.

`CrankDynamics::step` now has a separate signed transmission-torque argument
(default zero), plus a read-only inertia accessor for the clutch solver.
Positive transmission torque motors the crank; negative torque loads it.
The existing scenario resistance still rejects negative inputs, and crank
speed still clamps at zero. A frictionless fixture verifies 20 Nm over 0.1 s
produces 10 rad/s with 0.20 kg·m² inertia, checks work against kinetic energy,
then brakes to rest. NaN/infinite transmission torque is rejected.
NativeLab `p_db1df9ebb75d` rebuilt with nproc and passed 14 selected crank,
transmission and ROM runner tests. Existing callers use the default zero;
this is the crank-side interface, not yet a coupled clutch simulation.
OES `ClutchConstraint::calculate` supplies opposite angular Jacobian entries
(-1,+1) and bounded torque; `Transmission::update` scales those bounds by
clutch pressure. Adapting this must preserve equal/opposite shaft impulses
and allow the vehicle to drive the engine, without recasting torque from
the wheels as combustion torque.

`include/engine/ClutchCoupling.hpp` now provides the isolated scalar solve:
`impulse = clamp((omega_crank - omega_vehicle) / (1/Ic + 1/Iv),
                -Tmax * pressure * dt, Tmax * pressure * dt)`.
This is an analytic adaptation of the donor constraint, not a literal copy
of its general solver. It returns equal/opposite impulses and dissipated
energy, with finite/positive inertia and timestep checks. The caller must
apply the impulses once to free velocities after external forces; applying
them again as torque would double-count the coupling. Neutral must bypass
the solve, since no reflected vehicle inertia exists for neutral.

Constraint source: `simple-2d-constraint-solver/src/clutch_constraint.cpp`,
submodule revision `e009f4ff1c9c4c5874e865e893cdb62e208fb2b3`, SHA-256
`9952b03aadb52f43d4aa50487f83f7300e4ee7f26be468e3c27918c2a5e49b64`.
NativeLab `p_7c715f7d4fe9` built and passed 13 selected clutch/crank/gear
tests. Clutch tests cover both directions of power transfer, locked-shaft
momentum conservation, energy dissipation, pressure-limited slip and open
clutch.

`include/engine/Drivetrain.hpp` now holds signed road velocity, selected gear,
clutch pressure, transmitted torque and accumulated clutch heat. Mass,
radius and torque capacity are explicit constructor arguments. Gear changes
preserve road velocity and derive reflected inertia/speed from the new ratio.
`CrankDynamics::step` accepts an optional drivetrain and applies its coupling
after free crank acceleration, before integrating angle/tooth position.
Equal/opposite impulses are limited together if the vehicle would reverse
the crank, which the current crank model cannot represent.

NativeLab `p_5058050e3d3d` rebuilt and passed 18 drivetrain/clutch/crank/gear
and ROM runner tests. The coupled fixture verifies final kinetic energy
plus clutch heat equals the initial 1000 J within 1e-6 J, neutral/open-clutch
coasting, a shift with unchanged road speed, reverse launch and back-driving
a stopped crank. These fixtures have no drag or rolling resistance. The
1000 kg / 200 Nm parameters are test inputs, not production calibration.
The ECU loop and GUI do not yet instantiate this drivetrain; command routing,
road forces, static breakaway under wheel torque and telemetry remain open.

Road resistance is now configurable in `Drivetrain` using the OES
`VehicleDragConstraint::calculate` formula `F = Frolling + 0.5*rho*v²*Cd*A`.
Parameters are explicit (rolling force in N, density in kg/m³, frontal area
in m²); defaults remain zero until a vehicle configuration supplies them.
Source SHA-256: `bdbc665ec021a3b4e9c71e434d6dfffc45ae51effc2b8af75c3baec88a785c2d`.
The road mass receives the opposing impulse before clutch coupling, also in
neutral/open clutch. The impulse is capped at rest to avoid numerical reversal.
This models motion resistance; a coupled static hold/breakaway constraint
is still pending, as are slope, brakes and the ECU/GUI integration.
NativeLab `p_629b0b82709a` rebuilt and passed 19 selected physics/ROM tests.
The road test checks 244 N at ±20 m/s for explicit fixture parameters,
19.9756 m/s magnitude after 0.1 s at 1000 kg, and no reversal or motion
from rest under resistance alone even for a long timestep.

The optional drivetrain is now routed through `EmulatorLoopContext` and
`tick_physical_crank_input` in both key-on and key-off paths. When attached,
road speed follows its signed physical velocity; the scenario speed target
is bypassed. Thermal airflow uses speed magnitude in either direction.
Snapshots publish `drivetrain_available`, `transmission_gear`,
`clutch_pressure`, `clutch_crank_torque_nm` and `clutch_heat_j` alongside
physical road speed. The controller owns the drivetrain for the entire run.

NativeLab `p_33cb7904b25c` rebuilt and passed 20 selected tests, including new
`LabRunner.DrivetrainTelemetry` with the original ROM. Its explicit fixture
connects first gear, engages 10% clutch after the starter interval and checks
positive speed/heat and exact speed agreement with the physical object even
while a 100 km/h scenario target is requested. CLI/session configuration,
GUI controls/source labels and persistence of the new fields remain pending;
ordinary runs still have no drivetrain unless a controller attaches one.

CLI activation is now available with `--physical-crank --drivetrain`.
Options: `--gear -1..5` (default N), `--clutch-percent 0..100` (default open),
`--vehicle-mass-kg 500..3000` (estimate 1000) and `--clutch-max-nm 1..1000`
(estimate 200). `--vehicle-kmh` initializes road speed in this mode.
The runner owns the drivetrain and prints the provisional calibration:
0.29 m tire radius, 100 N rolling resistance, 1.184 kg/m³ air density,
Cd 0.32 and 2 m² frontal area. These values are estimates, not manual data.
Without the flag the previous scenario-speed path remains active.

NativeLab `p_4f0c4a8046d0` built and passed 21 selected tests, including
`LabRunner.DrivetrainCli` with the ROM and first gear/10% clutch. NativeLab
`p_05fe8d50fb5d` separately rejected seven invalid option combinations with
exit 2 (missing prerequisite/value, out-of-range gear/pressure/capacity and
non-numeric mass). GUI controls and session persistence remain pending.

`SimSession` now queues `Gear` and `ClutchPressure` commands for execution
on the ECU thread. The trace names `gear` and `clutch_pressure` round-trip
through control recording/replay; values require integral gears -1..5 and
finite pressure 0..1. The new enum values are appended to preserve existing
numeric values. They affect the physical object only when drivetrain mode
is configured; GUI bindings and availability feedback remain pending.
NativeLab `p_1ae512417416` rebuilt and passed six selected runner/replay tests.
The expanded `LabSession.ControlReplay` test saves/reloads a first-to-second
gear sequence with an open-clutch interval and verifies exact final physical
speed, RPM, clutch torque and heat, plus command types, values and ticks.
This covers command persistence; snapshot CSV persistence remains separate.

Analog scope CSV export now appends drivetrain availability, signed physical
road speed, gear, clutch pressure, signed crank torque and clutch heat when
the selected history contains a drivetrain sample. Units are in column names;
missing/invalid values are empty, and scenario speed is not substituted.
`include/lab/DrivetrainExport.hpp` supplies the writer used by `save_scope_csv`.
NativeLab `p_313975448e63` rebuilt and passed both `DrivetrainExport.*` tests
and `LabSession.ControlReplay`. This checks serialization and command replay;
the GUI export interaction remains for the grouped interaction pass.
There is no full-snapshot CSV importer in the current app: this export is
for analysis, while reproducible re-execution uses command traces plus the
scenario/ROM. Archive extrema and gear-transition retention for these new
channels still need coverage before claiming long-history preservation.

### Physical gear selection in the donor card

The existing OES-derived gear card now sends scheduled `Gear` commands through
SimSession when drivetrain telemetry is available. Q/E and mouse arrows cover
R/N/1–5; rendering and the window title use the applied snapshot gear, including
replay. Reference-only sessions retain N–5 and the REF label. The TBI detail
shows applied clutch pressure; the gear tooltip distinguishes physical road
speed from its ideal no-slip calculation. Scenario speed keys are disabled
for an active drivetrain. The separate clutch dial/control remains pending.

NativeLab `p_e2f4d3d9c953`: parallel build and nine gear-widget, drivetrain-runner
and replay tests passed. New `LabControls.GearPhysical1920x1080` exercises
keyboard reverse and keyboard/mouse upshifts against applied telemetry.
Its first run sent input before the initial physical snapshot; the fixture now
waits for a positive simulation tick and keeps acquisition live through the
interaction. NativeLab `p_0543de2f90c3` passed (10.55 s), using isolated Xvfb
software rendering. This is an interaction check, not final visual acceptance.

The clutch dial is now bound to applied drivetrain pressure, with finite/range
and stale checks. Its existing donor scale (0–100, ticks 10/50, angles 0.8π/0.2π)
is retained. Page Up/Down adjusts pressure by 10 percentage points when physical
transmission is active; scenario sessions retain road-speed input on those keys.
Replay blocks these commands. Help, source tooltip and missing-state labels were
updated; physical speed now identifies its source in the speed tooltip.
NativeLab `p_af1b428b2695` rebuilt with nproc and passed 11 tests, including
drivetrain conservation, signed motion, telemetry, export, command replay and
GUI applied-pressure checks at 0%, 100%, and back to 10%. The interaction fixture
uses Xvfb; the heavy visual acceptance matrix remains pending. The dial is still
limited to wide layouts; compact layouts show applied pressure in TBI details.

### Drivetrain history retention

The 100 ms archive buckets now retain min/max road speed, clutch pressure,
signed clutch crank torque and dissipated heat, alongside the existing fields.
Both samples adjacent to gear and drivetrain-availability transitions are kept;
finite/missing transitions use the existing field-validity mechanism.
`LabSession.ControlReplay` compares an unabridged 1.2-million-tick run against
a 10-million-tick run after raw-history eviction, checking each complete bucket's
four extrema and both sides of gear changes at identical ticks and values.
NativeLab `p_4c51f0ef84d9` rebuilt and passed this test (12.65 s);
`p_65e8533d9cf5` passed `LabSession.WarmScenarioDeterminism` (9.50 s), covering
the earlier history/ADC/cadence behavior. Synthetic drivetrain NaN/availability
fault injection and the full GUI CSV export path remain separate coverage gaps.

The physical-gear GUI test now presses C after verifying applied clutch pressure
and parses the actual exported CSV. NativeLab `p_c34d6451b802` passed (10.58 s):
3,873 rows in `build-lab/.work/gui-review/sevel-scope-g0-1936500-1.csv`.
Checks cover canonical drivetrain column units, finite values, missing-state
blanks, sorted unique ticks, count/range metadata, positive dissipated heat,
and final gear 3 / pressure 0.1 matching applied GUI telemetry. Selection bounds
are checked separately from first/last retained sample timestamps: a window
can begin before the first acquisition. The initial test incorrectly required
those bounds to coincide and was corrected against the export contract.
The generated `build-lab/sevel-gear-physical-1920x1080.png` was inspected:
clutch 10% and gear 3 are visible in the donor cards and TBI detail; mechanical
views remain contained. Scope lower-axis labels overlap near the left edge;
this remains a layout correction for the grouped visual pass, not accepted.

The observed scope-footer overlap is corrected: DATA starts after the measured
width of the negative-time label plus a gap, and the zero label is right-aligned
using its measured width. Available data bounds use a shorter label if needed;
trigger status is ellipsized within its own left gutter. Text scale is retained.
NativeLab `p_e5f3f5edbaaa` rebuilt and passed the physical-gear/CSV interaction
test (10.58 s). Its updated 1920×1080 capture was inspected and shows separated
`-5.0 s`, `DATA 5.10..10.10 s`, and `0 s` labels. This verifies the reported cell;
compact/DPI/long-duration footer cases remain part of the grouped visual pass.

### Wide-layout clutch and gear proportions

The wide desktop cards now use the donor reference cell aspect:
`(2048 / 9) / (816 / 6) = 1.6732026`. This derives from the desktop thirds
grid and LoadSimulationCluster's 3×2 grid, whose adjacent clutch/gear cells
are equal. SEVEL fits two equal cells to its left panel with uniform scaling
and caps their height by available space. Gear rendering and mouse hitboxes
still consume the same `gear_widget_rect`; the clutch takes the adjacent cell.
Compact horizontal cards and short-desktop fallback retain their adaptations.

NativeLab `p_a1b9ddcb0db9`: build, GearWidget1920 and both 100% captures
(1920×1080/3440×1440) passed. The 1920 capture was inspected: equal landscape
cards replace the previous tall columns. GearPhysical reached its export check
but did not find the CSV log record; diagnostic output was expanded to retain
export lines. Follow-up `p_692d05dcf398` passed all physical gear, clutch and
CSV assertions (10.55 s). The first export failure is not explained by this
successful rerun and remains an intermittent-test investigation item.

Export diagnostics now record `[LAB-SCOPE-REQUEST]` when SDL accepts C, and
GearPhysical preserves its complete output beside the PNG before assertions.
NativeLab `p_f31523bcfd49` rebuilt and ran three consecutive instrumented
GearPhysical executions, all passed (31.87 s total). Last trace acknowledged
the request at tick 1,952,500 and saved data through 2,010,000, before the
10,000,000-tick stop. This excludes an end-of-session race in that observed
run, but does not establish the cause of the earlier failure. The test now
also distinguishes missing acknowledgement from missing completion and checks
request ≤ export-end < stop. No automatic retry was added to the test.

### Sanitizer batch — 2026-11-18

NativeLab `p_1e2b6fccf47d`: separate `.work/asan-gui-build`, build and
37/37 selected physics, drivetrain export, tachometer and donor geometry
tests passed (6.56 s). `p_25c50b877c7d`: scope decimation, control replay
and warm-scenario determinism passed 4/4 (63.14 s).
Compile and link flags confirm AddressSanitizer, LeakSanitizer and UBSan
with additional bounds, arithmetic, pointer and vptr checks; no TSan.
No sanitizer diagnostic occurred in these selected tests.
The geometry test range loop now binds dimension pairs by const reference
to satisfy GCC's warning-as-error build. Long simulation deadlines increased
to 120 seconds for instrumented execution; replay's short runs allow 30.
Observed long tests took 50.09 and 63.13 seconds, versus approximately
9.50 and 12.65 seconds without instrumentation. No retry was introduced.
This batch does not validate the graphical driver or close the visual audit.

### Offscreen backends — 2026-11-18

NativeLab validated the current donor preview without Xvfb using explicitly
selected lavapipe and RADV ICDs (p_8ecfdad940c9 / p_28d2c52ab70d, exit 0).
Vulkan enumeration confirms CPU llvmpipe and discrete Radeon RX 7900 XTX.
At tick 1500000 the main UI PNGs are identical; preview pixels differ only
by at most 1/255 per channel in 0.513% of pixels, with matching geometry.
Both previews and the main UI were visually inspected. The complete UI
still uses SDL's OpenGL renderer; this is not a complete Vulkan UI port.
Artifacts, reproduction command and hashes are retained in
`.work/gui-review/offscreen-20261118/REPORT.md` and the sibling
`offscreen-radv-20261118` directory. The test accepts an optional artifact
directory to preserve its output for visual review.

### UiButton presentation transplant — 2026-11-18

`third_party/open-engine-sim/include/ui_button_style.h` extracts the complete
color-selection and interpolation rule of donor `UiButton::render`, including
selected inversion, held-over-hover precedence, 0.08/0.04 blending and shared
frame/text foreground. `draw_lab_buttons` now consumes this presentation
adapter rather than the former hardcoded blue selected/hover/held colors.
The application supplies its foreground/background palette and SDL conversion;
disabled colors remain a SEVEL extension for replay and unavailable commands.
Hitboxes, starter HOLD annotation, load bar and command dispatch are unchanged.
This transplants the presentation rule, not the donor UiElement event runtime.

Donor revision: `1e226ee7bfbeb1d5012c7696aee82a57355df281`, MIT.
SHA-256 source `src/ui_button.cpp`:
`81192da119c73446ab5ae340a7731f87ef10db604ba2c93110fb3dff4babc48d`;
source `src/ui_utilities.cpp`:
`8a3f3ceb431d9e3debcee20a287d05f80dd5db03447537ca7533d311b9af5d6f`;
adapter: `e63c1aa01450519087c3d126f1e17e8251343b42807258c24392346ab67aeec3`.
NativeLab p_253a5481fbd1 built with nproc and passed all three selected
tests: unique control hit targets, MouseButtonBar and ReplayLocksMouse
(41.23 seconds). Visual acceptance is deferred to the next grouped GUI pass;
earlier screenshots precede this button appearance change.

### Full-cycle mesh envelope regression — 2026-11-18

`DonorScene.FullCycleMeshesStayInsideDefaultViewports` now inspects submitted
mesh vertices before clipping at 145 crank phases (0–720°, 5° steps), four
pane sizes (180×240, 269×576, 403×864, 720×350), and six projections:
longitudinal, four radial sections together, and each focused cylinder.
All four spark and combustion markers are active to cover peak geometry.
At default zoom 0.78 and zero pan, every sampled vertex is finite and the
scene retains at least 5% margin at each viewport edge (3480 combinations).
This is sampled envelope evidence, not an analytic proof between samples
or verification of arbitrary user zoom/pan and font-dependent UI regions.

The first run (NativeLab p_246cd96f75c4) exposed a real capacity exception:
the radial procedural buffer allowed 32 lines, but 17 housing/rod/shaft
lines plus 16 marker lines require 33. Capacity now derives from that
maximum: 132 vertices and 198 indices, plus the imported mesh capacities.
The donor generator itself is unchanged. After the fix, NativeLab
p_cce3dc8d8455 built and passed all 11 DonorScene tests (55.42 seconds).
No visual matrix was rerun for this allocation-only fix.

### Road resistance at launch — 2026-11-18

The scalar drivetrain previously discarded unused road-resistance impulse
when its first integration stage reached zero road speed. Clutch coupling
then produced a small nonzero speed even when tire force was below rolling
resistance. The new regression failed before the fix (NativeLab
p_f375f98ca518). The remaining force budget is now applied after coupling,
capped at rest in either direction, without applying resistance twice.

The regression exercises first and reverse gears: 1 Nm clutch torque gives
about 53 N tire force and remains stationary against 100 N rolling resistance
for 100 steps; 4 Nm exceeds resistance and launches with the analytically
expected signed net-force velocity increment. The crank remains loaded even
while the vehicle is stationary. NativeLab p_80db798fb640 built the complete
Lab and passed 14 physics, ROM telemetry/CLI and control-replay tests (12.67 s).
Existing no-road-loss energy/heat and reverse/backdrive checks still pass.

OES `vehicle_drag_constraint.cpp` supplies the rolling-plus-aerodynamic force
reference (SHA-256 bdbc665ec021a3b4e9c71e434d6dfffc45ae51effc2b8af75c3baec88a785c2d).
The residual impulse handling is a SEVEL scalar integration adaptation,
not a literal copy of OES's simultaneous constraint solver. It retains
timestep-dependent splitting error; tire slip, slope and braking remain
outside this initial approximate vehicle model. Road dissipation is separate
from the reported clutch heat. Historical GUI fixtures without --drivetrain
retain their original physical baseline.

### Single trigger chooses the first eligible crossing — 2026-11-18

`AnalogTrigger.hpp` now exposes First/Latest occurrence selection for analog
and recorded-event triggers. Single uses First; Auto/Normal retain Latest,
including through the existing latest_* wrappers. Previously Single could
choose a later crossing when several arrived between rendered frames.
The regression varies frame batch endpoints, checks analog and ignition
edges, rejects a NaN-adjacent crossing and checks falling-edge selection.

NativeLab `p_58626d599b4c` completed the parallel Lab build and passed all
six selected tests in 28.88 s: three AnalogTrigger tests and captures
TriggerSpark14x1920x1080, TriggerSingleTps1920x1080 and
TriggerWaitTps1920x1080. The three corresponding
`build-lab/sevel-trigger-{spark14,single-tps,wait-tps}-1920x1080.png`
images were inspected after the process-cleanup interruption. Single captures
show the TRIG line within both plot lanes and frozen history; the waiting
capture has no false TRIG marker. START/HOLD remains inside its button.

This guarantees the first eligible crossing in supplied retained history,
not an event already discarded before rendering. Eligibility still requires
the configured pre/post window and arm tick. Retention exhaustion and the
complete Auto/Normal/pre-trigger boundary audit remain open under UI-33.
These captures are a focused interaction batch, not acceptance of the full
resolution/DPI matrix or proof of the P1.1 tachometer hypothesis.

### Trigger window timing assertions — 2026-11-18

The Single capture log now includes span, pre-trigger ticks, earliest
retained sample and latest available tick. The GUI regression verifies
exactly one latch, a 990000-tick (1 s) window, `end - crossing = span - pre`,
and that the entire displayed interval fits available history. TPS exercises
25% pre-trigger; the spark fixture presses B once before arming to exercise
50%. These assertions use the actual renderer latch and acquisition bounds,
in addition to the prior marker-pixel and arm-order checks.

NativeLab `p_4c78c2128746`: full parallel build succeeded; both focused GUI
tests passed in 23.67 s (11.84 s spark, 11.81 s TPS). No broad visual matrix
was rerun. The new spark PNG supersedes the previous 25% fixture artifact;
this run verifies timing and automated marker checks, not a new visual
acceptance. Auto/Normal and history-exhaustion behavior remain pending.

### Normal trigger waiting display — 2026-11-18

Audit found Normal WAIT still displayed an untriggered live trace. Normal
now retains its last triggered history/snapshot/window while waiting, or
shows empty lanes and unavailable readouts before its first capture.
Rearming clears that retained capture, including when controls change at
the same paused simulation tick. Auto remains free-running without a match.
WAIT/HOLD precedes trigger parameters so footer truncation preserves state.

NativeLab `p_0f00cce69d0b` built successfully; waiting and spark tests passed,
but the TPS test could not parse the full new latch record despite matching
its initial fields. The original failure output omitted that record, so its
cause is unproven. Trigger tests now retain full `.log` artifacts and include
matching records in assertion diagnostics; no retry was added.
After explicit rearm invalidation, `p_0fd7535323ab` built and passed all three
trigger GUI tests in 25.47 s. TPS recorded tick 1452500, end 2195000,
span 990000, pre 247500, history_first 228500, available_end 2208500.
This pass does not establish that the earlier parsing failure is resolved.

The waiting PNG was inspected: empty lanes, unavailable readouts, no TRIG
marker, and visible `T:N WAIT` precede abbreviated settings. The regression
also checks zero shown samples before the first Normal trigger. Holding a
previous Normal capture after history eviction, Auto fallback, and the
intermittent latch-log parse remain explicit follow-up validation items.

### Normal retention, Auto fallback and log interleaving — 2026-11-18

Added GUI fixtures `TriggernormalTps1920x1080` and
`TriggerautoTps1920x1080`, with unique PNG/log artifacts. Capture-time
`LAB-TRIGGER-VIEW` records the displayed range, trigger and available samples.
Normal must retain a valid 25% pre-trigger capture after its latest sample
is older than the two-window acquisition range; Auto must show the live end
tick, nonempty data, no trigger marker and no waiting state without a crossing.
This covers renderer-window retention, not exhaustion of SimSession's archive.

NativeLab `p_a0b31f45e715` reproduced the Single log failure and passed the
other four tests. Its saved log contains `[LAB-TRIGGER] single t[RAM_17]`:
stderr diagnostics interrupted the buffered stdout record. The harness now
captures stdout/stderr into separate temporary files and combines them only
after process exit with a `[TEST-STDERR]` separator. Cross-stream ordering is
not implied. Parsing still requires complete records; no retries or relaxed
timing assertions were introduced.

NativeLab `p_f8c0515a68c3` passed all five GUI trigger tests in 35.97 s after
that fix. The current Normal PNG was inspected: retained rising TPS trace,
TRIG marker at 25%, `T:N WAIT`, frozen scope readouts and continuing engine
state. Auto fallback and empty first-wait state passed their capture-time
assertions. Further boundary coverage includes 10% pre-trigger and rearming
while paused; the entire UI-33 requirement is not declared complete.

### OES oscilloscope stroke taper — 2026-11-18

The digital scope already used the donor GeometryGenerator but forced a
constant 1.4 px stroke and overpainted it with SDL lines. The renderer now
uses the literal width calculation extracted from OES Oscilloscope::render:
`line_width * max(s, 0.5)`, plus the original additive tip highlight for
`s > 0.95`, with `s = index / count`. The initial width is 0.5 px. The donor
desktop's pixelsToUnits is identity. Duplicate SDL overpainting was removed;
the >5000-point fallback retains SDL lines with an explicit channel color.
Temporal splitting/decimation and digital high-level shading remain SEVEL
adaptations; the analog scope still has its own timestamp/gap-aware drawing.

Source `.work/open-engine-sim/src/oscilloscope.cpp` SHA-256:
`10d6d0a80903631f5c84a208e7af057607c61283ac0a3904c796895af744c334`.
Destination `third_party/open-engine-sim/include/oscilloscope_path.h` SHA-256:
`41252e3423c1ab75c63aa0014ee5ed45ebed797f1c09187889445db44536a8d4`.
The extracted header retains MIT attribution; production does not read .work.

NativeLab `p_90e6de43567b` rebuilt and passed three tests in 13.79 s:
DonorScope.PathWidthPreservesDonorTaperAndTip and digital events/cursors GUI
captures. The math test checks the half-pixel floor, 95% transition, 2.59 px
tip for 100 points and additive rather than multiplicative tip scaling.
The current digital-cursors PNG was inspected after removing overpainting:
older edges are thinner, recent edges emphasized, both cursors and electrical
measurements remain visible. This is a focused batch, not full DPI acceptance.

### Default-camera mechanical margins strengthened — 2026-11-18

The existing full-cycle mesh test now requires at least 10% clearance from
all four pane edges, previously 5%. It still measures actual submitted
vertices before clipping at 145 phases (0–720 degrees, step 5), four pane
sizes and six views: 3480 combinations, with spark/combustion/pin markers
enabled. Minimum normalized margins are available as GoogleTest properties
when XML output is requested. No production camera change was needed.

NativeLab `p_f57ca632d556` completed the parallel build and passed
DonorScene.FullCycleMeshesStayInsideDefaultViewports in 42.39 s. This proves
the stronger sampled bound for zoom 0.78 and zero pan in the tested panes.
It is not an analytic continuous-angle bound or acceptance of automatic FIT:
SdlDisplay::fit_scene_camera separately samples 16 phases without pulses,
then rescales/recenters into its useful target area. That fitted camera and
its marker envelope still need their own regression before closing UI-11.

### Shared automatic FIT and cycle regression — 2026-11-18

Moved the existing 16-phase FIT calculation from SdlDisplay into
`include/lab/SceneCameraFit.hpp`, with a generic x/y/w/h rectangle so tests
use the production calculation without SDL dependencies. Sampling, zoom
limits and anchor math are unchanged; the GUI calls the same function.

`DonorScene.AutomaticFitContainsFullCycleWithMarkers` fits with the same
marker-free probe as production, then checks actual vertices with all
markers active every 5 degrees through 720 degrees. It covers six views
and two panes (269x576 and 720x350): 1740 combinations. Target rectangles
use the desktop 80%-width and 108 px top/16 px bottom allowances. Every
vertex must remain within the target, allowing 0.1 px floating-point error.
This verifies sampled containment, not an extra 10% inset inside that target
or every responsive/DPI layout.

NativeLab `p_c0c9f1a7a93f`: parallel full build and the new test passed
(14.10 s test time). `p_5a2a254f52b2`: both GUI FIT-button interaction tests,
900x620 and 1920x1080, passed in 3.72 s. No broad screenshot acceptance was
repeated for this behavior-preserving extraction.
