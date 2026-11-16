#pragma once

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace engine {

struct IdleActuatorParameters {
    double base_stop_rad = 0.04;
    double initial_stem_m = 0.00298131700797732;
    // MA1.7 service literature reports about 18 degrees at full travel.
    // Stem travel and lever ratio remain engineering estimates.
    double maximum_stop_rad = 0.3141592653589793;
    double lever_rad_per_m = 10.0;
    double maximum_speed_m_s = 0.008;
    double battery_v = 12.5;
    double response_tau_s = 0.04;
    double brake_tau_s = 0.005;
    double coast_tau_s = 0.10;
};

// Effective worm-gear stem: position is retained when power is removed.
class IdleActuator {
  public:
    explicit IdleActuator(IdleActuatorParameters parameters = {})
        : parameters_(parameters), stem_m_(parameters.initial_stem_m) {
        if (!std::isfinite(parameters.base_stop_rad) ||
            !(parameters.initial_stem_m >= 0.0) ||
            !std::isfinite(parameters.maximum_stop_rad) ||
            !(parameters.lever_rad_per_m > 0.0) ||
            !(parameters.maximum_stop_rad >
              parameters.base_stop_rad +
                  parameters.lever_rad_per_m * parameters.initial_stem_m) ||
            !(parameters.maximum_speed_m_s > 0.0) ||
            !(parameters.battery_v > 0.0) ||
            !(parameters.response_tau_s > 0.0) ||
            !(parameters.brake_tau_s > 0.0) || !(parameters.coast_tau_s > 0.0))
            throw std::invalid_argument("invalid idle actuator parameters");
    }

    void step(double voltage_v, bool brake, double dt_s) {
        if (!std::isfinite(voltage_v) ||
            std::abs(voltage_v) > parameters_.battery_v ||
            !std::isfinite(dt_s) || dt_s <= 0.0)
            throw std::invalid_argument("invalid idle actuator drive");
        const double target_speed =
            parameters_.maximum_speed_m_s * voltage_v / parameters_.battery_v;
        const double tau_s = brake              ? parameters_.brake_tau_s
                             : voltage_v == 0.0 ? parameters_.coast_tau_s
                                                : parameters_.response_tau_s;
        speed_m_s_ +=
            (target_speed - speed_m_s_) * (1.0 - std::exp(-dt_s / tau_s));
        const double maximum_stem_m =
            (parameters_.maximum_stop_rad - parameters_.base_stop_rad) /
            parameters_.lever_rad_per_m;
        stem_m_ = std::clamp(stem_m_ + speed_m_s_ * dt_s, 0.0,
                             maximum_stem_m);
        if ((stem_m_ <= 0.0 && speed_m_s_ < 0.0) ||
            (stem_m_ >= maximum_stem_m && speed_m_s_ > 0.0))
            speed_m_s_ = 0.0;
    }

    double stem_m() const { return stem_m_; }
    double stop_angle_rad() const {
        return parameters_.base_stop_rad +
               parameters_.lever_rad_per_m * stem_m_;
    }

  private:
    IdleActuatorParameters parameters_;
    double stem_m_;
    double speed_m_s_ = 0.0;
};

} // namespace engine
