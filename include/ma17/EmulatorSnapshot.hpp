#pragma once

#include "ma17/AdcSimulator.hpp"

#include <array>
#include <cstdint>

namespace ma17 {

// Copied from the simulation thread after a complete machine-cycle batch.
// Electrical pin meanings remain candidates until board wiring is verified.
struct EmulatorSnapshot {
    // Set by the Lab session when the simulation thread stopped on a model
    // exception (e.g. invalid drivetrain input). Physical channels such as
    // the drivetrain are then published as unavailable and the values that
    // remain are the last valid ones, not live data.
    bool simulation_fault = false;
    long long tick = 0;
    double crank_angle_rad = 0.0;
    double tdc_phase_rad = 0.0; // Candidate physical 1/4 firing TDC reference.
    double rpm = 0.0;
    double tachometer_rpm = 0.0; // P1.1 candidate, two pulses/revolution.
    unsigned long long tachometer_pulses = 0;
    bool tachometer_available = false;
    bool crank_available = false;
    double throttle_angle_rad = 0.0;
    double pedal_pull_m = 0.0;
    bool throttle_available = false;
    bool tps_available = false;
    double applied_load_nm = 0.0;
    double manifold_pressure_pa = 0.0;
    double air_in_kg_s = 0.0;
    double injected_fuel_total_kg = 0.0;
    bool intake_available = false;
    double fuel_film_kg = 0.0;
    double fuel_vapor_kg = 0.0;
    double tps_track1_v = 0.0;
    double tps_track2_v = 0.0;
    double lambda = 0.0;
    bool exhaust_sample_available = false;
    double lambda_voltage_v = 0.0;
    double battery_supply_v = 0.0;
    bool battery_supply_available = false;
    // Last completed conversion per channel, including the driven pin voltage.
    // Its tick may precede this snapshot; consumers must show that age.
    std::array<AdcObservation, 8> adc_last_conversion{};
    double coolant_c = 0.0;
    double intake_air_c = 0.0;
    bool thermal_available = false;
    double vehicle_speed_kmh = 0.0;
    bool vehicle_speed_available = false;
    bool drivetrain_available = false;
    int transmission_gear = 0; // -1 reverse, 0 neutral, 1..5 forward.
    double clutch_pressure = 0.0;
    double clutch_crank_torque_nm = 0.0;
    double clutch_heat_j = 0.0;
    double thermostat_open_fraction = 0.0;
    bool radiator_fan_on = false;
    double idle_stem_m = 0.0;
    uint16_t pc = 0;
    uint8_t ram47 = 0;
    uint8_t ram46 =
        0; // ROM nominal idle RPM; 25 RPM/count, distinct from actual.
    std::array<uint8_t, 8> rom_iram_60_67{};
    uint8_t ram27_faults = 0;
    uint8_t ram28_faults = 0;
    std::array<uint8_t, 3> rom_current_fault_banks{};
    std::array<uint8_t, 3> rom_history_fault_banks{};
    bool cc3_high = false;
    bool p50_high = false;
    bool p51_high = false;
    bool lamp_on_candidate = false;
    bool idle_bridge_candidate = false;
    bool idle_motor_connected = true;
    bool idle_contact_closed = false;
    bool p15_high = false;
    bool p16_high = false;
    bool key_on = true;
    unsigned long long injector_pulses = 0;
    bool injector_available = false;
    unsigned long long burns = 0;
    unsigned long long missed_sparks = 0;
    std::array<unsigned long long, 4> burns_by_cylinder{};
};

using SnapshotCallback = void (*)(const EmulatorSnapshot &, void *);

} // namespace ma17
