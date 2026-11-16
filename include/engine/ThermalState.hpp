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
    double air_sensor_tau_s = 0.3;
    double coolant_sensor_tau_s = 1.0;
};

class ThermalState {
  public:
    ThermalState(double ambient_c = 20.0, double initial_coolant_c = 20.0,
                 ThermalParameters parameters = {});

    void advance_ticks(uint64_t ticks, double air_flow_kg_s = 0.0,
                       double coolant_heat_w = 0.0);

    double ambient_c() const { return ambient_c_; }
    double air_c() const { return air_c_; }
    double wall_c() const { return wall_c_; }
    double coolant_c() const { return coolant_c_; }
    double air_sensor_c() const { return air_sensor_c_; }
    double coolant_sensor_c() const { return coolant_sensor_c_; }

  private:
    ThermalParameters parameters_;
    double ambient_c_;
    double air_c_;
    double wall_c_;
    double coolant_c_;
    double air_sensor_c_;
    double coolant_sensor_c_;
};

} // namespace engine
