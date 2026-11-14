#include "ma17/AdcSimulator.hpp"
#include "ma17/CpuHooks.hpp"
#include "ma17/PortController.hpp"
#include "ma17/PtyBridge.hpp"
#include "ma17/UartScheduler.hpp"

#include <gtest/gtest.h>

extern "C" {
#include "emu8051.h"
}

#include <array>
#include <chrono>

TEST(CpuHooks, WiresUartPortsAdcAndXramCallbacks) {
    ma17::PtyBridge bridge{+[](uint8_t) {}};
    long long ticks = 0;
    auto start = std::chrono::steady_clock::now();
    ma17::UartScheduler uart{bridge, ticks};
    ma17::PortController ports{bridge, ticks, start};
    ma17::CpuHooks hooks{uart, ports, ticks};
    em8051 cpu{};
    std::array<uint8_t, 0x1000> xram{};
    cpu.mExtData = xram.data();
    cpu.mExtDataMaxIdx = 0x0FFF;

    hooks.install_uart(cpu);
    ASSERT_NE(cpu.sfrwrite[0x99 - 0x80], nullptr);
    ASSERT_NE(cpu.sfrread[0x98 - 0x80], nullptr);

    hooks.install_fiat_peripherals(cpu);
    cpu.mSFR[0xD8 - 0x80] = 7;
    ASSERT_NE(cpu.sfrwrite[0xDA - 0x80], nullptr);
    cpu.sfrwrite[0xDA - 0x80](&cpu, 0xDA);
    EXPECT_EQ(cpu.sfrread[0xD9 - 0x80](&cpu, 0xD9), ma17::read_adc_channel(7));
    cpu.mSFR[0xE8 - 0x80] = 0xEA;
    EXPECT_EQ(cpu.sfrread[0xE8 - 0x80](&cpu, 0xE8), 0xCA);
    cpu.xwrite(&cpu, 0xF123, 0xA5);
    EXPECT_EQ(cpu.xread(&cpu, 0x0123), 0xA5);
}
