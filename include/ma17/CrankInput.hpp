#pragma once

struct CrankshaftSimulator;
struct em8051;

namespace ma17 {

void tick_crank_input(em8051 *cpu, long long tick, CrankshaftSimulator &sim);

} // namespace ma17
