#include "ma17/CodeReadTrace.hpp"

#include <gtest/gtest.h>

TEST(CodeReadTrace, MovcAddressUsesDptrOrPc) {
    EXPECT_EQ(ma17::movc_effective_address(0x93, 0x1234, 0x05, 0x7C00), 0x7C05);
    EXPECT_EQ(ma17::movc_effective_address(0x83, 0x1000, 0x10, 0x0000), 0x1011);
    EXPECT_EQ(ma17::movc_effective_address(0xFF, 0x1000, 0x10, 0x7C00), -1);
    // 16-bit wraparound like the hardware: 0xFFFF + 0xFF = 0x100FE -> 0x00FE.
    EXPECT_EQ(ma17::movc_effective_address(0x93, 0, 0xFF, 0xFFFF), 0x00FE);
}

TEST(CodeReadTrace, MoveToFrontKeepsDistinctAddressesNewestFirst) {
    ma17::CodeReadTrace trace;
    trace.record(0x100);
    trace.record(0x200);
    trace.record(0x300);
    trace.record(0x100); // seen again: moves to the front, no duplicate
    ASSERT_EQ(trace.count, 3u);
    EXPECT_EQ(trace.addresses[0], 0x100);
    EXPECT_EQ(trace.addresses[1], 0x300);
    EXPECT_EQ(trace.addresses[2], 0x200);
    EXPECT_EQ(trace.total, 4u);
}

TEST(CodeReadTrace, DropsTheOldestWhenFull) {
    ma17::CodeReadTrace trace;
    for (std::uint16_t a = 0; a < ma17::kCodeReadTraceSize + 5; ++a)
        trace.record(a);
    EXPECT_EQ(trace.count, ma17::kCodeReadTraceSize);
    EXPECT_EQ(trace.addresses[0], ma17::kCodeReadTraceSize + 4);
    // The first five addresses were pushed out.
    for (std::size_t i = 0; i < trace.count; ++i)
        EXPECT_GE(trace.addresses[i], 5);
}
