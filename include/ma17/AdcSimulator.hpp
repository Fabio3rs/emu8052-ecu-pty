#pragma once

#include <cstdint>

struct em8051;

namespace ma17 {

// Return true for a driven channel and supply its instantaneous pin voltage.
using AdcVoltageProvider = bool (*)(uint8_t, void *, double &);
void set_adc_voltage_provider(AdcVoltageProvider provider, void *context);

uint8_t read_adc_channel(uint8_t channel);
void set_adc_tick(uint64_t tick);
uint8_t read_addat(em8051 *cpu, uint8_t address);
uint8_t read_addatl(em8051 *cpu, uint8_t address);
void start_adc_conversion(em8051 *cpu, uint8_t address);
void write_ircon(em8051 *cpu, uint8_t address);

} // namespace ma17
