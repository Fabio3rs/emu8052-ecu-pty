# SEVEL Lab donor reuse

The presentation donor is the local `open-engine-sim` checkout at commit
`1e226ee7bfbeb1d5012c7696aee82a57355df281`. Its root license is MIT;
the original Ange Yaghi copyright and license text are in
`third_party/open-engine-sim/LICENSE`. The local upstream `engine-sim` checkout
at `85f7c3b959a908ed5232ede4f1a4ac7eafe6b630` is a comparison source,
not a build dependency. No proprietary community-edition files are imported.

| Donor path | Local path | License | Modification | SHA-256 |
| --- | --- | --- | --- | --- |
| `include/renderer.h` | `third_party/open-engine-sim/include/renderer.h` | MIT | None | `60729e83c038d4510ce9f01180b562049d72cb05ed91d36c9d50e3107e5bf8` |
| `include/render_math.h` | `third_party/open-engine-sim/include/render_math.h` | MIT | None | `4fe33a3c8cc39bdf1011032257f83504da0838f8a6fb89a91d1f3d884e6270dd` |
| `include/shaders.h` | `third_party/open-engine-sim/include/shaders.h` | MIT | None | `494f7f024b749c1073d2148b821ecab0e1ccfbd3e27c7fa9c3e331f59fb27629` |
| `src/shaders.cpp` | `third_party/open-engine-sim/src/shaders.cpp` | MIT | None | `37bf29a66304f6608bf871bcc70541e22426b65052096cb3803d631f0709288d` |
| `include/sdl_gpu_renderer.h` | `third_party/open-engine-sim/include/sdl_gpu_renderer.h` | MIT | None | `4120785969dbfa2fdfb6ac565872191f9b0845356ba6eb8f4f78b5f8f250ce0e` |
| `src/sdl_gpu_renderer.cpp` | `third_party/open-engine-sim/src/sdl_gpu_renderer.cpp` | MIT | None | `d2ea282d5d5e8e6abca5d4ba60c166adec731163f64106478191b52196ce293c` |
| `assets/shaders/engine_sim.hlsl` | `third_party/open-engine-sim/assets/shaders/engine_sim.hlsl` | MIT | None | `1b2a84ac016479f75778f01ab05ef0c0000b99fca1017e587de9965183d69a8f` |
| `assets/shaders/engine_sim.vertex.msl` | `third_party/open-engine-sim/assets/shaders/engine_sim.vertex.msl` | MIT | None | `0163ffae0eafd4056401409201208430135b522ed2be562aaea673b503b78146` |
| `assets/shaders/engine_sim.fragment.msl` | `third_party/open-engine-sim/assets/shaders/engine_sim.fragment.msl` | MIT | None | `e874caa51e8bf19ec95d3532501e1858e13ad2f968af6cd7b16a9a0f23228424` |
| `assets/shaders/engine_sim.vertex.spv` | `third_party/open-engine-sim/assets/shaders/engine_sim.vertex.spv.zlib.b64` | MIT | Lossless packaging | Original `09b1c962916c34b8d22b06c7df24b58d86738b84c4ab97f1dc9ab8f00f8a0d09`; packaged `60f2e524be510044874ed8cb98f66faf17d677a91a15ee0cac02d50a4276b582` |
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
| `include/gauge.h` | `third_party/open-engine-sim/include/gauge.h` | MIT | Retained donor configuration and `std::vector<Band>`; removed application-bound render methods, added reset/getter and bounded band access | Donor `97c1289d779da8da6662e287fc59d238336592894c7efa7594e9667afd57e981`; local `5a13193b6028132f2b55aa212b45079fc41966897667dda8bb97b4b7da04b4e2` |
| `src/gauge.cpp` | `third_party/open-engine-sim/src/gauge.cpp` | MIT | Retained constructor and spring-damped update; removed GPU rendering, guarded zero range and bounded frame delta | Donor `b8df51e45a9da4b8d71784c1b0d53a6bfcdc2ae97107c93964bc4850c526b9dc`; local `e0c848bae23bd79aa9d38715bba2c1b14cb1da2812c4b6931d308140995b4be3` |
| `src/gauge.cpp` (radial ticks) | `src/lab/LabInstruments.cpp` | MIT | Adapted to SDL3 software gauges | Donor `b8df51e45a9da4b8d71784c1b0d53a6bfcdc2ae97107c93964bc4850c526b9dc` |
| `include/oscilloscope.h` | `third_party/open-engine-sim/include/oscilloscope.h` | MIT | Removed application-bound render methods; replaced raw point arrays with a bounded `std::vector` ring and ordered-point accessor | Donor `c7823144db2db9a307041af83359b698814346e097ccadbb4590d875a35a6d43`; local `ecd3da6e3966d0c993f146e1a6a5a1ac81ceb3d5d89f9f3de565f6518b02f5ee` |
| `src/oscilloscope.cpp` | `third_party/open-engine-sim/src/oscilloscope.cpp` | MIT | Retained sample-window and dynamic range logic; replaced raw arrays with `std::vector`, removed GPU rendering and added ordered-point output for the Lab | Donor `10d6d0a80903631f5c84a208e7af057607c61283ac0a3904c796895af744c334`; local `ff0897176b67bd32bac23a71fc7c6ac417b7da2cf15ec622ff6aa75432a52685` |
| `src/oscilloscope.cpp` (path algorithm) | `src/lab/LabInstruments.cpp` | MIT | Adapted `startPath`/`generatePathSegment` through the unmodified donor `GeometryGenerator`; event traces remain tick-based and use `std::vector` storage | Donor `10d6d0a80903631f5c84a208e7af057607c61283ac0a3904c796895af744c334` |
| `src/ui_button.cpp` (frame/hover/held design) | `apps/sevel-ma17-lab/SdlDisplay.cpp`, `include/lab/LabButtons.hpp` | MIT | Adapted button drawing and hit testing to SDL3 software renderer and the Lab's command queue; no donor UI runtime copied | Donor `81192da119c73446ab5ae340a7731f87ef10db604ba2c93110fb3dff4babc48d` |
| `src/firing_order_display.cpp` (circular cylinder indicator) | `apps/sevel-ma17-lab/SdlDisplay.cpp` | MIT | Adapted the donor's ring-and-light presentation to a fixed SEVEL 1–3–4–2 strip; brightness comes from actual recent combustion/misfire events, without importing donor engine state | Donor `34d6326043d9da2a316da3f387a9947b60cb126cc2e4ea8962dc0c9a24124f85` |
| `assets/es/sound-library/smooth/smooth_39.wav` | `third_party/open-engine-sim/assets/smooth_39.wav.zlib.b64` | MIT (donor root) | Complete WAV, losslessly packaged with zlib/Base64 | Original WAV `75de9db47063395665d36b6d4232f477aae385feaa9ba158353fbdaf122db5cc`; packaged text `f64df2895813394ec2a5b4d248474f38f74da2fbe031495f5d8bcbfc63f47496` |
| `assets/es/sound-library/smooth/smooth_39.wav` (first 2048 PCM frames) | `include/lab/SevelImpulse.hpp` | MIT (donor root) | Exact PCM samples in `std::array`; runtime convolution gain is configured separately | Local text `c925313058584b5656eef3f5cd7fbfc26566675f5ea953a63f56eb831dc70159` |

The renderer and math headers provide a backend-neutral drawing contract. The
donor `Shaders` state now supplies object transforms and colors for mechanical
draw submissions. The original SDL GPU backend and compiled shaders are built
for an opt-in second-window scene preview. NativeLab/Xvfb reports no supported
SDL GPU backend, so only the primary SDL software window was visually verified.
unmodified donor `GeometryGenerator::generateLine2d` builds each mechanical
stroke in the SDL3 window from the same SEVEL poses used by the headless scene.
`DonorScene` owns generator cleanup and the Lab test compares all 47 stroke
bounds across four crank phases. The
audio subset builds as `open-engine-sim-audio`; `AcousticAdapter` feeds it from
real MA1.7/SEVEL combustion events for offline WAV and SDL3 live playback.
The 2048-frame donor-derived impulse retains 99.69% of the complete WAV's
sample energy and is convolved at 35% mix. The complete source is archived
losslessly above. This is an acoustic effect, not a Fiat exhaust measurement.
The three live Lab dials instantiate the adapted donor `Gauge` class for
spring-damped needle state; SDL software draws their radial geometry. The
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
Two small, labeled axial panels now draw the imported `Crankshaft` mesh for
the 1/4 and 2/3 journal pairs at opposite physical phases. They use the same
snapshot as the longitudinal scene and are kept separate from it.
The static donor `CylinderHead` mesh sits behind eight donor `Valve` meshes
whose lifts follow the documented SEVEL timing. The schematic single camshaft
remains visible.
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
