#include "engine/CrankDynamics.hpp"

#include <cmath>
#include <stdexcept>

namespace engine {
namespace {
constexpr double pi = 3.14159265358979323846;
constexpr double position_rad = 2.0 * pi / CrankDynamics::wheel_positions;
} // namespace

CrankDynamics::CrankDynamics(CrankParameters parameters)
    : parameters_(parameters) {
    if (!std::isfinite(parameters.inertia_kg_m2) ||
        parameters.inertia_kg_m2 <= 0.0 ||
        !std::isfinite(parameters.wheel_offset_rad) ||
        parameters.wheel_offset_rad < 0.0 ||
        parameters.wheel_offset_rad >= position_rad ||
        !std::isfinite(parameters.starter_torque_nm) ||
        parameters.starter_torque_nm < 0.0 ||
        !std::isfinite(parameters.breakaway_torque_nm) ||
        parameters.breakaway_torque_nm < 0.0 ||
        !std::isfinite(parameters.running_friction_nm) ||
        parameters.running_friction_nm < 0.0 ||
        !std::isfinite(parameters.viscous_friction_nm_per_rad_s) ||
        parameters.viscous_friction_nm_per_rad_s < 0.0)
        throw std::invalid_argument("invalid crank parameters");
}

bool CrankDynamics::step(bool starter_engaged, double combustion_torque_nm,
                         double load_torque_nm) {
    if (!std::isfinite(combustion_torque_nm) ||
        !std::isfinite(load_torque_nm) || load_torque_nm < 0.0)
        throw std::invalid_argument("invalid crank torque");

    const double drive_nm =
        combustion_torque_nm +
        (starter_engaged ? parameters_.starter_torque_nm : 0.0) -
        load_torque_nm;
    if (speed_rad_s_ == 0.0 && drive_nm <= parameters_.breakaway_torque_nm)
        return false;

    const double friction_nm = friction_torque_nm();
    const double acceleration =
        (drive_nm - friction_nm) / parameters_.inertia_kg_m2;
    const double next_speed =
        std::fmax(0.0, speed_rad_s_ + acceleration / ticks_per_second);
    angle_rad_ += (speed_rad_s_ + next_speed) / (2.0 * ticks_per_second);
    speed_rad_s_ = next_speed;

    const auto reached = static_cast<long long>(
        std::floor((angle_rad_ + parameters_.wheel_offset_rad) / position_rad));
    if (reached > crossed_positions_) {
        crossed_positions_ = reached;
        return true;
    }
    return false;
}

double CrankDynamics::rpm() const { return speed_rad_s_ * 30.0 / pi; }

double CrankDynamics::friction_torque_nm() const {
    return parameters_.running_friction_nm +
           parameters_.viscous_friction_nm_per_rad_s * speed_rad_s_;
}

int CrankDynamics::wheel_position() const {
    return static_cast<int>(crossed_positions_ % wheel_positions);
}

double CrankDynamics::wheel_phase_rad() const {
    return angle_rad_ + parameters_.wheel_offset_rad -
           static_cast<double>(crossed_positions_) * position_rad;
}

} // namespace engine
