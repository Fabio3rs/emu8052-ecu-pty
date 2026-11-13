#include "ma17/PortController.hpp"

extern "C" {
#include "emu8051.h"
}

#include <cstdio>
#include <cstdlib>

namespace ma17 {

uint8_t PortController::read(em8051 *cpu, uint8_t address) {
    if (address == 0xE8) { // P4: the K-line transceiver drives pin P4.5.
        if (!bridge_.override_rxd && bridge_.low_until_ms &&
            PtyBridge::now_ms() >= bridge_.low_until_ms) {
            if (!bridge_.rxd_line_state) {
                fprintf(stderr,
                        "[K-LINE] UNBREAK: RXD LOW→HIGH (timer expired)\n");
                fflush(stderr);
            }
            bridge_.rxd_line_state = true;
            bridge_.low_until_ms = 0;
        }

        uint8_t p4 = cpu->mSFR[address - 0x80];
        const bool physical_high = bridge_.override_rxd
                                       ? bridge_.override_state
                                       : bridge_.rxd_line_state;
        // The L9637/MC33199 inverts K-line voltage: 12V -> P4.5=0.
        if (!physical_high)
            p4 |= 0x20;
        else
            p4 &= static_cast<uint8_t>(~0x20u);

        if (p4 != last_p4_value_) {
            const auto elapsed =
                std::chrono::duration_cast<std::chrono::milliseconds>(
                    std::chrono::steady_clock::now() - startup_time_);
            const uint8_t ram40 = cpu->mLowerData[0x40];
            fprintf(stderr,
                    "[P4.5] Read: 0x%02X (K-line=%s, P4.5=%d); PC=0x%04X; "
                    "RAM[0x40]=0x%02X; instru=%lld; time_since_start=%ld ms\n",
                    p4, physical_high ? "IDLE(12V)" : "BREAK(0V)",
                    (p4 >> 5) & 1, cpu->mPC, ram40, ticks_, elapsed.count());
            fflush(stderr);
            last_p4_value_ = p4;
        }

        cpu->mSFR[address - 0x80] = p4;
        return p4;
    }

    if (address == 0xF8) { // P5 feedback read, latch by default.
        uint8_t p5 = cpu->mSFR[address - 0x80];
        if (std::getenv("MA17_P5_FORCE_HIGH"))
            p5 |= 0x03;
        return p5;
    }

    return cpu->mSFR[address - 0x80];
}

} // namespace ma17
