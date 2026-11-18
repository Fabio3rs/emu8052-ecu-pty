#pragma once

namespace engine {

class Drivetrain;

// Estimated equivalent crank/flywheel parameters; SI units throughout.
struct CrankParameters {
    double inertia_kg_m2 = 0.20;
    double starter_torque_nm = 50.0;
    double breakaway_torque_nm = 4.0;
    // ~1.1 bar FMEP near 900 rpm for a 1.58 L four-stroke engine.
    // Provisional motored estimate; includes accessories, not pumping.
    double running_friction_nm = 12.5;
    double viscous_friction_nm_per_rad_s = 0.02;
    double wheel_offset_rad = 0.0; // Position zero relative to crank zero.
};

class CrankDynamics {
  public:
    static constexpr double ticks_per_second = 990000.0;
    static constexpr int wheel_positions = 60;
    static constexpr int physical_teeth = 58;

    explicit CrankDynamics(CrankParameters parameters = {});

    // Advance one 11.88 MHz / 12 machine cycle. Returns true at a 6-degree
    // wheel boundary; positions 58 and 59 are the missing teeth.
    // Transmission torque is signed: positive drives the crank, negative
    // loads it. Keep this separate from combustion and scenario resistance.
    bool step(bool starter_engaged, double combustion_torque_nm = 0.0,
              double load_torque_nm = 0.0, double transmission_torque_nm = 0.0,
              Drivetrain *drivetrain = nullptr);

    double angle_rad() const { return angle_rad_; }
    double speed_rad_s() const { return speed_rad_s_; }
    double inertia_kg_m2() const { return parameters_.inertia_kg_m2; }
    double rpm() const;
    double friction_torque_nm() const;
    int wheel_position() const;
    double wheel_phase_rad() const;

  private:
    CrankParameters parameters_;
    double angle_rad_ = 0.0;
    double speed_rad_s_ = 0.0;
    long long crossed_positions_ = 0;
};

} // namespace engine
