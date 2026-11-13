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
                   std::chrono::steady_clock::time_point &startup_time)
        : bridge_(pty_bridge), ticks_(emulated_ticks),
          startup_time_(startup_time) {}

    uint8_t read(em8051 *cpu, uint8_t address);

  private:
    PtyBridge &bridge_;
    long long &ticks_;
    std::chrono::steady_clock::time_point &startup_time_;
    uint8_t last_p4_value_ = 0xFF;
};

} // namespace ma17
