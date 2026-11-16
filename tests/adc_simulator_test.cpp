#include "ma17/AdcSimulator.hpp"

#include <gtest/gtest.h>

extern "C" {
#include "emu8051.h"
}

TEST(AdcSimulator, ConversionLatchesSelectedChannelUntilNextStart) {
    em8051 cpu{};
    cpu.mSFR[0xD8 - 0x80] = 0xF5;
    ma17::start_adc_conversion(&cpu, 0xDA);
    EXPECT_EQ(ma17::read_addat(&cpu, 0xD9), ma17::read_adc_channel(5));
    cpu.mSFR[0xD8 - 0x80] = 0xF7;
    EXPECT_EQ(ma17::read_addat(&cpu, 0xD9), ma17::read_adc_channel(5));
    ma17::start_adc_conversion(&cpu, 0xDA);
    EXPECT_EQ(ma17::read_addat(&cpu, 0xD9), ma17::read_adc_channel(7));
}

TEST(AdcSimulator, IrconWriteRestoresReadyBit) {
    em8051 cpu{};
    cpu.mSFR[0xC0 - 0x80] = 0xA4;
    ma17::write_ircon(&cpu, 0xC0);
    EXPECT_EQ(cpu.mSFR[0xC0 - 0x80], 0xA5);
}

TEST(AdcSimulator, DynamicVoltageIsQuantizedAtConversionStart) {
    double voltage = 2.5;
    ma17::set_adc_voltage_provider(
        +[](uint8_t channel, void *context, double &sample) {
            if (channel != 6) return false;
            sample = *static_cast<double *>(context);
            return true;
        },
        &voltage);
    em8051 cpu{};
    cpu.mSFR[0xD8 - 0x80] = 6;
    ma17::start_adc_conversion(&cpu, 0xDA);
    EXPECT_EQ(ma17::read_addat(&cpu, 0xD9), 128);
    EXPECT_EQ(ma17::read_addatl(&cpu, 0xDA), 0);

    voltage = 4.0;
    EXPECT_EQ(ma17::read_addat(&cpu, 0xD9), 128);
    ma17::start_adc_conversion(&cpu, 0xDA);
    EXPECT_EQ(ma17::read_addat(&cpu, 0xD9), 204);
    EXPECT_EQ(ma17::read_addatl(&cpu, 0xDA), 128);
    ma17::set_adc_voltage_provider(nullptr, nullptr);
}
