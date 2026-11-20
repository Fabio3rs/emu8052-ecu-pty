#pragma once

#include <SDL3/SDL_pixels.h>
#include "lab/LabTheme.hpp"

#include <array>
#include <cstddef>
#include <cstring>

namespace lab::profile {

inline constexpr const char *vehicle = "FIAT TIPO 1.6 i.e. / SEVEL 1581 cm3";
inline constexpr const char *engine = "SOHC 8V / 4 CIL / SPI";
inline constexpr const char *ecu = "BOSCH MONO-MOTRONIC MA1.7";

struct Band {
    double start = 0.0;
    double end = 0.0;
    SDL_Color color{};
    // OES RightGaugeCluster: three-pixel ring, six-pixel outer offset.
    float width = 3.0f;
    float radial_offset = 6.0f;
    float shorten_start = 0.0f;
    float shorten_end = 0.0f;
    // G3: a band that is a target mark carries its caption (e.g. "ALVO").
    const char *label = nullptr;
};

inline constexpr float band_shorten_angle = 0.017453292519943295f;

struct Instrument {
    const char *id;
    const char *title;
    const char *unit;
    const char *source;
    double minimum;
    double maximum;
    double major_step;
    double minor_step;
    std::array<Band, 3> bands{};
    std::size_t band_count = 0;
    bool undefined = false;
    // Scale numerals every `label_step` (instrument units), printed as
    // value / label_divisor. label_step == 0 draws no numerals.
    double label_step = 0.0;
    double label_divisor = 1.0;
};

// L4: titles that can be too wide for a small dial have a short form, chosen
// by measurement at draw time; a title is never ellipsized when one exists.
struct ShortLabel {
    const char *id;
    const char *label;
};
inline constexpr std::array<ShortLabel, 5> short_labels{{
    {"manifold_pressure", "MAP kPa"},
    {"oxygen_voltage", "O2 ECU"},
    {"lambda", "LAM PLT"},
    {"volumetric_efficiency", "VE AMB"},
    {"clutch_pressure", "CLTCH"},
}};

inline const char *short_label_for(const char *id) {
    for (const auto &entry : short_labels)
        if (std::strcmp(entry.id, id) == 0)
            return entry.label;
    return nullptr;
}

constexpr Instrument with_labels(Instrument spec, double step, double divisor) {
    spec.label_step = step;
    spec.label_divisor = divisor;
    return spec;
}

inline constexpr Instrument rpm = with_labels(
    Instrument{"rpm",
               "RPM",
               "RPM",
               "physical crank model; ECU P1.1 pulse candidate in tooltip",
               0.0,
               8000.0,
               1000.0,
               100.0,
               {{{850.0, 900.0, {0, 229, 255, 255}, 3.0f, 6.0f, 0.0f, 0.0f,
                  "ALVO"},
                 {5600.0,
                  6000.0,
                  {245, 205, 30, 255},
                  3.0f,
                  6.0f,
                  -band_shorten_angle,
                  band_shorten_angle},
                 {6000.0,
                  8000.0,
                  kCritical,
                  3.0f,
                  6.0f,
                  band_shorten_angle,
                  -band_shorten_angle}}},
               3},
    1000.0, 100.0); // numerals 0..80 (x100 RPM)
// docs/SEVEL_TIPO_16_SPECS.md: 0-8000 RPM, secondary marks every 100 RPM, idle
// zone 850-900 RPM, yellow 5600-6000 and red 6000-8000.
static_assert(rpm.minimum == 0.0 && rpm.maximum == 8000.0);
static_assert(rpm.major_step == 1000.0 && rpm.minor_step == 100.0);
static_assert(rpm.band_count == 3);
static_assert(rpm.bands[0].start == 850.0 && rpm.bands[0].end == 900.0);
static_assert(rpm.bands[1].start == 5600.0 && rpm.bands[1].end == 6000.0);
static_assert(rpm.bands[2].start == 6000.0 && rpm.bands[2].end == 8000.0);

inline constexpr Instrument speed =
    with_labels(Instrument{"vehicle_speed", "VEHICLE SPEED", "KM/H",
                           "scenario road input", 0.0, 200.0, 20.0, 10.0},
                20.0, 1.0); // numerals 0..200 every 20
inline constexpr Instrument battery_supply{"battery_supply",
                                           "BATTERY SUPPLY",
                                           "V",
                                           "physical sensor-circuit supply",
                                           0.0,
                                           16.0,
                                           2.0,
                                           1.0};
inline constexpr Instrument coolant =
    with_labels(Instrument{"coolant",
                           "COOLANT",
                           "C",
                           "physical thermal model",
                           50.0,
                           130.0,
                           40.0,
                           10.0,
                           {{{120.0, 130.0, kCritical}}},
                           1},
                40.0, 1.0); // 50/90/130
// Scale numerals: tachometer 0..80 (x100), speedometer 0..200 every 20,
// coolant 50/90/130.
static_assert(rpm.label_step == 1000.0 && rpm.label_divisor == 100.0);
static_assert(speed.label_step == 20.0 && speed.maximum == 200.0);
static_assert(coolant.label_step == 40.0 && coolant.minimum == 50.0 &&
              coolant.maximum == 130.0);

inline constexpr Instrument ect_scope{
    "ect_physical", "ECT PHYSICAL", "C",  "physical thermal model coolant",
    -40.0,          130.0,          20.0, 10.0};
inline constexpr Instrument iat_scope{
    "iat_physical", "IAT PHYSICAL", "C",  "physical thermal model air sensor",
    -40.0,          130.0,          20.0, 10.0};
inline constexpr Instrument thermostat{
    "thermostat", "THERMOSTAT", "%",  "physical thermal model",
    0.0,          100.0,        20.0, 10.0};
inline constexpr Instrument load{
    "applied_load", "APPLIED LOAD", "Nm", "scenario resisting load", 0.0,
    60.0,           20.0,           5.0};
inline constexpr Instrument clutch{"clutch_pressure",
                                   "CLUTCH",
                                   "%",
                                   "drivetrain pressure: 0=open, 100=engaged",
                                   0.0,
                                   100.0,
                                   50.0,
                                   10.0};
inline constexpr Instrument lambda{
    "lambda", "LAMBDA PLANT", "1", "physical exhaust model (plant truth)", 0.5,
    1.5,      0.25,     0.05}; // 0.05 divides both the 0.25 major step and
                               // the 1.0 range
inline constexpr Instrument oxygen_voltage{"oxygen_voltage",
                                           "O2 SENSOR ECU",
                                           "V",
                                           "exhaust sensor model",
                                           0.0,
                                           1.0,
                                           0.2,
                                           0.1};
inline constexpr Instrument tps_track1{
    "tps_track1", "TPS1 MODEL", "V", "TPS circuit model before ADC override",
    0.0,          5.0,          1.0, 0.5};
inline constexpr Instrument tps_track2{
    "tps_track2", "TPS2 MODEL", "V", "TPS circuit model before ADC override",
    0.0,          5.0,          1.0, 0.5};
inline constexpr Instrument adc0_tps2_pin{
    "adc0_tps2_pin",
    "ADC0 TPS2 LAST",
    "V",
    "last completed ADC0 conversion at the driven pin",
    0.0,
    5.0,
    1.0,
    0.5};
inline constexpr Instrument adc6_tps1_pin{
    "adc6_tps1_pin",
    "ADC6 TPS1 LAST",
    "V",
    "last completed ADC6 conversion at the driven pin",
    0.0,
    5.0,
    1.0,
    0.5};
inline constexpr Instrument adc1_battery_pin{
    "adc1_battery_pin",
    "ADC1 BAT DIV",
    "V",
    "last ADC1 conversion after the modeled battery divider",
    0.0,
    5.0,
    1.0,
    0.5};
inline constexpr Instrument adc5_lambda_pin{
    "adc5_lambda_pin",
    "ADC5 LAMBDA",
    "V",
    "last ADC5 conversion after modeled lambda conditioning",
    0.0,
    5.0,
    1.0,
    0.5};
inline constexpr Instrument adc2_iat_pin{
    "adc2_iat_pin",
    "ADC2 IAT NTC",
    "V",
    "last ADC2 conversion at the modeled IAT NTC divider",
    0.0,
    5.0,
    1.0,
    0.5};
inline constexpr Instrument adc3_ect_pin{
    "adc3_ect_pin",
    "ADC3 ECT NTC",
    "V",
    "last ADC3 conversion at the modeled ECT NTC divider",
    0.0,
    5.0,
    1.0,
    0.5};
inline constexpr Instrument throttle_angle{"throttle_angle",
                                           "ANGLE",
                                           "deg",
                                           "physical throttle model",
                                           0.0,
                                           90.0,
                                           10.0,
                                           5.0};
inline constexpr Instrument cable_pull{
    "cable_pull", "CABLE", "mm", "physical throttle cable position",
    0.0,          25.0,    5.0,  1.0};
inline constexpr Instrument idle_stem{
    "idle_stem", "IDLE STEM", "mm", "candidate idle-actuator bridge",
    -10.0,       30.0,        10.0, 2.0};
inline constexpr Instrument idle_contact{"idle_contact",
                                         "IDLE SW",
                                         "state",
                                         "physical throttle contact",
                                         0.0,
                                         1.0,
                                         1.0,
                                         1.0};
inline constexpr Instrument manifold_pressure{"manifold_pressure",
                                              "MANIFOLD PRESSURE",
                                              "kPa",
                                              "intake model",
                                              0.0,
                                              110.0,
                                              20.0,
                                              5.0};
inline constexpr Instrument air_flow{
    "air_flow", "AIR FLOW", "g/s", "intake model at TBI inlet",
    0.0,        100.0,      20.0,  5.0};
inline constexpr Instrument injected_total{
    "injected_fuel_total",
    "INJECTED TOTAL",
    "mg or g",
    "intake model integrated injected mass",
    0.0,
    0.0,
    0.0,
    0.0};
inline constexpr Instrument fuel_film{
    "fuel_film", "FUEL FILM", "mg",  "intake manifold model",
    0.0,         1000.0,      200.0, 50.0};
inline constexpr Instrument fuel_vapor{
    "fuel_vapor", "FUEL VAPOR", "mg", "intake manifold model",
    0.0,          250.0,        50.0, 10.0};
inline constexpr Instrument injector_pulses{
    "injector_pulses",
    "INJECTOR PULSES",
    "count",
    "injector stage published pulse count",
    0.0,
    0.0,
    0.0,
    0.0};
// Ambient-referenced VE of the calibrated plant (GOAL_SEVEL_FISICA, F-16/F-48):
// sum(air to cylinders) / (rho_ref * Vd * cycles) over a 20-cycle window.
inline constexpr Instrument volumetric_efficiency{
    "volumetric_efficiency",
    "VE REF. AMBIENTE",
    "%",
    "plant window ve_ambient: 20 cycles, rho_ref 100 kPa / 20 C",
    0.0,
    120.0,
    20.0,
    5.0,
    {},
    0,
    false};

// D7: the ignition column as a hover target; its tooltip carries the spark
// efficiency and residual fraction of the last ignition event.
inline constexpr Instrument ignition_spark{
    "ignition_spark",
    "IGNITION",
    "deg",
    "P5.0/P5.1 events; MBT + efficiency: plant model",
    0.0,
    0.0,
    0.0,
    0.0};

// Every instrument, for audits (tests/lab_profile_audit_test.cpp).
inline constexpr std::array<const Instrument *, 31> all_instruments{
    {&rpm,
     &speed,
     &battery_supply,
     &coolant,
     &ect_scope,
     &iat_scope,
     &thermostat,
     &load,
     &clutch,
     &lambda,
     &oxygen_voltage,
     &tps_track1,
     &tps_track2,
     &adc0_tps2_pin,
     &adc6_tps1_pin,
     &adc1_battery_pin,
     &adc5_lambda_pin,
     &adc2_iat_pin,
     &adc3_ect_pin,
     &throttle_angle,
     &cable_pull,
     &idle_stem,
     &idle_contact,
     &manifold_pressure,
     &air_flow,
     &injected_total,
     &fuel_film,
     &fuel_vapor,
     &injector_pulses,
     &volumetric_efficiency,
     &ignition_spark}};

} // namespace lab::profile
