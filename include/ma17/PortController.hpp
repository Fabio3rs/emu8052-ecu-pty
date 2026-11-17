#pragma once

#include "ma17/PtyBridge.hpp"

#include <chrono>
#include <cstdint>
#include <stdexcept>

struct em8051;

namespace ma17 {

// Fiat board-level P4 K-line input and optional P5 feedback stimulus.
class PortController {
  public:
    using ContactProvider = bool (*)(void *);
    PortController(PtyBridge &pty_bridge EMU_LIFETIMEBOUND,
                   long long &emulated_ticks EMU_LIFETIMEBOUND,
                   std::chrono::steady_clock::time_point &startup_time
                       EMU_LIFETIMEBOUND,
                   bool p4_6_force_low = false,
                   bool p4_7_force_low = false,
                   long long p4_6_low_from_tick = -1,
                   bool p4_3_force_low = false)
        : bridge_(pty_bridge), ticks_(emulated_ticks),
          startup_time_(startup_time), p4_6_force_low_(p4_6_force_low),
          p4_7_force_low_(p4_7_force_low),
          p4_6_low_from_tick_(p4_6_low_from_tick),
          p4_3_force_low_(p4_3_force_low) {}

    void set_idle_contact_provider(ContactProvider provider, void *context,
                                   bool high_when_closed = false,
                                   uint8_t pin_mask = 0x40u) {
        if (pin_mask != 0x08u && pin_mask != 0x40u)
            throw std::invalid_argument("invalid idle contact P4 pin");
        idle_contact_provider_ = provider;
        idle_contact_context_ = context;
        idle_contact_high_when_closed_ = high_when_closed;
        idle_contact_pin_mask_ = pin_mask;
    }

    void set_idle_contact_open_fault(long long from_tick,
                                     long long restore_tick) {
        idle_contact_open_tick_ = from_tick;
        idle_contact_restore_tick_ = restore_tick;
    }

    void set_idle_contact_closed_fault(long long from_tick) {
        idle_contact_closed_tick_ = from_tick;
    }

    uint8_t read(em8051 *cpu, uint8_t address);

  private:
    PtyBridge &bridge_;
    long long &ticks_;
    std::chrono::steady_clock::time_point &startup_time_;
    bool p4_6_force_low_;
    bool p4_7_force_low_;
    long long p4_6_low_from_tick_;
    bool p4_3_force_low_;
    ContactProvider idle_contact_provider_ = nullptr;
    void *idle_contact_context_ = nullptr;
    bool idle_contact_high_when_closed_ = false;
    uint8_t idle_contact_pin_mask_ = 0x40u;
    long long idle_contact_open_tick_ = 0;
    long long idle_contact_closed_tick_ = 0;
    long long idle_contact_restore_tick_ = 0;
    uint8_t last_p4_value_ = 0xFF;
};

} // namespace ma17
