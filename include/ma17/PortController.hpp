#pragma once

#include "ma17/PtyBridge.hpp"

#include <chrono>
#include <cstdint>

struct em8051;

namespace ma17 {

// Fiat board-level P4 K-line input and optional P5 feedback stimulus.
class PortController {
  public:
    PortController(PtyBridge &pty_bridge, long long &emulated_ticks,
                   std::chrono::steady_clock::time_point &startup_time,
                   bool p4_6_force_low = false,
                   bool p4_7_force_low = false,
                   long long p4_6_low_from_tick = -1)
        : bridge_(pty_bridge), ticks_(emulated_ticks),
          startup_time_(startup_time), p4_6_force_low_(p4_6_force_low),
          p4_7_force_low_(p4_7_force_low),
          p4_6_low_from_tick_(p4_6_low_from_tick) {}

    uint8_t read(em8051 *cpu, uint8_t address);

  private:
    PtyBridge &bridge_;
    long long &ticks_;
    std::chrono::steady_clock::time_point &startup_time_;
    bool p4_6_force_low_;
    bool p4_7_force_low_;
    long long p4_6_low_from_tick_;
    uint8_t last_p4_value_ = 0xFF;
};

} // namespace ma17
