#pragma once

#include <cmath>

namespace lab {

// 4.5: the Fiat 60-2 crank wheel. 60 positions 6 degrees apart, positions 58
// and 59 have no tooth. The gap ends at the TDC reference (tdc_phase_rad): at
// wheel rotation 0 the first tooth (position 0) starts at wheel angle 0.
inline constexpr int kWheelPositions = 60;
inline constexpr int kWheelMissing = 2;
inline constexpr double kWheelPi = 3.14159265358979323846;
inline constexpr double kWheelStepRad = 2.0 * kWheelPi / kWheelPositions;

inline bool wheel_tooth_present(int position) {
    return position >= 0 && position < kWheelPositions - kWheelMissing;
}

inline double wheel_wrap(double angle) {
    const double turn = 2.0 * kWheelPi;
    angle = std::fmod(angle, turn);
    return angle < 0.0 ? angle + turn : angle;
}

// How far the wheel has turned from its TDC reference, in [0, 2 pi).
inline double wheel_rotation_rad(double crank_angle_rad, double tdc_phase_rad) {
    return wheel_wrap(crank_angle_rad - tdc_phase_rad);
}

// The position under a fixed sensor at `sensor_angle_rad` (lab frame).
inline int wheel_position_under_sensor(double rotation_rad,
                                       double sensor_angle_rad) {
    const double wheel_angle = wheel_wrap(sensor_angle_rad - rotation_rad);
    int position = static_cast<int>(wheel_angle / kWheelStepRad);
    return position >= kWheelPositions ? kWheelPositions - 1 : position;
}

// True while the sensor sees a tooth (the VR output is then "on").
inline bool wheel_sensor_sees_tooth(double rotation_rad, double sensor_angle_rad) {
    return wheel_tooth_present(
        wheel_position_under_sensor(rotation_rad, sensor_angle_rad));
}

} // namespace lab
