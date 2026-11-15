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

TEST(PortController, P4BitSixExternalLowDoesNotChangeOutputLatch) {
    ma17::PtyBridge bridge{+[](uint8_t) {}};
    long long ticks = 0;
    auto start = std::chrono::steady_clock::now();
    ma17::PortController ports{bridge, ticks, start, true};
    em8051 cpu{};
    cpu.mSFR[0xE8 - 0x80] = 0xEA;

    bridge.rxd_line_state = true;
    EXPECT_EQ(ports.read(&cpu, 0xE8), 0x8A);
    EXPECT_EQ(cpu.mSFR[0xE8 - 0x80], 0xCA);
    EXPECT_EQ(ports.read(&cpu, 0xE8), 0x8A);
}

TEST(PortController, P4BitSevenExperimentalLowDoesNotChangeOutputLatch) {
    ma17::PtyBridge bridge{+[](uint8_t) {}};
    long long ticks = 0;
    auto start = std::chrono::steady_clock::now();
    ma17::PortController ports{bridge, ticks, start, false, true};
    em8051 cpu{};
    cpu.mSFR[0xE8 - 0x80] = 0xEA;

    bridge.rxd_line_state = true;
    EXPECT_EQ(ports.read(&cpu, 0xE8), 0x4A);
    EXPECT_EQ(cpu.mSFR[0xE8 - 0x80], 0xCA);
    EXPECT_EQ(ports.read(&cpu, 0xE8), 0x4A);
}

TEST(PortController, P4BitThreeCandidateInputLowPreservesOutputLatch) {
    ma17::PtyBridge bridge{+[](uint8_t) {}};
    long long ticks = 0;
    auto start = std::chrono::steady_clock::now();
    ma17::PortController ports{bridge, ticks, start, false, false, -1, true};
    em8051 cpu{};
    cpu.mSFR[0xE8 - 0x80] = 0xEA;
    bridge.rxd_line_state = true;

    EXPECT_EQ(ports.read(&cpu, 0xE8), 0xC2);
    EXPECT_EQ(cpu.mSFR[0xE8 - 0x80], 0xCA);
    EXPECT_EQ(ports.read(&cpu, 0xE8), 0xC2);
}

TEST(PortController, P4BitSixTimedLowUsesEmulatedTicks) {
    ma17::PtyBridge bridge{+[](uint8_t) {}};
    long long ticks = 99;
    auto start = std::chrono::steady_clock::now();
    ma17::PortController ports{bridge, ticks, start, false, false, 100};
    em8051 cpu{};
    cpu.mSFR[0xE8 - 0x80] = 0xEA;
    bridge.rxd_line_state = true;

    EXPECT_EQ(ports.read(&cpu, 0xE8), 0xCA);
    ticks = 100;
    EXPECT_EQ(ports.read(&cpu, 0xE8), 0x8A);
    EXPECT_EQ(cpu.mSFR[0xE8 - 0x80], 0xCA);
}
