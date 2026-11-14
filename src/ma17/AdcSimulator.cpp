#include "ma17/AdcSimulator.hpp"

extern "C" {
#include "emu8051.h"
}

#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdio>
#include <cstdlib>

namespace ma17 {

namespace {

uint64_t adc_tick = 0;

uint16_t read_adc_10bit_channel(uint8_t channel) {
    // Fiat ROM 06E3h..06F1h first targets IRAM 60h..67h; channel 3 is
    // redirected to upper IRAM A8h. Legacy 8-bit stimuli occupy the high
    // eight result bits; MA17_ADC10_CHn can supply all ten bits.
    static const std::array<uint16_t, 8> adc_values = [] {
        std::array<uint16_t, 8> values{120 * 4, 130 * 4, 100 * 4, 80 * 4,
                                       90 * 4, 110 * 4, 95 * 4, 105 * 4};
        for (unsigned index = 0; index < values.size(); ++index) {
            char name[32];
            snprintf(name, sizeof(name), "MA17_ADC_CH%u", index);
            const char *setting = std::getenv(name);
            if (setting) {
                char *end = nullptr;
                const long value = std::strtol(setting, &end, 10);
                if (*setting && *end == '\0' && value >= 4 && value <= 247)
                    values[index] = static_cast<uint16_t>(value * 4);
                else
                    fprintf(stderr, "[ADC] invalid %s=%s; using %u\n", name,
                            setting, static_cast<unsigned>(values[index] >> 2));
            }
            snprintf(name, sizeof(name), "MA17_ADC10_CH%u", index);
            setting = std::getenv(name);
            if (setting) {
                char *end = nullptr;
                const long value = std::strtol(setting, &end, 10);
                if (*setting && *end == '\0' && value >= 0 && value <= 1023)
                    values[index] = static_cast<uint16_t>(value);
                else
                    fprintf(stderr, "[ADC] invalid %s=%s; using %u\n", name,
                            setting, values[index]);
            }
        }
        return values;
    }();
    struct Step {
        uint64_t tick{};
        uint16_t value{};
    };
    struct StepProgram {
        std::array<Step, 8> steps{};
        size_t count{};
    };
    static const std::array<StepProgram, 8> programs = [] {
        std::array<StepProgram, 8> values{};
        for (unsigned index = 0; index < values.size(); ++index) {
            char name[32];
            snprintf(name, sizeof(name), "MA17_ADC10_STEP_CH%u", index);
            const char *setting = std::getenv(name);
            if (!setting)
                continue;
            const char *cursor = setting;
            uint64_t previous_tick = 0;
            while (*cursor) {
                errno = 0;
                char *separator = nullptr;
                const unsigned long long tick = std::strtoull(cursor, &separator, 10);
                if (values[index].count == values[index].steps.size() || errno ||
                    separator == cursor || *separator != ':' ||
                    !std::all_of(cursor, static_cast<const char *>(separator),
                                 [](char digit) {
                        return digit >= '0' && digit <= '9';
                    }) ||
                    tick <= previous_tick) {
                    fprintf(stderr, "[ADC] invalid %s=%s; expected ascending "
                            "tick:value steps (max 8)\n", name, setting);
                    std::exit(2);
                }
                errno = 0;
                char *end = nullptr;
                const long value = std::strtol(separator + 1, &end, 10);
                if (errno || end == separator + 1 ||
                    !std::all_of(separator + 1, end, [](char digit) {
                        return digit >= '0' && digit <= '9';
                    }) ||
                    (*end != '\0' && *end != ',') || value < 0 || value > 1023 ||
                    (*end == ',' && end[1] == '\0')) {
                    fprintf(stderr, "[ADC] invalid %s=%s; expected ascending "
                            "tick:value steps (max 8)\n", name, setting);
                    std::exit(2);
                }
                values[index].steps[values[index].count++] = {
                    static_cast<uint64_t>(tick), static_cast<uint16_t>(value)};
                previous_tick = static_cast<uint64_t>(tick);
                cursor = *end == ',' ? end + 1 : end;
            }
            if (values[index].count == 0) {
                fprintf(stderr, "[ADC] invalid %s=%s; expected tick:value\n",
                        name, setting);
                std::exit(2);
            }
        }
        return values;
    }();
    uint16_t result = adc_values[channel];
    const StepProgram &program = programs[channel];
    for (size_t index = 0; index < program.count; ++index) {
        if (adc_tick < program.steps[index].tick)
            break;
        result = program.steps[index].value;
    }
    return result;
}

uint8_t selected_channel(em8051 *cpu) {
    return cpu->mSFR[0xD8 - 0x80] & 0x07;
}

} // namespace

void set_adc_tick(uint64_t tick) {
    adc_tick = tick;
}

uint8_t read_adc_channel(uint8_t channel) {
    return static_cast<uint8_t>(read_adc_10bit_channel(channel) >> 2);
}

uint8_t read_addat(em8051 *cpu, uint8_t) {
    return cpu->mSFR[0xD9 - 0x80];
}

uint8_t read_addatl(em8051 *cpu, uint8_t) {
    return cpu->mSFR[0xDA - 0x80];
}

void start_adc_conversion(em8051 *cpu, uint8_t) {
    // SAB80C517A User's Manual Addendum, pp. 5-6/5-7: writing ADDATL
    // starts conversion; the left-justified result remains in both ADDAT
    // registers until the next conversion completes. Latency is modeled
    // as zero here, matching the existing immediate IRCON-ready behavior.
    const uint16_t result = read_adc_10bit_channel(selected_channel(cpu));
    cpu->mSFR[0xD9 - 0x80] = static_cast<uint8_t>(result >> 2);
    cpu->mSFR[0xDA - 0x80] = static_cast<uint8_t>((result & 0x03) << 6);
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
