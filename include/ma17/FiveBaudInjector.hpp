#pragma once

#include "ma17/PtyBridge.hpp"

namespace ma17 {

// ISO 9141-2 slow init for address 10h at the Fiat 11.88 MHz clock.
struct FiveBaudInjector {
    explicit FiveBaudInjector(PtyBridge &pty_bridge) : bridge(pty_bridge) {}

    void start(long long current_tick);
    void tick(long long current_tick);

    PtyBridge &bridge;
    bool active = false;
    int current_bit = 0;
    long long bit_end_instruction = 0;
    static constexpr int bits[10] = {0, 0, 0, 0, 0, 1, 0, 0, 0, 1};
    static constexpr long long ticks_per_bit = 198000;
};

} // namespace ma17
