#pragma once

#include <cstdint>

namespace ecu_hw {

// Candidate only: Fiat ROM P5.4 behaves like an active-low warning lamp.
// CPU-to-ECU connector 31 continuity and the output driver are unverified.
class Ma17DiagnosticLamp {
  public:
    void sample_p5(uint8_t p5_latch) {
        lamp_on_ = (p5_latch & 0x10u) == 0;
    }

    bool lamp_on() const { return lamp_on_; }

  private:
    bool lamp_on_ = false; // No ECU power is modeled before the first sample.
};

} // namespace ecu_hw
