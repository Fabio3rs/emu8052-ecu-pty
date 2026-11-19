#pragma once

#include <cstdint>

namespace engine {

// Lumped estimates, not measured SEVEL thermal masses or conductances.
struct ThermalParameters {
    double air_capacity_j_per_k = 120.0;
    double wall_capacity_j_per_k = 6000.0;
    double coolant_capacity_j_per_k = 50000.0;
    double coolant_wall_w_per_k = 40.0;
    double wall_air_w_per_k = 12.0;
    double air_ambient_w_per_k = 20.0;
    double coolant_ambient_w_per_k = 5.0;
    // Manual B.500.837 p.17: thermostat starts to open at 85-89 C and is fully open
    // at 96-100 C (centres 87 / 98). Previous code: 87 / 95.
    double thermostat_open_c = 87.0;
    double thermostat_full_open_c = 98.0;
    double radiator_still_w_per_k = 30.0;
    double radiator_speed_w_per_k_per_kmh = 3.0;
    double radiator_fan_w_per_k = 260.0;
    // Manual p.17: fan on at 90-94 C (centre 92), off at 85-89 C. Off is set to 86 C,
    // inside that range and 1 K below the thermostat start, so the hysteresis can
    // complete (the radiator conductance vanishes at 87 C). Previous code: 100 / 95.
    double fan_on_c = 92.0;
    double fan_off_c = 86.0;
    double air_sensor_tau_s = 0.3;
    double coolant_sensor_tau_s = 1.0;
};

class ThermalState {
  public:
    ThermalState(double ambient_c = 20.0, double initial_coolant_c = 20.0,
                 ThermalParameters parameters = {});

    void advance_ticks(uint64_t ticks, double air_flow_kg_s = 0.0,
                       double coolant_heat_w = 0.0,
                       double vehicle_speed_kmh = 0.0);

    double ambient_c() const { return ambient_c_; }
    double air_c() const { return air_c_; }
    double wall_c() const { return wall_c_; }
    double coolant_c() const { return coolant_c_; }
    double air_sensor_c() const { return air_sensor_c_; }
    double coolant_sensor_c() const { return coolant_sensor_c_; }
    double thermostat_open_fraction() const;
    bool fan_on() const { return fan_on_; }

  private:
    ThermalParameters parameters_;
    double ambient_c_;
    double air_c_;
    double wall_c_;
    double coolant_c_;
    double air_sensor_c_;
    double coolant_sensor_c_;
    bool fan_on_ = false;
};

} // namespace engine
