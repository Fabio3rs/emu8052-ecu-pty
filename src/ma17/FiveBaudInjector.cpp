#include "ma17/FiveBaudInjector.hpp"

#include <cstdio>

namespace ma17 {

void FiveBaudInjector::start(long long current_tick) {
    if (active)
        return;
    active = true;
    current_bit = 0;
    bit_end_instruction = current_tick + ticks_per_bit;

    bridge.override_rxd = true;
    bridge.override_state = bits[0] != 0;
    fprintf(stderr, "\n[5-BAUD START] Bit 0: %s until instr=%lld\n",
            bridge.override_state ? "MARK(HIGH)" : "BREAK(LOW)",
            bit_end_instruction);
    fflush(stderr);
}

void FiveBaudInjector::tick(long long current_tick) {
    if (!active || current_tick < bit_end_instruction)
        return;

    current_bit++;
    if (current_bit >= 10) {
        active = false;
        bridge.override_state = true;
        bridge.override_rxd = false;
        fprintf(stderr,
                "[5-BAUD COMPLETE] All bits sent at instr=%lld, line "
                "returned to HIGH\n\n",
                current_tick);
        fflush(stderr);
        return;
    }

    bit_end_instruction = current_tick + ticks_per_bit;
    bridge.override_state = bits[current_bit] != 0;
    fprintf(stderr, "[5-BAUD] Bit %d: %s until instr=%lld\n", current_bit,
            bridge.override_state ? "MARK(HIGH)" : "BREAK(LOW)",
            bit_end_instruction);
    fflush(stderr);
}

} // namespace ma17
