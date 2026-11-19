#pragma once
// F-04..F-09 cylinder geometry and slider-crank kinematics. SI units.
#include "engine/physics/Gas.hpp"

namespace engine::physics {
struct EngineGeometry {
    double bore_m = 0.0864;          // manual B.500.837 p.5,7
    double stroke_m = 0.0674;        // manual B.500.837 p.5,7
    double compression_ratio = 9.2;  // manual B.500.837 p.5
    double rod_length_m = 0.1270;    // estimativa de literatura (128 SOHC ~127 mm); manual nao informa
    double pin_offset_m = 0.0;       // manual p.10 ambiguo (~1 mm); candidato, desligado
    int cylinders = 4;               // manual p.5
};

inline double cylinder_displacement(const EngineGeometry &g) { // F-04
    return pi / 4.0 * g.bore_m * g.bore_m * g.stroke_m;
}
inline double total_displacement(const EngineGeometry &g) {
    return static_cast<double>(g.cylinders) * cylinder_displacement(g);
}
inline double clearance_volume(const EngineGeometry &g) { // F-05
    return cylinder_displacement(g) / (g.compression_ratio - 1.0);
}
inline double mean_piston_speed(const EngineGeometry &g, double rpm) { // F-08
    return 2.0 * g.stroke_m * rpm / 60.0;
}
// Piston position from crank center, F-06.
inline double piston_x(const EngineGeometry &g, double theta) {
    const double a = g.stroke_m / 2.0;
    const double s = a * std::sin(theta) - g.pin_offset_m;
    return a * std::cos(theta) + std::sqrt(g.rod_length_m * g.rod_length_m - s * s);
}
inline double piston_x_tdc(const EngineGeometry &g) {
    const double a = g.stroke_m / 2.0;
    return std::sqrt((g.rod_length_m + a) * (g.rod_length_m + a) -
                     g.pin_offset_m * g.pin_offset_m);
}
inline double piston_travel(const EngineGeometry &g, double theta) { // s(theta)
    return piston_x_tdc(g) - piston_x(g, theta);
}
inline double cylinder_volume(const EngineGeometry &g, double theta) {
    return clearance_volume(g) + pi / 4.0 * g.bore_m * g.bore_m * piston_travel(g, theta);
}
inline double piston_travel_rate(const EngineGeometry &g, double theta) { // F-07 ds/dtheta
    const double a = g.stroke_m / 2.0;
    const double s = a * std::sin(theta) - g.pin_offset_m;
    return a * std::sin(theta) +
           a * std::cos(theta) * s / std::sqrt(g.rod_length_m * g.rod_length_m - s * s);
}
inline double gas_torque_per_cylinder(const EngineGeometry &g, double theta, // F-09
                                      double p_cyl_pa, double p_crankcase_pa) {
    return (p_cyl_pa - p_crankcase_pa) * pi / 4.0 * g.bore_m * g.bore_m *
           piston_travel_rate(g, theta);
}
} // namespace engine::physics
