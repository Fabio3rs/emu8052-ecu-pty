#pragma once

#include <array>
#include <cmath>
#include <stdexcept>

namespace lab {

// Fiat Tipo B.500.837 specifies the stroke; rod length is a drawing estimate.
struct SevelVisualGeometry {
    static constexpr double crank_radius_m = 0.0337;
    double visual_estimate_rod_length_m = 0.14;
};

struct CylinderPose {
    double crank_pin_x_m;
    double crank_pin_y_m;
    double piston_pin_y_m;
    double rod_angle_rad;
};

inline CylinderPose cylinder_pose(double crank_angle_rad, int cylinder,
                                  SevelVisualGeometry geometry = {}) {
    if (!std::isfinite(crank_angle_rad) || cylinder < 1 || cylinder > 4 ||
        !std::isfinite(geometry.visual_estimate_rod_length_m) ||
        geometry.visual_estimate_rod_length_m <=
            SevelVisualGeometry::crank_radius_m) {
        throw std::invalid_argument("invalid SEVEL visual geometry");
    }

    constexpr double pi = 3.14159265358979323846;
    const double phase = (cylinder == 2 || cylinder == 3) ? pi : 0.0;
    const double theta = std::remainder(crank_angle_rad + phase, 2.0 * pi);
    const double radius = SevelVisualGeometry::crank_radius_m;
    const double pin_x = radius * std::sin(theta);
    const double pin_y = radius * std::cos(theta);
    const double rod_y = std::sqrt(geometry.visual_estimate_rod_length_m *
                                       geometry.visual_estimate_rod_length_m -
                                   pin_x * pin_x);
    return {pin_x, pin_y, pin_y + rod_y, std::atan2(-pin_x, rod_y)};
}

inline std::array<CylinderPose, 4>
sevel_cylinder_poses(double crank_angle_rad,
                     SevelVisualGeometry geometry = {}) {
    return {cylinder_pose(crank_angle_rad, 1, geometry),
            cylinder_pose(crank_angle_rad, 2, geometry),
            cylinder_pose(crank_angle_rad, 3, geometry),
            cylinder_pose(crank_angle_rad, 4, geometry)};
}

} // namespace lab
