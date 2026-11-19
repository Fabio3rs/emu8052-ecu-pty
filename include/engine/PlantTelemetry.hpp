#pragma once
// Cycle-window averages of the plant energy and air balance (F-36, F-37, F-38,
// F-48). Windows are multiples of 4*pi of crank angle, never frames. SI units
// inside; convert to bar, kW, g/h only in GUI and reports. LLM-written (Claude).
#include "engine/physics/Combustion.hpp"
#include "engine/physics/Gas.hpp"

#include <algorithm>
#include <cmath>

namespace engine {

struct PlantWindowResult {
    bool valid = false; // false means N/D (no rotation or empty window)
    // Identification: a republished line is recognisable by window_id and its tick span.
    unsigned long long window_id = 0;
    long long tick_start = 0;
    long long tick_end = 0;
    double window_s = 0.0;
    double mean_rpm = 0.0;
    // Angle-averaged torques [N.m] (work over the window divided by the crank angle).
    double indicated_torque_nm = 0.0;
    double friction_torque_nm = 0.0;
    double pumping_torque_nm = 0.0;
    double accessory_torque_nm = 0.0;  // alternator + water pump only
    // shaft = indicated - friction - pumping - accessory (torque available at the shaft).
    double shaft_torque_nm = 0.0;
    double brake_absorbed_nm = 0.0;    // external brake / scenario load: W_brake / dtheta
    // Old brake_torque_nm, renamed: mean net torque on the crank ~ J * d(omega)/dt.
    double net_torque_nm = 0.0;
    // Energy ledger of the window [J]: sources positive, sinks as magnitudes.
    double w_indicated_j = 0.0, w_friction_j = 0.0, w_pumping_j = 0.0, w_accessory_j = 0.0;
    double w_brake_j = 0.0, w_starter_j = 0.0, w_drivetrain_j = 0.0;
    double omega_start_rad_s = 0.0, omega_end_rad_s = 0.0;
    double inertia_kg_m2 = 0.0;
    double kinetic_j = 0.0;            // 1/2 J (omega_end^2 - omega_start^2)
    double shaft_power_kw = 0.0;       // (W_brake + dE_kin - W_starter - W_drivetrain) / dt
    // (W_ind + W_start + W_drv - W_fric - W_pump - W_acc - W_brake - dE_kin) / W_ind
    double energy_residual_rel = 0.0;
    double imep_bar = 0.0;
    double bmep_bar = 0.0;             // from the shaft torque
    double work_per_cycle_j = 0.0;     // indicated, whole engine
    double ve_ambient = 0.0;           // F-48 eta_v,window vs rho_ref
    double air_mg_per_cyl_cycle = 0.0;
    double air_to_cylinders_kg_s = 0.0;
    double fuel_g_s = 0.0;
    double fuel_l_h = 0.0;
    double bsfc_g_kwh = 0.0;           // from the shaft power; 0 when power <= 0.5 kW
    double lambda_cylinders = 0.0;     // from delivered air and fuel
};

// Torques acting on the crank during one tick [N.m], all evaluated exactly as the crank
// integrator uses them (see CrankDynamics::step): the energy ledger then closes to rounding.
struct TickTorques {
    double combustion_nm = 0.0;
    double friction_nm = 0.0;
    double pumping_nm = 0.0;
    double accessory_nm = 0.0;
    double brake_nm = 0.0;       // external brake / scenario load (absorbing, >= 0)
    double starter_nm = 0.0;     // driving, >= 0 while the starter is engaged
    double drivetrain_nm = 0.0;  // signed torque of the clutch on the crank
};

class PlantWindow {
  public:
    explicit PlantWindow(double displacement_m3 = 0.00158, int cylinders = 4,
                         double window_cycles = 20.0)
        : displacement_m3_(displacement_m3), cylinders_(cylinders),
          window_angle_rad_(window_cycles * 4.0 * physics::pi) {}

    void set_inertia(double kg_m2) { inertia_ = kg_m2; }

    // Advance by one tick of simulated time; the angle step must be >= 0.
    void accumulate(long long tick, double dt_s, double d_angle_rad, double omega_before,
                    double omega_after, const TickTorques &t) {
        if (d_angle_rad < 0.0) return;
        if (angle_ == 0.0 && time_ == 0.0) {
            tick_start_ = tick;
            omega_start_ = omega_before;
        }
        tick_end_ = tick;
        omega_end_ = omega_after;
        angle_ += d_angle_rad;
        time_ += dt_s;
        w_ind_ += t.combustion_nm * d_angle_rad;
        w_fric_ += t.friction_nm * d_angle_rad;
        w_pump_ += t.pumping_nm * d_angle_rad;
        w_acc_ += t.accessory_nm * d_angle_rad;
        w_brake_ += t.brake_nm * d_angle_rad;
        w_start_ += t.starter_nm * d_angle_rad;
        w_drv_ += t.drivetrain_nm * d_angle_rad;
    }
    void add_mass(double air_to_cylinders_kg, double injected_fuel_kg,
                  double delivered_fuel_kg) {
        air_kg_ += air_to_cylinders_kg;
        inj_kg_ += injected_fuel_kg;
        fuel_cyl_kg_ += delivered_fuel_kg;
    }
    // Close the window when it spans enough cycles; returns true when it did.
    bool finish_if_ready(double rho_ref_kg_m3, double afr_st, double pci_j_kg) {
        if (angle_ < window_angle_rad_) return false;
        PlantWindowResult r;
        r.valid = time_ > 0.0 && angle_ > 0.0;
        r.window_id = windows_closed_ + 1;
        r.tick_start = tick_start_;
        r.tick_end = tick_end_;
        r.window_s = time_;
        const double omega = angle_ / time_;
        r.mean_rpm = omega * 60.0 / (2.0 * physics::pi);
        r.indicated_torque_nm = w_ind_ / angle_;
        r.friction_torque_nm = w_fric_ / angle_;
        r.pumping_torque_nm = w_pump_ / angle_;
        r.accessory_torque_nm = w_acc_ / angle_;
        r.shaft_torque_nm = r.indicated_torque_nm - r.friction_torque_nm -
                            r.pumping_torque_nm - r.accessory_torque_nm;
        r.brake_absorbed_nm = w_brake_ / angle_;
        r.w_indicated_j = w_ind_;
        r.w_friction_j = w_fric_;
        r.w_pumping_j = w_pump_;
        r.w_accessory_j = w_acc_;
        r.w_brake_j = w_brake_;
        r.w_starter_j = w_start_;
        r.w_drivetrain_j = w_drv_;
        r.omega_start_rad_s = omega_start_;
        r.omega_end_rad_s = omega_end_;
        r.inertia_kg_m2 = inertia_;
        r.kinetic_j = 0.5 * inertia_ * (omega_end_ * omega_end_ - omega_start_ * omega_start_);
        const double net_work = w_ind_ + w_start_ + w_drv_ - w_fric_ - w_pump_ - w_acc_ - w_brake_;
        r.net_torque_nm = net_work / angle_;
        r.shaft_power_kw = (w_brake_ + r.kinetic_j - w_start_ - w_drv_) / time_ / 1000.0;
        const double scale = std::max(w_ind_, std::max(std::abs(w_start_), std::abs(w_drv_)));
        r.energy_residual_rel = scale > 1e-9 ? (net_work - r.kinetic_j) / scale : 0.0;
        const double cycles = angle_ / (4.0 * physics::pi);
        r.work_per_cycle_j = w_ind_ / cycles;
        r.imep_bar = r.work_per_cycle_j / displacement_m3_ / 1e5;
        r.bmep_bar = physics::bmep_pa(r.shaft_torque_nm, displacement_m3_) / 1e5;
        r.ve_ambient = air_kg_ / (rho_ref_kg_m3 * displacement_m3_ * cycles);
        r.air_mg_per_cyl_cycle = air_kg_ / (cylinders_ * cycles) * 1e6;
        r.air_to_cylinders_kg_s = air_kg_ / time_;
        r.fuel_g_s = inj_kg_ / time_ * 1e3;
        r.fuel_l_h = r.fuel_g_s * 3.6 / 740.0; // gasoline-class density, report only
        r.bsfc_g_kwh = r.shaft_power_kw > 0.5
                           ? physics::bsfc_g_kwh(inj_kg_ / time_, r.shaft_power_kw)
                           : 0.0;
        r.lambda_cylinders =
            fuel_cyl_kg_ > 0.0 ? air_kg_ / (fuel_cyl_kg_ * afr_st) : 0.0;
        (void)pci_j_kg;
        last_ = r;
        ++windows_closed_;
        reset();
        return true;
    }
    const PlantWindowResult &last() const { return last_; }
    // Diagnostic only: shorter windows for transient analysis (>= 1 cycle).
    void set_window_cycles(double cycles) {
        if (cycles >= 1.0) window_angle_rad_ = cycles * 4.0 * physics::pi;
    }
    unsigned long long windows_closed() const { return windows_closed_; }

  private:
    void reset() {
        angle_ = time_ = w_ind_ = w_fric_ = w_pump_ = w_acc_ = w_brake_ = w_start_ = w_drv_ = 0.0;
        air_kg_ = inj_kg_ = fuel_cyl_kg_ = 0.0;
    }
    double displacement_m3_;
    int cylinders_;
    double window_angle_rad_;
    double angle_ = 0, time_ = 0, w_ind_ = 0, w_fric_ = 0, w_pump_ = 0, w_acc_ = 0, w_brake_ = 0,
           w_start_ = 0, w_drv_ = 0;
    long long tick_start_ = 0, tick_end_ = 0;
    double omega_start_ = 0, omega_end_ = 0, inertia_ = 0.2;
    double air_kg_ = 0, inj_kg_ = 0, fuel_cyl_kg_ = 0;
    PlantWindowResult last_{};
    unsigned long long windows_closed_ = 0;
};

} // namespace engine
