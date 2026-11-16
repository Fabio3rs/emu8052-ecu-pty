#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <stdexcept>

namespace ecu_hw {

struct IgnitionStageParameters {
    bool charge_active_low = true; // P5 polarity is a candidate binding.
    double minimum_charge_s = 0.0003;
    double full_charge_s = 0.0020;
};

class Ma17IgnitionStage {
  public:
    explicit Ma17IgnitionStage(IgnitionStageParameters parameters = {})
        : parameters_(parameters) {
        if (!(parameters.minimum_charge_s >= 0.0) ||
            !(parameters.full_charge_s > parameters.minimum_charge_s))
            throw std::invalid_argument("invalid ignition charge times");
    }

    void set_connected(unsigned channel, bool connected) {
        if (channel >= connected_.size())
            throw std::out_of_range("invalid ignition channel");
        connected_[channel] = connected;
    }

    // Returns candidate spark strengths on current interruption, one per coil.
    std::array<double, 2> step(uint8_t p5_bits, double dt_s) {
        if (!(dt_s > 0.0))
            throw std::invalid_argument("invalid ignition tick");
        std::array<double, 2> sparks{};
        attempts_ = {};
        for (unsigned channel = 0; channel < 2; ++channel) {
            const bool high = (p5_bits & (1u << channel)) != 0;
            const bool active = parameters_.charge_active_low ? !high : high;
            attempts_[channel] = initialized_ && charging_[channel] && !active;
            if (attempts_[channel] && connected_[channel] &&
                charge_s_[channel] >= parameters_.minimum_charge_s)
                sparks[channel] = std::min(1.0, charge_s_[channel] /
                                                    parameters_.full_charge_s);
            charge_s_[channel] = active ? charge_s_[channel] + dt_s : 0.0;
            charging_[channel] = active;
        }
        initialized_ = true;
        return sparks;
    }

    bool attempted(unsigned channel) const { return attempts_.at(channel); }

  private:
    IgnitionStageParameters parameters_;
    std::array<double, 2> charge_s_{};
    std::array<bool, 2> charging_{};
    std::array<bool, 2> connected_{true, true};
    std::array<bool, 2> attempts_{};
    bool initialized_ = false;
};

} // namespace ecu_hw
