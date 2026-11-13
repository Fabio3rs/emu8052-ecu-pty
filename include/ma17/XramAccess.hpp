#pragma once

#include <cstdint>

struct em8051;

namespace ma17 {

uint8_t read_xram(em8051 *cpu, uint16_t address);
void write_xram(em8051 *cpu, uint16_t address, uint8_t value,
                long long emulated_ticks);

} // namespace ma17
