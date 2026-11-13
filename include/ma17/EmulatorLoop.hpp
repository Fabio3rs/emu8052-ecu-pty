#pragma once

#include <atomic>
#include <chrono>

struct em8051;
struct CrankshaftSimulator;

namespace ma17 {

struct FiveBaudInjector;
struct PtyBridge;
class UartScheduler;

struct EmulatorLoopContext {
    em8051 &cpu;
    CrankshaftSimulator &crank;
    PtyBridge &bridge;
    UartScheduler &uart;
    FiveBaudInjector &slow_init;
    std::atomic<bool> &running;
    std::atomic<bool> &inject_5baud;
    long long &ticks;
    std::chrono::steady_clock::time_point startup_time;
    std::chrono::nanoseconds batch_duration;
    int steps_per_batch;
    bool trace_pc;
};

void run_emulator_loop(EmulatorLoopContext &context);

} // namespace ma17
