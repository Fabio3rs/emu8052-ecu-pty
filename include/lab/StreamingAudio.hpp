#pragma once

#include "ma17/EmulatorEvent.hpp"
#include "synthesizer.h"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace lab {

class StreamingAudio {
  public:
    StreamingAudio();
    ~StreamingAudio();
    StreamingAudio(const StreamingAudio &) = delete;
    StreamingAudio &operator=(const StreamingAudio &) = delete;

    std::vector<std::int16_t>
    render_until(const std::vector<ma17::EmulatorEvent> &events,
                 long long stop_tick, std::size_t event_base_index = 0);
    void seek_to(long long tick, std::size_t next_event_index);

  private:
    void initialize_synth();
    Synthesizer synth_;
    std::size_t input_sample_ = 0;
    std::size_t event_index_ = 0;
    std::size_t block_samples_ = 0;
    double pressure_ = 0.0;
};

} // namespace lab
