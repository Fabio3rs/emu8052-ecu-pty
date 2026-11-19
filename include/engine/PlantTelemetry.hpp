#pragma once
// Cycle-window averages of the plant energy and air balance (F-36, F-37, F-38,
// F-48). Windows are multiples of 4*pi of crank angle, never frames. SI units
// inside; convert to bar, kW, g/h only in GUI and reports. LLM-written (Claude).
#include "engine/physics/Combustion.hpp"
#include "engine/physics/Gas.hpp"

#include <cmath>

namespace engine {

struct PlantWindowResult {
    bool valid = false; // false means N/D (no rotation or empty window)
    double window_s = 0.0;
    double mean_rpm = 0.0;
    double indicated_torque_nm = 0.0;
    double friction_torque_nm = 0.0;
    double pumping_torque_nm = 0.0;
    double accessory_torque_nm = 0.0; // load + accessories seen by the crank
    double brake_torque_nm = 0.0;     // T_b = T_i - T_f - T_p - T_ac
    double brake_power_kw = 0.0;
    double imep_bar = 0.0;
    double bmep_bar = 0.0;
    double work_per_cycle_j = 0.0;    // indicated, whole engine
    double ve_ambient = 0.0;          // F-48 eta_v,window vs rho_ref
    double air_mg_per_cyl_cycle = 0.0;
    double air_to_cylinders_kg_s = 0.0;
    double fuel_g_s = 0.0;
    double fuel_l_h = 0.0;
    double bsfc_g_kwh = 0.0;          // 0 when power <= 0
    double lambda_cylinders = 0.0;    // from delivered air and fuel
};

class PlantWindow {
  public:
    explicit PlantWindow(double displacement_m3 = 0.00158, int cylinders = 4,
                         double window_cycles = 20.0)
        : displacement_m3_(displacement_m3), cylinders_(cylinders),
          window_angle_rad_(window_cycles * 4.0 * physics::pi) {}

    // Advance by one tick of simulated time; angle step must be >= 0.
    void accumulate(double dt_s, double d_angle_rad, double combustion_nm,
                    double friction_nm, double pumping_nm, double load_nm) {
        if (d_angle_rad < 0.0) return;
        angle_ += d_angle_rad;
        time_ += dt_s;
        w_ind_ += combustion_nm * d_angle_rad;
        w_fric_ += friction_nm * d_angle_rad;
        w_pump_ += pumping_nm * d_angle_rad;
        w_load_ += load_nm * d_angle_rad;
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
        const double t_i = w_ind_ / angle_, t_f = w_fric_ / angle_,
                     t_p = w_pump_ / angle_, t_l = w_load_ / angle_;
        r.valid = time_ > 0.0 && angle_ > 0.0;
        r.window_s = time_;
        const double omega = angle_ / time_;
        r.mean_rpm = omega * 60.0 / (2.0 * physics::pi);
        r.indicated_torque_nm = t_i;
        r.friction_torque_nm = t_f;
        r.pumping_torque_nm = t_p;
        r.accessory_torque_nm = t_l;
        r.brake_torque_nm = t_i - t_f - t_p - t_l;
        r.brake_power_kw = r.brake_torque_nm * omega / 1000.0;
        const double cycles = angle_ / (4.0 * physics::pi);
        r.work_per_cycle_j = w_ind_ / cycles;
        r.imep_bar = r.work_per_cycle_j / displacement_m3_ / 1e5;
        r.bmep_bar = physics::bmep_pa(r.brake_torque_nm, displacement_m3_) / 1e5;
        r.ve_ambient = air_kg_ / (rho_ref_kg_m3 * displacement_m3_ * cycles);
        r.air_mg_per_cyl_cycle = air_kg_ / (cylinders_ * cycles) * 1e6;
        r.air_to_cylinders_kg_s = air_kg_ / time_;
        r.fuel_g_s = inj_kg_ / time_ * 1e3;
        r.fuel_l_h = r.fuel_g_s * 3.6 / 740.0; // gasoline-class density, report only
        r.bsfc_g_kwh = r.brake_power_kw > 0.5
                           ? physics::bsfc_g_kwh(inj_kg_ / time_, r.brake_power_kw)
                           : 0.0;
        r.lambda_cylinders =
            fuel_cyl_kg_ > 0.0 ? air_kg_ / (fuel_cyl_kg_ * afr_st) : 0.0;
        (void)pci_j_kg;
        last_ = r;
        reset();
        return true;
    }
    const PlantWindowResult &last() const { return last_; }

  private:
    void reset() {
        angle_ = time_ = w_ind_ = w_fric_ = w_pump_ = w_load_ = 0.0;
        air_kg_ = inj_kg_ = fuel_cyl_kg_ = 0.0;
    }
    double displacement_m3_;
    int cylinders_;
    double window_angle_rad_;
    double angle_ = 0, time_ = 0, w_ind_ = 0, w_fric_ = 0, w_pump_ = 0, w_load_ = 0;
    double air_kg_ = 0, inj_kg_ = 0, fuel_cyl_kg_ = 0;
    PlantWindowResult last_{};
};

} // namespace engine
