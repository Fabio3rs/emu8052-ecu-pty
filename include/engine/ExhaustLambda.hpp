#pragma once

#include "engine/Combustion.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <deque>
#include <stdexcept>

namespace engine {

struct ExhaustParameters {
    double sensor_distance_m = 0.60;
    double pipe_area_m2 = 0.00049; // 25 mm diameter candidate.
    double exhaust_pressure_pa = 100000.0;
    // Engineering estimates: heater gain and response need sensor measurements.
    double heater_rise_c_per_w = 16.0;
    double heater_tau_s = 6.0;
    double narrowband_slope = 25.0; // Candidate voltage-vs-lambda calibration.
    FuelBlend fuel;
};

class ExhaustLambda {
  public:
    explicit ExhaustLambda(ExhaustParameters parameters = {})
        : parameters_(parameters) {
        if (!(parameters.sensor_distance_m > 0.0) ||
            !(parameters.pipe_area_m2 > 0.0) ||
            !(parameters.exhaust_pressure_pa > 0.0) ||
            !(parameters.heater_rise_c_per_w > 0.0) ||
            !(parameters.heater_tau_s > 0.0) ||
            !(parameters.narrowband_slope > 0.0) ||
            !std::isfinite(parameters.narrowband_slope))
            throw std::invalid_argument("invalid exhaust geometry");
    }

    void admit(const CombustionEvent &event, double flow_kg_s, int64_t tick) {
        if (!(flow_kg_s >= 0.0) || tick < 0)
            throw std::invalid_argument("invalid exhaust event");
        if (event.air_kg <= 0.0 && event.fuel_kg <= 0.0)
            return;
        const double stoich = parameters_.fuel.stoichiometric_air_fuel_ratio();
        const double burnable_fuel_kg =
            std::min(event.fuel_kg, event.air_kg / stoich);
        const double burned_fraction =
            burnable_fuel_kg > 0.0
                ? std::clamp(event.burned_fuel_kg / burnable_fuel_kg, 0.0, 1.0)
                : 0.0;
        // Linear interpolation is a provisional partial-burn approximation.
        const double gas_c = 120.0 + 530.0 * burned_fraction;
        const double gas_k = gas_c + 273.15;
        const double density_kg_m3 =
            parameters_.exhaust_pressure_pa / (287.0 * gas_k);
        const double travel_s = std::min(
            5.0, parameters_.sensor_distance_m * density_kg_m3 *
                     parameters_.pipe_area_m2 / std::max(flow_kg_s, 1e-5));
        const int64_t delay_ticks =
            static_cast<int64_t>(std::ceil(travel_s * 990000.0));
        const int64_t arrival =
            std::max(tick + delay_ticks, last_arrival_tick_ + 1);
        last_arrival_tick_ = arrival;
        // Lambda uses this blend's stoichiometric AFR. The zirconia cell
        // responds to residual exhaust oxygen versus reference air, not
        // directly to the charge's absolute AFR.
        const double charge_lambda = event.fuel_kg > 0.0
                                         ? event.air_kg / (stoich * event.fuel_kg)
                                         : 5.0;
        const double oxygen_lambda =
            charge_lambda + (5.0 - charge_lambda) * (1.0 - burned_fraction);
        packets_.push_back({arrival, std::clamp(oxygen_lambda, 0.0, 5.0),
                            std::clamp(charge_lambda, 0.0, 5.0),
                            std::max(event.air_kg, 1e-9), gas_c});
    }

    void step(double dt_s, int64_t tick, double heater_power_w = 0.0) {
        if (!(dt_s > 0.0) || tick < 0 || !std::isfinite(heater_power_w) ||
            heater_power_w < 0.0)
            throw std::invalid_argument("invalid exhaust step");
        double arriving_air_kg = 0.0;
        double arriving_lambda_air_kg = 0.0;
        double arriving_charge_lambda_air_kg = 0.0;
        double arriving_temperature_air_kg = 0.0;
        while (!packets_.empty() && packets_.front().arrival_tick <= tick) {
            arriving_air_kg += packets_.front().air_kg;
            arriving_lambda_air_kg +=
                packets_.front().lambda * packets_.front().air_kg;
            arriving_charge_lambda_air_kg +=
                packets_.front().charge_lambda * packets_.front().air_kg;
            arriving_temperature_air_kg +=
                packets_.front().gas_c * packets_.front().air_kg;
            packets_.pop_front();
        }
        if (arriving_air_kg > 0.0) {
            target_lambda_ = arriving_lambda_air_kg / arriving_air_kg;
            target_charge_lambda_ =
                arriving_charge_lambda_air_kg / arriving_air_kg;
            target_gas_c_ = arriving_temperature_air_kg / arriving_air_kg;
        }
        // Heater power is an explicit electrical input; the runner only uses
        // it when its candidate ECU-to-relay binding is requested.
        if (packets_.empty() && tick - last_arrival_tick_ > 495000)
            target_gas_c_ = 20.0;
        // A finite sensor-side gas volume mixes successive firing/misfire
        // packets instead of exposing only the last cylinder event.
        lambda_ += (target_lambda_ - lambda_) *
                   (1.0 - std::exp(-dt_s / 0.08));
        charge_lambda_ += (target_charge_lambda_ - charge_lambda_) *
                          (1.0 - std::exp(-dt_s / 0.08));
        double thermal_tau_s = target_gas_c_ > 20.0 ? 2.0 : 10.0;
        if (heater_power_w > 0.0)
            thermal_tau_s = std::min(thermal_tau_s, parameters_.heater_tau_s);
        const double thermal_target_c = std::clamp(
            target_gas_c_ + heater_power_w * parameters_.heater_rise_c_per_w,
            20.0, 850.0);
        temperature_c_ += (thermal_target_c - temperature_c_) *
                          (1.0 - std::exp(-dt_s / thermal_tau_s));
        // Empirical narrowband switch around lambda=1; lambda_ is an oxygen
        // proxy, not a calculated oxygen partial pressure or Nernst voltage.
        // An experimental slope of 600 approximates SAE 920289's >6-fold
        // change across lambda 0.995..1.005; this ECU's probe is unmeasured.
        const double target_v =
            valid() ? 0.1 + 0.8 / (1.0 + std::exp(parameters_.narrowband_slope *
                                                  (lambda_ - 1.0)))
                    : 0.45;
        voltage_v_ += (target_v - voltage_v_) * (1.0 - std::exp(-dt_s / 0.1));
    }

    bool valid() const { return temperature_c_ >= 300.0; }
    double lambda() const { return lambda_; }
    double charge_lambda() const { return charge_lambda_; }
    double temperature_c() const { return temperature_c_; }
    double voltage_v() const { return voltage_v_; }

  private:
    struct Packet {
        int64_t arrival_tick;
        double lambda;
        double charge_lambda;
        double air_kg;
        double gas_c;
    };
    ExhaustParameters parameters_;
    std::deque<Packet> packets_;
    int64_t last_arrival_tick_ = 0;
    double target_gas_c_ = 20.0;
    double temperature_c_ = 20.0;
    double target_lambda_ = 5.0;
    double target_charge_lambda_ = 5.0;
    double lambda_ = 5.0;
    double charge_lambda_ = 5.0;
    double voltage_v_ = 0.45;
};

} // namespace engine
