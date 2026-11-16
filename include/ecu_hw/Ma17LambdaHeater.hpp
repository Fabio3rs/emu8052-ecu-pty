#pragma once

#include <cmath>
#include <cstdint>
#include <stdexcept>

namespace ecu_hw {

struct PumpRelayParameters {
    // Estimated mechanical dropout; the Fiat ROM emits 31-32 tick P3.4 pulses.
    int64_t dropout_ticks = 9900; // 10 ms at 990,000 machine cycles/s.
};

class Ma17PumpRelay {
  public:
    explicit Ma17PumpRelay(PumpRelayParameters parameters = {})
        : parameters_(parameters) {
        if (parameters_.dropout_ticks <= 0)
            throw std::invalid_argument("invalid pump relay dropout");
    }

    bool step(bool p34_high, int64_t tick) {
        if (tick < 0 || tick < last_tick_)
            throw std::invalid_argument("invalid pump relay tick");
        last_tick_ = tick;
        if (!p34_high) {
            closed_ = true;
            high_since_tick_ = -1;
        } else if (closed_) {
            if (high_since_tick_ < 0)
                high_since_tick_ = tick;
            else if (tick - high_since_tick_ >= parameters_.dropout_ticks)
                closed_ = false;
        }
        return closed_;
    }

    bool closed() const { return closed_; }

  private:
    PumpRelayParameters parameters_;
    int64_t last_tick_ = -1;
    int64_t high_since_tick_ = -1;
    bool closed_ = false;
};

struct LambdaHeaterParameters {
    // Alfatest MA1.7 repair manual: 4-8 ohms; 6 ohms is the test midpoint.
    double resistance_ohm = 6.0;
};

class Ma17LambdaHeater {
  public:
    explicit Ma17LambdaHeater(LambdaHeaterParameters parameters = {})
        : parameters_(parameters) {
        if (!std::isfinite(parameters_.resistance_ohm) ||
            parameters_.resistance_ohm <= 0.0)
            throw std::invalid_argument("invalid lambda heater resistance");
    }

    double power_w(double battery_v, bool pump_relay_closed) const {
        if (!std::isfinite(battery_v) || battery_v < 0.0)
            throw std::invalid_argument("invalid battery voltage");
        return pump_relay_closed
                   ? battery_v * battery_v / parameters_.resistance_ohm
                   : 0.0;
    }

  private:
    LambdaHeaterParameters parameters_;
};

} // namespace ecu_hw
