#include "ma17/XramAccess.hpp"

extern "C" {
#include "emu8051.h"
}

#include <cstdio>
#include <cstdlib>

namespace ma17 {

uint8_t read_xram(em8051 *cpu, uint16_t address) {
    if (!cpu->mExtData)
        return 0;
    return cpu->mExtData[address & cpu->mExtDataMaxIdx];
}

void write_xram(em8051 *cpu, uint16_t address, uint8_t value,
                long long emulated_ticks) {
    const uint16_t masked = address & cpu->mExtDataMaxIdx;
    const uint8_t previous = read_xram(cpu, address);
    static const bool trace_pc = std::getenv("MA17_TRACE_PC") != nullptr;
    if (trace_pc && masked == 0xF8DD && previous != value) {
        static int gate_writes = 0;
        if (gate_writes++ < 32)
            fprintf(stderr,
                    "[CC3-GATE-WRITE] instr=%lld PC=%04X "
                    "XRAM_F8DD=%02X->%02X\n",
                    emulated_ticks, cpu->mPC, previous, value);
    }

    if (cpu->mExtData)
        cpu->mExtData[masked] = value;
}

} // namespace ma17
