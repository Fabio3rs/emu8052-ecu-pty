#include "lab/AcousticAdapter.hpp"
#include "lab/StreamingAudio.hpp"
#include "lab/WavWriter.hpp"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

int main(int argc, char **argv) {
    if (argc != 2)
        return 2;
    constexpr long long stop_tick = 99000;
    const std::vector<ma17::EmulatorEvent> silent_events;
    const auto silence = lab::render_combustion_audio(silent_events, stop_tick);
    if (silence.empty() ||
        std::any_of(silence.begin(), silence.end(),
                    [](std::int16_t value) { return value != 0; }))
        return 1;

    ma17::EmulatorEvent combustion;
    combustion.tick = 1000;
    combustion.type = ma17::EmulatorEventType::Combustion;
    combustion.burned_fuel_kg = 0.00001;
    const std::vector<ma17::EmulatorEvent> events{combustion};
    const auto first = lab::render_combustion_audio(events, stop_tick);
    const auto second = lab::render_combustion_audio(events, stop_tick);
    if (first != second || first.size() != silence.size() ||
        std::none_of(first.begin(), first.end(),
                     [](std::int16_t value) { return value != 0; }))
        return 1;
    lab::StreamingAudio stream;
    auto first_half = stream.render_until(events, stop_tick / 2);
    const auto second_half = stream.render_until(events, stop_tick);
    first_half.insert(first_half.end(), second_half.begin(), second_half.end());
    if (first_half != first)
        return 1;
    ma17::EmulatorEvent later = combustion;
    later.tick = 60000;
    const std::vector<ma17::EmulatorEvent> both{combustion, later};
    const auto continuous = lab::render_combustion_audio(both, stop_tick);
    lab::StreamingAudio sliding;
    auto early = sliding.render_until(both, stop_tick / 2);
    const std::vector<ma17::EmulatorEvent> recent{later};
    const auto late = sliding.render_until(recent, stop_tick, 1);
    early.insert(early.end(), late.begin(), late.end());
    if (early != continuous)
        return 1;
    lab::StreamingAudio seeking;
    seeking.seek_to(stop_tick / 2, 1);
    const auto resumed = seeking.render_until(recent, stop_tick, 1);
    if (resumed.empty() ||
        std::none_of(resumed.begin(), resumed.end(),
                     [](std::int16_t value) { return value != 0; }))
        return 1;
    seeking.seek_to(stop_tick, 2);
    if (!seeking.render_until({}, stop_tick, 2).empty())
        return 1;
    if (!lab::save_mono_wav(argv[1], first, lab::audio_sample_rate))
        return 1;
    std::printf("[LAB-AUDIO-TEST] samples=%zu nonzero=yes deterministic=yes\n",
                first.size());
    return 0;
}
