#include "lab/StreamingAudio.hpp"

#include "lab/AcousticAdapter.hpp"
#include "lab/SevelImpulse.hpp"

#include <algorithm>
#include <array>
#include <cmath>

namespace lab {

StreamingAudio::StreamingAudio() { initialize_synth(); }

void StreamingAudio::initialize_synth() {
    Synthesizer::Parameters parameters;
    parameters.inputChannelCount = 1;
    parameters.inputBufferSize = 1024;
    parameters.audioBufferSize = 2048;
    parameters.initialAudioParameters.airNoise = 0.0f;
    parameters.initialAudioParameters.inputSampleNoise = 0.0f;
    parameters.initialAudioParameters.convolution = 0.35f;
    parameters.initialAudioParameters.dF_F_mix = 0.02f;
    parameters.initialAudioParameters.levelerMinGain = 1.0f;
    parameters.initialAudioParameters.levelerMaxGain = 1.0f;
    // 0.06 (was 0.08): with the corrected spark torque (CURVES_STUDY F-2) the engine starts faster and the first
    // firings peak ~27 % above full scale at 0.08 (41.5k); 0.06 keeps the true peak under full scale.
    parameters.initialAudioParameters.volume = 0.06f;
    synth_.initialize(parameters);
    synth_.initializeImpulseResponse(
        donor_smooth_impulse.data(),
        static_cast<unsigned>(donor_smooth_impulse.size()), 0.1f, 0);
}

StreamingAudio::~StreamingAudio() { synth_.destroy(); }

void StreamingAudio::seek_to(long long tick, std::size_t next_event_index) {
    synth_.destroy();
    initialize_synth();
    input_sample_ = static_cast<std::size_t>(
        std::ceil(static_cast<double>(std::max(0LL, tick)) * 10000.0 /
                  emulator_ticks_per_second));
    event_index_ = next_event_index;
    block_samples_ = 0;
    pressure_ = 0.0;
}

std::vector<std::int16_t>
StreamingAudio::render_until(const std::vector<ma17::EmulatorEvent> &events,
                             long long stop_tick,
                             std::size_t event_base_index) {
    if (stop_tick <= 0)
        return {};
    const auto input_count = static_cast<std::size_t>(std::ceil(
        static_cast<double>(stop_tick) * 10000.0 / emulator_ticks_per_second));
    if (input_count <= input_sample_)
        return {};
    event_index_ = std::max(event_index_, event_base_index);
    std::size_t event_offset = event_index_ - event_base_index;
    std::vector<std::int16_t> output;
    output.reserve(static_cast<std::size_t>(
        std::ceil(static_cast<double>(input_count - input_sample_) * 4.41)));
    std::array<std::int16_t, 2048> block{};
    for (; input_sample_ < input_count; ++input_sample_) {
        if (block_samples_ == 0)
            synth_.endInputBlock();
        const long long sample_tick =
            static_cast<long long>(input_sample_) * 99;
        while (event_offset < events.size() &&
               events[event_offset].tick <= sample_tick) {
            const auto &event = events[event_offset++];
            ++event_index_;
            if (event.type == ma17::EmulatorEventType::Combustion &&
                event.burned_fuel_kg > 0.0)
                pressure_ +=
                    std::clamp(event.burned_fuel_kg * 2.0e8, 0.0, 12000.0);
        }
        pressure_ *= 0.955;
        const double input = pressure_;
        synth_.writeInput(&input);
        ++block_samples_;
        if (block_samples_ == 128 || input_sample_ + 1 == input_count) {
            synth_.renderAudio();
            const int buffered = synth_.m_audioBufferedSamples.load();
            if (buffered > 0 && buffered <= static_cast<int>(block.size())) {
                const int read = synth_.readAudioOutput(buffered, block.data());
                // Soft limiter on the PCM peaks (CURVES_STUDY F-2: the corrected spark torque makes the engine
                // start faster and the first firings reached full scale): samples below 75 % of full scale are
                // untouched, higher ones are compressed asymptotically towards +-32766 instead of hard clipping.
                constexpr double knee = 24576.0, ceiling = 32766.0;
                for (int i = 0; i < read; ++i) {
                    const double magnitude = std::abs(static_cast<double>(block[static_cast<std::size_t>(i)]));
                    if (magnitude > knee) {
                        const double limited =
                            knee + (ceiling - knee) * std::tanh((magnitude - knee) / (ceiling - knee));
                        block[static_cast<std::size_t>(i)] = static_cast<std::int16_t>(
                            std::lround(block[static_cast<std::size_t>(i)] < 0 ? -limited : limited));
                    }
                }
                output.insert(output.end(), block.begin(),
                              block.begin() + read);
            }
            block_samples_ = 0;
        }
    }
    return output;
}

} // namespace lab
