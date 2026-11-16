#include "ecu_hw/Ma17TpsCircuit.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace ecu_hw {

Ma17TpsCircuit::Ma17TpsCircuit(TpsCircuitParameters parameters)
    : parameters_(parameters) {
    if (!std::isfinite(parameters.reference_v) ||
        parameters.reference_v <= 0.0 ||
        !std::isfinite(parameters.rest_angle_rad) ||
        parameters.rest_angle_rad < 0.0 ||
        !std::isfinite(parameters.track1_rest_v) ||
        parameters.track1_rest_v < 0.0 ||
        !std::isfinite(parameters.track1_slope_v_per_rad) ||
        parameters.track1_slope_v_per_rad < 0.0 ||
        !std::isfinite(parameters.track1_end_rad) ||
        parameters.track1_end_rad <= parameters.rest_angle_rad ||
        !std::isfinite(parameters.track2_rest_v) ||
        parameters.track2_rest_v < 0.0 ||
        !std::isfinite(parameters.track2_low_slope_v_per_rad) ||
        parameters.track2_low_slope_v_per_rad < 0.0 ||
        !std::isfinite(parameters.track2_transition_rad) ||
        parameters.track2_transition_rad <= parameters.rest_angle_rad ||
        !std::isfinite(parameters.track2_high_slope_v_per_rad) ||
        parameters.track2_high_slope_v_per_rad < 0.0 ||
        !std::isfinite(parameters.track2_overlap_end_rad) ||
        parameters.track2_overlap_end_rad <= parameters.track2_transition_rad ||
        !std::isfinite(parameters.track2_wide_slope_v_per_rad) ||
        parameters.track2_wide_slope_v_per_rad < 0.0)
        throw std::invalid_argument("invalid TPS circuit parameters");
}

double Ma17TpsCircuit::track1_voltage(double angle_rad) const {
    if (!std::isfinite(angle_rad) || angle_rad < 0.0)
        throw std::invalid_argument("invalid throttle angle");
    const double active_angle = std::min(angle_rad, parameters_.track1_end_rad);
    return std::clamp(parameters_.track1_rest_v +
                          (active_angle - parameters_.rest_angle_rad) *
                              parameters_.track1_slope_v_per_rad,
                      0.0, parameters_.reference_v);
}

double Ma17TpsCircuit::track2_voltage(double angle_rad) const {
    if (!std::isfinite(angle_rad) || angle_rad < 0.0)
        throw std::invalid_argument("invalid throttle angle");
    const double low_span = std::clamp(
        angle_rad - parameters_.rest_angle_rad, -parameters_.rest_angle_rad,
        parameters_.track2_transition_rad - parameters_.rest_angle_rad);
    const double high_span =
        std::clamp(angle_rad - parameters_.track2_transition_rad, 0.0,
                   parameters_.track2_overlap_end_rad -
                       parameters_.track2_transition_rad);
    const double wide_span =
        std::max(0.0, angle_rad - parameters_.track2_overlap_end_rad);
    return std::clamp(parameters_.track2_rest_v +
                          low_span * parameters_.track2_low_slope_v_per_rad +
                          high_span * parameters_.track2_high_slope_v_per_rad +
                          wide_span * parameters_.track2_wide_slope_v_per_rad,
                      0.0, parameters_.reference_v);
}

} // namespace ecu_hw
