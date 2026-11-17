#include "engine/ThermalState.hpp"

#include <algorithm>
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
        !std::isfinite(parameters.thermostat_open_c) ||
        !std::isfinite(parameters.thermostat_full_open_c) ||
        parameters.thermostat_full_open_c <= parameters.thermostat_open_c ||
        !nonnegative(parameters.radiator_still_w_per_k) ||
        !nonnegative(parameters.radiator_speed_w_per_k_per_kmh) ||
        !nonnegative(parameters.radiator_fan_w_per_k) ||
        !std::isfinite(parameters.fan_on_c) ||
        !std::isfinite(parameters.fan_off_c) ||
        parameters.fan_off_c >= parameters.fan_on_c ||
        !positive(parameters.air_sensor_tau_s) ||
        !positive(parameters.coolant_sensor_tau_s))
        throw std::invalid_argument("invalid thermal parameters");
}

double ThermalState::thermostat_open_fraction() const {
    return std::clamp((coolant_c_ - parameters_.thermostat_open_c) /
                          (parameters_.thermostat_full_open_c -
                           parameters_.thermostat_open_c),
                      0.0, 1.0);
}

void ThermalState::advance_ticks(uint64_t ticks, double air_flow_kg_s,
                                 double coolant_heat_w,
                                 double vehicle_speed_kmh) {
    if (!std::isfinite(air_flow_kg_s) || air_flow_kg_s < 0.0 ||
        !std::isfinite(coolant_heat_w) || coolant_heat_w < 0.0 ||
        !std::isfinite(vehicle_speed_kmh) || vehicle_speed_kmh < 0.0)
        throw std::invalid_argument("invalid thermal input");
    constexpr double ticks_per_second = 990000.0;
    constexpr double air_specific_heat_j_per_kg_k = 1005.0;
    while (ticks > 0) {
        const uint64_t step_ticks = ticks > 990 ? 990 : ticks;
        const double dt_s = static_cast<double>(step_ticks) / ticks_per_second;
        if (coolant_c_ >= parameters_.fan_on_c) fan_on_ = true;
        if (coolant_c_ <= parameters_.fan_off_c) fan_on_ = false;
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
        const double radiator_w_per_k = thermostat_open_fraction() *
            (parameters_.radiator_still_w_per_k +
             parameters_.radiator_speed_w_per_k_per_kmh * vehicle_speed_kmh +
             (fan_on_ ? parameters_.radiator_fan_w_per_k : 0.0));
        const double radiator_heat_w =
            radiator_w_per_k * std::max(0.0, coolant_c_ - ambient_c_);
        coolant_c_ +=
            (coolant_heat_w - coolant_to_wall_w - coolant_to_ambient_w -
             radiator_heat_w) * dt_s /
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
