#include "ma17/EmulatorLoop.hpp"

#include "CrankshaftSimulator.hpp"
#include "ma17/AdcSimulator.hpp"
#include "ma17/CrankInput.hpp"
#include "ma17/ExecutionTracer.hpp"
#include "ma17/FiveBaudInjector.hpp"
#include "ma17/PtyBridge.hpp"
#include "ma17/UartScheduler.hpp"

extern "C" {
#include "emu8051.h"
#include <time.h>
}

#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <tuple>
#include <vector>

namespace ma17 {

using MovcKey = std::tuple<uint16_t, uint8_t, uint16_t, uint8_t,
                           uint16_t, uint16_t, uint8_t>;
using MovcCounts = std::map<MovcKey, unsigned long long>;
using MovcBucketCounts = std::map<std::pair<uint64_t, uint16_t>,
                                  unsigned long long>;
using LookupKey = std::tuple<uint8_t, uint8_t, uint8_t, uint8_t, uint8_t,
                             uint8_t, uint8_t, uint8_t, uint8_t, uint8_t>;
using LookupCounts = std::map<LookupKey, unsigned long long>;
static MovcCounts *movc_counts = nullptr;
static MovcBucketCounts *movc_bucket_counts = nullptr;
static uint64_t movc_bucket_ticks = 0;
static uint64_t movc_tick = 0;
static em8051operation original_movc_pc = nullptr;
static em8051operation original_movc_dptr = nullptr;
static std::array<em8051operation, 256> original_indirect_reads{};
using IndirectReadKey = std::tuple<uint16_t, uint8_t, uint8_t>;
using IndirectReadCounts = std::map<IndirectReadKey,
                                    std::pair<unsigned long long, uint64_t>>;
static IndirectReadCounts *indirect_read_counts = nullptr;
static int indirect_read_address = -1;

static uint8_t trace_indirect_read(em8051 *cpu) {
    const uint16_t pc = cpu->mPC;
    const uint8_t opcode = cpu->mCodeMem[pc & cpu->mCodeMemMaxIdx];
    const uint8_t bank = cpu->mSFR[REG_PSW] & 0x18u;
    // SAB80C517 Instruction Set: @R0/@R1 and stack POP/RET/RETI read
    // indirect RAM; 80h..FFh select upper IRAM, not SFR space.
    const bool stack_read = opcode == 0x22 || opcode == 0x32 || opcode == 0xD0;
    const uint8_t address = stack_read ? cpu->mSFR[REG_SP]
                                       : cpu->mLowerData[bank + (opcode & 1u)];
    const int count = opcode == 0x22 || opcode == 0x32 ? 2 : 1;
    for (int index = 0; index < count; ++index) {
        const uint8_t effective = static_cast<uint8_t>(address - index);
        if (effective == indirect_read_address) {
            auto &sample = (*indirect_read_counts)[
                {pc, opcode, cpu->mUpperData[effective - 0x80u]}];
            if (sample.first == 0) sample.second = movc_tick;
            ++sample.first;
        }
    }
    return original_indirect_reads[opcode](cpu);
}

struct MatrixDonor {
    int base = -1;
    int size = 0;
    std::array<uint8_t, 0x8000> bytes{};
};

struct MovcValueOverride {
    int pc = -1;
    uint16_t address = 0;
    uint8_t value = 0;
    bool announced = false;
};

static uint8_t trace_movc(em8051 *cpu, uint8_t opcode,
                          em8051operation original) {
    const uint16_t pc = cpu->mPC;
    const uint8_t acc = cpu->mSFR[REG_ACC];
    const uint16_t dptr = uint16_t((uint16_t(cpu->mSFR[REG_DPH]) << 8) |
                                   cpu->mSFR[REG_DPL]);
    const uint16_t address = opcode == 0x83 ? uint16_t(pc + 1 + acc)
                                             : uint16_t(dptr + acc);
    const uint16_t mapped = address & cpu->mCodeMemMaxIdx;
    const uint8_t delay = original(cpu);
    const uint8_t value = cpu->mSFR[REG_ACC];
    ++(*movc_counts)[{pc, opcode, dptr, acc, address, mapped, value}];
    if (movc_bucket_counts) {
        const uint64_t start = movc_tick / movc_bucket_ticks * movc_bucket_ticks;
        ++(*movc_bucket_counts)[{start, mapped}];
    }
    static const int forced_7b45 = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_MOVC_7B45");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long parsed = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || parsed > 0xFF) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_MOVC_7B45: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(parsed);
    }();
    static const int forced_7580 = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_MOVC_7580");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long parsed = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || parsed > 0xFF) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_MOVC_7580: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(parsed);
    }();
    static const int delta_7581 = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_MOVC_7581_DELTA");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long parsed = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || parsed > 0xFF) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_MOVC_7581_DELTA: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(parsed);
    }();
    static const int delta_7100 = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_MOVC_7100_DELTA");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long parsed = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || parsed > 0xFF) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_MOVC_7100_DELTA: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(parsed);
    }();
    static const MatrixDonor matrix_donor = [] {
        MatrixDonor donor;
        const char *path = std::getenv("MA17_OVERRIDE_MOVC_MATRIX_ROM");
        const char *base = std::getenv("MA17_OVERRIDE_MOVC_MATRIX_BASE");
        if (!path && !base) return donor;
        if (!path || !base) {
            fprintf(stderr, "Matrix donor requires ROM and BASE\n");
            std::exit(2);
        }
        char *end = nullptr;
        const unsigned long parsed = std::strtoul(base, &end, 16);
        if (end == base || *end != '\0' ||
            (parsed != 0x743A && parsed != 0x7444 &&
             parsed != 0x744E && parsed != 0x7462 &&
             parsed != 0x746C && parsed != 0x752A && parsed != 0x753E &&
             parsed != 0x7581 && parsed != 0x7662 &&
             parsed != 0x7743 &&
             parsed != 0x7895 && parsed != 0x78BD && parsed != 0x7925 &&
             parsed != 0x7939 && parsed != 0x7B46 &&
             parsed != 0x7BBE && parsed != 0x7C36 &&
             parsed != 0x7CAE && parsed != 0x7D26 && parsed != 0x7D9E &&
             parsed != 0x7E16 &&
             parsed != 0x7ED9 && parsed != 0x7F15 && parsed != 0x7F51)) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_MOVC_MATRIX_BASE: %s\n", base);
            std::exit(2);
        }
        FILE *input = std::fopen(path, "rb");
        if (!input || std::fread(donor.bytes.data(), 1, donor.bytes.size(), input)
                          != donor.bytes.size() || std::fgetc(input) != EOF) {
            fprintf(stderr, "Matrix donor must be a readable 32768-byte ROM: %s\n",
                    path);
            if (input) std::fclose(input);
            std::exit(2);
        }
        std::fclose(input);
        donor.base = static_cast<int>(parsed);
        // SAB80C517 Instruction Set, p. 222: the following MOVC result
        // substitution covers one pointer-verified ROM table at a time.
        donor.size = (parsed == 0x743A || parsed == 0x7444 ||
                      parsed == 0x744E || parsed == 0x7462 ||
                      parsed == 0x746C || parsed == 0x752A ||
                      parsed == 0x753E) ? 10 :
                     (parsed == 0x7895 || parsed == 0x78BD ||
                      parsed == 0x7925 || parsed == 0x7939) ? 20 :
                     (parsed == 0x7B46 || parsed == 0x7BBE ||
                      parsed == 0x7C36 || parsed == 0x7E16 ||
                      (parsed >= 0x7CAE && parsed <= 0x7D9E)) ? 120 :
                     (parsed < 0x7ED9 ? 225 : 60);
        return donor;
    }();
    static std::vector<MovcValueOverride> point_overrides = [] {
        std::vector<MovcValueOverride> settings;
        const char *raw = std::getenv("MA17_OVERRIDE_MOVC_AT");
        if (!raw) return settings;
        const char *hex = "0123456789abcdefABCDEF";
        const std::size_t length = std::strlen(raw);
        if (!length || (length + 1) % 13 != 0) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_MOVC_AT; expected "
                    "PC:ADDRESS:VALUE[,PC:ADDRESS:VALUE...] in hex\n");
            std::exit(2);
        }
        for (std::size_t pos = 0; pos < length; pos += 13) {
            if ((pos && raw[pos - 1] != ',') || raw[pos + 4] != ':' ||
                raw[pos + 9] != ':' || std::strspn(raw + pos, hex) != 4 ||
                std::strspn(raw + pos + 5, hex) != 4 ||
                std::strspn(raw + pos + 10, hex) != 2) {
                fprintf(stderr, "Invalid MA17_OVERRIDE_MOVC_AT entry\n");
                std::exit(2);
            }
            MovcValueOverride setting;
            setting.pc = static_cast<int>(std::strtoul(raw + pos, nullptr, 16));
            setting.address = static_cast<uint16_t>(
                std::strtoul(raw + pos + 5, nullptr, 16));
            setting.value = static_cast<uint8_t>(
                std::strtoul(raw + pos + 10, nullptr, 16));
            const auto duplicate = std::find_if(settings.begin(), settings.end(),
                [&](const auto &other) {
                    return other.pc == setting.pc &&
                           other.address == setting.address;
                });
            if (duplicate != settings.end()) {
                fprintf(stderr, "Duplicate MA17_OVERRIDE_MOVC_AT entry\n");
                std::exit(2);
            }
            settings.push_back(setting);
        }
        return settings;
    }();
    if (forced_7b45 >= 0 && pc == 0x5289 && mapped == 0x7B45) {
        // SAB 80C517 Instruction Set, p. 222: MOVC returns the code
        // byte in A. This experiment substitutes A, not the ROM byte.
        static bool announced = false;
        if (!announced) {
            fprintf(stderr, "[MOVC-OVERRIDE] PC=5289 mapped=7B45 "
                    "original=%02X supplied=%02X\n", value,
                    static_cast<unsigned>(forced_7b45));
            announced = true;
        }
        cpu->mSFR[REG_ACC] = static_cast<uint8_t>(forced_7b45);
    }
    if (forced_7580 >= 0 && pc == 0x5289 && mapped == 0x7580) {
        // SAB 80C517 Instruction Set, p. 222: substitute the MOVC
        // result in A while leaving code memory and raw trace intact.
        static bool announced = false;
        if (!announced) {
            fprintf(stderr, "[MOVC-OVERRIDE] PC=5289 mapped=7580 "
                    "original=%02X supplied=%02X\n", value,
                    static_cast<unsigned>(forced_7580));
            announced = true;
        }
        cpu->mSFR[REG_ACC] = static_cast<uint8_t>(forced_7580);
    }
    if (delta_7581 >= 0 && pc >= 0x532F && pc <= 0x5350 &&
        mapped >= 0x7581 && mapped < 0x7662) {
        // SAB80C517 Instruction Set, p. 222: MOVC returns a code byte in A.
        // Substitute the matrix result only; the ROM and raw trace stay intact.
        static bool announced = false;
        if (!announced) {
            fprintf(stderr, "[MOVC-OVERRIDE] matrix=7581..7661 delta=%02X\n",
                    static_cast<unsigned>(delta_7581));
            announced = true;
        }
        cpu->mSFR[REG_ACC] = static_cast<uint8_t>(value + delta_7581);
    }
    if (delta_7100 >= 0 && (pc == 0x532F || pc == 0x5333) &&
        mapped >= 0x7100 && mapped < 0x7109) {
        // SAB80C517A Instruction Set, MOVC A,@A+DPTR: intervene on the
        // returned calibration byte, leaving the original ROM unchanged.
        static bool announced = false;
        if (!announced) {
            fprintf(stderr, "[MOVC-OVERRIDE] table=7100..7108 delta=%02X\n",
                    static_cast<unsigned>(delta_7100));
            announced = true;
        }
        cpu->mSFR[REG_ACC] = static_cast<uint8_t>(value + delta_7100);
    }
    if (matrix_donor.base >= 0 &&
        ((pc >= 0x532F && pc <= 0x5350) ||
         (matrix_donor.base == 0x746C && pc == 0x499F)) &&
        mapped >= matrix_donor.base &&
        mapped < matrix_donor.base + matrix_donor.size) {
        // SAB80C517 Instruction Set, MOVC: replace the returned A byte;
        // code memory and the raw MOVC trace retain the original ROM.
        static bool announced = false;
        if (!announced) {
            fprintf(stderr, "[MOVC-OVERRIDE] matrix=%04X..%04X donor-ROM\n",
                    static_cast<unsigned>(matrix_donor.base),
                    static_cast<unsigned>(matrix_donor.base + matrix_donor.size - 1));
            announced = true;
        }
        cpu->mSFR[REG_ACC] = matrix_donor.bytes[mapped];
    }
    for (auto &setting : point_overrides) {
        if (setting.pc == pc && setting.address == mapped) {
            // SAB80C517 Instruction Set, MOVC A,@A+DPTR: replace A only;
            // code memory and raw MOVC observations retain the ROM byte.
            if (!setting.announced) {
                fprintf(stderr, "[MOVC-OVERRIDE] PC=%04X mapped=%04X "
                        "original=%02X supplied=%02X\n", pc, mapped,
                        value, setting.value);
                setting.announced = true;
            }
            cpu->mSFR[REG_ACC] = setting.value;
        }
    }
    return delay;
}

static uint8_t trace_movc_pc(em8051 *cpu) {
    return trace_movc(cpu, 0x83, original_movc_pc);
}

static uint8_t trace_movc_dptr(em8051 *cpu) {
    return trace_movc(cpu, 0x93, original_movc_dptr);
}

static void run_tick_batch(EmulatorLoopContext &context,
                           std::array<uint8_t, 0x8000> &pc_seen,
                           uint16_t &last_pc, long long stop_ticks,
                           LookupCounts *lookup_counts) {
    em8051 &cpu = context.cpu;
    static const int forced_ram5b_read = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_RAM5B_READ");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long value = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || end - raw != 2 || value > 0xFF) {
            std::fprintf(stderr, "Invalid MA17_OVERRIDE_RAM5B_READ: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    static const int forced_ram6e_read = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_RAM6E_READ");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long value = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || end - raw != 2 || value > 0xFF) {
            std::fprintf(stderr, "Invalid MA17_OVERRIDE_RAM6E_READ: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    static const std::vector<std::array<int, 3>> forced_iram_reads = [] {
        std::vector<std::array<int, 3>> settings;
        const char *raw = std::getenv("MA17_OVERRIDE_IRAM_READ_AT");
        if (!raw) return settings;
        const char *hex = "0123456789abcdefABCDEF";
        const std::size_t length = std::strlen(raw);
        if (!length || (length + 1) % 11 != 0) {
            std::fprintf(stderr, "MA17_OVERRIDE_IRAM_READ_AT expects "
                                 "PC:ADDRESS:VALUE[,PC:ADDRESS:VALUE...] in hex\n");
            std::exit(2);
        }
        for (std::size_t pos = 0; pos < length; pos += 11) {
            if ((pos && raw[pos - 1] != ',') || raw[pos + 4] != ':' ||
                raw[pos + 7] != ':' || std::strspn(raw + pos, hex) != 4 ||
                std::strspn(raw + pos + 5, hex) != 2 ||
                std::strspn(raw + pos + 8, hex) != 2) {
                std::fprintf(stderr, "Invalid MA17_OVERRIDE_IRAM_READ_AT entry\n");
                std::exit(2);
            }
            std::array<int, 3> setting{
                static_cast<int>(std::strtoul(raw + pos, nullptr, 16)),
                static_cast<int>(std::strtoul(raw + pos + 5, nullptr, 16)),
                static_cast<int>(std::strtoul(raw + pos + 8, nullptr, 16))};
            if (std::any_of(settings.begin(), settings.end(),
                            [&](const auto &other) { return other[0] == setting[0]; })) {
                std::fprintf(stderr, "Duplicate MA17_OVERRIDE_IRAM_READ_AT PC\n");
                std::exit(2);
            }
            settings.push_back(setting);
        }
        return settings;
    }();
    for (const auto &setting : forced_iram_reads) {
        const uint8_t opcode = cpu.mCodeMem[setting[0] & cpu.mCodeMemMaxIdx];
        if (setting[1] >= 0x80 ||
            (opcode != 0xE5 && opcode != 0x95 &&
             !(opcode >= 0xA8 && opcode <= 0xAF && setting[1] >= 0x20)) ||
            cpu.mCodeMem[(setting[0] + 1) & cpu.mCodeMemMaxIdx] != setting[1]) {
            std::fprintf(stderr, "MA17_OVERRIDE_IRAM_READ_AT requires "
                                 "MOV A/Rn,direct or SUBB A,direct "
                                 "from lower IRAM\n");
            std::exit(2);
        }
    }
    static const bool clear_ram2c_bit7_at_1840 = [] {
        const char *raw = std::getenv("MA17_CLEAR_RAM2C_BIT7_ONCE_AT_1840");
        if (!raw) return false;
        if (raw[0] != '1' || raw[1] != '\0') {
            std::fprintf(stderr, "MA17_CLEAR_RAM2C_BIT7_ONCE_AT_1840 must be 1\n");
            std::exit(2);
        }
        return true;
    }();
    if (clear_ram2c_bit7_at_1840 &&
        (cpu.mCodeMem[0x1840 & cpu.mCodeMemMaxIdx] != 0x30 ||
         cpu.mCodeMem[0x1841 & cpu.mCodeMemMaxIdx] != 0x67 ||
         cpu.mCodeMem[0x1842 & cpu.mCodeMemMaxIdx] != 0x08)) {
        std::fprintf(stderr, "MA17_CLEAR_RAM2C_BIT7_ONCE_AT_1840 requires "
                             "Fiat JNB 2Ch.7,184Bh at 1840h\n");
        std::exit(2);
    }
    if (forced_ram5b_read >= 0 &&
        (cpu.mCodeMem[0x1866 & cpu.mCodeMemMaxIdx] != 0xE5 ||
         cpu.mCodeMem[0x1867 & cpu.mCodeMemMaxIdx] != 0x5B)) {
        std::fprintf(stderr, "MA17_OVERRIDE_RAM5B_READ requires Fiat "
                             "MOV A,5Bh at 1866h\n");
        std::exit(2);
    }
    if (forced_ram6e_read >= 0 &&
        (cpu.mCodeMem[0x1773 & cpu.mCodeMemMaxIdx] != 0xAC ||
         cpu.mCodeMem[0x1774 & cpu.mCodeMemMaxIdx] != 0x6E)) {
        std::fprintf(stderr, "MA17_OVERRIDE_RAM6E_READ requires Fiat "
                             "MOV R4,6Eh at 1773h\n");
        std::exit(2);
    }
    static bool ram2c_gate_used = false;
    static const unsigned long long forced_iram_read_after_tick = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_IRAM_READ_AFTER_TICK");
        if (!raw) return 0ULL;
        char *end = nullptr;
        const unsigned long long value = std::strtoull(raw, &end, 10);
        if (end == raw || *end != '\0') {
            std::fprintf(stderr, "Invalid MA17_OVERRIDE_IRAM_READ_AFTER_TICK: %s\n",
                         raw);
            std::exit(2);
        }
        return value;
    }();
    static const std::array<unsigned long long, 2> pc_window = [] {
        const char *raw = std::getenv("MA17_TRACE_PC_WINDOW");
        if (!raw) return std::array<unsigned long long, 2>{1, 0};
        char *separator = nullptr;
        const unsigned long long first = std::strtoull(raw, &separator, 10);
        char *end = nullptr;
        const unsigned long long last = separator && *separator == ':'
            ? std::strtoull(separator + 1, &end, 10) : 0;
        if (separator == raw || !separator || *separator != ':' ||
            end == separator + 1 || !end || *end != '\0' ||
            last < first || last - first > 1000) {
            std::fprintf(stderr, "MA17_TRACE_PC_WINDOW expects START:END "
                                 "within 1000 ticks\n");
            std::exit(2);
        }
        return std::array<unsigned long long, 2>{first, last};
    }();
    for (int i = 0; i < context.steps_per_batch &&
                    (!stop_ticks || context.ticks < stop_ticks); ++i) {
        context.ticks++; // One count per emulated machine-cycle tick.
        movc_tick = static_cast<uint64_t>(context.ticks);
        set_adc_tick(static_cast<uint64_t>(context.ticks));
        tick_crank_input(&cpu, context.ticks, context.crank);
        apply_pre_tick_experiments(cpu);
        if (static_cast<unsigned long long>(context.ticks) >= pc_window[0] &&
            static_cast<unsigned long long>(context.ticks) <= pc_window[1]) {
            // SAB80C517 interrupt vectors: record foreground and ISR PCs
            // without changing interrupt state or instruction timing.
            std::fprintf(stderr, "[PC-WINDOW] tick=%lld PC=%04X PSW=%02X "
                                 "TCON=%02X\n", context.ticks, cpu.mPC,
                         cpu.mSFR[0xD0 - 0x80], cpu.mSFR[0x88 - 0x80]);
        }
        if (context.trace_pc && cpu.mPC < pc_seen.size())
            pc_seen[cpu.mPC] = 1;
        if (context.trace_pc) {
            trace_pre_tick_boot_and_crank(cpu, context.ticks,
                                          context.crank.enabled);
            trace_pre_tick_engine(cpu, context.ticks);
            trace_pre_tick_cc3(cpu, context.ticks);
        }
        if (lookup_counts && cpu.mPC == 0x137B) {
            const uint8_t bank = cpu.mSFR[REG_PSW] & 0x18;
            ++(*lookup_counts)[{cpu.mLowerData[0x47], cpu.mLowerData[0x6F],
                                cpu.mLowerData[0x57], cpu.mLowerData[0x2E],
                                cpu.mLowerData[bank], cpu.mLowerData[bank + 4],
                                cpu.mLowerData[bank + 5], cpu.mLowerData[bank + 6],
                                cpu.mSFR[REG_ACC], cpu.mSFR[REG_B]}];
        }

        trace_invalid_pc(cpu, last_pc);
        last_pc = cpu.mPC;
        const uint16_t timer2_before = static_cast<uint16_t>(
            (uint16_t(cpu.mSFR[0xCD - 0x80]) << 8) | cpu.mSFR[0xCC - 0x80]);
        // SAB80C517 User's Manual, Instruction Set: Fiat 1866h is
        // MOV A,5Bh (E5 5B). Restore RAM after that single read.
        const bool override_ram5b = forced_ram5b_read >= 0 && cpu.mPC == 0x1866;
        const uint8_t saved_ram5b = cpu.mLowerData[0x5B];
        const bool override_ram6e = forced_ram6e_read >= 0 &&
            cpu.mPC == 0x1773 &&
            (cpu.mLowerData[0x5C] || cpu.mLowerData[0x5D]);
        const uint8_t saved_ram6e = cpu.mLowerData[0x6E];
        const auto iram_setting = std::find_if(
            forced_iram_reads.begin(), forced_iram_reads.end(),
            [&](const auto &setting) { return cpu.mPC == setting[0]; });
        const bool override_iram_read = iram_setting != forced_iram_reads.end() &&
            context.ticks >= 0 &&
            static_cast<unsigned long long>(context.ticks) >=
                forced_iram_read_after_tick;
        const uint8_t saved_iram_read = override_iram_read
            ? cpu.mLowerData[(*iram_setting)[1]] : 0;
        const uint8_t bank = cpu.mSFR[REG_PSW] & 0x18u;
        const bool override_ram2c = clear_ram2c_bit7_at_1840 &&
            !ram2c_gate_used &&
            cpu.mPC == 0x1840 && (cpu.mLowerData[0x2C] & 0x80u) &&
            (cpu.mLowerData[bank + 6] || cpu.mLowerData[bank + 7]);
        const uint8_t saved_ram2c = cpu.mLowerData[0x2C];
        if (override_ram2c) {
            // SAB80C517 Instruction Set: JNB reads bit 67h (IRAM 2Ch.7).
            // Restore the byte immediately after this original instruction.
            std::fprintf(stderr, "[RAM2C-BIT7-GATE] PC=1840 original=%02X "
                                 "R7:R6=%02X%02X\n", saved_ram2c,
                         cpu.mLowerData[bank + 7], cpu.mLowerData[bank + 6]);
            cpu.mLowerData[0x2C] &= 0x7Fu;
            ram2c_gate_used = true;
        }
        if (override_ram5b) {
            std::fprintf(stderr,
                         "[RAM5B-READ-OVERRIDE] PC=1866 original=%02X supplied=%02X\n",
                         saved_ram5b, static_cast<unsigned>(forced_ram5b_read));
            cpu.mLowerData[0x5B] = static_cast<uint8_t>(forced_ram5b_read);
        }
        if (override_ram6e) {
            // SAB80C517 Instruction Set: AC 6E reads lower IRAM 6Eh
            // into banked R4; restore the source after this instruction.
            static int announced = 0;
            if (announced++ < 8)
                std::fprintf(stderr, "[RAM6E-READ-OVERRIDE] PC=1773 "
                                     "original=%02X supplied=%02X\n",
                             saved_ram6e, static_cast<unsigned>(forced_ram6e_read));
            cpu.mLowerData[0x6E] = static_cast<uint8_t>(forced_ram6e_read);
        }
        if (override_iram_read) {
            // SAB80C517.PDF, Instruction Set: MOV A/Rn,direct and
            // SUBB A,direct read lower IRAM; restore after this opcode.
            static int announced = 0;
            if (announced++ < 8)
                std::fprintf(stderr,
                             "[IRAM-READ-OVERRIDE] PC=%04X addr=%02X "
                             "stored=%02X supplied=%02X\n",
                             static_cast<unsigned>((*iram_setting)[0]),
                             static_cast<unsigned>((*iram_setting)[1]),
                             saved_iram_read,
                             static_cast<unsigned>((*iram_setting)[2]));
            cpu.mLowerData[(*iram_setting)[1]] =
                static_cast<uint8_t>((*iram_setting)[2]);
        }
        tick(&cpu);
        if (override_iram_read)
            cpu.mLowerData[(*iram_setting)[1]] = saved_iram_read;
        if (override_ram5b) cpu.mLowerData[0x5B] = saved_ram5b;
        if (override_ram6e) cpu.mLowerData[0x6E] = saved_ram6e;
        if (override_ram2c) cpu.mLowerData[0x2C] = saved_ram2c;

        if (context.trace_pc) {
            trace_cc3_and_ram67(cpu, context.ticks, last_pc, timer2_before);
            trace_memory_changes(cpu, context.ticks, last_pc);
        }
        trace_p13_shadow(cpu, context.ticks, last_pc);
        if (context.trace_pc)
            trace_port_edges(cpu, context.ticks, last_pc);

        context.uart.tick(&cpu, context.ticks);
        trace_isr_vector(cpu);
        trace_timer0_stall(cpu);
        trace_kline_decoder(cpu, context.ticks);
        trace_rpm_state(cpu, context.trace_pc);
        trace_reset_watchdog(cpu);
        trace_stack_range(cpu);
    }
}

void run_emulator_loop(EmulatorLoopContext &context) {
    em8051 &cpu = context.cpu;
    uint16_t last_pc = cpu.mPC;
    std::array<uint8_t, 0x8000> pc_seen{};
    MovcCounts local_movc_counts;
    MovcBucketCounts local_movc_bucket_counts;
    LookupCounts lookup_counts;
    IndirectReadCounts local_indirect_read_counts;
    const bool trace_movc_enabled = std::getenv("MA17_TRACE_MOVC") != nullptr;
    if (const char *setting = std::getenv("MA17_TRACE_INDIRECT_IRAM_ADDRESS")) {
        char *end = nullptr;
        errno = 0;
        const unsigned long parsed = std::strtoul(setting, &end, 16);
        if (end == setting || *end != '\0' || errno || parsed < 0x80 ||
            parsed > 0xFF || !cpu.mUpperData) {
            fprintf(stderr, "Invalid MA17_TRACE_INDIRECT_IRAM_ADDRESS=%s; "
                            "expected upper IRAM hex address 80..FF\n", setting);
            std::exit(2);
        }
        indirect_read_address = static_cast<int>(parsed);
        indirect_read_counts = &local_indirect_read_counts;
        // Matched against every read_mem_indir caller in emu8051/opcodes.c.
        constexpr std::array<uint8_t, 13> bases{
            0x06, 0x16, 0x26, 0x36, 0x46, 0x56, 0x66,
            0x86, 0x96, 0xB6, 0xC6, 0xD6, 0xE6};
        for (const uint8_t base : bases) {
            for (uint8_t opcode = base; opcode <= base + 1; ++opcode) {
                original_indirect_reads[opcode] = cpu.op[opcode];
                cpu.op[opcode] = &trace_indirect_read;
            }
        }
        for (const uint8_t opcode : {uint8_t{0x22}, uint8_t{0x32},
                                     uint8_t{0xD0}}) {
            original_indirect_reads[opcode] = cpu.op[opcode];
            cpu.op[opcode] = &trace_indirect_read;
        }
    }
    if (const char *setting = std::getenv("MA17_MOVC_BUCKET_TICKS")) {
        char *end = nullptr;
        errno = 0;
        const unsigned long long parsed = std::strtoull(setting, &end, 10);
        if (!trace_movc_enabled || !*setting || *end != '\0' || errno ||
            parsed == 0 || !std::all_of(setting, static_cast<const char *>(end),
                                      [](char digit) {
                return digit >= '0' && digit <= '9';
            })) {
            fprintf(stderr, "Invalid MA17_MOVC_BUCKET_TICKS=%s; requires "
                    "MA17_TRACE_MOVC and a positive tick count\n", setting);
            std::exit(2);
        }
        movc_bucket_ticks = static_cast<uint64_t>(parsed);
        movc_bucket_counts = &local_movc_bucket_counts;
    }
    if ((std::getenv("MA17_OVERRIDE_MOVC_7B45") ||
         std::getenv("MA17_OVERRIDE_MOVC_7580") ||
         std::getenv("MA17_OVERRIDE_MOVC_7581_DELTA") ||
         std::getenv("MA17_OVERRIDE_MOVC_7100_DELTA") ||
         std::getenv("MA17_OVERRIDE_MOVC_AT")) && !trace_movc_enabled) {
        fprintf(stderr, "MOVC override requires MA17_TRACE_MOVC\n");
        std::exit(2);
    }
    const bool trace_lookup_enabled = std::getenv("MA17_TRACE_LOOKUP") != nullptr;
    long long stop_ticks = 0;
    if (const char *setting = std::getenv("MA17_STOP_TICKS")) {
        char *end = nullptr;
        errno = 0;
        const long long parsed = std::strtoll(setting, &end, 10);
        if (*setting && *end == '\0' && errno == 0 && parsed > 0)
            stop_ticks = parsed;
        else
            fprintf(stderr, "[TRACE-STOP] invalid MA17_STOP_TICKS=%s\n", setting);
    }
    if (trace_movc_enabled) {
        original_movc_pc = cpu.op[0x83];
        original_movc_dptr = cpu.op[0x93];
        movc_counts = &local_movc_counts;
        cpu.op[0x83] = &trace_movc_pc;
        cpu.op[0x93] = &trace_movc_dptr;
    }
    struct timespec ts {
        0, 407000
    };

    context.uart.bind_cpu(&cpu);
    while (context.running.load()) {
        const auto loop_start = std::chrono::steady_clock::now();
        if (context.inject_5baud.load()) {
            context.inject_5baud = false;
            fprintf(stderr, "\n[SIGUSR1] Received - starting 5-baud injection "
                            "(non-blocking)\n");
            fflush(stderr);
            context.slow_init.start(context.ticks);
        }

        context.slow_init.tick(context.ticks);
        if (context.crank.check_and_enable(context.ticks)) {
            fprintf(stderr,
                    "\n[CRANKSHAFT] *** Startup delay complete - "
                    "Beginning pulse injection @ %d RPM ***\n\n",
                    context.crank.target_rpm);
            fflush(stderr);
        }

        run_tick_batch(context, pc_seen, last_pc, stop_ticks,
                       trace_lookup_enabled ? &lookup_counts : nullptr);
        context.bridge.read_and_process();
        trace_performance(cpu, context.ticks, context.startup_time);
        if (stop_ticks && context.ticks >= stop_ticks) {
            fprintf(stderr, "[TRACE-STOP] ticks=%lld\n", context.ticks);
            context.running.store(false);
            break;
        }

        const auto elapsed_ns =
            std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::steady_clock::now() - loop_start);
        const auto sleep_ns = (context.batch_duration - elapsed_ns) -
                              std::chrono::nanoseconds(41200);
        if (sleep_ns.count() > 0) {
            ts.tv_sec = 0;
            ts.tv_nsec = sleep_ns.count();
            nanosleep(&ts, nullptr);
        }
    }

    if (context.trace_pc) {
        for (size_t pc = 0; pc < pc_seen.size(); ++pc) {
            if (pc_seen[pc])
                fprintf(stderr, "[PC-HIT] %04zX\n", pc);
        }
        fprintf(stderr,
                "[PC-COVERAGE] unique=%zu reset=%u timer0=%u "
                "kline=%u collection=%u table_copy=%u serial=%u adc=%u\n",
                static_cast<size_t>(
                    std::count(pc_seen.begin(), pc_seen.end(), uint8_t{1})),
                pc_seen[0x0850], pc_seen[0x000B], pc_seen[0x4AD1],
                pc_seen[0x4E67], pc_seen[0x4EAF], pc_seen[0x61D8],
                pc_seen[0x6441]);
    }
    if (trace_movc_enabled) {
        cpu.op[0x83] = original_movc_pc;
        cpu.op[0x93] = original_movc_dptr;
        movc_counts = nullptr;
        for (const auto &[key, count] : local_movc_counts) {
            const auto &[pc, opcode, dptr, acc, address, mapped, value] = key;
            fprintf(stderr,
                    "[MOVC-SUMMARY] pc=%04X opcode=%02X dptr=%04X acc=%02X "
                    "address=%04X mapped=%04X value=%02X count=%llu\n",
                    pc, opcode, dptr, acc, address, mapped, value, count);
        }
        for (const auto &[key, count] : local_movc_bucket_counts) {
            fprintf(stderr, "[MOVC-BUCKET] start=%llu address=%04X "
                    "count=%llu\n", static_cast<unsigned long long>(key.first),
                    key.second, count);
        }
        movc_bucket_counts = nullptr;
    }
    if (trace_lookup_enabled) {
        for (const auto &[key, count] : lookup_counts) {
            const auto &[rpm, load, selector, flags, r0, r4, r5, r6,
                         result_a, result_b] = key;
            fprintf(stderr,
                    "[LOOKUP-SUMMARY] rpm=%02X load=%02X selector=%02X "
                    "flags=%02X r0=%02X r4=%02X r5=%02X r6=%02X "
                    "result_a=%02X result_b=%02X count=%llu\n",
                    rpm, load, selector, flags, r0, r4, r5, r6,
                    result_a, result_b, count);
        }
    }
    if (indirect_read_counts) {
        for (const auto &[key, sample] : local_indirect_read_counts) {
            const auto &[pc, opcode, value] = key;
            fprintf(stderr, "[INDIRECT-IRAM-READ] pc=%04X opcode=%02X "
                            "address=%02X value=%02X count=%llu first_tick=%llu\n",
                    pc, opcode, static_cast<unsigned>(indirect_read_address),
                    value, sample.first,
                    static_cast<unsigned long long>(sample.second));
        }
        for (size_t opcode = 0; opcode < original_indirect_reads.size(); ++opcode)
            if (original_indirect_reads[opcode])
                cpu.op[opcode] = original_indirect_reads[opcode];
        indirect_read_counts = nullptr;
    }
}

} // namespace ma17
