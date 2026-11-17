#pragma once

#include "ma17/EmulatorEvent.hpp"

#include <cstdint>
#include <vector>

namespace lab {

constexpr int audio_sample_rate = 44100;
constexpr int emulator_ticks_per_second = 990000;

std::vector<std::int16_t>
render_combustion_audio(const std::vector<ma17::EmulatorEvent> &events,
                        long long stop_tick);

} // namespace lab
