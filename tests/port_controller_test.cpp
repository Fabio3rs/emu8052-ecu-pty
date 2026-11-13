#include "ma17/PortController.hpp"

#include <gtest/gtest.h>

extern "C" {
#include "emu8051.h"
}

TEST(PortController, KLineVoltageIsInvertedOnP4BitFive) {
    ma17::PtyBridge bridge{+[](uint8_t) {}};
    long long ticks = 0;
    auto start = std::chrono::steady_clock::now();
    ma17::PortController ports{bridge, ticks, start};
    em8051 cpu{};
    cpu.mSFR[0xE8 - 0x80] = 0xEA;

    bridge.rxd_line_state = true;
    EXPECT_EQ(ports.read(&cpu, 0xE8), 0xCA);
    bridge.rxd_line_state = false;
    EXPECT_EQ(ports.read(&cpu, 0xE8), 0xEA);

    bridge.override_rxd = true;
    bridge.override_state = true;
    EXPECT_EQ(ports.read(&cpu, 0xE8), 0xCA);
}

TEST(PortController, P5ReadsCurrentFirmwareLatch) {
    ma17::PtyBridge bridge{+[](uint8_t) {}};
    long long ticks = 0;
    auto start = std::chrono::steady_clock::now();
    ma17::PortController ports{bridge, ticks, start};
    em8051 cpu{};
    cpu.mSFR[0xF8 - 0x80] = 0xA7;

    EXPECT_EQ(ports.read(&cpu, 0xF8), 0xA7);
}
