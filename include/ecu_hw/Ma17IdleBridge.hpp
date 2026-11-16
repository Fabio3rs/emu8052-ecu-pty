#pragma once

#include <cmath>
#include <cstdint>
#include <stdexcept>

namespace ecu_hw {

struct IdleBridgeDrive {
    double voltage_v;
    bool brake;
};

// Candidate P1.5/P1.6 mapping. Driver transistors and freewheel mode
// have not been identified on the Fiat board.
class Ma17IdleBridge {
  public:
    explicit Ma17IdleBridge(double battery_v = 12.5,
                            bool reverse_direction = false)
        : battery_v_(battery_v), reverse_direction_(reverse_direction) {
        if (!std::isfinite(battery_v) || battery_v <= 0.0)
            throw std::invalid_argument("invalid idle bridge voltage");
    }

    IdleBridgeDrive drive(uint8_t p1_latch) const {
        const bool p15 = (p1_latch & 0x20u) != 0;
        const bool p16 = (p1_latch & 0x40u) != 0;
        if (p15 != p16)
            return {p15 != reverse_direction_ ? battery_v_ : -battery_v_,
                    false};
        return {0.0, !p15}; // 00 brake, 11 coast: provisional.
    }

  private:
    double battery_v_;
    bool reverse_direction_;
};

} // namespace ecu_hw
