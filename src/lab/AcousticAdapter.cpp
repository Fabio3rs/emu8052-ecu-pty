#include "lab/AcousticAdapter.hpp"

#include "lab/StreamingAudio.hpp"

namespace lab {

std::vector<std::int16_t>
render_combustion_audio(const std::vector<ma17::EmulatorEvent> &events,
                        long long stop_tick) {
    StreamingAudio audio;
    return audio.render_until(events, stop_tick);
}

} // namespace lab
