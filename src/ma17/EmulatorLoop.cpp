#include "ma17/EmulatorLoop.hpp"

#include "CrankshaftSimulator.hpp"
#include "ma17/AdcSimulator.hpp"
#include "ma17/CrankInput.hpp"
#include "engine/CrankDynamics.hpp"
#include "engine/Drivetrain.hpp"
#include "engine/ThrottleAssembly.hpp"
#include "engine/ThermalState.hpp"
#include "ecu_hw/Ma17TpsCircuit.hpp"
#include "ecu_hw/Ma17SensorCircuit.hpp"
#include "ecu_hw/Ma17InjectorStage.hpp"
#include "engine/IntakeFuel.hpp"
#include "engine/physics/Losses.hpp"
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
// Diagnostic switch read once (never per tick): finer plant windows, one line each.
static bool fine_plant_windows() {
    static const bool enabled = std::getenv("SEVEL_PLANT_WINDOW_CYCLES") != nullptr;
    return enabled;
}

static void print_plant_line(const EmulatorLoopContext &context) {
    const auto &w = context.plant_window.last();
            fprintf(stdout,
                    "{\"type\":\"plant\",\"tick\":%lld,\"rpm\":%.1f,"
                    "\"indicated_nm\":%.3f,\"friction_nm\":%.3f,"
                    "\"pumping_nm\":%.3f,\"accessory_nm\":%.3f,"
                    "\"brake_nm\":%.3f,\"brake_kw\":%.4f,"
                    "\"imep_bar\":%.3f,\"bmep_bar\":%.3f,"
                    "\"work_cycle_j\":%.2f,\"ve_ambient\":%.4f,"
                    "\"ve_manifold\":%.4f,\"air_mg_cyl_cycle\":%.2f,"
                    "\"fuel_g_s\":%.4f,\"bsfc\":%.1f,\"lambda_cyl\":%.3f,"
                    "\"spark_deg\":%.2f,\"mbt_deg\":%.2f,"
                    "\"spark_eff\":%.4f,\"residual\":%.4f,"
                    "\"air_throttle_kg_s\":%.6f,\"air_cyl_kg_s\":%.6f}\n",
                    context.ticks, w.mean_rpm, w.indicated_torque_nm,
                    w.friction_torque_nm, w.pumping_torque_nm,
                    w.accessory_torque_nm, w.brake_torque_nm, w.brake_power_kw,
                    w.imep_bar, w.bmep_bar, w.work_per_cycle_j, w.ve_ambient,
                    context.intake->last_ve_manifold(), w.air_mg_per_cyl_cycle,
                    w.fuel_g_s, w.bsfc_g_kwh, w.lambda_cylinders,
                    context.combustion.last_spark_advance_deg(),
                    context.combustion.last_mbt_deg(),
                    context.combustion.last_spark_efficiency(),
                    context.combustion.last_residual_fraction(),
                    context.intake->last_air_in_kg_s(),
                    context.intake->last_air_to_cylinders_kg_s());
}



static double tps1_pin_voltage(const EmulatorLoopContext &context) {
    if (context.tps1_high_tick && context.ticks >= context.tps1_high_tick &&
        (!context.tps1_restore_tick ||
         context.ticks < context.tps1_restore_tick))
        return context.tps_circuit->reference_voltage();
    return context.tps_circuit->track1_voltage(context.throttle->angle_rad());
}

static double tps2_pin_voltage(const EmulatorLoopContext &context) {
    if (context.tps2_high_tick && context.ticks >= context.tps2_high_tick &&
        (!context.tps2_restore_tick ||
         context.ticks < context.tps2_restore_tick))
        return context.tps_circuit->reference_voltage();
    return context.tps_circuit->track2_voltage(context.throttle->angle_rad());
}

static double ect_pin_voltage(const EmulatorLoopContext &context) {
    if (context.ect_open_tick && context.ticks >= context.ect_open_tick &&
        (!context.ect_restore_tick ||
         context.ticks < context.ect_restore_tick))
        return 5.0;
    return context.sensor_circuit->coolant_voltage(
        context.thermal->coolant_sensor_c());
}

using MovcKey = std::tuple<uint16_t, uint8_t, uint16_t, uint8_t,
                           uint16_t, uint16_t, uint8_t>;
using MovcCounts = std::map<MovcKey, unsigned long long>;
using MovcBucketCounts = std::map<std::pair<uint64_t, uint16_t>,
                                  unsigned long long>;
using LookupKey = std::tuple<uint8_t, uint8_t, uint8_t, uint8_t, uint8_t,
                             uint8_t, uint8_t, uint8_t, uint8_t, uint8_t>;
using LookupCounts = std::map<LookupKey, unsigned long long>;
static thread_local MovcCounts *movc_counts = nullptr;
static thread_local MovcBucketCounts *movc_bucket_counts = nullptr;
static uint64_t movc_bucket_ticks = 0;
static uint64_t movc_tick = 0;
static em8051operation original_movc_pc = nullptr;
static em8051operation original_movc_dptr = nullptr;
static std::array<em8051operation, 256> original_indirect_reads{};
using IndirectReadKey = std::tuple<uint16_t, uint8_t, uint8_t>;
using IndirectReadCounts = std::map<IndirectReadKey,
                                    std::pair<unsigned long long, uint64_t>>;
static thread_local IndirectReadCounts *indirect_read_counts = nullptr;
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
        if (!input || std::fseek(input, 0, SEEK_END) != 0 ||
            std::ftell(input) != static_cast<long>(donor.bytes.size()) ||
            std::fseek(input, 0, SEEK_SET) != 0 ||
            std::fread(donor.bytes.data(), 1, donor.bytes.size(), input) !=
                donor.bytes.size()) {
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
        context.bridge.emulated_tick = context.ticks;
        if (!context.key_on && context.physical_crank) {
            const double load = context.load_step_tick &&
                                        context.ticks >= context.load_step_tick
                                    ? context.load_torque_nm
                                    : 0.0;
            tick_physical_crank_input(&cpu, *context.physical_crank,
                                      *context.physical_input, false, 0.0,
                                      load + (context.intake
                                                  ? context.intake->pumping_torque_nm()
                                                  : 0.0),
                                      false, context.drivetrain);
            if (context.drivetrain)
                context.vehicle_speed_kmh = context.drivetrain->speed_m_s() * 3.6;
            if (context.thermal && context.ticks % 990 == 0) {
                if (!context.drivetrain) context.vehicle_speed_kmh += std::clamp(
                    context.vehicle_speed_target_kmh - context.vehicle_speed_kmh,
                    -0.02, 0.02);
                context.thermal->advance_ticks(
                    990,
                    context.intake
                        ? std::max(0.0, context.intake->last_air_in_kg_s())
                        : 0.0,
                    context.coolant_heat_pending_j * 1000.0,
                    std::abs(context.vehicle_speed_kmh));
                context.coolant_heat_pending_j = 0.0;
            }
            if (context.intake && context.throttle && context.thermal &&
                context.ticks % context.fluid_step_ticks == 0) {
                const double dt_s =
                    static_cast<double>(context.fluid_step_ticks) / 990000.0;
                const auto charge = context.intake->step(
                    dt_s, context.physical_crank->rpm(),
                    context.throttle->angle_rad(), context.thermal->air_c(),
                    context.thermal->wall_c(),
                    context.injected_mass_pending_kg);
                // Coasting carries residual fuel away without new sparks.
                context.exhaust_flow_kg_s = charge.air_to_cylinders_kg / dt_s;
                context.exhaust.step(dt_s, context.ticks, 0.0);
                context.injected_mass_pending_kg = 0.0;
            }
            continue;
        }
        const bool idle_contact_before =
            context.throttle && context.throttle->contact_closed();
        if (context.idle_bridge_candidate &&
            context.ticks == context.idle_motor_disconnect_tick) {
            context.idle_motor_connected = false;
            fprintf(stdout, "{\"type\":\"idle_motor_disconnect\","
                            "\"tick\":%lld}\n", context.ticks);
        }
        if (context.idle_bridge_candidate &&
            context.ticks == context.idle_motor_reconnect_tick) {
            context.idle_motor_connected = true;
            fprintf(stdout, "{\"type\":\"idle_motor_reconnect\","
                            "\"tick\":%lld}\n", context.ticks);
        }
        if (context.injector_stage &&
            context.ticks == context.injector_disconnect_tick) {
            context.injector_stage->set_connected(false);
            fprintf(stdout, "{\"type\":\"injector_disconnect\","
                            "\"tick\":%lld}\n", context.ticks);
        }
        if (context.injector_stage &&
            context.ticks == context.injector_reconnect_tick) {
            context.injector_stage->set_connected(true);
            fprintf(stdout, "{\"type\":\"injector_reconnect\","
                            "\"tick\":%lld}\n", context.ticks);
        }
        if (context.physical_crank &&
            context.ticks == context.coil_disconnect_tick) {
            context.ignition_stage.set_connected(context.coil_channel, false);
            fprintf(stdout, "{\"type\":\"coil_disconnect\","
                            "\"tick\":%lld,\"channel\":%u}\n",
                    context.ticks, context.coil_channel);
        }
        if (context.physical_crank &&
            context.ticks == context.coil_reconnect_tick) {
            context.ignition_stage.set_connected(context.coil_channel, true);
            fprintf(stdout, "{\"type\":\"coil_reconnect\","
                            "\"tick\":%lld,\"channel\":%u}\n",
                    context.ticks, context.coil_channel);
        }
        if (context.thermal && context.ticks % 990 == 0) {
            if (!context.drivetrain) context.vehicle_speed_kmh += std::clamp(
                context.vehicle_speed_target_kmh - context.vehicle_speed_kmh,
                -0.02, 0.02);
            context.thermal->advance_ticks(
                990, context.intake ? std::max(0.0, context.intake->last_air_in_kg_s())
                                    : 0.0,
                context.coolant_heat_pending_j * 1000.0,
                std::abs(context.vehicle_speed_kmh));
            context.coolant_heat_pending_j = 0.0;
        }
        if (context.throttle && context.ticks == context.pedal_step_tick) {
            if (context.pedal_rise_ticks) {
                fprintf(stdout, "{\"type\":\"pedal_command\",\"tick\":%lld,"
                                "\"target_pull_m\":%.6f,\"rise_ticks\":%lld}\n",
                        context.ticks, context.pedal_pull_m,
                        context.pedal_rise_ticks);
            } else {
                context.throttle->set_cable_pull_m(context.pedal_pull_m);
                fprintf(stdout, "{\"type\":\"pedal\",\"tick\":%lld,"
                                "\"pull_m\":%.6f,\"angle_rad\":%.6f,"
                                "\"contact\":%s}\n",
                        context.ticks, context.pedal_pull_m,
                        context.throttle->angle_rad(),
                        context.throttle->contact_closed() ? "true" : "false");
            }
        }
        if (context.throttle && context.pedal_rise_ticks) {
            const long long elapsed = context.ticks - context.pedal_step_tick;
            if (elapsed > 0 && elapsed < context.pedal_rise_ticks &&
                context.ticks % context.fluid_step_ticks == 0) {
                context.throttle->set_cable_pull_m(
                    context.pedal_pull_m * static_cast<double>(elapsed) /
                    static_cast<double>(context.pedal_rise_ticks));
            } else if (elapsed == context.pedal_rise_ticks) {
                context.throttle->set_cable_pull_m(context.pedal_pull_m);
                fprintf(stdout, "{\"type\":\"pedal\",\"tick\":%lld,"
                                "\"pull_m\":%.6f,\"angle_rad\":%.6f,"
                                "\"contact\":%s}\n",
                        context.ticks, context.pedal_pull_m,
                        context.throttle->angle_rad(),
                        context.throttle->contact_closed() ? "true" : "false");
            }
        }
        if (context.throttle && context.ticks == context.pedal_release_tick) {
            context.throttle->set_cable_pull_m(0.0);
            fprintf(stdout, "{\"type\":\"pedal_release\",\"tick\":%lld,"
                            "\"angle_rad\":%.6f,\"contact\":%s}\n",
                    context.ticks, context.throttle->angle_rad(),
                    context.throttle->contact_closed() ? "true" : "false");
        }
        if (context.physical_crank && context.ticks == context.load_step_tick)
            fprintf(stdout, "{\"type\":\"load_step\",\"tick\":%lld,"
                            "\"torque_nm\":%.3f}\n",
                    context.ticks, context.load_torque_nm);
        if (context.throttle && context.ticks == context.tps1_high_tick) {
            fprintf(stdout, "{\"type\":\"tps_fault\",\"tick\":%lld,"
                            "\"channel\":6,\"voltage_v\":%.3f}\n",
                    context.ticks, context.tps_circuit->reference_voltage());
        }
        if (context.throttle && context.ticks == context.tps1_restore_tick) {
            fprintf(stdout, "{\"type\":\"tps_restore\",\"tick\":%lld,"
                            "\"channel\":6}\n", context.ticks);
        }
        if (context.throttle && context.ticks == context.tps2_high_tick)
            fprintf(stdout, "{\"type\":\"tps_fault\",\"tick\":%lld,"
                            "\"channel\":0,\"voltage_v\":%.3f}\n",
                    context.ticks, context.tps_circuit->reference_voltage());
        if (context.throttle && context.ticks == context.tps2_restore_tick)
            fprintf(stdout, "{\"type\":\"tps_restore\",\"tick\":%lld,"
                            "\"channel\":0}\n", context.ticks);
        if (context.thermal && context.ticks == context.ect_open_tick)
            fprintf(stdout, "{\"type\":\"ect_open\",\"tick\":%lld,"
                            "\"adc3_v\":5.0}\n", context.ticks);
        if (context.thermal && context.ticks == context.ect_restore_tick)
            fprintf(stdout, "{\"type\":\"ect_restore\",\"tick\":%lld}\n",
                    context.ticks);
        movc_tick = static_cast<uint64_t>(context.ticks);
        set_adc_tick(static_cast<uint64_t>(context.ticks));
        if (context.physical_crank) {
            if (context.ticks == context.crank_sensor_open_tick)
                fprintf(stdout, "{\"type\":\"crank_sensor_open\","
                                "\"tick\":%lld}\n", context.ticks);
            if (context.ticks == context.crank_sensor_restore_tick)
                fprintf(stdout, "{\"type\":\"crank_sensor_restore\","
                                "\"tick\":%lld}\n", context.ticks);
            const bool sensor_connected =
                !context.crank_sensor_open_tick ||
                context.ticks < context.crank_sensor_open_tick ||
                (context.crank_sensor_restore_tick &&
                 context.ticks >= context.crank_sensor_restore_tick);
            const auto gaps_before = context.physical_input->missing_positions;
            if (context.thermal && context.physical_plant_friction_temp &&
                context.ticks % context.fluid_step_ticks == 0)
                context.physical_crank->set_friction_scale(
                    engine::physics::oil_friction_scale(
                        engine::physics::OilFrictionParams{},
                        context.thermal->coolant_c()));
            const double plant_angle_before = context.physical_crank->angle_rad();
            const double plant_friction_nm =
                context.physical_crank->friction_torque_nm();
            const double plant_comb_nm = context.combustion.torque_nm(plant_angle_before);
            const double plant_load_nm =
                context.load_step_tick && context.ticks >= context.load_step_tick
                    ? context.load_torque_nm
                    : 0.0;
            const double plant_pump_nm =
                context.intake ? context.intake->pumping_torque_nm() : 0.0;
            // Accessories (F-45): alternator + water pump, calibrated plant only.
            double plant_acc_nm = 0.0;
            if (context.physical_plant_accessories &&
                context.physical_crank->speed_rad_s() > 1.0) {
                const double omega = context.physical_crank->speed_rad_s();
                const double v_sys = context.sensor_circuit
                                         ? context.sensor_circuit->supply_voltage()
                                         : 14.0;
                plant_acc_nm = engine::physics::accessory_torque_nm(
                    engine::physics::AccessoryParams{}, v_sys, omega);
            }
            tick_physical_crank_input(&cpu, *context.physical_crank,
                                      *context.physical_input,
                                      context.ticks <= context.starter_stop_tick,
                                      context.combustion.torque_nm(
                                          context.physical_crank->angle_rad()),
                                      (context.load_step_tick &&
                                               context.ticks >= context.load_step_tick
                                           ? context.load_torque_nm
                                           : 0.0) +
                                          plant_acc_nm +
                                          (context.intake
                                               ? context.intake->pumping_torque_nm()
                                               : 0.0),
                                      sensor_connected, context.drivetrain);
            if (context.drivetrain)
                context.vehicle_speed_kmh = context.drivetrain->speed_m_s() * 3.6;
            context.combustion_integrated_j +=
                plant_comb_nm * (context.physical_crank->angle_rad() - plant_angle_before);
            if (context.intake) {
                context.plant_window.accumulate(
                    1.0 / 990000.0,
                    context.physical_crank->angle_rad() - plant_angle_before,
                    plant_comb_nm, plant_friction_nm, plant_pump_nm,
                    plant_load_nm + plant_acc_nm);
                const auto &ip = context.intake->parameters();
                const double rho_ref = ip.ambient_pressure_pa /
                    (287.05 * (ip.ambient_temperature_c + 273.15));
                if (context.plant_window.finish_if_ready(
                        rho_ref, context.combustion.stoichiometric_afr(),
                        context.combustion.fuel_energy_j_per_kg()) &&
                    fine_plant_windows())
                    print_plant_line(context);
            }
            if (context.physical_input->missing_positions != gaps_before) {
                fprintf(stdout, "{\"type\":\"crank_gap\",\"tick\":%lld,"
                                "\"position\":%d,\"rpm\":%.3f}\n",
                        context.ticks,
                        context.physical_input->last_missing_position,
                        context.physical_crank->rpm());
            }
        } else {
            tick_crank_input(&cpu, context.ticks, context.crank);
        }
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
        const uint8_t rpm_before = cpu.mLowerData[0x47];
        const uint8_t idle_fault_before = cpu.mLowerData[0x27];
        const uint8_t published_fault_before = cpu.mExtData[0xF84E];
        const uint8_t ram28_before = cpu.mLowerData[0x28];
        const uint8_t f84f_before = cpu.mExtData[0xF84F];
        const uint8_t lambda_flags_before =
            (cpu.mLowerData[0x2F] & 0x02u) | (cpu.mLowerData[0x2C] & 0x08u);
        const uint8_t idle_state_before = cpu.mExtData[0xF847];
        const uint8_t cc3_before = cpu.cc3_output_pin;
        const uint8_t bridge_before = cpu.mSFR[0x90 - 0x80] & 0x60u;
        const uint8_t ignition_before = cpu.mSFR[0xF8 - 0x80] & 0x03u;
        const uint8_t p54_before = cpu.mSFR[0xF8 - 0x80] & 0x10u;
        const uint8_t p17_before = cpu.mSFR[0x90 - 0x80] & 0x80u;
        static constexpr std::array<uint8_t, 4> observed_ports{
            0x90, 0xB0, 0xE8, 0xF8}; // P1, P3, P4, P5 latch addresses.
        static const bool trace_port_latches =
            std::getenv("MA17_TRACE_PORT_LATCHES") != nullptr;
        std::array<uint8_t, 4> port_latches_before{};
        if (trace_port_latches && context.physical_crank)
            for (size_t port = 0; port < observed_ports.size(); ++port)
                port_latches_before[port] =
                    cpu.mSFR[observed_ports[port] - 0x80];
        const uint8_t tps2_before = cpu.mLowerData[0x60];
        const uint8_t tps1_before = cpu.mLowerData[0x66];
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
        context.diagnostic_lamp.sample_p5(cpu.mSFR[0xF8 - 0x80]);
        if (context.pump_relay_p34_candidate) {
            const bool p34_high =
                (cpu.mSFR[0xB0 - 0x80] & 0x10u) != 0;
            const bool was_closed = context.pump_relay.closed();
            const bool closed =
                context.pump_relay.step(p34_high, context.ticks);
            if (closed != was_closed)
                fprintf(stdout, "{\"type\":\"pump_relay_candidate\","
                                "\"tick\":%lld,\"closed\":%s,"
                                "\"p34_high\":%s,\"pc\":%u}\n",
                        context.ticks, closed ? "true" : "false",
                        p34_high ? "true" : "false",
                        static_cast<unsigned>(last_pc));
        }
        if (trace_port_latches && context.physical_crank) {
            for (size_t port = 0; port < observed_ports.size(); ++port) {
                const uint8_t changed = port_latches_before[port] ^
                                        cpu.mSFR[observed_ports[port] - 0x80];
                for (unsigned bit = 0; bit < 8; ++bit) {
                    if (changed & (1u << bit)) {
                        const unsigned latch =
                            cpu.mSFR[observed_ports[port] - 0x80];
                        const unsigned high = (latch >> bit) & 1u;
                        fprintf(stderr,
                                "[PORT-LATCH] tick=%lld pc=%04X port=%02X "
                                "bit=%u high=%u ram47=%u\n",
                                context.ticks, static_cast<unsigned>(last_pc),
                                observed_ports[port], bit, high,
                                static_cast<unsigned>(cpu.mLowerData[0x47]));
                        if (observed_ports[port] == 0x90 && bit == 1 &&
                            cpu.mUpperData)
                            fprintf(stderr,
                                    "[P11-OBS] tick=%lld high=%u angle=%.12f "
                                    "physical_rpm=%.6f ram46=%u ram47=%u "
                                    "iram9fa0=%u irama1a2=%u\n",
                                    context.ticks, high,
                                    context.physical_crank->angle_rad(),
                                    context.physical_crank->rpm(),
                                    static_cast<unsigned>(cpu.mLowerData[0x46]),
                                    static_cast<unsigned>(cpu.mLowerData[0x47]),
                                    (static_cast<unsigned>(cpu.mUpperData[0x1F]) << 8) |
                                        cpu.mUpperData[0x20],
                                    (static_cast<unsigned>(cpu.mUpperData[0x21]) << 8) |
                                        cpu.mUpperData[0x22]);
                    }
                }
            }
        }
        static const bool trace_output_candidates =
            std::getenv("MA17_TRACE_OUTPUT_CANDIDATES") != nullptr;
        if (trace_output_candidates &&
            p17_before != (cpu.mSFR[0x90 - 0x80] & 0x80u))
            fprintf(stderr, "[OUTPUT-CANDIDATE] tick=%lld pc=%04X "
                            "p17=%u ram1d=%u ram2d=%02X ram47=%u "
                            "t2con=%02X\n",
                    context.ticks, static_cast<unsigned>(last_pc),
                    (cpu.mSFR[0x90 - 0x80] >> 7) & 1u,
                    static_cast<unsigned>(cpu.mLowerData[0x1D]),
                    static_cast<unsigned>(cpu.mLowerData[0x2D]),
                    static_cast<unsigned>(cpu.mLowerData[0x47]),
                    static_cast<unsigned>(cpu.mSFR[0xC8 - 0x80]));
        if (context.physical_crank &&
            p54_before != (cpu.mSFR[0xF8 - 0x80] & 0x10u))
            fprintf(stdout, "{\"type\":\"p54_raw\","
                            "\"tick\":%lld,\"pc\":%u,\"p54\":%u,"
                            "\"ram2d\":%u,\"xram_f881\":%u,"
                            "\"ram47\":%u}\n",
                    context.ticks, static_cast<unsigned>(last_pc),
                    (cpu.mSFR[0xF8 - 0x80] >> 4) & 1u,
                    static_cast<unsigned>(cpu.mLowerData[0x2D]),
                    static_cast<unsigned>(cpu.mExtData[0xF881]),
                    static_cast<unsigned>(cpu.mLowerData[0x47]));
        if (context.on_event && context.physical_crank &&
            p54_before != (cpu.mSFR[0xF8 - 0x80] & 0x10u))
            context.on_event(
                {context.ticks, EmulatorEventType::LampCandidate, 0,
                 (cpu.mSFR[0xF8 - 0x80] & 0x10u) != 0,
                 context.physical_crank->angle_rad(),
                 context.physical_crank->rpm()},
                context.event_context);
        if (context.physical_crank && cpu.mExtData[0xF847] != idle_state_before)
            fprintf(stdout, "{\"type\":\"idle_state_raw\",\"tick\":%lld,"
                            "\"pc\":%u,\"before\":%u,\"after\":%u,"
                            "\"ram24\":%u,\"ram27\":%u,\"f84e\":%u}\n",
                    context.ticks, static_cast<unsigned>(last_pc),
                    static_cast<unsigned>(idle_state_before),
                    static_cast<unsigned>(cpu.mExtData[0xF847]),
                    static_cast<unsigned>(cpu.mLowerData[0x24]),
                    static_cast<unsigned>(cpu.mLowerData[0x27]),
                    static_cast<unsigned>(cpu.mExtData[0xF84E]));
        if (context.physical_crank &&
            (cpu.mLowerData[0x27] != idle_fault_before ||
             cpu.mExtData[0xF84E] != published_fault_before))
            fprintf(stdout, "{\"type\":\"idle_fault_raw\",\"tick\":%lld,"
                            "\"pc\":%u,\"ram27\":%u,\"f84e\":%u,"
                            "\"f83b\":%u,\"contact\":%s}\n",
                    context.ticks, static_cast<unsigned>(last_pc),
                    static_cast<unsigned>(cpu.mLowerData[0x27]),
                    static_cast<unsigned>(cpu.mExtData[0xF84E]),
                    static_cast<unsigned>(cpu.mExtData[0xF83B]),
                    context.throttle->contact_closed() ? "true" : "false");
        if (context.physical_crank &&
            (cpu.mLowerData[0x28] != ram28_before ||
             cpu.mExtData[0xF84F] != f84f_before))
            fprintf(stdout, "{\"type\":\"sensor_fault_raw\",\"tick\":%lld,"
                            "\"pc\":%u,\"ram28\":%u,\"f84f\":%u,"
                            "\"ram63\":%u,\"ram60\":%u,\"ram66\":%u}\n",
                    context.ticks, static_cast<unsigned>(last_pc),
                    static_cast<unsigned>(cpu.mLowerData[0x28]),
                    static_cast<unsigned>(cpu.mExtData[0xF84F]),
                    static_cast<unsigned>(cpu.mLowerData[0x63]),
                    static_cast<unsigned>(cpu.mLowerData[0x60]),
                    static_cast<unsigned>(cpu.mLowerData[0x66]));
        const uint8_t lambda_flags_after =
            (cpu.mLowerData[0x2F] & 0x02u) | (cpu.mLowerData[0x2C] & 0x08u);
        if (context.physical_crank && lambda_flags_after != lambda_flags_before)
            fprintf(stdout, "{\"type\":\"lambda_class_raw\",\"tick\":%lld,"
                            "\"pc\":%u,\"ram65\":%u,\"flags\":%u,"
                            "\"f8e8\":%u,\"f8ea\":%u}\n",
                    context.ticks, static_cast<unsigned>(last_pc),
                    static_cast<unsigned>(cpu.mLowerData[0x65]),
                    static_cast<unsigned>(lambda_flags_after),
                    static_cast<unsigned>(cpu.mExtData[0xF8E8]),
                    static_cast<unsigned>(cpu.mExtData[0xF8EA]));
        if (context.physical_crank) {
            const uint8_t bridge_after = cpu.mSFR[0x90 - 0x80] & 0x60u;
            if (bridge_before != bridge_after)
                fprintf(stdout, "{\"type\":\"bridge_candidate\","
                                "\"tick\":%lld,\"p15\":%u,\"p16\":%u,"
                                "\"pc\":%u,\"ram1c\":%u,\"ram1f\":%u,"
                                "\"ram24\":%u,\"contact\":%s}\n",
                        context.ticks, (bridge_after >> 5) & 1u,
                        (bridge_after >> 6) & 1u,
                        static_cast<unsigned>(last_pc),
                        static_cast<unsigned>(cpu.mLowerData[0x1C]),
                        static_cast<unsigned>(cpu.mLowerData[0x1F]),
                        static_cast<unsigned>(cpu.mLowerData[0x24]),
                        context.throttle->contact_closed() ? "true" : "false");
            if (context.idle_bridge_candidate) {
                const auto drive = context.idle_bridge.drive(bridge_after);
                context.idle_actuator.step(
                    context.idle_motor_connected ? drive.voltage_v : 0.0,
                    context.idle_motor_connected && drive.brake,
                    1.0 / 990000.0);
                context.throttle->set_stop_angle_rad(
                    context.idle_actuator.stop_angle_rad());
            }
        }
        if (context.idle_bridge_candidate && context.throttle &&
            context.throttle->contact_closed() != idle_contact_before)
            fprintf(stdout, "{\"type\":\"idle_contact\",\"tick\":%lld,"
                            "\"closed\":%s,\"cable_rad\":%.6f,"
                            "\"stop_rad\":%.6f}\n",
                    context.ticks,
                    context.throttle->contact_closed() ? "true" : "false",
                    context.throttle->cable_angle_rad(),
                    context.throttle->stop_angle_rad());
        if (context.physical_crank) {
            const uint8_t ignition_after = cpu.mSFR[0xF8 - 0x80] & 0x03u;
            const auto sparks = context.ignition_stage.step(
                ignition_after, 1.0 / 990000.0);
            for (unsigned channel = 0; channel < 2; ++channel) {
                const uint8_t mask = static_cast<uint8_t>(1u << channel);
                if (context.ignition_stage.attempted(channel)) {
                    if (context.on_event && sparks[channel] > 0.0)
                        context.on_event(
                            {context.ticks, EmulatorEventType::Spark, channel,
                             false, context.physical_crank->angle_rad(),
                             context.physical_crank->rpm(), 0.0, 0,
                             context.combustion.pair_for_channel(channel)},
                            context.event_context);
                    const auto event = context.combustion.spark(
                        context.physical_crank->angle_rad(), channel,
                        sparks[channel]);
                    context.coolant_heat_pending_j +=
                        event.burned_fuel_kg *
                        context.combustion.fuel_energy_j_per_kg() * 0.25;
                    context.exhaust.admit(event, context.exhaust_flow_kg_s,
                                          context.ticks);
                    if (context.on_event && event.air_kg > 0.0)
                        context.on_event(
                            {context.ticks,
                             event.burned_fuel_kg > 0.0
                                 ? EmulatorEventType::Combustion
                                 : EmulatorEventType::Misfire,
                             channel, false,
                             context.physical_crank->angle_rad(),
                             context.physical_crank->rpm(),
                             event.burned_fuel_kg, event.cylinder_index},
                            context.event_context);
                }
                if ((ignition_before ^ ignition_after) & mask) {
                    fprintf(stdout, "{\"type\":\"ignition_pin\","
                                    "\"tick\":%lld,\"channel\":%u,"
                                    "\"high\":%s,\"angle_rad\":%.6f,"
                                    "\"rpm\":%.3f}\n",
                            context.ticks, channel,
                            ignition_after & mask ? "true" : "false",
                            context.physical_crank->angle_rad(),
                            context.physical_crank->rpm());
                    if (context.on_event)
                        context.on_event(
                            {context.ticks, EmulatorEventType::IgnitionPin,
                             channel, (ignition_after & mask) != 0,
                             context.physical_crank->angle_rad(),
                             context.physical_crank->rpm()},
                            context.event_context);
                }
            }
        }
        if (context.injector_stage) {
            if (cpu.cc3_output_pin != cc3_before)
                fprintf(stdout, "{\"type\":\"cc3_pin\",\"tick\":%lld,"
                                "\"high\":%s,\"shadow_high\":%s,"
                                "\"ram14_15\":%u,\"lambda_flags\":%u,"
                                "\"ram65\":%u}\n",
                        context.ticks, cpu.cc3_output_pin ? "true" : "false",
                        cpu.mSFR[0x90 - 0x80] & 0x08u ? "true" : "false",
                        (static_cast<unsigned>(cpu.mLowerData[0x14]) << 8) |
                            cpu.mLowerData[0x15],
                        static_cast<unsigned>(lambda_flags_after),
                        static_cast<unsigned>(cpu.mLowerData[0x65]));
            if (context.on_event && context.physical_crank &&
                cpu.cc3_output_pin != cc3_before)
                context.on_event(
                    {context.ticks, EmulatorEventType::InjectorPin, 0,
                     cpu.cc3_output_pin != 0,
                     context.physical_crank->angle_rad(),
                     context.physical_crank->rpm()},
                    context.event_context);
            context.injected_mass_pending_kg += context.injector_stage->step(
                cpu.cc3_output_pin != 0, 1.0 / 990000.0,
                context.sensor_circuit ? context.sensor_circuit->supply_voltage()
                                       : 12.5);
            if (context.ticks % context.fluid_step_ticks == 0) {
                const auto charge = context.intake->step(
                    static_cast<double>(context.fluid_step_ticks) / 990000.0,
                    context.physical_crank->rpm(), context.throttle->angle_rad(),
                    context.thermal->air_c(), context.thermal->wall_c(),
                    context.injected_mass_pending_kg);
                context.plant_window.add_mass(
                    charge.air_to_cylinders_kg, context.injected_mass_pending_kg,
                    charge.fuel_to_cylinders_kg);
                context.combustion.admit(charge,
                                         context.physical_crank->angle_rad());
                context.combustion.set_operating_point(
                    context.physical_crank->rpm(), context.intake->pressure_pa(),
                    context.intake->exhaust_pressure_pa());
                const double fluid_dt_s =
                    static_cast<double>(context.fluid_step_ticks) / 990000.0;
                context.exhaust_flow_kg_s = charge.air_to_cylinders_kg /
                                            fluid_dt_s;
                const double heater_power_w = context.pump_relay_p34_candidate
                    ? context.lambda_heater.power_w(
                          context.sensor_circuit
                              ? context.sensor_circuit->supply_voltage()
                              : 12.5,
                          context.pump_relay.closed())
                    : 0.0;
                context.exhaust.step(fluid_dt_s, context.ticks,
                                     heater_power_w);
                context.injected_mass_pending_kg = 0.0;
            }
        }
        if (context.thermal && context.ticks % 990000 == 0) {
            fprintf(stdout, "{\"type\":\"thermal\",\"tick\":%lld,"
                            "\"air_c\":%.3f,\"wall_c\":%.3f,"
                            "\"coolant_c\":%.3f,\"vehicle_kmh\":%.2f,"
                            "\"thermostat_open\":%.3f,\"fan_on\":%u,"
                            "\"iat_c\":%.3f,"
                            "\"ect_c\":%.3f,\"adc2_v\":%.4f,"
                            "\"adc3_v\":%.4f,\"adc3_upper\":%u,"
                            "\"ram61\":%u,"
                            "\"ram62\":%u,\"ram63\":%u}\n",
                    context.ticks, context.thermal->air_c(),
                    context.thermal->wall_c(), context.thermal->coolant_c(),
                    context.vehicle_speed_kmh,
                    context.thermal->thermostat_open_fraction(),
                    context.thermal->fan_on() ? 1U : 0U,
                    context.thermal->air_sensor_c(),
                    context.thermal->coolant_sensor_c(),
                    context.sensor_circuit->air_voltage(context.thermal->air_sensor_c()),
                    ect_pin_voltage(context),
                    static_cast<unsigned>(cpu.mUpperData[0xA8 - 0x80]),
                    static_cast<unsigned>(cpu.mLowerData[0x61]),
                    static_cast<unsigned>(cpu.mLowerData[0x62]),
                    static_cast<unsigned>(cpu.mLowerData[0x63]));
        }
        if (context.intake && context.ticks % 990000 == 0)
            fprintf(stdout, "{\"type\":\"intake\",\"tick\":%lld,"
                            "\"pressure_pa\":%.1f,\"air_kg\":%.9f,"
                            "\"air_in_kg\":%.9f,\"air_out_kg\":%.9f,"
                            "\"injected_kg\":%.9f,\"film_kg\":%.9f,"
                            "\"vapor_kg\":%.9f,\"delivered_kg\":%.9f,"
                            "\"cc3_pulses\":%llu}\n",
                    context.ticks, context.intake->pressure_pa(),
                    context.intake->air_mass_kg(),
                    context.intake->air_in_total_kg(),
                    context.intake->air_delivered_total_kg(),
                    context.intake->injected_total_kg(),
                    context.intake->fuel_film_kg(),
                    context.intake->fuel_vapor_kg(),
                    context.intake->fuel_delivered_total_kg(),
                    context.injector_stage->pulse_count());
        if (context.physical_crank && context.ticks % 990000 == 0) {
            const auto &by_cylinder = context.combustion.burns_by_cylinder();
            fprintf(stdout, "{\"type\":\"combustion\",\"tick\":%lld,"
                            "\"burns\":%llu,\"missed\":%llu,"
                            "\"burned_fuel_kg\":%.9f,\"rpm\":%.3f,"
                            "\"burns_cyl_1\":%llu,\"burns_cyl_2\":%llu,"
                            "\"burns_cyl_3\":%llu,\"burns_cyl_4\":%llu}\n",
                    context.ticks, context.combustion.burns(),
                    context.combustion.missed_sparks(),
                    context.combustion.burned_fuel_kg(),
                    context.physical_crank->rpm(), by_cylinder[0],
                    by_cylinder[1], by_cylinder[2], by_cylinder[3]);
        }
        if (context.intake && context.physical_crank &&
            context.ticks % 990000 == 0 && !fine_plant_windows() && context.plant_window.last().valid)
            print_plant_line(context);
        if (context.physical_crank && context.ticks % 990000 == 0)
            fprintf(stdout, "{\"type\":\"lambda\",\"tick\":%lld,"
                            "\"physical\":%.3f,"
                            "\"oxygen_equivalent\":%.3f,"
                            "\"voltage_v\":%.4f,"
                            "\"adc5_pin_v\":%.4f,"
                            "\"temperature_c\":%.1f,\"valid\":%s,"
                            "\"ram65\":%u}\n",
                    context.ticks, context.exhaust.charge_lambda(),
                    context.exhaust.lambda(),
                    context.exhaust.voltage_v(),
                    context.lambda_adc_pin_override_v >= 0.0 &&
                            context.ticks >= context.lambda_stuck_tick &&
                            (!context.lambda_restore_tick ||
                             context.ticks < context.lambda_restore_tick)
                        ? context.lambda_adc_pin_override_v
                        : context.sensor_circuit->lambda_adc_voltage(
                              context.exhaust.voltage_v()),
                    context.exhaust.temperature_c(),
                    context.exhaust.valid() ? "true" : "false",
                    static_cast<unsigned>(cpu.mLowerData[0x65]));
        if (context.physical_crank && context.ticks % 990000 == 0)
            fprintf(stdout, "{\"type\":\"diagnostic\",\"tick\":%lld,"
                            "\"ram27\":%u,\"ram28\":%u,"
                            "\"f84e\":%u,\"f84f\":%u,\"f850\":%u,"
                            "\"f85e\":%u,\"f85f\":%u,\"f860\":%u,"
                            "\"lamp_on_candidate\":%s}\n",
                    context.ticks, static_cast<unsigned>(cpu.mLowerData[0x27]),
                    static_cast<unsigned>(cpu.mLowerData[0x28]),
                    static_cast<unsigned>(cpu.mExtData[0xF84E]),
                    static_cast<unsigned>(cpu.mExtData[0xF84F]),
                    static_cast<unsigned>(cpu.mExtData[0xF850]),
                    static_cast<unsigned>(cpu.mExtData[0xF85E]),
                    static_cast<unsigned>(cpu.mExtData[0xF85F]),
                    static_cast<unsigned>(cpu.mExtData[0xF860]),
                    context.diagnostic_lamp.lamp_on() ? "true" : "false");
        if (context.idle_bridge_candidate && context.ticks % 990000 == 0)
            fprintf(stdout, "{\"type\":\"idle_actuator\",\"tick\":%lld,"
                            "\"stem_m\":%.6f,\"stop_rad\":%.6f,"
                            "\"angle_rad\":%.6f,\"contact\":%s,"
                            "\"ram60\":%u,\"ram66\":%u}\n",
                    context.ticks, context.idle_actuator.stem_m(),
                    context.throttle->stop_angle_rad(),
                    context.throttle->angle_rad(),
                    context.throttle->contact_closed() ? "true" : "false",
                    static_cast<unsigned>(cpu.mLowerData[0x60]),
                    static_cast<unsigned>(cpu.mLowerData[0x66]));
        if (context.physical_crank && cpu.mLowerData[0x47] != rpm_before) {
            fprintf(stdout, "[COSIM-RPM] tick=%lld physical_rpm=%.3f "
                            "ram47=%u pc=%04X\n",
                    context.ticks, context.physical_crank->rpm(),
                    static_cast<unsigned>(cpu.mLowerData[0x47]), last_pc);
        }
        if (context.throttle &&
            (cpu.mLowerData[0x60] != tps2_before ||
             cpu.mLowerData[0x66] != tps1_before)) {
            fprintf(stdout, "{\"type\":\"tps_ram\",\"tick\":%lld,"
                            "\"angle_rad\":%.6f,\"adc0_v\":%.6f,"
                            "\"adc6_v\":%.6f,\"ram60\":%u,\"ram66\":%u}\n",
                    context.ticks, context.throttle->angle_rad(),
                    tps2_pin_voltage(context),
                    tps1_pin_voltage(context),
                    static_cast<unsigned>(cpu.mLowerData[0x60]),
                    static_cast<unsigned>(cpu.mLowerData[0x66]));
        }
        if (override_iram_read)
            cpu.mLowerData[(*iram_setting)[1]] = saved_iram_read;
        if (override_ram5b) cpu.mLowerData[0x5B] = saved_ram5b;
        if (override_ram6e) cpu.mLowerData[0x6E] = saved_ram6e;
        if (override_ram2c) cpu.mLowerData[0x2C] = saved_ram2c;

        if (context.trace_pc) {
            trace_cc3_and_ram67(cpu, context.ticks, last_pc, timer2_before);
            trace_memory_changes(cpu, context.ticks, last_pc);
        }
        context.tachometer.observe((cpu.mSFR[0x90 - 0x80] & 0x02u) != 0,
                                   context.ticks);
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

static void reboot_cpu_with_retained_ram(em8051 &cpu) {
    // Hypothesis: key-on releases /HWPD while battery-backed RAM retains data.
    // reset(false) resets the core but also reinstalls opcode/SFR callbacks;
    // restore the harness hooks and optional trace wrappers afterward.
    std::array<em8051operation, 256> operations{};
    std::array<em8051sfrread, 128> sfr_reads{};
    std::array<em8051sfrwrite, 128> sfr_writes{};
    std::copy(std::begin(cpu.op), std::end(cpu.op), operations.begin());
    std::copy(std::begin(cpu.sfrread), std::end(cpu.sfrread), sfr_reads.begin());
    std::copy(std::begin(cpu.sfrwrite), std::end(cpu.sfrwrite), sfr_writes.begin());
    reset(&cpu, false);
    std::copy(operations.begin(), operations.end(), std::begin(cpu.op));
    std::copy(sfr_reads.begin(), sfr_reads.end(), std::begin(cpu.sfrread));
    std::copy(sfr_writes.begin(), sfr_writes.end(), std::begin(cpu.sfrwrite));
}

static EmulatorSnapshot capture_snapshot(const EmulatorLoopContext &context) {
    const em8051 &cpu = context.cpu;
    EmulatorSnapshot snapshot;
    snapshot.tick = context.ticks;
    snapshot.pc = cpu.mPC;
    snapshot.ram47 = cpu.mLowerData[0x47];
    snapshot.ram46 = cpu.mLowerData[0x46];
    snapshot.tachometer_rpm = context.tachometer.rpm(context.ticks);
    snapshot.tachometer_pulses = context.tachometer.pulses();
    snapshot.tachometer_available = context.tachometer.available();
    for (std::size_t index = 0; index < snapshot.rom_iram_60_67.size(); ++index)
        snapshot.rom_iram_60_67[index] = cpu.mLowerData[0x60 + index];
    snapshot.ram27_faults = cpu.mLowerData[0x27];
    snapshot.ram28_faults = cpu.mLowerData[0x28];
    for (std::size_t index = 0; index < 3; ++index) {
        snapshot.rom_current_fault_banks[index] = cpu.mExtData[0xF84E + index];
        snapshot.rom_history_fault_banks[index] = cpu.mExtData[0xF85E + index];
    }
    snapshot.cc3_high = cpu.cc3_output_pin != 0;
    for (uint8_t channel = 0; channel < snapshot.adc_last_conversion.size();
         ++channel)
        snapshot.adc_last_conversion[channel] = adc_observation(channel);
    snapshot.p50_high = (cpu.mSFR[0xF8 - 0x80] & 0x01u) != 0;
    snapshot.p51_high = (cpu.mSFR[0xF8 - 0x80] & 0x02u) != 0;
    snapshot.lamp_on_candidate = context.diagnostic_lamp.lamp_on();
    snapshot.idle_bridge_candidate = context.idle_bridge_candidate;
    snapshot.idle_motor_connected = context.idle_motor_connected;
    snapshot.p15_high = (cpu.mSFR[0x90 - 0x80] & 0x20u) != 0;
    snapshot.p16_high = (cpu.mSFR[0x90 - 0x80] & 0x40u) != 0;
    if (context.idle_bridge_candidate)
        snapshot.idle_stem_m = context.idle_actuator.stem_m();
    snapshot.key_on = context.key_on;
    snapshot.vehicle_speed_kmh = context.vehicle_speed_kmh;
    snapshot.vehicle_speed_available = true;
    if (context.drivetrain && context.physical_crank) {
        snapshot.drivetrain_available = true;
        snapshot.vehicle_speed_kmh = context.drivetrain->speed_m_s() * 3.6;
        snapshot.transmission_gear = context.drivetrain->gear();
        snapshot.clutch_pressure = context.drivetrain->clutch_pressure();
        snapshot.clutch_crank_torque_nm = context.drivetrain->crank_torque_nm();
        snapshot.clutch_heat_j = context.drivetrain->clutch_heat_j();
    }
    if (context.sensor_circuit) {
        snapshot.battery_supply_v = context.sensor_circuit->supply_voltage();
        snapshot.battery_supply_available = true;
    }
    if (context.physical_crank) {
        snapshot.crank_available = true;
        snapshot.crank_angle_rad = context.physical_crank->angle_rad();
        snapshot.tdc_phase_rad = context.combustion.tdc_phase_rad();
        snapshot.rpm = context.physical_crank->rpm();
        snapshot.applied_load_nm =
            context.load_step_tick && context.ticks >= context.load_step_tick
                ? context.load_torque_nm
                : 0.0;
        snapshot.burns = context.combustion.burns();
        snapshot.missed_sparks = context.combustion.missed_sparks();
        snapshot.burns_by_cylinder = context.combustion.burns_by_cylinder();
        snapshot.lambda = context.exhaust.lambda();
        snapshot.exhaust_sample_available =
            context.exhaust.has_exhaust_sample();
        snapshot.lambda_voltage_v = context.exhaust.voltage_v();
    }
    if (context.throttle) {
        snapshot.throttle_available = true;
        snapshot.throttle_angle_rad = context.throttle->angle_rad();
        snapshot.idle_contact_closed = context.throttle->contact_closed();
        snapshot.pedal_pull_m = context.throttle->cable_pull_m();
        if (context.tps_circuit) {
            snapshot.tps_available = true;
            snapshot.tps_track1_v = context.tps_circuit->track1_voltage(
                snapshot.throttle_angle_rad);
            snapshot.tps_track2_v = context.tps_circuit->track2_voltage(
                snapshot.throttle_angle_rad);
        }
    }
    if (context.intake) {
        snapshot.manifold_pressure_pa = context.intake->pressure_pa();
        snapshot.air_in_kg_s = context.intake->last_air_in_kg_s();
        snapshot.injected_fuel_total_kg = context.intake->injected_total_kg();
        snapshot.intake_available = true;
        snapshot.fuel_film_kg = context.intake->fuel_film_kg();
        snapshot.fuel_vapor_kg = context.intake->fuel_vapor_kg();
        snapshot.air_throttle_kg_s = context.intake->last_air_in_kg_s();
        snapshot.air_to_cylinders_kg_s = context.intake->last_air_to_cylinders_kg_s();
        snapshot.manifold_air_mass_kg = context.intake->air_mass_kg();
        snapshot.manifold_air_c = context.intake->air_temperature_c();
        snapshot.ve_manifold_coefficient = context.intake->last_ve_manifold();
        snapshot.spark_advance_deg = context.combustion.last_spark_advance_deg();
        snapshot.mbt_deg = context.combustion.last_mbt_deg();
        snapshot.spark_efficiency = context.combustion.last_spark_efficiency();
        snapshot.residual_fraction = context.combustion.last_residual_fraction();
        snapshot.plant_window = context.plant_window.last();
    }
    if (context.thermal) {
        snapshot.thermal_available = true;
        snapshot.coolant_c = context.thermal->coolant_c();
        snapshot.intake_air_c = context.thermal->air_sensor_c();
        snapshot.thermostat_open_fraction =
            context.thermal->thermostat_open_fraction();
        snapshot.radiator_fan_on = context.thermal->fan_on();
    }
    if (context.injector_stage) {
        snapshot.injector_available = true;
        snapshot.injector_pulses = context.injector_stage->pulse_count();
    }
    return snapshot;
}

void run_emulator_loop(EmulatorLoopContext &context) {
    em8051 &cpu = context.cpu;
    uint16_t last_pc = cpu.mPC;
    std::array<uint8_t, 0x8000> pc_seen{};
    static thread_local MovcCounts local_movc_counts;
    static thread_local MovcBucketCounts local_movc_bucket_counts;
    LookupCounts lookup_counts;
    static thread_local IndirectReadCounts local_indirect_read_counts;
    local_movc_counts.clear();
    local_movc_bucket_counts.clear();
    local_indirect_read_counts.clear();
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
    long long stop_ticks = context.physical_stop_tick;
    if (!context.physical_crank) if (const char *setting = std::getenv("MA17_STOP_TICKS")) {
        char *end = nullptr;
        errno = 0;
        const long long parsed = std::strtoll(setting, &end, 10);
        if (*setting && *end == '\0' && errno == 0 && parsed > 0)
            stop_ticks = parsed;
        else
            fprintf(stderr, "[TRACE-STOP] invalid MA17_STOP_TICKS=%s\n", setting);
    }
    long long warm_reboot_tick = 0;
    if (const char *setting = std::getenv("MA17_WARM_REBOOT_TICK")) {
        char *end = nullptr;
        errno = 0;
        warm_reboot_tick = std::strtoll(setting, &end, 10);
        if (!*setting || *end != '\0' || errno || warm_reboot_tick <= 0) {
            fprintf(stderr, "Invalid MA17_WARM_REBOOT_TICK=%s\n", setting);
            std::exit(2);
        }
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
    if (context.on_control)
        context.on_control(context, context.control_context);
    bool previous_key_on = context.key_on;
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
        if (!context.physical_crank && context.crank.check_and_enable(context.ticks)) {
            fprintf(stderr,
                    "\n[CRANKSHAFT] *** Startup delay complete - "
                    "Beginning pulse injection @ %d RPM ***\n\n",
                    context.crank.target_rpm);
            fflush(stderr);
        }

        run_tick_batch(context, pc_seen, last_pc, stop_ticks,
                       trace_lookup_enabled ? &lookup_counts : nullptr);
        if (context.on_control)
            context.on_control(context, context.control_context);
        if (context.key_on != previous_key_on) {
            if (context.injector_stage)
                context.injector_stage->reset_electrical_state();
            context.ignition_stage.reset_charge();
            if (context.key_on) {
                reboot_cpu_with_retained_ram(cpu);
                last_pc = cpu.mPC;
            }
            previous_key_on = context.key_on;
        }
        if (warm_reboot_tick && context.ticks >= warm_reboot_tick) {
            const uint8_t retained_marker = cpu.mExtData[0xF8FF];
            reboot_cpu_with_retained_ram(cpu);
            fprintf(stderr,
                    "[WARM-REBOOT] tick=%lld xram_f8ff=%02X retained=%02X "
                    "pc=%04X\n", context.ticks, retained_marker,
                    cpu.mExtData[0xF8FF], cpu.mPC);
            last_pc = cpu.mPC;
            warm_reboot_tick = 0;
        }
        if (context.on_snapshot) {
            const auto snapshot = capture_snapshot(context);
            context.on_snapshot(snapshot, context.snapshot_context);
        }
        if (context.cancel && context.cancel->load()) {
            context.running.store(false);
            break;
        }
        context.bridge.read_and_process();
        trace_performance(cpu, context.ticks, context.startup_time);
        if (stop_ticks && context.ticks >= stop_ticks) {
            fprintf(stderr, "[TRACE-STOP] ticks=%lld\n", context.ticks);
            context.running.store(false);
            break;
        }

        // An external PTY scanner uses wall-time 5-baud bit periods.
        // Physical headless runs retain their unrestricted virtual clock.
        if (context.physical_crank && !context.physical_pty_realtime) continue;
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

    if (context.physical_crank) {
        fprintf(stdout, "[PHYSICAL-CRANK] ticks=%lld rpm=%.3f "
                        "angle_rad=%.6f rising=%llu falling=%llu "
                        "missing=%llu ram47=%u ram46=%u\n",
                context.ticks, context.physical_crank->rpm(),
                context.physical_crank->angle_rad(),
                context.physical_input->rising_edges,
                context.physical_input->falling_edges,
                context.physical_input->missing_positions,
                static_cast<unsigned>(cpu.mLowerData[0x47]),
                static_cast<unsigned>(cpu.mLowerData[0x46]));
        fprintf(stdout, "[PHYSICAL-TPS] angle_rad=%.6f contact=%d "
                        "adc0_v=%.6f adc6_v=%.6f ram60=%u ram66=%u "
                        "ram6f=%u ram70=%u ram28=%u "
                        "fault85=%u fault4f=%u\n",
                context.throttle->angle_rad(),
                context.throttle->contact_closed(),
                tps2_pin_voltage(context),
                tps1_pin_voltage(context),
                static_cast<unsigned>(cpu.mLowerData[0x60]),
                static_cast<unsigned>(cpu.mLowerData[0x66]),
                static_cast<unsigned>(cpu.mLowerData[0x6F]),
                static_cast<unsigned>(cpu.mLowerData[0x70]),
                static_cast<unsigned>(cpu.mLowerData[0x28]),
                static_cast<unsigned>(cpu.mExtData[0xF885]),
                static_cast<unsigned>(cpu.mExtData[0xF84F]));
        fprintf(stdout, "[PHYSICAL-THERMAL] air_c=%.3f wall_c=%.3f "
                        "coolant_c=%.3f iat_c=%.3f ect_c=%.3f "
                        "adc3_v=%.4f adc3_upper=%u ram61=%u "
                        "ram62=%u ram63=%u\n",
                context.thermal->air_c(), context.thermal->wall_c(),
                context.thermal->coolant_c(),
                context.thermal->air_sensor_c(),
                context.thermal->coolant_sensor_c(),
                ect_pin_voltage(context),
                static_cast<unsigned>(cpu.mUpperData[0xA8 - 0x80]),
                static_cast<unsigned>(cpu.mLowerData[0x61]),
                static_cast<unsigned>(cpu.mLowerData[0x62]),
                static_cast<unsigned>(cpu.mLowerData[0x63]));
        {
            // Energy check (GOAL_DYNO_ROM 1.4): integrated per-tick torque vs the exact
            // T * 2 rad of every pulse, discounting the unfinished tail of the last one.
            const double angle = context.physical_crank->angle_rad();
            const double tail_j =
                context.combustion.pulse_torque_nm() *
                std::max(0.0, context.combustion.pulse_end_rad() -
                                  std::max(angle, context.combustion.pulse_start_rad()));
            fprintf(stdout,
                    "[PHYSICAL-ENERGY] scheduled_j=%.9f tail_j=%.9f integrated_j=%.9f "
                    "burns=%llu\n",
                    context.combustion.energy_scheduled_j(), tail_j,
                    context.combustion_integrated_j, context.combustion.burns());
        }
        fprintf(stdout, "[PHYSICAL-INTAKE] pressure_pa=%.1f air_kg=%.9f "
                        "air_in_kg=%.9f air_out_kg=%.9f "
                        "injected_kg=%.9f film_kg=%.9f vapor_kg=%.9f "
                        "delivered_kg=%.9f cc3_pulses=%llu on_ticks=%llu "
                        "ram67=%u ram2b=%u\n",
                context.intake->pressure_pa(), context.intake->air_mass_kg(),
                context.intake->air_in_total_kg(),
                context.intake->air_delivered_total_kg(),
                context.intake->injected_total_kg(),
                context.intake->fuel_film_kg(),
                context.intake->fuel_vapor_kg(),
                context.intake->fuel_delivered_total_kg(),
                context.injector_stage->pulse_count(),
                context.injector_stage->energized_ticks(),
                static_cast<unsigned>(cpu.mLowerData[0x67]),
                static_cast<unsigned>(cpu.mLowerData[0x2B]));
        fprintf(stdout, "[PHYSICAL-ADC7] ram67=%u f8dd=%u gate2b5=%u\n",
                static_cast<unsigned>(cpu.mLowerData[0x67]),
                static_cast<unsigned>(cpu.mExtData[0xF8DD]),
                (cpu.mLowerData[0x2B] >> 5) & 1u);
        fprintf(stdout, "[PHYSICAL-ADC4] ram61=%u ram64=%u ram7d=%u\n",
                static_cast<unsigned>(cpu.mLowerData[0x61]),
                static_cast<unsigned>(cpu.mLowerData[0x64]),
                static_cast<unsigned>(cpu.mLowerData[0x7D]));
        fprintf(stdout, "[PHYSICAL-DIAG] ram27=%u f84e=%u f847=%u "
                        "f83d=%u f83c=%u f885=%u f84f=%u f850=%u "
                        "f85e=%u f85f=%u f860=%u\n",
                static_cast<unsigned>(cpu.mLowerData[0x27]),
                static_cast<unsigned>(cpu.mExtData[0xF84E]),
                static_cast<unsigned>(cpu.mExtData[0xF847]),
                static_cast<unsigned>(cpu.mExtData[0xF83D]),
                static_cast<unsigned>(cpu.mExtData[0xF83C]),
                static_cast<unsigned>(cpu.mExtData[0xF885]),
                static_cast<unsigned>(cpu.mExtData[0xF84F]),
                static_cast<unsigned>(cpu.mExtData[0xF850]),
                static_cast<unsigned>(cpu.mExtData[0xF85E]),
                static_cast<unsigned>(cpu.mExtData[0xF85F]),
                static_cast<unsigned>(cpu.mExtData[0xF860]));
        if (context.idle_bridge_candidate)
            fprintf(stdout, "[PHYSICAL-IDLE] stem_m=%.6f stop_rad=%.6f "
                            "angle_rad=%.6f contact=%d\n",
                    context.idle_actuator.stem_m(),
                    context.throttle->stop_angle_rad(),
                    context.throttle->angle_rad(),
                    context.throttle->contact_closed());
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
