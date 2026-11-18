# OES visual geometry reference for the SEVEL Lab

Source checkout: `.work/open-engine-sim`, revision
`1e226ee7bfbeb1d5012c7696aee82a57355df281`. This is a read-only
coordinate inventory, not a second engine or a calibration source. The
production mesh/font copies and their hashes are listed in
[SEVEL_LAB_REUSE.md](SEVEL_LAB_REUSE.md).

## Donor panel fractions

Machine-readable export: [SEVEL_LAB_OES_COORDINATES.csv](SEVEL_LAB_OES_COORDINATES.csv).
Each row gives a normalized rectangle in **top-left drawable coordinates**;
`x1` and `y1` are exclusive edges. The source column points into
`.work/open-engine-sim/src/` at the revision above. Convert to pixels with
`(x0*W, y0*H, (x1-x0)*W, (y1-y0)*H)`. Decimal thirds are rounded to nine
places in the CSV, so compare resulting pixels with a one-pixel tolerance.
For the 2048×838 supplied screenshot use `W=2048`, `H=816`, and add 22
pixels to each Y edge for the desktop title bar. These rectangles include
overlapping parent/child rows; they are reference geometry, not a flat tiling.

Fractions below are relative to the named parent rectangle. OES `Bounds`
uses a bottom-origin Y axis; SEVEL SDL rectangles use top-origin Y. Thus
`donor.verticalSplit(a,b)` maps to SDL top interval `[1-b,1-a]`.

### Exported dashboard boxes

These rectangles come from `Grid::get` in `include/ui_math.h:189-202`
and `EngineSimApplication::renderScene`, with the default dashboard screen
(`m_screen == 0`). Coordinates are **top-left origin**, half-open
`[x0,x1) × [y0,y1)`, normalized to the OES drawable content. For the supplied
2048×838 screenshot the content begins at screen `y=22`, so multiply `x`
fractions by 2048, `y` fractions by 816, then add 22 to both screen `y`
coordinates. Pixel values are rounded to the nearest pixel and are references,
not additional layout constants.

| Element | Normalized x0–x1 | Normalized y0–y1 | Screenshot x0–x1 | Screenshot y0–y1 |
|---|---:|---:|---:|---:|
| Left column | 0–1/3 | 0–1 | 0–683 | 22–838 |
| Header/info | 0–1/3 | 0–2/9 | 0–683 | 22–203 |
| Left mixer | 0–1/3 | 2/9–1/3 | 0–683 | 203–294 |
| Left performance | 0–1/3 | 1/3–2/3 | 0–683 | 294–566 |
| Left load controls | 0–1/3 | 2/3–1 | 0–683 | 566–838 |
| Center engine view | 1/3–2/3 | 0–1/2 | 683–1365 | 22–430 |
| Center oscilloscope | 1/3–2/3 | 1/2–1 | 683–1365 | 430–838 |
| Right tachometer | 2/3–5/6 | 0–1/4 | 1365–1707 | 22–226 |
| Right vehicle speed | 2/3–5/6 | 1/4–1/2 | 1365–1707 | 226–430 |
| Right ignition | 5/6–1 | 0–1/2 | 1707–2048 | 22–430 |
| Right throttle | 2/3–5/6 | 1/2–3/4 | 1365–1707 | 430–634 |
| Right AFR | 2/3–3/4 | 3/4–1 | 1365–1536 | 634–838 |
| Right fuel | 3/4–5/6 | 3/4–1 | 1536–1707 | 634–838 |
| Right manifold pressure | 5/6–1 | 1/2–2/3 | 1707–2048 | 430–566 |
| Right air flow | 5/6–1 | 2/3–5/6 | 1707–2048 | 566–702 |
| Right volumetric efficiency | 5/6–1 | 5/6–1 | 1707–2048 | 702–838 |

For any drawable size `W×H`, the same table scales as
`x_px = round(W*x_fraction)` and `y_px = round(H*y_fraction)`; the window
decoration offset applies only when measuring a full desktop screenshot.
The donor draws borders at these box edges. The SEVEL two-view center splits
the engine box again; preserve physical aspect ratio in each view instead of
scaling the mesh independently in X and Y.

### Internal grid coordinates

All intervals below use the same **full drawable** normalized axes as the
table above; each cell is half-open. These are derived from the nested `Grid`
calls, so they also export the distances between neighboring instruments.
At 2048×816 drawable pixels, a horizontal `1/18` step is 113.8 px, a
`1/9` step is 227.6 px, and a vertical `1/8` step is 102 px. The full-window
coordinates must be converted to screenshot coordinates with the 22 px top
decoration offset above.

| Region / contents | X intervals | Y intervals | Donor source |
|---|---|---|---|
| Info: logo, title | 0–1/18; 1/18–1/3 | 0–1/9 | `info_cluster.cpp:54-70` |
| Info: toolbar | 1/18–1/3 | title's bottom 24%, Y `0.76/9–1/9` | `info_cluster.cpp:38-42,71-86` |
| Info: vehicle, status | 0–1/3 | 1/9–1/6; 1/6–2/9 | `info_cluster.cpp:88-106` |
| Mixer: VOL., CONV., +HF, ~LF, ~HF, LVL. | successive 1/18 cells from 0 to 1/3 | 2/9–1/3 | `mixer_cluster.cpp:146-169` |
| Performance: FPS, RT/dT, 1/SPEED | successive 1/9 cells from 0 to 1/3 | 1/3–1/2 | `performance_cluster.cpp:189-204` |
| Performance: LATENCY, IN. BUFFER, FREQUENCY | same three columns | 1/2–2/3 | `performance_cluster.cpp:205-214` |
| Load: status, CLUTCH, GEAR | same three columns | 2/3–5/6 | `load_simulation_cluster.cpp:191-203,288-291` |
| Load: DYNO. SPEED, TORQUE, POWER | same three columns | 5/6–1 | `load_simulation_cluster.cpp:204-227` |
| Scope: focus plot/title | 1/3–2/3 | 1/2–3/4 | `oscilloscope_cluster.cpp:268-279` |
| Scope thumbnails: waveform, exhaust flow, valve lift | successive 1/9 cells from 1/3 to 2/3 | 3/4–7/8 | `oscilloscope_cluster.cpp:243-266` |
| Scope thumbnails: torque/power, pressure-volume, gas flow | same three columns | 7/8–1 | `oscilloscope_cluster.cpp:243-266` |

The focus plot reserves **39 px** at the top for its title (`24+15`), measured
inside its focus rectangle; this margin is fixed in pixels, whereas its outer
box is proportional. Thus the plot's drawable height is `H/4-39` on the
default dashboard. The donor does not allocate a full-width signal plot under
the entire engine view: the bottom half is a 3×4 grid with the focus plot
spanning its top 3×2 cells.

| Parent | Child | Horizontal fraction | Vertical fraction | Donor source |
|---|---|---:|---:|---|
| Window | Left information/control | 0–1/3 | 0–1 | `desktop_application.cpp:189-200` |
| Window | Engine view | 1/3–2/3 | top 1/2 | `desktop_application.cpp:193` |
| Window | Oscilloscope | 1/3–2/3 | bottom 1/2 | `desktop_application.cpp:195` |
| Window | Right instruments | 2/3–1 | 0–1 | `desktop_application.cpp:194` |
| Right instruments | Tach/speed/ignition | 0–1 | top 1/2 | `right_gauge_cluster.cpp:198-205` |
| Right instruments | Throttle/air/fuel | 0–1 | bottom 1/2 | `right_gauge_cluster.cpp:200-205` |
| Upper right | Tachometer | 0–1/2 | top 1/2 | `right_gauge_cluster.cpp:216-222` |
| Upper right | Speedometer | 0–1/2 | bottom 1/2 | `right_gauge_cluster.cpp:237-238` |
| Upper right | Ignition | 1/2–1 | 0–1 | `right_gauge_cluster.cpp:246` |
| Lower right | Throttle | 0–1/2 | top 1/2 | `right_gauge_cluster.cpp:250-255` |
| Lower right | AFR/fuel | 0–1/2 | bottom 1/2, then halves across | `right_gauge_cluster.cpp:257-265` |
| Lower right | Pressure/air/VE | 1/2–1 | three equal rows | `right_gauge_cluster.cpp:268-304` |

The current SEVEL desktop outer split is **24/42/34%**. The shared scope
height is `max(248 px, 40% of output height)` for a center panel at least
460 px wide; a narrower center uses 146 px. It is capped at `height-112 px`
on very short windows. The two mechanical views share
the height above that scope, with a 12 px bottom margin
(`LabLayout.hpp`, `LabInstruments.cpp`, `SdlDisplay.cpp`). The right cluster
splits its upper width equally between tach/speed and ignition, as in OES. Below
1100 px, the left column collapses and the second large dial shows coolant
instead of vehicle speed, preserving RPM, coolant and lambda in the compact
view.
The adapted analog `Grid` places its focus plot above eleven SEVEL previews.
At scope height 360 px or greater, the previews occupy six columns and two
52 px rows at the bottom, with the final cell empty. Between 248 and 360 px
they occupy one eleven-column row. Each cell has a 3 px horizontal and 4 px
vertical gap. The plot and its two signal bands derive from the same focus
rectangle; the 41 px gap before the previews contains cursor and time labels. A panel
below 248 px omits previews and retains the focus plot.
Those are deliberate adaptations, not values exported from OES. Copying the
donor's one-third center width would leave too little room for two views.

Each mechanical camera now fits the recorded donor triangles into its own
viewport. The fit unions 16 visual poses across a 720-degree crank cycle,
then applies one zoom and pan to that view; it does not change the snapshot,
engine geometry or physical model. Desktop viewports reserve 10% width on
each side, while the compact layout reserves 14% and extra space above the
head for labels and the shaft detail overlay. The fit is recomputed on resize,
focus change, `R`, and the visible `FIT` button. On compact windows, `VIEW`
and `FIT` occupy the free row above the mechanical panes; drawing and hit
testing share their rectangles. Wheel zoom and middle-button pan remain
independent after fitting.

## Gauge proportions and pixels

Machine-readable gauge constants: [SEVEL_LAB_OES_GAUGE_METRICS.csv](SEVEL_LAB_OES_GAUGE_METRICS.csv).
The fractional values apply to the named parent dimension or dial radius;
fixed pixel values belong to the donor's drawable coordinate scale.
Derived gauge placement at the reference drawable size is in
[SEVEL_LAB_OES_GAUGE_PLACEMENT_2048x816.csv](SEVEL_LAB_OES_GAUGE_PLACEMENT_2048x816.csv).
Its pixel coordinates exclude the desktop's 22 px title bar. The signed
`needle_inner_px` is behind the dial center; `needle_outer_px` is ahead.
For another size, recompute the panel from the normalized coordinates CSV,
then use `R=min(w-20,0.9*(h-20))/2`, `cx=x+w/2`, and
`cy=y+30+0.55*(h-20)`. The 10 and 20 px terms are donor constants and
should follow UI scale on a high-density display.

`labeled_gauge.cpp` sets a 10 px inset, title in the top 10% of the inset
(`24 px` text), value in the lower quarter of the gauge area (`height/8`
text), gauge center 20 px below its element center, and outer radius
`min(gaugeWidth,gaugeHeight)/2`. Its needle runs from `-0.10 R` to `0.70 R`;
`right_gauge_cluster.cpp` sets the main needle width to 4 px. The tachometer
arc runs from `1.2π` to `-0.2π` radians. The exact donor bands and steps are
motor specific and are replaced by `SevelInstrumentProfile.hpp`.
For a donor gauge panel of width `w` and height `h`, the drawable dial has
`w_d=w-20`, `h_d=0.9*(h-20)`, radius `R=min(w_d,h_d)/2`, and a dial center
20 px below the center of that drawable area. Thus in the supplied screenshot
the tachometer/speedometer panels have `R=82.8 px` and needle tip radius
`58.0 px`; the manifold/air/efficiency panels have `R=52.2 px` and tip
radius `36.5 px`. These figures explain why simply applying the OES needle
length to a much smaller SEVEL panel would make the dial hard to read.
The major/minor tick lengths are **10/5 px** and widths **2/1 px**;
the main needle width is **4 px**. The needle starts `0.10R` behind the
center, ends `0.70R` ahead, and therefore spans `0.80R`. For two neighboring
main gauges, the center separation is one panel height (`H/4`, 204 px in the
reference screenshot); for the three stacked small right gauges it is `H/6`
(136 px). These fixed pixel tick widths should be scaled with UI scale on a
different-density display, while the dial radius follows its panel bounds.
The throttle slider's active bounds are the throttle panel's X interval
`0.84–0.96` and bottom-origin Y interval `0.12–0.82`, i.e. top-origin Y
`0.18–0.88` (`right_gauge_cluster.cpp:307-313`).
The donor `firing_order_display.cpp` draws each ignition light as a disc of
`0.75 R` with a ring from `0.80 R` to `0.85 R`. The SEVEL indicator uses these
fractions for four cylinders and adds two compact pair markers from its own
spark events.

The SDL dial (`LabInstruments.cpp:852`) now uses the donor's 10 px inset and
`R=0.5*min(boxWidth-20s,0.9*(boxHeight-20s))`, where `s` is the UI scale.
Its center follows the donor's inset/title/gauge fractions; the downward
offset is `min(20s,0.1*boxHeight)` so the two half-height SEVEL lambda cells
keep their numeric values clear. The needle spans `-0.10 R` to `0.70 R`.
Major/minor marks use the donor's 10/5 px lengths and 2/1 px widths, with
lengths reduced by `min(s,boxHeight/136)` below the donor's smallest right
gauge cell height. The reduced metrics are an adaptation for the SEVEL split.

## Mesh and camera proportions

Machine-readable local mesh bounds: [SEVEL_LAB_OES_MESH_METRICS.csv](SEVEL_LAB_OES_MESH_METRICS.csv).
These are the `v` records under each named `o` block of
`.work/open-engine-sim/assets/authored_meshes.obj`, rounded to six decimal
places. X and Y are model units before object transforms; the authored meshes
are planar (Z = 0). `width_over_height` is a shape ratio, not a screen ratio.
To compare a rendered part, multiply **both** dimensions by its uniform object
scale and then by the same camera pixels-per-metre value. Rotation can change
its axis-aligned screen box without changing the shape. In the donor,
`PistonObject::render` scales `Piston` by `bore/2`; for a hypothetical
86.4 mm bore, its local 2.000185 × 1.599286 extent becomes
86.408 × 69.089 mm. The SEVEL draw now uses `bore/2 = 0.0432 m` on both axes,
giving the same mesh extent at the documented bore. Its crown stays 23 mm
above the wrist pose, a drawing offset rather than a measured Fiat piston
dimension.
`ConnectingRod`, `CylinderHead`, and `Valve` also receive their own transforms
in the donor (`connecting_rod_object.cpp`, `cylinder_head_object.cpp`), so
their CSV bounds should not be interpreted as final pixel sizes.

The donor OBJ asset contains the named `Piston`, `ConnectingRod`, `Crankshaft`,
`CylinderHead`, and `Valve` meshes. `Piston` spans approximately `[-1,1]` in
local X and `[0,1.5993]` in local Y. OES `piston_object.cpp:33-43` scales the
piston from bore/2. In SDL's top-origin projection, positive local Y formerly
put the curved skirt at the top. The SEVEL views now reflect local Y: the
flat edge and ring marks at mesh Y=0 face the head, while the curved skirt at
mesh Y=1.599286 faces the crank. Both views retain the bore/2 scale, and the
translation is tied to the SEVEL wrist-pin pose. The rod length and crown offset
are estimates, not Fiat specifications. The bore and stroke remain the
project's SEVEL values.

OES `desktop_application.cpp:237-238` derives camera width from viewport
aspect ratio; its display height is 0.6096 m at zoom 1. The SEVEL two-view
camera uses a viewport fit instead: `pixelsPerMetre = zoom *
min(viewportWidth/worldWidth, 0.72*viewportHeight/worldHeight)`. The
donor's 2048×816 drawable gives its engine panel 682.7×408 px, so its
zoom-1 scale is `408/0.6096 = 669.3 px/m` **on both axes**. The visible world
width is `0.6096*(682.7/408) = 1.0199 m`. The scene composition adds a
`-0.12 m` vertical transform (`desktop_application.cpp:21,266-271`), about
80.3 px at this size. This moves the scene as a whole; it must not stretch
the piston, rod or cylinder head. Their screen positions additionally depend
on the active engine geometry, crank angle, viewport pan and zoom, so a static
pixel bounding box for those parts would be misleading. Use the donor OBJ
mesh vertices and their object transforms for shape, and the uniform camera
scale for size.
The SEVEL longitudinal bounds are `3.4*pitch+0.08 m` by `0.34 m`; the focused axial
bounds are `0.14 m` by `0.34 m`. Both clip axes use the same
`pixelsPerMetre`, and the scene center is placed at 42% of viewport height.
This is implemented in `scene_fit_projection()` and shared with the shaft
overlay. It prevents the long, narrow viewport from stretching one axis.
The SDL profile camera adds 10% of viewport height in downward pan so the
head clears the title and view controls at 1280×720.

The projected engine viewport and piston sizes at 2560×1440 are exported in
[SEVEL_LAB_OES_ENGINE_PROJECTION_2560x1440.csv](SEVEL_LAB_OES_ENGINE_PROJECTION_2560x1440.csv).
The OES row uses a hypothetical 86.4 mm bore for shape comparison; the donor
reference itself runs a different engine. The SEVEL focused profile is larger
than its longitudinal piston because its narrow 0.14 m world width allows a
height-limited camera fit. The profile scale includes the initial camera zoom
of `1−12/1440` at this output size. Mesh widths and heights use the local
OBJ bounds times `bore/2` and a single pixels-per-metre factor. Their signs
and screen position depend on the view transform and piston pose; these CSV
sizes are unsigned extents, not measured screenshot boxes.

## Equal-resolution layout comparison

At 2560×1440, the donor reference is `.work/donor-reference-2560x1440.png`
(SHA-256 `5bd900e5291278230cdb02e31f2a624a5dfb3aeef0ea91223e4d358d24dd8b9a`).
The current SEVEL capture is `build-lab/sevel-piston-upright-2560x1440.png`
(SHA-256 `cb6ed43903e5e6db27e7c18de4cef85c89fc7f9500623d120a989da2ddef28b4`).
It was generated through NativeLab from the original Fiat Tipo ROM at tick
1,500,000 with the bench preset. These images compare layout and scale only;
the donor runs a different engine and scenario. The earlier
`.work/donor-1920x1080.png` is entirely black and is not comparison evidence.

The machine-readable rectangles and dial radii are in
[SEVEL_LAB_LAYOUT_COMPARE_2560x1440.csv](SEVEL_LAB_LAYOUT_COMPARE_2560x1440.csv).
The SEVEL outer columns are 24/42/34% to fit two mechanical views. Its right
cluster now splits at y=720 px, the same height as the donor's right cluster.
The SEVEL tachometer radius is 149.4 px, versus 153.0 px in the donor; before
adjusting the top margin and dial inset, it was 135.5 px. The meshes retain a
uniform X/Y projection in both SEVEL views, so this gauge adjustment does not
change piston or cylinder proportions.
