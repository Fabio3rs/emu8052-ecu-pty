#include "engine/ThermalState.hpp"

#include <cmath>
#include <stdexcept>

namespace engine {

ThermalState::ThermalState(double ambient_c, double initial_coolant_c,
                           ThermalParameters parameters)
    : parameters_(parameters), ambient_c_(ambient_c), air_c_(ambient_c),
      wall_c_(initial_coolant_c), coolant_c_(initial_coolant_c),
      air_sensor_c_(ambient_c), coolant_sensor_c_(initial_coolant_c) {
    const auto positive = [](double value) {
        return std::isfinite(value) && value > 0.0;
    };
    const auto nonnegative = [](double value) {
        return std::isfinite(value) && value >= 0.0;
    };
    if (!std::isfinite(ambient_c) || !std::isfinite(initial_coolant_c) ||
        ambient_c < -50.0 || ambient_c > 150.0 || initial_coolant_c < -50.0 ||
        initial_coolant_c > 150.0 ||
        !positive(parameters.air_capacity_j_per_k) ||
        !positive(parameters.wall_capacity_j_per_k) ||
        !positive(parameters.coolant_capacity_j_per_k) ||
        !nonnegative(parameters.coolant_wall_w_per_k) ||
        !nonnegative(parameters.wall_air_w_per_k) ||
        !nonnegative(parameters.air_ambient_w_per_k) ||
        !nonnegative(parameters.coolant_ambient_w_per_k) ||
        !positive(parameters.air_sensor_tau_s) ||
        !positive(parameters.coolant_sensor_tau_s))
        throw std::invalid_argument("invalid thermal parameters");
}

void ThermalState::advance_ticks(uint64_t ticks, double air_flow_kg_s,
                                 double coolant_heat_w) {
    if (!std::isfinite(air_flow_kg_s) || air_flow_kg_s < 0.0 ||
        !std::isfinite(coolant_heat_w) || coolant_heat_w < 0.0)
        throw std::invalid_argument("invalid thermal input");
    constexpr double ticks_per_second = 990000.0;
    constexpr double air_specific_heat_j_per_kg_k = 1005.0;
    while (ticks > 0) {
        const uint64_t step_ticks = ticks > 990 ? 990 : ticks;
        const double dt_s = static_cast<double>(step_ticks) / ticks_per_second;
        const double coolant_to_wall_w =
            parameters_.coolant_wall_w_per_k * (coolant_c_ - wall_c_);
        const double wall_to_air_w =
            parameters_.wall_air_w_per_k * (wall_c_ - air_c_);
        const double ambient_to_air_w =
            (parameters_.air_ambient_w_per_k +
             air_flow_kg_s * air_specific_heat_j_per_kg_k) *
            (ambient_c_ - air_c_);
        const double coolant_to_ambient_w =
            parameters_.coolant_ambient_w_per_k * (coolant_c_ - ambient_c_);
        coolant_c_ +=
            (coolant_heat_w - coolant_to_wall_w - coolant_to_ambient_w) * dt_s /
            parameters_.coolant_capacity_j_per_k;
        wall_c_ += (coolant_to_wall_w - wall_to_air_w) * dt_s /
                   parameters_.wall_capacity_j_per_k;
        air_c_ += (wall_to_air_w + ambient_to_air_w) * dt_s /
                  parameters_.air_capacity_j_per_k;
        air_sensor_c_ += (air_c_ - air_sensor_c_) *
                         (1.0 - std::exp(-dt_s / parameters_.air_sensor_tau_s));
        coolant_sensor_c_ +=
            (coolant_c_ - coolant_sensor_c_) *
            (1.0 - std::exp(-dt_s / parameters_.coolant_sensor_tau_s));
        ticks -= step_ticks;
    }
}

} // namespace engine
