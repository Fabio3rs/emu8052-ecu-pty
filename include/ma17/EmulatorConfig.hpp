#pragma once

#include <optional>

namespace ma17 {

struct EmulatorConfig {
    const char *rom_path;
    int crank_rpm = 1000;
    bool crank_immediate = false;
    bool physical_crank = false;
    bool drivetrain = false;
    int transmission_gear = 0;
    int clutch_percent = 0;
    int vehicle_mass_kg = 1000; // Provisional, configurable; not a manual value.
    int clutch_max_nm = 200; // Provisional capacity.
    bool physical_pty_realtime = false;
    long long starter_ticks = 0;
    long long stop_ticks = 0;
    long long crank_sensor_open_tick = 0;
    long long crank_sensor_restore_tick = 0;
    long long pedal_step_tick = 0;
    long long pedal_release_tick = 0;
    long long pedal_rise_ticks = 0;
    double pedal_pull_m = 0.0;
    double dyno_point_rpm = 0.0; // --dyno-point: ROM bench at this rpm (0 = off)
    double dyno_cycles = 40.0;   // --dyno-cycles: measurement window
    bool tps_bench_profile = false;
    bool idle_bridge_p15_p16 = false;
    bool idle_bridge_reverse = false;
    bool idle_contact_p43 = false;
    bool idle_contact_p46 = false;
    bool idle_contact_p46_high_closed = false;
    bool pump_relay_p34 = false;
    long long idle_contact_open_tick = 0;
    long long idle_contact_closed_tick = 0;
    long long idle_contact_restore_tick = 0;
    long long idle_motor_disconnect_tick = 0;
    long long idle_motor_reconnect_tick = 0;
    int idle_motor_speed_mm_s = -1;
    int idle_min_stop_mrad = -1;
    int throttle_leak_mm2 = -1;
    long long load_step_tick = 0;
    double load_torque_nm = 0.0;
    long long tps1_high_tick = 0;
    long long tps1_restore_tick = 0;
    long long tps2_high_tick = 0;
    long long tps2_restore_tick = 0;
    long long tps_open_tick = 0;
    long long tps_restore_tick = 0;
    int tps_open_mv = -1; // Explicit test voltage; board bias is unknown.
    double initial_coolant_c = 20.0;
    double vehicle_speed_kmh = 0.0;
    double battery_v = 12.5;
    int ethanol_percent = 0; // Explicit E0 baseline; E22/E25 are candidate fuel cases.
    long long ect_open_tick = 0;
    long long ect_restore_tick = 0;
    // Board source unknown; -1 retains the explicit 1.760 V scenario estimate.
    int adc4_mv = -1;
    double adc7_boundary_v = -1.0;
    double adc7_step_v = -1.0;
    long long adc7_step_tick = 0;
    double lambda_stuck_v = -1.0;
    long long lambda_stuck_tick = 0;
    long long lambda_restore_tick = 0;
    int lambda_adc_gain = 1;
    int lambda_switch_slope = 25; // Experimental exhaust probe calibration.
    long long injector_disconnect_tick = 0;
    long long injector_reconnect_tick = 0;
    long long coil_disconnect_tick = 0;
    long long coil_reconnect_tick = 0;
    int coil_channel = -1;
    int tdc_reference_deg = -1;
    bool swap_ignition_coils = false;
    // Calibrated plant: eta_v(N,p_m) map + physical indicated efficiency
    // (GOAL_SEVEL_FISICA fase 4). --legacy-plant restores the old constant-VE plant.
    bool physical_plant = true;
    // F-45 accessory torque (alternator + water pump) on the crank. Off by default:
    // scenarios with an explicit external load (24 N.m) already stand in for it.
    bool accessory_load = false;
    // Physical plant uses the Heywood area + compressible flow throttle (F-10/F-11);
    // --legacy-throttle keeps the old Bernoulli A_leak + A_max sin^2 model.
    bool legacy_throttle = false;
    int fluid_step_ticks = 990;
};

std::optional<EmulatorConfig> parse_emulator_config(int argc, char **argv);

} // namespace ma17
