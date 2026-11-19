#pragma once

#include "Lifetime.hpp"

#include "engine/IntakeFuel.hpp"
#include "engine/FuelBlend.hpp"
#include "engine/physics/Combustion.hpp"
#include "engine/physics/Volumetric.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>

namespace engine {

struct CombustionEvent {
    double air_kg = 0.0;
    double fuel_kg = 0.0;
    double burned_fuel_kg = 0.0;
    unsigned cylinder_index = 0; // Zero-based, provisional firing order 1-3-4-2.
};

struct CombustionParameters {
    // MA1.7 repair manual cites 120 degrees from missing teeth to 1/4 TDC;
    // exact wheel-zero edge, installed polarity and 720-degree compression
    // assignment remain unverified. Adding 360 degrees swaps compression
    // cylinders within each wasted-spark pair.
    double tdc_phase_rad = 2.0 * 3.14159265358979323846 / 3.0;
    bool swap_coil_channels = false; // Candidate P5-to-cylinder-pair binding.
    // Relative coil charge threshold is an engineering estimate, not a
    // measured ignition probability. The observed nominal minimum is 0.817.
    double full_burn_strength = 0.80;
    // false: legacy fixed 0.24 efficiency, optimum fixed at 11.5 deg BTDC.
    // true: eta_i = eta_ref * g(lambda) * f_av * f_dil (F-30..F-34).
    bool physical_efficiency = false;
    double eta_ref = 0.36;        // calibrado: alvo 133 N.m @3000 (F-31: 0,34-0,38)
    double burn_duration0_deg = 60.0; // calibrado: F-33 faixa 50-75 deg
    double burn_ref_rpm = 3000.0;     // referencia de F-33
    double burn_residual_gain = 1.2;  // calibrado: MBT na lenta ~19 deg
    double spark_k = 3.5e-4;      // F-33 (10 deg de atraso -> -3,5%)
    double dilution_k = 1.0;      // calibrado (F-34)
    double dilution_x0 = 0.10;    // calibrado (F-34)
    double compression_ratio = 9.2; // manual B.500.837 p.5
    // Experiments (--exp adv_force_mbt / adv_offset_deg): efficiency evaluated at the plant MBT
    // (+offset) instead of the ROM advance. Pulse timing in crank angle is NOT moved. Off by default.
    bool exp_force_mbt = false;
    double exp_adv_offset_deg = 0.0;
    // Pulse torque scales with burn_fraction (strength / full_burn_strength, capped at 1), consistent with the
    // burn-fraction rule: a coil charged above the ignition threshold burns the whole charge (CURVES_STUDY F-2).
    // --exp spark_torque_legacy=1 restores the earlier proportional-to-raw-strength law for comparison.
    bool exp_legacy_strength_scaling = false;
};

// Provisional four-cylinder, wasted-spark event model. Coil 0 serves 1/4,
// coil 1 serves 3/2; one cylinder is on compression at each half revolution.
class Combustion {
  public:
    explicit Combustion(CombustionParameters parameters = {},
                        FuelBlend fuel = {})
        : parameters_(parameters), fuel_(fuel) {
        if (!std::isfinite(parameters.tdc_phase_rad) ||
            parameters.tdc_phase_rad < 0.0 ||
            parameters.tdc_phase_rad >= 4.0 * 3.14159265358979323846)
            throw std::invalid_argument("invalid TDC phase");
        if (!std::isfinite(parameters.full_burn_strength) ||
            parameters.full_burn_strength <= 0.0 ||
            parameters.full_burn_strength > 1.0)
            throw std::invalid_argument("invalid burn strength thresholds");
    }

    void admit(const IntakeStep &charge, double crank_angle_rad) {
        const unsigned cylinder = cylinder_for_slot(slot_at(crank_angle_rad, true));
        pending_air_kg_[cylinder] += charge.air_to_cylinders_kg;
        pending_fuel_kg_[cylinder] += charge.fuel_to_cylinders_kg;
    }

    // Operating point for the physical efficiency model (rpm, p_m, p_e).
    void set_operating_point(double rpm, double manifold_pa, double exhaust_pa) {
        rpm_ = rpm;
        manifold_pa_ = manifold_pa;
        exhaust_pa_ = exhaust_pa;
    }
    double last_spark_advance_deg() const { return last_advance_deg_; }
    double last_mbt_deg() const { return last_mbt_deg_; }
    double last_spark_efficiency() const { return last_eta_i_; }
    double last_residual_fraction() const { return last_xr_; }
    double last_lambda() const { return last_lambda_; }

    CombustionEvent spark(double crank_angle_rad, unsigned channel,
                          double spark_strength = 1.0) {
        constexpr double pi = 3.14159265358979323846;
        if (channel >= 2)
            throw std::out_of_range("invalid ignition channel");
        const unsigned slot = slot_at(crank_angle_rad, false);
        const unsigned cylinder = cylinder_for_slot(slot);
        const double phase =
            std::remainder(crank_angle_rad - parameters_.tdc_phase_rad, pi);
        const double air_kg = std::min(pending_air_kg_[cylinder], 0.0006);
        const double fuel_kg = std::min(
            pending_fuel_kg_[cylinder],
            air_kg / fuel_.stoichiometric_air_fuel_ratio());
        CombustionEvent event{pending_air_kg_[cylinder],
                              pending_fuel_kg_[cylinder], 0.0, cylinder};
        pending_air_kg_[cylinder] = 0.0;
        pending_fuel_kg_[cylinder] = 0.0;
        if (event.air_kg <= 0.0 && event.fuel_kg <= 0.0)
            return event;
        const unsigned expected_channel =
            (slot % 2) ^ static_cast<unsigned>(parameters_.swap_coil_channels);
        if (std::abs(phase) > (parameters_.physical_efficiency ? 0.85 : 0.60) ||
            channel != expected_channel ||
            fuel_kg <= 0.0 || !std::isfinite(spark_strength) ||
            spark_strength <= 0.0) {
            ++missed_sparks_;
            return event;
        }
        constexpr double indicated_efficiency = 0.24;
        constexpr double expansion_rad = 2.0;
        // Provisional peak near 11.5 degrees BTDC; timing reduces useful
        // work smoothly while the burned fuel still reaches the exhaust.
        const double phase_error_rad = (phase + 0.20) / 0.60;
        const double phase_efficiency =
            std::exp(-0.5 * phase_error_rad * phase_error_rad);
        // Normal coil charge can ignite the full charge even when below the
        // reference maximum; below it, partial burn remains provisional.
        const double burn_fraction = std::clamp(
            spark_strength / parameters_.full_burn_strength, 0.0, 1.0);
        const double burned_fuel_kg = fuel_kg * burn_fraction;
        double efficiency = indicated_efficiency * phase_efficiency;
        if (parameters_.physical_efficiency) {
            const double afr = fuel_.stoichiometric_air_fuel_ratio();
            last_lambda_ = pending_lambda(event.air_kg, event.fuel_kg, afr);
            last_advance_deg_ = -phase * 180.0 / pi;
            last_xr_ = physics::residual_fraction(
                exhaust_pa_, std::max(1000.0, manifold_pa_),
                parameters_.compression_ratio);
            const double dur = physics::burn_duration_deg(
                parameters_.burn_duration0_deg, std::max(rpm_, 1.0),
                parameters_.burn_ref_rpm, parameters_.burn_residual_gain,
                last_xr_, 1.0);
            last_mbt_deg_ = physics::mbt_deg(dur);
            efficiency = parameters_.eta_ref *
                         physics::f_lambda_fuel(last_lambda_) *
                         physics::f_advance((parameters_.exp_force_mbt
                                                   ? parameters_.exp_adv_offset_deg
                                                   : last_advance_deg_ + parameters_.exp_adv_offset_deg -
                                                         last_mbt_deg_),
                                            parameters_.spark_k) *
                         std::max(0.0, physics::f_dilution(
                                           last_xr_, parameters_.dilution_k,
                                           parameters_.dilution_x0));
            last_eta_i_ = efficiency;
        }
        pulse_torque_nm_ =
            fuel_kg * fuel_.lower_heating_value_j_kg() *
            efficiency *
            (parameters_.exp_legacy_strength_scaling ? std::min(1.0, spark_strength) : burn_fraction) /
            expansion_rad;
        pulse_start_rad_ = crank_angle_rad;
        pulse_end_rad_ = crank_angle_rad + expansion_rad;
        energy_scheduled_j_ += pulse_torque_nm_ * expansion_rad;
        burned_fuel_kg_ += burned_fuel_kg;
        event.burned_fuel_kg = burned_fuel_kg;
        ++burns_;
        ++burns_by_cylinder_[cylinder];
        return event;
    }

    // Torque of the current pulse at a crank angle: zero before the spark and after
    // the end of the expansion window (GOAL_DYNO_ROM 1.1).
    double torque_nm(double crank_angle_rad) const {
        return crank_angle_rad >= pulse_start_rad_ && crank_angle_rad < pulse_end_rad_
                   ? pulse_torque_nm_
                   : 0.0;
    }
    // Exact work [J] of the current pulse over the crank interval [a0, a1]:
    // T * |[a0, a1] intersect [spark, spark + 2 rad]|.
    double work_j(double a0, double a1) const {
        const double lo = std::max(a0, pulse_start_rad_);
        const double hi = std::min(a1, pulse_end_rad_);
        return hi > lo ? pulse_torque_nm_ * (hi - lo) : 0.0;
    }
    double pulse_torque_nm() const { return pulse_torque_nm_; }
    double pulse_start_rad() const { return pulse_start_rad_; }
    double pulse_end_rad() const { return pulse_end_rad_; }
    // Sum of T * 2 rad over every pulse scheduled so far (telemetry, energy checks).
    double energy_scheduled_j() const { return energy_scheduled_j_; }
    unsigned long long burns() const { return burns_; }
    const std::array<unsigned long long, 4> &burns_by_cylinder() const
        EMU_LIFETIMEBOUND {
        return burns_by_cylinder_;
    }
    unsigned long long missed_sparks() const { return missed_sparks_; }
    double burned_fuel_kg() const { return burned_fuel_kg_; }
    double tdc_phase_rad() const { return parameters_.tdc_phase_rad; }
    unsigned pair_for_channel(unsigned channel) const {
        if (channel >= 2)
            throw std::out_of_range("invalid ignition channel");
        return channel ^ static_cast<unsigned>(parameters_.swap_coil_channels);
    }
    double stoichiometric_afr() const { return fuel_.stoichiometric_air_fuel_ratio(); }
    double fuel_energy_j_per_kg() const {
        return fuel_.lower_heating_value_j_kg();
    }

  private:
    static double pending_lambda(double air, double fuel, double afr) {
        return fuel > 0.0 ? air / (fuel * afr) : 99.0;
    }
    static unsigned cylinder_for_slot(unsigned slot) {
        constexpr std::array<unsigned, 4> order{0, 2, 3, 1};
        return order[slot];
    }
    unsigned slot_at(double crank_angle_rad, bool intake) const {
        constexpr double pi = 3.14159265358979323846;
        if (!std::isfinite(crank_angle_rad))
            throw std::invalid_argument("invalid crank angle");
        const double turns = (crank_angle_rad - parameters_.tdc_phase_rad) / pi;
        double slot = std::fmod(intake ? std::floor(turns) + 2.0
                                       : std::round(turns), 4.0);
        if (slot < 0.0) slot += 4.0;
        return static_cast<unsigned>(slot);
    }
    CombustionParameters parameters_;
    FuelBlend fuel_;
    std::array<double, 4> pending_air_kg_{};
    std::array<double, 4> pending_fuel_kg_{};
    double pulse_torque_nm_ = 0.0;
    double pulse_start_rad_ = 0.0;
    double pulse_end_rad_ = 0.0;
    double energy_scheduled_j_ = 0.0;
    double burned_fuel_kg_ = 0.0;
    double rpm_ = 0.0, manifold_pa_ = 100000.0, exhaust_pa_ = 100000.0;
    double last_advance_deg_ = 0.0, last_mbt_deg_ = 0.0, last_eta_i_ = 0.0,
           last_xr_ = 0.0, last_lambda_ = 0.0;
    unsigned long long burns_ = 0;
    std::array<unsigned long long, 4> burns_by_cylinder_{};
    unsigned long long missed_sparks_ = 0;
};

} // namespace engine
