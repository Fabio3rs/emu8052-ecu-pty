#pragma once

#include <cstdint>

struct em8051;

namespace ma17 {

uint8_t read_adc_channel(uint8_t channel);
void set_adc_tick(uint64_t tick);
uint8_t read_addat(em8051 *cpu, uint8_t address);
uint8_t read_addatl(em8051 *cpu, uint8_t address);
void start_adc_conversion(em8051 *cpu, uint8_t address);
void write_ircon(em8051 *cpu, uint8_t address);

} // namespace ma17
