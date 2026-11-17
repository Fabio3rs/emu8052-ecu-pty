#pragma once

#include <array>
#include <cstdint>

namespace ma17 {

// Copied from the simulation thread after a complete machine-cycle batch.
// Electrical pin meanings remain candidates until board wiring is verified.
struct EmulatorSnapshot {
    long long tick = 0;
    double crank_angle_rad = 0.0;
    double rpm = 0.0;
    double throttle_angle_rad = 0.0;
    double pedal_pull_m = 0.0;
    double applied_load_nm = 0.0;
    double fuel_film_kg = 0.0;
    double fuel_vapor_kg = 0.0;
    double tps_track1_v = 0.0;
    double tps_track2_v = 0.0;
    double lambda = 0.0;
    double lambda_voltage_v = 0.0;
    double coolant_c = 0.0;
    uint16_t pc = 0;
    uint8_t ram47 = 0;
    uint8_t ram27_faults = 0;
    uint8_t ram28_faults = 0;
    bool cc3_high = false;
    bool p50_high = false;
    bool p51_high = false;
    bool lamp_on_candidate = false;
    bool key_on = true;
    unsigned long long injector_pulses = 0;
    unsigned long long burns = 0;
    unsigned long long missed_sparks = 0;
    std::array<unsigned long long, 4> burns_by_cylinder{};
};

using SnapshotCallback = void (*)(const EmulatorSnapshot &, void *);

} // namespace ma17
