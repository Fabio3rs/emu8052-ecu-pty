#include "ma17/XramAccess.hpp"

#include <gtest/gtest.h>

extern "C" {
#include "emu8051.h"
}

#include <array>

TEST(XramAccess, MasksAddressAndPreservesPreviousValue) {
    std::array<uint8_t, 0x1000> memory{};
    em8051 cpu{};
    cpu.mExtData = memory.data();
    cpu.mExtDataMaxIdx = 0x0FFF;

    ma17::write_xram(&cpu, 0xF123, 0xA5, 0);
    EXPECT_EQ(memory[0x123], 0xA5);
    EXPECT_EQ(ma17::read_xram(&cpu, 0x0123), 0xA5);
    EXPECT_EQ(ma17::read_xram(&cpu, 0xF123), 0xA5);
}

TEST(XramAccess, MissingMemoryReadsAsZero) {
    em8051 cpu{};
    EXPECT_EQ(ma17::read_xram(&cpu, 0xF8DD), 0);
    ma17::write_xram(&cpu, 0xF8DD, 0x7F, 0);
}
