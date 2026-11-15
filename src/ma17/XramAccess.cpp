#include "ma17/XramAccess.hpp"

extern "C" {
#include "emu8051.h"
}

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <array>

namespace ma17 {

namespace {

int boot_xram_field_index(uint16_t address) {
    // SAB80C517 Instruction Set, MOVX @Ri: P2/XPAGE supplies the XRAM page.
    // Original Fiat boot copies ROM 7FF6h..7FFFh to these ten F8-page bytes.
    constexpr std::array<uint16_t, 10> destinations{
        0xF80F, 0xF81E, 0xF849, 0xF84A, 0xF863,
        0xF864, 0xF83F, 0xF84D, 0xF88F, 0xF8DE};
    for (size_t index = 0; index < destinations.size(); ++index) {
        if (address == destinations[index])
            return static_cast<int>(index);
    }
    return -1;
}

int trace_xram_address() {
    static const int address = [] {
        const char *raw = std::getenv("MA17_TRACE_XRAM_ADDRESS");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long parsed = std::strtoul(raw, &end, 16);
        if (std::strlen(raw) != 4 || *end != '\0' || parsed > 0xFFFF) {
            std::fprintf(stderr, "Invalid MA17_TRACE_XRAM_ADDRESS: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(parsed);
    }();
    return address;
}

int trace_xram_pc() {
    static const int pc = [] {
        const char *raw = std::getenv("MA17_TRACE_XRAM_PC");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long parsed = std::strtoul(raw, &end, 16);
        if (std::strlen(raw) != 4 || *end != '\0' || parsed > 0xFFFF) {
            std::fprintf(stderr, "Invalid MA17_TRACE_XRAM_PC: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(parsed);
    }();
    return pc;
}

}  // namespace

uint8_t read_xram(em8051 *cpu, uint16_t address) {
    if (!cpu->mExtData)
        return 0;
    const uint8_t stored = cpu->mExtData[address & cpu->mExtDataMaxIdx];
    if (address == trace_xram_address()) {
        // SAB80C517 Instruction Set: MOVX A,@Ri uses the P2/XPAGE page.
        // This records the XRAM byte before any experimental read override.
        static int observations = 0;
        if (observations++ < 1000)
            std::fprintf(stderr, "[XRAM-ADDRESS-READ] PC=%04X addr=%04X "
                         "stored=%02X\n", cpu->mPC, address, stored);
    }
    if (cpu->mPC == trace_xram_pc()) {
        // SAB80C517 Instruction Set: log the effective MOVX address after
        // P2/XPAGE selection; the instruction's R0/R1 byte alone is partial.
        static int observations = 0;
        if (observations++ < 1000)
            std::fprintf(stderr, "[XRAM-PC-READ] PC=%04X addr=%04X "
                         "stored=%02X P2=%02X XPAGE=%02X\n", cpu->mPC,
                         address, stored, cpu->mSFR[REG_P2],
                         cpu->mSFR[REG_XPAGE]);
    }
    static const bool trace_f8a2 =
        std::getenv("MA17_TRACE_XRAM_F8A2") != nullptr;
    if (trace_f8a2 && address == 0xF8A2 && cpu->mPC == 0x2016) {
        // SAB80C517 Instruction Set, MOVX A,@R1: P2 selects the XRAM page.
        // Fiat G PC2017h tests this byte before the conditional CC3 path.
        static int last_value = -1;
        if (stored != last_value) {
            last_value = stored;
            std::fprintf(stderr, "[F8A2-READ] PC=2016 value=%02X\n", stored);
        }
    }
    static const bool trace_f87f_reader =
        std::getenv("MA17_TRACE_XRAM_F87F") != nullptr;
    if (trace_f87f_reader && address == 0xF87F && cpu->mPC == 0x480D) {
        // SAB80C517 MOVX A,@R1: this is the Fiat G 74EEh curve's
        // XRAM scaling input. The XRAM address is not a processor pin.
        static int observations = 0;
        if (observations++ < 512)
            std::fprintf(stderr,
                         "[F87F-TABLE-READ] PC=480D stored=%02X\n", stored);
    }
    static const std::array<int, 3> read_override = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_XRAM_READ_AT");
        if (!raw)
            return std::array<int, 3>{-1, -1, -1};
        unsigned int pc = 0;
        unsigned int target = 0;
        unsigned int value = 0;
        char extra = 0;
        if (std::strlen(raw) != 12 || raw[4] != ':' || raw[9] != ':' ||
            std::strspn(raw, "0123456789abcdefABCDEF:") != 12 ||
            std::sscanf(raw, "%4x:%4x:%2x%c", &pc, &target, &value, &extra) != 3) {
            std::fprintf(stderr, "Invalid MA17_OVERRIDE_XRAM_READ_AT: %s\n", raw);
            std::exit(2);
        }
        return std::array<int, 3>{static_cast<int>(pc),
                                  static_cast<int>(target),
                                  static_cast<int>(value)};
    }();
    if (cpu->mPC == read_override[0] && address == read_override[1]) {
        // SAB80C517 Instruction Set, MOVX A,@Ri: P2/XPAGE supplies the
        // high XRAM address. Fiat G PC2027h reads F8:A3h after PC45F8h writes it.
        static int observations = 0;
        if (observations++ < 4)
            std::fprintf(stderr,
                         "[XRAM-READ-OVERRIDE] PC=%04X addr=%04X "
                         "stored=%02X supplied=%02X\n",
                         cpu->mPC, address, stored,
                         static_cast<unsigned>(read_override[2]));
        return static_cast<uint8_t>(read_override[2]);
    }
    static const bool trace_boot_fields =
        std::getenv("MA17_TRACE_BOOT_XRAM_FIELDS") != nullptr;
    if (trace_boot_fields) {
        const int index = boot_xram_field_index(address);
        if (index >= 0) {
            static std::array<uint16_t, 65536> seen_pc{};
            const uint16_t bit = static_cast<uint16_t>(1u << index);
            if ((seen_pc[cpu->mPC] & bit) == 0) {
                seen_pc[cpu->mPC] |= bit;
                std::fprintf(stderr,
                             "[BOOT-XRAM-READ] PC=%04X addr=%04X stored=%02X\n",
                             cpu->mPC, address, stored);
            }
        }
    }
    static const bool trace_f891 =
        std::getenv("MA17_TRACE_XRAM_F891") != nullptr;
    if (trace_f891 && address == 0xF891) {
        // SAB80C517 Instruction Set: MOVX A,@Ri uses the P2/XPAGE page.
        // Log each Fiat G consumer once; the 47A2h fault path is only one.
        static std::array<bool, 65536> seen_pc{};
        if (!seen_pc[cpu->mPC]) {
            seen_pc[cpu->mPC] = true;
            std::fprintf(stderr, "[F891-READ] PC=%04X value=%02X\n",
                         cpu->mPC, stored);
        }
        if (cpu->mPC == 0x564A) {
            // LCALL pushes the return low byte then high byte on the 8051 stack.
            // This distinguishes the three callers of the shared index helper.
            const uint8_t sp = cpu->mSFR[REG_SP];
            const auto stack_byte = [cpu](uint8_t offset) -> uint8_t {
                return offset < 0x80 ? cpu->mLowerData[offset]
                                     : (cpu->mUpperData ? cpu->mUpperData[offset - 0x80]
                                                        : 0);
            };
            const uint16_t return_pc = static_cast<uint16_t>(
                (stack_byte(sp) << 8) | stack_byte(static_cast<uint8_t>(sp - 1)));
            static std::array<bool, 65536> seen_return{};
            if (!seen_return[return_pc]) {
                seen_return[return_pc] = true;
                std::fprintf(stderr,
                             "[F891-564A-CALLER] return=%04X value=%02X\n",
                             return_pc, stored);
            }
        }
    }
    static const bool trace_f802 =
        std::getenv("MA17_TRACE_XRAM_F802") != nullptr;
    if (trace_f802 && address == 0xF802) {
        // SAB80C517 Instruction Set: MOVX A,@Ri uses the P2/XPAGE page.
        // Fiat G 461Ch writes this byte after the 708Ah/708Ch interpolation.
        static std::array<bool, 65536> seen_pc{};
        if (!seen_pc[cpu->mPC]) {
            seen_pc[cpu->mPC] = true;
            std::fprintf(stderr, "[F802-READ] PC=%04X value=%02X\n",
                         cpu->mPC, stored);
        }
    }
    static const int override_f891_47a2 = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_XRAM_F891_47A2");
        if (!raw) return -1;
        unsigned int value = 0;
        char extra = 0;
        if (std::strlen(raw) != 2 ||
            std::sscanf(raw, "%2x%c", &value, &extra) != 1) {
            std::fprintf(stderr, "Invalid MA17_OVERRIDE_XRAM_F891_47A2: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    if (address == 0xF891 && cpu->mPC == 0x47A2 &&
        override_f891_47a2 >= 0) {
        // SAB80C517 Instruction Set: MOVX A,@R1 reads the P2/XPAGE page.
        // Fiat G 47A2h alone gets the supplied byte; stored XRAM is intact.
        static int observations = 0;
        if (observations++ < 4)
            std::fprintf(stderr,
                         "[F891-READ-OVERRIDE] PC=47A2 stored=%02X supplied=%02X\n",
                         stored, static_cast<unsigned>(override_f891_47a2));
        return static_cast<uint8_t>(override_f891_47a2);
    }
    static const int override_f891_564a = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_XRAM_F891_564A");
        if (!raw) return -1;
        unsigned int value = 0;
        char extra = 0;
        if (std::strlen(raw) != 2 ||
            std::sscanf(raw, "%2x%c", &value, &extra) != 1) {
            std::fprintf(stderr, "Invalid MA17_OVERRIDE_XRAM_F891_564A: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    static const int override_f891_564a_return = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_XRAM_F891_564A_RETURN");
        if (!raw) return -1;
        unsigned int value = 0;
        char extra = 0;
        if (std::strlen(raw) != 4 ||
            std::sscanf(raw, "%4x%c", &value, &extra) != 1) {
            std::fprintf(stderr,
                         "Invalid MA17_OVERRIDE_XRAM_F891_564A_RETURN: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    if (address == 0xF891 && cpu->mPC == 0x564A &&
        override_f891_564a >= 0) {
        // SAB80C517 Instruction Set: MOVX A,@R0 uses the P2/XPAGE page.
        // Fiat G 564Ah serves three engine-table callers, unlike 47A2h.
        const uint8_t sp = cpu->mSFR[REG_SP];
        const auto stack_byte = [cpu](uint8_t offset) -> uint8_t {
            return offset < 0x80 ? cpu->mLowerData[offset]
                                 : (cpu->mUpperData ? cpu->mUpperData[offset - 0x80]
                                                    : 0);
        };
        const uint16_t return_pc = static_cast<uint16_t>(
            (stack_byte(sp) << 8) | stack_byte(static_cast<uint8_t>(sp - 1)));
        if (override_f891_564a_return >= 0 &&
            return_pc != override_f891_564a_return)
            return stored;
        static int observations = 0;
        if (observations++ < 4)
            std::fprintf(stderr,
                         "[F891-READ-OVERRIDE] PC=564A return=%04X "
                         "stored=%02X supplied=%02X\n",
                         return_pc, stored, static_cast<unsigned>(override_f891_564a));
        return static_cast<uint8_t>(override_f891_564a);
    }
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
    if (masked == trace_xram_address() && previous != value) {
        // SAB80C517 Instruction Set, MOVX @Ri,A uses P2/XPAGE as the
        // high address byte. This logs internal XRAM, not an ECU pin.
        static int observations = 0;
        if (observations++ < 1000)
            std::fprintf(stderr,
                         "[XRAM-ADDRESS-WRITE] tick=%lld PC=%04X "
                         "addr=%04X value=%02X->%02X\n",
                         emulated_ticks, cpu->mPC, masked, previous, value);
    }
    static const bool trace_curve_79c4 =
        std::getenv("MA17_TRACE_CURVE_79C4_WRITE") != nullptr;
    if (trace_curve_79c4 && cpu->mPC == 0x35C2) {
        // SAB80C517 Instruction Set, MOVX @R0,A: the P2/XPAGE latch
        // supplies the high address byte. This records memory, not a pin.
        static int observations = 0;
        if (observations++ < 32)
            std::fprintf(stderr,
                         "[CURVE79C4-WRITE] tick=%lld PC=%04X addr=%04X "
                         "previous=%02X value=%02X\n",
                         emulated_ticks, cpu->mPC, address, previous, value);
    }
    static const bool trace_f8a2 =
        std::getenv("MA17_TRACE_XRAM_F8A2") != nullptr;
    if (trace_f8a2 && masked == 0xF8A2 && previous != value) {
        // SAB80C517 Instruction Set, MOVX @Ri,A: P2 selects the XRAM page.
        static int observations = 0;
        if (observations++ < 1000)
            std::fprintf(stderr,
                         "[F8A2-WRITE] tick=%lld PC=%04X value=%02X->%02X\n",
                         emulated_ticks, cpu->mPC, previous, value);
    }
    static const bool trace_f88e =
        std::getenv("MA17_TRACE_XRAM_F88E") != nullptr;
    if (trace_f88e && masked == 0xF88E && previous != value) {
        // SAB80C517 Instruction Set, MOVX @R0,A uses P2/XPAGE. Fiat G
        // 3E62h..3E7Eh writes this internal field after the 7074h/7076h
        // lookup; this XRAM address is not a processor or ECU output pin.
        static int observations = 0;
        if (observations++ < 1000)
            std::fprintf(stderr,
                         "[F88E-WRITE] tick=%lld PC=%04X value=%02X->%02X\n",
                         emulated_ticks, cpu->mPC, previous, value);
    }
    static const bool trace_f8f2 =
        std::getenv("MA17_TRACE_XRAM_F8F2") != nullptr;
    if (trace_f8f2 && masked == 0xF8F2 && previous != value) {
        // SAB80C517 Instruction Set, MOVX @R0,A uses P2/XPAGE as the
        // high address byte. Fiat G 28A9h looks up 79E5h..79E7h and
        // stores the result here; F8F2h is internal XRAM, not an ECU pin.
        static int observations = 0;
        if (observations++ < 1000)
            std::fprintf(stderr,
                         "[F8F2-WRITE] tick=%lld PC=%04X value=%02X->%02X\n",
                         emulated_ticks, cpu->mPC, previous, value);
    }
    static const bool trace_boot_fields =
        std::getenv("MA17_TRACE_BOOT_XRAM_FIELDS") != nullptr;
    if (trace_boot_fields) {
        const int index = boot_xram_field_index(address);
        if (index >= 0) {
            static std::array<uint16_t, 65536> seen_pc{};
            const uint16_t bit = static_cast<uint16_t>(1u << index);
            if ((seen_pc[cpu->mPC] & bit) == 0) {
                seen_pc[cpu->mPC] |= bit;
                std::fprintf(stderr,
                             "[BOOT-XRAM-WRITE] tick=%lld PC=%04X addr=%04X "
                             "previous=%02X value=%02X\n",
                             emulated_ticks, cpu->mPC, address, previous, value);
            }
        }
    }
    static const bool trace_f802 =
        std::getenv("MA17_TRACE_XRAM_F802") != nullptr;
    if (trace_f802 && masked == 0xF802 && previous != value) {
        // SAB80C517 Instruction Set: MOVX @Ri uses the P2/XPAGE page.
        std::fprintf(stderr,
                     "[F802-WRITE] tick=%lld PC=%04X value=%02X->%02X\n",
                     emulated_ticks, cpu->mPC, previous, value);
    }
    static const bool trace_f87f_table =
        std::getenv("MA17_TRACE_XRAM_F87F") != nullptr;
    if (trace_f87f_table && masked == 0xF87F) {
        // SAB80C517 Instruction Set, MOVX @R1: P2 supplies the page.
        // Fiat G PC3E50h writes this XRAM byte after the 7036h lookup;
        // XRAM F8:7Fh is internal state, not an ECU output pin.
        static int observations = 0;
        if (observations++ < 512)
            std::fprintf(stderr,
                         "[F87F-TABLE-WRITE] tick=%lld PC=%04X "
                         "previous=%02X value=%02X\n",
                         emulated_ticks, cpu->mPC, previous, value);
    }
    static const bool trace_f891 =
        std::getenv("MA17_TRACE_XRAM_F891") != nullptr;
    if (trace_f891 && masked == 0xF891 && previous != value) {
        // SAB80C517 Instruction Set: MOVX @Ri uses the P2/XPAGE page.
        // Fiat G PC4608h writes this byte before the conditional 47A2h read.
        std::fprintf(stderr,
                     "[F891-WRITE] tick=%lld PC=%04X value=%02X->%02X\n",
                     emulated_ticks, cpu->mPC, previous, value);
    }
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
