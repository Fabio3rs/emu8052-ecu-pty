#pragma once

#include <cstdint>

struct em8051;

namespace ma17 {

void trace_cpu_exception(em8051 *cpu, int code);
void trace_ie_write(em8051 *cpu, uint8_t address);
void trace_ien1_write(em8051 *cpu, uint8_t address);

} // namespace ma17
