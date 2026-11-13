#include "ma17/AdcSimulator.hpp"

#include <gtest/gtest.h>

extern "C" {
#include "emu8051.h"
}

TEST(AdcSimulator, AddatSelectsChannelFromAdcon0) {
    em8051 cpu{};
    cpu.mSFR[0xD8 - 0x80] = 0xF7;
    EXPECT_EQ(ma17::read_addat(&cpu, 0xD9), ma17::read_adc_channel(7));
}

TEST(AdcSimulator, IrconWriteRestoresReadyBit) {
    em8051 cpu{};
    cpu.mSFR[0xC0 - 0x80] = 0xA4;
    ma17::write_ircon(&cpu, 0xC0);
    EXPECT_EQ(cpu.mSFR[0xC0 - 0x80], 0xA5);
}
