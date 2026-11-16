#include "engine/ThrottleAssembly.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace engine {

ThrottleAssembly::ThrottleAssembly(ThrottleParameters parameters)
    : parameters_(parameters) {
    if (!std::isfinite(parameters.cable_radius_m) ||
        parameters.cable_radius_m <= 0.0 ||
        !std::isfinite(parameters.cable_free_play_m) ||
        parameters.cable_free_play_m < 0.0 ||
        !std::isfinite(parameters.maximum_angle_rad) ||
        parameters.maximum_angle_rad <= stop_angle_rad_ ||
        !std::isfinite(parameters.contact_on_gap_rad) ||
        parameters.contact_on_gap_rad < 0.0 ||
        !std::isfinite(parameters.contact_off_gap_rad) ||
        parameters.contact_off_gap_rad < parameters.contact_on_gap_rad)
        throw std::invalid_argument("invalid throttle parameters");
}

void ThrottleAssembly::set_cable_pull_m(double pull_m) {
    if (!std::isfinite(pull_m) || pull_m < 0.0)
        throw std::invalid_argument("invalid cable pull");
    cable_pull_m_ = pull_m;
    update_geometry();
}

void ThrottleAssembly::set_stop_angle_rad(double angle_rad) {
    if (!std::isfinite(angle_rad) || angle_rad < 0.0 ||
        angle_rad > parameters_.maximum_angle_rad)
        throw std::invalid_argument("invalid throttle stop");
    stop_angle_rad_ = angle_rad;
    update_geometry();
}

void ThrottleAssembly::update_geometry() {
    cable_angle_rad_ =
        std::clamp((cable_pull_m_ - parameters_.cable_free_play_m) /
                       parameters_.cable_radius_m,
                   0.0, parameters_.maximum_angle_rad);
    angle_rad_ = std::max(cable_angle_rad_, stop_angle_rad_);
    const double gap_rad = cable_angle_rad_ - stop_angle_rad_;
    if (contact_closed_ && gap_rad > parameters_.contact_off_gap_rad)
        contact_closed_ = false;
    else if (!contact_closed_ && gap_rad <= parameters_.contact_on_gap_rad)
        contact_closed_ = true;
}

} // namespace engine
