#include "ma17/ExecutionTracer.hpp"

extern "C" {
#include "emu8051.h"
}

#include <array>
#include <chrono>
#include <cstdio>

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
    for (int s = 0; s < 4 && sp >= s; s++)
        fprintf(stderr, "0x%02X ",
                cpu.mLowerData[sp - static_cast<unsigned int>(s)]);
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
    static constexpr std::array<uint8_t, 8> sensor_addresses{
        0x60, 0x61, 0x62, 0x63, 0x66, 0x6F, 0x70, 0xA8};
    static std::array<uint8_t, 8> previous_sensor_values{};
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

    // ADC-derived battery byte, table interpolation and Timer 1 scheduling.
    static constexpr std::array<uint8_t, 6> engine_addresses{0x31, 0x34, 0x35,
                                                             0x7D, 0x7F, 0xC7};
    static std::array<uint8_t, 6> previous_engine_values{};
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
}

} // namespace ma17
