#include "ma17/ExecutionTracer.hpp"

extern "C" {
#include "emu8051.h"
}

#include <cstdio>
#include <cstdlib>

namespace ma17 {

void apply_pre_tick_experiments(em8051 &cpu) {
    static const int forced_selector = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_RPM_SELECTOR");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long value = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || value > 0xFF) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_RPM_SELECTOR: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    static const int forced_ram69 = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_RAM69");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long value = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || value > 0xFF) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_RAM69: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    static const int forced_ram31 = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_RAM31");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long value = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || value > 0xFF) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_RAM31: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    static const int forced_ram57 = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_RAM57");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long value = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || value > 2) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_RAM57: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    static const int forced_ram78 = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_RAM78");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long value = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || value > 0xFF) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_RAM78: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    static const int forced_ram4f = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_RAM4F");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long value = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || value > 0xFF) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_RAM4F: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    static const int forced_idle_r4 = [] {
        const char *raw = std::getenv("MA17_OVERRIDE_IDLE_POSITION_R4");
        if (!raw) return -1;
        char *end = nullptr;
        const unsigned long value = std::strtoul(raw, &end, 16);
        if (end == raw || *end != '\0' || end - raw != 2 || value > 0xFF) {
            fprintf(stderr, "Invalid MA17_OVERRIDE_IDLE_POSITION_R4: %s\n", raw);
            std::exit(2);
        }
        return static_cast<int>(value);
    }();
    if (forced_idle_r4 >= 0 && cpu.mPC == 0x23B1) {
        // SAB80C517 User's Manual, Register Banks and Instruction Set:
        // PSW.RS1:RS0 selects R4; Fiat 23B1h loads the comparison bound
        // before comparing this R4 with R5 and stepping MOVX F8:3Dh.
        const uint8_t bank = cpu.mSFR[REG_PSW] & 0x18u;
        static bool announced = false;
        if (!announced) {
            fprintf(stderr,
                    "[IDLE-R4-OVERRIDE] PC=23B1 original=%02X supplied=%02X\n",
                    cpu.mLowerData[bank + 4],
                    static_cast<unsigned>(forced_idle_r4));
            announced = true;
        }
        cpu.mLowerData[bank + 4] = static_cast<uint8_t>(forced_idle_r4);
    }
    if (forced_ram4f >= 0 && cpu.mPC == 0x1588) {
        // SAB80C517 Instruction Set, MOV A,direct: Fiat opcode E5 4F
        // reads lower IRAM 4Fh here before writing the 59h:5Ah pair.
        static bool announced = false;
        if (!announced) {
            fprintf(stderr, "[RAM4F-OVERRIDE] PC=1588 original=%02X supplied=%02X\n",
                    cpu.mLowerData[0x4F], static_cast<unsigned>(forced_ram4f));
            announced = true;
        }
        cpu.mLowerData[0x4F] = static_cast<uint8_t>(forced_ram4f);
    }
    if (forced_ram78 >= 0 && cpu.mPC == 0x1D4B) {
        // SAB80C517 Instruction Set, MOV A,direct and MUL AB: Fiat reads
        // lower IRAM 78h here before multiplying by the 79h-derived B.
        static bool announced = false;
        if (!announced) {
            fprintf(stderr, "[RAM78-OVERRIDE] PC=1D4B RAM78=%02X\n",
                    static_cast<unsigned>(forced_ram78));
            announced = true;
        }
        cpu.mLowerData[0x78] = static_cast<uint8_t>(forced_ram78);
    }
    if (forced_ram57 >= 0 && cpu.mPC == 0x1378) {
        // SAB80C517 Instruction Set: MOV A,57h at 5228h selects one
        // big-endian ROM pointer. Change lower IRAM before that lookup.
        static bool announced = false;
        if (!announced) {
            fprintf(stderr, "[RAM57-OVERRIDE] PC=1378 selector=%02X\n",
                    static_cast<unsigned>(forced_ram57));
            announced = true;
        }
        cpu.mLowerData[0x57] = static_cast<uint8_t>(forced_ram57);
    }
    // Keep the RAM31, RAM69 and BC experiments out of startup before RPM exists.
    if (cpu.mLowerData[0x47] != 0x28 &&
        !(forced_ram31 >= 0 && cpu.mPC == 0x0490 &&
          cpu.mLowerData[0x47] != 0) &&
        !(forced_ram69 >= 0 && cpu.mPC == 0x043B &&
          cpu.mLowerData[0x47] != 0) &&
        !(forced_selector >= 0 && cpu.mPC == 0x330D &&
          cpu.mLowerData[0x47] != 0))
        return;
    if (forced_selector >= 0 && cpu.mPC == 0x330D && cpu.mUpperData) {
        // Siemens SAB 80C517 Instruction Set, p. 222: MOVC at 532Fh
        // reads the table index derived from upper RAM BCh at 330Dh.
        static bool announced_by_rpm_byte[256]{};
        const uint8_t rpm_byte = cpu.mLowerData[0x47];
        if (!announced_by_rpm_byte[rpm_byte]) {
            fprintf(stderr, "[RPM-SELECTOR-OVERRIDE] RAM47=%02X BC=%02X\n",
                    rpm_byte,
                    static_cast<unsigned>(forced_selector));
            announced_by_rpm_byte[rpm_byte] = true;
        }
        cpu.mUpperData[0xBC - 0x80] = static_cast<uint8_t>(forced_selector);
    }
    if (forced_ram69 >= 0 && cpu.mPC == 0x043B) {
        // SAB 80C517 Instruction Set, p. 215: MOV A,direct at 043Bh
        // is the first of two IRAM[69h] reads in the Timer 1 calculation.
        static bool announced_by_rpm_byte[256]{};
        const uint8_t rpm_byte = cpu.mLowerData[0x47];
        if (!announced_by_rpm_byte[rpm_byte]) {
            fprintf(stderr, "[RAM69-OVERRIDE] RAM47=%02X RAM69=%02X\n",
                    rpm_byte,
                    static_cast<unsigned>(forced_ram69));
            announced_by_rpm_byte[rpm_byte] = true;
        }
        cpu.mLowerData[0x69] = static_cast<uint8_t>(forced_ram69);
    }
    if (forced_ram31 >= 0 && cpu.mPC == 0x0490) {
        // SAB 80C517 Instruction Set, p. 217: MOV direct,direct at
        // 0490h copies IRAM[31h] into B for the Timer 1 calculation.
        static bool announced_by_rpm_byte[256]{};
        const uint8_t rpm_byte = cpu.mLowerData[0x47];
        if (!announced_by_rpm_byte[rpm_byte]) {
            fprintf(stderr, "[RAM31-OVERRIDE] RAM47=%02X RAM31=%02X\n",
                    rpm_byte,
                    static_cast<unsigned>(forced_ram31));
            announced_by_rpm_byte[rpm_byte] = true;
        }
        cpu.mLowerData[0x31] = static_cast<uint8_t>(forced_ram31);
    }
}

void trace_pre_tick_boot_and_crank(const em8051 &cpu, long long tick,
                                   bool crank_enabled) {
    if (cpu.mPC == 0x4BDE) {
        static int page_checks = 0;
        if (page_checks++ < 8)
            fprintf(stderr, "[KLINE-PAGE] instr=%lld P2=%02X XPAGE=%02X\n",
                    tick, cpu.mSFR[0xA0 - 0x80], cpu.mSFR[0x91 - 0x80]);
    }
    if (cpu.mPC == 0x0AAB || cpu.mPC == 0x4A36) {
        static int copy_checks = 0;
        static int compare_checks = 0;
        int &checks = cpu.mPC == 0x0AAB ? copy_checks : compare_checks;
        if (checks++ < 32) {
            const uint8_t psw = cpu.mSFR[0xD0 - 0x80];
            const uint8_t r0 = cpu.mLowerData[((psw >> 3) & 3u) * 8u];
            const uint16_t xaddr = static_cast<uint16_t>(
                (uint16_t(cpu.mSFR[0xA0 - 0x80]) << 8) | r0);
            const uint16_t dptr = static_cast<uint16_t>(
                (uint16_t(cpu.mSFR[0x83 - 0x80]) << 8) | cpu.mSFR[0x82 - 0x80]);
            fprintf(stderr,
                    "[BOOT-%s] instr=%lld P2=%02X R0=%02X "
                    "XRAM[%04X]=%02X F81E=%02X ROM[%04X]=%02X ACC=%02X\n",
                    cpu.mPC == 0x0AAB ? "COPY" : "COMPARE", tick,
                    cpu.mSFR[0xA0 - 0x80], r0, xaddr, cpu.mExtData[xaddr],
                    cpu.mExtData[0xF81E], dptr, cpu.mCodeMem[dptr],
                    cpu.mSFR[0xE0 - 0x80]);
        }
    }
    if (crank_enabled && cpu.mPC == 0x07CE) {
        static int checks = 0;
        if (checks++ < 12)
            fprintf(stderr,
                    "[CRANK-POLL] instr=%lld IRCON=%02X C4=%02X "
                    "RAM51=%02X IEN1=%02X\n",
                    tick, cpu.mSFR[0xC0 - 0x80], cpu.mUpperData[0xC4 - 0x80],
                    cpu.mLowerData[0x51], cpu.mSFR[0xB8 - 0x80]);
    }
    if (crank_enabled && cpu.mPC == 0x4AB7) {
        static int restarts = 0;
        if (restarts++ < 12)
            fprintf(stderr,
                    "[CRANK-LOOP-RESTART] instr=%lld RAM47=%02X "
                    "C4=%02X RAM51=%02X IRCON=%02X IEN1=%02X ACC=%02X "
                    "SP=%02X\n",
                    tick, cpu.mLowerData[0x47], cpu.mUpperData[0xC4 - 0x80],
                    cpu.mLowerData[0x51], cpu.mSFR[0xC0 - 0x80],
                    cpu.mSFR[0xB8 - 0x80], cpu.mSFR[0xE0 - 0x80],
                    cpu.mSFR[0x81 - 0x80]);
    }
}

void trace_pre_tick_engine(const em8051 &cpu, long long tick) {
    static const bool trace_upper_ae_source =
        std::getenv("MA17_TRACE_UPPER_AE_SOURCE") != nullptr;
    if (trace_upper_ae_source && cpu.mPC == 0x14FD) {
        static int ae_observations = 0;
        if (ae_observations++ < 1024) {
            // SAB80C517 User's Manual, On-Chip RAM and Instruction Set:
            // MOV @R0,A with R0=AEh writes upper IRAM, distinct from SFR AEh.
            const uint16_t page = static_cast<uint16_t>(
                static_cast<unsigned>(cpu.mSFR[REG_P2]) << 8);
            const unsigned bank = cpu.mSFR[REG_PSW] & 0x18u;
            std::fprintf(stderr,
                         "[UPPER-AE-SOURCE] tick=%lld PC=%04X P2=%02X "
                         "A=%02X UAE_before=%02X RAM7C=%02X "
                         "R2=%02X R3=%02X R7=%02X X6B=%02X X6C=%02X\n",
                         tick, cpu.mPC, cpu.mSFR[REG_P2],
                         cpu.mSFR[REG_ACC], cpu.mUpperData[0xAE - 0x80],
                         cpu.mLowerData[0x7C], cpu.mLowerData[bank + 2],
                         cpu.mLowerData[bank + 3], cpu.mLowerData[bank + 7],
                         cpu.mExtData[(page | 0x6Bu) & cpu.mExtDataMaxIdx],
                         cpu.mExtData[(page | 0x6Cu) & cpu.mExtDataMaxIdx]);
        }
    }
    static const bool trace_78xx_path =
        std::getenv("MA17_TRACE_78XX_PATH") != nullptr;
    if (trace_78xx_path && (cpu.mPC == 0x1CB7 || cpu.mPC == 0x1CDF)) {
        static int consumer_observations = 0;
        if (consumer_observations++ < 1000) {
            // SAB80C517 Instruction Set, MOVX @R0 and MUL AB: Fiat
            // 1CB7h..1CDFh consumes the P2-paged byte written at 3E33h.
            const uint16_t page = static_cast<uint16_t>(
                static_cast<unsigned>(cpu.mSFR[REG_P2]) << 8);
            std::fprintf(stderr,
                         "[78XX-CONSUMER] tick=%lld PC=%04X P2=%02X "
                         "X01=%02X XFB=%02X RAM7A=%02X RAM7B=%02X "
                         "A=%02X B=%02X R1=%02X\n",
                         tick, cpu.mPC, cpu.mSFR[REG_P2],
                         cpu.mExtData[(page | 0x01u) & cpu.mExtDataMaxIdx],
                         cpu.mExtData[(page | 0xFBu) & cpu.mExtDataMaxIdx],
                         cpu.mLowerData[0x7A], cpu.mLowerData[0x7B],
                         cpu.mSFR[REG_ACC], cpu.mSFR[REG_B],
                         cpu.mLowerData[(cpu.mSFR[REG_PSW] & 0x18u) + 1]);
        }
    }
    if (trace_78xx_path &&
        (cpu.mPC == 0x3DC1 || cpu.mPC == 0x3DC7 ||
         cpu.mPC == 0x3DD6 || cpu.mPC == 0x3DDC ||
         cpu.mPC == 0x1863 ||
         cpu.mPC == 0x3E1A || cpu.mPC == 0x3E25 ||
         cpu.mPC == 0x3E2E || cpu.mPC == 0x3E33)) {
        static int observations = 0;
        if (observations++ < 3000) {
            // SAB80C517 Instruction Set, MOVC/MOVX @Ri: observe the
            // pointer-selected ROM lookup and P2-paged XRAM destination.
            const uint8_t bank = cpu.mSFR[REG_PSW] & 0x18u;
            std::fprintf(stderr,
                         "[78XX-PATH] tick=%lld PC=%04X DPTR=%02X%02X "
                         "P2=%02X R0=%02X R1=%02X R5=%02X R6=%02X "
                         "A=%02X RAM6E=%02X RAM5B=%02X F28=%02X F2F=%02X\n",
                         tick, cpu.mPC, cpu.mSFR[0x83 - 0x80],
                         cpu.mSFR[0x82 - 0x80], cpu.mSFR[REG_P2],
                         cpu.mLowerData[bank], cpu.mLowerData[bank + 1],
                         cpu.mLowerData[bank + 5], cpu.mLowerData[bank + 6],
                         cpu.mSFR[REG_ACC], cpu.mLowerData[0x6E],
                         cpu.mLowerData[0x5B],
                         cpu.mLowerData[0x28], cpu.mLowerData[0x2F]);
        }
    }
    static const bool trace_7939_index =
        std::getenv("MA17_TRACE_7939_INDEX") != nullptr;
    if (trace_7939_index && (cpu.mPC == 0x3DD6 || cpu.mPC == 0x3DDC ||
                             cpu.mPC == 0x3DDE)) {
        static int observations = 0;
        if (observations++ < 4000) {
            // SAB80C517 User's Manual, Instruction Set: MOVC reads A+DPTR;
            // Fiat 3DDCh stores the interpolated accumulator in direct 5Bh.
            const uint8_t bank = cpu.mSFR[REG_PSW] & 0x18u;
            std::fprintf(stderr,
                         "[7939-INDEX] tick=%lld PC=%04X DPTR=%02X%02X "
                         "R0=%02X R2=%02X R3=%02X R4=%02X R5=%02X "
                         "R6=%02X A=%02X RAM5B=%02X RAM47=%02X "
                         "RAM70=%02X F28=%02X F2F=%02X\n",
                         tick, cpu.mPC, cpu.mSFR[0x83 - 0x80],
                         cpu.mSFR[0x82 - 0x80], cpu.mLowerData[bank],
                         cpu.mLowerData[bank + 2], cpu.mLowerData[bank + 3],
                         cpu.mLowerData[bank + 4], cpu.mLowerData[bank + 5],
                         cpu.mLowerData[bank + 6], cpu.mSFR[REG_ACC],
                         cpu.mLowerData[0x5B], cpu.mLowerData[0x47],
                         cpu.mLowerData[0x70], cpu.mLowerData[0x28],
                         cpu.mLowerData[0x2F]);
        }
    }
    static const bool trace_timer1_path =
        std::getenv("MA17_TRACE_TIMER1_PATH") != nullptr;
    if (trace_timer1_path && cpu.mLowerData[0x47] != 0 &&
        (cpu.mPC == 0x0090 || cpu.mPC == 0x0223 ||
         cpu.mPC == 0x0252 || cpu.mPC == 0x0286 ||
         cpu.mPC == 0x0298)) {
        // SAB80C517 User's Manual, Timer 0/1 and SFR map: TCON.TR1/TF1
        // control Timer 1, while Fiat code loads TL1/TH1 from 34h:35h
        // or 32h:33h at 0286h/0298h before the P5.0/P5.1 service.
        std::fprintf(stderr,
                     "[TIMER1-PATH] tick=%lld PC=%04X TCON=%02X "
                     "TMOD=%02X TL1=%02X TH1=%02X P5=%02X "
                     "F2A=%02X RAM30=%02X R32_33=%02X%02X "
                     "R34_35=%02X%02X\n",
                     tick, cpu.mPC, cpu.mSFR[REG_TCON],
                     cpu.mSFR[REG_TMOD], cpu.mSFR[REG_TL1],
                     cpu.mSFR[REG_TH1], cpu.mSFR[0xF8 - 0x80],
                     cpu.mLowerData[0x2A], cpu.mLowerData[0x30],
                     cpu.mLowerData[0x32], cpu.mLowerData[0x33],
                     cpu.mLowerData[0x34], cpu.mLowerData[0x35]);
    }
    static const bool trace_idle_position_gate =
        std::getenv("MA17_TRACE_IDLE_POSITION_GATE") != nullptr;
    if (trace_idle_position_gate && cpu.mPC == 0x23AF) {
        static int observations = 0;
        if (observations++ < 4096) {
            // SAB80C517 Instruction Set: JC tests PSW.CY after the ORL C
            // guards; these flags are lower IRAM bit addresses.
            std::fprintf(stderr,
                         "[IDLE-POSITION-GATE] tick=%lld PC=23AF CY=%u "
                         "RAM63=%02X RAM46=%02X RAM47=%02X "
                         "F20=%02X F24=%02X F28=%02X F2D=%02X F2E=%02X "
                         "PSW=%02X\n",
                         tick, (cpu.mSFR[REG_PSW] >> 7) & 1u,
                         cpu.mLowerData[0x63], cpu.mLowerData[0x46],
                         cpu.mLowerData[0x47], cpu.mLowerData[0x20],
                         cpu.mLowerData[0x24], cpu.mLowerData[0x28],
                         cpu.mLowerData[0x2D], cpu.mLowerData[0x2E],
                         cpu.mSFR[REG_PSW]);
        }
    }
    if (trace_idle_position_gate && cpu.mPC == 0x23B9) {
        // SAB80C517 User's Manual, Register Banks: PSW.RS1:RS0 selects
        // R4/R5. The following JNB/JNZ decide whether F8:3Dh can step.
        const uint8_t bank = cpu.mSFR[REG_PSW] & 0x18u;
        std::fprintf(stderr,
                     "[IDLE-POSITION-STEP] tick=%lld PC=23B9 R4=%02X "
                     "R5=%02X RAM46=%02X RAM47=%02X F20=%02X "
                     "XRAM3D=%02X\n",
                     tick, cpu.mLowerData[bank + 4],
                     cpu.mLowerData[bank + 5], cpu.mLowerData[0x46],
                     cpu.mLowerData[0x47], cpu.mLowerData[0x20],
                     cpu.mExtData[0xF83D]);
    }
    static const bool trace_idle_fault =
        std::getenv("MA17_TRACE_IDLE_FAULT") != nullptr;
    if (trace_idle_fault && (cpu.mPC == 0x2B38 || cpu.mPC == 0x2B39 ||
                             cpu.mPC == 0x2B3C || cpu.mPC == 0x2B42 ||
                             cpu.mPC == 0x2B44 || cpu.mPC == 0x2B49)) {
        static int observations = 0;
        if (observations++ < 128) {
            // SAB80C517 User's Manual, Register Banks and MOVX @Ri:
            // PSW selects R0/R2/R3; P2 supplies the XRAM high address.
            const uint8_t bank = cpu.mSFR[REG_PSW] & 0x18u;
            const uint8_t r0 = cpu.mLowerData[bank];
            const uint16_t address = static_cast<uint16_t>(
                (uint16_t(cpu.mSFR[REG_P2]) << 8) | r0);
            std::fprintf(stderr,
                         "[IDLE-FAULT-GATE] tick=%lld PC=%04X R0=%02X "
                         "R2=%02X R3=%02X XRAM=%04X:%02X A=%02X "
                         "F24=%02X F27=%02X PSW=%02X\n",
                         tick, cpu.mPC, r0, cpu.mLowerData[bank + 2],
                         cpu.mLowerData[bank + 3], address,
                         cpu.mExtData[address & cpu.mExtDataMaxIdx],
                         cpu.mSFR[REG_ACC], cpu.mLowerData[0x24],
                         cpu.mLowerData[0x27], cpu.mSFR[REG_PSW]);
        }
    }
    static const bool trace_ram31_gate =
        std::getenv("MA17_TRACE_RAM31_GATE") != nullptr;
    if (trace_ram31_gate && cpu.mLowerData[0x47] != 0 &&
        (cpu.mPC == 0x0490 || cpu.mPC == 0x049B)) {
        static int gate_observations = 0;
        if (gate_observations++ < 1000) {
            // SAB 80C517 Instruction Set, p. 217: MOV direct,direct at
            // 0490h copies IRAM[31h] to B; 049Bh stores the carry in 22h.7.
            fprintf(stderr,
                    "[RAM31-GATE] tick=%lld PC=%04X RAM47=%02X "
                    "RAM31=%02X RAM69=%02X A=%02X B=%02X PSW=%02X F22=%02X\n",
                    tick, cpu.mPC, cpu.mLowerData[0x47],
                    cpu.mLowerData[0x31], cpu.mLowerData[0x69],
                    cpu.mSFR[0xE0 - 0x80], cpu.mSFR[0xF0 - 0x80],
                    cpu.mSFR[0xD0 - 0x80], cpu.mLowerData[0x22]);
        }
    }
    static const bool trace_ram78_gate =
        std::getenv("MA17_TRACE_RAM78_GATE") != nullptr;
    if (trace_ram78_gate && (cpu.mPC == 0x1B34 || cpu.mPC == 0x1B3D ||
                             cpu.mPC == 0x1B48 || cpu.mPC == 0x1B77 ||
                             cpu.mPC == 0x1BD2 || cpu.mPC == 0x1BFD ||
                             cpu.mPC == 0x1C34 || cpu.mPC == 0x1C7D)) {
        static int observations = 0;
        if (observations++ < 1200) {
            // SAB80C517 User's Manual, On-Chip RAM: PSW.RS1:RS0 select
            // the R-register bank; 21h and 78h are direct lower IRAM.
            const uint8_t bank = (cpu.mSFR[REG_PSW] & 0x18u);
            fprintf(stderr,
                    "[RAM78-GATE] tick=%lld PC=%04X R1=%02X R6=%02X "
                    "R7=%02X F21=%02X F2E=%02X F2F=%02X "
                    "RAM70=%02X RAM72=%02X RAM78=%02X\n",
                    tick, cpu.mPC, cpu.mLowerData[bank + 1],
                    cpu.mLowerData[bank + 6], cpu.mLowerData[bank + 7],
                    cpu.mLowerData[0x21], cpu.mLowerData[0x2E],
                    cpu.mLowerData[0x2F], cpu.mLowerData[0x70],
                    cpu.mLowerData[0x72], cpu.mLowerData[0x78]);
        }
    }
    static const bool trace_coolant_gate =
        std::getenv("MA17_TRACE_COOLANT_GATE") != nullptr;
    if (trace_coolant_gate && (cpu.mPC == 0x465D || cpu.mPC == 0x467C ||
                               cpu.mPC == 0x4686 || cpu.mPC == 0x469C ||
                               cpu.mPC == 0x46C6 || cpu.mPC == 0x46E6 ||
                               cpu.mPC == 0x4756)) {
        static int coolant_checks = 0;
        if (coolant_checks++ < 4096 || coolant_checks % 512 == 0) {
            // SAB80C517 User's Manual, On-Chip RAM and Instruction Set:
            // PSW selects the bank; @R1 accesses upper IRAM, and MOVX @R1
            // uses the P2 page for external addresses D7h/D9h.
            const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
            const uint16_t page = static_cast<uint16_t>(
                uint16_t(cpu.mSFR[0xA0 - 0x80]) << 8);
            fprintf(stderr,
                    "[COOLANT-GATE] tick=%lld PC=%04X R2=%02X R3=%02X "
                    "R5=%02X R6=%02X A8=%02X A9=%02X F28=%02X "
                    "F29=%02X F2D=%02X F2E=%02X P2=%02X "
                    "XRAMD7=%02X XRAMD9=%02X\n",
                    tick, cpu.mPC, cpu.mLowerData[bank + 2],
                    cpu.mLowerData[bank + 3], cpu.mLowerData[bank + 5],
                    cpu.mLowerData[bank + 6], cpu.mUpperData[0xA8 - 0x80],
                    cpu.mUpperData[0xA9 - 0x80], cpu.mLowerData[0x28],
                    cpu.mLowerData[0x29], cpu.mLowerData[0x2D],
                    cpu.mLowerData[0x2E], cpu.mSFR[0xA0 - 0x80],
                    cpu.mExtData[page | 0xD7], cpu.mExtData[page | 0xD9]);
        }
    }
    static const bool trace_air_gate =
        std::getenv("MA17_TRACE_AIR_716C_GATE") != nullptr;
    if (trace_air_gate && cpu.mPC == 0x11A8) {
        static int set_events = 0;
        if (set_events++ < 200) {
            // SAB80C517 User's Manual, On-Chip RAM: @R1=BFh reads upper IRAM.
            const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
            fprintf(stderr,
                    "[AIR-2E6-SET] tick=%lld PC=11A8 UBF=%02X "
                    "R1=%02X R2=%02X R3=%02X F2E=%02X PSW=%02X\n",
                    tick, cpu.mUpperData[0xBF - 0x80],
                    cpu.mLowerData[bank + 1], cpu.mLowerData[bank + 2],
                    cpu.mLowerData[bank + 3], cpu.mLowerData[0x2E],
                    cpu.mSFR[0xD0 - 0x80]);
        }
    }
    if (trace_air_gate && (cpu.mPC == 0x3C73 || cpu.mPC == 0x3CB7 ||
                           cpu.mPC == 0x3CDA ||
                           cpu.mPC == 0x3CE2 || cpu.mPC == 0x3CE6 ||
                           cpu.mPC == 0x3CFC || cpu.mPC == 0x3D08 ||
                           cpu.mPC == 0x3D0B || cpu.mPC == 0x3D0C ||
                           cpu.mPC == 0x397D || cpu.mPC == 0x398D ||
                           cpu.mPC == 0x39F4)) {
        static int air_gate_checks = 0;
        if (air_gate_checks++ < 3000) {
            // SAB80C517 Instruction Set: @R1 addresses upper IRAM, while
            // direct bit address C9h addresses SFR C8h. Keep them separate.
            fprintf(stderr,
                    "[AIR-716C-GATE] tick=%lld PC=%04X ADC2=%02X "
                    "UCC=%02X UAE=%02X UC8=%02X PSW=%02X "
                    "SFR_C8=%02X F22=%02X F2E=%02X F2F=%02X "
                    "RAM6F=%02X R2=%02X A=%02X B=%02X\n",
                    tick, cpu.mPC, cpu.mLowerData[0x62],
                    cpu.mUpperData[0xCC - 0x80],
                    cpu.mUpperData[0xAE - 0x80],
                    cpu.mUpperData[0xC8 - 0x80],
                    cpu.mSFR[0xD0 - 0x80], cpu.mSFR[0xC8 - 0x80],
                    cpu.mLowerData[0x22], cpu.mLowerData[0x2E],
                    cpu.mLowerData[0x2F], cpu.mLowerData[0x6F],
                    cpu.mLowerData[(cpu.mSFR[0xD0 - 0x80] & 0x18) + 2],
                    cpu.mSFR[0xE0 - 0x80], cpu.mSFR[0xF0 - 0x80]);
        }
    }
    static const bool trace_7e16_gate =
        std::getenv("MA17_TRACE_7E16_GATE") != nullptr;
    if (trace_7e16_gate && (cpu.mPC == 0x1B77 || cpu.mPC == 0x1B7A ||
                           cpu.mPC == 0x1C0F || cpu.mPC == 0x1D60 ||
                           cpu.mPC == 0x1D96 || cpu.mPC == 0x36DE ||
                           cpu.mPC == 0x36EC || cpu.mPC == 0x3701 ||
                           cpu.mPC == 0x371D || cpu.mPC == 0x3739 ||
                           cpu.mPC == 0x3752 ||
                           cpu.mPC == 0x3775 || cpu.mPC == 0x378C ||
                           cpu.mPC == 0x37E3 || cpu.mPC == 0x37FB ||
                           cpu.mPC == 0x3830 || cpu.mPC == 0x3849)) {
        static int checks = 0;
        if (checks++ < 3000) {
            // SAB80C517 Instruction Set: JBC/JNB at 36DEh..3752h test
            // B bits and lower IRAM bits before the MOVC matrix path.
            const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
            fprintf(stderr,
                    "[MATRIX-7E16-GATE] tick=%lld PC=%04X F21=%02X "
                    "F2F=%02X B=%02X A=%02X R0=%02X R1=%02X "
                    "R2=%02X R3=%02X RAM47=%02X "
                    "RAM70=%02X RAM72=%02X RAM78=%02X\n",
                    tick, cpu.mPC, cpu.mLowerData[0x21],
                    cpu.mLowerData[0x2F], cpu.mSFR[0xF0 - 0x80],
                    cpu.mSFR[0xE0 - 0x80], cpu.mLowerData[bank],
                    cpu.mLowerData[bank + 1], cpu.mLowerData[bank + 2],
                    cpu.mLowerData[bank + 3], cpu.mLowerData[0x47],
                    cpu.mLowerData[0x70], cpu.mLowerData[0x72],
                    cpu.mLowerData[0x78]);
        }
    }
    static const bool trace_matrix_path =
        std::getenv("MA17_TRACE_MATRIX_PATH") != nullptr;
    if (trace_matrix_path && (cpu.mPC == 0x3CDA || cpu.mPC == 0x3CE2 ||
                              cpu.mPC == 0x3CE6 || cpu.mPC == 0x3CFC ||
                              cpu.mPC == 0x3D08 || cpu.mPC == 0x3D0B)) {
        static int carry_checks = 0;
        if (carry_checks++ < 4000) {
            const uint8_t p2 = cpu.mSFR[0xA0 - 0x80];
            // SAB80C517 User's Manual: MOVX @R0 selects the P2 data page;
            // PSW.C and PSW.F0 (bit address D5h) are separate gate states.
            fprintf(stderr,
                    "[MATRIX-CARRY] tick=%lld PC=%04X C=%u A=%02X "
                    "F0=%u T2CON=%02X RAM2F=%02X RAM22=%02X "
                    "RAM57=%02X RAM63=%02X P2=%02X X9F=%02X\n",
                    tick, cpu.mPC, (cpu.mSFR[0xD0 - 0x80] >> 7) & 1u,
                    cpu.mSFR[0xE0 - 0x80],
                    (cpu.mSFR[0xD0 - 0x80] >> 5) & 1u,
                    cpu.mSFR[0xC8 - 0x80], cpu.mLowerData[0x2F],
                    cpu.mLowerData[0x22], cpu.mLowerData[0x57],
                    cpu.mLowerData[0x63], p2,
                    cpu.mExtData[((static_cast<unsigned int>(p2) << 8) |
                                  0x9Fu) & cpu.mExtDataMaxIdx]);
        }
    }
    if (trace_matrix_path && (cpu.mPC == 0x3D0C || cpu.mPC == 0x3341 ||
                              cpu.mPC == 0x3356 || cpu.mPC == 0x3369)) {
        static int selector_checks = 0;
        if (selector_checks++ < 4000) {
            const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
            // SAB80C517 Instruction Set: MOV bit,C at 3D0Ch stores carry
            // in IRAM 2Fh.2; JB at 3350h selects the matrix pointer.
            fprintf(stderr,
                    "[MATRIX-SELECTOR] tick=%lld PC=%04X C=%u "
                    "RAM2F=%02X RAM22=%02X RAM28=%02X RAM2E=%02X "
                    "RAM57=%02X R4=%02X R5=%02X UAE=%02X UBC=%02X "
                    "DPTR=%04X\n",
                    tick, cpu.mPC, (cpu.mSFR[0xD0 - 0x80] >> 7) & 1u,
                    cpu.mLowerData[0x2F], cpu.mLowerData[0x22],
                    cpu.mLowerData[0x28], cpu.mLowerData[0x2E],
                    cpu.mLowerData[0x57], cpu.mLowerData[bank + 4],
                    cpu.mLowerData[bank + 5],
                    cpu.mUpperData[0xAE - 0x80], cpu.mUpperData[0xBC - 0x80],
                    static_cast<unsigned int>(cpu.mSFR[0x83 - 0x80] << 8) |
                        cpu.mSFR[0x82 - 0x80]);
        }
    }
    if (trace_matrix_path && cpu.mPC == 0x1412) {
        const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
        const uint8_t r4 = cpu.mLowerData[bank + 4];
        const uint8_t r5 = cpu.mLowerData[bank + 5];
        const uint8_t ram27 = cpu.mLowerData[0x27];
        const uint8_t ram2c = cpu.mLowerData[0x2C];
        const uint8_t t2con = cpu.mSFR[0xC8 - 0x80];
        const unsigned state = r4 | (unsigned(r5) << 8) |
                               (unsigned(ram27 & 0xC0) << 10) |
                               (unsigned(ram2c & 0x20) << 13) |
                               (unsigned(t2con & 0x02) << 24);
        static unsigned previous_state = ~0u;
        if (state != previous_state) {
            // SAB80C517 User's Manual: PSW selects the R register bank;
            // T2CON.T2I1 is bit 1, tested by the original ROM at 1414h.
            fprintf(stderr,
                    "[MATRIX-PRE] tick=%lld PC=1412 R4=%02X R5=%02X "
                    "RAM27=%02X RAM2C=%02X T2CON=%02X\n",
                    tick, r4, r5, ram27, ram2c, t2con);
            previous_state = state;
        }
    }
    if (trace_matrix_path && cpu.mPC == 0x145E) {
        const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
        const uint8_t index = cpu.mLowerData[bank + 5];
        static int previous_index = -1;
        if (index != previous_index) {
            // SAB80C517 User's Manual: PSW.RS1:RS0 select the R0-R7 bank.
            fprintf(stderr,
                    "[MATRIX-INDEX] tick=%lld PC=145E R4=%02X R5=%02X "
                    "RAM27=%02X RAM63=%02X RAM65=%02X\n",
                    tick, cpu.mLowerData[bank + 4], index,
                    cpu.mLowerData[0x27], cpu.mLowerData[0x63],
                    cpu.mLowerData[0x65]);
            previous_index = index;
        }
    }
    if (trace_matrix_path && (cpu.mPC == 0x199E || cpu.mPC == 0x19A2 ||
                              cpu.mPC == 0x19A6 || cpu.mPC == 0x19AC ||
                              cpu.mPC == 0x19B2)) {
        static int state_checks = 0;
        if (state_checks++ < 3000) {
            const uint8_t psw = cpu.mSFR[0xD0 - 0x80];
            const uint8_t bank = (psw >> 3 & 3u) * 8u;
            // SAB80C517 User's Manual: PSW selects the register bank.
            fprintf(stderr,
                    "[MATRIX-STATE] tick=%lld PC=%04X PSW=%02X "
                    "R6=%02X R7=%02X RAM27=%02X RAM2C=%02X RAM2F=%02X\n",
                    tick, cpu.mPC, psw, cpu.mLowerData[bank + 6],
                    cpu.mLowerData[bank + 7], cpu.mLowerData[0x27],
                    cpu.mLowerData[0x2C], cpu.mLowerData[0x2F]);
        }
    }
    if (trace_matrix_path && (cpu.mPC == 0x0FEF || cpu.mPC == 0x1047 ||
                              cpu.mPC == 0x10EC || cpu.mPC == 0x1104 ||
                              cpu.mPC == 0x113C)) {
        static int flag_checks = 0;
        if (flag_checks++ < 3000) {
            const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
            // SAB80C517 Instruction Set: MOVX A,@R0 at 0FECh reads via P2.
            fprintf(stderr,
                    "[MATRIX-FLAG] tick=%lld PC=%04X P2=%02X A=%02X "
                    "B=%02X PSW=%02X R2=%02X R4=%02X "
                    "RAM28=%02X RAM60=%02X RAM66=%02X\n",
                    tick, cpu.mPC, cpu.mSFR[0xA0 - 0x80],
                    cpu.mSFR[0xE0 - 0x80], cpu.mSFR[0xF0 - 0x80],
                    cpu.mSFR[0xD0 - 0x80], cpu.mLowerData[bank + 2],
                    cpu.mLowerData[bank + 4],
                    cpu.mLowerData[0x28], cpu.mLowerData[0x60],
                    cpu.mLowerData[0x66]);
        }
    }
    if (trace_matrix_path && (cpu.mPC == 0x137B || cpu.mPC == 0x1386 ||
                              cpu.mPC == 0x145E || cpu.mPC == 0x147E ||
                              cpu.mPC == 0x1487 || cpu.mPC == 0x14C2 ||
                              cpu.mPC == 0x14D9 || cpu.mPC == 0x14F0 ||
                              cpu.mPC == 0x150E || cpu.mPC == 0x1523)) {
        static int matrix_checks = 0;
        if (matrix_checks++ < 3000) {
            const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
            const uint8_t p2 = cpu.mSFR[0xA0 - 0x80];
            const uint16_t base = static_cast<uint16_t>(
                static_cast<unsigned int>(p2) << 8);
            // SAB80C517 Instruction Set, pp. 222, 224: MOVC returns the
            // matrix byte; MOVX @Ri uses the external-data page from P2.
            // At 137Bh, A:B is the lookup result before MOV R2,B; MOV R3,A.
            fprintf(stderr,
                    "[MATRIX-PATH] tick=%lld PC=%04X P2=%02X "
                    "X92=%02X X93=%02X R2=%02X R3=%02X R4=%02X R5=%02X A=%02X B=%02X "
                    "PSW=%02X RAM27=%02X RAM28=%02X RAM48=%02X RAM7C=%02X\n",
                    tick, cpu.mPC, p2,
                    cpu.mExtData[(base | 0x92u) & cpu.mExtDataMaxIdx],
                    cpu.mExtData[(base | 0x93u) & cpu.mExtDataMaxIdx],
                    cpu.mLowerData[bank + 2], cpu.mLowerData[bank + 3],
                    cpu.mLowerData[bank + 4], cpu.mLowerData[bank + 5],
                    cpu.mSFR[0xE0 - 0x80], cpu.mSFR[0xF0 - 0x80],
                    cpu.mSFR[0xD0 - 0x80],
                    cpu.mLowerData[0x27], cpu.mLowerData[0x28],
                    cpu.mLowerData[0x48], cpu.mLowerData[0x7C]);
        }
    }
    static const bool trace_terminal_segment =
        std::getenv("MA17_TRACE_TERMINAL_SEGMENT") != nullptr;
    if (trace_terminal_segment && cpu.mPC == 0x3341) {
        static int terminal_source_checks = 0;
        if (terminal_source_checks++ < 200) {
            // SAB80C517 User's Manual, Instruction Set, MOV bit,C:
            // Fiat 3341h copies carry (selected from RAM28h) into B.3.
            fprintf(stderr,
                    "[TERMINAL-SOURCE] tick=%lld PC=%04X C=%u "
                    "RAM28=%02X RAM2E=%02X B=%02X U94=%02X\n",
                    tick, cpu.mPC, (cpu.mSFR[REG_PSW] >> 7) & 1u,
                    cpu.mLowerData[0x28], cpu.mLowerData[0x2E],
                    cpu.mSFR[REG_B], cpu.mUpperData[0x94 - 0x80]);
        }
    }
    if (trace_terminal_segment && cpu.mPC == 0x3A7D) {
        static int terminal_gate_checks = 0;
        if (terminal_gate_checks++ < 200) {
            const uint8_t bank = cpu.mSFR[REG_PSW] & 0x18u;
            // SAB80C517 User's Manual, Instruction Set, JB and MOV A,@R0:
            // Fiat 3A7Dh begins gates that test B.3 at 3A80h, upper
            // IRAM and the low bits of @R0.
            fprintf(stderr,
                    "[TERMINAL-GATE] tick=%lld PC=%04X B=%02X A=%02X "
                    "RAM22=%02X U9B=%02X UCB=%02X UC9=%02X R0=%02X\n",
                    tick, cpu.mPC, cpu.mSFR[REG_B], cpu.mSFR[REG_ACC],
                    cpu.mLowerData[0x22], cpu.mUpperData[0x9B - 0x80],
                    cpu.mUpperData[0xCB - 0x80],
                    cpu.mUpperData[0xC9 - 0x80], cpu.mLowerData[bank]);
        }
    }
    if (trace_terminal_segment && (cpu.mPC == 0x3AAD || cpu.mPC == 0x3AB3)) {
        static int terminal_checks = 0;
        if (terminal_checks++ < 200) {
            const uint8_t bank = cpu.mSFR[0xD0 - 0x80] & 0x18u;
            // SAB80C517 User's Manual, Instruction Set, MOV A,@R0:
            // Fiat 527Fh reads the lower-IRAM address from ROM[7F8Dh].
            fprintf(stderr,
                    "[TERMINAL-SEGMENT] tick=%lld PC=%04X RAM0F=%02X "
                    "RAM28=%02X RAM35=%02X R3=%02X U83=%02X "
                    "U8C=%02X RAM69=%02X\n",
                    tick, cpu.mPC, cpu.mLowerData[0x0F],
                    cpu.mLowerData[0x28],
                    cpu.mLowerData[0x35], cpu.mLowerData[bank + 3],
                    cpu.mUpperData[0x83 - 0x80],
                    cpu.mUpperData[0x8C - 0x80], cpu.mLowerData[0x69]);
        }
    }
    static const bool trace_ram69 = std::getenv("MA17_TRACE_RAM69") != nullptr;
    if (trace_ram69 && (cpu.mPC == 0x330D || cpu.mPC == 0x3356 ||
                        cpu.mPC == 0x3371 ||
                        cpu.mPC == 0x3A04 || cpu.mPC == 0x3AD2 ||
                        cpu.mPC == 0x3AD3 || cpu.mPC == 0x3AE0 ||
                        cpu.mPC == 0x3B06)) {
        static int ram69_checks = 0;
        if (ram69_checks++ < 2000) {
            const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
            // Siemens SAB 80C517 Instruction Set, p. 222: MOVC at 3AD2h
            // reads code memory at (A + DPTR); the 330Dh path reads upper
            // IRAM AEh through the 7B28h segment header, not SFR AEh.
            fprintf(stderr,
                    "[RAM69-PATH] tick=%lld PC=%04X A=%02X B=%02X "
                    "DPTR=%02X%02X R2=%02X R5=%02X R6=%02X R7=%02X "
                    "UBC=%02X UAE=%02X U83=%02X U8C=%02X "
                    "RAM47=%02X RAM69=%02X flags2B=%02X PSW=%02X\n",
                    tick, cpu.mPC, cpu.mSFR[0xE0 - 0x80],
                    cpu.mSFR[0xF0 - 0x80], cpu.mSFR[0x83 - 0x80],
                    cpu.mSFR[0x82 - 0x80], cpu.mLowerData[bank + 2],
                    cpu.mLowerData[bank + 5], cpu.mLowerData[bank + 6],
                    cpu.mLowerData[bank + 7],
                    cpu.mUpperData[0xBC - 0x80],
                    cpu.mUpperData[0xAE - 0x80],
                    cpu.mUpperData[0x83 - 0x80],
                    cpu.mUpperData[0x8C - 0x80], cpu.mLowerData[0x47],
                    cpu.mLowerData[0x69],
                    cpu.mLowerData[0x2B], cpu.mSFR[0xD0 - 0x80]);
        }
    }
    static const bool trace_lambda = std::getenv("MA17_TRACE_LAMBDA") != nullptr;
    static const bool trace_ram4d_path =
        std::getenv("MA17_TRACE_RAM4D_PATH") != nullptr;
    if (trace_ram4d_path &&
        (cpu.mPC == 0x220C || cpu.mPC == 0x220E ||
         cpu.mPC == 0x497A || cpu.mPC == 0x4997 ||
         cpu.mPC == 0x499F)) {
        static int curve_gate_checks = 0;
        if (curve_gate_checks++ < 2000) {
            // SAB80C517 Instruction Set, bit operations and MOVC/MOVX:
            // inspect the Fiat guard before its P2-paged lookup result.
            const uint8_t bank = cpu.mSFR[REG_PSW] & 0x18u;
            std::fprintf(stderr,
                         "[RAM4D-CURVE-GATE] tick=%lld PC=%04X "
                         "RAM22=%02X UA5=%02X RAM57=%02X "
                         "R2=%02X R5=%02X R6=%02X A=%02X PSW=%02X\n",
                         tick, cpu.mPC, cpu.mLowerData[0x22],
                         cpu.mUpperData[0xA5 - 0x80], cpu.mLowerData[0x57],
                         cpu.mLowerData[bank + 2], cpu.mLowerData[bank + 5],
                         cpu.mLowerData[bank + 6], cpu.mSFR[REG_ACC],
                         cpu.mSFR[REG_PSW]);
        }
    }
    if (trace_ram4d_path && (cpu.mPC == 0x22F3 || cpu.mPC == 0x2320 ||
                             cpu.mPC == 0x233B || cpu.mPC == 0x2580 ||
                             cpu.mPC == 0x2593)) {
        static int ram4d_checks = 0;
        if (ram4d_checks++ < 6000) {
            // SAB80C517 Instruction Set, section 9.1 and MUL AB entry:
            // direct 4Dh is lower IRAM; 2322h multiplies its R2 copy in B.
            const uint8_t bank = cpu.mSFR[0xD0 - 0x80] & 0x18u;
            fprintf(stderr,
                    "[RAM4D-PATH] tick=%lld PC=%04X RAM4D=%02X "
                    "RAM49=%02X P2=%02X R1=%02X R2=%02X R3=%02X "
                    "A=%02X B=%02X PSW=%02X\n",
                    tick, cpu.mPC, cpu.mLowerData[0x4D],
                    cpu.mLowerData[0x49], cpu.mSFR[0xA0 - 0x80],
                    cpu.mLowerData[bank + 1],
                    cpu.mLowerData[bank + 2], cpu.mLowerData[bank + 3],
                    cpu.mSFR[0xE0 - 0x80], cpu.mSFR[0xF0 - 0x80],
                    cpu.mSFR[0xD0 - 0x80]);
        }
    }
    static const bool trace_ram5b_gate =
        std::getenv("MA17_TRACE_RAM5B_GATE") != nullptr;
    if (trace_ram5b_gate && (cpu.mPC == 0x183C || cpu.mPC == 0x1840 ||
                            cpu.mPC == 0x1843 || cpu.mPC == 0x1846 ||
                            cpu.mPC == 0x1853 || cpu.mPC == 0x1863 ||
                            cpu.mPC == 0x18B2 || cpu.mPC == 0x18B5 ||
                            cpu.mPC == 0x18D9 || cpu.mPC == 0x1952 ||
                            cpu.mPC == 0x1958 || cpu.mPC == 0x1971 ||
                            cpu.mPC == 0x199A || cpu.mPC == 0x19B6 ||
                            cpu.mPC == 0x19D0 || cpu.mPC == 0x19D2)) {
        static int ram5b_gate_checks = 0;
        if (ram5b_gate_checks++ < 3000) {
            const uint8_t bank = cpu.mSFR[0xD0 - 0x80] & 0x18u;
            // SAB80C517 User's Manual, Instruction Set: JB/JNB test the
            // call guard; MUL AB, ADDC and MOVX carry 5Bh toward F8:0Ch.
            fprintf(stderr,
                    "[RAM5B-GATE] tick=%lld PC=%04X RAM2C=%02X "
                    "RAM5B=%02X R4=%02X R5=%02X R6=%02X R7=%02X "
                    "RAM5C=%02X RAM5D=%02X A=%02X B=%02X PSW=%02X\n",
                    tick, cpu.mPC, cpu.mLowerData[0x2C],
                    cpu.mLowerData[0x5B], cpu.mLowerData[bank + 4],
                    cpu.mLowerData[bank + 5], cpu.mLowerData[bank + 6],
                    cpu.mLowerData[bank + 7], cpu.mLowerData[0x5C],
                    cpu.mLowerData[0x5D], cpu.mSFR[0xE0 - 0x80],
                    cpu.mSFR[0xF0 - 0x80], cpu.mSFR[0xD0 - 0x80]);
        }
    }
    // Siemens SAB 80C517 Instruction Set, p. 222: MOVC at 186Fh reads
    // code memory at A+DPTR; 1870h observes the returned accumulator.
    if (trace_lambda && (cpu.mPC == 0x153A || cpu.mPC == 0x155A ||
                         cpu.mPC == 0x155B || cpu.mPC == 0x1562 ||
                         cpu.mPC == 0x1644 || cpu.mPC == 0x17C2 ||
                         cpu.mPC == 0x17E8 || cpu.mPC == 0x17ED ||
                         cpu.mPC == 0x1810 || cpu.mPC == 0x181B ||
                         cpu.mPC == 0x1825 || cpu.mPC == 0x182D ||
                         cpu.mPC == 0x186D || cpu.mPC == 0x1870 ||
                         cpu.mPC == 0x1889 || cpu.mPC == 0x190B ||
                         cpu.mPC == 0x19B6 || cpu.mPC == 0x19D0 ||
                         cpu.mPC == 0x19D9 || cpu.mPC == 0x19E1)) {
        static int lambda_checks = 0;
        if (lambda_checks++ < 20000) {
            const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
            fprintf(stderr,
                    "[LAMBDA-GATE] tick=%lld PC=%04X RAM65=%02X "
                    "F80C=%02X R4=%02X R5=%02X R6=%02X R7=%02X "
                    "RAM47=%02X RAM62=%02X RAM63=%02X "
                    "RAM5C=%02X RAM5D=%02X RAM3C=%02X RAM3D=%02X "
                    "RAM1A=%02X RAM87=%02X A=%02X B=%02X DPTR=%02X%02X PSW=%02X "
                    "flags25=%02X flags26=%02X flags28=%02X "
                    "flags29=%02X flags2C=%02X flags2D=%02X "
                    "flags2E=%02X flags2F=%02X T2I0=%u T2I1=%u\n",
                    tick, cpu.mPC, cpu.mLowerData[0x65],
                    cpu.mExtData[0xF80C], cpu.mLowerData[bank + 4],
                    cpu.mLowerData[bank + 5], cpu.mLowerData[bank + 6],
                    cpu.mLowerData[bank + 7], cpu.mLowerData[0x47],
                    cpu.mLowerData[0x62], cpu.mLowerData[0x63],
                    cpu.mLowerData[0x5C],
                    cpu.mLowerData[0x5D], cpu.mLowerData[0x3C],
                    cpu.mLowerData[0x3D], cpu.mLowerData[0x1A],
                    cpu.mUpperData[0x87 - 0x80], cpu.mSFR[0xE0 - 0x80],
                    cpu.mSFR[0xF0 - 0x80], cpu.mSFR[0x83 - 0x80],
                    cpu.mSFR[0x82 - 0x80], cpu.mSFR[0xD0 - 0x80],
                    cpu.mLowerData[0x25], cpu.mLowerData[0x26],
                    cpu.mLowerData[0x28], cpu.mLowerData[0x29],
                    cpu.mLowerData[0x2C],
                    cpu.mLowerData[0x2D], cpu.mLowerData[0x2E],
                    cpu.mLowerData[0x2F],
                    cpu.mSFR[0xC8 - 0x80] & 1u,
                    (cpu.mSFR[0xC8 - 0x80] >> 1) & 1u);
        }
    }
    if (cpu.mPC == 0x1D4B || cpu.mPC == 0x1DD8 ||
        cpu.mPC == 0x1E02 || cpu.mPC == 0x1ED3) {
        static int injection_checks = 0;
        if (injection_checks++ < 1200) {
            const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
            fprintf(stderr,
                    "[INJECTION-FLOW] tick=%lld PC=%04X R2=%02X R3=%02X "
                    "RAM63=%02X RAM78=%02X RAM48=%02X DPTR=%02X%02X "
                    "PSW=%02X FLAGS25=%02X FLAGS2E=%02X\n",
                    tick, cpu.mPC, cpu.mLowerData[bank + 2],
                    cpu.mLowerData[bank + 3], cpu.mLowerData[0x63],
                    cpu.mLowerData[0x78], cpu.mLowerData[0x48],
                    cpu.mSFR[0x83 - 0x80], cpu.mSFR[0x82 - 0x80],
                    cpu.mSFR[0xD0 - 0x80], cpu.mLowerData[0x25],
                    cpu.mLowerData[0x2E]);
            if (cpu.mPC == 0x1D4B)
                fprintf(stderr,
                        "[INJECTION-INPUT] tick=%lld R1=%02X R4=%02X "
                        "R5=%02X R6=%02X R7=%02X B=%02X RAM59=%02X "
                        "RAM5A=%02X FLAGS2F=%02X\n",
                        tick, cpu.mLowerData[bank + 1],
                        cpu.mLowerData[bank + 4], cpu.mLowerData[bank + 5],
                        cpu.mLowerData[bank + 6], cpu.mLowerData[bank + 7],
                        cpu.mSFR[0xF0 - 0x80], cpu.mLowerData[0x59],
                        cpu.mLowerData[0x5A], cpu.mLowerData[0x2F]);
        }
    }
    if (cpu.mPC == 0x3291 || cpu.mPC == 0x32B8) {
        static int table_checks = 0;
        if (table_checks++ < 200) {
            const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
            fprintf(stderr,
                    "[ENGINE-TABLE] tick=%lld PC=%04X R3=%02X "
                    "R4=%02X R5=%02X R6=%02X B=%02X A=%02X "
                    "RAM31=%02X RAM7D=%02X RAM7F=%02X\n",
                    tick, cpu.mPC, cpu.mLowerData[bank + 3],
                    cpu.mLowerData[bank + 4], cpu.mLowerData[bank + 5],
                    cpu.mLowerData[bank + 6], cpu.mSFR[0xF0 - 0x80],
                    cpu.mSFR[0xE0 - 0x80], cpu.mLowerData[0x31],
                    cpu.mLowerData[0x7D], cpu.mLowerData[0x7F]);
        }
    }
    if (cpu.mPC == 0x4329) {
        static int fault_triplet_checks = 0;
        if (fault_triplet_checks++ < 64) {
            const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
            fprintf(stderr,
                    "[FAULT-TRIPLET] tick=%lld R3=%02X R7=%02X "
                    "XRAM4E=%02X XRAM4F=%02X XRAM50=%02X\n",
                    tick, cpu.mLowerData[bank + 3], cpu.mLowerData[bank + 7],
                    cpu.mExtData[0xF84E], cpu.mExtData[0xF84F],
                    cpu.mExtData[0xF850]);
        }
    }
    if (cpu.mPC == 0x1047 || cpu.mPC == 0x10F3 || cpu.mPC == 0x1104 ||
        cpu.mPC == 0x1132 || cpu.mPC == 0x1159 || cpu.mPC == 0x115F ||
        cpu.mPC == 0x1175 || cpu.mPC == 0x11C4 || cpu.mPC == 0x11CC ||
        cpu.mPC == 0x11D1) {
        // Siemens SAB80C517 Instruction Set (local SAB80C517.PDF): these
        // are original ROM instruction PCs; the optional window only
        // selects observations and does not write CPU or peripheral state.
        static const unsigned long long start_tick = [] {
            const char *raw = std::getenv("MA17_TRACE_TPS_AFTER_TICK");
            if (!raw) return 0ULL;
            char *end = nullptr;
            const unsigned long long value = std::strtoull(raw, &end, 10);
            if (end == raw || *end != '\0') {
                fprintf(stderr, "Invalid MA17_TRACE_TPS_AFTER_TICK: %s\n", raw);
                std::exit(2);
            }
            return value;
        }();
        static int tps_checks = 0;
        if (tick >= 0 && static_cast<unsigned long long>(tick) >= start_tick &&
            tps_checks++ < 120) {
            const uint8_t bank = (cpu.mSFR[0xD0 - 0x80] >> 3 & 3u) * 8u;
            fprintf(stderr,
                    "[TPS-FLOW] tick=%lld PC=%04X R2=%02X R3=%02X "
                    "R4=%02X B=%02X A=%02X PSW=%02X RAM28=%02X "
                    "RAM2E=%02X RAM6D=%02X DPTR=%02X%02X\n",
                    tick, cpu.mPC, cpu.mLowerData[bank + 2],
                    cpu.mLowerData[bank + 3], cpu.mLowerData[bank + 4],
                    cpu.mSFR[0xF0 - 0x80], cpu.mSFR[0xE0 - 0x80],
                    cpu.mSFR[0xD0 - 0x80], cpu.mLowerData[0x28],
                    cpu.mLowerData[0x2E], cpu.mLowerData[0x6D],
                    cpu.mSFR[0x83 - 0x80], cpu.mSFR[0x82 - 0x80]);
        }
    }
}

void trace_pre_tick_cc3(const em8051 &cpu, long long tick) {
    if (cpu.mPC == 0x058E || cpu.mPC == 0x5469) {
        // SAB80C517 Timer 2 compare (local datasheet): observe the
        // firmware's CC3 schedule after a selected emulated tick only.
        static const unsigned long long start_tick = [] {
            const char *raw = std::getenv("MA17_TRACE_CC3_AFTER_TICK");
            if (!raw) return 0ULL;
            char *end = nullptr;
            const unsigned long long value = std::strtoull(raw, &end, 10);
            if (end == raw || *end != '\0') {
                fprintf(stderr, "Invalid MA17_TRACE_CC3_AFTER_TICK: %s\n", raw);
                std::exit(2);
            }
            return value;
        }();
        static int cc3_checks = 0;
        if (tick >= 0 && static_cast<unsigned long long>(tick) >= start_tick &&
            cc3_checks++ < 200) {
            const uint8_t psw = cpu.mSFR[0xD0 - 0x80];
            const uint8_t bank = ((psw >> 3) & 3u) * 8u;
            fprintf(stderr,
                    "[CC3-ENTRY] instr=%lld PC=%04X flags2B=%02X "
                    "flags26=%02X IRAM14_15=%02X%02X R2_R3=%02X%02X "
                    "P1=%02X CCEN=%02X\n",
                    tick, cpu.mPC, cpu.mLowerData[0x2B], cpu.mLowerData[0x26],
                    cpu.mLowerData[0x14], cpu.mLowerData[0x15],
                    cpu.mLowerData[bank + 2], cpu.mLowerData[bank + 3],
                    cpu.mSFR[0x90 - 0x80], cpu.mSFR[0xC1 - 0x80]);
        }
    }
    if (cpu.mPC == 0x3B0B) {
        static int gate_checks = 0;
        if (gate_checks++ < 32) {
            const uint8_t p2 = cpu.mSFR[0xA0 - 0x80];
            const uint8_t xpage = cpu.mSFR[0x91 - 0x80];
            fprintf(stderr,
                    "[CC3-GATE] instr=%lld P2=%02X XPAGE=%02X "
                    "ACC=%02X XRAM_F8DD=%02X XRAM_F9DD=%02X "
                    "flags2B=%02X RAM67=%02X\n",
                    tick, p2, xpage, cpu.mSFR[0xE0 - 0x80],
                    cpu.mExtData[0xF8DD], cpu.mExtData[0xF9DD],
                    cpu.mLowerData[0x2B], cpu.mLowerData[0x67]);
        }
    }
}

} // namespace ma17
