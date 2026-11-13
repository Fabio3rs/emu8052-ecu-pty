#include "ma17/ExecutionTracer.hpp"

extern "C" {
#include "emu8051.h"
}

#include <cstdio>

namespace ma17 {

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
    if (cpu.mPC == 0x1047 || cpu.mPC == 0x115F || cpu.mPC == 0x1175 ||
        cpu.mPC == 0x11C4 || cpu.mPC == 0x11CC || cpu.mPC == 0x11D1) {
        static int tps_checks = 0;
        if (tps_checks++ < 120) {
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
        static int cc3_checks = 0;
        if (cc3_checks++ < 200) {
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
