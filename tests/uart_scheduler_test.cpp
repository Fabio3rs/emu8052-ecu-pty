#include "ma17/UartScheduler.hpp"

#include <gtest/gtest.h>

extern "C" {
#include "emu8051.h"
}

TEST(UartScheduler, TxSetsTiAtStartOfStopBit) {
    ma17::PtyBridge bridge{+[](uint8_t) {}};
    long long ticks = 100;
    ma17::UartScheduler uart{bridge, ticks};
    em8051 cpu{};
    uart.bind_cpu(&cpu);
    cpu.mSFR[0x99 - 0x80] = 0x5A;

    uart.on_sbuf_write(&cpu);
    uart.tick(&cpu, 100 + 9 * 206 - 1);
    EXPECT_EQ(cpu.mSFR[0x98 - 0x80] & 0x02, 0);

    uart.tick(&cpu, 100 + 9 * 206);
    EXPECT_EQ(cpu.mSFR[0x98 - 0x80] & 0x02, 0x02);
    EXPECT_EQ(uart.on_sbuf_read(&cpu, 0x99), 0);
}

TEST(UartScheduler, RxSetsRiAfterNineAndHalfBitsWithoutReplacingTx) {
    ma17::PtyBridge bridge{+[](uint8_t) {}};
    long long ticks = 0;
    ma17::UartScheduler uart{bridge, ticks};
    em8051 cpu{};
    uart.bind_cpu(&cpu);
    cpu.mSFR[0x99 - 0x80] = 0x55;
    uart.on_sbuf_write(&cpu);

    uart.on_scanner_byte(0xA5);
    uart.tick(&cpu, 9 * 206 + 103 - 1);
    EXPECT_EQ(cpu.mSFR[0x98 - 0x80] & 0x01, 0);
    EXPECT_EQ(uart.on_sbuf_read(&cpu, 0x99), 0);

    uart.tick(&cpu, 9 * 206 + 103);
    EXPECT_EQ(cpu.mSFR[0x98 - 0x80] & 0x01, 0x01);
    EXPECT_EQ(uart.on_sbuf_read(&cpu, 0x99), 0xA5);
    EXPECT_EQ(cpu.mSFR[0x99 - 0x80], 0x55);
    ASSERT_EQ(bridge.rx_queue.size(), 1);
    EXPECT_EQ(bridge.rx_queue.front(), 0xA5);

    uart.on_scanner_byte(0x33);
    EXPECT_EQ(bridge.rx_queue.size(), 1);
    EXPECT_EQ(uart.on_sbuf_read(&cpu, 0x99), 0xA5);
}
