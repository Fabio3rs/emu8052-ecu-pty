#include "ma17/InterruptTracer.hpp"

extern "C" {
#include "emu8051.h"
}

#include <cstdio>

namespace ma17 {

void trace_cpu_exception(em8051 *cpu, int code) {
    const char *exception_names[] = {"STACK",
                                     "ACC_TO_A",
                                     "IRET_PSW_MISMATCH",
                                     "IRET_SP_MISMATCH",
                                     "IRET_ACC_MISMATCH",
                                     "ILLEGAL_OPCODE"};
    static int exception_count = 0;
    if (exception_count >= 5)
        return;

    const unsigned char sp = cpu->mSFR[REG_SP];
    fprintf(stderr,
            "[EXCEPTION] Code %d (%s) at PC=0x%04X SP=0x%02X ACC=0x%02X\n",
            code, (code >= 0 && code <= 5) ? exception_names[code] : "UNKNOWN",
            cpu->mPC, sp, cpu->mSFR[REG_ACC]);

    const unsigned char s1 = sp < 127 ? cpu->mLowerData[sp + 1] : 0xFF;
    const unsigned char s2 = sp < 126 ? cpu->mLowerData[sp + 2] : 0xFF;
    fprintf(stderr,
            "[EXCEPTION] Stack[SP+1]=0x%02X Stack[SP+2]=0x%02X (return "
            "addr would be 0x%02X%02X)\n",
            static_cast<unsigned int>(s1), static_cast<unsigned int>(s2),
            static_cast<unsigned int>(s2), static_cast<unsigned int>(s1));
    fflush(stderr);
    exception_count++;
}

void trace_ie_write(em8051 *cpu, uint8_t address) {
    const unsigned char ie = cpu->mSFR[address - 0x80];
    static int ie_write_count = 0;
    if (ie_write_count >= 50)
        return;

    fprintf(stderr,
            "[IE WRITE] PC=0x%04X IE=0x%02X (EA=%d ET2=%d ES=%d ET1=%d "
            "EX1=%d ET0=%d EX0=%d)\n",
            cpu->mPC, ie, (ie & 0x80) ? 1 : 0, (ie & 0x20) ? 1 : 0,
            (ie & 0x10) ? 1 : 0, (ie & 0x08) ? 1 : 0, (ie & 0x04) ? 1 : 0,
            (ie & 0x02) ? 1 : 0, (ie & 0x01) ? 1 : 0);
    fflush(stderr);
    ie_write_count++;
}

void trace_ien1_write(em8051 *cpu, uint8_t address) {
    // SAB80C517 IEN1 is at B8h; generic 8051 names this address IP.
    static uint8_t last_ien1 = 0xFF;
    static int ien1_write_count = 0;
    const uint8_t new_ien1 = cpu->mSFR[address - 0x80];
    const bool old_ex3 = (last_ien1 & 0x04) != 0;
    const bool new_ex3 = (new_ien1 & 0x04) != 0;

    if (old_ex3 != new_ex3 || ien1_write_count < 20) {
        fprintf(stderr, "[IEN1] 0x%02X → 0x%02X (EX3: %d→%d) PC=0x%04X\n",
                last_ien1, new_ien1, old_ex3 ? 1 : 0, new_ex3 ? 1 : 0,
                cpu->mPC);
        fflush(stderr);
        ien1_write_count++;
    }
    last_ien1 = new_ien1;
}

} // namespace ma17
