#include <gtest/gtest.h>
#include <algorithm>
#include <array>
#include <fstream>
#include <tuple>
#include <utility>
extern "C" {
#include "emu8051.h"
}

TEST(SampleTest, BasicTest) {
    EXPECT_EQ(1, 1);
}

#ifdef __SAB80C517__
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

    std::array<uint16_t, 2> reloads{};
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
        cpu.mLowerData[0x69] = index == 0 ? 0x9A : 0xA2;
        cpu.mLowerData[0x36] = 0x01;
        cpu.mLowerData[0x37] = 0x1D;
        cpu.mPC = 0x043B;
        for (int step = 0; step < 100 && cpu.mPC != 0x048C; ++step)
            tick(&cpu);
        ASSERT_EQ(cpu.mPC, 0x048C);
        reloads[index] = static_cast<uint16_t>(cpu.mLowerData[0x32] << 8 |
                                                cpu.mLowerData[0x33]);
    }
    EXPECT_NE(reloads[0], reloads[1]);
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
