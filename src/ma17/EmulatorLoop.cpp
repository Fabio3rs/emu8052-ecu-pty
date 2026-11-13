#include "ma17/EmulatorLoop.hpp"

#include "CrankshaftSimulator.hpp"
#include "ma17/CrankInput.hpp"
#include "ma17/ExecutionTracer.hpp"
#include "ma17/FiveBaudInjector.hpp"
#include "ma17/PtyBridge.hpp"
#include "ma17/UartScheduler.hpp"

extern "C" {
#include "emu8051.h"
#include <time.h>
}

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>

namespace ma17 {

static void run_tick_batch(EmulatorLoopContext &context,
                           std::array<uint8_t, 0x8000> &pc_seen,
                           uint16_t &last_pc) {
    em8051 &cpu = context.cpu;
    for (int i = 0; i < context.steps_per_batch; ++i) {
        context.ticks++; // One count per emulated machine-cycle tick.
        tick_crank_input(&cpu, context.ticks, context.crank);
        if (context.trace_pc && cpu.mPC < pc_seen.size())
            pc_seen[cpu.mPC] = 1;
        if (context.trace_pc) {
            trace_pre_tick_boot_and_crank(cpu, context.ticks,
                                          context.crank.enabled);
            trace_pre_tick_engine(cpu, context.ticks);
            trace_pre_tick_cc3(cpu, context.ticks);
        }

        trace_invalid_pc(cpu, last_pc);
        last_pc = cpu.mPC;
        const uint16_t timer2_before = static_cast<uint16_t>(
            (uint16_t(cpu.mSFR[0xCD - 0x80]) << 8) | cpu.mSFR[0xCC - 0x80]);
        tick(&cpu);

        if (context.trace_pc) {
            trace_cc3_and_ram67(cpu, context.ticks, last_pc, timer2_before);
            trace_memory_changes(cpu, context.ticks, last_pc);
        }
        trace_p13_shadow(cpu, context.ticks, last_pc);
        if (context.trace_pc)
            trace_port_edges(cpu, context.ticks, last_pc);

        context.uart.tick(&cpu, context.ticks);
        trace_isr_vector(cpu);
        trace_timer0_stall(cpu);
        trace_kline_decoder(cpu, context.ticks);
        trace_rpm_state(cpu, context.trace_pc);
        trace_reset_watchdog(cpu);
        trace_stack_range(cpu);
    }
}

void run_emulator_loop(EmulatorLoopContext &context) {
    em8051 &cpu = context.cpu;
    uint16_t last_pc = cpu.mPC;
    std::array<uint8_t, 0x8000> pc_seen{};
    struct timespec ts {
        0, 407000
    };

    context.uart.bind_cpu(&cpu);
    while (context.running.load()) {
        const auto loop_start = std::chrono::steady_clock::now();
        if (context.inject_5baud.load()) {
            context.inject_5baud = false;
            fprintf(stderr, "\n[SIGUSR1] Received - starting 5-baud injection "
                            "(non-blocking)\n");
            fflush(stderr);
            context.slow_init.start(context.ticks);
        }

        context.slow_init.tick(context.ticks);
        if (context.crank.check_and_enable(context.ticks)) {
            fprintf(stderr,
                    "\n[CRANKSHAFT] *** Startup delay complete - "
                    "Beginning pulse injection @ %d RPM ***\n\n",
                    context.crank.target_rpm);
            fflush(stderr);
        }

        run_tick_batch(context, pc_seen, last_pc);
        context.bridge.read_and_process();
        trace_performance(cpu, context.ticks, context.startup_time);

        const auto elapsed_ns =
            std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::steady_clock::now() - loop_start);
        const auto sleep_ns = (context.batch_duration - elapsed_ns) -
                              std::chrono::nanoseconds(41200);
        if (sleep_ns.count() > 0) {
            ts.tv_sec = 0;
            ts.tv_nsec = sleep_ns.count();
            nanosleep(&ts, nullptr);
        }
    }

    if (context.trace_pc) {
        for (size_t pc = 0; pc < pc_seen.size(); ++pc) {
            if (pc_seen[pc])
                fprintf(stderr, "[PC-HIT] %04zX\n", pc);
        }
        fprintf(stderr,
                "[PC-COVERAGE] unique=%zu reset=%u timer0=%u "
                "kline=%u collection=%u table_copy=%u serial=%u adc=%u\n",
                static_cast<size_t>(
                    std::count(pc_seen.begin(), pc_seen.end(), uint8_t{1})),
                pc_seen[0x0850], pc_seen[0x000B], pc_seen[0x4AD1],
                pc_seen[0x4E67], pc_seen[0x4EAF], pc_seen[0x61D8],
                pc_seen[0x6441]);
    }
}

} // namespace ma17
