#pragma once

#include <SDL3/SDL_pixels.h>

#include <array>
#include <cstddef>

namespace lab::profile {

inline constexpr const char *vehicle = "FIAT TIPO 1.6 i.e. / SEVEL 1581 cm3";
inline constexpr const char *engine = "SOHC 8V / 4 CIL / SPI";
inline constexpr const char *ecu = "BOSCH MONO-MOTRONIC MA1.7";

struct Band {
    double start = 0.0;
    double end = 0.0;
    SDL_Color color{};
};

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
};

inline constexpr Instrument rpm{
    "rpm", "ENGINE SPEED", "RPM", "physical crank model", 0.0, 8000.0,
    1000.0, 200.0,
    {{{400.0, 1000.0, {0, 229, 255, 255}},
      {5600.0, 6000.0, {245, 205, 30, 255}},
      {6000.0, 8000.0, {238, 68, 69, 255}}}},
    3};
inline constexpr Instrument speed{
    "vehicle_speed", "VEHICLE SPEED", "KM/H", "scenario road input",
    0.0, 200.0, 20.0, 10.0};
inline constexpr Instrument battery_supply{
    "battery_supply", "BATTERY SUPPLY", "V", "physical sensor-circuit supply",
    0.0, 16.0, 2.0, 1.0};
inline constexpr Instrument coolant{
    "coolant", "COOLANT", "C", "physical thermal model", 50.0, 130.0,
    40.0, 10.0,
    {{{120.0, 130.0, {238, 68, 69, 255}}}}, 1};
inline constexpr Instrument ect_scope{
    "ect_physical", "ECT PHYSICAL", "C", "physical thermal model coolant",
    -40.0, 130.0, 20.0, 10.0};
inline constexpr Instrument iat_scope{
    "iat_physical", "IAT PHYSICAL", "C", "physical thermal model air sensor",
    -40.0, 130.0, 20.0, 10.0};
inline constexpr Instrument thermostat{
    "thermostat", "THERMOSTAT", "%", "physical thermal model", 0.0,
    100.0, 20.0, 10.0};
inline constexpr Instrument load{
    "applied_load", "APPLIED LOAD", "Nm", "scenario resisting load",
    0.0, 60.0, 20.0, 5.0};
inline constexpr Instrument clutch{
    "clutch_pressure", "CLUTCH", "%", "no SEVEL clutch state published",
    0.0, 100.0, 50.0, 10.0, {}, 0, true};
inline constexpr Instrument lambda{
    "lambda", "LAMBDA", "1", "physical exhaust model", 0.5, 1.5,
    0.25, 0.1};
inline constexpr Instrument oxygen_voltage{
    "oxygen_voltage", "SONDA V", "V", "exhaust sensor model", 0.0,
    1.0, 0.2, 0.1};
inline constexpr Instrument tps_track1{
    "tps_track1", "TPS1 MODEL", "V", "TPS circuit model before ADC override",
    0.0, 5.0, 1.0, 0.5};
inline constexpr Instrument tps_track2{
    "tps_track2", "TPS2 MODEL", "V", "TPS circuit model before ADC override",
    0.0, 5.0, 1.0, 0.5};
inline constexpr Instrument adc0_tps2_pin{
    "adc0_tps2_pin", "ADC0 TPS2 LAST", "V",
    "last completed ADC0 conversion at the driven pin", 0.0, 5.0,
    1.0, 0.5};
inline constexpr Instrument adc6_tps1_pin{
    "adc6_tps1_pin", "ADC6 TPS1 LAST", "V",
    "last completed ADC6 conversion at the driven pin", 0.0, 5.0,
    1.0, 0.5};
inline constexpr Instrument adc1_battery_pin{
    "adc1_battery_pin", "ADC1 BAT DIV", "V",
    "last ADC1 conversion after the modeled battery divider", 0.0, 5.0,
    1.0, 0.5};
inline constexpr Instrument adc5_lambda_pin{
    "adc5_lambda_pin", "ADC5 LAMBDA", "V",
    "last ADC5 conversion after modeled lambda conditioning", 0.0, 5.0,
    1.0, 0.5};
inline constexpr Instrument adc2_iat_pin{
    "adc2_iat_pin", "ADC2 IAT NTC", "V",
    "last ADC2 conversion at the modeled IAT NTC divider", 0.0, 5.0,
    1.0, 0.5};
inline constexpr Instrument adc3_ect_pin{
    "adc3_ect_pin", "ADC3 ECT NTC", "V",
    "last ADC3 conversion at the modeled ECT NTC divider", 0.0, 5.0,
    1.0, 0.5};
inline constexpr Instrument throttle_angle{
    "throttle_angle", "ANGLE", "deg", "physical throttle model", 0.0,
    90.0, 10.0, 5.0};
inline constexpr Instrument cable_pull{
    "cable_pull", "CABLE", "mm", "physical throttle cable position", 0.0,
    25.0, 5.0, 1.0};
inline constexpr Instrument idle_stem{
    "idle_stem", "HASTE", "mm", "candidate idle-actuator bridge", -10.0,
    30.0, 10.0, 2.0};
inline constexpr Instrument idle_contact{
    "idle_contact", "IDLE SW", "state", "physical throttle contact", 0.0,
    1.0, 1.0, 1.0};
inline constexpr Instrument manifold_pressure{
    "manifold_pressure", "MANIFOLD PRESSURE", "kPa", "intake model",
    0.0, 110.0, 20.0, 5.0};
inline constexpr Instrument air_flow{
    "air_flow", "AIR FLOW", "g/s", "intake model at TBI inlet",
    0.0, 100.0, 20.0, 5.0};
inline constexpr Instrument injected_total{
    "injected_fuel_total", "INJECTED TOTAL", "mg or g",
    "intake model integrated injected mass", 0.0, 0.0, 0.0, 0.0};
inline constexpr Instrument fuel_film{
    "fuel_film", "FUEL FILM", "mg", "intake manifold model", 0.0,
    1000.0, 200.0, 50.0};
inline constexpr Instrument fuel_vapor{
    "fuel_vapor", "FUEL VAPOR", "mg", "intake manifold model", 0.0,
    250.0, 50.0, 10.0};
inline constexpr Instrument injector_pulses{
    "injector_pulses", "INJECTOR PULSES", "count",
    "injector stage published pulse count", 0.0, 0.0, 0.0, 0.0};
inline constexpr Instrument volumetric_efficiency{
    "volumetric_efficiency", "VOLUMETRIC EFF.", "%", "unavailable",
    0.0, 120.0, 20.0, 5.0, {}, 0, true};

} // namespace lab::profile
