#pragma once

#include <chrono>
#include <cstdint>

struct em8051;

namespace ma17 {

void trace_memory_changes(const em8051 &cpu, long long tick,
                          uint16_t source_pc);
void trace_cc3_and_ram67(const em8051 &cpu, long long tick, uint16_t source_pc,
                         uint16_t timer2_before);
void trace_port_edges(const em8051 &cpu, long long tick, uint16_t source_pc);
void trace_p13_shadow(const em8051 &cpu, long long tick, uint16_t source_pc);
void trace_isr_vector(const em8051 &cpu);
void trace_pre_tick_boot_and_crank(const em8051 &cpu, long long tick,
                                   bool crank_enabled);
void trace_pre_tick_engine(const em8051 &cpu, long long tick);
void trace_pre_tick_cc3(const em8051 &cpu, long long tick);
void trace_invalid_pc(const em8051 &cpu, uint16_t last_pc);
void trace_kline_decoder(const em8051 &cpu, long long tick);
void trace_rpm_state(const em8051 &cpu, bool trace_pc);
void trace_reset_watchdog(const em8051 &cpu);
void trace_stack_range(const em8051 &cpu);
void trace_timer0_stall(const em8051 &cpu);
void trace_performance(const em8051 &cpu, long long tick,
                       std::chrono::steady_clock::time_point startup_time);

} // namespace ma17
