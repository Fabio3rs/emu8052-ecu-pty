#include <gtest/gtest.h>
#include <algorithm>
#include <array>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <tuple>
#include <utility>
#include "ma17/AdcSimulator.hpp"
extern "C" {
#include "emu8051.h"
}

TEST(SampleTest, BasicTest) {
    EXPECT_EQ(1, 1);
}

#ifdef __SAB80C517__
TEST(Sab80C517, FiatAdcReadsC517aResultAfterStartingConversion) {
    // SAB80C517A User's Manual Addendum, ADC registers (p. 5-6): DAh
    // returns result bits 1:0 in positions 7:6 after starting conversion.
    std::array<unsigned char, 32> code{};
    std::array<unsigned char, 32> xram{};
    em8051 cpu{};
    cpu.mCodeMem = code.data();
    cpu.mCodeMemMaxIdx = 31;
    cpu.mExtData = xram.data();
    cpu.mExtDataMaxIdx = 31;
    reset(&cpu, true);
    cpu.sfrread[0xD9 - 0x80] = ma17::read_addat;
    cpu.sfrread[0xDA - 0x80] = ma17::read_addatl;
    cpu.sfrwrite[0xDA - 0x80] = ma17::start_adc_conversion;
    cpu.mSFR[0xD8 - 0x80] = 0x85; // ADC channel 5
    const unsigned char program[]{
        0x75, 0xDA, 0x85, // MOV ADDATL,#85h: starts conversion
        0xE5, 0xDA,       // MOV A,ADDATL
        0x23,             // RL A
        0x54, 0x01,       // ANL A,#1
        0x25, 0xD9,       // ADD A,ADDATH
    };
    std::copy(std::begin(program), std::end(program), code.begin());
    for (int step = 0; step < 5; ++step) {
        cpu.mTickDelay = 0;
        tick(&cpu);
    }
    EXPECT_EQ(cpu.mSFR[REG_ACC], ma17::read_adc_channel(5));
    EXPECT_EQ(cpu.mSFR[REG_ACC], 110); // No artificial +1 from 85h.
}

TEST(Sab80C517, PortReadModifyWriteUsesLatchWhileMovReadsPin) {
    unsigned char code[256]{};
    unsigned char xram[256]{};
    em8051 cpu{};
    cpu.mCodeMem = code;
    cpu.mCodeMemMaxIdx = 255;
    cpu.mExtData = xram;
    cpu.mExtDataMaxIdx = 255;
    reset(&cpu, true);
    cpu.mSFR[0xF8 - 0x80] = 0;
    cpu.sfrread[0xF8 - 0x80] = +[](em8051 *, uint8_t) -> uint8_t {
        return 0x03; // External P5.0/1 high, independent of output latch.
    };
    const unsigned char program[] = {
        0x43, 0xF8, 0x00, // ORL P5,#00h: latch remains zero
        0xE5, 0xF8,       // MOV A,P5: sees external pins
        0x05, 0xF8,       // INC P5: latch becomes one
        0x53, 0xF8, 0x01, // ANL P5,#01h: latch remains one
        0x63, 0xF8, 0x02, // XRL P5,#02h: latch becomes three
        0x15, 0xF8,       // DEC P5: latch becomes two
        0xD5, 0xF8, 0x00, // DJNZ P5,+0: latch becomes one
    };
    std::copy(std::begin(program), std::end(program), code);
    const auto step = [&] {
        cpu.mTickDelay = 0;
        tick(&cpu);
    };

    step(); EXPECT_EQ(cpu.mSFR[0xF8 - 0x80], 0);
    step(); EXPECT_EQ(cpu.mSFR[REG_ACC], 0x03);
    step(); EXPECT_EQ(cpu.mSFR[0xF8 - 0x80], 1);
    step(); EXPECT_EQ(cpu.mSFR[0xF8 - 0x80], 1);
    step(); EXPECT_EQ(cpu.mSFR[0xF8 - 0x80], 3);
    step(); EXPECT_EQ(cpu.mSFR[0xF8 - 0x80], 2);
    step(); EXPECT_EQ(cpu.mSFR[0xF8 - 0x80], 1);
}

TEST(Sab80C517, MovDirectIndirectReadsWhileMovIndirectDirectWrites) {
    std::array<unsigned char, 256> code{};
    std::array<unsigned char, 256> xram{};
    std::array<unsigned char, 128> upper{};
    em8051 cpu{};
    cpu.mCodeMem = code.data();
    cpu.mCodeMemMaxIdx = 255;
    cpu.mExtData = xram.data();
    cpu.mExtDataMaxIdx = 255;
    cpu.mUpperData = upper.data();
    reset(&cpu, true);
    const unsigned char program[]{
        0x86, 0xF0, // MOV B,@R0 (upper IRAM to direct SFR)
        0x87, 0x30, // MOV 30h,@R1 (lower IRAM to direct IRAM)
        0xA6, 0xF0, // MOV @R0,B (direct SFR to upper IRAM)
        0xA7, 0x30, // MOV @R1,30h (direct to indirect lower IRAM)
    };
    std::copy(std::begin(program), std::end(program), code.begin());
    cpu.mSFR[REG_PSW] = 0x08;
    cpu.mLowerData[0x08] = 0x87;
    cpu.mLowerData[0x09] = 0x42;
    cpu.mUpperData[0x87 - 0x80] = 0x5A;
    cpu.mLowerData[0x42] = 0xA5;
    cpu.mLowerData[0x30] = 0x22;
    cpu.mSFR[REG_B] = 0x11;
    const auto step = [&] {
        cpu.mTickDelay = 0;
        tick(&cpu);
    };
    step();
    EXPECT_EQ(cpu.mSFR[REG_B], 0x5A);
    EXPECT_EQ(cpu.mUpperData[0x87 - 0x80], 0x5A);
    step();
    EXPECT_EQ(cpu.mLowerData[0x30], 0xA5);
    EXPECT_EQ(cpu.mLowerData[0x42], 0xA5);
    cpu.mSFR[REG_B] = 0xC3;
    step();
    EXPECT_EQ(cpu.mUpperData[0x87 - 0x80], 0xC3);
    cpu.mLowerData[0x30] = 0x66;
    step();
    EXPECT_EQ(cpu.mLowerData[0x42], 0x66);
}

TEST(Sab80C517, ResetRegistersInterruptCallbacksAtSfrIndices) {
    unsigned char code[256]{};
    unsigned char xram[256]{};
    em8051 cpu{};
    cpu.mCodeMem = code;
    cpu.mCodeMemMaxIdx = 255;
    cpu.mExtData = xram;
    cpu.mExtDataMaxIdx = 255;
    reset(&cpu, true);

    for (auto index : {REG_IEN0, REG_IEN1, REG_IEN2, REG_IP0, REG_IP1}) {
        ASSERT_NE(cpu.sfrwrite[index], nullptr);
        cpu.sfrwrite[index](&cpu, static_cast<uint8_t>(index + 0x80));
        EXPECT_EQ(cpu.irq_inhibit, 1);
        cpu.irq_inhibit = 0;
    }
}

TEST(Sab80C517, Timer2UsesC517PrescalerAndReloadBits) {
    unsigned char code[256]{};
    unsigned char xram[256]{};
    em8051 cpu{};
    cpu.mCodeMem = code;
    cpu.mCodeMemMaxIdx = 255;
    cpu.mExtData = xram;
    cpu.mExtDataMaxIdx = 255;
    reset(&cpu, true);
    cpu.mSFR[REG_T2CON] = 0x85; // Timer, fOSC/24, reload disabled
    cpu.mSFR[REG_TL2] = 0xFE;
    cpu.mSFR[REG_TH2] = 0xFF;
    cpu.mSFR[REG_RCAP2L] = 0x34;
    cpu.mSFR[REG_RCAP2H] = 0x12;

    tick(&cpu);
    EXPECT_EQ(cpu.mSFR[REG_TL2], 0xFE);
    tick(&cpu);
    EXPECT_EQ(cpu.mSFR[REG_TL2], 0xFF);
    tick(&cpu);
    tick(&cpu);
    EXPECT_EQ(cpu.mSFR[REG_TL2], 0x00);
    EXPECT_EQ(cpu.mSFR[REG_TH2], 0x00);
    EXPECT_NE(cpu.mSFR[REG_IRCON] & IRCONMASK_TF2, 0);

    cpu.mSFR[REG_T2CON] = 0x11; // Timer, overflow reload enabled
    cpu.mSFR[REG_TL2] = 0xFF;
    cpu.mSFR[REG_TH2] = 0xFF;
    tick(&cpu);
    EXPECT_EQ(cpu.mSFR[REG_TL2], 0x34);
    EXPECT_EQ(cpu.mSFR[REG_TH2], 0x12);
}

TEST(Sab80C517, Timer2CountsExternalEdgesAndReloadsFromT2ex) {
    unsigned char code[256]{};
    unsigned char xram[256]{};
    em8051 cpu{};
    cpu.mCodeMem = code;
    cpu.mCodeMemMaxIdx = 255;
    cpu.mExtData = xram;
    cpu.mExtDataMaxIdx = 255;
    reset(&cpu, true);
    cpu.mSFR[REG_T2CON] = 0x02; // Counter input P1.7
    tick(&cpu);
    EXPECT_EQ(cpu.mSFR[REG_TL2], 0);
    cpu.mSFR[REG_P1] &= 0x7F;
    tick(&cpu);
    EXPECT_EQ(cpu.mSFR[REG_TL2], 1);
    tick(&cpu);
    EXPECT_EQ(cpu.mSFR[REG_TL2], 1);

    cpu.mSFR[REG_T2CON] = 0x19; // Timer, external reload mode
    cpu.mSFR[REG_IEN1] = IEN1MASK_EXEN2;
    cpu.mSFR[REG_RCAP2L] = 0x34;
    cpu.mSFR[REG_RCAP2H] = 0x12;
    tick(&cpu);
    cpu.mSFR[REG_P1] &= 0xDF; // Falling T2EX/P1.5
    tick(&cpu);
    EXPECT_EQ(cpu.mSFR[REG_TL2], 0x34);
    EXPECT_EQ(cpu.mSFR[REG_TH2], 0x12);
    EXPECT_NE(cpu.mSFR[REG_IRCON] & IRCONMASK_EXF2, 0);
}

TEST(Sab80C517, RetiRestoresInterruptedPriorityLevel) {
    unsigned char code[256]{};
    unsigned char xram[256]{};
    em8051 cpu{};
    cpu.mCodeMem = code;
    cpu.mCodeMemMaxIdx = 255;
    cpu.mExtData = xram;
    cpu.mExtDataMaxIdx = 255;
    reset(&cpu, true);
    code[0x0B] = 0x32; // RETI at Timer 0 vector
    cpu.mSFR[REG_IEN0] = IEN0MASK_EA | IEN0MASK_ET0;
    cpu.mSFR[REG_IP0] = 0x02; // Timer 0 priority level 1
    cpu.mSFR[REG_TCON] = 0x20; // TF0

    tick(&cpu);
    EXPECT_EQ(cpu.mInterruptActive, 1);
    EXPECT_EQ(cpu.int_prev_level_517[1], SAB80C517_NO_INT_ACTIVE);
    tick(&cpu);
    tick(&cpu);
    EXPECT_EQ(cpu.mInterruptActive, SAB80C517_NO_INT_ACTIVE);
    EXPECT_EQ(cpu.mPC, 0);
}

TEST(Sab80C517, MovxIndirectUsesPort2Page) {
    unsigned char code[256]{};
    std::array<unsigned char, 65536> xram{};
    em8051 cpu{};
    cpu.mCodeMem = code;
    cpu.mCodeMemMaxIdx = 255;
    cpu.mExtData = xram.data();
    cpu.mExtDataMaxIdx = 65535;
    reset(&cpu, true);
    const unsigned char program[] = {
        0x78, 0xF8,       // MOV R0,#F8h
        0x75, 0xA0, 0xF8, // MOV P2,#F8h
        0x74, 0x5A,       // MOV A,#5Ah
        0xF2,             // MOVX @R0,A
        0x74, 0x00,       // MOV A,#0
        0xE2,             // MOVX A,@R0
        0x80, 0xFE        // SJMP $
    };
    std::copy(std::begin(program), std::end(program), code);
    xram[0x00F8] = 0x11;

    for (int i = 0; i < 24; ++i)
        tick(&cpu);
    EXPECT_EQ(xram[0xF8F8], 0x5A);
    EXPECT_EQ(xram[0x00F8], 0x11);
    EXPECT_EQ(cpu.mSFR[REG_ACC], 0x5A);
}

TEST(Sab80C517, XpageTracksPort2AndSelectsInternalXram) {
    unsigned char code[256]{};
    std::array<unsigned char, 65536> xram{};
    em8051 cpu{};
    cpu.mCodeMem = code;
    cpu.mCodeMemMaxIdx = 255;
    cpu.mExtData = xram.data();
    cpu.mExtDataMaxIdx = 65535;
    reset(&cpu, true);
    EXPECT_EQ(cpu.mSFR[REG_XPAGE], 0);
    EXPECT_EQ(cpu.mSFR[REG_SYSCON] & 1, 1);
    const unsigned char program[] = {
        0x75, 0xA0, 0xF8, // MOV P2,#F8h; also loads XPAGE
        0x75, 0x91, 0xF9, // MOV XPAGE,#F9h; P2 stays F8h
        0x75, 0xB1, 0x02, // MOV SYSCON,#2; enable internal XRAM
        0x78, 0x1E,       // MOV R0,#1Eh
        0x74, 0x5A,       // MOV A,#5Ah
        0xF2,             // MOVX @R0,A => F91Eh
        0xC0, 0x91,       // PUSH XPAGE
        0x75, 0xA0, 0x00, // MOV P2,#0; also loads XPAGE=0
        0xD0, 0xA0,       // POP P2; restores F9h to P2 and XPAGE
        0xE2,             // MOVX A,@R0 => F91Eh
        0x80, 0xFE        // SJMP $
    };
    std::copy(std::begin(program), std::end(program), code);
    for (int i = 0; i < 40; ++i)
        tick(&cpu);
    EXPECT_EQ(xram[0xF91E], 0x5A);
    EXPECT_EQ(xram[0xF81E], 0);
    EXPECT_EQ(cpu.mSFR[REG_P2], 0xF9);
    EXPECT_EQ(cpu.mSFR[REG_XPAGE], 0xF9);
    EXPECT_EQ(cpu.mSFR[REG_ACC], 0x5A);
}

TEST(Sab80C517, FirmwareRestoringDivisionHandlesSharedEntry) {
    // Fiat MA1.7 ROM 5367h..5386h: entry 5367h computes an A/R5 fraction.
    constexpr std::array<unsigned char, 32> program = {
        0x7B, 0x00, 0x7C, 0x00, 0x79, 0x08, 0x7E, 0x00,
        0xC3, 0xCB, 0x33, 0xCB, 0x33, 0xCE, 0x33, 0xCE,
        0x9D, 0xCE, 0x9C, 0xCE, 0x50, 0x04, 0x2D, 0xCE,
        0x3C, 0xCE, 0xD9, 0xED, 0xEB, 0x33, 0xF4, 0x22,
    };
    for (const auto [dividend, divisor] : {
             std::pair{0, 5}, std::pair{1, 2}, std::pair{3, 4},
             std::pair{9, 10}, std::pair{10, 10}, std::pair{100, 10}}) {
        std::array<unsigned char, 256> code{};
        unsigned char xram[256]{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 255;
        cpu.mExtData = xram;
        cpu.mExtDataMaxIdx = 255;
        reset(&cpu, true);
        std::copy(program.begin(), program.end(), code.begin());
        cpu.mSFR[REG_ACC] = static_cast<unsigned char>(dividend);
        cpu.mLowerData[5] = static_cast<unsigned char>(divisor);
        for (int step = 0; step < 1000 && cpu.mPC != 31; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 31);
        EXPECT_EQ(cpu.mSFR[REG_ACC], std::min(255, (dividend << 8) / divisor))
            << "dividend=" << dividend << " divisor=" << divisor
            << " R3=" << static_cast<int>(cpu.mLowerData[3])
            << " R5=" << static_cast<int>(cpu.mLowerData[5])
            << " R6=" << static_cast<int>(cpu.mLowerData[6])
            << " PSW=" << static_cast<int>(cpu.mSFR[REG_PSW]);
    }

    // Entry 536Bh preserves the caller's low dividend and high divisor bytes.
    for (const auto [high, low, divisor_high, divisor_low] : {
             std::array{0, 100, 0, 10}, std::array{1, 44, 0, 5},
             std::array{0x12, 0x34, 1, 0}, std::array{1, 44, 1, 44}}) {
        std::array<unsigned char, 256> code{};
        unsigned char xram[256]{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 255;
        cpu.mExtData = xram;
        cpu.mExtDataMaxIdx = 255;
        reset(&cpu, true);
        std::copy(program.begin(), program.end(), code.begin());
        cpu.mPC = 4; // Skip MOV R3,#0 and MOV R4,#0.
        cpu.mSFR[REG_ACC] = static_cast<unsigned char>(high);
        cpu.mLowerData[3] = static_cast<unsigned char>(low);
        cpu.mLowerData[4] = static_cast<unsigned char>(divisor_high);
        cpu.mLowerData[5] = static_cast<unsigned char>(divisor_low);
        for (int step = 0; step < 1000 && cpu.mPC != 31; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 31);
        const int dividend = (high << 8) | low;
        const int divisor = (divisor_high << 8) | divisor_low;
        EXPECT_EQ(cpu.mSFR[REG_ACC], dividend / divisor)
            << "dividend=" << dividend << " divisor=" << divisor;
    }

    std::array<unsigned char, 256> code{};
    unsigned char xram[256]{};
    em8051 cpu{};
    cpu.mCodeMem = code.data();
    cpu.mCodeMemMaxIdx = 255;
    cpu.mExtData = xram;
    cpu.mExtDataMaxIdx = 255;
    reset(&cpu, true);
    std::copy(program.begin(), program.end(), code.begin());
    cpu.mPC = 6; // 536Dh: caller selects the number of restoring steps.
    cpu.mLowerData[1] = 9;
    cpu.mLowerData[3] = 100;
    cpu.mLowerData[5] = 10;
    for (int step = 0; step < 1200 && cpu.mPC != 31; ++step)
        tick(&cpu);
    ASSERT_EQ(cpu.mPC, 31);
    EXPECT_EQ(cpu.mSFR[REG_ACC], 20); // One extra step doubles 100/10.
}

TEST(Sab80C517, FirmwareScaledMultiplyRoundsQ8) {
    // Exact Fiat MA1.7 opcodes at 561Ah..5638h; RET is at offset 30.
    constexpr std::array<unsigned char, 31> program = {
        0xEB, 0xFD, 0xEA, 0xFC, 0x74, 0xBC, 0x93, 0xF5,
        0xF0, 0xCD, 0xA4, 0xCC, 0xC5, 0xF0, 0xCD, 0xA4,
        0xCC, 0x25, 0xF0, 0xCD, 0x34, 0x00, 0xCC, 0x33,
        0xE4, 0x3D, 0xCC, 0x34, 0x00, 0xFD, 0x22,
    };
    for (const auto [value, factor] : {
             std::pair{0, 255}, std::pair{0x101, 0x80},
             std::pair{0x1234, 0x80}, std::pair{0xFFFF, 0xFF}}) {
        std::array<unsigned char, 256> code{};
        unsigned char xram[256]{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 255;
        cpu.mExtData = xram;
        cpu.mExtDataMaxIdx = 255;
        reset(&cpu, true);
        std::copy(program.begin(), program.end(), code.begin());
        code[0xBC] = static_cast<unsigned char>(factor);
        cpu.mLowerData[2] = static_cast<unsigned char>(value & 0xFF);
        cpu.mLowerData[3] = static_cast<unsigned char>(value >> 8);
        for (int step = 0; step < 100 && cpu.mPC != 30; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 30);
        EXPECT_EQ((cpu.mLowerData[5] << 8) | cpu.mLowerData[4],
                  ((value * factor) + 128) >> 8)
            << "value=" << value << " factor=" << factor;
    }
}

TEST(Sab80C517, FirmwareThresholdClassifierUsesTwoRomBounds) {
    // Exact Fiat MA1.7 opcodes at 2FF4h..3010h; stop before either RET.
    constexpr std::array<unsigned char, 29> program = {
        0xE3, 0xF5, 0xF0, 0x74, 0x6B, 0x93, 0xB5, 0xF0,
        0x00, 0x40, 0x03, 0xD2, 0xD5, 0x22, 0x74, 0x6A,
        0x93, 0xC5, 0xF0, 0xB5, 0xF0, 0x00, 0x40, 0x02,
        0xE5, 0xF0, 0xC2, 0xD5, 0x22,
    };
    for (int value : {50, 100, 101, 150, 160}) {
        std::array<unsigned char, 256> code{};
        unsigned char xram[256]{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 255;
        cpu.mExtData = xram;
        cpu.mExtDataMaxIdx = 255;
        reset(&cpu, true);
        std::copy(program.begin(), program.end(), code.begin());
        code[0x6A] = 150;
        code[0x6B] = 100;
        cpu.mSFR[REG_P2] = 0;
        cpu.mLowerData[1] = 0x20;
        xram[0x20] = static_cast<unsigned char>(value);
        for (int step = 0; step < 40 && cpu.mPC != 13 && cpu.mPC != 28; ++step)
            tick(&cpu);
        ASSERT_TRUE(cpu.mPC == 13 || cpu.mPC == 28);
        EXPECT_EQ(cpu.mSFR[REG_ACC], value <= 100 ? 100 : std::min(value, 150));
        EXPECT_EQ((cpu.mSFR[REG_PSW] & 0x20) != 0, value <= 100);
    }
}

TEST(Sab80C517, FiatP53GateUsesP47CoolantThresholdAndBit225) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    ASSERT_EQ(original[0x72C5], 0x0E);

    struct Case {
        uint8_t p47, ram63, flags22, psw;
        bool p53_low;
    };
    for (const auto test : {
             Case{1, 0x0F, 0, 0x20, true},
             Case{0, 0x0F, 0, 0x20, false},
             Case{1, 0x0E, 0, 0x20, false},
             Case{1, 0x0F, 0x20, 0x20, false},
             Case{1, 0x0F, 0, 0, false}}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mPC = 0x2202;
        cpu.mSFR[REG_DPH] = 0x72;
        cpu.mSFR[REG_DPL] = 0;
        cpu.mSFR[REG_ACC] = 0xC5;
        cpu.mSFR[REG_PSW] = test.psw;
        cpu.mSFR[0xE8 - 0x80] = test.p47 ? 0x80 : 0;
        cpu.mSFR[0xF8 - 0x80] = 0x08;
        cpu.mLowerData[0x22] = test.flags22;
        cpu.mLowerData[0x63] = test.ram63;
        // SAB80C517: MOVC A,@A+DPTR reads 72C5h, then MOV P5.3,C
        // writes the latch. These opcodes do not prove ECU wiring.
        for (int step = 0; step < 20 && cpu.mPC != 0x2211; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
            if (test.p53_low && cpu.mPC == 0x2203)
                EXPECT_EQ(cpu.mSFR[REG_ACC], 0x0E);
            if (test.p53_low &&
                (cpu.mPC == 0x2206 || cpu.mPC == 0x2208 ||
                 cpu.mPC == 0x220A || cpu.mPC == 0x220C))
                EXPECT_NE(cpu.mSFR[REG_PSW] & 0x80, 0) << std::hex << cpu.mPC;
        }
        ASSERT_EQ(cpu.mPC, 0x2211);
        EXPECT_EQ((cpu.mSFR[0xF8 - 0x80] & 0x08) == 0, test.p53_low);
        EXPECT_EQ((cpu.mLowerData[0x22] & 0x10) != 0, test.p53_low);
    }
}

TEST(Sab80C517, FirmwareMultiplyRegisterPairsReturnsProductShiftedEight) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    for (const auto [left, right] : {
             std::pair{0x0000, 0xFFFF}, std::pair{0x1234, 0x5678},
             std::pair{0xFFFF, 0xFFFF}, std::pair{0x0100, 0x0100},
             std::pair{0x00FF, 0x00FF}, std::pair{0x8000, 0xFFFF}}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mLowerData[2] = left & 0xFF;
        cpu.mLowerData[3] = static_cast<unsigned char>(left >> 8);
        cpu.mLowerData[5] = right & 0xFF;
        cpu.mLowerData[7] = static_cast<unsigned char>(right >> 8);
        cpu.mPC = 0x5205;
        for (int step = 0; step < 40 && cpu.mPC != 0x5227; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x5227);
        const uint32_t actual = (uint32_t(cpu.mSFR[REG_ACC]) << 16) |
                                (uint32_t(cpu.mLowerData[2]) << 8) |
                                cpu.mLowerData[7];
        EXPECT_EQ(actual, (uint32_t(left) * uint32_t(right)) >> 8)
            << "left=" << left << " right=" << right;
    }
}

TEST(Sab80C517, FirmwareMemoryReadRequestUsesHighByteAsSpaceSelector) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    for (const auto selector : {0x00, 0xF8, 0x01}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 65535;
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_P2] = 0xF8;
        cpu.mSFR[REG_XPAGE] = 0xF8;
        for (std::size_t slot = 0; slot < 3; ++slot) {
            cpu.mLowerData[0x61 + slot] = static_cast<unsigned char>(0x11 + slot);
            xram[0xF861 + slot] = static_cast<unsigned char>(0x21 + slot);
        }
        xram[0xF8BB] = 3;
        xram[0xF8BC] = static_cast<unsigned char>(selector);
        xram[0xF8BD] = 0x61;
        cpu.mLowerData[2] = 0x01;
        cpu.mPC = 0x50CE;
        for (int step = 0; step < 20 && cpu.mPC != 0x510C; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x510C);
        EXPECT_EQ(cpu.mLowerData[0x42], 0x05);
        cpu.mPC = 0x4C06;
        for (int step = 0; step < 30 && cpu.mPC != 0x4E2E; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x4E2E);
        for (int step = 0; step < 150 && cpu.mPC != 0x4C53; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x4C53) << "selector=" << selector;
        EXPECT_EQ(xram[0xF8B8], 0x06);
        EXPECT_EQ(xram[0xF8B9], 0x01);
        EXPECT_EQ(xram[0xF8BA], 0xFE);
        for (std::size_t slot = 0; slot < 3; ++slot)
            EXPECT_EQ(xram[0xF8BB + slot], (selector == 0 ? 0x11 : 0x21) + slot);
        EXPECT_EQ(xram[0xF8BE], 0x03);
        EXPECT_EQ(cpu.mSFR[REG_P2], 0xF8);
        if (selector == 0) {
            // The scanner requests RAM[14h:15h] as two bytes for inj_time_ms.
            xram[0xF8BB] = 2;
            xram[0xF8BC] = 0;
            xram[0xF8BD] = 0x14;
            cpu.mLowerData[0x14] = 0x09;
            cpu.mLowerData[0x15] = 0xA7;
            cpu.mLowerData[0x40] = 0;
            cpu.mPC = 0x4E2E;
            for (int step = 0; step < 80 && cpu.mPC != 0x4C53; ++step)
                tick(&cpu);
            ASSERT_EQ(cpu.mPC, 0x4C53);
            EXPECT_EQ(xram[0xF8B8], 0x05);
            EXPECT_EQ(xram[0xF8BB], 0x09);
            EXPECT_EQ(xram[0xF8BC], 0xA7);
            EXPECT_EQ(xram[0xF8BD], 0x03);
            for (const auto length : {0, 13}) {
                xram[0xF8BB] = static_cast<unsigned char>(length);
                cpu.mLowerData[0x40] = 0;
                cpu.mPC = 0x4E2E;
                for (int step = 0; step < 80 && cpu.mPC != 0x4C53; ++step)
                    tick(&cpu);
                ASSERT_EQ(cpu.mPC, 0x4C53) << "length=" << length;
                EXPECT_EQ(xram[0xF8B8], 0x04);
                EXPECT_EQ(xram[0xF8B9], 0x01);
                EXPECT_EQ(xram[0xF8BA], 0x0A);
                EXPECT_EQ(xram[0xF8BB], 0x00);
                EXPECT_EQ(xram[0xF8BC], 0x03);
            }
        }
    }
}

TEST(Sab80C517, FirmwareCoolantGateCombinesThrottleAndRpmThresholds) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    ASSERT_EQ(original[0x4095], 0x7C); // MOV R4,#3Fh
    ASSERT_EQ(original[0x40CF], 0xEC); // MOV A,R4 before ORL #C0h

    struct Case {
        uint8_t coolant;
        uint8_t throttle;
        uint8_t rpm;
        uint8_t prior_gate;
        bool sets_flags;
    };
    constexpr std::array cases{
        Case{0x19, 0x2F, 0x50, 0, true},
        Case{0x1A, 0x2F, 0x50, 0, false},
        Case{0x19, 0x2E, 0x50, 0, false},
        Case{0x19, 0x2F, 0x4F, 0, false},
        Case{0x19, 0x2F, 0x50, 1, false},
    };
    for (const auto &test : cases) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 65535;
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_P2] = 0xF8;
        cpu.mSFR[REG_XPAGE] = 0xF8;
        cpu.mLowerData[0x63] = test.coolant;
        cpu.mLowerData[0x70] = test.throttle;
        cpu.mLowerData[0x47] = test.rpm;
        xram[0xF888] = test.prior_gate;
        cpu.mPC = 0x4095;
        for (int step = 0; step < 70 && cpu.mPC != 0x40D7; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x40D7) << "coolant=" << int(test.coolant);
        EXPECT_EQ(cpu.mLowerData[4], test.sets_flags ? 0xFF : 0x3F);
        EXPECT_EQ(cpu.mLowerData[2], test.sets_flags ? 0x7F : 0x7E);
        EXPECT_EQ(xram[0xF888], test.coolant >= 0x1A ? 0x96 : test.prior_gate);
    }
}

TEST(Sab80C517, FirmwareXramRangeCheckUsesRomBoundsAt7305And7306) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    ASSERT_EQ(original[0x7305], 0x65);
    ASSERT_EQ(original[0x7306], 0x9C);

    for (const auto [value, outside] : {
             std::pair{0x64, true}, std::pair{0x65, false},
             std::pair{0x7F, false}, std::pair{0x80, false},
             std::pair{0x9C, false}, std::pair{0x9D, true}}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 65535;
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_P2] = 0xF8;
        cpu.mSFR[REG_XPAGE] = 0xF8;
        cpu.mSFR[REG_DPH] = 0x73;
        cpu.mSFR[REG_DPL] = 0x00;
        cpu.mLowerData[0] = 0x40;
        cpu.mLowerData[1] = 5;
        cpu.mLowerData[2] = 6;
        xram[0xF840] = static_cast<unsigned char>(value);
        cpu.mPC = 0x5887;
        for (int step = 0; step < 30 && cpu.mPC != 0x5895; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x5895) << "value=" << value;
        EXPECT_EQ((cpu.mSFR[REG_PSW] & 0x80) != 0, outside)
            << "value=" << value << " A=" << int(cpu.mSFR[REG_ACC])
            << " R3=" << int(cpu.mLowerData[3])
            << " R0=" << int(cpu.mLowerData[0])
            << " PSW=" << int(cpu.mSFR[REG_PSW])
            << " P2=" << int(cpu.mSFR[REG_P2]);
    }

    for (const auto invalid_address : {0x40, 0x43}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 65535;
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_P2] = 0xF8;
        cpu.mSFR[REG_XPAGE] = 0xF8;
        for (std::size_t address = 0x40; address <= 0x45; ++address)
            xram[0xF800 + address] = 0x80;
        const auto slot = 0xF800u + static_cast<unsigned>(invalid_address);
        xram[slot] = 0x9D;
        cpu.mPC = 0x4A05;
        for (int step = 0; step < 300 && cpu.mPC != 0x4A9D; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x4A9D) << "address=" << invalid_address;
        EXPECT_EQ(xram[slot], 0x80);
    }
}

TEST(Sab80C517, FirmwareRam69ChangesTimer1ReloadCalculation) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    const std::array<uint8_t, 4> ram69_values{0x9A, 0x89, 0x7F, 0x7A};
    std::array<uint16_t, 4> reloads{};
    for (std::size_t index = 0; index < reloads.size(); ++index) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mLowerData[0x69] = ram69_values[index];
        cpu.mLowerData[0x31] = 0x59;
        cpu.mLowerData[0x36] = 0x01;
        cpu.mLowerData[0x37] = 0x1D;
        cpu.mPC = 0x043B;
        for (int step = 0; step < 500 && cpu.mPC != 0x0522; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x0522);
        reloads[index] = static_cast<uint16_t>(cpu.mLowerData[0x34] << 8 |
                                                cpu.mLowerData[0x35]);
    }
    EXPECT_NE(reloads[0], reloads[1]); // Values observed in G and S88 traces.
    EXPECT_EQ(reloads[2], 0x4CFE); // G-derived RAM69 in G timer code.
    EXPECT_EQ(reloads[3], 0x34FF); // A-derived RAM69 in G timer code.
}

TEST(Sab80C517, FiatBatterySegmentVariantsChangeIram31WithSameInputs) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin"};
    std::array<uint8_t, 2> results{};
    std::array<std::array<uint8_t, 8>, 2> segment_tables{};
    std::array<std::array<uint8_t, 60>, 2> selected_matrices{};
    for (size_t index = 0; index < paths.size(); ++index) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(paths[index], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[index];
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        std::copy_n(code.begin() + 0x7B3E, 8, segment_tables[index].begin());
        std::copy_n(code.begin() + 0x7ED9, 60, selected_matrices[index].begin());
        cpu.mLowerData[0x47] = 0x28; // Same RPM byte in both ROMs.
        cpu.mLowerData[0x7D] = 0x73; // Same low-battery ratio byte.
        cpu.mLowerData[0x57] = 0;    // Select pointer 70A2h -> 7ED9h.
        cpu.mPC = 0x3291;
        for (int step = 0; step < 5000 && cpu.mPC != 0x32BA; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x32BA) << paths[index];
        results[index] = cpu.mLowerData[0x31];
    }
    EXPECT_EQ(results[0], 0x59);
    EXPECT_EQ(results[1], 0x50);
    EXPECT_TRUE(std::equal(segment_tables[0].begin(),
                           segment_tables[0].end() - 1,
                           segment_tables[1].begin()));
    EXPECT_EQ(segment_tables[0][7], 0x05);
    EXPECT_EQ(segment_tables[1][7], 0x0D);
    EXPECT_EQ(selected_matrices[0], selected_matrices[1]);
}

TEST(Sab80C517, Fiat4044StoresSaturatedQ8RatioInIram7d) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    ASSERT_EQ(original[0x4044], 0xE5); // MOV A,61h.
    ASSERT_EQ(original[0x404B], 0xF5); // MOV 7Dh,A after LCALL 5367h.
    for (const unsigned dividend : {0u, 1u, 40u, 47u, 50u, 80u,
                                    156u, 160u, 172u, 181u, 255u}) {
        for (const unsigned divisor : {0u, 1u, 16u, 90u, 128u, 218u, 255u}) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mLowerData[0x61] = static_cast<unsigned char>(dividend);
            cpu.mLowerData[0x64] = static_cast<unsigned char>(divisor);
            cpu.mPC = 0x4044;
            for (int step = 0; step < 1000 && cpu.mPC != 0x404D; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x404D)
                << "61h=" << dividend << " 64h=" << divisor;
            const unsigned expected = divisor == 0 ? 255u :
                                      std::min(255u, (dividend << 8) / divisor);
            EXPECT_EQ(cpu.mLowerData[0x7D], expected)
                << "61h=" << dividend << " 64h=" << divisor;
        }
    }
}

TEST(Sab80C517, SixRomZeroDivisorSaturatesIram7d) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (std::size_t variant = 0; variant < paths.size(); ++variant) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(paths[variant], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[variant];
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        const bool relocated = variant != 0 && variant != 3;
        const uint16_t entry = relocated ? 0x4101 : 0x4044;
        const uint16_t divide = relocated ? 0x542A : 0x5367;
        ASSERT_EQ(original[entry], 0xE5); // MOV A,61h.
        ASSERT_EQ(original[entry + 4], 0x12); // LCALL division helper.
        ASSERT_EQ((original[entry + 5] << 8) | original[entry + 6], divide);
        ASSERT_EQ(original[entry + 7], 0xF5); // MOV 7Dh,A.
        for (const unsigned numerator : {0u, 1u, 47u, 255u}) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mLowerData[0x61] = static_cast<unsigned char>(numerator);
            cpu.mLowerData[0x64] = 0;
            cpu.mPC = entry;
            for (int step = 0; step < 1000 && cpu.mPC != entry + 9; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, entry + 9) << paths[variant];
            EXPECT_EQ(cpu.mLowerData[0x7D], 0xFF)
                << paths[variant] << " numerator=" << numerator;
        }
    }
}

TEST(Sab80C517, SixRom7968LookupReturns80ForEveryRawRatioByte) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (std::size_t variant = 0; variant < paths.size(); ++variant) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(paths[variant], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[variant];
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        ASSERT_EQ(original[0x706E], 0x79);
        ASSERT_EQ(original[0x706F], 0x68);
        const uint16_t entry = variant == 0 || variant == 3 ? 0x4066 : 0x4123;
        ASSERT_EQ(original[entry], 0x90); // MOV DPTR,#706Eh.
        ASSERT_EQ(original[entry + 9], 0xF7); // MOV @R1,A to upper 9Dh.
        for (unsigned raw = 0; raw <= 0xFF; ++raw) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mSFR[REG_SP] = 0x42;
            cpu.mLowerData[0x7D] = static_cast<unsigned char>(raw);
            cpu.mPC = entry;
            for (int step = 0; step < 500 && cpu.mPC != entry + 10; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, entry + 10)
                << paths[variant] << " 7Dh=" << raw;
            EXPECT_EQ(upper[0x9D - 0x80], 0x80)
                << paths[variant] << " 7Dh=" << raw;
        }
    }
}

TEST(Sab80C517, SixRom7960LookupMatchesAcrossAllRawRatioBytes) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    std::array<unsigned char, 256> gasoline_outputs{};
    for (std::size_t variant = 0; variant < paths.size(); ++variant) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(paths[variant], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[variant];
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        ASSERT_EQ(original[0x706C], 0x79);
        ASSERT_EQ(original[0x706D], 0x60);
        const uint16_t entry = variant == 0 || variant == 3 ? 0x404D : 0x410A;
        ASSERT_EQ(original[entry], 0x90); // MOV DPTR,#706Ch.
        ASSERT_EQ(original[entry + 23], 0xF5); // MOV 7Fh,A.
        ASSERT_EQ(original[entry + 24], 0x7F);
        for (unsigned raw = 0; raw <= 0xFF; ++raw) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mSFR[REG_SP] = 0x42;
            cpu.mLowerData[0x7D] = static_cast<unsigned char>(raw);
            cpu.mPC = entry;
            for (int step = 0; step < 500 && cpu.mPC != entry + 25; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, entry + 25)
                << paths[variant] << " 7Dh=" << raw;
            const auto output = cpu.mLowerData[0x7F];
            if (variant == 0) {
                gasoline_outputs[raw] = output;
            } else {
                EXPECT_EQ(output, gasoline_outputs[raw])
                    << paths[variant] << " 7Dh=" << raw;
            }
        }
    }
    for (const auto [raw, expected] :
         {std::pair{0u, 150u}, std::pair{64u, 150u},
          std::pair{128u, 131u}, std::pair{133u, 122u},
          std::pair{200u, 49u}, std::pair{254u, 34u},
          std::pair{255u, 34u}})
        EXPECT_EQ(gasoline_outputs[raw], expected) << "7Dh=" << raw;
    for (unsigned raw = 1; raw <= 0xFF; ++raw)
        EXPECT_LE(gasoline_outputs[raw], gasoline_outputs[raw - 1])
            << "7Dh=" << raw;
}

TEST(Sab80C517, SixRom79a8RpmCurveWritesF8a3ForAllRawValues) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    std::array<unsigned char, 256> gasoline_outputs{};
    for (std::size_t variant = 0; variant < paths.size(); ++variant) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(paths[variant], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[variant];
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        ASSERT_EQ(original[0x709A], 0x79);
        ASSERT_EQ(original[0x709B], 0xA8);
        ASSERT_EQ(original[0x79A8], 0x47);
        ASSERT_EQ(original[0x79A9], 0x03);
        const uint16_t entry = variant == 0 || variant == 3 ? 0x45EF : 0x46AC;
        ASSERT_EQ(original[entry], 0x90); // MOV DPTR,#709Ah.
        ASSERT_EQ(original[entry + 6], 0x78); // MOV R0,#A3h.
        for (unsigned raw = 0; raw <= 0xFF; ++raw) {
            std::array<unsigned char, 32768> code = original;
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mLowerData[0x47] = static_cast<unsigned char>(raw);
            cpu.mPC = entry;
            for (int step = 0; step < 500 && cpu.mPC != entry + 10; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, entry + 10) << paths[variant] << " raw=" << raw;
            const unsigned expected_segment = (raw >= 79) + (raw >= 129);
            EXPECT_EQ(cpu.mLowerData[3], expected_segment)
                << paths[variant] << " raw=" << raw;
            const auto output = xram[0xF8A3];
            if (variant == 0)
                gasoline_outputs[raw] = output;
            else
                EXPECT_EQ(output, gasoline_outputs[raw])
                    << paths[variant] << " raw=" << raw;
        }
    }
    EXPECT_EQ(gasoline_outputs[0], 0xFF);
    EXPECT_EQ(gasoline_outputs[255], 0x67);
    for (unsigned raw = 1; raw <= 0xFF; ++raw)
        EXPECT_LE(gasoline_outputs[raw], gasoline_outputs[raw - 1])
            << "raw=" << raw;
}

TEST(Sab80C517, SixRom7960LookupAddsSignedF872WithSaturation) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (std::size_t variant = 0; variant < paths.size(); ++variant) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(paths[variant], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[variant];
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        const uint16_t entry = variant == 0 || variant == 3 ? 0x404D : 0x410A;
        for (const auto [raw, base] :
             {std::pair{0u, 150}, std::pair{128u, 131},
              std::pair{200u, 49}, std::pair{255u, 34}}) {
            for (const unsigned raw_offset : {0x00u, 0x40u, 0x7Fu,
                                              0x80u, 0xC0u, 0xFFu}) {
                std::array<unsigned char, 32768> code{};
                std::array<unsigned char, 65536> xram{};
                std::array<unsigned char, 128> upper{};
                em8051 cpu{};
                cpu.mCodeMem = code.data();
                cpu.mCodeMemMaxIdx = code.size() - 1;
                cpu.mExtData = xram.data();
                cpu.mExtDataMaxIdx = xram.size() - 1;
                cpu.mUpperData = upper.data();
                reset(&cpu, true);
                std::copy(original.begin(), original.end(), code.begin());
                cpu.mSFR[REG_SP] = 0x42;
                cpu.mSFR[REG_P2] = 0xF8;
                cpu.mSFR[REG_XPAGE] = 0xF8;
                cpu.mLowerData[0x7D] = static_cast<unsigned char>(raw);
                xram[0xF872] = static_cast<unsigned char>(raw_offset);
                cpu.mPC = entry;
                for (int step = 0; step < 500 && cpu.mPC != entry + 25; ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, entry + 25)
                    << paths[variant] << " 7Dh=" << raw;
                const int offset = static_cast<int>(raw_offset) -
                                   (raw_offset >= 0x80 ? 256 : 0);
                EXPECT_EQ(cpu.mLowerData[0x7F],
                          std::clamp(base + offset, 0, 255))
                    << paths[variant] << " 7Dh=" << raw
                    << " F872h=" << raw_offset;
            }
        }
    }
}

TEST(Sab80C517, AlcoholCodeMatrixSecondAxisUsesHeaderSelectedIramByte) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const auto alcohol = root / "firmwares_modificados_ma17_tipo" /
                         "tipo 1.6 alcool27c256.bin";
    const auto sun37 = root / "firmwares_modificados_ma17_tipo" /
                       "tipo 1.6 alcool27c256 SUN 37a5.bin";
    const auto run = [&](const std::filesystem::path &path, uint8_t af,
                         uint8_t ram7d, uint8_t selector = 0,
                         uint8_t rpm47 = 0x28) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(path, std::ios::binary);
        EXPECT_TRUE(file.is_open()) << path;
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        EXPECT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        cpu.mLowerData[0x47] = rpm47;
        cpu.mLowerData[0x57] = selector; // 70A2h/70A4h/70A6h.
        cpu.mLowerData[0x7D] = ram7d;
        upper[0xAF - 0x80] = af;
        cpu.mPC = 0x32AD;
        for (int step = 0; step < 500 && cpu.mPC != 0x32D6; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        EXPECT_EQ(cpu.mPC, 0x32D6) << path;
        return cpu.mLowerData[0x31];
    };
    const auto a_low = run(alcohol, 0x20, 0x20);
    const auto a_af_high = run(alcohol, 0xC0, 0x20);
    const auto a_7d_high = run(alcohol, 0x20, 0xC0);
    EXPECT_NE(a_low, a_af_high);
    EXPECT_EQ(a_low, a_7d_high);
    const auto s_low = run(sun37, 0x20, 0x20);
    const auto s_af_high = run(sun37, 0xC0, 0x20);
    const auto s_7d_high = run(sun37, 0x20, 0xC0);
    EXPECT_EQ(a_low, 0x9A);
    EXPECT_EQ(a_af_high, 0x42);
    EXPECT_EQ(a_7d_high, 0x9A);
    EXPECT_NE(run(alcohol, 0x00, 0x20), run(alcohol, 0xFF, 0x20));
    EXPECT_EQ(s_low, 0x78);
    EXPECT_EQ(s_af_high, 0x78);
    EXPECT_EQ(s_7d_high, 0x1B);
    EXPECT_EQ(s_low, s_af_high);
    EXPECT_NE(s_low, s_7d_high);
    const auto a_mode1 = run(alcohol, 0x20, 0x20, 1);
    const auto a_mode2 = run(alcohol, 0x20, 0x20, 2);
    const auto s_mode1 = run(sun37, 0x20, 0x20, 1);
    const auto s_mode2 = run(sun37, 0x20, 0x20, 2);
    EXPECT_EQ(a_mode1, a_low);
    EXPECT_NE(a_mode2, a_low);
    EXPECT_EQ(s_mode1, s_low);
    EXPECT_NE(s_mode2, s_low);
    EXPECT_EQ(a_mode2, 0xEC);
    EXPECT_EQ(s_mode2, 0xD8);
    EXPECT_EQ(run(alcohol, 0xC0, 0x20, 1), a_af_high);
    EXPECT_EQ(run(sun37, 0x20, 0xC0, 1), s_7d_high);
    bool alcohol_mode1_differs = false;
    int first_rpm = -1, first_af = -1, first_base = -1, first_mode1 = -1;
    for (const uint8_t rpm : std::array<uint8_t, 6>{0x10, 0x20, 0x28,
                                                      0x40, 0x60, 0x80}) {
        for (const uint8_t af : std::array<uint8_t, 8>{0x00, 0x20, 0x40,
                                                       0x60, 0x80, 0xA0,
                                                       0xC0, 0xFF}) {
            const auto base = run(alcohol, af, 0x20, 0, rpm);
            const auto mode1 = run(alcohol, af, 0x20, 1, rpm);
            if (base != mode1 && first_rpm < 0) {
                first_rpm = rpm;
                first_af = af;
                first_base = base;
                first_mode1 = mode1;
            }
            alcohol_mode1_differs |= base != mode1;
        }
    }
    EXPECT_TRUE(alcohol_mode1_differs);
    EXPECT_EQ(first_rpm, 0x10);
    EXPECT_EQ(first_af, 0xFF);
    EXPECT_EQ(first_base, 0x2C);
    EXPECT_EQ(first_mode1, 0x0A);
}

TEST(Sab80C517, TerminalSegmentHeaderSelectsDifferentIramSource) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const auto alcohol = root / "firmwares_modificados_ma17_tipo" /
                         "tipo 1.6 alcool27c256.bin";
    const auto run = [&](const std::filesystem::path &path, uint16_t entry,
                         uint16_t after_call, uint8_t ram0f, uint8_t ram35) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(path, std::ios::binary);
        EXPECT_TRUE(file.is_open()) << path;
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        EXPECT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        cpu.mLowerData[0x0F] = ram0f;
        cpu.mLowerData[0x35] = ram35;
        cpu.mPC = entry;
        for (int step = 0; step < 500 && cpu.mPC != after_call; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        EXPECT_EQ(cpu.mPC, after_call) << path;
        return cpu.mLowerData[0x03]; // R3 holds the segment lookup result.
    };
    const auto g_low = run(MA17_ROM_PATH, 0x3AAD, 0x3AB3, 0x00, 0x00);
    const auto g_0f_high = run(MA17_ROM_PATH, 0x3AAD, 0x3AB3, 0x80, 0x00);
    const auto g_35_high = run(MA17_ROM_PATH, 0x3AAD, 0x3AB3, 0x00, 0x80);
    const auto a_low = run(alcohol, 0x3ADB, 0x3AE1, 0x00, 0x00);
    const auto a_0f_high = run(alcohol, 0x3ADB, 0x3AE1, 0x80, 0x00);
    const auto a_35_high = run(alcohol, 0x3ADB, 0x3AE1, 0x00, 0x80);
    EXPECT_NE(g_low, g_0f_high);
    EXPECT_EQ(g_low, g_35_high);
    EXPECT_EQ(a_low, a_0f_high);
    EXPECT_NE(a_low, a_35_high);
    int different_segment_indices = 0;
    for (int value = 0; value < 256; ++value) {
        const auto sample = static_cast<uint8_t>(value);
        const auto g = run(MA17_ROM_PATH, 0x3AAD, 0x3AB3, sample, sample);
        const auto a = run(alcohol, 0x3ADB, 0x3AE1, sample, sample);
        EXPECT_LE(g, 6) << "G input=" << value;
        EXPECT_LE(a, 6) << "A input=" << value;
        EXPECT_EQ(g != a, value < 0x20) << "equal IRAM sources=" << value;
        different_segment_indices += g != a;
    }
    EXPECT_EQ(different_segment_indices, 0x20);
}

TEST(Sab80C517, TerminalCurveLookupStaysWithinSevenBytes) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const auto alcohol = root / "firmwares_modificados_ma17_tipo" /
                         "tipo 1.6 alcool27c256.bin";
    const auto run = [&](const std::filesystem::path &path, uint16_t entry,
                         uint16_t lookup, uint8_t source) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        for (int value = 0; value < 256; ++value) {
            for (const uint8_t previous83 : std::array<uint8_t, 5>{0, 1, 6, 7, 255}) {
                for (const uint8_t previous82 : std::array<uint8_t, 2>{0, 1}) {
                    em8051 cpu{};
                    cpu.mCodeMem = code.data();
                    cpu.mCodeMemMaxIdx = code.size() - 1;
                    cpu.mExtData = xram.data();
                    cpu.mExtDataMaxIdx = xram.size() - 1;
                    cpu.mUpperData = upper.data();
                    upper.fill(0);
                    reset(&cpu, false); // The ROM was loaded once above.
                    cpu.mLowerData[source] = static_cast<uint8_t>(value);
                    upper[0x82 - 0x80] = previous82;
                    upper[0x83 - 0x80] = previous83;
                    cpu.mPC = entry;
                    for (int step = 0; step < 200 && cpu.mPC != lookup; ++step) {
                        cpu.mTickDelay = 0;
                        tick(&cpu);
                    }
                    ASSERT_EQ(cpu.mPC, lookup) << path << " input=" << value;
                    const auto index = cpu.mSFR[REG_ACC];
                    EXPECT_LE(index, 6) << path << " input=" << value
                                         << " previous83=" << int(previous83)
                                         << " previous82=" << int(previous82);
                    EXPECT_EQ(cpu.mSFR[REG_DPH], 0x7F);
                    EXPECT_EQ(cpu.mSFR[REG_DPL], 0x96);
                    EXPECT_EQ(upper[0x83 - 0x80], index);
                }
            }
        }
    };
    run(MA17_ROM_PATH, 0x3AAD, 0x3AD2, 0x0F);
    run(alcohol, 0x3ADB, 0x3B00, 0x35);
}

TEST(Sab80C517, FiveIram78GateTablesSelectOriginalRomBytes) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    ASSERT_EQ(original[0x721E], 0x7A);
    ASSERT_EQ(original[0x720D], 0x26);
    struct Case {
        uint8_t flags2f, t2con, ram62, ram63, upper9e;
        uint16_t slot, target;
    };
    const std::array cases{
        Case{0x00, 0, 0, 0, 0, 0x70E8, 0x7AB0},
        Case{0x30, 0, 0x7B, 0, 0, 0x70E6, 0x7A80},
        Case{0x30, 0, 0x7A, 0x26, 0x14, 0x70E4, 0x7A50},
        Case{0x20, 0x02, 0, 0, 0, 0x70E2, 0x7A20},
        Case{0x20, 0, 0, 0x26, 0, 0x70E0, 0x79F0},
        Case{0x20, 0, 0, 0x27, 0x14, 0x70E0, 0x79F0},
        Case{0x20, 0, 0, 0x26, 0x14, 0x70E4, 0x7A50},
    };
    for (const auto &test : cases) {
        ASSERT_EQ((original[test.slot] << 8) | original[test.slot + 1],
                  test.target);
        for (const uint8_t index : std::array<uint8_t, 2>{0, 47}) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mPC = 0x19FA;
            cpu.mSFR[REG_ACC] = index;
            cpu.mSFR[REG_T2CON] = test.t2con;
            cpu.mLowerData[0x2F] = test.flags2f;
            cpu.mLowerData[0x62] = test.ram62;
            cpu.mLowerData[0x63] = test.ram63;
            upper[0x9E - 0x80] = test.upper9e;
            for (int step = 0; step < 40 && cpu.mPC != 0x1A3A; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x1A3A) << std::hex << test.slot;
            EXPECT_EQ((cpu.mSFR[REG_DPH] << 8) | cpu.mSFR[REG_DPL],
                      test.target);
            EXPECT_EQ(cpu.mLowerData[1], original[test.target + index]);
        }
    }
}

TEST(Sab80C517, SignedAccumulatorCanClearNonzeroTableGateR1) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const auto variants = std::array{
        std::pair{std::filesystem::path(MA17_ROM_PATH), 0x5419},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                      "tipo 1.6 alcool27c256.bin", 0x54DC},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                      "tipo 1.6 alcool27c256+1.5bar.bin", 0x54DC},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                      "tipo 1.6 alcool27c256 SUN 8817.bin", 0x5419},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                      "tipo 1.6 alcool27c256 SUN 37a5.bin", 0x54DC},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                      "tipo 1.6 alcool27c256 SUN 36fd.bin", 0x54DC},
    };
    for (const auto &[path, entry] : variants) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        for (const uint8_t sample : std::array<uint8_t, 2>{2, 3}) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mPC = static_cast<uint16_t>(entry);
            cpu.mSFR[REG_ACC] = sample;
            cpu.mLowerData[1] = 3;    // R1 from the selected table.
            cpu.mLowerData[3] = 0x7F; // Keep the R3 threshold inactive.
            cpu.mLowerData[7] = 0x7F;
            const auto before_return = static_cast<uint16_t>(entry + 0x32);
            for (int step = 0; step < 35 && cpu.mPC != before_return; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, before_return) << path;
            EXPECT_EQ(cpu.mLowerData[1], sample == 3 ? 0 : 3);
            EXPECT_EQ((cpu.mSFR[REG_PSW] & 0x20) != 0, sample == 3);
        }
    }
}

TEST(Sab80C517, Ram78ConsumerRequiresNonzeroR6AndSelectsOriginalTable) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    struct Case { uint8_t r6, flags2f, t2con; uint16_t table; };
    const std::array cases{
        Case{0, 0, 0, 0},
        Case{1, 0, 0, 0x713F},
        Case{1, 0x20, 0, 0x712D},
        Case{1, 0x20, 0x02, 0x7136},
    };
    for (const auto &test : cases) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mPC = 0x1C19;
        cpu.mLowerData[6] = test.r6;
        cpu.mLowerData[0x2F] = test.flags2f;
        cpu.mSFR[REG_T2CON] = test.t2con;
        bool visited_lookup = false;
        for (int step = 0; step < 100 && cpu.mPC != 0x1C38; ++step) {
            if (cpu.mPC == 0x532F) {
                visited_lookup = true;
                EXPECT_EQ((cpu.mSFR[REG_DPH] << 8) | cpu.mSFR[REG_DPL],
                          test.table);
            }
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x1C38);
        EXPECT_EQ(visited_lookup, test.r6 != 0);
        if (test.r6 == 0) {
            EXPECT_EQ(cpu.mLowerData[0x78], 0);
        } else {
            EXPECT_GT(cpu.mLowerData[0x78], 0);
            EXPECT_EQ(cpu.mLowerData[0x78], cpu.mLowerData[2]);
        }
    }
}

TEST(Sab80C517, Iram47SegmentDecoderBoundsR4IndexInSixRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const auto variants = std::array{
        std::pair{std::filesystem::path(MA17_ROM_PATH), 0x52CD},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                      "tipo 1.6 alcool27c256.bin", 0x5390},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                      "tipo 1.6 alcool27c256+1.5bar.bin", 0x5390},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                      "tipo 1.6 alcool27c256 SUN 8817.bin", 0x52CD},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                      "tipo 1.6 alcool27c256 SUN 37a5.bin", 0x5390},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                      "tipo 1.6 alcool27c256 SUN 36fd.bin", 0x5390},
    };
    for (const auto &[path, entry] : variants) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        ASSERT_EQ(original[0x70DE], 0x79);
        ASSERT_EQ(original[0x70DF], 0xE8);
        ASSERT_EQ(original[0x79E8], 0x47); // IRAM source selector.
        ASSERT_EQ(original[0x79E9], 0x06); // Segment count and multiplier.
        ASSERT_EQ(original[0x79EA], 0x20);
        ASSERT_EQ(original[0x79EF], 0x70);
        const std::array thresholds{32, 48, 80, 110, 144};
        for (int value = 0; value < 256; ++value) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mSFR[REG_DPH] = 0x70;
            cpu.mSFR[REG_DPL] = 0xDE;
            cpu.mLowerData[0x47] = static_cast<uint8_t>(value);
            cpu.mPC = static_cast<uint16_t>(entry);
            const auto before_return = static_cast<uint16_t>(entry + 0x1F);
            for (int step = 0; step < 100 && cpu.mPC != before_return; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, before_return) << path << " input=" << value;
            ASSERT_EQ(cpu.mSFR[REG_B], 6);
            const auto expected = std::count_if(
                thresholds.begin(), thresholds.end(),
                [value](int threshold) { return value >= threshold; });
            EXPECT_EQ(cpu.mLowerData[3], expected) << path << " input=" << value;
            // At G 19E7h, R4=(IRAM6Ah & 0Fh)*B+R3: at most 15*6+5.
            EXPECT_LE(15 * cpu.mSFR[REG_B] + cpu.mLowerData[3], 95);
        }
    }
}

TEST(Sab80C517, ConstantCurve741cInterpolatesAdjacentBytesAtBoundary) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const auto variants = std::array{
        std::tuple{std::filesystem::path(MA17_ROM_PATH), 0x15D5, 0x15DB, 0x532F},
        std::tuple{root / "firmwares_modificados_ma17_tipo" /
                       "tipo 1.6 alcool27c256.bin", 0x161C, 0x1622, 0x53F2},
        std::tuple{root / "firmwares_modificados_ma17_tipo" /
                       "tipo 1.6 alcool27c256+1.5bar.bin", 0x161C, 0x1622, 0x53F2},
        std::tuple{root / "firmwares_modificados_ma17_tipo" /
                       "tipo 1.6 alcool27c256 SUN 8817.bin", 0x15D5, 0x15DB, 0x532F},
        std::tuple{root / "firmwares_modificados_ma17_tipo" /
                       "tipo 1.6 alcool27c256 SUN 37a5.bin", 0x161C, 0x1622, 0x53F2},
        std::tuple{root / "firmwares_modificados_ma17_tipo" /
                       "tipo 1.6 alcool27c256 SUN 36fd.bin", 0x161C, 0x1622, 0x53F2},
    };
    for (const auto &[path, entry, after, first_movc] : variants) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        ASSERT_EQ(original[0x7006], 0x74);
        ASSERT_EQ(original[0x7007], 0x1C);
        const auto branch = static_cast<std::size_t>(entry) - 6;
        ASSERT_EQ(original[branch], 0x20); // JB 2Fh.0 skips this lookup.
        ASSERT_EQ(original[branch + 1], 0x78);
        for (const uint8_t index : std::array<uint8_t, 3>{0, 8, 9}) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mLowerData[5] = index; // R5, first adjacent-cell index.
            cpu.mLowerData[6] = 0x80;  // R6, interpolation fraction.
            cpu.mPC = static_cast<uint16_t>(entry);
            std::array<uint16_t, 2> reads{};
            std::size_t read_count = 0;
            for (int step = 0; step < 50 && cpu.mPC != after; ++step) {
                if (cpu.mPC == first_movc || cpu.mPC == first_movc + 4) {
                    ASSERT_LT(read_count, reads.size());
                    reads[read_count++] = static_cast<uint16_t>(
                        (cpu.mSFR[REG_DPH] << 8) | cpu.mSFR[REG_DPL]) +
                        cpu.mSFR[REG_ACC];
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, after) << path;
            ASSERT_EQ(read_count, 2);
            EXPECT_EQ(reads[0], 0x741C + index);
            EXPECT_EQ(reads[1], 0x741D + index);
            if (index <= 8)
                EXPECT_EQ(cpu.mLowerData[2], 0x40); // R2 from equal cells.
        }
    }
}

TEST(Sab80C517, TerminalSegmentFlowsIntoIram69InIsolatedCode) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const auto alcohol = root / "firmwares_modificados_ma17_tipo" /
                         "tipo 1.6 alcool27c256.bin";
    const auto run = [&](const std::filesystem::path &path, uint16_t entry,
                         uint16_t after_write, uint8_t ram0f, uint8_t ram35,
                         uint8_t initial83) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(path, std::ios::binary);
        EXPECT_TRUE(file.is_open()) << path;
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        EXPECT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        cpu.mLowerData[0x0F] = ram0f;
        cpu.mLowerData[0x35] = ram35;
        upper[0x82 - 0x80] = 1;
        upper[0x83 - 0x80] = initial83;
        upper[0x8C - 0x80] = 0x80;
        cpu.mPC = entry;
        for (int step = 0; step < 800 && cpu.mPC != after_write; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        EXPECT_EQ(cpu.mPC, after_write) << path;
        return std::array<uint8_t, 3>{upper[0x83 - 0x80],
                                      upper[0x8C - 0x80],
                                      cpu.mLowerData[0x69]};
    };
    const auto g_blocked_low = run(MA17_ROM_PATH, 0x3AAD, 0x3B08,
                                   0x00, 0x00, 0);
    const auto g_blocked_high = run(MA17_ROM_PATH, 0x3AAD, 0x3B08,
                                    0x80, 0x00, 0);
    const auto a_blocked_low = run(alcohol, 0x3ADB, 0x3B36, 0x00, 0x00, 0);
    const auto a_blocked_high = run(alcohol, 0x3ADB, 0x3B36, 0x00, 0x80, 0);
    EXPECT_EQ(g_blocked_low, g_blocked_high);
    EXPECT_EQ(a_blocked_low, a_blocked_high);
    EXPECT_EQ(g_blocked_low, a_blocked_low);
    const auto g_low = run(MA17_ROM_PATH, 0x3AAD, 0x3B08, 0x00, 0x00, 7);
    const auto g_0f_high = run(MA17_ROM_PATH, 0x3AAD, 0x3B08, 0x80, 0x00, 7);
    const auto g_35_high = run(MA17_ROM_PATH, 0x3AAD, 0x3B08, 0x00, 0x80, 7);
    const auto a_low = run(alcohol, 0x3ADB, 0x3B36, 0x00, 0x00, 7);
    const auto a_0f_high = run(alcohol, 0x3ADB, 0x3B36, 0x80, 0x00, 7);
    const auto a_35_high = run(alcohol, 0x3ADB, 0x3B36, 0x00, 0x80, 7);
    EXPECT_NE(g_low, g_0f_high);
    EXPECT_EQ(g_low, g_35_high);
    EXPECT_EQ(a_low, a_0f_high);
    EXPECT_NE(a_low, a_35_high);
    EXPECT_NE(g_low[2], g_0f_high[2]);
    EXPECT_NE(a_low[2], a_35_high[2]);
    EXPECT_EQ(g_low[1], g_low[2]);
    EXPECT_EQ(a_low[1], a_low[2]);
    // Equal inputs neutralize the changed IRAM source; only the final
    // segment increment differs between these aligned code paths.
    EXPECT_EQ(g_low[2], 0x7F);
    EXPECT_EQ(a_low[2], 0x7A);
    const auto g_boundary = run(MA17_ROM_PATH, 0x3AAD, 0x3B08,
                                0x20, 0x20, 7);
    const auto a_boundary = run(alcohol, 0x3ADB, 0x3B36,
                                0x20, 0x20, 7);
    EXPECT_EQ(g_boundary[2], 0x77);
    EXPECT_EQ(g_boundary, a_boundary);
}

TEST(Sab80C517, AlcoholCodeRpmWindowWritesUpperAfAtRomThreshold) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    for (const auto &path : paths) {
        for (const auto [rpm47, expected] : {
                 std::pair{0x28, 0xFF}, std::pair{0x29, 0x00},
                 std::pair{0x31, 0x00}, std::pair{0x32, 0xFF}}) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x734E], 0x0A);
            cpu.mLowerData[0x46] = 0x28;
            cpu.mLowerData[0x47] = static_cast<uint8_t>(rpm47);
            upper[0xAF - 0x80] = 0x55;
            cpu.mPC = 0x3302;
            for (int step = 0; step < 50 && cpu.mPC != 0x3329; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x3329) << path;
            EXPECT_EQ(upper[0xAF - 0x80], expected) << path << " 47h=" << rpm47;
        }
    }
}

TEST(Sab80C517, AlcoholCodeUpperAfRpmComparisonUsesTwoRomBounds) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    struct Case {
        uint8_t previous47, current47, psw_f1, expected_af;
    };
    constexpr std::array cases{
        Case{0x28, 0x34, 0x00, 0x55}, // Difference 12: no 734Dh crossing.
        Case{0x28, 0x35, 0x00, 0x00}, // Difference 13: clear AFh.
        Case{0x28, 0x28, 0x02, 0xFF}, // PSW.F1 selects 734Eh branch.
        Case{0x28, 0x29, 0x02, 0x55}, // Positive difference preserves AFh.
    };
    for (const auto &path : paths) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        ASSERT_EQ(original[0x734D], 0x0C);
        ASSERT_EQ(original[0x734E], 0x0A);
        for (const auto &sample : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mLowerData[0x46] = sample.previous47;
            cpu.mLowerData[0x47] = sample.current47;
            upper[0x94 - 0x80] = 0;
            upper[0xAF - 0x80] = 0x55;
            cpu.mSFR[REG_PSW] = sample.psw_f1;
            cpu.mSFR[REG_DPL] = 0x00;
            cpu.mSFR[REG_DPH] = 0x73;
            cpu.mPC = 0x3473;
            for (int step = 0; step < 80 && cpu.mPC != 0x34B3; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x34B3) << path;
            EXPECT_EQ(upper[0xAF - 0x80], sample.expected_af)
                << path << " 46h=" << static_cast<int>(sample.previous47)
                << " 47h=" << static_cast<int>(sample.current47)
                << " PSW.F1=" << static_cast<int>(sample.psw_f1 != 0);
        }
    }
}

TEST(Sab80C517, AlcoholCodeStartupSeedsUpperAfAndIram7d) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (const auto &path : paths) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        ASSERT_EQ(code[0x0C52], 0x79); // MOV R1,#AFh.
        ASSERT_EQ(code[0x0C54], 0x77); // MOV @R1,#FFh.
        cpu.mPC = 0x0C48;
        for (int step = 0; step < 30 && cpu.mPC != 0x0C59; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x0C59) << path;
        EXPECT_EQ(upper[0xAF - 0x80], 0xFF) << path;
        EXPECT_EQ(cpu.mLowerData[0x7D], 0xC0) << path;
    }
}

TEST(Sab80C517, AlcoholCodeUpperAfZeroSurvivesOnlyOpenGate) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (std::size_t variant = 0; variant < paths.size(); ++variant) {
        const auto &path = paths[variant];
        std::array<unsigned char, 32768> original{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        ASSERT_EQ(original[0x3479], 0x20); // JB PSW.F1.
        ASSERT_EQ(original[0x34B3], 0xA6); // MOV @R0,B.
        std::array<unsigned char, 2> matrix_results{};
        for (const bool gate_open : {true, false}) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mLowerData[0x46] = 0x28;
            cpu.mLowerData[0x47] = 0x35;
            cpu.mLowerData[0x22] = gate_open ? 0x02 : 0x00;
            cpu.mLowerData[0x2F] = 0x01;
            upper[0x94 - 0x80] = 0x01; // B.0 routes to 34CFh.
            upper[0xB3 - 0x80] = 0x00; // ACC.4 clear at the gate.
            upper[0xAF - 0x80] = 0x55;
            cpu.mSFR[REG_DPH] = 0x73;
            cpu.mSFR[REG_DPL] = 0;
            cpu.mPC = 0x3473;
            const uint16_t exit = gate_open ? 0x3562 : 0x35CF;
            for (int step = 0; step < 100 && cpu.mPC != exit; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, exit) << path << " gate=" << gate_open;
            EXPECT_EQ(upper[0xAF - 0x80], gate_open ? 0x00 : 0xFF)
                << path << " gate=" << gate_open;
            // Stage the original matrix consumer with AFh as the only
            // retained state from the producer path.
            const unsigned char af = upper[0xAF - 0x80];
            upper.fill(0);
            upper[0xAF - 0x80] = af;
            std::fill_n(cpu.mLowerData, 128, 0);
            cpu.mLowerData[0x47] = 0x35;
            cpu.mLowerData[0x7D] = 0x20;
            cpu.mSFR[REG_PSW] = 0;
            cpu.mSFR[REG_B] = 0;
            cpu.mSFR[REG_ACC] = 0;
            cpu.mPC = 0x32AD;
            for (int step = 0; step < 500 && cpu.mPC != 0x32D6; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x32D6) << path << " gate=" << gate_open;
            matrix_results[gate_open ? 0 : 1] = cpu.mLowerData[0x31];
        }
        if (variant < 2) {
            EXPECT_EQ(matrix_results[0], 0xBA) << path;
            EXPECT_EQ(matrix_results[1], 0x37) << path;
        } else {
            EXPECT_EQ(matrix_results[0], 0x98) << path;
            EXPECT_EQ(matrix_results[1], 0x98) << path;
        }
    }
}

TEST(Sab80C517, AlcoholCodeUpperAfAccumulatesB0OnlyWhenFlagsAllow) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    struct Case {
        uint8_t af, b0, flag26, flag2d, expected;
    };
    constexpr std::array cases{
        Case{0x20, 0x10, 0x00, 0x20, 0x30},
        Case{0x20, 0xFF, 0x00, 0x20, 0xFF},
        Case{0x00, 0xFF, 0x00, 0x20, 0xFF},
        Case{0xEF, 0x10, 0x00, 0x20, 0xFF},
        Case{0xF8, 0x10, 0x00, 0x20, 0xFF},
        Case{0x20, 0x10, 0x20, 0x20, 0x20},
        Case{0x20, 0x10, 0x00, 0x00, 0x20},
        Case{0xFF, 0x10, 0x00, 0x20, 0xFF}};
    for (const auto &path : paths) {
        for (const auto &test : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            upper[0xAF - 0x80] = test.af;
            upper[0xB0 - 0x80] = test.b0;
            cpu.mLowerData[0x26] = test.flag26;
            cpu.mLowerData[0x2D] = test.flag2d;
            cpu.mPC = 0x34D5;
            for (int step = 0; step < 30 && cpu.mPC != 0x34F3; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x34F3) << path;
            EXPECT_EQ(upper[0xAF - 0x80], test.expected)
                << path << " initial AFh=" << static_cast<unsigned>(test.af);
        }
    }
}

TEST(Sab80C517, AlcoholCodeB0LookupUsesAllFfTableAt7552) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    constexpr std::array<uint8_t, 4> samples{0x00, 0x04, 0x48, 0x88};
    for (const auto &path : paths) {
        for (const uint8_t ram4e : samples) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x7040], 0x75);
            ASSERT_EQ(code[0x7041], 0x52);
            ASSERT_TRUE(std::all_of(code.begin() + 0x7552,
                                    code.begin() + 0x755C,
                                    [](uint8_t value) { return value == 0xFF; }));
            cpu.mLowerData[0x4E] = ram4e;
            upper[0xB0 - 0x80] = 0;
            cpu.mPC = 0x3D43;
            for (int step = 0; step < 100 && cpu.mPC != 0x3D56; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x3D56) << path;
            EXPECT_EQ(upper[0xB0 - 0x80], 0xFF) << path;
        }
    }
}

TEST(Sab80C517, FiatIram31ChangesTimer1ReloadWithSameOtherState) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    std::array<uint16_t, 2> reloads{};
    std::array<uint8_t, 2> flags{};
    for (size_t index = 0; index < reloads.size(); ++index) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mLowerData[0x31] = index == 0 ? 0x59 : 0x50;
        cpu.mLowerData[0x69] = 0xA8;
        cpu.mLowerData[0x36] = 0x01;
        cpu.mLowerData[0x37] = 0x1D;
        cpu.mPC = 0x043B;
        for (int step = 0; step < 500 && cpu.mPC != 0x0522; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x0522);
        flags[index] = cpu.mLowerData[0x22] & 0x80;
        reloads[index] = uint16_t(cpu.mLowerData[0x34] << 8 |
                                  cpu.mLowerData[0x35]);
    }
    EXPECT_EQ(flags[0], 0x00);
    EXPECT_EQ(flags[1], 0x80);
    EXPECT_EQ(reloads[0], 0x69FE);
    EXPECT_EQ(reloads[1], 0x2FFE);
}

TEST(Sab80C517, AlcoholNativeMatrixRam31CanChangeIsolatedTimer1Reload) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const auto variants = root / "firmwares_modificados_ma17_tipo";
    const std::array paths{
        variants / "tipo 1.6 alcool27c256.bin",
        variants / "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    std::array<unsigned char, 0x0522 - 0x043B> consumer_code{};
    std::array<uint8_t, 2> ram31{};
    std::array<std::array<uint16_t, 256>, 4> reloads{};
    std::array<uint8_t, 2> ff_flags{};
    for (size_t index = 0; index < reloads.size(); ++index) {
        const size_t variant = index % paths.size();
        SCOPED_TRACE(paths[variant].string());
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(paths[variant], std::ios::binary);
        ASSERT_TRUE(file.is_open());
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        if (index == 0) {
            std::copy_n(code.begin() + 0x043B, consumer_code.size(),
                        consumer_code.begin());
        } else if (index == 1) {
            EXPECT_TRUE(std::equal(consumer_code.begin(), consumer_code.end(),
                                   code.begin() + 0x043B));
        }
        for (int value = 0; value < 256; ++value) {
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mLowerData[0x47] = 0x28;
            cpu.mLowerData[0x57] = 0;
            cpu.mLowerData[0x7D] = 0x20;
            upper[0xAF - 0x80] = 0x20;
            cpu.mPC = 0x32AD;
            for (int step = 0; step < 500 && cpu.mPC != 0x32D6; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x32D6);
            EXPECT_EQ(cpu.mLowerData[0x31], variant == 0 ? 0x9A : 0x78);
            if (index < 2) ram31[index] = cpu.mLowerData[0x31];
            if (index >= 2) cpu.mLowerData[0x31] = variant == 0 ? 0x78 : 0x9A;
            cpu.mLowerData[0x69] = static_cast<uint8_t>(value);
            cpu.mLowerData[0x36] = 0x01;
            cpu.mLowerData[0x37] = 0x1D;
            cpu.mPC = 0x043B;
            for (int step = 0; step < 500 && cpu.mPC != 0x0522; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x0522);
            reloads[index][static_cast<size_t>(value)] =
                uint16_t(cpu.mLowerData[0x34] << 8 | cpu.mLowerData[0x35]);
            if (index < 2 && value == 0xFF) {
                ff_flags[index] = cpu.mLowerData[0x22] & 0x80;
            }
        }
    }
    EXPECT_EQ(ram31[0], 0x9A);
    EXPECT_EQ(ram31[1], 0x78);
    EXPECT_EQ(ff_flags[0], 0x00);
    EXPECT_EQ(ff_flags[1], 0x80);
    size_t first_difference = 256;
    for (size_t value = 0; value < 256; ++value) {
        if (reloads[0][value] != reloads[1][value]) {
            first_difference = value;
            break;
        }
    }
    EXPECT_EQ(first_difference, 0x12);
    EXPECT_EQ(reloads[0][0x12], 0xFFFF);
    EXPECT_EQ(reloads[1][0x12], 0x12FE);
    EXPECT_EQ(reloads[2][0x12], reloads[1][0x12]);
    EXPECT_EQ(reloads[3][0x12], reloads[0][0x12]);
    EXPECT_EQ(reloads[2][0x89], reloads[1][0x89]);
    EXPECT_EQ(reloads[3][0x89], reloads[0][0x89]);
    uint64_t high_range_difference_mask = 0;
    for (size_t value = 0x80; value <= 0xA5; ++value) {
        if (reloads[0][value] != reloads[1][value]) {
            high_range_difference_mask |= uint64_t{1} << (value - 0x80);
        }
    }
    EXPECT_EQ(high_range_difference_mask, uint64_t{0xFFFFF});
    EXPECT_EQ(reloads[0][0xFF], 0xC0FE);
    EXPECT_EQ(reloads[1][0xFF], 0xC0FE);
}

TEST(Sab80C517, SixRomRam69ProducerUsesSharedCapAndFlaggedValue) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const auto variants = root / "firmwares_modificados_ma17_tipo";
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        variants / "tipo 1.6 alcool27c256.bin",
        variants / "tipo 1.6 alcool27c256+1.5bar.bin",
        variants / "tipo 1.6 alcool27c256 SUN 8817.bin",
        variants / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        variants / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    struct Case {
        uint8_t upper8c, flag2b, expected;
    };
    constexpr std::array cases{
        Case{0x70, 0x00, 0x70}, Case{0x89, 0x00, 0x89},
        Case{0xB0, 0x00, 0xA5}, Case{0x89, 0x10, 0x80},
        Case{0xB0, 0x10, 0x80}};
    std::array<unsigned char, 0x3B08 - 0x3AE4> reference_code{};
    for (size_t index = 0; index < paths.size(); ++index) {
        SCOPED_TRACE(paths[index].string());
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[index], std::ios::binary);
        ASSERT_TRUE(file.is_open());
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const bool gasoline_layout = index == 0 || index == 3;
        const size_t start = gasoline_layout ? 0x3AE4 : 0x3B12;
        const size_t end = gasoline_layout ? 0x3B08 : 0x3B36;
        if (index == 0) {
            std::copy_n(code.begin() + start, reference_code.size(),
                        reference_code.begin());
        } else {
            EXPECT_TRUE(std::equal(reference_code.begin(), reference_code.end(),
                                   code.begin() + start));
        }
        EXPECT_EQ(code[0x72A2], 0x80);
        EXPECT_EQ(code[0x72A7], 0xA5);
        for (const auto &test : cases) {
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            upper[0x8C - 0x80] = test.upper8c;
            cpu.mLowerData[0x2B] = test.flag2b;
            cpu.mPC = static_cast<uint16_t>(start);
            for (int step = 0; step < 40 && cpu.mPC != end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, end);
            EXPECT_EQ(cpu.mLowerData[0x69], test.expected)
                << "upper 8Ch=" << static_cast<unsigned>(test.upper8c)
                << " flags 2Bh=" << static_cast<unsigned>(test.flag2b);
        }
    }
}

TEST(Sab80C517, SixRomSerialFrame38SetsRam69FlagBelowRpmBound) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const auto variants = root / "firmwares_modificados_ma17_tipo";
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        variants / "tipo 1.6 alcool27c256.bin",
        variants / "tipo 1.6 alcool27c256+1.5bar.bin",
        variants / "tipo 1.6 alcool27c256 SUN 8817.bin",
        variants / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        variants / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    struct Case {
        uint8_t command, rpm_byte, initial_flag, expected_flag;
        uint8_t counter, terminator, expected_state;
        uint16_t stop_g;
    };
    constexpr std::array cases{
        Case{0x38, 0x64, 0x00, 0x10, 2, 3, 0x08, 0x510C},
        Case{0x38, 0x65, 0x00, 0x00, 2, 3, 0x04, 0x510C},
        Case{0x09, 0x28, 0x10, 0x00, 2, 3, 0x00, 0x5096},
        Case{0x38, 0x64, 0x00, 0x00, 3, 3, 0x04, 0x510C},
        Case{0x38, 0x64, 0x00, 0x00, 2, 0, 0x04, 0x510C}};
    for (size_t index = 0; index < paths.size(); ++index) {
        SCOPED_TRACE(paths[index].string());
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[index], std::ios::binary);
        ASSERT_TRUE(file.is_open());
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        EXPECT_EQ(code[0x728D], 0x64);
        const bool gasoline_layout = index == 0 || index == 3;
        const uint16_t shift = gasoline_layout ? 0 : 0xC3;
        for (const auto &test : cases) {
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_P2] = 0;
            cpu.mLowerData[0x40] = 1;
            cpu.mLowerData[0x44] = 0xBB;
            xram[0xB9] = test.counter;
            xram[0xBA] = test.command;
            xram[0xBB] = test.terminator;
            cpu.mLowerData[0x47] = test.rpm_byte;
            cpu.mLowerData[0x2B] = test.initial_flag;
            cpu.mPC = static_cast<uint16_t>(0x5058 + shift);
            const uint16_t stop = static_cast<uint16_t>(test.stop_g + shift);
            for (int step = 0; step < 60 && cpu.mPC != stop; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, stop)
                << "command=" << static_cast<unsigned>(test.command);
            if (test.counter == 2 && test.terminator == 3) {
                EXPECT_EQ(cpu.mLowerData[2], test.command);
                EXPECT_EQ(cpu.mLowerData[0x40], 2);
            }
            EXPECT_EQ(cpu.mLowerData[0x2B] & 0x10, test.expected_flag);
            if (stop == static_cast<uint16_t>(0x510C + shift)) {
                EXPECT_EQ(cpu.mLowerData[0x42], test.expected_state);
            }
        }
    }
}

TEST(Sab80C517, FiatRpmSegmentVariantsChangeMatrixColumnBeforeLookup) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin"};
    std::array<uint8_t, 2> offsets{};
    std::array<std::array<uint8_t, 17>, 2> axis_tables{};
    for (size_t index = 0; index < paths.size(); ++index) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(paths[index], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[index];
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        std::copy_n(code.begin() + 0x7570, 17, axis_tables[index].begin());
        cpu.mLowerData[0x47] = 0x28; // Same simulated RPM byte.
        cpu.mLowerData[0x6F] = 0x27; // Same second-axis byte.
        cpu.mPC = 0x1344;
        for (int step = 0; step < 5000 && cpu.mPC != 0x136F; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x136F) << paths[index];
        offsets[index] = cpu.mLowerData[5]; // R5, bank zero.
    }
    EXPECT_EQ(offsets[0], 0x30);
    EXPECT_EQ(offsets[1], 0x32);
    EXPECT_TRUE(std::equal(axis_tables[0].begin(), axis_tables[0].end() - 1,
                           axis_tables[1].begin()));
    EXPECT_EQ(axis_tables[0][16], 0x10);
    EXPECT_EQ(axis_tables[1][16], 0x25);
}

TEST(Sab80C517, FiatRpmSelectorChangesSharedTableLookup) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin"};
    constexpr std::array<uint8_t, 2> selectors{0x03, 0x15};
    constexpr std::array<uint8_t, 2> expected_r2{0x97, 0x86};
    constexpr std::array<std::array<uint16_t, 2>, 2> expected_reads{{
        {{0x7ECD, 0x7ECE}}, {{0x7ECF, 0x7ED0}}}};
    for (size_t case_index = 0; case_index < paths.size() * selectors.size();
         ++case_index) {
        const size_t rom_index = case_index / selectors.size();
        const size_t selector_index = case_index % selectors.size();
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(paths[rom_index], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom_index];
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        upper[0xBC - 0x80] = selectors[selector_index];
        cpu.mLowerData[0x47] = 0x28;
        cpu.mLowerData[0x28] = 0x02; // Select the 70C2h -> 7ECAh branch.
        cpu.mPC = 0x330D;
        std::array<uint16_t, 2> reads{};
        size_t read_count = 0;
        for (int step = 0; step < 1000 && cpu.mPC != 0x3371; ++step) {
            // SAB 80C517 Instruction Set, p. 222: MOVC reads A+DPTR.
            if (cpu.mPC == 0x532F || cpu.mPC == 0x5333) {
                ASSERT_LT(read_count, 2);
                reads[read_count++] = uint16_t(
                    (cpu.mSFR[REG_DPH] << 8 | cpu.mSFR[REG_DPL]) +
                    cpu.mSFR[REG_ACC]);
            }
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x3371) << paths[rom_index];
        ASSERT_EQ(read_count, 2);
        EXPECT_EQ(reads, expected_reads[selector_index]);
        EXPECT_EQ(cpu.mLowerData[2], expected_r2[selector_index]);
    }
}

TEST(Sab80C517, FiatStartupMapsUseThreePointerTargetsAndOriginalBytes) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin"};
    constexpr std::array<uint16_t, 3> starts{0x7B46, 0x7BBE, 0x7C36};
    for (size_t rom_index = 0; rom_index < paths.size(); ++rom_index) {
        for (size_t mode = 0; mode < starts.size(); ++mode) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            std::ifstream file(paths[rom_index], std::ios::binary);
            ASSERT_TRUE(file.is_open()) << paths[rom_index];
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            cpu.mLowerData[0x57] = static_cast<uint8_t>(mode);
            cpu.mPC = 0x330D;
            std::array<uint16_t, 2> reads{};
            std::array<uint8_t, 2> values{};
            size_t read_count = 0;
            bool selected_startup_map = false;
            for (int step = 0; step < 1000 && cpu.mPC != 0x3371; ++step) {
                if (cpu.mPC == 0x3356)
                    selected_startup_map = true;
                // SAB 80C517 Instruction Set, p. 222: MOVC uses A+DPTR.
                if (cpu.mPC == 0x532F || cpu.mPC == 0x5333) {
                    ASSERT_LT(read_count, 2);
                    reads[read_count] = uint16_t(
                        (cpu.mSFR[REG_DPH] << 8 | cpu.mSFR[REG_DPL]) +
                        cpu.mSFR[REG_ACC]);
                    values[read_count] = code[reads[read_count]];
                    ++read_count;
                }
                tick(&cpu);
            }
            ASSERT_TRUE(selected_startup_map);
            ASSERT_EQ(cpu.mPC, 0x3371) << paths[rom_index];
            ASSERT_EQ(read_count, 2);
            EXPECT_EQ(reads[0], starts[mode]);
            EXPECT_EQ(reads[1], starts[mode] + 1);
            EXPECT_EQ(values[0], rom_index == 0 ? 0x99 : 0xA1);
            EXPECT_EQ(cpu.mLowerData[2], values[0]);
        }
    }
}

TEST(Sab80C517, AlcoholCodeSelectsThreeStartupMatricesAtFixedCell) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    constexpr std::array<uint16_t, 3> starts{0x7B46, 0x7BBE, 0x7C36};
    constexpr std::array expected{
        std::array<uint8_t, 3>{0x8E, 0x97, 0x77},
        std::array<uint8_t, 3>{0xA4, 0xAD, 0x8D}};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        for (size_t mode = 0; mode < starts.size(); ++mode) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(paths[rom], std::ios::binary);
            ASSERT_TRUE(file.is_open()) << paths[rom];
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            cpu.mLowerData[0] = 15; // Row stride; R4=0 avoids second row.
            cpu.mLowerData[4] = 0;
            cpu.mLowerData[5] = 4;  // Fifth raw cell in first row.
            cpu.mLowerData[6] = 0;
            cpu.mLowerData[0x57] = static_cast<uint8_t>(mode);
            cpu.mPC = 0x3372;
            bool reached_movc = false;
            for (int step = 0; step < 100 && cpu.mPC != 0x339F; ++step) {
                if (cpu.mPC == 0x53F2) {
                    reached_movc = true;
                    EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                       cpu.mSFR[REG_DPL]), starts[mode]);
                    EXPECT_EQ(cpu.mSFR[REG_ACC], 4);
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_TRUE(reached_movc) << paths[rom];
            ASSERT_EQ(cpu.mPC, 0x339F) << paths[rom];
            EXPECT_EQ(code[starts[mode] + 4], expected[rom][mode]);
            EXPECT_EQ(cpu.mLowerData[2], expected[rom][mode]);
        }
    }
}

TEST(Sab80C517, AlcoholCodeFlagsSelectFourUpperAeMatrices) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    constexpr std::array<uint16_t, 4> starts{0x7B46, 0x7BBE, 0x7CAE, 0x7D26};
    for (const auto &path : paths) {
        for (size_t flags = 0; flags < starts.size(); ++flags) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            cpu.mLowerData[0] = 15; // Row stride used by the original reader.
            cpu.mLowerData[4] = 0;  // No interpolation into the next row.
            cpu.mLowerData[5] = 4;  // Fifth raw cell in row zero.
            cpu.mLowerData[6] = 0;
            cpu.mLowerData[0x2B] = (flags & 1) ? 0x80 : 0;
            cpu.mLowerData[0x2F] = (flags & 2) ? 0x04 : 0;
            cpu.mPC = 0x3369;
            bool reached_movc = false;
            for (int step = 0; step < 100 && cpu.mPC != 0x3381; ++step) {
                if (cpu.mPC == 0x53F2) {
                    reached_movc = true;
                    EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                       cpu.mSFR[REG_DPL]), starts[flags]);
                    EXPECT_EQ(cpu.mSFR[REG_ACC], 4);
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_TRUE(reached_movc) << path << " flags=" << flags;
            ASSERT_EQ(cpu.mPC, 0x3381) << path << " flags=" << flags;
            EXPECT_EQ(cpu.mLowerData[2], code[starts[flags] + 4]);
        }
    }
}

TEST(Sab80C517, AlcoholCodeFlagSelectsConstant7eacCurve) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (const auto &path : paths) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        constexpr std::array<uint8_t, 4> indices{0, 3, 4, 13};
        for (size_t case_index = 0; case_index < 8; ++case_index) {
            const uint8_t index = indices[case_index / 2];
            const bool flag = (case_index & 1) != 0;
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false); // Keep the original ROM loaded above.
            cpu.mSFR[REG_PSW] = 0;
            upper[0xBC - 0x80] = static_cast<uint8_t>(0xA0 | index);
            cpu.mPC = 0x3329;
            for (int step = 0; step < 8 && cpu.mPC != 0x3333; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x3333) << path;
            EXPECT_EQ(cpu.mLowerData[7], index) << path;
            EXPECT_EQ(cpu.mLowerData[6], 0xA0) << path;
            cpu.mLowerData[0x22] = 0x02; // Enter 3384h branch.
            cpu.mLowerData[0x2B] = flag ? 0x80 : 0;
            cpu.mLowerData[6] = 0; // No interpolation fraction.
            cpu.mPC = 0x3384;
            const uint16_t target = flag ? 0x7EAC : 0x7E9D;
            bool reached_movc = false;
            for (int step = 0; step < 100 && cpu.mPC != 0x33D3; ++step) {
                if (cpu.mPC == 0x53F2) {
                    reached_movc = true;
                    EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                       cpu.mSFR[REG_DPL]), target) << path;
                    EXPECT_EQ(cpu.mSFR[REG_ACC], index) << path;
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_TRUE(reached_movc) << path;
            ASSERT_EQ(cpu.mPC, 0x33D3) << path;
            const uint8_t expected = code[target + index];
            EXPECT_EQ(cpu.mLowerData[2], expected) << path;
            EXPECT_EQ(upper[0xA4 - 0x80], expected) << path;
            EXPECT_EQ(expected, flag ? 0x99 : code[0x7E9D + index]) << path;
            if (index <= 3)
                EXPECT_EQ(expected, 0x99) << path;
            else if (!flag)
                EXPECT_LT(expected, 0x99) << path;
        }
    }
}

TEST(Sab80C517, Pointer70bcSelectsThreeCurvesWithRam57) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t image_index = 0; image_index < paths.size(); ++image_index) {
        const auto &path = paths[image_index];
        const bool a_code = image_index != 0 && image_index != 3;
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        for (uint8_t mode = 0; mode < 3; ++mode) {
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_PSW] = 0; // Bank 0 and F0 clear.
            cpu.mLowerData[0x57] = mode;
            cpu.mLowerData[0x2B] = 0; // A-code selects base 70BCh.
            cpu.mLowerData[7] = 9; // Tenth cell of the selected curve.
            cpu.mLowerData[6] = 0; // No fractional interpolation.
            cpu.mPC = a_code ? 0x3384 : 0x335C;
            const uint16_t expected_pointer = 0x70BC + 2 * mode;
            const uint16_t expected_table =
                uint16_t(code[expected_pointer] << 8 | code[expected_pointer + 1]);
            ASSERT_EQ(expected_table, (std::array<uint16_t, 3>{
                0x7E9D, 0x7EAC, 0x7EBB})[mode]) << path;
            bool reached_movc = false;
            for (int step = 0; step < 100 &&
                 cpu.mPC != (a_code ? 0x339F : 0x3371); ++step) {
                if (cpu.mPC == (a_code ? 0x53F2 : 0x532F)) {
                    reached_movc = true;
                    EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                       cpu.mSFR[REG_DPL]), expected_table)
                        << path << " mode " << int(mode);
                    EXPECT_EQ(cpu.mSFR[REG_ACC], 9) << path;
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_TRUE(reached_movc) << path << " mode " << int(mode);
            ASSERT_EQ(cpu.mPC, (a_code ? 0x339F : 0x3371)) << path;
            EXPECT_EQ(cpu.mLowerData[2], code[expected_table + 9])
                << path << " mode " << int(mode);
            for (int step = 0; step < 25 &&
                 cpu.mPC != (a_code ? 0x33CF : 0x33A1); ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, (a_code ? 0x33CF : 0x33A1)) << path;
            for (int step = 0; step < 3; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            EXPECT_EQ(upper[0xA4 - 0x80], code[expected_table + 9])
                << path << " mode " << int(mode);
        }
    }
}

TEST(Sab80C517, Pointer705a705c70d0BranchesFeedXramF800) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t image_index = 0; image_index < paths.size(); ++image_index) {
        const auto &path = paths[image_index];
        const bool a_code = image_index != 0 && image_index != 3;
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        for (const auto [f8da, flag2f5, pointer, expected_target] :
             {std::tuple<uint8_t, uint8_t, uint16_t, uint16_t>{
                  0, 1, 0x705A, 0x7831},
              {0, 0, 0x705C, 0x7859}, {1, 0, 0x70D0, 0x786D}}) {
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_PSW] = 0;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_XPAGE] = 0xF8;
            cpu.mLowerData[0x2F] = flag2f5 ? 0x20 : 0;
            cpu.mLowerData[0] = 4; // Row stride in the matrix helper.
            cpu.mLowerData[4] = 0; // No row fraction.
            cpu.mLowerData[5] = 1; // Second cell of first row.
            cpu.mLowerData[6] = 0; // No column fraction.
            xram[0xF8DA] = f8da;
            cpu.mPC = a_code ? 0x3E9B : 0x3DDE;
            const uint16_t target =
                uint16_t(code[pointer] << 8 | code[pointer + 1]);
            EXPECT_EQ(target, expected_target) << path;
            bool reached_movc = false;
            for (int step = 0; step < 100 &&
                 cpu.mPC != (a_code ? 0x3EC3 : 0x3E06); ++step) {
                if (cpu.mPC == (a_code ? 0x53F2 : 0x532F)) {
                    reached_movc = true;
                    EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                       cpu.mSFR[REG_DPL]), target) << path;
                    EXPECT_EQ(cpu.mSFR[REG_ACC], 1) << path;
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_TRUE(reached_movc) << path << " pointer " << pointer;
            ASSERT_EQ(cpu.mPC, (a_code ? 0x3EC3 : 0x3E06)) << path;
            EXPECT_EQ(xram[0xF800], code[target + 1])
                << path << " pointer " << pointer;
        }
    }
}

TEST(Sab80C517, SixRomFinalMatrixRowReadsAdjacentPointerInterval) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    struct Case {
        uint16_t pointer;
        uint16_t matrix;
        uint16_t next_start;
        uint16_t g_start;
        uint16_t g_end;
        uint8_t f8da;
        uint8_t flag2f5;
    };
    const std::array cases{
        Case{0x705A, 0x7831, 0x7845, 0x3DDE, 0x3E06, 0, 1},
        Case{0x705C, 0x7859, 0x786D, 0x3DDE, 0x3E06, 0, 0},
        Case{0x70D0, 0x786D, 0x7881, 0x3DDE, 0x3E06, 1, 0},
        Case{0x7080, 0x7895, 0x78A9, 0x3E25, 0x3E34, 0, 0},
        Case{0x7084, 0x78BD, 0x78D1, 0x3E1A, 0x3E34, 0, 0}};
    for (size_t image_index = 0; image_index < paths.size(); ++image_index) {
        const auto &path = paths[image_index];
        const bool a_code = image_index != 0 && image_index != 3;
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        for (const Case test : cases) {
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_PSW] = 0;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_XPAGE] = 0xF8;
            cpu.mLowerData[0x2F] = test.flag2f5 ? 0x20 : 0;
            cpu.mLowerData[0] = 4;
            cpu.mLowerData[4] = 0x80;
            cpu.mLowerData[5] = 15;
            cpu.mLowerData[6] = 0;
            xram[0xF8DA] = test.f8da;
            cpu.mPC = test.g_start + (a_code ? 0xBD : 0);
            EXPECT_EQ(uint16_t(code[test.pointer] << 8 |
                               code[test.pointer + 1]), test.matrix) << path;
            ASSERT_EQ(test.matrix + 20, test.next_start);
            bool read_next_interval = false;
            const uint16_t end = test.g_end + (a_code ? 0xBD : 0);
            for (int step = 0; step < 150 && cpu.mPC != end; ++step) {
                if (cpu.mPC == (a_code ? 0x5413 : 0x5350)) {
                    read_next_interval = true;
                    EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                       cpu.mSFR[REG_DPL]), test.matrix) << path;
                    EXPECT_EQ(cpu.mSFR[REG_ACC], 20) << path;
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                    EXPECT_EQ(cpu.mSFR[REG_ACC], code[test.next_start])
                        << path << " pointer " << test.pointer;
                    continue;
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, end) << path;
            EXPECT_TRUE(read_next_interval) << path << " pointer " << test.pointer;
        }
    }
}

TEST(Sab80C517, T2i1GuardSkips7098And70d2PointerPaths) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t image_index = 0; image_index < paths.size(); ++image_index) {
        const auto &path = paths[image_index];
        const bool a_code = image_index != 0 && image_index != 3;
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        EXPECT_EQ(uint16_t(code[0x7098] << 8 | code[0x7099]), 0x7845)
            << path;
        EXPECT_EQ(uint16_t(code[0x70D2] << 8 | code[0x70D3]), 0x7881)
            << path;
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        reset(&cpu, false);
        cpu.mSFR[REG_T2CON] = 0x02;
        cpu.mPC = a_code ? 0x3E9B : 0x3DDE;
        cpu.mTickDelay = 0;
        tick(&cpu);
        EXPECT_EQ(cpu.mPC, (a_code ? 0x3EC3 : 0x3E06)) << path;
    }
}

TEST(Sab80C517, T2i1GuardSkips7082And7086PointerPaths) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t image_index = 0; image_index < paths.size(); ++image_index) {
        const auto &path = paths[image_index];
        const bool a_code = image_index != 0 && image_index != 3;
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        EXPECT_EQ(uint16_t(code[0x7082] << 8 | code[0x7083]), 0x78A9)
            << path;
        EXPECT_EQ(uint16_t(code[0x7086] << 8 | code[0x7087]), 0x78D1)
            << path;
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        reset(&cpu, false);
        cpu.mSFR[REG_T2CON] = 0x02;
        cpu.mPC = a_code ? 0x3EC3 : 0x3E06;
        cpu.mTickDelay = 0;
        tick(&cpu);
        EXPECT_EQ(cpu.mPC, (a_code ? 0x3EF1 : 0x3E34)) << path;
    }
}

TEST(Sab80C517, Pointer703c703eBranchesFeedXramF806) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t image_index = 0; image_index < paths.size(); ++image_index) {
        const auto &path = paths[image_index];
        const bool a_code = image_index != 0 && image_index != 3;
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        for (const auto [flag2f5, pointer, target] :
             {std::tuple<uint8_t, uint16_t, uint16_t>{1, 0x703C, 0x753E},
              {0, 0x703E, 0x7548}}) {
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_PSW] = 0;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_XPAGE] = 0xF8;
            cpu.mLowerData[0x2F] = flag2f5 ? 0x20 : 0;
            cpu.mLowerData[5] = 0;
            cpu.mLowerData[6] = 0;
            xram[0xF806] = 0xFF;
            cpu.mPC = a_code ? 0x488E : 0x47D1;
            EXPECT_EQ(uint16_t(code[pointer] << 8 | code[pointer + 1]),
                      target) << path;
            bool reached_movc = false;
            for (int step = 0; step < 50 &&
                 cpu.mPC != (a_code ? 0x489E : 0x47E1); ++step) {
                if (cpu.mPC == (a_code ? 0x53F2 : 0x532F)) {
                    reached_movc = true;
                    EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                       cpu.mSFR[REG_DPL]), target) << path;
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_TRUE(reached_movc) << path;
            ASSERT_EQ(cpu.mPC, (a_code ? 0x489E : 0x47E1)) << path;
            EXPECT_EQ(xram[0xF806], code[target]) << path;
        }
    }
}

TEST(Sab80C517, FourNeutral70ae70b4CurvesUseAdjacentByteHelper) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    struct Case {
        uint16_t pointer;
        uint16_t target;
        uint16_t g_pc;
        uint16_t g_end_pc;
        uint8_t output_upper_addr;
    };
    for (size_t image_index = 0; image_index < paths.size(); ++image_index) {
        const auto &path = paths[image_index];
        const bool a_code = image_index != 0 && image_index != 3;
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        for (const Case test : {Case{0x70AE, 0x7B00, 0x483B, 0x4847, 0xCF},
                                {0x70B0, 0x7B0A, 0x4874, 0x4890, 0xCE},
                                {0x70B2, 0x7B14, 0x48A9, 0x48CC, 0xCD},
                                {0x70B4, 0x7B1E, 0x4896, 0x48CC, 0xCD}}) {
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_PSW] = 0;
            cpu.mLowerData[5] = 3;
            cpu.mLowerData[6] = 0;
            upper[test.output_upper_addr - 0x80] = 0x55;
            const uint16_t start = test.g_pc + (a_code ? 0xBD : 0);
            cpu.mPC = start;
            EXPECT_EQ(uint16_t(code[test.pointer] << 8 |
                               code[test.pointer + 1]), test.target) << path;
            bool read_first_cell = false;
            bool read_next_cell = false;
            for (int step = 0; step < 70 && cpu.mPC != start + 6; ++step) {
                if (cpu.mPC == (a_code ? 0x53F2 : 0x532F) ||
                    cpu.mPC == (a_code ? 0x53F6 : 0x5333)) {
                    const bool first = cpu.mPC == (a_code ? 0x53F2 : 0x532F);
                    (first ? read_first_cell : read_next_cell) = true;
                    EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                       cpu.mSFR[REG_DPL]), test.target) << path;
                    EXPECT_EQ(cpu.mSFR[REG_ACC], first ? 3 : 4) << path;
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, start + 6) << path;
            EXPECT_TRUE(read_first_cell) << path;
            EXPECT_TRUE(read_next_cell) << path;
            EXPECT_EQ(cpu.mLowerData[2], 0x80) << path;
            const uint16_t end = test.g_end_pc + (a_code ? 0xBD : 0);
            for (int step = 0; step < 35 && cpu.mPC != end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, end) << path;
            EXPECT_EQ(upper[test.output_upper_addr - 0x80], 0)
                << path << " pointer " << test.pointer;
        }
    }
}

TEST(Sab80C517, Pointer7088LoadsFfIntoXramF8fbWhenRam7aIsZero) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t image_index = 0; image_index < paths.size(); ++image_index) {
        const auto &path = paths[image_index];
        const bool a_code = image_index != 0 && image_index != 3;
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const uint16_t target = uint16_t(code[0x7088] << 8 | code[0x7089]);
        ASSERT_EQ(target, 0x78E5) << path;
        for (const uint8_t ram7a : {uint8_t{0}, uint8_t{1}}) {
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_PSW] = 0;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_XPAGE] = 0xF8;
            cpu.mLowerData[0x7A] = ram7a;
            cpu.mLowerData[5] = 1;
            cpu.mLowerData[6] = 0;
            cpu.mPC = a_code ? 0x3EF1 : 0x3E34;
            bool reached_movc = false;
            for (int step = 0; step < 70 &&
                 cpu.mPC != (a_code ? 0x3EFE : 0x3E41); ++step) {
                if (cpu.mPC == (a_code ? 0x53F2 : 0x532F)) {
                    reached_movc = true;
                    EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                       cpu.mSFR[REG_DPL]), target) << path;
                    EXPECT_EQ(cpu.mSFR[REG_ACC], 1) << path;
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, (a_code ? 0x3EFE : 0x3E41)) << path;
            EXPECT_EQ(reached_movc, ram7a == 0) << path;
            EXPECT_EQ(xram[0xF8FB], ram7a == 0 ? 0xFF : 0) << path;
        }
    }
}

TEST(Sab80C517, Pointer708a708cBranchesFeedXramF802) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t image_index = 0; image_index < paths.size(); ++image_index) {
        const auto &path = paths[image_index];
        const bool a_code = image_index != 0 && image_index != 3;
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        for (const auto [flag2f5, pointer, target] :
             {std::tuple<uint8_t, uint16_t, uint16_t>{1, 0x708A, 0x73C8},
              {0, 0x708C, 0x73CE}}) {
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_PSW] = 0;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_XPAGE] = 0xF8;
            cpu.mSFR[REG_T2CON] &= static_cast<uint8_t>(~0x02);
            cpu.mLowerData[0x2F] = flag2f5 ? 0x20 : 0;
            cpu.mLowerData[5] = 1; // Second byte of the selected curve.
            cpu.mLowerData[6] = 0; // No interpolation fraction.
            cpu.mPC = a_code ? 0x46C6 : 0x4609;
            EXPECT_EQ(uint16_t(code[pointer] << 8 | code[pointer + 1]),
                      target) << path;
            bool reached_movc = false;
            for (int step = 0; step < 100 &&
                 cpu.mPC != (a_code ? 0x46D9 : 0x461C); ++step) {
                if (cpu.mPC == (a_code ? 0x53F2 : 0x532F)) {
                    reached_movc = true;
                    EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                       cpu.mSFR[REG_DPL]), target) << path;
                    EXPECT_EQ(cpu.mSFR[REG_ACC], 1) << path;
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_TRUE(reached_movc) << path << " pointer " << pointer;
            ASSERT_EQ(cpu.mPC, (a_code ? 0x46D9 : 0x461C)) << path;
            EXPECT_EQ(xram[0xF802], code[target + 1]) << path;
        }
    }
}

TEST(Sab80C517, Pointer70d4IndexesUpperBcAndWritesUpper8d) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    struct Case {
        uint8_t upper_bc;
        uint8_t index;
    };
    for (size_t image_index = 0; image_index < paths.size(); ++image_index) {
        const auto &path = paths[image_index];
        const bool a_code = image_index != 0 && image_index != 3;
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        for (const Case test : {Case{0x03, 3}, {0x05, 5},
                                {0x07, 7}, {0x8A, 11}, {0x8F, 16}}) {
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_PSW] = 0;
            cpu.mSFR[REG_B] = 0xA5;
            upper[0xBC - 0x80] = test.upper_bc;
            upper[0x8D - 0x80] = 0xFF;
            cpu.mPC = a_code ? 0x37D8 : 0x37AA;
            const uint16_t target = uint16_t(code[0x70D4] << 8 |
                                             code[0x70D5]);
            ASSERT_EQ(target, 0x7E8E) << path;
            bool reached_movc = false;
            for (int step = 0; step < 35 &&
                 cpu.mPC != (a_code ? 0x37F2 : 0x37C4); ++step) {
                if (cpu.mPC == (a_code ? 0x37ED : 0x37BF)) {
                    reached_movc = true;
                    EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                       cpu.mSFR[REG_DPL]), target) << path;
                    EXPECT_EQ(cpu.mSFR[REG_ACC], test.index) << path;
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_TRUE(reached_movc) << path;
            ASSERT_EQ(cpu.mPC, (a_code ? 0x37F2 : 0x37C4)) << path;
            EXPECT_EQ(upper[0x8D - 0x80], code[target + test.index])
                << path << " upper BC=" << unsigned(test.upper_bc);
            EXPECT_EQ(cpu.mSFR[REG_B], 0xA5) << path;
        }
    }
}

TEST(Sab80C517, Pointer70baSelects7d9eWhenModeTwo) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin"};
    constexpr std::array<uint8_t, 4> expected_a4{0x77, 0x77, 0x8D, 0x7F};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        cpu.mLowerData[0] = 15;
        cpu.mLowerData[4] = 0;
        cpu.mLowerData[5] = 4;
        cpu.mLowerData[6] = 0;
        cpu.mLowerData[0x57] = 2;    // Third pointer from 70B6h is 70BAh.
        cpu.mLowerData[0x2F] = 0x04; // Select 70B6h pointer group.
        cpu.mLowerData[0x2B] = 0;    // A-code starts at 70B6h, not 70B8h.
        cpu.mSFR[0xC8 - 0x80] = 0;  // T2CON.1=0 follows the @A4h store.
        const bool gasoline_code = rom == 0 || rom == 3;
        cpu.mPC = gasoline_code ? 0x334D : 0x3369;
        const uint16_t movc = gasoline_code ? 0x532F : 0x53F2;
        const uint16_t finish = gasoline_code ? 0x33A5 : 0x33D3;
        bool reached_movc = false;
        for (int step = 0; step < 150 && cpu.mPC != finish; ++step) {
            if (cpu.mPC == movc) {
                reached_movc = true;
                EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                   cpu.mSFR[REG_DPL]), 0x7D9E);
                EXPECT_EQ(cpu.mSFR[REG_ACC], 4);
            }
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_TRUE(reached_movc) << paths[rom];
        ASSERT_EQ(cpu.mPC, finish) << paths[rom];
        EXPECT_EQ(cpu.mLowerData[2], code[0x7DA2]);
        EXPECT_EQ(upper[0xA4 - 0x80], expected_a4[rom]);
    }
}

TEST(Sab80C517, FiatFlag2f2GateDependsOnPsw5AndTimer2Mode) {
    for (const auto [psw5, timer2_mode, expected] : {
             std::tuple{false, false, false},
             std::tuple{true, false, true},
             std::tuple{true, true, false}}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 0x1000> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::ifstream file(MA17_ROM_PATH, std::ios::binary);
        ASSERT_TRUE(file.is_open());
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        cpu.mSFR[REG_PSW] = psw5 ? 0x20 : 0;
        cpu.mSFR[0xC8 - 0x80] = timer2_mode ? 0x02 : 0;
        cpu.mLowerData[0] = 0x9F; // R0 addresses the XRAM gate byte.
        cpu.mLowerData[0x22] = 0; // 22h.6 bypasses coolant threshold.
        cpu.mLowerData[0x2F] = 0; // 2Fh.5=0, 2Fh.2 starts clear.
        cpu.mSFR[REG_ACC] = 0;
        cpu.mPC = 0x3CDA;
        for (int step = 0; step < 30 && cpu.mPC != 0x3D0E; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x3D0E);
        EXPECT_EQ((cpu.mLowerData[0x2F] & 0x04) != 0, expected);
    }
}

TEST(Sab80C517, FiatAndAlcoholCodeRead7e16IntoUpperCa) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin"};
    constexpr std::array<uint16_t, 2> entry{0x3830, 0x385E};
    constexpr std::array<uint16_t, 2> finish{0x384C, 0x387A};
    constexpr std::array<uint16_t, 2> movc{0x532F, 0x53F2};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        cpu.mLowerData[1] = 0xFF; // Fixed multiplier for the table result.
        cpu.mLowerData[4] = 0;    // Read one row without interpolation.
        cpu.mLowerData[5] = 2;    // 7E18h is 19h in G, 33h in A.
        cpu.mLowerData[6] = 0;
        cpu.mLowerData[0x70] = 0; // 7163h supplies FFh for the second factor.
        cpu.mPC = entry[rom];
        bool reached_movc = false;
        for (int step = 0; step < 100 && cpu.mPC != finish[rom]; ++step) {
            if (cpu.mPC == movc[rom] && !reached_movc) {
                reached_movc = true;
                EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                   cpu.mSFR[REG_DPL]), 0x7E16);
                EXPECT_EQ(cpu.mSFR[REG_ACC], 2);
            }
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_TRUE(reached_movc) << paths[rom];
        ASSERT_EQ(cpu.mPC, finish[rom]) << paths[rom];
        EXPECT_EQ(code[0x7E18], rom == 0 ? 0x19 : 0x33);
        EXPECT_EQ(upper[0xCA - 0x80], rom == 0 ? 0x17 : 0x31);
    }
}

TEST(Sab80C517, FiatAndAlcoholUpperCaConsumerUsesMaximumBeforeUpdatingR2) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    struct Scenario {
        std::filesystem::path path;
        uint16_t entry;
        uint16_t finish;
        uint8_t upper_ca;
    };
    for (const auto &scenario : {
             Scenario{MA17_ROM_PATH, 0x39B2, 0x39F4, 3},
             Scenario{MA17_ROM_PATH, 0x39B2, 0x39F4, 5},
             Scenario{MA17_ROM_PATH, 0x39B2, 0x39F4, 8},
             Scenario{MA17_ROM_PATH, 0x39B2, 0x39F4, 0x17},
             Scenario{root / "firmwares_modificados_ma17_tipo" /
                          "tipo 1.6 alcool27c256.bin", 0x39E0, 0x3A22, 0x17},
             Scenario{root / "firmwares_modificados_ma17_tipo" /
                          "tipo 1.6 alcool27c256.bin", 0x39E0, 0x3A22, 0x31}}) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(scenario.path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << scenario.path;
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        code = original;
        cpu.mLowerData[2] = 0x10; // R2 entering the original clamp.
        cpu.mLowerData[7] = 0x7F; // Select the 39E9h additive path.
        cpu.mSFR[REG_B] = 5;
        upper[0xCA - 0x80] = scenario.upper_ca;
        cpu.mPC = scenario.entry;
        for (int step = 0; step < 30 && cpu.mPC != scenario.finish; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, scenario.finish) << scenario.path;
        EXPECT_EQ(cpu.mSFR[REG_ACC],
                  0x10 + std::max(5, int(scenario.upper_ca)));
        cpu.mTickDelay = 0;
        tick(&cpu);
        EXPECT_EQ(cpu.mLowerData[2],
                  0x10 + std::max(5, int(scenario.upper_ca)));
    }
}

TEST(Sab80C517, FiatUpper81StateProducerOpensB5MatrixBranch) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    ASSERT_EQ(original[0x72A6], 0x06);
    ASSERT_EQ(original[0x72DE], 0x96);

    struct Case { uint8_t rpm_byte, xram_f9, expected_upper; };
    for (const auto scenario : {
             Case{0x48, 0, 0x24},
             Case{0x46, 0, 0x00},
             Case{0x48, 1, 0x00}}) {
        SCOPED_TRACE(testing::Message() << "47=" << int(scenario.rpm_byte)
                                        << " F9=" << int(scenario.xram_f9));
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_P2] = 0xF8;
        cpu.mSFR[REG_XPAGE] = 0xF8;
        cpu.mSFR[REG_DPH] = 0x72;
        cpu.mSFR[REG_DPL] = 0x00;
        cpu.mLowerData[0x46] = 0x40;
        cpu.mLowerData[0x47] = scenario.rpm_byte;
        xram[0xF8F9] = scenario.xram_f9;
        cpu.mPC = 0x2E06;
        for (int step = 0; step < 30 && cpu.mPC != 0x2E24; ++step) {
            if (cpu.mPC == 0x2E0B)
                EXPECT_EQ(cpu.mSFR[REG_ACC], 0x46);
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x2E24);
        EXPECT_EQ(upper[0x81 - 0x80], scenario.expected_upper);
        EXPECT_EQ(xram[0xF8FA], scenario.expected_upper ? 0x96 : 0x00);

        // The real 36AFh load is tested; intervening control flow is
        // deliberately skipped because natural reachability is unproven.
        cpu.mPC = 0x36AF;
        for (int step = 0; step < 2; ++step) {
            cpu.mTickDelay = 0;
            EXPECT_TRUE(tick(&cpu)) << "PC=" << std::hex << cpu.mPC
                                   << " PCON=" << int(cpu.mSFR[REG_PCON]);
        }
        ASSERT_EQ(cpu.mPC, 0x36B3);
        ASSERT_EQ(cpu.mSFR[REG_B], scenario.expected_upper);
        xram[0xF8FA] = 0xFF; // Select the direct 36EAh -> 3701h route.
        cpu.mPC = 0x36DE;
        const uint16_t target = scenario.expected_upper ? 0x3701 : 0x3739;
        for (int step = 0; step < 10 && cpu.mPC != target; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        EXPECT_EQ(cpu.mPC, target);
        if (scenario.expected_upper) {
            cpu.mTickDelay = 0;
            tick(&cpu); // ANL B,#D0h
            cpu.mTickDelay = 0;
            tick(&cpu); // ORL B,#05h
            EXPECT_EQ(cpu.mSFR[REG_B] & 0x21, 0x01);
        }
    }
}

TEST(Sab80C517, AlcoholCodeStartupMatrixIndexUsesBcAndUpperAe) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    struct Case { uint8_t bc, ae, expected_row; };
    constexpr std::array cases{Case{0x03, 0x00, 0}, Case{0x15, 0x00, 0},
                               Case{0x03, 0x20, 2}};
    for (const auto &path : paths) {
        for (const auto &test : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x7B28], 0xAE);
            ASSERT_EQ(code[0x7B29], 0x08);
            ASSERT_EQ(code[0x7571], 0x0F);
            upper[0xBC - 0x80] = test.bc;
            upper[0xAE - 0x80] = test.ae;
            cpu.mPC = 0x3329;
            for (int step = 0; step < 300 && cpu.mPC != 0x335D; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x335D) << path;
            EXPECT_EQ(cpu.mLowerData[0], 15);
            EXPECT_EQ(cpu.mLowerData[7], test.bc & 0x0F);
            EXPECT_EQ(cpu.mLowerData[6], test.bc & 0xF0);
            EXPECT_EQ(cpu.mLowerData[3], test.expected_row);
            EXPECT_EQ(cpu.mLowerData[5], test.expected_row * 15 +
                                        (test.bc & 0x0F));
        }
    }
}

TEST(Sab80C517, AlcoholCodeAdc2Lookup7100WritesIram7cWhenEnabled) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    struct Case { uint8_t adc2_ram62, flag_2f, expected_7c; };
    constexpr std::array cases{Case{100, 0x00, 0x7E},
                               Case{40, 0x00, 0x76},
                               Case{100, 0x20, 0x80}};
    for (const auto &path : paths) {
        for (const auto &test : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x46E0], 0x90); // MOV DPTR,#7100h
            ASSERT_EQ(code[0x46E1], 0x71);
            ASSERT_EQ(code[0x46E2], 0x00);
            cpu.mLowerData[0x62] = test.adc2_ram62;
            cpu.mLowerData[0x2F] = test.flag_2f;
            cpu.mPC = 0x46D9;
            for (int step = 0; step < 300 && cpu.mPC != 0x46E8; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x46E8) << path;
            EXPECT_EQ(cpu.mLowerData[0x7C], test.expected_7c)
                << path << " RAM62=" << int(test.adc2_ram62);
        }
    }
}

TEST(Sab80C517, AlcoholCodeAdcScheduleRoutesChannelsTwoAndThree) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    struct Case { uint8_t schedule_index, destination, channel; };
    constexpr std::array cases{Case{8, 0x62, 2}, Case{7, 0x63, 3}};
    for (const auto &path : paths) {
        for (const auto &test : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x6E1], 0x83); // MOVC A,@A+PC
            ASSERT_EQ(code[0x6E2 + test.schedule_index], test.destination);
            cpu.mLowerData[6] = test.schedule_index;
            cpu.mPC = 0x6D0;
            for (int step = 0; step < 30 && cpu.mPC != 0x6F2; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x6F2) << path;
            EXPECT_EQ(cpu.mLowerData[1], test.destination);
            EXPECT_EQ(cpu.mSFR[0xD8 - 0x80] & 7, test.channel);

            // Inject a completed conversion at the firmware read point.
            cpu.mSFR[0xD9 - 0x80] = 99;
            cpu.mPC = 0x716;
            for (int step = 0; step < 30 && cpu.mPC != 0x745; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x745) << path;
            if (test.channel == 2) {
                EXPECT_EQ(cpu.mLowerData[0x62], 100);
                EXPECT_EQ(upper[0xA8 - 0x80], 0);
                ASSERT_EQ(code[0x6E7E], 0x00);
                ASSERT_EQ(code[0x6E7F], 0x62);
                cpu.mSFR[REG_P2] = 0xF8;
                cpu.mSFR[REG_DPH] = 0x6E;
                cpu.mSFR[REG_DPL] = 0x7E;
                cpu.mLowerData[1] = 0xBB;
                cpu.mLowerData[7] = 1;
                cpu.mPC = 0x4F72;
                for (int step = 0; step < 40 && cpu.mPC != 0x4F8A; ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, 0x4F8A) << path;
                EXPECT_EQ(xram[0xF8BB], 100);
            } else {
                EXPECT_EQ(cpu.mLowerData[0x63], 0);
                EXPECT_EQ(upper[0xA8 - 0x80], 100);
            }
        }
    }
}

TEST(Sab80C517, AlcoholCodeUpperA8BoundsBecomeCoolantRam63) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    struct Case { uint8_t adc3, previous, expected_63; };
    constexpr std::array cases{Case{3, 3, 0x11}, Case{4, 4, 4},
                               Case{0xE7, 0xE7, 0xE7}, Case{0xE8, 0xE8, 0x11},
                               Case{0x33, 0x28, 0x33},
                               Case{0x34, 0x28, 0x11},
                               Case{0x35, 0x28, 0x11}};
    for (const auto &path : paths) {
        for (const auto &test : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x46E6], 0x8A); // MOV 7Ch,R2
            ASSERT_EQ(code[0x4813], 0xF5); // MOV 63h,A
            upper[0xA8 - 0x80] = test.adc3;
            upper[0xA9 - 0x80] = test.previous;
            cpu.mSFR[REG_DPH] = 0x72;
            cpu.mSFR[REG_DPL] = 0x00;
            cpu.mPC = 0x46E6;
            for (int step = 0; step < 300 && cpu.mPC != 0x4815; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x4815) << path;
            EXPECT_EQ(cpu.mLowerData[0x63], test.expected_63)
                << path << " raw ADC3=" << int(test.adc3);
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_DPH] = 0x6E;
            cpu.mSFR[REG_DPL] = 0x78;
            cpu.mLowerData[1] = 0xBB;
            cpu.mLowerData[7] = 1;
            cpu.mPC = 0x4F72;
            for (int step = 0; step < 40 && cpu.mPC != 0x4F8A; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x4F8A) << path;
            EXPECT_EQ(xram[0xF8BB], test.expected_63)
                << path << " K-Line slot 0, raw ADC3=" << int(test.adc3);
        }
    }
}

TEST(Sab80C517, CoolantControlConstants7265To7269UseOriginalOpcodes) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array images{
        std::pair{root / "FiatTipo_MA17_dump_27c256.bin", 0u},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256.bin", 0xBDu},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256+1.5bar.bin", 0xBDu},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256 SUN 8817.bin", 0u},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256 SUN 37a5.bin", 0xBDu},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256 SUN 36fd.bin", 0xBDu}};
    struct Case {
        uint16_t start;
        uint8_t r2, r3, ram63, r5, xram_d9;
        std::array<bool, 3> reads_67_68_69;
    };
    const std::array cases{
        Case{0x46E6, 0x22, 0x20, 0x22, 0, 0, {false, true, false}},
        Case{0x46E6, 0x30, 0x20, 0x20, 0x17, 0, {true, true, false}},
        Case{0x46C6, 0x20, 0x40, 0x20, 0, 4, {false, false, true}}};
    for (const auto &[path, shift] : images) {
        for (const auto &scenario : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x7265], 0x31) << path;
            ASSERT_EQ(code[0x7266], 0x1E) << path;
            ASSERT_EQ(code[0x7267], 0x17) << path;
            ASSERT_EQ(code[0x7268], 0x03) << path;
            ASSERT_EQ(code[0x7269], 0x04) << path;
            cpu.mLowerData[2] = scenario.r2;
            cpu.mLowerData[3] = scenario.r3;
            cpu.mSFR[REG_DPH] = 0x72;
            cpu.mSFR[REG_DPL] = 0;
            cpu.mSFR[REG_P2] = 0;
            cpu.mPC = static_cast<uint16_t>(scenario.start + shift);
            std::array<bool, 3> read{};
            for (int step = 0; step < 100 &&
                               cpu.mPC != 0x4758 + shift; ++step) {
                read[0] |= cpu.mPC == 0x4708 + shift;
                read[1] |= cpu.mPC == 0x46FD + shift;
                read[2] |= cpu.mPC == 0x46D7 + shift;
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x4758 + shift) << path;
            EXPECT_EQ(read, scenario.reads_67_68_69) << path;
            EXPECT_EQ(cpu.mLowerData[0x63], scenario.ram63) << path;
            EXPECT_EQ(cpu.mLowerData[5], scenario.r5) << path;
            EXPECT_EQ(xram[0xD9], scenario.xram_d9) << path;
        }
    }
}

TEST(Sab80C517, CoolantCountersD7AndD9DecayUnderOriginalGuards) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array images{
        std::pair{root / "FiatTipo_MA17_dump_27c256.bin", 0u},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256.bin", 0x1Cu},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256+1.5bar.bin", 0x1Cu},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256 SUN 8817.bin", 0u},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256 SUN 37a5.bin", 0x1Cu},
        std::pair{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256 SUN 36fd.bin", 0x1Cu}};
    struct Case {
        uint8_t d7, d9, flags2d, t2con, expected_d7, expected_d9;
    };
    constexpr std::array cases{
        Case{0x1E, 4, 0x10, 0, 0x1D, 3},
        Case{0x1E, 4, 0, 0, 0x1E, 4},
        Case{0, 4, 0x10, 0, 0, 3},
        Case{0x1E, 4, 0x10, 0x02, 0x1E, 4}};
    for (const auto &[path, shift] : images) {
        for (const auto &scenario : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x327A + shift], 0x20) << path; // JB T2CON.1
            ASSERT_EQ(code[0x3285 + shift], 0x14) << path; // DEC A
            xram[0xF8D7] = scenario.d7;
            xram[0xF8D9] = scenario.d9;
            cpu.mLowerData[0x2D] = scenario.flags2d;
            cpu.mSFR[REG_T2CON] = scenario.t2con;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mPC = static_cast<uint16_t>(0x327A + shift);
            for (int step = 0; step < 30 &&
                               cpu.mPC != 0x3291 + shift; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x3291 + shift) << path;
            EXPECT_EQ(xram[0xF8D7], scenario.expected_d7) << path;
            EXPECT_EQ(xram[0xF8D9], scenario.expected_d9) << path;
        }
    }
}

TEST(Sab80C517, FiatCoolantSegmentUsesFourBitResidualFraction) {
    std::array<unsigned char, 32768> code{};
    std::array<unsigned char, 256> xram{};
    std::array<unsigned char, 128> upper{};
    em8051 cpu{};
    cpu.mCodeMem = code.data();
    cpu.mCodeMemMaxIdx = code.size() - 1;
    cpu.mExtData = xram.data();
    cpu.mExtDataMaxIdx = xram.size() - 1;
    cpu.mUpperData = upper.data();
    reset(&cpu, true);
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(code.data()), code.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
    ASSERT_EQ(code[0x7002], 0x73);
    ASSERT_EQ(code[0x7003], 0xD4);
    cpu.mLowerData[0x63] = 0x50;
    cpu.mPC = 0x4773;
    for (int step = 0; step < 200 && cpu.mPC != 0x52A2; ++step) {
        cpu.mTickDelay = 0;
        tick(&cpu);
    }
    ASSERT_EQ(cpu.mPC, 0x52A2);
    EXPECT_EQ(cpu.mLowerData[0], 7); // Residual before the four divide bits.
    EXPECT_EQ(cpu.mLowerData[3], 3); // Segment index.
    EXPECT_EQ(cpu.mSFR[REG_ACC], 4); // D5h+4 selects width D9h=2Ah.
    for (int step = 0; step < 60 && cpu.mPC != 0x477F; ++step) {
        cpu.mTickDelay = 0;
        tick(&cpu);
    }
    ASSERT_EQ(cpu.mPC, 0x477F);
    EXPECT_EQ(cpu.mLowerData[0x4E], 0x23); // floor(16*7/42)=2, index 3.
}

TEST(Sab80C517, FiatPostCoolantAxisCanSwitchToXram91WhenAirAndFlagsPermit) {
    std::array<unsigned char, 32768> code{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(code.data()), code.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
    ASSERT_EQ(code[0x7264], 0x6E); // Air threshold read at 4786h.
    ASSERT_EQ(code[0x47A2], 0xE3); // MOVX A,@R1, with R1=91h.
    for (const bool permit : {false, true}) {
        std::array<unsigned char, 65536> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, false); // Preserve the original ROM loaded above.
        cpu.mSFR[REG_P2] = 0xF8;
        cpu.mSFR[REG_XPAGE] = 0xF8;
        cpu.mLowerData[0x62] = 0x80; // Above ROM[7264h].
        cpu.mLowerData[0x28] = permit ? 0x08 : 0x00;
        cpu.mLowerData[0x29] = 0;
        cpu.mLowerData[5] = 3;       // Prior segment index.
        cpu.mLowerData[6] = 0x20;    // Prior fraction.
        xram[0xF89E] = 1;
        xram[0xF891] = 0xA3;
        cpu.mPC = 0x477F;
        bool read_xram91 = false;
        for (int step = 0; step < 80 && cpu.mPC != 0x47AC; ++step) {
            if (cpu.mPC == 0x479B) {
                EXPECT_EQ(cpu.mSFR[REG_PSW] & 0x80,
                          permit ? 0x80 : 0)
                    << "flags28=" << int(cpu.mLowerData[0x28])
                    << " flags29=" << int(cpu.mLowerData[0x29]);
            }
            read_xram91 |= cpu.mPC == 0x47A2;
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x47AC);
        EXPECT_EQ(read_xram91, permit);
        EXPECT_EQ(cpu.mLowerData[5], permit ? 7 : 3);
        EXPECT_EQ(cpu.mLowerData[6], permit ? 0xA0 : 0x20);
    }
}

TEST(Sab80C517, AlcoholCodeRam63IndexesSegmentTable73d4) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    struct Case { uint8_t ram63, expected_index, expected_fraction; };
    constexpr std::array cases{Case{20, 0, 0}, Case{40, 1, 0xB0},
                               Case{80, 3, 0x20}, Case{160, 5, 0xE0},
                               Case{220, 9, 0}};
    for (const auto &path : paths) {
        for (const auto &test : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x7002], 0x73);
            ASSERT_EQ(code[0x7003], 0xD4);
            ASSERT_EQ(code[0x4830], 0x90); // MOV DPTR,#7002h
            cpu.mLowerData[0x63] = test.ram63;
            cpu.mPC = 0x4830;
            for (int step = 0; step < 300 && cpu.mPC != 0x483C; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x483C) << path;
            EXPECT_EQ(cpu.mLowerData[5], test.expected_index);
            EXPECT_EQ(cpu.mLowerData[6], test.expected_fraction);
            EXPECT_EQ(cpu.mLowerData[0x4E],
                      (test.expected_fraction | test.expected_index))
                << path << " RAM63=" << int(test.ram63);
        }
    }
}

TEST(Sab80C517, AlcoholCodeRam63SegmentClampsIndexNineFraction) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (const auto& path : paths) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        int terminal_count = 0;
        int penultimate_fraction_count = 0;
        for (int raw = 0; raw < 256; ++raw) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mLowerData[0x63] = static_cast<uint8_t>(raw);
            cpu.mPC = 0x4830;
            for (int step = 0; step < 300 && cpu.mPC != 0x483C; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x483C) << path << " RAM63=" << raw;
            const auto index = cpu.mLowerData[5];
            const auto fraction = cpu.mLowerData[6];
            EXPECT_LE(index, 9) << path << " RAM63=" << raw;
            if (index == 9) {
                ++terminal_count;
                EXPECT_EQ(fraction, 0) << path << " RAM63=" << raw;
            }
            if (index == 8 && fraction != 0)
                ++penultimate_fraction_count;
        }
        EXPECT_GT(terminal_count, 0) << path;
        EXPECT_GT(penultimate_fraction_count, 0) << path;
    }
}

TEST(Sab80C517, SixRomRpm7992TerminalSegmentHasZeroFraction) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "FiatTipo_MA17_dump_27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (std::size_t variant = 0; variant < paths.size(); ++variant) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(paths[variant], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[variant];
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        const bool gasoline_code = variant == 0 || variant == 3;
        const uint16_t entry = gasoline_code ? 0x3CA2 : 0x3D5A;
        const uint16_t exit = gasoline_code ? 0x3CAB : 0x3D63;
        ASSERT_EQ(original[entry], 0x90) << paths[variant];
        ASSERT_EQ(original[entry + 1], 0x70) << paths[variant];
        ASSERT_EQ(original[entry + 2], 0x90) << paths[variant];
        int terminal_count = 0;
        int penultimate_fraction_count = 0;
        for (int raw = 0; raw < 256; ++raw) {
            std::array<unsigned char, 32768> code = original;
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mLowerData[0x47] = static_cast<uint8_t>(raw);
            cpu.mPC = entry;
            for (int step = 0; step < 300 && cpu.mPC != exit; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, exit) << paths[variant] << " RAM47=" << raw;
            const auto index = cpu.mLowerData[5];
            const auto fraction = cpu.mLowerData[6];
            EXPECT_LE(index, 9) << paths[variant] << " RAM47=" << raw;
            if (index == 9) {
                ++terminal_count;
                EXPECT_EQ(fraction, 0) << paths[variant] << " RAM47=" << raw;
            }
            if (index == 8 && fraction != 0)
                ++penultimate_fraction_count;
            if (raw == 0xF1) {
                EXPECT_EQ(index, 9) << paths[variant];
                EXPECT_EQ(fraction, 0) << paths[variant];
            }
        }
        EXPECT_GT(terminal_count, 0) << paths[variant];
        EXPECT_GT(penultimate_fraction_count, 0) << paths[variant];
    }
}

TEST(Sab80C517, AlcoholAirSegmentWriterKeepsTerminalXram91FractionZero) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (const auto& path : paths) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        int terminal_count = 0;
        for (int raw = 0; raw < 256; ++raw) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_T2CON] = 0;
            cpu.mLowerData[0x62] = static_cast<uint8_t>(raw);
            cpu.mPC = 0x46B6;
            for (int step = 0; step < 300 && cpu.mPC != 0x46C6; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x46C6) << path << " RAM62=" << raw;
            const auto index = cpu.mLowerData[5];
            const auto fraction = cpu.mLowerData[6];
            EXPECT_EQ(xram[0xF891], (index | fraction)) << path;
            EXPECT_LE(index, 5) << path << " RAM62=" << raw;
            if (index == 5) {
                ++terminal_count;
                EXPECT_EQ(fraction, 0) << path << " RAM62=" << raw;
            }
        }
        EXPECT_GT(terminal_count, 0) << path;
    }
}

TEST(Sab80C517, CoolantRam4fCurvesFollowCalibrationBytesAcrossCodeRevisions) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "FiatTipo_MA17_dump_27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    std::array<std::array<std::array<uint8_t, 2>, 3>, 6> results{};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        const uint16_t shift = (rom == 0 || rom == 3) ? 0 : 0xBD;
        for (size_t trial = 0; trial < 6; ++trial) {
            const size_t curve = trial / 2;
            const size_t state = trial % 2;
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(paths[rom], std::ios::binary);
            ASSERT_TRUE(file.is_open()) << paths[rom];
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            const uint16_t segment_start = 0x4773 + shift;
            const uint16_t segment_end = 0x477F + shift;
            const uint16_t curve_start = 0x47E1 + shift;
            const uint16_t curve_end = 0x4825 + shift;
            ASSERT_EQ(code[curve_start], 0x20) << paths[rom]; // JB 2Fh.0
            ASSERT_EQ(code[curve_end - 2], 0xF5) << paths[rom]; // MOV 4Fh,A
            xram[0x7F] = 0xFF;
            cpu.mSFR[REG_P2] = 0;
            cpu.mLowerData[0x63] = state == 0 ? 0x33 : 0x11;
            cpu.mPC = segment_start;
            for (int step = 0; step < 300 && cpu.mPC != segment_end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, segment_end) << paths[rom];
            EXPECT_EQ(cpu.mLowerData[0x4E], state == 0 ? 0x42 : 0x00);
            cpu.mLowerData[0x2F] = curve == 2 ? 0x01 : 0;
            cpu.mLowerData[0x22] = curve == 1 ? 0x40 : 0;
            cpu.mPC = curve_start;
            for (int step = 0; step < 300 && cpu.mPC != curve_end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, curve_end) << paths[rom];
            results[rom][curve][state] = cpu.mLowerData[0x4F];
        }
    }
    for (size_t curve = 0; curve < 3; ++curve) {
        for (size_t state = 0; state < 2; ++state) {
            EXPECT_EQ(results[0][curve][state], results[3][curve][state]);
            EXPECT_EQ(results[0][curve][state], results[4][curve][state]);
            EXPECT_EQ(results[0][curve][state], results[5][curve][state]);
            EXPECT_EQ(results[1][curve][state], results[2][curve][state]);
            EXPECT_GT(results[1][curve][state], results[0][curve][state]);
        }
    }
    EXPECT_EQ(results[0][0], (std::array<uint8_t, 2>{0x04, 0x00}));
    EXPECT_EQ(results[1][0], (std::array<uint8_t, 2>{0x14, 0x10}));
    EXPECT_EQ(results[0][1], (std::array<uint8_t, 2>{0x05, 0x00}));
    EXPECT_EQ(results[1][1], (std::array<uint8_t, 2>{0x27, 0x22}));
    EXPECT_EQ(results[0][2], (std::array<uint8_t, 2>{0x04, 0x00}));
    EXPECT_EQ(results[1][2], (std::array<uint8_t, 2>{0x26, 0x22}));
}

TEST(Sab80C517, AlcoholCodeSelectsFourMatrixViewsByFlags) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    struct Mode { uint8_t flag_2b, flag_2e; uint16_t slot, start; };
    constexpr std::array modes{
        Mode{0x00, 0x00, 0x7048, 0x7581},
        Mode{0x80, 0x00, 0x704A, 0x7662},
        Mode{0x00, 0x40, 0x704E, 0x7617},
        Mode{0x80, 0x40, 0x7050, 0x76F8}};
    constexpr std::array expected{
        std::array<uint8_t, 4>{0x25, 0x25, 0xAB, 0xAB},
        std::array<uint8_t, 4>{0x39, 0x25, 0xBF, 0xC2}};
    for (size_t image = 0; image < paths.size(); ++image) {
        for (size_t index = 0; index < modes.size(); ++index) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(paths[image], std::ios::binary);
            ASSERT_TRUE(file.is_open()) << paths[image];
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            const auto &mode = modes[index];
            ASSERT_EQ(code[mode.slot], mode.start >> 8);
            ASSERT_EQ(code[mode.slot + 1], mode.start & 0xFF);
            ASSERT_EQ(code[mode.start + 4], expected[image][index]);
            cpu.mLowerData[0x2B] = mode.flag_2b;
            cpu.mLowerData[0x2E] = mode.flag_2e;
            cpu.mSFR[REG_B] = 15; // Row stride from the first axis header.
            cpu.mLowerData[3] = 0; // Row zero.
            cpu.mLowerData[4] = 0; // Zero second-axis fraction.
            cpu.mLowerData[5] = 4; // Column four.
            cpu.mLowerData[6] = 0; // Zero first-axis fraction.
            cpu.mPC = 0x13AB;
            for (int step = 0; step < 300 && cpu.mPC != 0x13CC; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x13CC) << paths[image];
            EXPECT_EQ(cpu.mLowerData[5], 4);
            EXPECT_EQ(cpu.mLowerData[3], expected[image][index]);
        }
    }
}

TEST(Sab80C517, Fiat7939HomologousLookupAndRam5bMultiply) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    constexpr std::array<uint8_t, 5> gasoline{0x13, 0x23, 0x3D, 0x52,
                                               0x1F};
    constexpr std::array<uint8_t, 5> alcohol{0x3B, 0x4B, 0x65, 0x7A,
                                              0x47};
    constexpr std::array<uint8_t, 5> gasoline_half{0x1B, 0x30, 0x47,
                                                    0x38, 0x2B};
    constexpr std::array<uint8_t, 5> alcohol_half{0x43, 0x58, 0x6F,
                                                   0x60, 0x3F};
    struct Image {
        std::filesystem::path path;
        uint16_t writer;
        uint16_t multiply;
        uint8_t first_cell;
    };
    const std::array images{
        Image{root / "FiatTipo_MA17_dump_27c256.bin", 0x3DD6, 0x1863,
              0x13},
        Image{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256.bin", 0x3E93, 0x187F, 0x3B},
        Image{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256+1.5bar.bin", 0x3E93, 0x187F, 0x3B},
        Image{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256 SUN 8817.bin", 0x3DD6, 0x1863,
              0x13},
        Image{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256 SUN 37a5.bin", 0x3E93, 0x187F,
              0x13},
        Image{root / "firmwares_modificados_ma17_tipo" /
                  "tipo 1.6 alcool27c256 SUN 36fd.bin", 0x3E93, 0x187F,
              0x13}};
    for (const auto &image : images) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::ifstream file(image.path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << image.path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const auto original_code = code;
        ASSERT_EQ(code[0x7066], 0x79);
        ASSERT_EQ(code[0x7067], 0x39);
        // SAB80C517 User's Manual, Instruction Set: MOVC uses A+DPTR;
        // MUL AB returns the high byte in B and low byte in A.
        for (size_t index = 0; index < gasoline.size(); ++index) {
            reset(&cpu, true);
            code = original_code;
            const uint8_t expected = image.first_cell == 0x13
                                         ? gasoline[index] : alcohol[index];
            ASSERT_EQ(code[0x7939 + index], expected) << image.path;
            cpu.mLowerData[0] = 4; // Row stride for the 5x4 table.
            cpu.mLowerData[3] = 0;
            cpu.mLowerData[4] = 0;
            cpu.mLowerData[5] = static_cast<uint8_t>(index);
            cpu.mLowerData[6] = 0;
            cpu.mSFR[REG_B] = 4;
            cpu.mPC = image.writer;
            for (int step = 0; step < 300 && cpu.mPC != image.writer + 8;
                 ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, image.writer + 8) << image.path << index;
            EXPECT_EQ(cpu.mLowerData[0x5B], expected) << image.path << index;
            cpu.mPC = image.multiply;
            for (int step = 0; step < 6 && cpu.mPC != image.multiply + 9;
                 ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, image.multiply + 9) << image.path << index;
            EXPECT_EQ(cpu.mLowerData[4], static_cast<uint8_t>(expected << 5))
                << image.path << index;
            EXPECT_EQ(cpu.mLowerData[5], expected >> 3) << image.path << index;
        }
        for (size_t index = 0; index < gasoline_half.size(); ++index) {
            reset(&cpu, true);
            code = original_code;
            const uint8_t expected = image.first_cell == 0x13
                                         ? gasoline_half[index]
                                         : alcohol_half[index];
            cpu.mLowerData[0] = 4;
            cpu.mLowerData[3] = 0;
            cpu.mLowerData[4] = 0;
            cpu.mLowerData[5] = static_cast<uint8_t>(index);
            cpu.mLowerData[6] = 0x80; // Halfway to the following cell.
            cpu.mSFR[REG_B] = 4;
            cpu.mPC = image.writer;
            for (int step = 0; step < 300 && cpu.mPC != image.writer + 8;
                 ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, image.writer + 8) << image.path << index;
            EXPECT_EQ(cpu.mLowerData[0x5B], expected) << image.path << index;
            EXPECT_EQ(cpu.mLowerData[2],
                      expected + (index == 2 || index == 3 ? 1 : 0))
                << image.path << index;
            cpu.mPC = image.multiply;
            for (int step = 0; step < 6 && cpu.mPC != image.multiply + 9;
                 ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, image.multiply + 9) << image.path << index;
            EXPECT_EQ(cpu.mLowerData[4], static_cast<uint8_t>(expected << 5))
                << image.path << index;
            EXPECT_EQ(cpu.mLowerData[5], expected >> 3) << image.path << index;
        }
        reset(&cpu, true);
        code = original_code;
        const bool alcohol_image = image.first_cell == 0x3B;
        cpu.mLowerData[0] = 4;
        cpu.mLowerData[3] = 0;
        cpu.mLowerData[4] = 0x80; // Second-axis half fraction.
        cpu.mLowerData[5] = 0;
        cpu.mLowerData[6] = 0x40; // First-axis quarter fraction.
        cpu.mSFR[REG_B] = 4;
        cpu.mPC = image.writer;
        for (int step = 0; step < 300 && cpu.mPC != image.writer + 8;
             ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, image.writer + 8) << image.path;
        EXPECT_EQ(cpu.mLowerData[2], alcohol_image ? 0x3F : 0x17)
            << image.path;
        EXPECT_EQ(cpu.mLowerData[3], alcohol_image ? 0x43 : 0x25)
            << image.path;
        EXPECT_EQ(cpu.mLowerData[0x5B], alcohol_image ? 0x41 : 0x1E)
            << image.path;
        cpu.mPC = image.multiply;
        for (int step = 0; step < 6 && cpu.mPC != image.multiply + 9;
             ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, image.multiply + 9) << image.path;
        EXPECT_EQ(cpu.mLowerData[4], alcohol_image ? 0x20 : 0xC0)
            << image.path;
        EXPECT_EQ(cpu.mLowerData[5], alcohol_image ? 0x08 : 0x03)
            << image.path;
    }
}

TEST(Sab80C517, MatrixConditionalThreshold7294IndexZeroDiffersByRevision) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    struct Image { std::filesystem::path path; uint16_t shift; uint8_t first; };
    const std::array images{
        Image{root / "FiatTipo_MA17_dump_27c256.bin", 0, 0xBC},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256.bin", 0x4E, 0x38},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256+1.5bar.bin", 0x4E, 0x38},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256 SUN 8817.bin", 0, 0xBC},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256 SUN 37a5.bin", 0x4E, 0x38},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256 SUN 36fd.bin", 0x4E, 0x38}};
    for (const auto &image : images) {
        for (const uint8_t index : {uint8_t{0}, uint8_t{4}}) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            reset(&cpu, true);
            std::ifstream file(image.path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << image.path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            const uint8_t expected = index == 0 ? image.first : 0xAF;
            ASSERT_EQ(code[0x7294 + index], expected) << image.path;
            cpu.mLowerData[2] = 0xC0; // Fractional byte of the matrix result.
            cpu.mLowerData[3] = 0x20; // Below both tested thresholds.
            cpu.mLowerData[5] = index;
            cpu.mSFR[REG_DPH] = 0x72;
            cpu.mSFR[REG_DPL] = 0;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mPC = static_cast<uint16_t>(0x145E + image.shift);
            for (int step = 0; step < 30 &&
                               cpu.mPC != 0x1485 + image.shift; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x1485 + image.shift) << image.path;
            EXPECT_EQ(cpu.mLowerData[2], 0) << image.path;
            EXPECT_EQ(cpu.mLowerData[3], expected) << image.path;
            cpu.mLowerData[2] = 0xC0;
            cpu.mLowerData[3] = expected; // Equality still drops the fraction.
            cpu.mLowerData[5] = index;
            cpu.mPC = static_cast<uint16_t>(0x145E + image.shift);
            for (int step = 0; step < 30 &&
                               cpu.mPC != 0x1485 + image.shift; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x1485 + image.shift) << image.path;
            EXPECT_EQ(cpu.mLowerData[2], 0) << image.path;
            EXPECT_EQ(cpu.mLowerData[3], expected) << image.path;
        }
    }
}

TEST(Sab80C517, SerialHandshakeRomBytes7292To7294ReachSbufInSixRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    struct Image {
        std::filesystem::path path;
        uint16_t shift;
        std::array<uint8_t, 3> serial_tail;
    };
    const std::array images{
        Image{root / "FiatTipo_MA17_dump_27c256.bin", 0,
              {0x89, 0x13, 0xBC}},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256.bin", 0xC3, {0x04, 0x94, 0x38}},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256+1.5bar.bin", 0xC3, {0x04, 0x94, 0x38}},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256 SUN 8817.bin", 0,
              {0x89, 0x13, 0xBC}},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256 SUN 37a5.bin", 0xC3,
              {0x04, 0x94, 0x38}},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256 SUN 36fd.bin", 0xC3,
              {0x04, 0x94, 0x38}}};
    for (const auto &image : images) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(image.path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << image.path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        for (std::size_t index = 0; index < image.serial_tail.size(); ++index)
            EXPECT_EQ(code[0x7292 + index], image.serial_tail[index])
                << image.path;
        const auto original_code = code;
        for (const uint8_t state : {uint8_t{2}, uint8_t{3}, uint8_t{4}}) {
            std::array<unsigned char, 65536> xram{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            reset(&cpu, true);
            std::copy(original_code.begin(), original_code.end(), code.begin());
            cpu.mLowerData[0] = 0x31; // R0 destination in state 4.
            cpu.mLowerData[1] = 0x30; // R1 points to serial state.
            cpu.mLowerData[0x30] = state;
            cpu.mPC = static_cast<uint16_t>(0x4CA0 + image.shift);
            const uint16_t store = static_cast<uint16_t>(0x4D0B + image.shift);
            for (int step = 0; step < 25 && cpu.mPC != store; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, store) << image.path << " state=" << +state;
            cpu.mTickDelay = 0;
            tick(&cpu); // MOV 45h,A stages the selected ROM byte.
            ASSERT_EQ(cpu.mLowerData[0x45], image.serial_tail[state - 2])
                << image.path << " state=" << +state;
            cpu.mPC = static_cast<uint16_t>(0x4C78 + image.shift);
            cpu.mTickDelay = 0;
            tick(&cpu); // MOV S0BUF,45h is shared by both code families.
            EXPECT_EQ(cpu.mSFR[REG_SBUF], image.serial_tail[state - 2])
                << image.path << " state=" << +state;
        }
    }
}

TEST(Sab80C517, MatrixStateCanPreserveThresholdIndexZeroInSixRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    struct Image { std::filesystem::path path; uint16_t shift; uint8_t first; };
    const std::array images{
        Image{root / "FiatTipo_MA17_dump_27c256.bin", 0, 0xBC},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256.bin", 0x4E, 0x38},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256+1.5bar.bin", 0x4E, 0x38},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256 SUN 8817.bin", 0, 0xBC},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256 SUN 37a5.bin", 0x4E, 0x38},
        Image{root / "firmwares_modificados_ma17_tipo" /
              "tipo 1.6 alcool27c256 SUN 36fd.bin", 0x4E, 0x38}};
    std::array<unsigned char, 32768> gasoline{};
    std::ifstream baseline(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(baseline.is_open());
    baseline.read(reinterpret_cast<char *>(gasoline.data()), gasoline.size());
    ASSERT_EQ(baseline.gcount(), static_cast<std::streamsize>(gasoline.size()));
    std::array<unsigned char, 32768> original{};
    std::array<unsigned char, 32768> code{};
    std::array<unsigned char, 256> xram{};

    struct Case { uint8_t state; uint8_t expected_index; };
    constexpr std::array cases{Case{5, 0}, Case{4, 4}};
    for (const auto &image : images) {
        std::ifstream file(image.path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << image.path;
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        ASSERT_TRUE(std::equal(gasoline.begin() + 0x1412, gasoline.begin() + 0x1462,
                               original.begin() + 0x1412 + image.shift)) << image.path;
        for (const auto &scenario : cases) {
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mSFR[REG_DPH] = 0x72;
            cpu.mSFR[REG_DPL] = 0;
            cpu.mLowerData[0x2C] = 0x00; // Clear the transition guard.
            cpu.mLowerData[0x27] = 0x80; // Positive transition from 19A6h.
            cpu.mLowerData[4] = scenario.state;
            cpu.mLowerData[5] = 0;
            cpu.mPC = static_cast<uint16_t>(0x1412 + image.shift);
            for (int step = 0; step < 120 && cpu.mPC != 0x1462 + image.shift; ++step)
                tick(&cpu);
            ASSERT_EQ(cpu.mPC, 0x1462 + image.shift) << image.path;
            EXPECT_EQ(cpu.mLowerData[5], scenario.expected_index);
            EXPECT_EQ(cpu.mSFR[REG_ACC], scenario.expected_index ? 0xAF : image.first)
                << image.path;
            EXPECT_EQ(cpu.mLowerData[0x23] & 0x08, scenario.state == 5 ? 0x08 : 0);
        }
    }
}

TEST(Sab80C517, MatrixStateDirectionSetsRam27FlagsInSixRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "FiatTipo_MA17_dump_27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    struct Case { uint8_t psw, r7, initial, expected; };
    constexpr std::array cases{
        Case{0x00, 0x20, 0xC0, 0x00},
        Case{0x02, 0x20, 0x00, 0x80},
        Case{0x02, 0xE0, 0x00, 0x40}};
    for (const auto &path : paths) {
        const uint16_t shift = path.filename() == "FiatTipo_MA17_dump_27c256.bin" ||
                               path.filename() == "tipo 1.6 alcool27c256 SUN 8817.bin"
                                   ? 0 : 0x1C;
        for (const auto &scenario : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            cpu.mSFR[REG_PSW] = scenario.psw;
            cpu.mLowerData[7] = scenario.r7;
            cpu.mLowerData[0x27] = scenario.initial;
            cpu.mPC = static_cast<uint16_t>(0x199E + shift);
            for (int step = 0; step < 12 &&
                               cpu.mPC != 0x19B6 + shift; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x19B6 + shift) << path;
            EXPECT_EQ(cpu.mLowerData[0x27] & 0xC0, scenario.expected) << path;
        }
    }
}

TEST(Sab80C517, AlcoholCodeMatrixFlagUsesRpmBoundAt72e9) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    struct Case { uint8_t ram47, expected_flag, expected_state; };
    constexpr std::array cases{Case{0x9F, 0x80, 4},
                               Case{0xA0, 0x80, 4},
                               Case{0xA1, 0x00, 0x15}};
    for (const auto &path : paths) {
        for (const auto &test : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x72E9], 0xA0);
            xram[0xF985] = 4; // State read earlier at 3C7Dh.
            cpu.mSFR[REG_P2] = 0xF9;
            cpu.mSFR[REG_DPH] = 0x72;
            cpu.mSFR[REG_DPL] = 0;
            cpu.mSFR[REG_ACC] = 4;
            cpu.mLowerData[0] = 0x85;
            cpu.mLowerData[0x47] = test.ram47;
            cpu.mPC = 0x3CE8;
            for (int step = 0; step < 30 && cpu.mPC != 0x3D04; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x3D04) << path;
            EXPECT_EQ(cpu.mLowerData[0x2B] & 0x80, test.expected_flag);
            EXPECT_EQ(xram[0xF985], test.expected_state);
        }
    }
}

TEST(Sab80C517, AlcoholCodeMatrixStateTransitionsUseCountersAndRpmWindow) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    struct Case {
        uint8_t prior_state, prior_count, ram47, expected_state,
            expected_count, expected_flag, flag_2f;
    };
    constexpr std::array cases{
        Case{1, 0x0E, 0x55, 2, 0x0F, 0x00, 1},
        Case{2, 0x31, 0x58, 3, 0x32, 0x00, 0},
        Case{2, 0x31, 0x59, 0x12, 0x32, 0x00, 0},
        Case{3, 0x40, 0x52, 0x13, 0x41, 0x00, 0},
        Case{3, 0x40, 0x53, 4, 0x41, 0x80, 0},
        Case{3, 0x40, 0x5E, 4, 0x41, 0x80, 0},
        Case{3, 0x40, 0x5F, 0x13, 0x41, 0x00, 0}};
    for (const auto &path : paths) {
        for (const auto &test : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x72E3], 0x0F);
            ASSERT_EQ(code[0x72E4], 0x32);
            ASSERT_EQ(code[0x72E5], 0x41);
            ASSERT_EQ(code[0x72E6], 0x58);
            ASSERT_EQ(code[0x72E7], 0x52);
            ASSERT_EQ(code[0x72E8], 0x5E);
            xram[0xF984] = test.prior_count;
            xram[0xF985] = test.prior_state;
            cpu.mSFR[REG_P2] = 0xF9;
            cpu.mSFR[REG_DPH] = 0x72;
            cpu.mSFR[REG_DPL] = 0;
            cpu.mLowerData[0x47] = test.ram47;
            cpu.mLowerData[0x2F] = test.flag_2f;
            cpu.mPC = 0x3C7D;
            for (int step = 0; step < 80 && cpu.mPC != 0x3D04; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x3D04) << path;
            EXPECT_EQ(xram[0xF984], test.expected_count);
            EXPECT_EQ(xram[0xF985], test.expected_state);
            EXPECT_EQ(cpu.mLowerData[0x2B] & 0x80, test.expected_flag);
        }
    }
}

TEST(Sab80C517, AlcoholStateWindowFeedsUpperAeMatrixSelector) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    for (const auto &path : paths) {
        for (const uint8_t rpm_byte : {uint8_t{0x55}, uint8_t{0x5F}}) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            xram[0xF984] = 0x40; // State 3 counter reaches 72E5h=41h.
            xram[0xF985] = 3;
            cpu.mSFR[REG_P2] = 0xF9;
            cpu.mSFR[REG_DPH] = 0x72;
            cpu.mSFR[REG_DPL] = 0;
            cpu.mLowerData[0x47] = rpm_byte;
            cpu.mPC = 0x3C7D;
            for (int step = 0; step < 80 && cpu.mPC != 0x3D04; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x3D04) << path;
            const bool in_window = rpm_byte == 0x55;
            EXPECT_EQ((cpu.mLowerData[0x2B] & 0x80) != 0, in_window)
                << path;
            EXPECT_EQ(xram[0xF985], in_window ? 4 : 0x13) << path;

            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_PSW] = 0;
            cpu.mLowerData[0] = 15; // Matrix row stride.
            cpu.mLowerData[4] = 0;
            cpu.mLowerData[5] = 4;
            cpu.mLowerData[6] = 0;
            cpu.mLowerData[0x57] = 0;
            cpu.mLowerData[0x2F] |= 0x04; // Existing 2Fh.2 matrix branch.
            cpu.mPC = 0x3369;
            const uint16_t matrix = in_window ? 0x7D26 : 0x7CAE;
            bool reached_movc = false;
            for (int step = 0; step < 100 && cpu.mPC != 0x3381; ++step) {
                if (cpu.mPC == 0x53F2) {
                    reached_movc = true;
                    EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                       cpu.mSFR[REG_DPL]), matrix) << path;
                }
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_TRUE(reached_movc) << path;
            ASSERT_EQ(cpu.mPC, 0x3381) << path;
            EXPECT_EQ(cpu.mLowerData[2], code[matrix + 4]) << path;
        }
    }
}

TEST(Sab80C517, AlcoholRpmBoundMovcFeedsRelocatedComparisons) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path() /
                      "firmwares_modificados_ma17_tipo";
    const std::array paths{
        root / "tipo 1.6 alcool27c256.bin",
        root / "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (const auto &path : paths) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        cpu.mSFR[REG_DPH] = 0x73;
        cpu.mSFR[REG_DPL] = 0;
        cpu.mPC = 0x2C65;
        for (int step = 0; step < 3; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x2C69) << path;
        ASSERT_EQ(cpu.mLowerData[2], code[0x7310]) << path;
        ASSERT_EQ(cpu.mLowerData[2], 0x38) << path;

        for (const uint16_t comparison : {uint16_t{0x2C98},
                                          uint16_t{0x2D20}}) {
            for (const uint8_t rpm_byte : {uint8_t{0x38}, uint8_t{0x39}}) {
                cpu.mLowerData[0x47] = rpm_byte;
                cpu.mPC = comparison;
                const uint16_t end = comparison == 0x2C98 ? 0x2C9C : 0x2D24;
                for (int step = 0; step < 3 && cpu.mPC != end; ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, end) << path;
                EXPECT_EQ((cpu.mSFR[REG_PSW] & 0x80) != 0,
                          rpm_byte == 0x39) << path;
            }
        }
    }
}

TEST(Sab80C517, FirmwareP4StatusBitsReachXramF8e2InSixRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    struct Case { uint8_t p4, flags2e, flags2a, flags22, expected; };
    constexpr std::array cases{
        Case{0, 0, 0, 0, 0}, Case{0x08, 0, 0, 0, 0x04},
        Case{0x40, 0, 0, 0, 0x01}, Case{0x48, 0, 0, 0, 0x05},
        Case{0xEA, 0x80, 0x02, 0x10, 0x7F}};
    for (const auto &path : paths) {
        const bool a_family = path != MA17_ROM_PATH &&
                              path.filename().string().find("SUN 8817") ==
                                  std::string::npos;
        const uint16_t start = a_family ? 0x4A70 : 0x49AD;
        for (const auto &test : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[0xE8 - 0x80] = test.p4;
            cpu.mSFR[REG_ACC] = 0xA5;
            cpu.mLowerData[0x2E] = test.flags2e;
            cpu.mLowerData[0x2A] = test.flags2a;
            cpu.mLowerData[0x22] = test.flags22;
            cpu.mPC = start;
            for (int step = 0; step < 24 && cpu.mPC != start + 28; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, start + 28) << path;
            EXPECT_EQ(cpu.mLowerData[0x4D], 0xA5) << path;
            EXPECT_EQ(xram[0xF8E2], test.expected) << path;
        }
    }
}

TEST(Sab80C517, FirmwareP43IndexGateRequiresHighRom7375Bit) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    struct Case { uint8_t mode, p4, expected_b, expected_r7; };
    constexpr std::array cases{
        Case{0, 0x80, 0x09, 5}, Case{0, 0x88, 0x09, 5},
        Case{1, 0x80, 0x03, 5}, Case{1, 0x88, 0x03, 5},
        Case{2, 0x80, 0x05, 5}, Case{2, 0x88, 0x05, 5},
        Case{15, 0x80, 0xC2, 4}, Case{15, 0x88, 0xC2, 5}};
    for (const auto &path : paths) {
        const bool a_family = path != MA17_ROM_PATH &&
                              path.filename().string().find("SUN 8817") ==
                                  std::string::npos;
        const uint16_t start = a_family ? 0x2357 : 0x233B;
        for (const auto &test : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x7042], 0x75) << path;
            ASSERT_EQ(code[0x7043], 0x5C) << path;
            cpu.mSFR[REG_DPH] = 0x73;
            cpu.mSFR[REG_DPL] = 0;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[0xE8 - 0x80] = test.p4;
            cpu.mLowerData[0x22] = 0x10; // 22h.4 contributes three.
            cpu.mLowerData[0x57] = test.mode;
            cpu.mPC = start;
            for (int step = 0; step < 50 && cpu.mPC != start + 62; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, start + 62) << path;
            EXPECT_EQ(cpu.mSFR[REG_B], test.expected_b) << path;
            EXPECT_EQ(cpu.mLowerData[7], test.expected_r7) << path;

            const uint16_t selector = a_family ? 0x4A49 : 0x4986;
            const uint16_t selector_end = a_family ? 0x4A5A : 0x4997;
            cpu.mSFR[REG_DPH] = 0x73;
            cpu.mSFR[REG_DPL] = 0;
            cpu.mPC = selector;
            for (int step = 0; step < 10 && cpu.mPC != selector_end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, selector_end) << path;
            const uint16_t directory = test.mode == 15 &&
                (test.p4 & 0x08) == 0 ? 0x7024 : 0x702A;
            EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                               cpu.mSFR[REG_DPL]), directory) << path;

            upper[0x1E] = 0xB0; // MOV B,@R1 reads upper IRAM 9Eh.
            cpu.mLowerData[0] = 0x10; // MOVX @R0 reads zero at F8:10h.
            const uint16_t flag_reader = a_family ? 0x2121 : 0x2105;
            const uint16_t reader_end = a_family ? 0x2139 : 0x211D;
            cpu.mPC = flag_reader;
            for (int step = 0; step < 14 && cpu.mPC != reader_end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, reader_end) << path;
            EXPECT_EQ(cpu.mSFR[REG_B], test.mode == 2 ? 0xB0 : 0xA0)
                << path;
            const uint16_t writer_end = a_family ? 0x2165 : 0x2149;
            for (int step = 0; step < 20 && cpu.mPC != writer_end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, writer_end) << path;
            EXPECT_EQ(upper[0x1E], test.mode == 2 ? 0x9C : 0x8C)
                << path;

            for (const uint8_t ram63 : {uint8_t{0x26}, uint8_t{0x27}}) {
                cpu.mLowerData[0x63] = ram63; // ROM720Dh=26h.
                cpu.mLowerData[4] = 0; // First cell of the selected curve.
                cpu.mPC = a_family ? 0x1A2E : 0x1A12;
                const uint16_t curve_movc = a_family ? 0x1A54 : 0x1A38;
                for (int step = 0; step < 100 && cpu.mPC != curve_movc;
                     ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, curve_movc) << path;
                const uint16_t curve = test.mode == 2 && ram63 == 0x26
                    ? 0x7A50 : 0x79F0;
                EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                   cpu.mSFR[REG_DPL]), curve) << path;
                cpu.mTickDelay = 0;
                tick(&cpu);
                EXPECT_EQ(cpu.mSFR[REG_ACC], code[curve]) << path;
                cpu.mTickDelay = 0;
                tick(&cpu);
                EXPECT_EQ(cpu.mLowerData[1], code[curve]) << path;
            }
        }
    }
}

TEST(Sab80C517, FirmwareF8efProducerModeFlagAndC9ConsumerLinkInSixRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (const auto &path : paths) {
        const bool a_family = path != MA17_ROM_PATH &&
                              path.filename().string().find("SUN 8817") ==
                                  std::string::npos;
        const uint16_t start = a_family ? 0x3635 : 0x3607;
        const uint16_t end = a_family ? 0x36C8 : 0x369A;
        for (const uint8_t mode : {uint8_t{0}, uint8_t{1}, uint8_t{2}}) {
            for (const uint8_t f8ef : {uint8_t{0}, uint8_t{1}}) {
                std::array<unsigned char, 32768> code{};
                std::array<unsigned char, 65536> xram{};
                std::array<unsigned char, 128> upper{};
                em8051 cpu{};
                cpu.mCodeMem = code.data();
                cpu.mCodeMemMaxIdx = code.size() - 1;
                cpu.mExtData = xram.data();
                cpu.mExtDataMaxIdx = xram.size() - 1;
                cpu.mUpperData = upper.data();
                reset(&cpu, true);
                std::ifstream file(path, std::ios::binary);
                ASSERT_TRUE(file.is_open()) << path;
                file.read(reinterpret_cast<char *>(code.data()), code.size());
                ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
                ASSERT_EQ(code[0x7375], 0x09) << path;
                ASSERT_EQ(code[0x7376], 0x03) << path;
                ASSERT_EQ(code[0x7377], 0x05) << path;
                ASSERT_EQ(code[0x72CC], 0x3C) << path;
                ASSERT_EQ(code[0x72D0], 0x47) << path;
                cpu.mSFR[REG_P2] = 0xF8;
                cpu.mLowerData[0x2F] = 0x01;
                cpu.mLowerData[0x2D] = 0x80;
                cpu.mLowerData[0x6F] = f8ef ? 0x60 : 0x20;
                xram[0xF831] = f8ef ? 0x20 : 0x60;
                cpu.mPC = a_family ? 0x2DA1 : 0x2D85;
                const uint16_t producer_end = a_family ? 0x2E5C : 0x2E40;
                for (int step = 0; step < 30 && cpu.mPC != producer_end;
                     ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, producer_end) << path;
                EXPECT_EQ(xram[0xF8EF], f8ef ? 0x40 : 0) << path;
                EXPECT_EQ(xram[0xF8F5], f8ef ? 0x60 : 0x20) << path;
                cpu.mSFR[REG_P2] = 0xF9;
                cpu.mLowerData[0x57] = mode;
                xram[0xF987] = 4;
                cpu.mPC = start;
                for (int step = 0; step < 90 && cpu.mPC != end; ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, end) << path << " mode=" << int(mode)
                                         << " F8EF=" << int(f8ef);
                // 47h * 4 overflows MUL AB, then clamps against 3Ch.
                const uint8_t expected = mode == 0 && f8ef ? 0x3C : 0;
                EXPECT_EQ(upper[0x49], expected)
                    << path << " mode=" << int(mode) << " F8EF=" << int(f8ef);
                cpu.mLowerData[2] = 0x10;
                cpu.mLowerData[7] = 0x7F;
                cpu.mSFR[REG_B] = 0;
                cpu.mPC = a_family ? 0x39E0 : 0x39B2;
                const uint16_t consumer_end = a_family ? 0x3A22 : 0x39F4;
                for (int step = 0; step < 30 && cpu.mPC != consumer_end;
                     ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, consumer_end) << path;
                EXPECT_EQ(cpu.mSFR[REG_ACC], 0x10 + expected) << path;
                cpu.mTickDelay = 0;
                tick(&cpu);
                EXPECT_EQ(cpu.mLowerData[2], 0x10 + expected) << path;
            }
        }
    }
}

TEST(Sab80C517, AlcoholCodeCoolantWindowsEnterMatrixStateOne) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    struct Case { uint8_t ram63, flag_28, expected_state; };
    constexpr std::array cases{
        Case{0x0D, 0, 0x10}, Case{0x0E, 0, 1},
        Case{0x13, 0, 1}, Case{0x14, 0, 0x10},
        Case{0x5C, 0, 0x10}, Case{0x5D, 0, 1},
        Case{0x78, 0, 1}, Case{0x79, 0, 0x10},
        Case{0x0E, 0x08, 0x20}};
    for (const auto &path : paths) {
        for (const auto &test : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x72DF], 0x78);
            ASSERT_EQ(code[0x72E0], 0x5C);
            ASSERT_EQ(code[0x72E1], 0x13);
            ASSERT_EQ(code[0x72E2], 0x0D);
            cpu.mLowerData[0x63] = test.ram63;
            cpu.mLowerData[0x28] = test.flag_28;
            cpu.mPC = 0x1339;
            for (int step = 0; step < 80 && cpu.mPC != 0x1378; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x1378) << path;
            EXPECT_EQ(xram[0xF985], test.expected_state)
                << path << " IRAM63=" << int(test.ram63);
        }
    }
}

TEST(Sab80C517, AlcoholCodeAdc3StateLadderSelectsDifferentMatrixCell) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    constexpr std::array<uint8_t, 2> expected_axis{0x10, 0x24};
    constexpr std::array<uint8_t, 2> expected_index{36, 38};
    constexpr std::array<uint8_t, 2> expected_fraction{0xD0, 0x10};
    constexpr std::array<uint8_t, 2> expected_result{0x1C, 0x31};
    std::array<std::array<std::array<uint8_t, 256>, 3>, 2> responses{};
    for (size_t image = 0; image < paths.size(); ++image) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::ifstream file(paths[image], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[image];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        ASSERT_EQ(code[0x7580], expected_axis[image]);
        ASSERT_EQ(uint16_t(code[0x7046] << 8 | code[0x7047]), 0x7570);
        ASSERT_EQ(code[0x7570], 0x47);
        ASSERT_EQ(code[0x7571], 15);
        const auto run_until = [&](uint16_t target, int max_steps) {
            for (int step = 0; step < max_steps && cpu.mPC != target; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            return cpu.mPC == target;
        };

        upper[0xA8 - 0x80] = 0x60;
        upper[0xA9 - 0x80] = 0x60;
        cpu.mSFR[REG_DPH] = 0x72;
        cpu.mSFR[REG_DPL] = 0;
        cpu.mPC = 0x46E6;
        ASSERT_TRUE(run_until(0x4815, 300)) << paths[image];
        ASSERT_EQ(cpu.mLowerData[0x63], 0x60);

        cpu.mPC = 0x1339;
        ASSERT_TRUE(run_until(0x1378, 80)) << paths[image];
        ASSERT_EQ(xram[0xF985], 1);

        cpu.mLowerData[0x47] = 0x55;
        cpu.mLowerData[0x2F] = 1;
        constexpr std::array<uint8_t, 3> prior_counts{0x0E, 0x31, 0x40};
        for (size_t stage = 0; stage < prior_counts.size(); ++stage) {
            xram[0xF984] = prior_counts[stage];
            cpu.mPC = 0x3C7D;
            ASSERT_TRUE(run_until(0x3D04, 80)) << paths[image];
            ASSERT_EQ(xram[0xF985], stage + 2) << paths[image];
        }
        ASSERT_EQ(cpu.mLowerData[0x2B] & 0x80, 0x80);

        cpu.mLowerData[0x6F] = 0x14;
        cpu.mPC = 0x1378;
        ASSERT_TRUE(run_until(0x13C6, 1000)) << paths[image] << " PC=" << cpu.mPC;
        EXPECT_EQ(upper[0xBC - 0x80] & 0x0F,
                  image == 0 ? 6 : 8) << paths[image];
        EXPECT_EQ(cpu.mLowerData[5], expected_index[image]);
        EXPECT_EQ(cpu.mLowerData[4], 0x10);
        EXPECT_EQ(cpu.mLowerData[6], expected_fraction[image]);
        EXPECT_EQ(cpu.mLowerData[0], 15);
        EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 | cpu.mSFR[REG_DPL]),
                  0x704A);
        ASSERT_TRUE(run_until(0x13CC, 1000)) << paths[image] << " PC=" << cpu.mPC;
        EXPECT_EQ(cpu.mLowerData[3], expected_result[image]);

        // Reuse the flag produced by the original state ladder, then enter
        // the separate A-code reader with its upstream guard prepared.
        ASSERT_EQ(cpu.mLowerData[0x2B] & 0x80, 0x80);
        cpu.mSFR[REG_PSW] = 0;
        cpu.mSFR[REG_T2CON] &= static_cast<uint8_t>(~0x02);
        cpu.mLowerData[0x22] |= 0x02;
        cpu.mLowerData[7] = 4;
        cpu.mLowerData[6] = 0;
        cpu.mPC = 0x3384;
        bool reached_curve = false;
        for (int step = 0; step < 100 && cpu.mPC != 0x33D3; ++step) {
            if (cpu.mPC == 0x53F2) {
                reached_curve = true;
                EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                   cpu.mSFR[REG_DPL]), 0x7EAC);
                EXPECT_EQ(cpu.mSFR[REG_ACC], 4);
            }
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_TRUE(reached_curve) << paths[image];
        ASSERT_EQ(cpu.mPC, 0x33D3) << paths[image];
        EXPECT_EQ(cpu.mLowerData[2], 0x99);
        EXPECT_EQ(upper[0xA4 - 0x80], 0x99);

        std::array<int, 15> segment_starts{};
        for (size_t segment = 1; segment < segment_starts.size(); ++segment) {
            int remaining = 0;
            for (size_t cell = segment; cell < segment_starts.size(); ++cell)
                remaining += code[0x7572 + cell];
            segment_starts[segment] = 256 - remaining;
        }
        for (int raw = 0; raw < 256; ++raw) {
            cpu.mLowerData[0x47] = static_cast<uint8_t>(raw);
            cpu.mPC = 0x1386;
            ASSERT_TRUE(run_until(0x139E, 300))
                << paths[image] << " RAM47=" << raw;
            size_t expected_column = 0;
            for (size_t segment = 1; segment < segment_starts.size(); ++segment)
                if (raw >= segment_starts[segment])
                    expected_column = segment;
            EXPECT_EQ(upper[0xBC - 0x80] & 0x0F, expected_column)
                << paths[image] << " RAM47=" << raw;
            for (int flag = 0; flag < 2; ++flag) {
                cpu.mSFR[REG_PSW] = 0;
                cpu.mSFR[REG_T2CON] &= static_cast<uint8_t>(~0x02);
                cpu.mLowerData[0x22] = 0x02;
                cpu.mLowerData[0x2B] = flag ? 0x80 : 0;
                cpu.mLowerData[0x57] = 0;
                cpu.mPC = 0x3329;
                ASSERT_TRUE(run_until(0x3333, 20)) << paths[image];
                cpu.mPC = 0x3384;
                ASSERT_TRUE(run_until(0x33D3, 100)) << paths[image];
                responses[image][static_cast<size_t>(flag)]
                         [static_cast<size_t>(raw)] = cpu.mLowerData[2];
            }
            cpu.mSFR[REG_PSW] = 0;
            cpu.mSFR[REG_T2CON] &= static_cast<uint8_t>(~0x02);
            cpu.mLowerData[0x22] = 0x02;
            cpu.mLowerData[0x2B] = 0;
            cpu.mLowerData[0x57] = 2;
            cpu.mPC = 0x3329;
            ASSERT_TRUE(run_until(0x3333, 20)) << paths[image];
            cpu.mPC = 0x3384;
            ASSERT_TRUE(run_until(0x33D3, 100)) << paths[image];
            responses[image][2][static_cast<size_t>(raw)] = cpu.mLowerData[2];
        }
        int first_bank_difference = -1;
        for (int raw = segment_starts[3]; raw <= segment_starts[4]; ++raw) {
            cpu.mLowerData[0x47] = static_cast<uint8_t>(raw);
            cpu.mPC = 0x1386;
            ASSERT_TRUE(run_until(0x139E, 300)) << paths[image];
            std::array<uint8_t, 2> result{};
            for (size_t flag = 0; flag < result.size(); ++flag) {
                cpu.mSFR[REG_PSW] = 0;
                cpu.mSFR[REG_T2CON] &= static_cast<uint8_t>(~0x02);
                cpu.mLowerData[0x22] = 0x02;
                cpu.mLowerData[0x2B] = flag == 0 ? 0 : 0x80;
                cpu.mLowerData[0x57] = 0;
                cpu.mPC = 0x3329;
                ASSERT_TRUE(run_until(0x3333, 20)) << paths[image];
                cpu.mPC = 0x3384;
                ASSERT_TRUE(run_until(0x33D3, 100)) << paths[image];
                result[flag] = cpu.mLowerData[2];
            }
            if (result[0] != result[1] && first_bank_difference < 0)
                first_bank_difference = raw;
            if (raw == segment_starts[3])
                EXPECT_EQ(result[0], result[1]) << paths[image];
            if (raw == segment_starts[3] + 1)
                EXPECT_EQ(result[0], result[1]) << paths[image];
            if (raw == segment_starts[3] + 2)
                EXPECT_NE(result[0], result[1]) << paths[image];
            if (raw == segment_starts[4])
                EXPECT_EQ(result, (std::array<uint8_t, 2>{0x94, 0x99}))
                    << paths[image];
        }
        EXPECT_EQ(first_bank_difference, segment_starts[3] + 2)
            << paths[image];
        // The same 7E9Dh bytes use different 7570h axes in A and S37.
        cpu.mLowerData[0x47] = 40;
        cpu.mPC = 0x1386;
        ASSERT_TRUE(run_until(0x139E, 300)) << paths[image];
        for (int flag = 0; flag < 2; ++flag) {
            cpu.mSFR[REG_PSW] = 0;
            cpu.mSFR[REG_T2CON] &= static_cast<uint8_t>(~0x02);
            cpu.mLowerData[0x22] = 0x02;
            cpu.mLowerData[0x2B] = flag ? 0x80 : 0;
            cpu.mLowerData[0x57] = 0;
            cpu.mPC = 0x3329;
            ASSERT_TRUE(run_until(0x3333, 20)) << paths[image];
            EXPECT_EQ(cpu.mLowerData[7], image == 0 ? 3 : 5)
                << paths[image];
            cpu.mPC = 0x3384;
            ASSERT_TRUE(run_until(0x33D3, 100)) << paths[image];
            EXPECT_EQ(cpu.mLowerData[2],
                      flag ? 0x99 : (image == 0 ? 0x99 : 0x8E))
                << paths[image];
        }
    }
    int default_differences = 0;
    int alternate_differences = 0;
    int first_default_difference = -1;
    int last_default_difference = -1;
    for (size_t raw = 0; raw < 256; ++raw) {
        if (responses[0][0][raw] != responses[1][0][raw]) {
            ++default_differences;
            if (first_default_difference < 0)
                first_default_difference = static_cast<int>(raw);
            last_default_difference = static_cast<int>(raw);
        }
        alternate_differences += responses[0][1][raw] != responses[1][1][raw];
    }
    EXPECT_EQ(default_differences, 215);
    EXPECT_EQ(first_default_difference, 22);
    EXPECT_EQ(last_default_difference, 236);
    EXPECT_EQ(alternate_differences, 0);
    for (size_t raw = 0; raw < 236; ++raw)
        EXPECT_EQ(responses[1][0][raw], responses[0][0][raw + 20])
            << "raw RAM47h=" << raw;
    for (size_t raw = 5; raw < 236; ++raw)
        EXPECT_EQ(responses[1][2][raw], responses[0][2][raw + 20])
            << "third curve raw RAM47h=" << raw;
    if (const char *path = std::getenv("MA17_7E9D_SWEEP_CSV")) {
        std::ofstream output(path);
        ASSERT_TRUE(output.is_open()) << path;
        output << "raw_ram47,a_default,s37_default,a_alternate,s37_alternate\n";
        for (size_t raw = 0; raw < 256; ++raw)
            output << raw << ',' << int(responses[0][0][raw]) << ','
                   << int(responses[1][0][raw]) << ','
                   << int(responses[0][1][raw]) << ','
                   << int(responses[1][1][raw]) << '\n';
    }
    if (const char *path = std::getenv("MA17_7EBB_SWEEP_CSV")) {
        std::ofstream output(path);
        ASSERT_TRUE(output.is_open()) << path;
        output << "raw_ram47,a_third,s37_third\n";
        for (size_t raw = 0; raw < 256; ++raw)
            output << raw << ',' << int(responses[0][2][raw]) << ','
                   << int(responses[1][2][raw]) << '\n';
    }
}

TEST(Sab80C517, AlcoholCodeMatrix7662SeparatesAxisAndCellDifferences) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    struct Axis { uint8_t index, fraction, row_fraction; };
    constexpr std::array axes{Axis{36, 0xD0, 0x10},
                              Axis{38, 0x10, 0x10}};
    constexpr std::array expected{
        std::array<uint8_t, 2>{0x1C, 0x1A},
        std::array<uint8_t, 2>{0x33, 0x31}};
    constexpr std::array expected_48{
        std::array<uint8_t, 2>{0x0A, 0x09},
        std::array<uint8_t, 2>{0x12, 0x12}};
    constexpr std::array expected_timer{
        std::array<uint16_t, 2>{0x0130, 0x0140},
        std::array<uint16_t, 2>{0x00F1, 0x00F1}};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        for (size_t axis = 0; axis < axes.size(); ++axis) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(paths[rom], std::ios::binary);
            ASSERT_TRUE(file.is_open()) << paths[rom];
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x704A], 0x76);
            ASSERT_EQ(code[0x704B], 0x62);
            ASSERT_EQ(code[0x1571], 0xF5); // MOV 48h,A
            ASSERT_EQ(code[0x1572], 0x48);
            cpu.mSFR[REG_DPH] = 0x70;
            cpu.mSFR[REG_DPL] = 0x4A;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mLowerData[0] = 15;
            cpu.mLowerData[4] = axes[axis].row_fraction;
            cpu.mLowerData[5] = axes[axis].index;
            cpu.mLowerData[6] = axes[axis].fraction;
            cpu.mLowerData[0x7C] = 0x7E; // Fixed ADC2-path factor; XRAM stays zero.
            cpu.mPC = 0x13C6;
            for (int step = 0; step < 1000 && cpu.mPC != 0x13CC; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x13CC) << paths[rom];
            EXPECT_EQ(cpu.mLowerData[3], expected[rom][axis])
                << "ROM=" << rom << " axis=" << axis;
            for (int step = 0; step < 2000 && cpu.mPC != 0x1573; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x1573) << paths[rom];
            EXPECT_EQ(cpu.mLowerData[0x48], expected_48[rom][axis])
                << "ROM=" << rom << " axis=" << axis;
            cpu.mSFR[REG_DPH] = 0x72;
            cpu.mSFR[REG_DPL] = 0;
            cpu.mLowerData[2] = 0xC0;
            cpu.mLowerData[3] = 0;
            xram[0xF869] = 0x40;
            xram[0xF88D] = 0xFF;
            xram[0xF808] = 0x80;
            upper[0x1D] = 0xFF;
            cpu.mPC = 0x1E30;
            for (int step = 0; step < 1000 && cpu.mPC != 0x1EF7; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x1EF7) << paths[rom];
            EXPECT_EQ(uint16_t(cpu.mLowerData[0x14] << 8 |
                               cpu.mLowerData[0x15]), expected_timer[rom][axis])
                << "ROM=" << rom << " axis=" << axis;
            ASSERT_EQ(code[0x058E], 0x20); // Original CC3 scheduler entry.
            cpu.mSFR[REG_TL2] = 0x10;
            cpu.mSFR[REG_TH2] = 0x20;
            cpu.mPC = 0x058E;
            for (int step = 0; step < 100 && cpu.mPC != 0x05DD; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x05DD) << paths[rom];
            EXPECT_EQ(uint16_t(cpu.mSFR[REG_CCH3] << 8 |
                               cpu.mSFR[REG_CCL3]),
                      0x2010 + 2 * expected_timer[rom][axis])
                << "ROM=" << rom << " axis=" << axis;
            ASSERT_EQ(cpu.mSFR[REG_CCEN] & 0xC0, 0x80);
            ASSERT_NE(cpu.mSFR[REG_P1] & 0x08, 0);
            cpu.cc3_output_pin = 0; // Isolate the model's rising compare edge.
            cpu.mSFR[REG_T2CON] = 0x05;
            cpu.mSFR[REG_PCON] |= 0x01; // Idle CPU; Timer 2 keeps counting.
            const int delay = 2 * expected_timer[rom][axis];
            for (int elapsed = 1; elapsed <= delay; ++elapsed) {
                tick(&cpu);
                EXPECT_EQ(cpu.cc3_output_pin, elapsed == delay ? 1 : 0)
                    << "ROM=" << rom << " axis=" << axis
                    << " elapsed=" << elapsed;
            }
        }
    }
}

TEST(Sab80C517, AlcoholCodeRam48ReachesPublishedTimerPair) {
    struct Case { uint8_t ram48; uint16_t intermediate, published; };
    constexpr std::array cases{
        Case{0x09, 0x00A1, 0x0140},
        Case{0x0A, 0x0099, 0x0130},
        Case{0x12, 0x0079, 0x00F1}};
    for (const auto &[ram48, intermediate, published] : cases) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::ifstream file(
            std::filesystem::path(MA17_ROM_PATH).parent_path() /
                "firmwares_modificados_ma17_tipo" /
                "tipo 1.6 alcool27c256.bin",
            std::ios::binary);
        ASSERT_TRUE(file.is_open());
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        ASSERT_EQ(code[0x1E34], 0x85); // MOV B,48h in the original ROM.
        ASSERT_EQ(code[0x1E35], 0x48);
        cpu.mSFR[REG_P2] = 0xF8;
        cpu.mSFR[REG_DPH] = 0x72;
        cpu.mSFR[REG_DPL] = 0;
        cpu.mLowerData[2] = 0xC0;
        cpu.mLowerData[3] = 0;
        cpu.mLowerData[0x48] = ram48;
        xram[0xF869] = 0x40;
        xram[0xF88D] = 0xFF;
        xram[0xF808] = 0x80; // Keep the ROM's ceiling branch enabled.
        upper[0x1D] = 0xFF; // Internal 9Dh multiplier at 1EA4h.
        cpu.mPC = 0x1E30;
        for (int step = 0; step < 100 && cpu.mPC != 0x1E5C; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x1E5C) << "RAM48=" << int(ram48);
        EXPECT_EQ(uint16_t(cpu.mLowerData[3] << 8 | cpu.mLowerData[2]),
                  intermediate) << "RAM48=" << int(ram48);
        for (int step = 0; step < 1000 && cpu.mPC != 0x1EC5; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x1EC5) << "RAM48=" << int(ram48);
        EXPECT_EQ(uint16_t(cpu.mLowerData[3] << 8 | cpu.mLowerData[2]),
                  published)
            << "pre-limit RAM48=" << int(ram48);
        for (int step = 0; step < 1000 && cpu.mPC != 0x1EF7; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x1EF7) << "RAM48=" << int(ram48);
        EXPECT_EQ(uint16_t(cpu.mLowerData[0x14] << 8 |
                           cpu.mLowerData[0x15]), published)
            << "RAM48=" << int(ram48);
    }
}

TEST(Sab80C517, FiatMatrixAndAxisEffectsCanBeSeparatedWithOriginalRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin"};
    struct Case { size_t rom; uint8_t r5; uint8_t r6; };
    constexpr std::array cases{Case{0, 0x30, 0x00}, Case{1, 0x30, 0x00},
                               Case{0, 0x32, 0x10}, Case{1, 0x32, 0x10}};
    std::array<uint16_t, 4> results{};
    for (size_t index = 0; index < cases.size(); ++index) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(paths[cases[index].rom], std::ios::binary);
        ASSERT_TRUE(file.is_open());
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        cpu.mSFR[REG_DPH] = 0x75;
        cpu.mSFR[REG_DPL] = 0x81;
        cpu.mLowerData[0] = 0x0F; // Row stride from the 137Bh trace.
        cpu.mLowerData[4] = 0xC0;
        cpu.mLowerData[5] = cases[index].r5;
        cpu.mLowerData[6] = cases[index].r6;
        cpu.mSFR[REG_ACC] = cases[index].r5; // 5326h precedes 532Fh in the caller.
        cpu.mPC = 0x532F;
        for (int step = 0; step < 100 && cpu.mPC != 0x5366; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x5366);
        results[index] = uint16_t(cpu.mSFR[REG_ACC] << 8 | cpu.mSFR[REG_B]);
    }
    EXPECT_EQ(results[0], 0x37C0);
    EXPECT_EQ(results[1], 0x4CC0);
    EXPECT_EQ(results[2], 0x2CC0);
    EXPECT_EQ(results[3], 0x41C0);
    EXPECT_EQ(results[1] - results[0], 0x1500);
    EXPECT_EQ(results[3] - results[2], 0x1500);
}

TEST(Sab80C517, FiatMatrixSubviewFlagChangesLookupWithFixedIram6f) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    ASSERT_EQ(original[0x7048], 0x75);
    ASSERT_EQ(original[0x7049], 0x81);
    ASSERT_EQ(original[0x704E], 0x76);
    ASSERT_EQ(original[0x704F], 0x17);

    constexpr std::array<uint8_t, 2> axis_values{0x1B, 0xCB};
    std::array<std::array<uint16_t, 2>, 2> results{};
    for (size_t axis = 0; axis < axis_values.size(); ++axis) {
        for (size_t flag = 0; flag < 2; ++flag) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mSFR[REG_SP] = 0x40;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mLowerData[0x47] = 0x28;
            cpu.mLowerData[0x6F] = axis_values[axis];
            cpu.mLowerData[0x2E] = flag ? 0x40 : 0x00;
            cpu.mPC = 0x1344;
            for (int step = 0; step < 500 && cpu.mPC != 0x1378; ++step)
                tick(&cpu);
            ASSERT_EQ(cpu.mPC, 0x1378) << axis << "/" << flag;
            EXPECT_EQ((uint16_t(cpu.mSFR[REG_DPH]) << 8) |
                          cpu.mSFR[REG_DPL], flag ? 0x704E : 0x7048);
            for (int step = 0; step < 500 && cpu.mPC != 0x137B; ++step)
                tick(&cpu);
            ASSERT_EQ(cpu.mPC, 0x137B) << axis << "/" << flag;
            results[axis][flag] = uint16_t(cpu.mSFR[REG_ACC] << 8 |
                                           cpu.mSFR[REG_B]);
            tick(&cpu);  // MOV R2,B at 137Bh.
            tick(&cpu);  // MOV R3,A at 137Dh.
            EXPECT_EQ(uint16_t(cpu.mLowerData[3] << 8 | cpu.mLowerData[2]),
                      results[axis][flag]);
        }
        EXPECT_NE(results[axis][0], results[axis][1])
            << "fixed RAM6F=" << static_cast<unsigned>(axis_values[axis]);
    }
}

TEST(Sab80C517, FiatMatrixSubviewPointerAloneChangesLookup) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    constexpr std::array<uint16_t, 2> directory_slots{0x7048, 0x704E};
    constexpr std::array<uint16_t, 2> matrix_bases{0x7581, 0x7617};
    std::array<uint16_t, 2> results{};
    for (size_t index = 0; index < directory_slots.size(); ++index) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_SP] = 0x40;
        cpu.mSFR[REG_P2] = 0xF8;
        cpu.mSFR[REG_DPH] = directory_slots[index] >> 8;
        cpu.mSFR[REG_DPL] = directory_slots[index] & 0xFF;
        cpu.mLowerData[0] = 0x0F; // Fifteen columns per matrix row.
        cpu.mLowerData[4] = 0xC0;
        cpu.mLowerData[5] = 0x03; // Valid column in both views.
        cpu.mLowerData[6] = 0x40;
        cpu.mLowerData[0x57] = 0; // First directory entry in each view.
        cpu.mPC = 0x1378;
        for (int step = 0; step < 100 && cpu.mPC != 0x532F; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x532F) << index;
        EXPECT_EQ((uint16_t(cpu.mSFR[REG_DPH]) << 8) |
                      cpu.mSFR[REG_DPL], matrix_bases[index]);
        EXPECT_EQ(code[matrix_bases[index] + 3], index ? 0xAE : 0x26);
        for (int step = 0; step < 200 && cpu.mPC != 0x137B; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x137B) << index;
        results[index] = uint16_t(cpu.mSFR[REG_ACC] << 8 |
                                  cpu.mSFR[REG_B]);
    }
    EXPECT_NE(results[0], results[1]);
}

TEST(Sab80C517, FiatIram4eSelectsDistinctDecayFactors) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    const std::array<uint8_t, 2> segment_states{0x23, 0xB1};
    const std::array<uint8_t, 2> expected{0xE6, 0xE5};
    const std::array<uint8_t, 2> expected_second{0xEA, 0xE8};
    for (const auto &path : paths) {
        for (size_t index = 0; index < segment_states.size(); ++index) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            cpu.mLowerData[0x21] = 0x08; // Enter the 0781h table path.
            cpu.mLowerData[0x2F] = 0;    // Select the third ten-byte row.
            cpu.mLowerData[0x4E] = segment_states[index];
            cpu.mLowerData[0x78] = 0xF3;
            cpu.mLowerData[0x7A] = 0xF3;
            cpu.mPC = 0x0781;
            for (int step = 0; step < 10 && cpu.mPC != 0x0784 &&
                 cpu.mPC != 0x07B6; ++step)
                tick(&cpu);
            ASSERT_EQ(cpu.mPC, 0x0784) << path;
            for (int step = 0; step < 100 && cpu.mPC != 0x07B6; ++step)
                tick(&cpu);
            ASSERT_EQ(cpu.mPC, 0x07B6) << path;
            EXPECT_EQ(cpu.mLowerData[0x78], expected[index]) << path;
            EXPECT_EQ(cpu.mLowerData[0x7A], expected_second[index]) << path;
        }
    }
}

TEST(Sab80C517, FiatSyntheticIram78ChangesPreThresholdPair) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    struct State {
        uint8_t r4, r5, r6, b, ram5a, ram63;
        uint16_t expected_own;
    };
    // Synthetic nonzero-78h states: test the opcode path, not reachability.
    constexpr std::array states{State{0xB3, 0x17, 0x08, 0x17, 0xB3, 0x51, 0x0946},
                                State{0x36, 0x11, 0x08, 0x11, 0x36, 0x29, 0x0890}};
    constexpr std::array<uint8_t, 2> ram78_values{0x19, 0x15};
    std::array<std::array<uint16_t, 2>, 2> results{};
    for (size_t state_index = 0; state_index < states.size(); ++state_index) {
        for (size_t value_index = 0; value_index < ram78_values.size(); ++value_index) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = 32767;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = 65535;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            const auto &state = states[state_index];
            cpu.mSFR[REG_PSW] = 0x08; // Captured register bank 1.
            cpu.mSFR[REG_SP] = 0x40;  // Keep calls clear of bank 1 registers.
            cpu.mSFR[REG_B] = state.b;
            cpu.mSFR[REG_DPH] = 0x72;
            cpu.mSFR[REG_DPL] = 0x00;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mLowerData[0x09] = 0x00; // R1
            cpu.mLowerData[0x0A] = 0xFF; // R2
            cpu.mLowerData[0x0B] = 0x04; // R3
            cpu.mLowerData[0x0C] = state.r4;
            cpu.mLowerData[0x0D] = state.r5;
            cpu.mLowerData[0x0E] = state.r6;
            cpu.mLowerData[0x0F] = 0x00; // R7
            cpu.mLowerData[0x25] = 0x76;
            cpu.mLowerData[0x2E] = 0xA4;
            cpu.mLowerData[0x2F] = 0x9A;
            cpu.mLowerData[0x59] = 0x08;
            cpu.mLowerData[0x5A] = state.ram5a;
            cpu.mLowerData[0x63] = state.ram63;
            cpu.mLowerData[0x78] = ram78_values[value_index];
            cpu.mPC = 0x1D4B;
            for (int step = 0; step < 500 && cpu.mPC != 0x1DD8; ++step)
                tick(&cpu);
            ASSERT_EQ(cpu.mPC, 0x1DD8);
            results[state_index][value_index] =
                uint16_t(cpu.mLowerData[0x0B] << 8 | cpu.mLowerData[0x0A]);
        }
    }
    EXPECT_EQ(results[0][0], states[0].expected_own);
    EXPECT_EQ(results[1][1], states[1].expected_own);
    EXPECT_EQ(results[0][1], 0x0935);
    EXPECT_EQ(results[1][0], 0x08A0);
    EXPECT_EQ(results[0][0] - results[0][1], 0x11);
    EXPECT_EQ(results[1][0] - results[1][1], 0x10);
}

TEST(Sab80C517, FiatRam3dThresholdSelectsFlag2f5InOriginalRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin"};
    constexpr std::array<uint8_t, 8> selector{
        0xE5, 0x3D, 0xB4, 0x02, 0x00, 0xB3, 0x92, 0x7D};
    for (const auto &path : paths) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size())) << path;
        ASSERT_TRUE(std::equal(selector.begin(), selector.end(),
                               original.begin() + 0x19D9)) << path;
        for (const uint8_t value : {uint8_t{0}, uint8_t{1}, uint8_t{2},
                                    uint8_t{3}, uint8_t{0xFF}}) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = 32767;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = 255;
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mLowerData[0x3D] = value;
            cpu.mLowerData[0x2F] = 0xA5;
            cpu.mPC = 0x19D9;
            for (int step = 0; step < 4; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            EXPECT_EQ(cpu.mPC, 0x19E1) << path;
            EXPECT_EQ(bool(cpu.mLowerData[0x2F] & 0x20), value >= 2) << path;
            EXPECT_EQ(cpu.mLowerData[0x2F] & 0xDF, 0x85) << path;
        }
    }
}

TEST(Sab80C517, IdleFaultStateBitBranchIsHomologousInSixOriginalRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t index = 0; index < paths.size(); ++index) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[index], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[index];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const uint16_t pc = index == 0 || index == 3 ? 0x2B38 : 0x2B54;
        const std::array<uint8_t, 8> prefix{
            0xE2, 0x20, 0xE6, 0x03, 0x20, 0xE5, 0x03, 0x02};
        ASSERT_TRUE(std::equal(prefix.begin(), prefix.end(), code.begin() + pc))
            << paths[index];
        for (const auto [state, expected] :
             {std::pair<uint8_t, uint8_t>{0x0E, 0x00},
              {0x2E, 0x0A}, {0x6E, 0x00}, {0xAE, 0x02}}) {
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false); // Preserve the already loaded original ROM.
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_PSW] = 0;
            cpu.mLowerData[0] = 0x39; // Bank 0 R0; MOVX uses P2:F839h.
            xram[0xF839] = state;
            cpu.mPC = pc;
            cpu.mTickDelay = 0;
            tick(&cpu);
            ASSERT_EQ(cpu.mSFR[REG_ACC], state) << paths[index];
            ASSERT_EQ(cpu.mPC, pc + 1) << paths[index];
            for (int step = 0; step < 7; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            EXPECT_EQ(cpu.mLowerData[0x27] & 0x0A, expected)
                << paths[index] << " state=" << int(state);
            EXPECT_EQ(xram[0xF839], state) << paths[index];
        }
    }
}

TEST(Sab80C517, IdleFaultBitZeroRequiresThrottleThresholdAndZeroXramInSixRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    const std::array<uint8_t, 12> opcodes{
        0x74, 0x4A, 0xC3, 0x95, 0x70, 0x50,
        0x1E, 0xE2, 0x70, 0x33, 0xD2, 0x38};
    for (size_t index = 0; index < paths.size(); ++index) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[index], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[index];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const uint16_t pc = index == 0 || index == 3 ? 0x29CB : 0x29E7;
        ASSERT_TRUE(std::equal(opcodes.begin(), opcodes.end(), code.begin() + pc))
            << paths[index];
        for (const auto [throttle, xram3c, expected_pc, expected_bit] :
             {std::tuple<uint8_t, uint8_t, uint16_t, bool>{0x4A, 0, 0x29F0, false},
              {0x4B, 1, 0x2A08, false},
              {0x4B, 0, 0x29D7, true}}) {
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_PSW] = 0;
            cpu.mLowerData[0] = 0x3C; // Bank 0 R0; MOVX uses P2:F83Ch.
            cpu.mLowerData[0x70] = throttle;
            xram[0xF83C] = xram3c;
            cpu.mPC = pc;
            const uint16_t stop = expected_pc + (pc - 0x29CB);
            for (int step = 0; step < 7 && cpu.mPC != stop; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            EXPECT_EQ(cpu.mPC, stop) << paths[index];
            EXPECT_EQ(bool(cpu.mLowerData[0x27] & 1), expected_bit)
                << paths[index];
            EXPECT_EQ(xram[0xF83C], xram3c) << paths[index];
        }
    }
}

TEST(Sab80C517, AlternativeRam70FormulaIsIdenticalInSixOriginalRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    std::array<unsigned char, 32768> reference{};
    {
        std::ifstream file(paths[0], std::ios::binary);
        ASSERT_TRUE(file.is_open());
        file.read(reinterpret_cast<char *>(reference.data()), reference.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(reference.size()));
    }
    for (const auto &path : paths) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        ASSERT_TRUE(std::equal(reference.begin() + 0x11A8,
                               reference.begin() + 0x11C2,
                               code.begin() + 0x11A8)) << path;
        for (const auto [r2, r3, expected_6f, expected_70] :
             {std::tuple<uint8_t, uint8_t, uint8_t, uint8_t>{0x30, 0x22,
                                                              0x1B, 0x53},
              {0x00, 0x80, 0x00, 0x38},
              {0xF8, 0x00, 0xFF, 0xFF}}) {
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            reset(&cpu, false);
            cpu.mSFR[REG_PSW] = 0;
            cpu.mLowerData[2] = r2;
            cpu.mLowerData[3] = r3;
            cpu.mPC = 0x11A8;
            for (int step = 0; step < 16 && cpu.mPC != 0x11C2; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            EXPECT_EQ(cpu.mPC, 0x11C2) << path;
            EXPECT_EQ(cpu.mLowerData[0x6F], expected_6f) << path;
            EXPECT_EQ(cpu.mLowerData[0x70], expected_70) << path;
            EXPECT_NE(cpu.mLowerData[0x2E] & 0x40, 0) << path;
        }
    }
}

TEST(Sab80C517, IdlePositionR4StepUsesOriginalBoundsInSixRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t index = 0; index < paths.size(); ++index) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[index], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[index];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const uint16_t entry = index == 0 || index == 3 ? 0x23CE : 0x23EA;
        const uint16_t exit = index == 0 || index == 3 ? 0x2495 : 0x24B1;
        ASSERT_EQ(code[entry], 0x7B) << paths[index]; // MOV R3,#06h
        ASSERT_EQ(code[entry + 1], 0x06) << paths[index];
        ASSERT_EQ(code[0x7301], 0x33) << paths[index];
        ASSERT_EQ(code[0x7305], 0x65) << paths[index];
        ASSERT_EQ(code[0x7306], 0x9C) << paths[index];
        struct StepCase {
            bool carry;
            uint8_t position;
            uint8_t cluster;
            uint8_t expected_position;
            uint8_t expected_cluster;
        };
        const std::array<StepCase, 4> cases{{
            {false, 0x07, 0x66, 0x06, 0x67},
            {true, 0x07, 0x66, 0x08, 0x65},
            {false, 0x00, 0x9C, 0x00, 0x9C},
            {true, 0x33, 0x65, 0x33, 0x65}}};
        for (const auto &test_case : cases) {
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_PSW] = test_case.carry ? 0x80 : 0;
            cpu.mSFR[REG_DPH] = 0x73;
            cpu.mSFR[REG_DPL] = 0x00;
            cpu.mLowerData[4] = test_case.position; // Bank 0 R4.
            xram[0xF83D] = test_case.position;
            std::fill(xram.begin() + 0xF840, xram.begin() + 0xF846,
                      test_case.cluster);
            cpu.mPC = entry;
            for (int step = 0; step < 100 && cpu.mPC != exit; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, exit) << paths[index]
                                      << " carry=" << test_case.carry;
            EXPECT_EQ(xram[0xF83D], test_case.expected_position) << paths[index];
            EXPECT_EQ(xram[0xF840], test_case.expected_cluster) << paths[index];
        }
    }
}

TEST(Sab80C517, FiatLambdaGateClearsFlagOnlyWithoutMultiplyOverflow) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    for (const uint8_t factor : {uint8_t{0xA0}, uint8_t{0x00}}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_PSW] = 0x08;
        cpu.mSFR[REG_ACC] = 0xEE;
        cpu.mSFR[REG_B] = factor;
        cpu.mLowerData[0x08] = 0x87; // R0 in bank 1.
        cpu.mUpperData[0x87 - 0x80] = factor;
        cpu.mLowerData[0x2E] = 0xA4;
        cpu.mPC = 0x155A; // MUL AB, followed by overflow guard.
        for (int step = 0; step < 20 && cpu.mPC != 0x1562; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x1562);
        EXPECT_EQ(cpu.mLowerData[0x2E] & 0x04, factor ? 0x04 : 0x00);
        EXPECT_EQ(cpu.mSFR[REG_PSW] & 0x04, factor ? 0x04 : 0x00);
        EXPECT_EQ(cpu.mUpperData[0x87 - 0x80], factor ? 0x94 : 0x00);
    }
}

TEST(Sab80C517, FiatRpm7b32SegmentsAllRawValues) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    ASSERT_TRUE(std::equal(original.begin() + 0x7B32,
                           original.begin() + 0x7B3E,
                           std::array<unsigned char, 12>{
                               0x47, 0x0A, 0x06, 0x08, 0x0C, 0x18,
                               0x23, 0x29, 0x28, 0x28, 0x2F, 0x01}.begin()));
    const std::array<unsigned, 9> thresholds{
        8, 16, 28, 52, 87, 128, 168, 208, 255};
    for (unsigned raw = 0; raw <= 0xFF; ++raw) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_DPH] = 0x7B;
        cpu.mSFR[REG_DPL] = 0x32;
        cpu.mSFR[REG_SP] = 0x42;
        cpu.mLowerData[0x41] = 0x00;
        cpu.mLowerData[0x42] = 0x60;
        cpu.mLowerData[0x47] = static_cast<unsigned char>(raw);
        cpu.mPC = 0x527C;
        for (int step = 0; step < 400 && cpu.mPC != 0x6000; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x6000) << "RAM[47h]=" << raw;
        // SAB80C517 Instruction Set: MOVC reads the next reverse increment;
        // ADD/ADDC carry at 528Bh/5292h chooses the segment boundary.
        const auto expected = std::count_if(
            thresholds.begin(), thresholds.end(),
            [raw](unsigned threshold) { return raw >= threshold; });
        EXPECT_EQ(cpu.mLowerData[3], expected) << "RAM[47h]=" << raw;
    }
}

TEST(Sab80C517, SixRom7b3eSecondAxisSegmentsAllRawValues) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    const std::array<std::array<unsigned, 5>, 6> thresholds{{
        {141, 188, 220, 243, 251}, {141, 188, 220, 243, 251},
        {141, 188, 220, 243, 251}, {133, 180, 212, 235, 243},
        {119, 166, 198, 221, 229}, {119, 166, 198, 221, 229}}};
    for (std::size_t variant = 0; variant < paths.size(); ++variant) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(paths[variant], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[variant];
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        ASSERT_EQ(original[0x7B3F], 6) << paths[variant];
        const bool upper_axis = original[0x7B3E] == 0xAF;
        ASSERT_TRUE(upper_axis || original[0x7B3E] == 0x7D);
        const uint16_t reader = variant == 0 || variant == 3 ? 0x527C : 0x533F;
        for (unsigned raw = 0; raw <= 0xFF; ++raw) {
            std::array<unsigned char, 32768> code = original;
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mSFR[REG_DPH] = 0x7B;
            cpu.mSFR[REG_DPL] = 0x3E;
            cpu.mSFR[REG_SP] = 0x42;
            cpu.mLowerData[0x41] = 0x00;
            cpu.mLowerData[0x42] = 0x60;
            cpu.mLowerData[0x7D] = static_cast<unsigned char>(
                upper_axis ? raw ^ 0xFFu : raw);
            upper[0xAF - 0x80] = static_cast<unsigned char>(
                upper_axis ? raw : raw ^ 0xFFu);
            cpu.mPC = reader;
            for (int step = 0; step < 400 && cpu.mPC != 0x6000; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x6000) << paths[variant] << " raw=" << raw;
            const auto expected = std::count_if(
                thresholds[variant].begin(), thresholds[variant].end(),
                [raw](unsigned threshold) { return raw >= threshold; });
            EXPECT_EQ(cpu.mLowerData[3], expected)
                << paths[variant] << " raw=" << raw;
        }
    }
}

TEST(Sab80C517, SixRom7824And782bMatrixAxesSegmentAllRawValues) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    const std::array axes{
        std::pair{0x7824u, std::array{37u, 68u, 130u, 250u}},
        std::pair{0x782Bu, std::array{52u, 80u, 108u, 256u}}};
    for (std::size_t variant = 0; variant < paths.size(); ++variant) {
        std::array<unsigned char, 32768> original{};
        std::ifstream file(paths[variant], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[variant];
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        const uint16_t reader = variant == 0 || variant == 3 ? 0x527C : 0x533F;
        for (const auto &[base, thresholds] : axes) {
            const uint16_t slot = base == 0x7824 ? 0x7054 : 0x7056;
            ASSERT_EQ((static_cast<unsigned>(original[slot]) << 8) |
                          original[slot + 1], base) << paths[variant];
            ASSERT_EQ(original[base], base == 0x7824 ? 0x70 : 0x47);
            ASSERT_EQ(original[base + 1], base == 0x7824 ? 5 : 4);
            for (unsigned raw = 0; raw <= 0xFF; ++raw) {
                std::array<unsigned char, 32768> code = original;
                std::array<unsigned char, 256> xram{};
                std::array<unsigned char, 128> upper{};
                em8051 cpu{};
                cpu.mCodeMem = code.data();
                cpu.mCodeMemMaxIdx = code.size() - 1;
                cpu.mExtData = xram.data();
                cpu.mExtDataMaxIdx = xram.size() - 1;
                cpu.mUpperData = upper.data();
                reset(&cpu, true);
                std::copy(original.begin(), original.end(), code.begin());
                cpu.mSFR[REG_DPH] = static_cast<unsigned char>(base >> 8);
                cpu.mSFR[REG_DPL] = static_cast<unsigned char>(base & 0xFF);
                cpu.mSFR[REG_SP] = 0x42;
                cpu.mLowerData[0x41] = 0;
                cpu.mLowerData[0x42] = 0x60;
                cpu.mLowerData[original[base]] = static_cast<unsigned char>(raw);
                cpu.mPC = reader;
                for (int step = 0; step < 400 && cpu.mPC != 0x6000; ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, 0x6000) << paths[variant] << " raw=" << raw;
                const auto expected = std::count_if(
                    thresholds.begin(), thresholds.end(),
                    [raw](unsigned threshold) { return raw >= threshold; });
                EXPECT_EQ(cpu.mLowerData[3], expected)
                    << paths[variant] << " table=" << base << " raw=" << raw;
            }
        }
    }
}

TEST(Sab80C517, FiatOriginal1255LookupBounds79d8IndexForAllRam70) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    ASSERT_EQ(original[0x70D8], 0x79);
    ASSERT_EQ(original[0x70DA], 0x79);
    ASSERT_EQ(original[0x70DB], 0xD8);
    ASSERT_EQ(original[0x7058], 0x79);
    ASSERT_EQ(original[0x7059], 0x70);
    ASSERT_EQ(original[0x7970], 0x0D); // Bank-1 R5 receives IRAM70h.
    ASSERT_EQ(original[0x7971], 0x08); // Eight cumulative segments.
    const auto s88_path = std::filesystem::path(MA17_ROM_PATH).parent_path() /
        "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin";
    std::array<unsigned char, 32768> s88{};
    std::ifstream s88_file(s88_path, std::ios::binary);
    ASSERT_TRUE(s88_file.is_open());
    s88_file.read(reinterpret_cast<char *>(s88.data()), s88.size());
    ASSERT_EQ(s88_file.gcount(), static_cast<std::streamsize>(s88.size()));
    for (const auto [begin, end] : {std::pair{0x1255, 0x1260},
                                   std::pair{0x5279, 0x52C9},
                                   std::pair{0x7970, 0x7998},
                                   std::pair{0x1572, 0x1577}})
        EXPECT_TRUE(std::equal(original.begin() + begin, original.begin() + end,
                               s88.begin() + begin)) << std::hex << begin;
    std::array<unsigned, 17> index_counts{};
    for (unsigned input = 0; input <= 0xFF; ++input) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_PSW] = 0x08; // Fiat's bank 1 maps R5 to lower IRAM 0Dh.
        cpu.mSFR[REG_SP] = 0x40; // Keep the call stack clear of bank 1.
        cpu.mLowerData[0x70] = static_cast<unsigned char>(input);
        cpu.mPC = 0x1255; // Original lookup through 7058h, then write 6Ah.
        for (int step = 0; step < 400 && cpu.mPC != 0x1260; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x1260) << "RAM[70h]=" << input;
        const unsigned ram6a = cpu.mLowerData[0x6A];
        if (input == 0x1D) EXPECT_EQ(ram6a, 0xD1u);
        if (input == 0x1E) EXPECT_EQ(ram6a, 0xE1u);
        if ((ram6a & 0x0F) == 7)
            EXPECT_EQ(ram6a, 0x07u) << "RAM[70h]=" << input;
        // SAB80C517 Instruction Set: ADD sets carry; ANL preserves it;
        // ADDC at 1574h forms the MOVC index from RAM[6Ah].
        const unsigned index = (ram6a & 0x0F) + (ram6a >= 0x80);
        ASSERT_LT(index, index_counts.size());
        ++index_counts[index];
        EXPECT_LE(index, 7u) << "RAM[70h]=" << input
                             << " RAM[6Ah]=" << ram6a;
    }
    for (unsigned index = 0; index < 8; ++index)
        EXPECT_GT(index_counts[index], 0u) << "index=" << index;
}

TEST(Sab80C517, AlcoholCode1255LookupBounds79d8IndexForAllRam70) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array names{
        "tipo 1.6 alcool27c256.bin",
        "tipo 1.6 alcool27c256+1.5bar.bin",
        "tipo 1.6 alcool27c256 SUN 37a5.bin",
        "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (const char *name : names) {
        const auto path = root / "firmwares_modificados_ma17_tipo" / name;
        std::array<unsigned char, 32768> original{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(original.data()), original.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
        ASSERT_EQ(original[0x1255], 0xAD); // MOV R5,70h, bank 1.
        ASSERT_EQ(original[0x70DA], 0x79);
        ASSERT_EQ(original[0x70DB], 0xD8);
        ASSERT_EQ(original[0x7058], 0x79);
        ASSERT_EQ(original[0x7059], 0x70);
        std::array<unsigned, 17> index_counts{};
        for (unsigned input = 0; input <= 0xFF; ++input) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::copy(original.begin(), original.end(), code.begin());
            cpu.mSFR[REG_PSW] = 0x08;
            cpu.mSFR[REG_SP] = 0x40;
            cpu.mLowerData[0x70] = static_cast<unsigned char>(input);
            cpu.mPC = 0x1255;
            for (int step = 0; step < 400 && cpu.mPC != 0x1260; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x1260) << path << " RAM70=" << input;
            const unsigned ram6a = cpu.mLowerData[0x6A];
            if (input == 0x1D) EXPECT_EQ(ram6a, 0xD1u) << path;
            if (input == 0x1E) EXPECT_EQ(ram6a, 0xE1u) << path;
            if ((ram6a & 0x0F) == 7)
                EXPECT_EQ(ram6a, 0x07u) << path << " RAM70=" << input;
            // SAB80C517 Instruction Set: ADD/ANL/ADDC at 15C1h..15C3h
            // forms the A-code MOVC index without modifying program ROM.
            const unsigned index = (ram6a & 0x0F) + (ram6a >= 0x80);
            ASSERT_LT(index, index_counts.size());
            ++index_counts[index];
            EXPECT_LE(index, 7u) << path << " RAM70=" << input;
        }
        for (unsigned index = 0; index < 8; ++index)
            EXPECT_GT(index_counts[index], 0u) << path << " index=" << index;
    }
}

TEST(Sab80C517, FiatLambdaSecondGuardUsesCoolantOrRpmBounds) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));
    ASSERT_EQ(original[0x7226], 0x44); // RPM-derived threshold.
    ASSERT_EQ(original[0x7227], 0x2C); // Coolant-derived threshold.

    struct State {
        uint8_t ram63;
        uint8_t ram47;
        bool reaches_correction;
    };
    for (const State state : {State{0x51, 0x28, false},
                              State{0x2D, 0x44, false},
                              State{0x2C, 0x28, true},
                              State{0x2D, 0x45, true}}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_PSW] = 0x08;
        cpu.mSFR[0xA0 - 0x80] = 0xF8; // P2 and XPAGE select F8xxh.
        cpu.mSFR[REG_XPAGE] = 0xF8;
        cpu.mSFR[0x83 - 0x80] = 0x72; // DPTR=7200h.
        cpu.mSFR[0x82 - 0x80] = 0x00;
        cpu.mLowerData[0x2C] = 0x20; // Existing correction countdown.
        cpu.mLowerData[0x47] = state.ram47;
        cpu.mLowerData[0x63] = state.ram63;
        cpu.mPC = 0x17C2;
        for (int step = 0; step < 500 && cpu.mPC != 0x1825 &&
                                   cpu.mPC != 0x186D; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        EXPECT_EQ(upper[0xAB - 0x80] & 1u, state.reaches_correction)
            << "RAM63=" << int(state.ram63)
            << " RAM47=" << int(state.ram47);
        EXPECT_EQ(cpu.mPC, state.reaches_correction ? 0x186D : 0x1825);
    }
}

TEST(Sab80C517, FiatLambdaParameterBlockReloadsAndReducesTwoBounds) {
    std::array<unsigned char, 32768> code{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(code.data()), code.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
    ASSERT_EQ(code[0x733D], 0x1E);
    ASSERT_EQ(code[0x733E], 0x01);
    ASSERT_EQ(code[0x733F], 0x0A);
    ASSERT_EQ(code[0x7340], 0x1E);
    ASSERT_EQ(code[0x7341], 0x01);
    ASSERT_EQ(code[0x7342], 0x0F);
    const auto original = code;

    for (const uint8_t countdown : {uint8_t{1}, uint8_t{2}}) {
        std::array<unsigned char, 65536> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_PSW] = 0x08;
        cpu.mSFR[0xA0 - 0x80] = 0xF8;
        cpu.mSFR[REG_XPAGE] = 0xF8;
        cpu.mSFR[0x83 - 0x80] = 0x73; // DPTR=7300h at 1687h.
        cpu.mSFR[0x82 - 0x80] = 0x00;
        cpu.mLowerData[0x2D] = 0x20; // Bit address 6Dh = 2Dh.5.
        cpu.mLowerData[0x65] = 0xA0;
        xram[0xF8E8] = 0x0A;
        xram[0xF8E9] = countdown;
        xram[0xF8EA] = 0x0F;
        xram[0xF8EB] = countdown;
        cpu.mPC = 0x1687;
        // SAB80C517 Instruction Set, pp. 222, 224: these original
        // MOVC/MOVX opcodes read ROM constants and update paged XRAM.
        for (int step = 0; step < 100 && cpu.mPC != 0x16EB; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x16EB);
        const bool expired = countdown == 1;
        EXPECT_EQ(xram[0xF8E8], expired ? 0x09 : 0x0A);
        EXPECT_EQ(xram[0xF8E9], expired ? 0x1E : 0x01);
        EXPECT_EQ(xram[0xF8EA], expired ? 0x0E : 0x0F);
        EXPECT_EQ(xram[0xF8EB], expired ? 0x1E : 0x01);
    }
}

TEST(Sab80C517, SixRom79b0And79baCurvesWriteUpperIram85And86) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        for (const uint8_t index : {uint8_t{0}, uint8_t{4}, uint8_t{9}}) {
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false); // Preserve the original ROM loaded above.
            cpu.mLowerData[5] = index;
            cpu.mLowerData[6] = 0;
            cpu.mPC = a_code ? 0x4989 : 0x48CC;
            const uint16_t end = a_code ? 0x499D : 0x48E0;
            for (int step = 0; step < 120 && cpu.mPC != end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, end) << paths[rom];
            // SAB80C517 On-Chip RAM: @R0=85h/86h targets upper IRAM,
            // not direct SFR addresses or ECU connector pins.
            EXPECT_EQ(upper[0x85 - 0x80], code[0x79B0 + index]) << paths[rom];
            EXPECT_EQ(upper[0x86 - 0x80], code[0x79BA + index]) << paths[rom];
        }
    }
}

TEST(Sab80C517, SixRom74e4DirectIndexUsesR6HighBitAndBoundaryByte) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (const auto &path : paths) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open()) << path;
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        ASSERT_EQ(code[0x7016], 0x74);
        ASSERT_EQ(code[0x7017], 0xE4);
        for (const uint8_t r5 : {uint8_t{0}, uint8_t{1}, uint8_t{8},
                                 uint8_t{9}}) {
            for (const uint8_t r6 : {uint8_t{0}, uint8_t{0x80}}) {
                std::array<unsigned char, 128> upper{};
                em8051 cpu{};
                cpu.mCodeMem = code.data();
                cpu.mCodeMemMaxIdx = code.size() - 1;
                cpu.mUpperData = upper.data();
                reset(&cpu, false);
                cpu.mLowerData[5] = r5;
                cpu.mLowerData[6] = r6;
                cpu.mPC = 0x12B2;
                for (int step = 0; step < 30 && cpu.mPC != 0x12C0; ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, 0x12C0) << path;
                const size_t index = r5 + (r6 >> 7);
                // PC12BDh uses MOVC with R5+R6.7; index 10 reads the
                // next table's first byte and is only a synthetic boundary.
                EXPECT_EQ(cpu.mLowerData[0x49], code[0x74E4 + index])
                    << path << " index=" << index;
            }
        }
    }
}

TEST(Sab80C517, SixRom7036ConstantTableWritesPagedXram7f) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        ASSERT_EQ(code[0x7036], 0x7A);
        ASSERT_EQ(code[0x7037], 0xE0);
        for (const uint8_t index : {uint8_t{0}, uint8_t{4}}) {
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mLowerData[4] = 0;
            cpu.mLowerData[5] = index;
            cpu.mLowerData[6] = 0;
            cpu.mPC = rom == 0 || rom == 3 ? 0x3E41 : 0x3EFE;
            const uint16_t end = rom == 0 || rom == 3 ? 0x3E51 : 0x3F0E;
            for (int step = 0; step < 120 && cpu.mPC != end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, end) << paths[rom];
            // SAB80C517 MOVC and MOVX @R1: the ROM table result is
            // written to paged XRAM F8:7Fh, not an ECU output pin.
            EXPECT_EQ(xram[0xF87F], 0xFF) << paths[rom];
        }
    }
}

TEST(Sab80C517, FiatUpper85And86ReadersSelectSeparateMultipliers) {
    std::array<unsigned char, 32768> code{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(code.data()), code.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
    for (const uint8_t selected : {uint8_t{0x85}, uint8_t{0x86}}) {
        for (const uint8_t value : {uint8_t{0x00}, uint8_t{0xFF}}) {
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            upper[0x85 - 0x80] = selected == 0x85 ? value : 0xA5;
            upper[0x86 - 0x80] = selected == 0x86 ? value : 0x5A;
            cpu.mSFR[0xE0 - 0x80] = 0xFF; // PC37E3h copies A to R3.
            cpu.mSFR[0xF0 - 0x80] = selected == 0x85 ? 1 : 0;
            cpu.mSFR[0x83 - 0x80] = 0x73;
            cpu.mSFR[0x82 - 0x80] = 0x00;
            cpu.mLowerData[0x57] = 0;
            cpu.mPC = 0x37E3;
            for (int step = 0; step < 25 && cpu.mPC != 0x3801; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x3801);
            const uint8_t table = code[selected == 0x85 ? 0x735D : 0x7360];
            const uint8_t first_product_high = static_cast<uint8_t>(
                (static_cast<unsigned>(table) * 0xFFu) >> 8);
            const uint8_t high_product = static_cast<uint8_t>(
                (static_cast<unsigned>(first_product_high) * value) >> 8);
            // SAB80C517 On-Chip RAM: @R1 selects upper IRAM, not an
            // SFR or physical pin. PC37FFh reads it; PC3800h multiplies.
            EXPECT_EQ(cpu.mSFR[0xF0 - 0x80], high_product)
                << "selected=" << static_cast<unsigned>(selected)
                << " value=" << static_cast<unsigned>(value);
        }
    }
}

TEST(Sab80C517, SixRomIram46CurvesSelectSixPointerSlots) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        for (int selection = 0; selection < 6; ++selection) {
            const bool timer2 = selection >= 3;
            const uint8_t selector = static_cast<uint8_t>(selection % 3);
            for (const uint8_t index : {uint8_t{0}, uint8_t{4}, uint8_t{9}}) {
                std::array<unsigned char, 256> xram{};
                std::array<unsigned char, 128> upper{};
                em8051 cpu{};
                cpu.mCodeMem = code.data();
                cpu.mCodeMemMaxIdx = code.size() - 1;
                cpu.mExtData = xram.data();
                cpu.mExtDataMaxIdx = xram.size() - 1;
                cpu.mUpperData = upper.data();
                reset(&cpu, false); // The ROM was loaded once above.
                cpu.mLowerData[5] = index;
                cpu.mLowerData[6] = 0;
                cpu.mLowerData[0x57] = selector;
                cpu.mSFR[REG_T2CON] = timer2 ? 0x02 : 0;
                // SAB80C517 Port 4: low P4.7 skips the floor in the
                // T2I1=0 branch; T2I1=1 also skips it with P4.7 high.
                // The ECU connector role of P4.7 remains unknown.
                cpu.mSFR[0xE8 - 0x80] = timer2 ? 0x80 : 0;
                cpu.mPC = a_code ? 0x499D : 0x48E0;
                const uint16_t read_pc = a_code ? 0x53F2 : 0x532F;
                for (int step = 0; step < 80 && cpu.mPC != read_pc; ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, read_pc) << paths[rom];
                const uint16_t slot = uint16_t((timer2 ? 0x7010 : 0x700A) +
                                               2 * selector);
                const uint16_t base = uint16_t(code[slot] << 8 | code[slot + 1]);
                EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 | cpu.mSFR[REG_DPL]),
                          base) << paths[rom];
                const uint16_t end = a_code ? 0x49BE : 0x4901;
                for (int step = 0; step < 80 && cpu.mPC != end; ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, end) << paths[rom];
                EXPECT_EQ(cpu.mLowerData[0x46], code[base + index]) << paths[rom];
            }
        }
    }
}

TEST(Sab80C517, PostCoolantCurveSelectorUsesThreePointerSlots) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        const bool raised = rom == 1 || rom == 2;
        for (const bool timer2 : {false, true}) {
            for (const bool flag2b7 : {false, true}) {
                std::array<unsigned char, 32768> code{};
                std::array<unsigned char, 256> xram{};
                std::array<unsigned char, 128> upper{};
                em8051 cpu{};
                cpu.mCodeMem = code.data();
                cpu.mCodeMemMaxIdx = code.size() - 1;
                cpu.mExtData = xram.data();
                cpu.mExtDataMaxIdx = xram.size() - 1;
                cpu.mUpperData = upper.data();
                reset(&cpu, true);
                std::ifstream file(paths[rom], std::ios::binary);
                ASSERT_TRUE(file.is_open()) << paths[rom];
                file.read(reinterpret_cast<char *>(code.data()), code.size());
                ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
                cpu.mLowerData[5] = 3;
                cpu.mLowerData[6] = 0;
                cpu.mLowerData[0x2B] = flag2b7 ? 0x80 : 0;
                cpu.mSFR[REG_T2CON] = timer2 ? 0x02 : 0;
                cpu.mPC = a_code ? 0x49D3 : 0x4916;
                const uint16_t read_pc = a_code ? 0x53F2 : 0x532F;
                const uint16_t end = a_code ? 0x49E5 : 0x4922;
                for (int step = 0; step < 80 && cpu.mPC != read_pc; ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, read_pc) << paths[rom];
                const uint16_t slot = timer2 ? 0x701E :
                    (a_code && flag2b7 ? 0x701A : 0x7018);
                const uint16_t base =
                    uint16_t((uint16_t(code[slot]) << 8) | code[slot + 1]);
                EXPECT_EQ((uint16_t(cpu.mSFR[REG_DPH]) << 8) |
                          cpu.mSFR[REG_DPL], base) << paths[rom];
                for (int step = 0; step < 80 && cpu.mPC != end; ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, end) << paths[rom];
                const uint8_t expected = timer2 ? (raised ? 0x49 : 0x2F) :
                                          (raised ? 0x4D : 0x33);
                EXPECT_EQ(code[base + 3], expected) << paths[rom];
                EXPECT_EQ(cpu.mLowerData[2], expected) << paths[rom];
            }
        }
    }
}

TEST(Sab80C517, AlcoholPostCoolantEqualCurvesGiveEqualIsolatedOutput) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array cases{
        std::pair{root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
                  uint8_t{0x99}},
        std::pair{root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
                  uint8_t{0x7F}}};
    for (const auto& [path, expected_output] : cases) {
        std::array<unsigned char, 32768> code{};
        std::array<uint8_t, 2> outputs{};
        for (const bool alternate : {false, true}) {
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            EXPECT_TRUE(std::equal(code.begin() + 0x744E, code.begin() + 0x7458,
                                   code.begin() + 0x7458)) << path;
            xram[0x6C] = 0xB0;
            cpu.mLowerData[5] = 9;
            cpu.mLowerData[6] = 0;
            cpu.mLowerData[0x2B] = alternate ? 0x80 : 0;
            cpu.mLowerData[0x22] = 0;
            cpu.mSFR[REG_T2CON] = 0;
            cpu.mPC = 0x49D3;
            for (int step = 0; step < 100 && cpu.mPC != 0x49E5; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x49E5) << path;
            EXPECT_EQ(cpu.mLowerData[2], code[(alternate ? 0x7458 : 0x744E) + 9])
                << path;
            EXPECT_EQ(cpu.mLowerData[4], 0) << path;
            EXPECT_EQ((uint16_t(cpu.mSFR[REG_DPH]) << 8) |
                      cpu.mSFR[REG_DPL], 0x7200) << path;
            for (int step = 0; step < 300 && cpu.mPC != 0x4A72; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x4A72) << path << " alternate=" << alternate;
            outputs[alternate] = cpu.mLowerData[0x4D];
        }
        EXPECT_EQ(outputs[0], outputs[1]) << path;
        EXPECT_EQ(outputs[0], expected_output) << path;
    }
}

TEST(Sab80C517, AlcoholPostCoolantIndexNineFractionCrossesCurveBoundary) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array cases{
        std::pair{root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
                  std::array<uint8_t, 2>{0x5B, 0x5A}},
        std::pair{root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
                  std::array<uint8_t, 2>{0x41, 0x40}}};
    for (const auto& [path, expected] : cases) {
        std::array<unsigned char, 32768> code{};
        std::array<uint8_t, 2> interpolated{};
        for (const bool alternate : {false, true}) {
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            cpu.mLowerData[5] = 9;
            cpu.mLowerData[6] = 0x80;
            cpu.mLowerData[0x2B] = alternate ? 0x80 : 0;
            cpu.mSFR[REG_T2CON] = 0;
            cpu.mSFR[0xE8 - 0x80] = 0;
            cpu.mPC = 0x49D3;
            for (int step = 0; step < 100 && cpu.mPC != 0x49E5; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x49E5) << path;
            interpolated[alternate] = cpu.mLowerData[2];
            EXPECT_EQ((uint16_t(cpu.mSFR[REG_DPH]) << 8) |
                      cpu.mSFR[REG_DPL], 0x7200) << path;
            for (int step = 0; step < 200 && cpu.mPC != 0x4A72; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x4A72) << path;
            EXPECT_EQ(cpu.mLowerData[0x4D], interpolated[alternate]) << path;
        }
        EXPECT_EQ(interpolated, expected) << path;
    }
}

TEST(Sab80C517, PostCoolantTimer2SelectsBothRaisedCurves) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        const bool raised = rom == 1 || rom == 2;
        for (uint8_t mode : {uint8_t{1}, uint8_t{2}}) {
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mLowerData[5] = 7;
            cpu.mLowerData[6] = 0;
            cpu.mLowerData[0x57] = mode;
            cpu.mSFR[REG_T2CON] = 0x02;
            cpu.mPC = a_code ? 0x49D3 : 0x4916;
            const uint16_t read_pc = a_code ? 0x53F2 : 0x532F;
            for (int step = 0; step < 80 && cpu.mPC != read_pc; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, read_pc) << paths[rom];
            const uint16_t slot = uint16_t(0x701E + 2 * mode);
            const uint16_t base = uint16_t(code[slot] << 8 | code[slot + 1]);
            EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 | cpu.mSFR[REG_DPL]),
                      base) << paths[rom];
            const uint16_t end = a_code ? 0x49E5 : 0x4922;
            for (int step = 0; step < 80 && cpu.mPC != end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, end) << paths[rom];
            const uint8_t expected = mode == 1 ? (raised ? 0x9C : 0x82)
                                               : (raised ? 0x88 : 0x6E);
            EXPECT_EQ(code[base + 7], expected) << paths[rom];
            EXPECT_EQ(cpu.mLowerData[2], expected) << paths[rom];
        }
    }
}

TEST(Sab80C517, Pointer702aFirstCellAddsToIram4dAcrossSixRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        const bool raised = rom == 1 || rom == 2;
        for (uint8_t mode : {uint8_t{0}, uint8_t{1}, uint8_t{2}}) {
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_DPH] = 0x70;
            cpu.mSFR[REG_DPL] = 0x2A;
            cpu.mLowerData[0x57] = mode;
            cpu.mPC = a_code ? 0x4A5A : 0x4997;
            const uint16_t read_pc = a_code ? 0x4A62 : 0x499F;
            for (int step = 0; step < 50 && cpu.mPC != read_pc; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, read_pc) << paths[rom] << " mode=" << +mode;
            const uint16_t slot = uint16_t(0x702A + 2 * mode);
            const uint16_t base = uint16_t(code[slot] << 8 | code[slot + 1]);
            EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 | cpu.mSFR[REG_DPL]),
                      base) << paths[rom] << " mode=" << +mode;
            EXPECT_EQ(cpu.mSFR[REG_ACC], 0) << paths[rom] << " mode=" << +mode;
            const uint16_t end = a_code ? 0x4A72 : 0x49AF;
            for (int step = 0; step < 30 && cpu.mPC != end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, end) << paths[rom] << " mode=" << +mode;
            const uint8_t expected = mode == 0 ? (raised ? 0x29 : 0x0F)
                                               : 0x05;
            EXPECT_EQ(code[base], expected) << paths[rom] << " mode=" << +mode;
            EXPECT_EQ(cpu.mLowerData[0x4D], expected)
                << paths[rom] << " mode=" << +mode;
        }
    }
}

TEST(Sab80C517, Pointer7024ThreeCurvesAddToIram4dAcrossSixRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        for (uint8_t mode : {uint8_t{0}, uint8_t{1}, uint8_t{2}}) {
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_DPH] = 0x70;
            cpu.mSFR[REG_DPL] = 0x24;
            cpu.mLowerData[0x57] = mode;
            cpu.mPC = a_code ? 0x4A5A : 0x4997;
            const uint16_t read_pc = a_code ? 0x4A62 : 0x499F;
            for (int step = 0; step < 50 && cpu.mPC != read_pc; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, read_pc) << paths[rom] << " mode=" << +mode;
            const uint16_t slot = uint16_t(0x7024 + 2 * mode);
            const uint16_t base = uint16_t(code[slot] << 8 | code[slot + 1]);
            EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 | cpu.mSFR[REG_DPL]),
                      base) << paths[rom] << " mode=" << +mode;
            const uint16_t end = a_code ? 0x4A72 : 0x49AF;
            for (int step = 0; step < 30 && cpu.mPC != end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, end) << paths[rom] << " mode=" << +mode;
            const uint8_t expected = mode == 0 ? 0x08 : 0x03;
            EXPECT_EQ(code[base], expected) << paths[rom] << " mode=" << +mode;
            EXPECT_EQ(cpu.mLowerData[0x4D], expected)
                << paths[rom] << " mode=" << +mode;
        }
    }
}

TEST(Sab80C517, Iram6aCurveLookaheadChangesF88eAtLastIndex) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        for (uint8_t input : {uint8_t{0x82}, uint8_t{0x87}}) {
            for (uint8_t selector : {uint8_t{0}, uint8_t{1}}) {
                std::array<unsigned char, 65536> xram{};
                std::array<unsigned char, 128> upper{};
                em8051 cpu{};
                cpu.mCodeMem = code.data();
                cpu.mCodeMemMaxIdx = code.size() - 1;
                cpu.mExtData = xram.data();
                cpu.mExtDataMaxIdx = xram.size() - 1;
                cpu.mUpperData = upper.data();
                reset(&cpu, false);
                cpu.mSFR[REG_P2] = 0xF8;
                cpu.mSFR[REG_T2CON] = 0;
                cpu.mLowerData[0x6A] = input;
                cpu.mLowerData[0x2F] = selector;
                cpu.mPC = a_code ? 0x3F1F : 0x3E62;
                const uint16_t read_pc = a_code ? 0x53F2 : 0x532F;
                for (int step = 0; step < 80 && cpu.mPC != read_pc; ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, read_pc) << paths[rom];
                const uint16_t base = selector ? 0x7982 : 0x797A;
                EXPECT_EQ(uint16_t(cpu.mSFR[REG_DPH] << 8 |
                                   cpu.mSFR[REG_DPL]), base) << paths[rom];
                EXPECT_EQ(code[base + 7], 0x64) << paths[rom];
                EXPECT_EQ(code[base + 8], selector ? 0x40 : 0x03)
                    << paths[rom];
                const uint16_t end = a_code ? 0x3F3B : 0x3E7E;
                for (int step = 0; step < 120 && cpu.mPC != end; ++step) {
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_EQ(cpu.mPC, end) << paths[rom];
                const uint8_t expected = input == 0x82 ? 0x08
                    : selector ? 0x52 : 0x34;
                EXPECT_EQ(xram[0xF88E], expected)
                    << paths[rom] << " input=" << +input
                    << " selector=" << +selector;
            }
        }
    }
}

TEST(Sab80C517, CoolantFollowupCurvesSelectIram79And7BAcrossSixRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        const bool raised = rom == 1 || rom == 2;
        for (const bool timer2 : {false, true}) {
            for (const bool flag2f5 : {false, true}) {
                std::array<unsigned char, 32768> code{};
                std::array<unsigned char, 256> xram{};
                std::array<unsigned char, 128> upper{};
                em8051 cpu{};
                cpu.mCodeMem = code.data();
                cpu.mCodeMemMaxIdx = code.size() - 1;
                cpu.mExtData = xram.data();
                cpu.mExtDataMaxIdx = xram.size() - 1;
                cpu.mUpperData = upper.data();
                reset(&cpu, true);
                std::ifstream file(paths[rom], std::ios::binary);
                ASSERT_TRUE(file.is_open()) << paths[rom];
                file.read(reinterpret_cast<char *>(code.data()), code.size());
                ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
                cpu.mLowerData[5] = 3;
                cpu.mLowerData[6] = 0;
                cpu.mLowerData[0x2F] = flag2f5 ? 0x20 : 0;
                cpu.mSFR[REG_T2CON] = timer2 ? 0x02 : 0;
                cpu.mPC = a_code ? 0x4869 : 0x47AC;
                const uint16_t read_pc = a_code ? 0x53F2 : 0x532F;
                const uint16_t first_end = a_code ? 0x487D : 0x47C0;
                const uint16_t second_end = a_code ? 0x488B : 0x47CE;
                const auto run_until = [&](uint16_t pc) {
                    for (int step = 0; step < 100 && cpu.mPC != pc; ++step) {
                        cpu.mTickDelay = 0;
                        tick(&cpu);
                    }
                    return cpu.mPC == pc;
                };
                const uint16_t first_slot = !flag2f5 ? 0x703A :
                    (timer2 ? 0x7094 : 0x7038);
                const uint16_t second_slot = timer2 ? 0x70CA : 0x707C;
                const auto table_base = [&](uint16_t slot) {
                    return uint16_t((uint16_t(code[slot]) << 8) | code[slot + 1]);
                };
                ASSERT_TRUE(run_until(read_pc)) << paths[rom];
                EXPECT_EQ((uint16_t(cpu.mSFR[REG_DPH]) << 8) |
                          cpu.mSFR[REG_DPL], table_base(first_slot)) << paths[rom];
                ASSERT_TRUE(run_until(first_end)) << paths[rom];
                const uint8_t first_expected = uint8_t(
                    (!flag2f5 ? 0x93 : (timer2 ? 0x73 : 0x80)) +
                    (raised ? 0x22 : 0));
                EXPECT_EQ(code[table_base(first_slot) + 3], first_expected);
                EXPECT_EQ(cpu.mLowerData[0x79], first_expected) << paths[rom];
                ASSERT_TRUE(run_until(read_pc)) << paths[rom];
                EXPECT_EQ((uint16_t(cpu.mSFR[REG_DPH]) << 8) |
                          cpu.mSFR[REG_DPL], table_base(second_slot)) << paths[rom];
                ASSERT_TRUE(run_until(second_end)) << paths[rom];
                const uint8_t second_expected = uint8_t(
                    (timer2 ? 0x4D : 0x80) + (raised ? 0x22 : 0));
                EXPECT_EQ(code[table_base(second_slot) + 3], second_expected);
                EXPECT_EQ(cpu.mLowerData[0x7B], second_expected) << paths[rom];
            }
        }
    }
}

TEST(Sab80C517, AirLookupUpperIramCcReachesC8OnlyWhenGuardOpensInSixRoms) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        const uint16_t start = a_code ? 0x39AB : 0x397D;
        const uint16_t end = a_code ? 0x39CD : 0x399F;
        for (const auto [flag, upper_ae, upper_cc, expected] :
             {std::tuple{0x00, 0x40, 0x05, 0x10},
              std::tuple{0x04, 0x40, 0x00, 0x10},
              std::tuple{0x04, 0x40, 0x05, 0x15},
              std::tuple{0x00, 0x60, 0x05, 0x15}}) {
            SCOPED_TRACE(paths[rom].string());
            SCOPED_TRACE(::testing::Message() << "flag=" << flag
                         << " upper_ae=" << upper_ae);
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mPC = start;
            cpu.mSFR[REG_DPH] = 0x73;
            cpu.mSFR[REG_DPL] = 0x00;
            cpu.mSFR[REG_B] = 0x10;
            cpu.mLowerData[0x2F] = static_cast<unsigned char>(flag);
            upper[0xAE - 0x80] = static_cast<unsigned char>(upper_ae);
            upper[0xCC - 0x80] = static_cast<unsigned char>(upper_cc);
            for (int step = 0; step < 16 && cpu.mPC != end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, end);
            EXPECT_EQ(upper[0xC8 - 0x80], expected);
        }
    }
}

TEST(Sab80C517, Iram79And7BCurvesFeedOriginalMultiplyChains) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        const bool raised = rom == 1 || rom == 2;
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const auto table_at = [&](uint16_t slot) {
            const uint16_t base =
                uint16_t((uint16_t(code[slot]) << 8) | code[slot + 1]);
            return code[base + 3];
        };
        for (const bool use_79 : {false, true}) {
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false); // The original ROM was loaded before CPU setup.
            cpu.mSFR[REG_P2] = 0; // Select the test XRAM page for MOVX @R0.
            const uint16_t start = a_code ? (use_79 ? 0x1D1E : 0x1CD3) :
                                            (use_79 ? 0x1D02 : 0x1CB7);
            const uint16_t end = a_code ? (use_79 ? 0x1D39 : 0x1CFE) :
                                          (use_79 ? 0x1D1D : 0x1CE2);
            cpu.mPC = start;
            if (use_79) {
                cpu.mLowerData[0x79] = table_at(0x7038);
                cpu.mSFR[REG_ACC] = 0x80; // Result entering from prior lookup.
                xram[0] = 0x80;
                xram[2] = 0x80;
            } else {
                cpu.mLowerData[0x7B] = table_at(0x707C);
                cpu.mLowerData[0x7A] = 0x80;
                xram[1] = 0x80;
                xram[0xFB] = 0x80;
            }
            for (int step = 0; step < 80 && cpu.mPC != end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, end) << paths[rom];
            if (use_79)
                EXPECT_EQ(cpu.mSFR[REG_B], raised ? 0x15 : 0x10)
                    << paths[rom];
            else
                EXPECT_EQ(cpu.mLowerData[1], raised ? 0x0A : 0x08)
                    << paths[rom];
        }
    }
}

TEST(Sab80C517, F801MatrixConsumerDependsOnNonzeroIram7A) {
    std::array<unsigned char, 32768> code{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(code.data()), code.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));

    std::array<std::array<uint8_t, 2>, 2> results{};
    for (size_t gate = 0; gate < results.size(); ++gate) {
        for (size_t source = 0; source < results[gate].size(); ++source) {
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mSFR[REG_P2] = 0;
            cpu.mLowerData[0x7A] = gate == 0 ? 0 : 0x80;
            cpu.mLowerData[0x7B] = 0x78;
            xram[1] = source == 0 ? 0x61 : 0x89;
            xram[0xFB] = 0xFF;
            cpu.mPC = 0x1CB7;
            for (int step = 0; step < 80 && cpu.mPC != 0x1CE2; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x1CE2);
            // SAB80C517 Instruction Set, MOVX and MUL AB: original G
            // opcodes at 1CB7h..1CDFh consume XRAM[01h] and IRAM[7Ah].
            results[gate][source] = cpu.mLowerData[1];
        }
    }
    EXPECT_EQ(results[0][0], 0);
    EXPECT_EQ(results[0][1], 0);
    EXPECT_LT(results[1][0], results[1][1]);
}

TEST(Sab80C517, SixRomF8fbReaderFeedsRam7aMultiplyChain) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const bool a_code = rom != 0 && rom != 3;
        std::array<std::array<uint8_t, 2>, 2> results{};
        for (size_t gate = 0; gate < 2; ++gate) {
            for (size_t field = 0; field < 2; ++field) {
                std::array<unsigned char, 65536> xram{};
                std::array<unsigned char, 128> upper{};
                em8051 cpu{};
                cpu.mCodeMem = code.data();
                cpu.mCodeMemMaxIdx = code.size() - 1;
                cpu.mExtData = xram.data();
                cpu.mExtDataMaxIdx = xram.size() - 1;
                cpu.mUpperData = upper.data();
                reset(&cpu, false);
                cpu.mSFR[REG_P2] = 0xF8;
                cpu.mLowerData[0x7A] = gate ? 0x80 : 0;
                cpu.mLowerData[0x7B] = 0x78;
                xram[0xF801] = 0x61;
                xram[0xF8FB] = field ? 0xFF : 0;
                cpu.mPC = a_code ? 0x1CD3 : 0x1CB7;
                const uint16_t finish = a_code ? 0x1CFE : 0x1CE2;
                bool read_f8fb = false;
                for (int step = 0; step < 40 && cpu.mPC != finish; ++step) {
                    if (cpu.mPC == (a_code ? 0x1CE1 : 0x1CC5)) {
                        read_f8fb = true;
                        EXPECT_EQ(cpu.mLowerData[0], 0xFB) << paths[rom];
                    }
                    cpu.mTickDelay = 0;
                    tick(&cpu);
                }
                ASSERT_TRUE(read_f8fb) << paths[rom];
                ASSERT_EQ(cpu.mPC, finish) << paths[rom];
                results[gate][field] = cpu.mLowerData[1];
            }
        }
        EXPECT_EQ(results[0][0], 0) << paths[rom];
        EXPECT_EQ(results[0][1], 0) << paths[rom];
        EXPECT_EQ(results[1][0], 0) << paths[rom];
        EXPECT_GT(results[1][1], 0) << paths[rom];
    }
}

TEST(Sab80C517, SixRom78bdBranchWritesSelectedCellToF801) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        const bool raised_cells = rom == 1 || rom == 2;
        for (const bool select_78bd : {false, true}) {
            SCOPED_TRACE(paths[rom].string());
            SCOPED_TRACE(select_78bd ? "78BD" : "7895");
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mPC = a_code ? 0x3ED1 : 0x3E14;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_T2CON] = 0;
            cpu.mLowerData[0x2C] = select_78bd ? 0x10 : 0;
            cpu.mLowerData[0x2F] = 0;
            cpu.mLowerData[0] = 4; // Table stride.
            cpu.mLowerData[4] = 0; // No row interpolation.
            cpu.mLowerData[5] = 2; // Row zero, column two.
            cpu.mLowerData[6] = 0; // No column interpolation.
            const uint16_t end = a_code ? 0x3EF1 : 0x3E34;
            for (int step = 0; step < 160 && cpu.mPC != end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, end);
            const uint16_t slot = select_78bd ? 0x7084 : 0x7080;
            const uint16_t base = static_cast<uint16_t>(
                (static_cast<uint16_t>(code[slot]) << 8) | code[slot + 1]);
            EXPECT_EQ(xram[0xF801], code[base + 2]);
            EXPECT_EQ(xram[0xF801],
                      (raised_cells ? 0xA8 : 0x80) + (select_78bd ? 1 : 0));
        }
    }
}

TEST(Sab80C517, SixRomCc3LowerGatePublishesZeroBelowBound) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        ASSERT_EQ(code[0x7218], 0);
        ASSERT_EQ(code[0x7219], 0xC8);
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        for (const auto [candidate, x08, xef, flag, expected] : {
                 std::tuple{0x5A, 0x61, 0x00, 0x00, 0x00},
                 std::tuple{0x5A, 0xE1, 0x00, 0x00, 0xC8},
                 std::tuple{0x5A, 0x61, 0x01, 0x01, 0xC8},
                 std::tuple{0x5A, 0x61, 0x01, 0x00, 0x00},
                 std::tuple{0xE2, 0x61, 0x00, 0x00, 0xE2}}) {
            SCOPED_TRACE(paths[rom].string());
            SCOPED_TRACE(::testing::Message() << "candidate="
                         << static_cast<unsigned>(candidate));
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mPC = a_code ? 0x1EC5 : 0x1EA9;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_DPH] = 0x72;
            cpu.mSFR[REG_DPL] = 0;
            cpu.mSFR[REG_ACC] = 0;
            cpu.mLowerData[2] = static_cast<uint8_t>(candidate);
            cpu.mLowerData[0x2F] = static_cast<uint8_t>(flag);
            xram[0xF808] = static_cast<uint8_t>(x08);
            xram[0xF8EF] = static_cast<uint8_t>(xef);
            const uint16_t end = a_code ? 0x1EF5 : 0x1ED9;
            for (int step = 0; step < 50 && cpu.mPC != end; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, end);
            EXPECT_EQ(cpu.mLowerData[0x14], 0);
            EXPECT_EQ(cpu.mLowerData[0x15], expected);
            EXPECT_EQ((cpu.mLowerData[0x25] & 1u) != 0, candidate == 0x5A);
        }
    }
}

TEST(Sab80C517, SixRomResetPrefixConfiguresSamePortsAndSyscon) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (const auto &path : paths) {
        SCOPED_TRACE(path.string());
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open());
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, false);
        for (int step = 0; step < 2000 && cpu.mPC != 0x0883; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x0883);
        // SAB80C517 User's Manual, SFR and port map: these values come
        // from the original reset opcodes, before the XRAM self-test.
        EXPECT_EQ(cpu.mSFR[REG_P1], 0xFB);
        EXPECT_EQ(cpu.mSFR[REG_P2], 0xF8);
        // The shared CLR T0 at 0880h clears P3.4 after MOV P3,#F7h.
        EXPECT_EQ(cpu.mSFR[REG_P3], 0xE7);
        EXPECT_EQ(cpu.mSFR[0xE8 - 0x80], 0xEA); // P4.
        EXPECT_EQ(cpu.mSFR[0xF8 - 0x80], 0x0F); // P5.
        EXPECT_EQ(cpu.mSFR[REG_SP], 0xD0);
        EXPECT_EQ(cpu.mSFR[REG_SYSCON], 0x02);
    }
}

TEST(Sab80C517, SixRomXramSelfTestReachesCommonBootContinuation) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    std::array<uint8_t, 9> reference{};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        SCOPED_TRACE(paths[rom].string());
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open());
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, false);
        for (int step = 0; step < 100000 && cpu.mPC != 0x0A3A; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x0A3A);
        EXPECT_EQ(xram[0xF891], 0xAA);
        const std::array<uint8_t, 9> snapshot{
            cpu.mSFR[REG_P1], cpu.mSFR[REG_P2], cpu.mSFR[REG_P3],
            cpu.mSFR[0xE8 - 0x80], cpu.mSFR[0xF8 - 0x80],
            cpu.mSFR[REG_SP], cpu.mSFR[REG_SYSCON],
            cpu.mLowerData[0x2B], cpu.mLowerData[0x2E]};
        if (rom == 0)
            reference = snapshot;
        else
            EXPECT_EQ(snapshot, reference);
        // SAB80C517 MOVX @R0: this path tests external RAM before
        // continuing at 0A3Ah; it does not validate external wiring.
        EXPECT_EQ(xram[0xF8FF], 0xFF);
        for (int step = 0; step < 10000 && cpu.mPC != 0x0B30; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x0B30);
        // Original MOVC/MOVX opcodes copy each image's own tail bytes.
        const std::array<uint16_t, 10> xram_destinations{
            0xF80F, 0xF81E, 0xF849, 0xF84A, 0xF863,
            0xF864, 0xF83F, 0xF84D, 0xF88F, 0xF8DE};
        for (size_t index = 0; index < xram_destinations.size(); ++index)
            EXPECT_EQ(xram[xram_destinations[index]], code[0x7FF6 + index]);
        EXPECT_EQ(xram[0xF8FF], 0);
        EXPECT_EQ(xram[0xF891], 0);
        EXPECT_EQ(cpu.mSFR[REG_PCON], 0);
        EXPECT_EQ(cpu.mSFR[REG_SCON], 0x91);
        EXPECT_EQ(cpu.mSFR[REG_TMOD], 0x11);
        EXPECT_EQ(cpu.mSFR[REG_TCON], 0x15);
        EXPECT_EQ(cpu.mSFR[REG_T2CON], 0x85);
        EXPECT_EQ(cpu.mSFR[REG_CCEN], 0x01);
        EXPECT_EQ(cpu.mSFR[REG_IP0], 0x39);
        EXPECT_EQ(cpu.mSFR[REG_IP1], 0x0C);
        EXPECT_EQ(cpu.mSFR[REG_IEN0], 0xA2);
        EXPECT_EQ(cpu.mSFR[REG_IEN1], 0x30);
        // Continue with each original ROM past initialization. This checks
        // code reachability on an isolated C517A CPU, not Fiat board wiring.
        for (int step = 0; step < 300000 && cpu.mPC != 0x11C4; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        EXPECT_EQ(cpu.mPC, 0x11C4);
    }
}

TEST(Sab80C517, SixRomTpsFallbackMovcReadsOriginalByte) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (const auto &path : paths) {
        SCOPED_TRACE(path.string());
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(path, std::ios::binary);
        ASSERT_TRUE(file.is_open());
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, false);
        cpu.mSFR[REG_PSW] = 0;
        cpu.mSFR[REG_DPH] = 0x72;
        cpu.mSFR[REG_DPL] = 0x00;
        cpu.mPC = 0x116D;
        for (int step = 0; step < 3; ++step) {
            cpu.mTickDelay = 0;
            tick(&cpu);
        }
        EXPECT_EQ(cpu.mPC, 0x1171);
        EXPECT_EQ(cpu.mLowerData[4], 0x34); // R4 in register bank 0.
        EXPECT_EQ(code[0x72A1], 0x34);
    }
}

TEST(Sab80C517, SixRomTailBytesGuardXramIntegrity) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" / "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    const std::array<uint16_t, 9> xram_addresses{
        0xF81E, 0xF849, 0xF84A, 0xF863, 0xF864,
        0xF83F, 0xF84D, 0xF88F, 0xF8DE};
    for (size_t rom = 0; rom < paths.size(); ++rom) {
        std::array<unsigned char, 32768> code{};
        std::ifstream file(paths[rom], std::ios::binary);
        ASSERT_TRUE(file.is_open()) << paths[rom];
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
        const uint16_t start = a_code ? 0x4AF4 : 0x4A31;
        const uint16_t match = a_code ? 0x4B88 : 0x4AC5;
        const uint16_t reset_entry = 0x0850;
        for (size_t changed = 0; changed <= xram_addresses.size(); ++changed) {
            SCOPED_TRACE(paths[rom].string());
            SCOPED_TRACE(::testing::Message() << "changed=" << changed);
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mPC = start;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_SP] = 0x40;
            for (size_t index = 0; index < xram_addresses.size(); ++index)
                xram[xram_addresses[index]] = code[0x7FF7 + index];
            if (changed < xram_addresses.size())
                xram[xram_addresses[changed]] ^= 1u;
            for (int step = 0; step < 200 && cpu.mPC != match &&
                               cpu.mPC != reset_entry; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            EXPECT_EQ(cpu.mPC, changed == xram_addresses.size() ?
                                match : reset_entry);
        }
        for (const auto [ram47, ram48, expected] :
             {std::tuple<uint8_t, uint8_t, uint16_t>{0x01, 0x00, match},
              {0x96, 0x20, reset_entry},
              {0x96, 0x21, match}}) {
            SCOPED_TRACE(paths[rom].string());
            SCOPED_TRACE(::testing::Message() << "IRAM47=" << int(ram47)
                                              << " IRAM48=" << int(ram48));
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, false);
            cpu.mPC = start;
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_SP] = 0x40;
            cpu.mLowerData[0x47] = ram47;
            cpu.mLowerData[0x48] = ram48;
            for (size_t index = 0; index < xram_addresses.size(); ++index)
                xram[xram_addresses[index]] = code[0x7FF7 + index];
            xram[xram_addresses[0]] ^= 1u;
            for (int step = 0; step < 200 && cpu.mPC != match &&
                               cpu.mPC != reset_entry; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            EXPECT_EQ(cpu.mPC, expected);
        }
    }
}

TEST(Sab80C517, Sun36Iex3VectorLeaves32KiBRom) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const auto variants = root / "firmwares_modificados_ma17_tipo";
    for (const auto [filename, expected] :
         {std::pair{"tipo 1.6 alcool27c256 SUN 37a5.bin", uint16_t{0x00B0}},
          {"tipo 1.6 alcool27c256 SUN 36fd.bin", uint16_t{0xAA0D}}}) {
        SCOPED_TRACE(filename);
        std::array<unsigned char, 32768> code{};
        std::ifstream file(variants / filename, std::ios::binary);
        ASSERT_TRUE(file.is_open());
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        std::array<unsigned char, 65536> xram{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        reset(&cpu, false);
        cpu.mPC = 0x1000;
        cpu.mSFR[REG_IEN0] = IEN0MASK_EA;
        cpu.mSFR[REG_IEN1] = IEN1MASK_EX3;
        cpu.mSFR[REG_IP1] = 0x04; // Boot configures IEX3 priority group 2.
        cpu.mSFR[REG_IRCON] = IRCONMASK_IEX3;
        tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x0053);
        EXPECT_EQ(cpu.mSFR[REG_IRCON] & IRCONMASK_IEX3, 0);
        for (int step = 0; step < 8 && cpu.mPC == 0x0053; ++step)
            tick(&cpu);
        EXPECT_EQ(cpu.mPC, expected);
        EXPECT_EQ(code[expected & 0x7FFF], expected == 0xAA0D ? 0x38 : 0xD5);
    }
}

TEST(Sab80C517, AlcoholGateFactorTableRaisesIram87WithSameIndex) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256+1.5bar.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 36fd.bin"};
    for (const uint8_t index : {uint8_t{0x20}, uint8_t{0x33},
                                uint8_t{0xC1}}) {
        std::array<uint8_t, 6> outputs{};
        for (size_t rom = 0; rom < paths.size(); ++rom) {
            const bool a_code = rom == 1 || rom == 2 || rom == 4 || rom == 5;
            const bool a_calibration = rom == 1 || rom == 2;
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 256> xram{};
            std::array<unsigned char, 128> upper{};
            std::ifstream file(paths[rom], std::ios::binary);
            ASSERT_TRUE(file.is_open()) << paths[rom];
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = 32767;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = 255;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            cpu.mSFR[REG_PSW] = 0x08;
            cpu.mSFR[REG_SP] = 0x40;
            cpu.mLowerData[0x0D] = index & 0x0F; // R5 from 5639h/56FCh.
            cpu.mLowerData[0x0E] = index & 0xF0; // R6 from 5639h/56FCh.
            cpu.mPC = 0x12BE;
            for (int step = 0; step < 100 && cpu.mPC != 0x12CD; ++step)
                tick(&cpu);
            ASSERT_EQ(cpu.mPC, 0x12CD) << paths[rom];
            outputs[rom] = cpu.mUpperData[0x87 - 0x80];
            if (index == 0x20) {
                cpu.mSFR[REG_DPH] = 0x72;
                cpu.mSFR[REG_DPL] = 0x00;
                cpu.mLowerData[0x1A] = 0x0A; // ROM[7204h] modulo period.
                cpu.mLowerData[0x2D] = 0x20;
                cpu.mLowerData[0x2E] = 0xA4;
                cpu.mLowerData[0x4E] = index;
                cpu.mLowerData[0x08] = 0x00; // Do not reuse 12BEh's R0=87h.
                const uint16_t gate_mul = a_code ? 0x15A8 : 0x155A;
                const uint16_t gate_end = a_code ? 0x15B0 : 0x1562;
                cpu.mPC = a_code ? 0x1588 : 0x153A;
                for (int step = 0; step < 500 && cpu.mPC != gate_mul; ++step)
                    tick(&cpu);
                ASSERT_EQ(cpu.mPC, gate_mul) << paths[rom];
                EXPECT_EQ(cpu.mUpperData[0x87 - 0x80], outputs[rom]);
                for (int step = 0; step < 20 && cpu.mPC != gate_end; ++step)
                    tick(&cpu);
                ASSERT_EQ(cpu.mPC, gate_end) << paths[rom];
                EXPECT_EQ(cpu.mLowerData[0x2E] & 0x04,
                          a_calibration ? 0x04 : 0x00);
            }
        }
        if (index == 0x20) {
            EXPECT_EQ(outputs[0], 0);
            EXPECT_GE(outputs[1], 2);
        } else {
            EXPECT_EQ(outputs[1] - outputs[0], 0x10)
                << "IRAM[4Eh]=" << int(index);
        }
        EXPECT_EQ(outputs[2], outputs[1]);
        for (const size_t rom : {size_t{3}, size_t{4}, size_t{5}})
            EXPECT_EQ(outputs[rom], outputs[0]) << paths[rom];
    }
}

TEST(Sab80C517, FiatMatrixDeltaPersistsAcrossRpmAndTpsLookupStates) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        std::filesystem::path(MA17_ROM_PATH),
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 8817.bin"};
    struct State {
        const char *name;
        uint8_t g_r5, g_r6, s_r5, s_r6, r4;
        uint16_t expected_g, expected_s;
    };
    constexpr std::array states{
        State{"750 rpm", 0x2E, 0xB0, 0x31, 0x10, 0xC0, 0x4980, 0x42C0},
        State{"2000 rpm", 0x33, 0x80, 0x34, 0xD0, 0xC0, 0x2040, 0x3340},
        State{"TPS 40/95", 0x5D, 0x00, 0x5F, 0x10, 0x40, 0x5B40, 0x5640},
        State{"TPS 120/180", 0x8A, 0x00, 0x8C, 0x10, 0x00, 0xA100, 0xA250},
    };
    const auto evaluate = [&](size_t rom, uint8_t r5, uint8_t r6,
                              uint8_t r4) -> uint16_t {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        std::ifstream file(paths[rom], std::ios::binary);
        EXPECT_TRUE(file.is_open()) << paths[rom];
        if (!file.is_open()) return 0;
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        file.read(reinterpret_cast<char *>(code.data()), code.size());
        EXPECT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
        if (file.gcount() != static_cast<std::streamsize>(code.size())) return 0;
        cpu.mSFR[REG_DPH] = 0x75;
        cpu.mSFR[REG_DPL] = 0x81;
        cpu.mLowerData[0] = 0x0F;
        cpu.mLowerData[4] = r4;
        cpu.mLowerData[5] = r5;
        cpu.mLowerData[6] = r6;
        cpu.mSFR[REG_ACC] = r5;
        cpu.mPC = 0x532F;
        const uint16_t stop_pc = r4 ? 0x5366 : 0x5348;
        for (int step = 0; step < 100 && cpu.mPC != stop_pc; ++step)
            tick(&cpu);
        EXPECT_EQ(cpu.mPC, stop_pc);
        return uint16_t(cpu.mSFR[REG_ACC] << 8 | cpu.mSFR[REG_B]);
    };
    for (const auto &state : states) {
        const auto g_g = evaluate(0, state.g_r5, state.g_r6, state.r4);
        const auto s_g = evaluate(1, state.g_r5, state.g_r6, state.r4);
        const auto g_s = evaluate(0, state.s_r5, state.s_r6, state.r4);
        const auto s_s = evaluate(1, state.s_r5, state.s_r6, state.r4);
        EXPECT_EQ(g_g, state.expected_g) << state.name;
        EXPECT_EQ(s_s, state.expected_s) << state.name;
        EXPECT_EQ(s_g - g_g, 0x1500) << state.name;
        EXPECT_EQ(s_s - g_s, 0x1500) << state.name;
    }
}

TEST(Sab80C517, FirmwareKlineFrameValidatorChecksCounterAndTerminator) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    struct Case {
        uint8_t counter;
        uint8_t terminator;
        uint8_t request;
        uint8_t expected_state;
    };
    constexpr std::array cases{
        Case{0x02, 0x03, 0x12, 0x0B},
        Case{0x02, 0x03, 0x11, 0x0A},
        Case{0x03, 0x03, 0x12, 0x04},
        Case{0x02, 0x00, 0x12, 0x04},
    };
    for (const auto &test : cases) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_P2] = 0;
        cpu.mLowerData[0x40] = 1;
        cpu.mLowerData[0x44] = 0xBB;
        xram[0xB9] = test.counter;
        xram[0xBA] = test.request;
        xram[0xBB] = test.terminator;
        cpu.mPC = 0x5058;
        for (int step = 0; step < 80 && cpu.mPC != 0x510C; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x510C);
        EXPECT_EQ(cpu.mLowerData[0x42], test.expected_state);
        if (test.expected_state != 0x04) {
            EXPECT_EQ(cpu.mLowerData[2], test.request);
            EXPECT_EQ(cpu.mLowerData[0x40], 2);
        }
    }
}

TEST(Sab80C517, FirmwareKlineCommandTailSelectsDiagnosticStates) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    for (const auto [command, state] : {
             std::pair{0x07, 0x09}, std::pair{0x05, 0x03},
             std::pair{0x12, 0x0B}, std::pair{0x13, 0x04}}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        xram.fill(0xA5);
        cpu.mSFR[REG_P2] = 0;
        cpu.mLowerData[2] = static_cast<unsigned char>(command);
        cpu.mLowerData[0x41] = 0x7F;
        cpu.mPC = 0x50E0;
        for (int step = 0; step < 130 && cpu.mPC != 0x510C; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x510C) << "command=" << command;
        EXPECT_EQ(cpu.mLowerData[0x42], state);
        if (command == 0x05) {
            for (const auto address : {0x4E, 0x50, 0x60, 0x84, 0x86, 0xD0, 0xD1})
                EXPECT_EQ(xram[static_cast<std::size_t>(address)], 0)
                    << "address=" << address;
            EXPECT_NE(cpu.mLowerData[0x20] & 0x40, 0);
        }
        if (command == 0x12) {
            cpu.mPC = 0x4C06; // Dispatch the selected state 0Bh.
            for (int step = 0; step < 30 && cpu.mPC != 0x4ECB; ++step)
                tick(&cpu);
            ASSERT_EQ(cpu.mPC, 0x4ECB);
            for (int step = 0; step < 150 && cpu.mPC != 0x4C53; ++step)
                tick(&cpu);
            ASSERT_EQ(cpu.mPC, 0x4C53);
            EXPECT_EQ(xram[0xB8], 0x0D);
            EXPECT_EQ(xram[0xB9], 0x01);
            EXPECT_EQ(xram[0xBA], 0xF4);
            for (std::size_t slot = 0; slot < 10; ++slot)
                EXPECT_EQ(xram[0xBB + slot], 0) << "slot=" << slot;
            EXPECT_EQ(xram[0xC5], 0x03);
        }
    }
}

TEST(Sab80C517, FiatKlineCommand04RequiresStoppedRpmFlagAndCyclesCounter) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    struct Case { uint8_t stopped_flag; uint8_t counter; uint8_t state; uint8_t next; };
    constexpr std::array cases{Case{0, 0, 4, 0}, Case{1, 0, 6, 8},
                               Case{1, 2, 6, 1}, Case{1, 1, 3, 0}};
    for (const auto &test : cases) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = code.size() - 1;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = xram.size() - 1;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mSFR[REG_SP] = 0x40;
        cpu.mSFR[REG_P2] = 0;
        cpu.mLowerData[2] = 0x04;
        upper[0x0A] = test.stopped_flag;
        upper[0x09] = 0x20;
        xram[0xC8] = test.counter;
        xram[0xCA] = 0x55;
        cpu.mPC = 0x50BB;
        for (int step = 0; step < 100 && cpu.mPC != 0x510C; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x510C) << int(test.stopped_flag) << "/"
                                       << int(test.counter);
        EXPECT_EQ(cpu.mLowerData[0x42], test.state);
        EXPECT_EQ(xram[0xC8], test.next);
        EXPECT_EQ(xram[0xCA], test.stopped_flag ? 0 : 0x55);
        if (test.state == 3)
            EXPECT_EQ(upper[0x09] & 0x20, 0);
        if (test.state == 6) {
            cpu.mPC = 0x4C06; // Dispatch state 06h into the F5h response.
            for (int step = 0; step < 100 && cpu.mPC != 0x4F61; ++step)
                tick(&cpu);
            ASSERT_EQ(cpu.mPC, 0x4F61);
            EXPECT_EQ(xram[0xB8], 0x05);
            EXPECT_EQ(xram[0xBA], 0xF5);
            const uint8_t payload = test.next == 8 ? 0x11 : 0x77;
            EXPECT_EQ(xram[0xBB], payload);
            EXPECT_EQ(xram[0xBC], payload);
            EXPECT_EQ(upper[0x0A] & 0x02, 0x02);
        }
    }
}

TEST(Sab80C517, FirmwareFaultTripletReadersUseOriginalRom) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    struct Case {
        uint16_t entry;
        uint16_t stop;
        uint8_t index;
        uint8_t offset;
        std::array<unsigned char, 3> expected;
    };
    constexpr std::array cases{
        Case{0x4329, 0x4342, 1, 0, {0x02, 0x04, 0x1D}},
        Case{0x4329, 0x4342, 2, 0, {0x02, 0x04, 0x1E}},
        Case{0x4329, 0x4342, 9, 9, {0x02, 0x06, 0x1F}},
        Case{0x4329, 0x4342, 12, 9, {0x02, 0x0A, 0x1E}},
        Case{0x44BB, 0x44D7, 2, 0, {0x02, 0x04, 0x9E}},
        Case{0x44BB, 0x44D7, 9, 9, {0x02, 0x06, 0x9F}},
    };
    for (const auto &test : cases) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mPC = test.entry;
        cpu.mSFR[REG_DPH] = 0x6E; // The second entry inherits DPTR.
        cpu.mSFR[REG_DPL] = 0x27;
        cpu.mLowerData[test.entry == 0x4329 ? 3 : 6] = test.index;
        cpu.mLowerData[7] = test.offset;
        for (int step = 0; step < 100 && cpu.mPC != test.stop; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, test.stop) << "entry=" << test.entry;
        for (std::size_t byte = 0; byte < 3; ++byte)
            EXPECT_EQ(xram[0xCD + byte], test.expected[byte])
                << "entry=" << test.entry << " byte=" << byte;

        cpu.mPC = 0x4DFB; // Stage the selected triplet as an FC response.
        cpu.mTickDelay = 0;
        for (int step = 0; step < 200 && cpu.mPC != 0x4C53; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x4C53) << "entry=" << test.entry;
        EXPECT_EQ(xram[0xB8], 0x06);
        EXPECT_EQ(xram[0xB9], 0x01);
        EXPECT_EQ(xram[0xBA], 0xFC);
        for (std::size_t byte = 0; byte < 3; ++byte)
            EXPECT_EQ(xram[0xBB + byte], test.expected[byte]);
        EXPECT_EQ(xram[0xBE], 0x03);

        cpu.mPC = 0x4FA3; // Send the first staged byte through S0BUF.
        cpu.mTickDelay = 0;
        cpu.mLowerData[0] = 0x3F; // R0 from the serial state dispatcher.
        cpu.mLowerData[0x41] = 1;
        cpu.mLowerData[0x44] = 0xB8;
        for (int step = 0; step < 1000 && cpu.mPC != 0x4C7D; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x4C7D) << "entry=" << test.entry;
        EXPECT_EQ(cpu.mSFR[REG_SBUF], 0x06);
        EXPECT_EQ(cpu.mLowerData[0x45], 0x06);
        EXPECT_EQ(cpu.mLowerData[0x44], 0xB9);
    }

    std::array<unsigned char, 32768> code{};
    std::array<unsigned char, 256> xram{};
    std::array<unsigned char, 128> upper{};
    em8051 cpu{};
    cpu.mCodeMem = code.data();
    cpu.mCodeMemMaxIdx = 32767;
    cpu.mExtData = xram.data();
    cpu.mExtDataMaxIdx = 255;
    cpu.mUpperData = upper.data();
    reset(&cpu, true);
    std::copy(original.begin(), original.end(), code.begin());
    cpu.mLowerData[0x28] = 0x40;
    xram[0x85] = 0x40; // Previously sampled flag must persist.
    cpu.mLowerData[0] = 0x84;
    cpu.mPC = 0x4081;
    for (int step = 0; step < 20 && cpu.mPC != 0x4086; ++step)
        tick(&cpu);
    ASSERT_EQ(cpu.mPC, 0x4086);
    EXPECT_EQ(cpu.mLowerData[6], 0x40);
    cpu.mPC = 0x41F3;
    cpu.mTickDelay = 0;
    for (int step = 0; step < 30 && cpu.mPC != 0x4201; ++step)
        tick(&cpu);
    ASSERT_EQ(cpu.mPC, 0x4201);
    EXPECT_EQ(xram[0x4F], 0x40);
    cpu.mLowerData[3] = 0x0F; // Fifteenth fault bit: XRAM 4Fh.6.
    cpu.mPC = 0x4414;
    for (int step = 0; step < 40 && cpu.mPC != 0x430E; ++step)
        tick(&cpu);
    ASSERT_EQ(cpu.mPC, 0x430E);
    EXPECT_EQ(cpu.mLowerData[7], 9);
    EXPECT_EQ(cpu.mLowerData[0], 0x4F);
    upper[0x89 - 0x80] = 0x10;
    cpu.mSFR[REG_DPH] = 0x6E;
    cpu.mSFR[REG_DPL] = 0x27;
    for (int step = 0; step < 120 && cpu.mPC != 0x4342; ++step)
        tick(&cpu);
    ASSERT_EQ(cpu.mPC, 0x4342);
    EXPECT_EQ(xram[0xCD], 0x02);
    EXPECT_EQ(xram[0xCE], 0x0B);
    EXPECT_EQ(xram[0xCF], 0x1E);
}

TEST(Sab80C517, FirmwareTpsFlagsSelectFaultCode0602) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    struct Case {
        unsigned char flag;
        unsigned char index;
        unsigned char status;
    };
    constexpr std::array cases{Case{0x02, 0x0A, 0x1D}, Case{0x04, 0x0B, 0x1E}};
    for (const auto [flag, index, status] : cases) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mLowerData[0x28] = flag;
        xram[0x85] = flag; // The previous fault snapshot must retain this bit.
        cpu.mLowerData[0] = 0x84;
        cpu.mPC = 0x4081;
        for (int step = 0; step < 20 && cpu.mPC != 0x4086; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x4086);
        EXPECT_EQ(cpu.mLowerData[6], flag);
        cpu.mPC = 0x41F3;
        cpu.mTickDelay = 0;
        for (int step = 0; step < 30 && cpu.mPC != 0x4201; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x4201);
        EXPECT_EQ(xram[0x4F], flag);
        cpu.mLowerData[3] = index;
        cpu.mPC = 0x4414;
        for (int step = 0; step < 40 && cpu.mPC != 0x430E; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x430E);
        EXPECT_EQ(cpu.mLowerData[7], 9);
        EXPECT_EQ(cpu.mLowerData[0], 0x4F);
        upper[0x89 - 0x80] = 0x10;
        cpu.mSFR[REG_DPH] = 0x6E;
        cpu.mSFR[REG_DPL] = 0x27;
        for (int step = 0; step < 120 && cpu.mPC != 0x4342; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x4342);
        EXPECT_EQ(xram[0xCD], 0x02);
        EXPECT_EQ(xram[0xCE], 0x06);
        EXPECT_EQ(xram[0xCF], status);
    }
}

TEST(Sab80C517, FiatTpsPriorBBitPersistsAtHighInputs) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    for (const unsigned char previous_b :
         std::array<unsigned char, 2>{0x00, 0x10}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 65535;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        // Siemens SAB80C517 Instruction Set: execute the original CJNE,
        // bit and MOVX opcodes; no substitute ROM bytes or forced branch.
        cpu.mPC = 0x10B1;
        cpu.mSFR[REG_P2] = 0xF8;
        cpu.mSFR[REG_XPAGE] = 0xF8; // C517A MOVX @R0 page.
        cpu.mSFR[REG_B] = previous_b;
        cpu.mLowerData[2] = 0xB4;
        cpu.mLowerData[4] = 0xF7;
        cpu.mLowerData[0x28] = 0x06;
        cpu.mLowerData[0x6D] = 0x30;
        bool saw_1132 = false;
        unsigned char flags_at_1159 = 0xFF;
        for (int step = 0; step < 500 && cpu.mPC != 0x115F; ++step) {
            saw_1132 |= cpu.mPC == 0x1132;
            if (cpu.mPC == 0x1159)
                flags_at_1159 = cpu.mLowerData[0x28];
            tick(&cpu);
        }
        ASSERT_EQ(cpu.mPC, 0x115F);
        EXPECT_TRUE(saw_1132);
        EXPECT_EQ(flags_at_1159 & 0x06,
                  previous_b == 0x10 ? 0x06 : 0x00);
        EXPECT_EQ(cpu.mSFR[REG_B], previous_b);
        EXPECT_EQ(cpu.mLowerData[0x28] & 0x06,
                  previous_b == 0x10 ? 0x06 : 0x00);
    }
}

TEST(Sab80C517, FirmwareSensorCollectionTablesSelectIramOrXram) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    struct Case {
        uint8_t table_low;
        std::array<unsigned char, 10> expected;
    };
    constexpr std::array cases{
        Case{0x78, {0x11, 0x12, 0x13, 0x14, 0x21,
                    0x22, 0x23, 0x24, 0x15, 0x25}},
        Case{0x8C, {0x11, 0x12, 0x16, 0x17, 0x26,
                    0x22, 0x23, 0x27, 0x15, 0x25}},
    };
    for (const auto &test : cases) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 65536> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 65535;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        for (const auto [address, value] : {
                 std::pair{0x63, 0x11}, std::pair{0x66, 0x12},
                 std::pair{0x47, 0x13}, std::pair{0x62, 0x14},
                 std::pair{0x61, 0x15}, std::pair{0x70, 0x16},
                 std::pair{0x2F, 0x17}})
            cpu.mLowerData[address] = static_cast<unsigned char>(value);
        for (const auto [address, value] : {
                 std::pair{0x0C, 0x21}, std::pair{0x6C, 0x22},
                 std::pair{0x6F, 0x23}, std::pair{0x3D, 0x24},
                 std::pair{0x69, 0x25}, std::pair{0x72, 0x26},
                 std::pair{0x40, 0x27}})
            xram[0xF800 + static_cast<std::size_t>(address)] =
                static_cast<unsigned char>(value);
        cpu.mSFR[REG_P2] = 0xF8;
        cpu.mSFR[REG_XPAGE] = 0xF8;
        cpu.mSFR[REG_DPH] = 0x6E;
        cpu.mSFR[REG_DPL] = test.table_low;
        cpu.mLowerData[1] = 0xBB;
        cpu.mLowerData[7] = 10;
        cpu.mPC = 0x4EAF;
        for (int step = 0; step < 300 && cpu.mPC != 0x4EC7; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x4EC7) << "table=" << static_cast<int>(test.table_low);
        for (std::size_t slot = 0; slot < test.expected.size(); ++slot)
            EXPECT_EQ(xram[0xF8BB + slot], test.expected[slot])
                << "table=" << static_cast<int>(test.table_low) << " slot=" << slot;

        upper[0xB3 - 0x80] = test.table_low == 0x8C ? 0x01 : 0x02;
        cpu.mLowerData[0x40] = 0;
        cpu.mPC = 0x4ECB;
        for (int step = 0; step < 300 && cpu.mPC != 0x4C53; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x4C53);
        EXPECT_EQ(xram[0xF8B8], 0x0D);
        EXPECT_EQ(xram[0xF8B9], 0x01);
        EXPECT_EQ(xram[0xF8BA], 0xF4);
        for (std::size_t slot = 0; slot < test.expected.size(); ++slot)
            EXPECT_EQ(xram[0xF8BB + slot], test.expected[slot])
                << "frame table=" << static_cast<int>(test.table_low) << " slot=" << slot;
        EXPECT_EQ(xram[0xF8C5], 0x03);

        cpu.mPC = 0x4FA3;
        cpu.mTickDelay = 0;
        cpu.mLowerData[0] = 0x3F;
        cpu.mLowerData[0x41] = 1;
        cpu.mLowerData[0x44] = 0xB8;
        for (int step = 0; step < 1000 && cpu.mPC != 0x4C7D; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x4C7D);
        EXPECT_EQ(cpu.mSFR[REG_SBUF], 0x0D);
    }

    for (const auto [selection, table_low, entry, stop] : {
             std::tuple{0x01, 0x8C, 0x4E67, 0x4EAA},
             std::tuple{0x02, 0x78, 0x4E67, 0x4EAA},
             std::tuple{0x03, 0x8C, 0x4E67, 0x4EAA},
             std::tuple{0x01, 0x8C, 0x4ECB, 0x4EF5},
             std::tuple{0x02, 0x78, 0x4ECB, 0x4EF5},
             std::tuple{0x03, 0x8C, 0x4ECB, 0x4EF5}}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        upper[0xB3 - 0x80] = static_cast<unsigned char>(selection);
        cpu.mPC = static_cast<uint16_t>(entry);
        for (int step = 0; step < 100 && cpu.mPC != stop; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, stop) << "selection=" << selection << " entry=" << entry;
        EXPECT_EQ(cpu.mSFR[REG_DPH], 0x6E);
        EXPECT_EQ(cpu.mSFR[REG_DPL], table_low);
        if (entry == 0x4ECB)
            EXPECT_EQ(upper[0xB3 - 0x80], selection);
    }
}

TEST(Sab80C517, AlcoholCodeSensorCollectionUsesIramAndXramSelectors) {
    const auto root = std::filesystem::path(MA17_ROM_PATH).parent_path();
    const std::array paths{
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256.bin",
        root / "firmwares_modificados_ma17_tipo" /
            "tipo 1.6 alcool27c256 SUN 37a5.bin"};
    struct Case { uint8_t table_low; std::array<uint8_t, 10> expected; };
    constexpr std::array cases{
        Case{0x78, {0x11, 0x12, 0x13, 0x14, 0x21,
                    0x22, 0x23, 0x24, 0x15, 0x25}},
        Case{0x8C, {0x11, 0x12, 0x16, 0x17, 0x26,
                    0x22, 0x23, 0x27, 0x15, 0x25}}};
    for (const auto &path : paths) {
        for (const auto &test : cases) {
            std::array<unsigned char, 32768> code{};
            std::array<unsigned char, 65536> xram{};
            std::array<unsigned char, 128> upper{};
            em8051 cpu{};
            cpu.mCodeMem = code.data();
            cpu.mCodeMemMaxIdx = code.size() - 1;
            cpu.mExtData = xram.data();
            cpu.mExtDataMaxIdx = xram.size() - 1;
            cpu.mUpperData = upper.data();
            reset(&cpu, true);
            std::ifstream file(path, std::ios::binary);
            ASSERT_TRUE(file.is_open()) << path;
            file.read(reinterpret_cast<char *>(code.data()), code.size());
            ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(code.size()));
            ASSERT_EQ(code[0x4F72], 0xE4); // CLR A; MOVC A,@A+DPTR.
            cpu.mSFR[REG_P2] = 0xF8;
            cpu.mSFR[REG_DPH] = 0x6E;
            cpu.mSFR[REG_DPL] = test.table_low;
            cpu.mLowerData[1] = 0xBB;
            cpu.mLowerData[7] = 10;
            for (const auto [address, value] : {
                     std::pair{0x63, 0x11}, std::pair{0x66, 0x12},
                     std::pair{0x47, 0x13}, std::pair{0x62, 0x14},
                     std::pair{0x61, 0x15}, std::pair{0x70, 0x16},
                     std::pair{0x2F, 0x17}})
                cpu.mLowerData[address] = static_cast<unsigned char>(value);
            for (const auto [address, value] : {
                     std::pair{0x0C, 0x21}, std::pair{0x6C, 0x22},
                     std::pair{0x6F, 0x23}, std::pair{0x3D, 0x24},
                     std::pair{0x69, 0x25}, std::pair{0x72, 0x26},
                     std::pair{0x40, 0x27}})
                xram[0xF800 + static_cast<std::size_t>(address)] =
                    static_cast<unsigned char>(value);
            cpu.mPC = 0x4F72;
            for (int step = 0; step < 300 && cpu.mPC != 0x4F8A; ++step) {
                cpu.mTickDelay = 0;
                tick(&cpu);
            }
            ASSERT_EQ(cpu.mPC, 0x4F8A) << path;
            for (size_t slot = 0; slot < test.expected.size(); ++slot)
                EXPECT_EQ(xram[0xF8BB + slot], test.expected[slot])
                    << path << " table=" << int(test.table_low) << " slot=" << slot;
        }
    }
}

TEST(Sab80C517, FirmwareAdcScheduleRedirectsChannelThreeToUpperIram) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    struct Case {
        uint8_t schedule_index;
        uint8_t target;
        uint8_t channel;
        uint8_t adc_data;
        uint8_t expected_value;
        uint8_t expected_flags;
    };
    constexpr std::array cases{
        Case{3, 0x61, 1, 0x5A, 0x5B, 0},
        Case{4, 0x66, 6, 0x5A, 0x5B, 0},
        Case{7, 0x63, 3, 0x5A, 0x5B, 0},
        Case{8, 0x62, 2, 0x5A, 0x5B, 0},
        Case{12, 0x67, 7, 0x5A, 0x5B, 0},
        Case{8, 0x62, 2, 0x02, 0x79, 0x80},
        Case{8, 0x62, 2, 0x03, 0x04, 0},
        Case{8, 0x62, 2, 0xF6, 0xF7, 0},
        Case{8, 0x62, 2, 0xF7, 0x79, 0x40},
    };
    for (const auto &test : cases) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mLowerData[6] = test.schedule_index;
        cpu.mPC = 0x06D0;
        for (int step = 0; step < 100 && cpu.mPC != 0x06F2; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x06F2);
        EXPECT_EQ(cpu.mLowerData[1], test.target);
        EXPECT_EQ(cpu.mSFR[0xD8 - 0x80] & 0x07, test.channel); // ADCON0

        cpu.mSFR[REG_IRCON] |= IRCONMASK_IADC;
        cpu.mSFR[0xD9 - 0x80] = test.adc_data; // ADDAT
        cpu.mPC = 0x0711;
        cpu.mTickDelay = 0;
        for (int step = 0; step < 100 && cpu.mPC != 0x0751; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x0751);
        if (test.target == 0x63) {
            EXPECT_EQ(upper[0xA8 - 0x80], test.expected_value);
            EXPECT_EQ(cpu.mLowerData[0x63], 0);
        } else {
            EXPECT_EQ(cpu.mLowerData[test.target], test.expected_value);
        }
        EXPECT_EQ(cpu.mLowerData[0x28] & 0xC0, test.expected_flags);
    }

    for (const auto [sample, expected_flag] : {
             std::pair{0x03, 0x10}, std::pair{0xE8, 0x08}}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        std::array<unsigned char, 128> upper{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        cpu.mUpperData = upper.data();
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        upper[0xA8 - 0x80] = static_cast<unsigned char>(sample);
        cpu.mPC = 0x463F;
        for (int step = 0; step < 50 && cpu.mPC != 0x4758; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x4758);
        EXPECT_EQ(cpu.mLowerData[0x28] & 0x18, expected_flag);
        EXPECT_EQ(cpu.mLowerData[0x63], 0x11);
    }
}

TEST(Sab80C517, DiagnosticSerialReceiveEchoesComplement) {
    std::array<unsigned char, 32768> original{};
    std::ifstream file(MA17_ROM_PATH, std::ios::binary);
    ASSERT_TRUE(file.is_open());
    file.read(reinterpret_cast<char *>(original.data()), original.size());
    ASSERT_EQ(file.gcount(), static_cast<std::streamsize>(original.size()));

    for (const auto [received, initial_r4, special_frame] : {
             std::tuple{0x34, 0, false}, std::tuple{0x12, 2, true}}) {
        std::array<unsigned char, 32768> code{};
        std::array<unsigned char, 256> xram{};
        em8051 cpu{};
        cpu.mCodeMem = code.data();
        cpu.mCodeMemMaxIdx = 32767;
        cpu.mExtData = xram.data();
        cpu.mExtDataMaxIdx = 255;
        reset(&cpu, true);
        std::copy(original.begin(), original.end(), code.begin());
        cpu.mLowerData[4] = static_cast<unsigned char>(initial_r4);
        cpu.mSFR[REG_SCON] |= SCONMASK_RI;
        cpu.mSFR[REG_SBUF] = static_cast<unsigned char>(received);
        cpu.mPC = 0x6253;
        for (int step = 0; step < 30 && cpu.mPC != 0x62BB; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x62BB);
        EXPECT_EQ(cpu.mSFR[REG_SCON] & SCONMASK_RI, 0);
        EXPECT_EQ(cpu.mSFR[REG_SBUF], static_cast<unsigned char>(~received));
        EXPECT_EQ(cpu.mLowerData[4], initial_r4 + 1);
        EXPECT_EQ((cpu.mLowerData[0x21] & 0x08) != 0, special_frame);
        EXPECT_NE(cpu.mLowerData[0x21] & 0x20, 0);
    }
}

TEST(Sab80C517, CaptureOnLowByteWriteLatchesBothTimer2Bytes) {
    struct Case { uint8_t low_sfr, capture_mode, compare_mode; };
    constexpr std::array cases{
        Case{0xCA, 0x03, 0x02}, Case{0xC2, 0x0C, 0x08},
        Case{0xC4, 0x30, 0x20}, Case{0xC6, 0xC0, 0x80}};
    for (const auto &test : cases) {
        unsigned char code[256]{};
        unsigned char xram[256]{};
        em8051 cpu{};
        cpu.mCodeMem = code;
        cpu.mCodeMemMaxIdx = 255;
        cpu.mExtData = xram;
        cpu.mExtDataMaxIdx = 255;
        reset(&cpu, true);
        code[0] = 0x75; code[1] = test.low_sfr; code[2] = 0xAA;
        code[3] = 0x00; // NOP: following machine cycle
        code[4] = 0x75; code[5] = test.low_sfr; code[6] = 0xBB;
        const auto low = static_cast<std::size_t>(test.low_sfr - 0x80);
        cpu.mSFR[REG_CCEN] = test.capture_mode;
        cpu.mSFR[REG_TL2] = 0x34;
        cpu.mSFR[REG_TH2] = 0x12;

        tick(&cpu);
        EXPECT_EQ(cpu.mSFR[low], 0xAA);
        EXPECT_EQ(cpu.mSFR[low + 1], 0);
        cpu.mSFR[REG_TL2] = 0x78;
        cpu.mSFR[REG_TH2] = 0x56;
        tick(&cpu);
        EXPECT_EQ(cpu.mSFR[low], 0x78);
        EXPECT_EQ(cpu.mSFR[low + 1], 0x56);
        EXPECT_EQ(cpu.mSFR[REG_IRCON], 0);

        cpu.mSFR[REG_CCEN] = test.compare_mode;
        tick(&cpu);
        EXPECT_EQ(cpu.mSFR[low], 0xBB);
        EXPECT_EQ(cpu.mSFR[low + 1], 0x56);
    }
}

TEST(Sab80C517, Cc3Mode1TransfersPortShadowOnlyAtTimer2Compare) {
    unsigned char code[256]{};
    unsigned char xram[256]{};
    em8051 cpu{};
    cpu.mCodeMem = code;
    cpu.mCodeMemMaxIdx = 255;
    cpu.mExtData = xram;
    cpu.mExtDataMaxIdx = 255;
    reset(&cpu, true);
    ASSERT_NE(cpu.sfrread[REG_P1], nullptr);
    ASSERT_NE(cpu.sfrwrite[REG_P1], nullptr);
    code[0] = 0xC2; code[1] = 0x93; // CLR P1.3: shadow write
    code[2] = 0x80; code[3] = 0xFE; // SJMP $
    code[0x10] = 0xE5; code[0x11] = 0x90; // MOV A,P1: pin read
    cpu.mSFR[REG_T2CON] = 0x05; // Timer 2, compare mode 1
    cpu.mSFR[REG_CCEN] = 0x80;  // CC3 compare enabled
    cpu.mSFR[REG_CCL3] = 3;
    cpu.mSFR[REG_TL2] = 1;

    tick(&cpu); // Shadow goes low, timer reaches 2.
    EXPECT_EQ(cpu.mSFR[REG_P1] & 0x08, 0);
    EXPECT_EQ(cpu.sfrread[REG_P1](&cpu, 0x90) & 0x08, 0x08);
    tick(&cpu); // Timer reaches 3 and transfers shadow to output.
    EXPECT_EQ(cpu.cc3_output_pin, 0);
    EXPECT_EQ(cpu.sfrread[REG_P1](&cpu, 0x90) & 0x08, 0);

    cpu.mSFR[REG_P1] |= 0x08;
    cpu.sfrwrite[REG_P1](&cpu, 0x90);
    cpu.mSFR[REG_CCL3] = 4;
    cpu.mPC = 0x10;
    cpu.mTickDelay = 0;
    tick(&cpu); // MOV A,P1 reads old pin; compare then transfers high.
    EXPECT_EQ(cpu.mSFR[REG_ACC] & 0x08, 0);
    EXPECT_EQ(cpu.cc3_output_pin, 1);
    EXPECT_EQ(cpu.sfrread[REG_P1](&cpu, 0x90) & 0x08, 0x08);

    cpu.mSFR[REG_CCEN] = 0;
    cpu.mSFR[REG_P1] &= static_cast<unsigned char>(~0x08);
    cpu.sfrwrite[REG_CCEN](&cpu, 0xC1);
    EXPECT_EQ(cpu.cc3_output_pin, 0);
}
#endif
