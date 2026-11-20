#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace ma17 {

// K2: the most recent distinct program-memory addresses the firmware read with
// MOVC A,@A+DPTR / MOVC A,@A+PC (the table lookups). Move-to-front, so a table
// cell read every few milliseconds stays at the front instead of being pushed
// out by a burst of other reads. Plain data: it is copied into the snapshot.
inline constexpr std::size_t kCodeReadTraceSize = 48;

struct CodeReadTrace {
    std::array<std::uint16_t, kCodeReadTraceSize> addresses{};
    std::size_t count = 0;          // valid entries, newest first
    unsigned long long total = 0;   // every MOVC seen, repeats included

    void record(std::uint16_t address) {
        ++total;
        std::size_t position = count;
        for (std::size_t i = 0; i < count; ++i)
            if (addresses[i] == address) {
                position = i;
                break;
            }
        if (position == count) {
            if (count < addresses.size())
                ++count;
            position = count - 1; // drop the oldest when full
        }
        for (std::size_t i = position; i > 0; --i)
            addresses[i] = addresses[i - 1];
        addresses[0] = address;
    }
};

// Effective address of the MOVC at `pc`, or -1 when `opcode` is not a MOVC.
// 0x93 = MOVC A,@A+DPTR; 0x83 = MOVC A,@A+PC (PC already points past it).
inline long movc_effective_address(std::uint8_t opcode, std::uint16_t pc,
                                   std::uint8_t accumulator,
                                   std::uint16_t dptr) {
    if (opcode == 0x93)
        return static_cast<long>((dptr + accumulator) & 0xFFFFu);
    if (opcode == 0x83)
        return static_cast<long>((pc + 1u + accumulator) & 0xFFFFu);
    return -1;
}

} // namespace ma17
