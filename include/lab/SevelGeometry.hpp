#pragma once

#include <array>
#include <cmath>
#include <stdexcept>

namespace lab {

// Fiat Tipo B.500.837 specifies the stroke; rod length is a drawing estimate.
struct SevelVisualGeometry {
    static constexpr double crank_radius_m = 0.0337;
    // 127 mm centre to centre: the same literature estimate the plant model
    // uses (SEVEL_TIPO_16_SPECS.md), so the scene and the physics agree (M4).
    double visual_estimate_rod_length_m = 0.127;
};

// Fiat Tipo 1.6 (manual p.5/p.7): 86.4 x 67.4 mm, compression ratio 9.2:1.
inline constexpr double kSevelBoreM = 0.0864;
inline constexpr double kSevelStrokeM = 0.0674;
inline constexpr double kSevelCompressionRatio = 9.2;
// Distance from the gudgeon pin axis to the piston crown; drawing estimate,
// to be confirmed against PhotosECU/desenhos_pistoes.png.
inline constexpr double kSevelPistonCrownAbovePinM = 0.023;

// M6: the manual shows three piston rings (two compression, one oil), measured
// as depth below the crown. Drawing estimate; all three lie in the crown land
// region above the gudgeon pin.
inline constexpr std::array<double, 3> kSevelPistonRingDepthsM{0.0025, 0.0055,
                                                               0.0085};

// Skirt length below the gudgeon pin axis (drawing estimate, same source as
// the crown height above).
inline constexpr double kSevelPistonSkirtBelowPinM = 0.040;
inline constexpr double kSevelLinerSkirtMarginM = 0.003;

// Height of the combustion chamber at TDC implied by the compression ratio:
// Vc = Vswept / (CR - 1) and Vswept = A * stroke, so h = stroke / (CR - 1)
// (8.22 mm, Vc = 48.2 cm3).
constexpr double sevel_chamber_height_m() {
    return kSevelStrokeM / (kSevelCompressionRatio - 1.0);
}

// Head face height above the crank axis, derived rather than chosen: the
// piston crown at TDC sits exactly one chamber height below it (M3).
inline double sevel_head_face_y_m(const SevelVisualGeometry &geometry) {
    return SevelVisualGeometry::crank_radius_m +
           geometry.visual_estimate_rod_length_m + kSevelPistonCrownAbovePinM +
           sevel_chamber_height_m();
}

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

// Bottom of the cylinder liner: 3 mm below the skirt at BDC, so the liner
// stops above the crank circle instead of crossing the crankshaft (M1).
inline double sevel_liner_bottom_y_m(const SevelVisualGeometry &geometry) {
    return geometry.visual_estimate_rod_length_m -
           SevelVisualGeometry::crank_radius_m - kSevelPistonSkirtBelowPinM -
           kSevelLinerSkirtMarginM;
}

} // namespace lab
