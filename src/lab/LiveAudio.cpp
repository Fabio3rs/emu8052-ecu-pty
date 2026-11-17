#include "lab/LiveAudio.hpp"

#include "lab/SimSession.hpp"
#include "lab/StreamingAudio.hpp"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <stdexcept>

namespace lab {

LiveAudio::LiveAudio(SimSession &session, SDL_AudioStream *stream)
    : session_(session), stream_(stream) {
    if (!stream_)
        throw std::invalid_argument("live audio stream is null");
}

LiveAudio::~LiveAudio() { stop(); }

void LiveAudio::start() {
    if (worker_.joinable())
        throw std::logic_error("live audio already started");
    stop_.store(false);
    worker_ = std::thread(&LiveAudio::run, this);
}

void LiveAudio::stop() {
    stop_.store(true);
    if (worker_.joinable())
        worker_.join();
}

void LiveAudio::run() {
    using namespace std::chrono_literals;
    StreamingAudio source;
    long long last_audio_tick = 0;
    bool was_active = false;
    bool had_output = false;
    bool device_started = false;
    while (!stop_.load()) {
        ma17::EmulatorSnapshot snapshot;
        if (!session_.latest(snapshot)) {
            std::this_thread::sleep_for(10ms);
            continue;
        }
        const bool active =
            snapshot.key_on && !session_.paused() && session_.speed() <= 1.0;
        if (!active) {
            suspended_.store(true);
            if (was_active) {
                if (!SDL_PauseAudioStreamDevice(stream_))
                    ++write_errors_;
                const int queued = SDL_GetAudioStreamQueued(stream_);
                if (queued > 0)
                    dropped_.fetch_add(static_cast<unsigned>(queued / 2));
                if (!SDL_ClearAudioStream(stream_))
                    ++write_errors_;
                was_active = false;
                had_output = false;
                device_started = false;
            }
            std::this_thread::sleep_for(10ms);
            continue;
        }
        const EventWindow window = session_.event_window();
        if (!was_active) {
            source.seek_to(snapshot.tick,
                           window.base_index + window.events.size());
            last_audio_tick = snapshot.tick;
            was_active = true;
            suspended_.store(false);
        }
        if (snapshot.tick > last_audio_tick) {
            constexpr long long max_gap_ticks = 495000;
            if (snapshot.tick - last_audio_tick > max_gap_ticks) {
                const long long start_tick = snapshot.tick - max_gap_ticks / 2;
                const auto first = std::lower_bound(
                    window.events.begin(), window.events.end(), start_tick,
                    [](const ma17::EmulatorEvent &event, long long tick) {
                        return event.tick < tick;
                    });
                source.seek_to(start_tick,
                               window.base_index +
                                   static_cast<std::size_t>(
                                       first - window.events.begin()));
                dropped_.fetch_add(static_cast<unsigned long long>(
                    (snapshot.tick - last_audio_tick - max_gap_ticks / 2) *
                    44100 / 990000));
            }
            const auto pcm = source.render_until(window.events, snapshot.tick,
                                                 window.base_index);
            const int queued = SDL_GetAudioStreamQueued(stream_);
            if (queued < 0) {
                ++write_errors_;
            } else if (!pcm.empty()) {
                if (queued == 0 && had_output && device_started)
                    ++empty_queue_observations_;
                if (queued >= 44100) {
                    dropped_.fetch_add(pcm.size());
                } else if (!SDL_PutAudioStreamData(
                               stream_, pcm.data(),
                               static_cast<int>(pcm.size() *
                                                sizeof(std::int16_t)))) {
                    ++write_errors_;
                } else {
                    had_output = true;
                    constexpr int startup_buffer_bytes = 4410;
                    if (!device_started && SDL_GetAudioStreamQueued(stream_) >=
                                               startup_buffer_bytes) {
                        if (SDL_ResumeAudioStreamDevice(stream_))
                            device_started = true;
                        else
                            ++write_errors_;
                    }
                }
            }
            last_audio_tick = snapshot.tick;
        }
        std::this_thread::sleep_for(10ms);
    }
}

} // namespace lab
