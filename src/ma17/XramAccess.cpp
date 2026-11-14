#include "ma17/XramAccess.hpp"

extern "C" {
#include "emu8051.h"
}

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <array>

namespace ma17 {

uint8_t read_xram(em8051 *cpu, uint16_t address) {
    if (!cpu->mExtData)
        return 0;
    const uint8_t stored = cpu->mExtData[address & cpu->mExtDataMaxIdx];
    static const bool trace_f806 =
        std::getenv("MA17_TRACE_XRAM_F806") != nullptr;
    if (trace_f806 && address == 0xF806) {
        // SAB80C517 Instruction Set, MOVX A,@Ri: P2 supplies the address page.
        static int observations = 0;
        if (observations++ < 1000)
            std::fprintf(stderr, "[F806-READ] PC=%04X value=%02X\n",
                         cpu->mPC, stored);
    }
    if (address == 0xF847 && cpu->mPC == 0x0CB7 &&
        std::getenv("MA17_TRACE_IDLE_FAULT")) {
        // SAB80C517 Instruction Set, p. 224: MOVX A,@Ri uses the P2 page.
        // Fiat startup copies bits from this byte after a conditional seed.
        std::fprintf(stderr, "[IDLE-FAULT-STARTUP] PC=0CB7 addr=F847 value=%02X\n",
                     stored);
    }
    if (address == 0xF839 && cpu->mPC == 0x2B38) {
        static const int supplied = [] {
            const char *raw = std::getenv("MA17_OVERRIDE_IDLE_FAULT_READ");
            if (!raw)
                return -1;
            unsigned int value = 0;
            char extra = 0;
            if (std::strlen(raw) != 2 ||
                std::sscanf(raw, "%2x%c", &value, &extra) != 1) {
                std::fprintf(stderr, "Invalid MA17_OVERRIDE_IDLE_FAULT_READ: %s\n", raw);
                std::exit(2);
            }
            return static_cast<int>(value);
        }();
        if (supplied >= 0) {
            std::fprintf(stderr,
                         "[IDLE-FAULT-READ-OVERRIDE] PC=2B38 addr=F839 "
                         "stored=%02X supplied=%02X\n", stored,
                         static_cast<unsigned int>(supplied));
            return static_cast<uint8_t>(supplied);
        }
    }
    static const int override_f80c = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_XRAM_F80C");
        if (!raw)
            return -1;
        unsigned int value = 0;
        char extra = 0;
        if (std::strlen(raw) != 2 || std::sscanf(raw, "%2x%c", &value, &extra) != 1) {
            std::fprintf(stderr, "Invalid MA17_OVERRIDE_XRAM_F80C: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    if (address == 0xF80C) {
        // SAB80C517 Instruction Set, p. 224: MOVX A,@Ri reads external data.
        // Fiat ROM PC=55A2 verifies XRAM by readback; never alter that test.
        static std::array<bool, 65536> seen_pc{};
        if (std::getenv("MA17_TRACE_XRAM_F80C") && !seen_pc[cpu->mPC]) {
            seen_pc[cpu->mPC] = true;
            std::fprintf(stderr, "[XRAM-READ] PC=%04X addr=F80C stored=%02X\n",
                         cpu->mPC, stored);
        }
        if (override_f80c >= 0 && cpu->mPC != 0x55A2) {
            static int observations = 0;
            if (observations++ < 4)
                std::fprintf(stderr,
                             "[XRAM-OVERRIDE] PC=%04X addr=F80C stored=%02X read=%02X\n",
                             cpu->mPC, stored, static_cast<unsigned int>(override_f80c));
            return static_cast<uint8_t>(override_f80c);
        }
    }
    return stored;
}

void write_xram(em8051 *cpu, uint16_t address, uint8_t value,
                long long emulated_ticks) {
    const uint16_t masked = address & cpu->mExtDataMaxIdx;
    const uint8_t previous = cpu->mExtData ? cpu->mExtData[masked] : 0;
    static const bool trace_coolant_gate =
        std::getenv("MA17_TRACE_COOLANT_GATE") != nullptr;
    if (trace_coolant_gate && previous != value &&
        (masked == 0xF8D7 || masked == 0xF8D9)) {
        // SAB80C517 Instruction Set: MOVX uses P2 as the high address for @Ri.
        std::fprintf(stderr,
                     "[COOLANT-XRAM-WRITE] tick=%lld PC=%04X addr=%04X "
                     "value=%02X->%02X\n",
                     emulated_ticks, cpu->mPC, masked, previous, value);
    }
    static const bool trace_f806 =
        std::getenv("MA17_TRACE_XRAM_F806") != nullptr;
    if (trace_f806 && masked == 0xF806 && previous != value) {
        // SAB80C517 Instruction Set, MOVX @Ri: P2 supplies the address page.
        static int observations = 0;
        if (observations++ < 1000)
            std::fprintf(stderr,
                         "[F806-WRITE] tick=%lld PC=%04X value=%02X->%02X\n",
                         emulated_ticks, cpu->mPC, previous, value);
    }
    static const bool trace_matrix_path =
        std::getenv("MA17_TRACE_MATRIX_PATH") != nullptr;
    if (trace_matrix_path && previous != value &&
        (masked == 0xF8A5 || masked == 0xF8A6)) {
        // SAB80C517 Instruction Set, p. 224: MOVX @Ri uses P2 as the
        // high address byte; these are external F8:A5h/F8:A6h, not upper IRAM.
        std::fprintf(stderr,
                     "[MATRIX-STATE-WRITE] tick=%lld PC=%04X addr=%04X "
                     "value=%02X->%02X\n",
                     emulated_ticks, cpu->mPC, masked, previous, value);
    }
    if (trace_matrix_path && masked == 0xF889 && previous != value) {
        // SAB80C517 Instruction Set: MOVX @Ri writes via the P2 page.
        std::fprintf(stderr,
                     "[MATRIX-XRAM-WRITE] tick=%lld PC=%04X "
                     "addr=F889 value=%02X->%02X\n",
                     emulated_ticks, cpu->mPC, previous, value);
    }
    static const bool trace_curve_744e =
        std::getenv("MA17_TRACE_CURVE_744E_PATH") != nullptr;
    if (trace_curve_744e && (masked == 0xF836 || masked == 0xF837) &&
        previous != value) {
        // SAB80C517 Instruction Set, p. 224: MOVX @Ri uses P2 as the
        // high address byte; Fiat code 2606h..263Dh writes F8:36h/37h.
        std::fprintf(stderr,
                     "[CURVE-744E-XRAM] tick=%lld PC=%04X addr=%04X "
                     "value=%02X->%02X\n",
                     emulated_ticks, cpu->mPC, masked, previous, value);
    }
    static const bool trace_idle_position_candidate =
        std::getenv("MA17_TRACE_IDLE_POSITION") != nullptr;
    if (trace_idle_position_candidate && masked == 0xF83D &&
        previous != value) {
        // SAB80C517 Instruction Set, p. 224: MOVX @Ri addresses external
        // data through P2. The scanner calls F8:3D an idle position;
        // the Fiat board connection and physical scale remain unverified.
        std::fprintf(stderr,
                     "[IDLE-XRAM-WRITE] tick=%lld PC=%04X addr=F83D "
                     "value=%02X->%02X\n",
                     emulated_ticks, cpu->mPC, previous, value);
    }
    if (masked == 0xF83D && std::getenv("MA17_TRACE_IDLE_POSITION_ALL")) {
        // SAB80C517 Instruction Set, p. 224: MOVX @Ri uses the P2 page.
        // Include equal-value writes to distinguish a static field from
        // a repeatedly computed value that happens to stay constant.
        std::fprintf(stderr,
                     "[IDLE-XRAM-ALL] tick=%lld PC=%04X addr=F83D "
                     "value=%02X->%02X\n",
                     emulated_ticks, cpu->mPC, previous, value);
    }
    static const bool trace_idle_fault =
        std::getenv("MA17_TRACE_IDLE_FAULT") != nullptr;
    if (trace_idle_fault && masked == 0xF839 && previous != value) {
        // SAB80C517 Instruction Set, p. 224: MOVX @Ri uses P2 as
        // the high address byte; Fiat PC 2B38h later reads F8:39h.
        std::fprintf(stderr,
                     "[IDLE-FAULT-XRAM] tick=%lld PC=%04X addr=F839 "
                     "value=%02X->%02X\n",
                     emulated_ticks, cpu->mPC, previous, value);
    }
    if (trace_idle_fault && masked == 0xF83B && previous != value) {
        // SAB80C517 Instruction Set, p. 224: MOVX @Ri uses P2 as
        // the high address byte. Fiat PC 2C0Ch tests this countdown.
        std::fprintf(stderr,
                     "[IDLE-FAULT-COUNTDOWN] tick=%lld PC=%04X addr=F83B "
                     "value=%02X->%02X\n",
                     emulated_ticks, cpu->mPC, previous, value);
    }
    if (trace_idle_fault && masked == 0xF847 && previous != value) {
        // SAB80C517 Instruction Set, p. 224: MOVX @Ri uses the P2 page.
        std::fprintf(stderr,
                     "[IDLE-FAULT-SAVED] tick=%lld PC=%04X addr=F847 "
                     "value=%02X->%02X\n",
                     emulated_ticks, cpu->mPC, previous, value);
    }
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
