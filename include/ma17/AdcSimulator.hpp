#pragma once

#include <cstdint>

struct em8051;

namespace ma17 {

// Return true for a driven channel and supply its instantaneous pin voltage.
using AdcVoltageProvider = bool (*)(uint8_t, void *, double &);
struct AdcObservation {
    uint64_t tick = 0;
    double pin_voltage_v = 0.0;
    uint16_t count = 0;
    bool sampled = false;
    bool voltage_available = false;
};
void set_adc_voltage_provider(AdcVoltageProvider provider, void *context);
AdcObservation adc_observation(uint8_t channel);

uint8_t read_adc_channel(uint8_t channel);
void set_adc_tick(uint64_t tick);
uint8_t read_addat(em8051 *cpu, uint8_t address);
uint8_t read_addatl(em8051 *cpu, uint8_t address);
void start_adc_conversion(em8051 *cpu, uint8_t address);
void write_ircon(em8051 *cpu, uint8_t address);

} // namespace ma17
