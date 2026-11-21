#include "ma17/ExecutionTracer.hpp"

extern "C" {
#include "emu8051.h"
}

#include <array>
#include <chrono>
#include <cstdio>
#include <cstdlib>

namespace ma17 {

void trace_invalid_pc(const em8051 &cpu, uint16_t last_pc) {
    // Detect recurrence of the historical indirect-memory stack corruption.
    if (cpu.mPC < 0x8000)
        return;

    static int alert_count = 0;
    if (alert_count >= 3)
        return;

    const unsigned char acc = cpu.mSFR[0xE0 - 0x80];
    const unsigned char psw = cpu.mSFR[0xD0 - 0x80];
    const unsigned char sp = cpu.mSFR[0x81 - 0x80];
    const unsigned char opcode = cpu.mCodeMem[cpu.mPC & 0xFFFF];
    fprintf(stderr, "\n[ALERT] PC entrou em região inválida!\n");
    fprintf(stderr, "[ALERT] last_PC=0x%04X → current_PC=0x%04X\n", last_pc,
            cpu.mPC);
    fprintf(stderr, "[ALERT] Opcode em 0x%04X: 0x%02X\n", cpu.mPC, opcode);
    fprintf(stderr, "[ALERT] Code memory [0xFF9B-0xFFA0]: ");
    for (int j = 0; j < 6; j++)
        fprintf(stderr, "%02X ", cpu.mCodeMem[0xFF9B + j]);
    fprintf(stderr, "\n");
    fprintf(stderr, "[ALERT] ACC=0x%02X PSW=0x%02X SP=0x%02X\n", acc, psw, sp);
    fprintf(stderr, "[ALERT] Stack top 4 bytes: ");
    for (int s = 0; s < 4 && sp >= s; s++) {
        const unsigned int addr = sp - static_cast<unsigned int>(s);
        const uint8_t val = (addr >= 0x80 && cpu.mUpperData)
                                ? cpu.mUpperData[addr - 0x80]
                                : cpu.mLowerData[addr & 0x7F];
        fprintf(stderr, "0x%02X ", val);
    }
    fprintf(stderr, "\n");
    fprintf(stderr, "[ALERT] IE=0x%02X, mInterruptActive=%d\n",
            cpu.mSFR[0xA8 - 0x80], cpu.mInterruptActive);
    fflush(stderr);
    alert_count++;
}

void trace_kline_decoder(const em8051 &cpu, long long tick) {
    static unsigned char last_ram_17 = 0x00;
    const unsigned char current_ram_17 = cpu.mLowerData[0x17];
    if (current_ram_17 != last_ram_17) {
        fprintf(stderr, "[RAM_17] 0x%02X → 0x%02X (PC=0x%04X)\n", last_ram_17,
                current_ram_17, cpu.mPC);
        fflush(stderr);
        last_ram_17 = current_ram_17;
    }

    static int decoder_trace_count = 0;
    static unsigned char last_ram_40_decoder = 0xFF;

    // 4C34h is the slow-init shift register; 4C3Ah jumps to 4C80h.
    if (cpu.mPC == 0x4C34 && decoder_trace_count < 200) {
        const unsigned char ram_40 = cpu.mLowerData[0x40];
        const unsigned char p4 = cpu.mSFR[0xE8 - 0x80];
        const unsigned char p4_bit5 = (p4 >> 5) & 1;
        if (ram_40 != last_ram_40_decoder) {
            fprintf(stderr,
                    "[DECODER-4C34] Instr=%lld PC=0x%04X RAM_40: "
                    "0x%02X → 0x%02X (0b",
                    tick, cpu.mPC, last_ram_40_decoder, ram_40);
            for (int bit_idx = 7; bit_idx >= 0; bit_idx--)
                fprintf(stderr, "%d", (ram_40 >> bit_idx) & 1);
            fprintf(stderr, ") P4.5=%d\n", p4_bit5);
            last_ram_40_decoder = ram_40;
        }
        decoder_trace_count++;
        fflush(stderr);
    }

    if (cpu.mPC == 0x4C44 && decoder_trace_count < 200) {
        fprintf(stderr,
                "[DECODER-4C44] Entry: RAM_17=0x%02X, RAM_40=0x%02X, "
                "A=0x%02X\n",
                cpu.mLowerData[0x17], cpu.mLowerData[0x40], cpu.mSFR[REG_ACC]);
        decoder_trace_count++;
        fflush(stderr);
    }

    if (cpu.mPC == 0x4C48 && decoder_trace_count < 200) {
        fprintf(stderr,
                "[DECODER-4C48] Before cmp: A=0x%02X (expect 0x10), "
                "RAM_40=0x%02X\n",
                cpu.mSFR[REG_ACC], cpu.mLowerData[0x40]);
        decoder_trace_count++;
        fflush(stderr);
    }

    if (cpu.mPC == 0x4C4A && decoder_trace_count < 200) {
        fprintf(stderr,
                "[DECODER-4C4A] CJNE A, RAM_40: A=0x%02X vs "
                "RAM_40=0x%02X (need match!)\n",
                cpu.mSFR[REG_ACC], cpu.mLowerData[0x40]);
        decoder_trace_count++;
        fflush(stderr);
    }
}

void trace_rpm_state(const em8051 &cpu, bool trace_pc) {
    static unsigned char last_ram_47 = 0xFF;
    static unsigned char last_ram_c4 = 0xFF;
    static int ram47_change_count = 0;
    static int ram_c4_change_count = 0;
    const unsigned char current_ram_47 = cpu.mLowerData[0x47];
    // C4h is upper IRAM addressed through @R1.
    const unsigned char current_ram_c4 =
        cpu.mUpperData ? cpu.mUpperData[0xC4 - 0x80] : 0;
    if (current_ram_47 != last_ram_47 && ram47_change_count < 20) {
        fprintf(stderr, "[RAM_47] 0x%02X → 0x%02X (PC=0x%04X) %s\n",
                last_ram_47, current_ram_47, cpu.mPC,
                (current_ram_47 == 0) ? "**RPM ZEROED!**" : "");
        fflush(stderr);
        last_ram_47 = current_ram_47;
        ram47_change_count++;
    }
    // Full state history is needed to compare crank speeds in trace runs.
    if (current_ram_c4 != last_ram_c4 &&
        (trace_pc || ram_c4_change_count < 30)) {
        fprintf(stderr, "[RAM_C4] State: 0x%02X → 0x%02X (PC=0x%04X)\n",
                last_ram_c4, current_ram_c4, cpu.mPC);
        fflush(stderr);
        last_ram_c4 = current_ram_c4;
        ram_c4_change_count++;
    }
}

void trace_reset_watchdog(const em8051 &cpu) {
    // 01ABh reads P2:F8h into the firmware's RPM byte.
    static bool seen_01ab = false;
    if (cpu.mPC == 0x01AB && !seen_01ab) {
        const unsigned int address =
            (static_cast<unsigned int>(cpu.mSFR[REG_P2]) << 8) | 0xF8u;
        fprintf(stderr, "[PC=0x01AB] Loading XRAM[%04X]=%02X → RAM_47\n",
                address, cpu.mExtData[address]);
        fflush(stderr);
        seen_01ab = true;
    }

    static bool seen_4b85 = false;
    static uint16_t last_pc_before_reset = 0;
    if (cpu.mPC == 0x4B85 && !seen_4b85) {
        fprintf(stderr,
                "[RESET TRIGGER] PC=0x4B85 (ljmp RESET_0), came from "
                "PC=0x%04X\n",
                last_pc_before_reset);
        fprintf(stderr,
                "[RESET TRIGGER] RAM_47=0x%02X, triggering full system "
                "reset\n",
                cpu.mLowerData[0x47]);
        fflush(stderr);
        seen_4b85 = true;
    }
    last_pc_before_reset = cpu.mPC;

    static bool seen_4b65 = false;
    if (cpu.mPC == 0x4B65 && !seen_4b65) {
        fprintf(stderr, "[WATCHDOG CHECK] PC=0x4B65, RAM_47=0x%02X\n",
                cpu.mLowerData[0x47]);
        fflush(stderr);
        seen_4b65 = true;
    }

    static int reset_0_count = 0;
    static uint16_t last_pc_before_0850 = 0;
    if (cpu.mPC == 0x0850) {
        reset_0_count++;
        if (reset_0_count <= 3) {
            fprintf(stderr,
                    "[RESET_0 ENTRY #%d] PC=0x0850, came from "
                    "PC=0x%04X, SP=0x%02X\n",
                    reset_0_count, last_pc_before_0850, cpu.mSFR[REG_SP]);
            fflush(stderr);
        }
    }
    last_pc_before_0850 = cpu.mPC;
}

void trace_stack_range(const em8051 &cpu) {
    static unsigned char last_sp = 0xD0;
    static unsigned char min_sp_seen = 0xFF;
    static unsigned char max_sp_seen = 0x00;
    const unsigned char current_sp = cpu.mSFR[REG_SP];

    if (current_sp < min_sp_seen)
        min_sp_seen = current_sp;
    if (current_sp > max_sp_seen)
        max_sp_seen = current_sp;

    if (current_sp < 0x08 && last_sp >= 0x08) {
        fprintf(stderr, "[STACK UNDERFLOW] SP: 0x%02X → 0x%02X (PC=0x%04X)\n",
                last_sp, current_sp, cpu.mPC);
        fprintf(stderr, "[STACK RANGE] Min=0x%02X Max=0x%02X\n", min_sp_seen,
                max_sp_seen);
        fflush(stderr);
    }

    // The stack enters upper IRAM when SP passes 7Fh.
    if (current_sp > 0x7F && last_sp <= 0x7F) {
        fprintf(stderr, "[STACK OVERFLOW] SP: 0x%02X → 0x%02X (PC=0x%04X)\n",
                last_sp, current_sp, cpu.mPC);
        fprintf(stderr, "[STACK RANGE] Min=0x%02X Max=0x%02X\n", min_sp_seen,
                max_sp_seen);
        fflush(stderr);
    }

    if (current_sp == 0x00 && last_sp != 0x00) {
        fprintf(stderr,
                "[STACK CRITICAL] SP reached 0x00! (PC=0x%04X, "
                "last_SP=0x%02X)\n",
                cpu.mPC, last_sp);
        fprintf(stderr, "[STACK DUMP] Stack[0x00-0x07]: ");
        for (int j = 0; j <= 7; j++)
            fprintf(stderr, "%02X ", cpu.mLowerData[j]);
        fprintf(stderr, "\n");
        fflush(stderr);
    }

    last_sp = current_sp;
}

void trace_timer0_stall(const em8051 &cpu) {
    static int64_t main_loop_counter = 0;
    static int64_t last_trace_at = 0;
    main_loop_counter++;
    if (cpu.mInterruptActive == 2 &&
        (main_loop_counter - last_trace_at) > 500 &&
        main_loop_counter < 100000) {
        fprintf(stderr, "[MAIN-TF0-TRACE] PC=0x%04X SP=0x%02X loop=%ld\n",
                cpu.mPC, cpu.mSFR[REG_SP], main_loop_counter);
        last_trace_at = main_loop_counter;
    }
}

void trace_performance(const em8051 &cpu, long long tick,
                       std::chrono::steady_clock::time_point startup_time) {
    // Slow emulation stretches IEX3 in wall time and can expose UART overruns.
    static long long last_report_time_ms = 0;
    static long long last_tick_count = 0;

    const auto elapsed_ms =
        std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - startup_time)
            .count();
    if (elapsed_ms - last_report_time_ms < 5000)
        return;

    const unsigned char rpm = cpu.mLowerData[0x47];
    const uint16_t injection_time = static_cast<uint16_t>(
        (cpu.mLowerData[0x14] << 8) | cpu.mLowerData[0x15]);
    const long long delta_ticks = tick - last_tick_count;
    const double delta_sec =
        static_cast<double>(elapsed_ms - last_report_time_ms) / 1000.0;
    const double ticks_per_sec = static_cast<double>(delta_ticks) / delta_sec;

    fprintf(stderr,
            "[PERF] %.0f ticks/sec (expected: ~990,000) "
            "delta_ticks=%lld delta_sec=%.2f RPM=%d inj_time=%d\n",
            ticks_per_sec, delta_ticks, delta_sec, rpm, injection_time);
    fflush(stderr);

    last_report_time_ms = elapsed_ms;
    last_tick_count = tick;
}

void trace_isr_vector(const em8051 &cpu) {
    static uint16_t previous_pc = 0;
    static int iex3_count = 0;
    static int tf0_count = 0;
    static int tf2_count = 0;
    const uint16_t pc = cpu.mPC;

    const bool vector_entry = pc == 0x03 || pc == 0x0B || pc == 0x13 ||
                              pc == 0x1B || pc == 0x23 || pc == 0x2B ||
                              pc == 0x43 || pc == 0x4B || pc == 0x53;
    if (vector_entry && previous_pc != pc) {
        if (pc == 0x53 && iex3_count < 20) {
            fprintf(stderr,
                    "[ISR-IEX3] #%d IEX3 called! CRCL=0x%02X CRCH=0x%02X\n",
                    ++iex3_count, cpu.mSFR[0xCA - 0x80], cpu.mSFR[0xCB - 0x80]);
            fflush(stderr);
        }
        if (pc == 0x0B && tf0_count < 20)
            fprintf(stderr,
                    "[ISR-TF0] #%d Timer 0 ISR called from PC=0x%04X "
                    "(mInterruptActive=%d)\n",
                    ++tf0_count, previous_pc, cpu.mInterruptActive);
        if (pc == 0x2B && tf2_count < 20)
            fprintf(stderr,
                    "[ISR-TF2] #%d Timer 2 ISR called from PC=0x%04X "
                    "(mInterruptActive=%d)\n",
                    ++tf2_count, previous_pc, cpu.mInterruptActive);
    }
    previous_pc = pc;
}

void trace_cc3_and_ram67(const em8051 &cpu, long long tick, uint16_t source_pc,
                         uint16_t timer2_before) {
    static uint8_t previous_cc3_pin = 1;
    if (cpu.cc3_output_pin != previous_cc3_pin) {
        fprintf(stderr,
                "[CC3-PIN] tick=%lld PC=%04X value=%u "
                "shadow=%u CCEN=%02X T2CON=%02X source_PC=%04X\n",
                tick, cpu.mPC, cpu.cc3_output_pin,
                (cpu.mSFR[0x90 - 0x80] >> 3) & 1u, cpu.mSFR[REG_CCEN],
                cpu.mSFR[REG_T2CON], source_pc);
        previous_cc3_pin = cpu.cc3_output_pin;
    }
    const uint16_t timer2_after = static_cast<uint16_t>(
        (uint16_t(cpu.mSFR[0xCD - 0x80]) << 8) | cpu.mSFR[0xCC - 0x80]);
    const uint16_t cc3 = static_cast<uint16_t>(
        (uint16_t(cpu.mSFR[0xC7 - 0x80]) << 8) | cpu.mSFR[0xC6 - 0x80]);
    if (timer2_after != timer2_before && timer2_after == cc3 &&
        (cpu.mSFR[0xC1 - 0x80] & 0xC0u) == 0x80u &&
        (cpu.mSFR[0xC8 - 0x80] & 0x04u)) {
        static int cc3_matches = 0;
        if (cc3_matches++ < 256)
            fprintf(stderr,
                    "[CC3-MATCH-CANDIDATE] tick=%lld PC=%04X "
                    "T2=%04X shadow_P1_3=%u\n",
                    tick, cpu.mPC, timer2_after,
                    (cpu.mSFR[0x90 - 0x80] >> 3) & 1u);
    }
    static uint8_t previous_ram67 = 0;
    const uint8_t ram67 = cpu.mLowerData[0x67];
    if (ram67 != previous_ram67)
        fprintf(stderr,
                "[RAM67-WRITE] instr=%lld PC=%04X next_PC=%04X "
                "value=%02X->%02X\n",
                tick, source_pc, cpu.mPC, previous_ram67, ram67);
    previous_ram67 = ram67;
}

void trace_port_edges(const em8051 &cpu, long long tick, uint16_t source_pc) {
    static uint8_t previous_p1 = 0xFF;
    static uint8_t previous_p5 = 0xFF;
    static uint8_t previous_p2 = 0xFF;
    static int port_events = 0;
    static int p2_events = 0;
    uint8_t p1 = cpu.mSFR[0x90 - 0x80] & 0x0Au;
    uint8_t p5 = cpu.mSFR[0xF8 - 0x80] & 0x03u;
    uint8_t p2 = cpu.mSFR[0xA0 - 0x80];
    if (p2 != previous_p2 && p2_events++ < 30)
        fprintf(stderr, "[P2-EDGE] instr=%lld PC=%04X P2=%02X\n", tick, cpu.mPC,
                p2);
    if (p5 != previous_p5)
        fprintf(stderr,
                "[P5-LATCH] instr=%lld PC=%04X value=%02X "
                "RAM47=%02X source_PC=%04X RAM69=%02X "
                "RAM36_37=%02X%02X RAM32_33=%02X%02X "
                "RAM34_35=%02X%02X\n",
                tick, cpu.mPC, p5, cpu.mLowerData[0x47], source_pc,
                cpu.mLowerData[0x69], cpu.mLowerData[0x36],
                cpu.mLowerData[0x37], cpu.mLowerData[0x32],
                cpu.mLowerData[0x33], cpu.mLowerData[0x34],
                cpu.mLowerData[0x35]);
    if ((p1 ^ previous_p1) & 0x02u)
        fprintf(stderr,
                "[P1.1-LATCH] instr=%lld source_PC=%04X value=%u RAM47=%02X\n",
                tick, source_pc, (p1 >> 1) & 1u, cpu.mLowerData[0x47]);
    if ((p1 != previous_p1 || p5 != previous_p5) && port_events++ < 40)
        fprintf(stderr,
                "[PORT-EDGE] instr=%lld PC=%04X P1.1/3=%02X "
                "P5.0/1=%02X RAM47=%02X\n",
                tick, cpu.mPC, p1, p5, cpu.mLowerData[0x47]);
    previous_p1 = p1;
    previous_p5 = p5;
    previous_p2 = p2;
}

void trace_p13_shadow(const em8051 &cpu, long long tick, uint16_t source_pc) {
    static const bool enabled = std::getenv("MA17_TRACE_P13") != nullptr;
    if (!enabled)
        return;

    static uint8_t last_value = (cpu.mSFR[0x90 - 0x80] >> 3) & 1u;
    static std::chrono::high_resolution_clock::time_point last_time =
        std::chrono::high_resolution_clock::now();
    uint8_t value = (cpu.mSFR[0x90 - 0x80] >> 3) & 1u;
    if (value == last_value)
        return;

    auto now = std::chrono::high_resolution_clock::now();
    auto duration =
        std::chrono::duration_cast<std::chrono::microseconds>(now - last_time)
            .count();
    fprintf(stderr,
            "[P1.3-SHADOW] tick=%lld 0x%02X → 0x%02X "
            "(PC=0x%04X) [dur=%ldµs] source_PC=%04X\n",
            tick, last_value, value, cpu.mPC, duration, source_pc);
    fflush(stderr);
    last_value = value;
    last_time = now;
}

void trace_memory_changes(const em8051 &cpu, long long tick,
                          uint16_t source_pc) {
    static const bool trace_idle_position_gate =
        std::getenv("MA17_TRACE_IDLE_POSITION_GATE") != nullptr;
    if (trace_idle_position_gate) {
        // SAB80C517 User's Manual, On-Chip RAM: these bit-addressable
        // lower-IRAM bytes supply the carry guards at Fiat PC 23AFh.
        static std::array<uint8_t, 3> previous{};
        static int observations = 0;
        constexpr std::array<uint8_t, 3> addresses{0x20, 0x24, 0x2D};
        constexpr std::array<uint8_t, 3> masks{0x08, 0x10, 0x70};
        for (size_t index = 0; index < addresses.size(); ++index) {
            const uint8_t current = cpu.mLowerData[addresses[index]];
            if (((current ^ previous[index]) & masks[index]) &&
                observations++ < 512)
                std::fprintf(stderr,
                             "[IDLE-POSITION-FLAG] tick=%lld PC=%04X "
                             "RAM%02X=%02X->%02X\n",
                             tick, source_pc, addresses[index],
                             previous[index], current);
            previous[index] = current;
        }
    }
    static const bool trace_idle_fault =
        std::getenv("MA17_TRACE_IDLE_FAULT") != nullptr;
    if (trace_idle_fault) {
        // SAB80C517 User's Manual, On-Chip RAM and Instruction Set:
        // 27h is lower IRAM; MOVX addresses F8:4Eh in external data.
        static uint8_t previous_ram27 = 0;
        static uint8_t previous_xram4e = 0;
        const uint8_t ram27 = cpu.mLowerData[0x27];
        const uint8_t xram4e = cpu.mExtData[0xF84E];
        if ((ram27 ^ previous_ram27) & 0x0F)
            std::fprintf(stderr,
                         "[IDLE-FAULT-SOURCE] tick=%lld PC=%04X "
                         "RAM27=%02X->%02X XRAM4E=%02X "
                         "F839=%02X RAM24=%02X RAM70=%02X P4_latch=%02X\n",
                         tick, source_pc, previous_ram27, ram27, xram4e,
                         cpu.mExtData[0xF839], cpu.mLowerData[0x24],
                         cpu.mLowerData[0x70], cpu.mSFR[0xE8 - 0x80]);
        if ((xram4e ^ previous_xram4e) & 0x0F)
            std::fprintf(stderr,
                         "[IDLE-FAULT-LATCH] tick=%lld PC=%04X "
                         "XRAM4E=%02X->%02X RAM27=%02X\n",
                         tick, source_pc, previous_xram4e, xram4e, ram27);
        previous_ram27 = ram27;
        previous_xram4e = xram4e;
    }
    static const bool trace_idle_f839 =
        std::getenv("MA17_TRACE_IDLE_F839") != nullptr;
    if (trace_idle_f839) {
        static uint8_t previous = 0;
        const uint8_t current = cpu.mExtData[0xF839];
        if (current != previous)
            std::fprintf(stderr,
                         "[IDLE-F839] tick=%lld value=%02X->%02X "
                         "source_PC=%04X F835=%02X RAM24=%02X "
                         "RAM6F=%02X RAM70=%02X\n",
                         tick, previous, current, source_pc,
                         cpu.mExtData[0xF835], cpu.mLowerData[0x24],
                         cpu.mLowerData[0x6F], cpu.mLowerData[0x70]);
        previous = current;
    }
    static const bool trace_idle_publish =
        std::getenv("MA17_TRACE_IDLE_PUBLISH") != nullptr;
    if (trace_idle_publish &&
        (source_pc == 0x407D || source_pc == 0x41CD ||
         source_pc == 0x41E5)) {
        // Fiat ROM: 407Dh selects bits into banked R7 before 41CDh
        // refreshes F884h; 41E5h publishes that earlier R7 value.
        const uint8_t source = cpu.mLowerData[0x27];
        const uint8_t snapshot = cpu.mExtData[0xF884];
        const uint8_t bank = cpu.mSFR[REG_PSW] & 0x18u;
        std::fprintf(stderr,
                     "[IDLE-PUBLISH] tick=%lld PC=%04X RAM27=%02X "
                     "F884=%02X R7=%02X F84E=%02X F887=%02X\n",
                     tick, source_pc, source, snapshot,
                     cpu.mLowerData[bank + 7], cpu.mExtData[0xF84E],
                     cpu.mExtData[0xF887]);
    }
    static const bool trace_coolant_gate =
        std::getenv("MA17_TRACE_COOLANT_GATE") != nullptr;
    if (trace_coolant_gate && (source_pc == 0x3286 || source_pc == 0x3290)) {
        // SAB80C517 Instruction Set: MOVX @R0,A writes through the P2 page.
        const uint8_t low = source_pc == 0x3286 ? 0xD7 : 0xD9;
        const uint16_t address = static_cast<uint16_t>(
            (uint16_t(cpu.mSFR[0xA0 - 0x80]) << 8) | low);
        fprintf(stderr,
                "[COOLANT-DECAY] tick=%lld PC=%04X addr=%04X value=%02X "
                "F2D=%02X T2CON=%02X\n",
                tick, source_pc, address, cpu.mExtData[address],
                cpu.mLowerData[0x2D], cpu.mSFR[0xC8 - 0x80]);
    }
    // SAB80C517 User's Manual, On-Chip RAM: direct 64h is lower IRAM;
    // Fiat 4044h uses it as the divisor when deriving the 7B3Eh axis byte.
    static constexpr std::array<uint8_t, 10> sensor_addresses{
        0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x6F, 0x70, 0xA8};
    static std::array<uint8_t, 10> previous_sensor_values{};
    for (size_t index = 0; index < sensor_addresses.size(); ++index) {
        const uint8_t address = sensor_addresses[index];
        const uint8_t value = address < 0x80 ? cpu.mLowerData[address]
                                             : cpu.mUpperData[address - 0x80];
        if (value != previous_sensor_values[index])
            fprintf(stderr,
                    "[SENSOR-RAM] tick=%lld addr=%02X "
                    "value=%02X->%02X source_PC=%04X next_PC=%04X\n",
                    tick, address, previous_sensor_values[index], value,
                    source_pc, cpu.mPC);
        previous_sensor_values[index] = value;
    }

    // ADC-derived intermediates, table indices and Timer 1 scheduling.
    // SAB80C517 User's Manual, On-Chip RAM: 57h/59h/5Ah are lower IRAM.
    // Fiat writes 59h:5Ah at 1644h and reads them at 1D60h. The 1562h
    // calculation also reads upper IRAM 87h through @R0 and lower 4Fh.
    // Fiat 47BEh/47CCh write lower IRAM 79h/7Bh; SAB80C517 User's Manual,
    // On-Chip RAM, distinguishes these direct bytes from upper IRAM.
    // Fiat 49ADh can write lower IRAM 4Dh after the 744Eh curve lookup.
    // SAB80C517 User's Manual, On-Chip RAM: Fiat 406Fh writes upper
    // IRAM 9Dh through @R1; 1E8Bh reads it through @R1, not as an SFR.
    static constexpr std::array<uint8_t, 25> engine_addresses{
        0x31, 0x34, 0x35, 0x48, 0x49, 0x4D, 0x4E, 0x4F, 0x57, 0x59, 0x5A,
        0x68, 0x69, 0x6A, 0x78, 0x79, 0x7A, 0x7B, 0x7C, 0x7D, 0x7F,
        0x87, 0x9D, 0xA4, 0xC7};
    static std::array<uint8_t, engine_addresses.size()> previous_engine_values{};
    for (size_t index = 0; index < engine_addresses.size(); ++index) {
        const uint8_t address = engine_addresses[index];
        const uint8_t value = address < 0x80 ? cpu.mLowerData[address]
                                             : cpu.mUpperData[address - 0x80];
        if (value != previous_engine_values[index])
            fprintf(stderr,
                    "[ENGINE-RAM] tick=%lld addr=%02X "
                    "value=%02X->%02X source_PC=%04X\n",
                    tick, address, previous_engine_values[index], value,
                    source_pc);
        previous_engine_values[index] = value;
    }

    static constexpr std::array<uint16_t, 5> fault_addresses{
        0xF885, 0xF84F, 0xF8CD, 0xF8CE, 0xF8CF};
    static std::array<uint8_t, 5> previous_fault_values{};
    for (size_t index = 0; index < fault_addresses.size(); ++index) {
        const uint16_t address = fault_addresses[index];
        const uint8_t value = cpu.mExtData[address];
        if (value != previous_fault_values[index])
            fprintf(stderr,
                    "[FAULT-XRAM] tick=%lld addr=%04X "
                    "value=%02X->%02X source_PC=%04X\n",
                    tick, address, previous_fault_values[index], value,
                    source_pc);
        previous_fault_values[index] = value;
    }

    // Raw XRAM locations named as fuel adaptations by the scanner. Their
    // physical role and closed-loop gate still require firmware evidence.
    static constexpr std::array<uint16_t, 4> adaptation_addresses{
        0xF80C, 0xF86C, 0xF86F, 0xF872};
    static std::array<uint8_t, 4> previous_adaptation_values{};
    for (size_t index = 0; index < adaptation_addresses.size(); ++index) {
        const uint16_t address = adaptation_addresses[index];
        const uint8_t value = cpu.mExtData[address];
        if (value != previous_adaptation_values[index])
            fprintf(stderr,
                    "[ADAPT-XRAM] tick=%lld addr=%04X "
                    "value=%02X->%02X source_PC=%04X\n",
                    tick, address, previous_adaptation_values[index], value,
                    source_pc);
        previous_adaptation_values[index] = value;
    }

    static const bool trace_lambda_bounds =
        std::getenv("MA17_TRACE_LAMBDA_BOUNDS") != nullptr;
    if (trace_lambda_bounds) {
        static constexpr std::array<uint16_t, 4> addresses{
            0xF8E8, 0xF8E9, 0xF8EA, 0xF8EB};
        static std::array<uint8_t, 4> previous{};
        for (size_t index = 0; index < addresses.size(); ++index) {
            const uint16_t address = addresses[index];
            const uint8_t value = cpu.mExtData[address];
            if (value != previous[index]) {
                // SAB80C517 Instruction Set, p. 224: MOVX @Ri writes
                // external data on the P2/XPAGE-selected page.
                fprintf(stderr,
                        "[LAMBDA-BOUND-XRAM] tick=%lld addr=%04X "
                        "value=%02X->%02X source_PC=%04X "
                        "RAM65=%02X F2C=%02X F2F=%02X "
                        "RAM5C5D=%02X%02X RAM1415=%02X%02X\n",
                        tick, address, previous[index], value, source_pc,
                        cpu.mLowerData[0x65], cpu.mLowerData[0x2C],
                        cpu.mLowerData[0x2F], cpu.mLowerData[0x5C],
                        cpu.mLowerData[0x5D], cpu.mLowerData[0x14],
                        cpu.mLowerData[0x15]);
            }
            previous[index] = value;
        }
    }
}

} // namespace ma17
