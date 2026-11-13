#pragma once

extern "C" {
#include "emu8051.h"
}

#include <algorithm>
#include <array>

namespace ma17 {

struct CpuContext {
    em8051 cpu{};
    std::array<unsigned char, 0x10000> code_memory{};
    std::array<unsigned char, 0x10000> ext_data_memory{};
    std::array<unsigned char, 128> upper_data{};

    CpuContext() {
        std::fill(std::begin(cpu.mSFR), std::end(cpu.mSFR), 0);
        std::fill(std::begin(cpu.mLowerData), std::end(cpu.mLowerData), 0);
        cpu.mCodeMem = code_memory.data();
        cpu.mCodeMemMaxIdx = 0xFFFF;
        cpu.mExtData = ext_data_memory.data();
        cpu.mExtDataMaxIdx = 0xFFFF;
        // Fiat firmware accesses 80h..FFh through @R0/@R1.
        cpu.mUpperData = upper_data.data();
    }
};

} // namespace ma17
