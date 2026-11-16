#pragma once

#include "engine/IntakeFuel.hpp"
#include "engine/FuelBlend.hpp"

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
        if (std::abs(phase) > 0.60 || channel != expected_channel ||
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
        pulse_torque_nm_ =
            fuel_kg * fuel_.lower_heating_value_j_kg() *
            indicated_efficiency *
            std::min(1.0, spark_strength) * phase_efficiency / expansion_rad;
        pulse_end_rad_ = crank_angle_rad + expansion_rad;
        burned_fuel_kg_ += burned_fuel_kg;
        event.burned_fuel_kg = burned_fuel_kg;
        ++burns_;
        ++burns_by_cylinder_[cylinder];
        return event;
    }

    double torque_nm(double crank_angle_rad) const {
        return crank_angle_rad < pulse_end_rad_ ? pulse_torque_nm_ : 0.0;
    }
    unsigned long long burns() const { return burns_; }
    const std::array<unsigned long long, 4> &burns_by_cylinder() const {
        return burns_by_cylinder_;
    }
    unsigned long long missed_sparks() const { return missed_sparks_; }
    double burned_fuel_kg() const { return burned_fuel_kg_; }
    double fuel_energy_j_per_kg() const {
        return fuel_.lower_heating_value_j_kg();
    }

  private:
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
    double pulse_end_rad_ = 0.0;
    double burned_fuel_kg_ = 0.0;
    unsigned long long burns_ = 0;
    std::array<unsigned long long, 4> burns_by_cylinder_{};
    unsigned long long missed_sparks_ = 0;
};

} // namespace engine
