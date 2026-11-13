#include "ma17/AdcSimulator.hpp"

extern "C" {
#include "emu8051.h"
}

#include <array>
#include <cstdio>
#include <cstdlib>

namespace ma17 {

uint8_t read_adc_channel(uint8_t channel) {
    // Fiat ROM 06E3h..06F1h first targets IRAM 60h..67h; channel 3 is
    // redirected to upper IRAM A8h. Values are test stimuli, not calibration.
    static const std::array<uint8_t, 8> adc_values = [] {
        std::array<uint8_t, 8> values{120, 130, 100, 80, 90, 110, 95, 105};
        for (unsigned index = 0; index < values.size(); ++index) {
            char name[32];
            snprintf(name, sizeof(name), "MA17_ADC_CH%u", index);
            const char *setting = std::getenv(name);
            if (!setting)
                continue;
            char *end = nullptr;
            const long value = std::strtol(setting, &end, 10);
            if (*setting && *end == '\0' && value >= 4 && value <= 247)
                values[index] = static_cast<uint8_t>(value);
            else
                fprintf(stderr, "[ADC] invalid %s=%s; using %u\n", name,
                        setting, values[index]);
        }
        return values;
    }();
    return adc_values[channel];
}

uint8_t read_addat(em8051 *cpu, uint8_t) {
    const uint8_t channel = cpu->mSFR[0xD8 - 0x80] & 0x07;
    return read_adc_channel(channel);
}

void write_ircon(em8051 *cpu, uint8_t address) {
    // The Fiat Timer 0 ISR waits at 0711h for SAB80C517 IRCON.0 (ADC ready).
    static int write_count = 0;
    if (write_count < 10)
        fprintf(stderr, "[IRCON-WRITE] #%d IRCON=0x%02X, forcing bit 0=1\n",
                ++write_count, cpu->mSFR[address - 0x80]);
    cpu->mSFR[address - 0x80] |= 0x01;
}

} // namespace ma17
