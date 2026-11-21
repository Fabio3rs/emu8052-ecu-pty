#pragma once

#include "engine/ClutchCoupling.hpp"
#include "engine/SevelTransmission.hpp"

namespace engine {

// Longitudinal vehicle mass reflected through the Fiat gearbox. Parameters
// are explicit; no donor demo-car mass or clutch calibration is installed.
class Drivetrain {
  public:
    Drivetrain(double mass_kg, double tire_radius_m, double max_clutch_torque_nm,
               double initial_speed_m_s = 0.0)
        : mass_kg_(mass_kg), radius_m_(tire_radius_m),
          max_torque_nm_(max_clutch_torque_nm), speed_m_s_(initial_speed_m_s) {
        if (!transmission::reflected_inertia_kg_m2(mass_kg, 1, tire_radius_m) ||
            !std::isfinite(max_clutch_torque_nm) || max_clutch_torque_nm < 0.0 ||
            !std::isfinite(initial_speed_m_s))
            throw std::invalid_argument("invalid drivetrain parameters");
        update_gear_cache(0);
    }

    void set_gear(int gear) {
        if (gear < -1 || gear > 5)
            throw std::invalid_argument("invalid drivetrain gear");
        // Road velocity survives shifts; reflected inertia/speed are derived
        // afresh, preserving the donor changeGear kinetic-energy invariant.
        gear_ = gear;
        update_gear_cache(gear);
    }
    void set_clutch_pressure(double pressure) {
        if (!std::isfinite(pressure) || pressure < 0.0 || pressure > 1.0)
            throw std::invalid_argument("invalid clutch pressure");
        pressure_ = pressure;
    }
    void set_road_resistance(double rolling_force_n, double air_density_kg_m3,
                             double drag_coefficient, double frontal_area_m2) {
        for (const double value : {rolling_force_n, air_density_kg_m3,
                                   drag_coefficient, frontal_area_m2}) {
            if (!std::isfinite(value) || value < 0.0)
                throw std::invalid_argument("invalid road resistance");
        }
        const double drag = 0.5 * air_density_kg_m3 * drag_coefficient * frontal_area_m2;
        if (!std::isfinite(drag))
            throw std::invalid_argument("road resistance exceeds numeric range");
        rolling_force_n_ = rolling_force_n;
        drag_factor_ = drag;
    }
    int gear() const { return gear_; }
    double clutch_pressure() const { return pressure_; }
    double speed_m_s() const { return speed_m_s_; }
    double clutch_heat_j() const { return heat_j_; }
    double crank_torque_nm() const { return crank_torque_nm_; }

    // Called once per physical step, after crank external forces and before
    // crank angle integration. Returns the coupled crank velocity.
    double couple(double crank_free_rad_s, double crank_inertia, double dt_s) {
        if (!std::isfinite(crank_free_rad_s) || crank_free_rad_s < 0.0 ||
            !std::isfinite(crank_inertia) || crank_inertia <= 0.0 ||
            !std::isfinite(dt_s) || dt_s <= 0.0)
            throw std::invalid_argument("invalid drivetrain step");
        crank_torque_nm_ = 0.0;
        // OES VehicleDragConstraint: rollingResistance + 0.5*rho*v²*Cd*A.
        // Apply to the road mass even in neutral; the opposing impulse is
        // capped at rest, so drag cannot launch the car in the other direction.
        const double resistance = rolling_force_n_ + drag_factor_ * speed_m_s_ * speed_m_s_;
        const double deceleration_step = resistance / mass_kg_ * dt_s;
        if (!std::isfinite(resistance) || !std::isfinite(deceleration_step))
            throw std::invalid_argument("road force exceeds numeric range");
        const double free_speed = std::copysign(
            std::max(0.0, std::abs(speed_m_s_) - deceleration_step), speed_m_s_);
        if (gear_ == 0 || pressure_ == 0.0) {
            speed_m_s_ = free_speed;
            return crank_free_rad_s;
        }
        const double shaft_speed = free_speed * cached_ratio_over_radius_;
        const auto transfer = solve_clutch_transfer(crank_free_rad_s, shaft_speed,
            crank_inertia, cached_reflected_inertia_, max_torque_nm_, pressure_, dt_s);
        // The crank model cannot rotate backward. Limit both impulses together
        // if the vehicle rolls opposite to the selected gear.
        const double impulse = std::min(transfer.vehicle_impulse_nm_s,
                                       crank_free_rad_s * crank_inertia);
        const double heat = impulse * (crank_free_rad_s - shaft_speed -
            0.5 * impulse * (1.0 / crank_inertia + 1.0 / cached_reflected_inertia_));
        const double driven_speed =
            free_speed + impulse * cached_ratio_over_mass_radius_;
        // Retain the unused road impulse when the first stage reaches rest.
        // Otherwise sub-threshold clutch drive launches the car again every
        // step. This scalar split caps resistance at zero velocity in both
        // directions, without spending the same force budget twice.
        const double remaining_deceleration =
            std::max(0.0, deceleration_step - std::abs(speed_m_s_));
        const double next_speed = std::copysign(
            std::max(0.0, std::abs(driven_speed) - remaining_deceleration),
            driven_speed);
        const double next_crank = crank_free_rad_s - impulse / crank_inertia;
        if (!std::isfinite(next_speed) || !std::isfinite(next_crank) ||
            !std::isfinite(heat_j_ + heat) || !std::isfinite(impulse / dt_s))
            throw std::invalid_argument("drivetrain state exceeds numeric range");
        speed_m_s_ = next_speed;
        heat_j_ += std::max(0.0, heat);
        crank_torque_nm_ = -impulse / dt_s;
        return std::max(0.0, next_crank);
    }

  private:
    void update_gear_cache(int gear) {
        if (gear != 0) {
            const auto inertia = transmission::reflected_inertia_kg_m2(
                mass_kg_, gear, radius_m_);
            cached_reflected_inertia_ = inertia ? *inertia : 0.0;
            cached_overall_ratio_ = transmission::overall_ratio(gear);
            cached_ratio_over_radius_ = cached_overall_ratio_ / radius_m_;
            cached_ratio_over_mass_radius_ =
                cached_overall_ratio_ / (mass_kg_ * radius_m_);
        } else {
            cached_reflected_inertia_ = 0.0;
            cached_overall_ratio_ = 0.0;
            cached_ratio_over_radius_ = 0.0;
            cached_ratio_over_mass_radius_ = 0.0;
        }
    }

    double mass_kg_, radius_m_, max_torque_nm_;
    double speed_m_s_ = 0.0;
    double pressure_ = 0.0;
    double heat_j_ = 0.0;
    double crank_torque_nm_ = 0.0;
    double rolling_force_n_ = 0.0;
    double drag_factor_ = 0.0;
    int gear_ = 0;
    double cached_reflected_inertia_ = 0.0;
    double cached_overall_ratio_ = 0.0;
    double cached_ratio_over_radius_ = 0.0;
    double cached_ratio_over_mass_radius_ = 0.0;
};

} // namespace engine
