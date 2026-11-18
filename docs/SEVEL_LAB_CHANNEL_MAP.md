# SEVEL Lab channel and source map

All `EmulatorSnapshot` values carry `snapshot.tick`, measured in 990,000
machine ticks per simulated second. The scope reads the bounded history
published by `SimSession`; the GUI never changes the acquisition cadence.
The warm original-ROM determinism test compares 3,000 retained snapshots
and 181 recorded events through the same 1.5 s interval while a consumer
polls `latest()` every 8 ms or 32 ms. It checks source ticks, physical
readings, ADC conversion values/ticks and event timestamps against an
unpolled run. A separate GUI test compares final state and event hashes at
8 ms and 32 ms frame delays with audio enabled and disabled.
The most recent 16,384 snapshots remain at source resolution. A separate
archive retains the first and last original snapshots and the minimum and
maximum of each displayed analog field in every 100 ms block, plus both
sides of sampled idle-contact and fan transitions, for up to 300 s. The
archive also keeps both sides of changes in producer availability or finite
value state, including the candidate idle-actuator stem and first exhaust
sample. These retained boundaries prevent a long-window trace from bridging
a short missing-data interval within one archive block. The
lambda extrema require both crank availability and a received exhaust
sample, matching the displayed lambda trace; the sensor-voltage baseline
remains a separate valid channel when the crank is available. The
ADC0/1/2/3/5/6 traces also retain the minimum and maximum valid pin voltage
and both sides of valid-to-missing transitions in each block. A held ADC
conversion may appear in several snapshots; its original conversion tick is
kept even when the archive retains a different snapshot with the same value.
The archive is still sparse: intermediate shape and pulses with no sampled
extremum may be absent. The scope offers a 300 s window and shows the
observed minimum and maximum intersample rates when archive and recent data
overlap. The header labels this rate `SNAP`: it describes retained snapshot
spacing, not the update rate of an individual physical or ECU signal.
For drawing, each pixel column retains its first, last, minimum and maximum
source samples. CSV export still uses the retained source snapshots, not this
pixel reduction. Invalid samples and gaps over 250 ms split rendered traces.
The sampled idle-contact track also retains every observed state change and
the preceding sample, even when several changes fall in one pixel column.
The ADC0/1/2/3/5/6 last-conversion voltage traces use a held step between
observed conversions; a sloped connection would imply unobserved voltages.
The GUI places each step at the first retained snapshot observing it and
shows the latest conversion age in the channel label. The paired CSV keeps
the exact conversion tick for measurements that need finer timing.
`RAW -N` counts snapshots removed from the full-resolution buffer; selected
extrema may remain in the archive. `ARCH -N` counts archived snapshots removed
after the five-minute retention limit. Both counters reset with a tick reset.
Event edges retain their individual `EmulatorEvent.tick` timestamps.
In the digital CC3/P5.0/P5.1 scope, the mouse wheel selects 10, 20, 50,
100 or 250 ms, or 1, 2 or 5 s. These three pin lanes display retained
electrical edges. The fourth lane, `IDLE SW SAMP`, displays the physical
throttle contact from retained snapshots. Its step is placed at the first
snapshot observing a change; unavailable samples and gaps over 250 ms break
the trace. The four labels can be clicked independently. The X axis marks
time before the displayed tick in ms or s. A pin trace begins at its first
retained edge when no earlier state is known; `NO EDGE` replaces an assumed
low level when that channel has no retained event. Zoom does not add samples
or change the emulator clock.
Pin labels show the last complete high interval available in the window.
When a full rise–fall–rise cycle is present, the high label, low interval,
period and duty all describe that same cycle. The values come from event
ticks; the 1.5 px minimum used to make narrow pulses visible is ignored.
An isolated completed high interval remains available without inventing a
period or duty.
On the digital plot, left click places cursor A and right click places cursor
B on the nearest retained CC3, P5.0 or P5.1 pin edge within 12 display pixels.
The idle-contact lane snaps to the first valid snapshot observing a change,
provided its preceding sample is no more than 250 ms old. The readout labels
that timestamp `IDLE SAMP` and shows OPEN/CLOSED, never implying an exact
electrical edge. Pin rows show the original edge tick and HIGH/LOW state.
Both cursor rows report elapsed time; a level difference is shown when both
select the same channel.
When the panel is tall enough, a separate strip plots recorded spark events
as chevrons (cyan pair 1/4, amber pair 2/3), combustion as green squares and
misfire as red crosses. These markers use event ticks, independently of the
high intervals of the ECU output pins. The legend names each event class;
the compact panel omits this strip to preserve the four signal lanes.
The analog scope cycles through Lambda, TPS, Thermal, Intake, Engine, Fuel,
ADC TPS, ADC BAT/L, ADC IAT/E, Battery and Idle with `G` or by clicking its preview card.
`Z` or `MAX` enlarges
the analog scope. `FIT Y` computes both visible vertical bands once from
valid retained samples; `Y:RESET` restores their profile scales. `O` toggles
the same action. The sampled idle-contact band keeps its fixed 0–1 axis.
Fitted limits do not follow each render frame; the user must fit again after
changing the viewed data. Each group uses two separate unit axes. TPS overlays both model
voltages on a 0–5 V axis, then shows physical
throttle angle and sampled idle-contact state in separate tracks. The
contact step occurs at the first snapshot that observes the new state;
it is not an electrical edge timestamp. Gaps over 250 ms or unavailable
throttle snapshots break that track. Thermal overlays physical coolant ECT
and air-sensor IAT in °C on a shared axis, then plots thermostat opening in
% with a sampled fan-state track below it. Fan edges occur at the first
snapshot observing a change; missing thermal data or gaps break the line.
Intake plots absolute
manifold pressure in kPa and TBI inlet air flow in g/s. Engine
plots physical RPM and scenario resisting load in N·m. Fuel plots manifold
film and vapor in mg; these are state masses, not tank level or consumption.
Idle plots the candidate idle-actuator stem position in mm and the sampled
physical idle-contact state in separate tracks. Stem samples require
`idle_bridge_candidate`; contact samples require `throttle_available`. The
contact uses held steps at observed state changes, with all retained transitions
preserved within a screen column. The stem's -10 to 30 mm display scale is a
laboratory range, not a claimed absolute actuator stroke.
The two TBI panels show `--` for a missing candidate stem; `N/D` remains
reserved for an undefined measurement such as volumetric efficiency. The right
throttle drawing handles angle, cable, stem and contact availability
independently, so an invalid angle does not hide a valid contact observation.
The ADC groups display last completed conversions: ADC TPS uses ADC0/TPS2
and ADC6/TPS1, ADC BAT/L uses ADC1 after the modeled battery divider and
ADC5 after modeled lambda conditioning, and ADC IAT/E uses the ADC2/ADC3
NTC divider voltages. The physical battery supply, ECT/IAT temperatures
and raw exhaust-sensor voltage are distinct quantities. The Battery group
plots physical sensor-circuit supply and the last ADC1 divider conversion
on separate voltage axes. The ADC charts use held observations, not a
continuous pin-voltage waveform. Values older than 100 ms are absent from
the plotted scope; the conversion tick is retained in the snapshot. The
ADC CSV adds each channel's 10-bit count, conversion tick and age in ms
at the exported snapshot tick, so repeated held values remain identifiable.
For ADC groups it also exports raw ECU lower-RAM bytes 60h–67h from that
snapshot, labeled by address and kept separate from the ADC conversion
columns. Their sensor interpretation is unverified; the debug inspector
shows the same eight bytes in hexadecimal.
Its heading shows the effective rate calculated from visible source timestamps;
`PARTIAL` means an uncovered end of the window exceeds 5% of its duration.
`X` freezes the selected chart window; the simulation continues. In digital
mode it retains the current event window and up to five seconds of contact
snapshots, so later clicks and CSV/PNG export use the frozen tick and sources.
Pressing `X` again returns to live following. In analog mode, a left
click places cursor A and a right click places cursor B on the analog plot.
Cursor lines snap to timestamped source samples and the footer reports each
sample's time and values, plus Δt and Δvalue.
The mouse wheel changes the analog time span around the pointer. A middle
button drag pans through retained samples; `X` returns to live following.
A double-click on the plot restores the five-second live window. Mechanical
camera navigation stays within the engine viewports.
`T` cycles trigger off, auto, normal and single. `U` cycles the analog
channels in the current group, then recorded ignition pin 0, ignition pin 1,
injector pin, spark pair 1/4 and spark pair 2/3. `Y` changes the edge for
analog channels and pins; spark events have no edge polarity. `I`/`J`
raise/lower an analog level by one twentieth of its channel scale, and `B`
cycles 10%, 25% and 50% pre-trigger. An analog crossing uses the tick of the
first valid source sample past the level; a missing value or a gap over
250 ms breaks continuity. Pin and spark triggers use exact recorded
`EmulatorEvent.tick` values, with no interpolated edge or spark.
Normal and single show `WAIT` until a complete window is available. Crossing
search starts when the mode or a trigger setting is armed; an older crossing
does not satisfy a newly armed single capture. Auto falls back to the live
window; single holds the first complete trigger window
until `X` or a trigger setting change. The green line labels the selected
sampled crossing or recorded event. These controls only select a view of the
retained snapshots and events; they
do not alter the ECU or the physical simulation.
`C` writes the current analog group's source samples or the digital panel's
retained events and sampled contact transitions to
`.work/gui-review/sevel-scope-*.csv` and, when PNG support is built, the
matching cropped scope panel to `.png`. With both cursors on valid source
samples or digital transitions, their original ticks bound the CSV export.
Analog cursors lacking a retained sample fall back to their requested ticks;
digital cursors outside the visible window export the whole visible window.
Digital rows distinguish CC3 and
P5.0/P5.1 HIGH/LOW pin events, spark/combustion/misfire markers, and
`IDLE SW SAMP` OPEN/CLOSED transitions. The latter tick is the first valid
snapshot observing a change. Digital CSV includes all retained digital sources
in the time selection; its header records the visible channel mask, event
window base index and cumulative event overflow.
The PNG retains the displayed panel, including any cursors, at the selected
frame. Both CSV formats record selected and visible tick ranges, channel IDs,
sources, ROM hash and scenario arguments. The analog header additionally
records trigger mode/configuration and its crossing or event tick. The PNG embeds
those same comment rows in a `SEVEL Scope` text chunk, so it remains traceable
without its CSV companion. Missing measurements are empty CSV cells; the tick
and time columns remain intact.
The analog header also records `retained_sample_count` (the number of exported
data rows), `gaps_over_250ms` (adjacent retained ticks separated by more than
250 ms), and cumulative `raw_evicted_total`/`archive_evicted_total` counters.
The selection may include archived first/last/extreme snapshots rather than
every intermediate observation; `sample_policy` identifies that retention
policy. These counters describe the session, not only the selected interval.

| Display channel | Snapshot field | Reading point and source | Display validity |
| --- | --- | --- | --- |
| Tachometer gauge (`RPM P1.1?`) | `tachometer_rpm`, `tachometer_pulses` | `ecu_hw::Ma17Tachometer` observes emulated P1.1 latch rising edges; candidate connector 24, assumed two pulses/revolution | `tachometer_available`; first level is not an edge, two edges needed for a period; zero after 500 ms without pulses; 200 ms display filter; no physical-crank fallback |
| Physical engine speed (status/scopes) | `rpm` | Physical crank model, not ROM RPM | `crank_available`; retained independently from the candidate tachometer |
| ROM actual / nominal idle RPM | `ram47` / `ram46` | Raw IRAM bytes 47h / 46h, each multiplied by 25 RPM/count | Distinct actual and target values; raw retained RAM is not proof of a fresh timer measurement |
| Vehicle speed | `vehicle_speed_kmh` | Physical signed road speed when `drivetrain_available`; otherwise scenario input | `vehicle_speed_available`; tooltip distinguishes the source; reverse retains its negative numeric value beyond the dial's 0–200 scale |
| Gear | `transmission_gear` when `drivetrain_available`; otherwise GUI reference selection | Fiat ratios × 63/16 differential; donor gear-card geometry | Physical R/N/1–5 comes from applied telemetry, including replay. Reference mode retains N–5 and REF. Tooltip ideal speed assumes no clutch slip and estimated 0.29 m radius; it is not measured road speed |
| Clutch pressure | `clutch_pressure` | Physical drivetrain applied pressure fraction × 100; donor dial 0–100, minor 10, major 50, angles 0.8π to 0.2π | Requires `drivetrain_available`, finite fraction in [0,1]; missing/stale hides needle. 0=open, 100=engaged. Page Up/Down requests ±10 percentage points with clamping and replay lock; applied value appears in the TBI detail and wide-layout dial |
| Battery supply | `battery_supply_v` | Physical sensor-circuit supply before ADC1 divider | `battery_supply_available`; scenario value, not an observed ADC conversion |
| Coolant | `coolant_c` | Physical thermal model | `thermal_available` |
| Intake air temperature | `intake_air_c` | Physical thermal model at the air sensor, in °C; distinct from ADC2 voltage | `thermal_available` |
| Fan / thermostat | `radiator_fan_on`, `thermostat_open_fraction` | Physical thermal model | `thermal_available` |
| Applied load | `applied_load_nm` | Scenario resisting torque applied to crank | `crank_available`; not produced torque |
| Throttle angle / idle contact | `throttle_angle_rad`, `idle_contact_closed` | Physical throttle assembly | `throttle_available` |
| Cable command | `pedal_pull_m` | Physical throttle assembly | `throttle_available`; distinct from GUI target |
| Idle stem | `idle_stem_m` | Candidate idle-actuator bridge | Only meaningful when `idle_bridge_candidate` |
| TPS1 / TPS2 model | `tps_track1_v`, `tps_track2_v` | TPS circuit evaluated at physical angle, before ADC overrides | `tps_available`; not effective ADC-pin voltage |
| ADC0 TPS2 / ADC6 TPS1 last | `adc_last_conversion[0/6]` | Voltage driven at the pin and 10-bit count at the last completed conversion, with conversion tick | `sampled && voltage_available`; scope omits observations older than 100 ms |
| ADC1 battery divider / ADC5 lambda conditioner last | `adc_last_conversion[1/5]` | Modeled voltage driven to ADC1/ADC5, including an ADC5 fault stimulus; last conversion count and tick | `sampled && voltage_available`; scope omits observations older than 100 ms |
| ADC2 IAT / ADC3 ECT NTC last | `adc_last_conversion[2/3]` | Modeled NTC divider voltage driven to ADC2/ADC3, including an ECT open-circuit stimulus; last conversion count and tick | `sampled && voltage_available`; scope omits observations older than 100 ms |
| ECU IRAM 60h–67h raw | `rom_iram_60_67` | Lower RAM copied from the original ROM execution at the snapshot tick; no sensor meaning inferred | Always present as raw bytes; with key off, these are retained state rather than a new conversion |
| Lambda | `lambda` | Physical exhaust model attached to crank simulation | `crank_available && exhaust_sample_available`; dimensionless; no reading before the first exhaust packet arrives |
| Oxygen-sensor voltage | `lambda_voltage_v` | Physical exhaust sensor model, including its pre-arrival 0.45 V baseline | `crank_available`; not conditioned ADC5 voltage or a measured lambda |
| Manifold pressure | `manifold_pressure_pa` | Intake model, absolute pressure | `intake_available`; no external MAP sensor claimed |
| Air flow | `air_in_kg_s` | Intake model at throttle-body inlet | `intake_available`; converted to g/s by GUI |
| Injected fuel total | `injected_fuel_total_kg` | Intake model cumulative injected mass | `intake_available`; converted to mg/g by GUI |
| Fuel film / vapor | `fuel_film_kg`, `fuel_vapor_kg` | Intake manifold model state | `intake_available`; converted to mg by GUI |
| Injector pulses | `injector_pulses` | Injector stage pulse counter | `injector_available`; independent of fuel mass |
| CC3 / P5.0 / P5.1 | `EmulatorEvent` edges | Emulator output pins; electrical polarity kept neutral | Event-window availability and overflow matter |
| Ignition `PIN 1/4`, `PIN 2/3` | `IgnitionPin` events mapped by the last recorded `Spark` pair/channel binding | ECU output edge, either polarity; 10 ms display afterglow | No inferred pair until a spark establishes the channel mapping; exact edge tick remains in the scope |
| Ignition `SPK 1/4`, `SPK 2/3` | `Spark` events | Ignition-stage spark attempt; 5 ms display afterglow | Separate from the electrical edge and from combustion |
| Ignition cylinder 1–4 discs | `Combustion` / `Misfire` events | Physical burn outcome; 10 ms display afterglow | Misfire uses red and `!`; a spark alone cannot light a burn disc |
| ROM fault banks | `rom_current_fault_banks`, `rom_history_fault_banks` | XRAM F84E–50 / F85E–60 | Raw bytes; not decoded DTCs |

The debug summary labels the accumulated `injector_pulses` value `INJ PULSES`.
`CC3` names the electrical pin trace and its current level, not this counter.

`volumetric_efficiency`, intake AFR, produced torque, produced power, fuel
tank level, cylinder pressure and exhaust flow
are not published by this snapshot. Their gauges must show `N/D` or remain
absent; no widget may synthesize them from throttle angle or pulse count.
An instrument with a defined channel but no valid current reading shows `--`
and its tooltip says `MISSING`; `N/D` is reserved for an undefined channel.
Analog cursor rows follow the same rule: a defined signal without a valid
sample shows `--`, and its two-cursor difference also shows `--` when either
endpoint is missing.

Producer availability flags now prevent absent gauge and analog-scope values
from appearing as zero. The main status lines show `--` for missing readings;
gauge tooltips identify the channel, source, validity and snapshot tick. The
right-hand throttle drawing also exposes separate
angle, cable, candidate stem and idle-contact tooltips over their own regions.
These reuse the TBI channel profiles and are drawn after the right-hand
gauges so their source text stays visible across adjacent cells. In a
running live session, the header and tooltips show `STALE` when the snapshot
tick has not advanced for 1.5 seconds of wall time. Pause, finished runs and
fixed captures do not trigger that warning. The ECU inspector title carries
the same warning when debug replaces the normal status line. Debug rows and other secondary
readouts still need the same validity contract before UI-02 is complete. The
debug pedal/load/film/vapor row now uses the snapshot's throttle, crank and
intake availability flags and shows `--` for missing or nonfinite readings.
The debug header also withholds the injector and burn counters when their
producer is unavailable, and its phase field shows `--` when crank phase is
unavailable or nonfinite. Its event-loss count comes from the live
`SimSession` event buffer; a standalone fixed capture has no corresponding
session counter and shows `--` instead of a fabricated zero.
