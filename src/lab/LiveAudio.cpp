#include "lab/LiveAudio.hpp"

#include "lab/SimSession.hpp"
#include "lab/StreamingAudio.hpp"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
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
    callback_installed_ =
        SDL_SetAudioStreamGetCallback(stream_, &LiveAudio::on_stream_get, this);
    if (!callback_installed_)
        ++write_errors_;
    worker_ = std::thread(&LiveAudio::run, this);
}

void LiveAudio::stop() {
    stop_.store(true);
    device_started_.store(false);
    if (worker_.joinable())
        worker_.join();
    if (callback_installed_) {
        if (!SDL_SetAudioStreamGetCallback(stream_, nullptr, nullptr))
            ++write_errors_;
        callback_installed_ = false;
    }
}

void SDLCALL LiveAudio::on_stream_get(void *userdata, SDL_AudioStream *,
                                      int additional_amount, int) {
    auto *self = static_cast<LiveAudio *>(userdata);
    if (additional_amount > 0 && self->device_started_.load())
        self->device_need_samples_.fetch_add(
            (static_cast<unsigned long long>(additional_amount) + 1ULL) /
            sizeof(std::int16_t));
}

void LiveAudio::run() {
    using namespace std::chrono_literals;
    StreamingAudio source;
    long long last_audio_tick = 0;
    std::size_t cursor = 0;
    bool was_active = false;
    bool had_output = false;
    bool device_started = false;
    while (!stop_.load()) {
        ma17::EmulatorSnapshot snapshot;
        if (!session_.latest(snapshot)) {
            std::this_thread::sleep_for(10ms);
            continue;
        }
        const double current_speed = session_.speed();
        const bool active =
            snapshot.key_on && !session_.paused() && current_speed <= 1.0;
        if (!active) {
            suspended_.store(true);
            recent_pcm_peak_.store(0);
            if (was_active) {
                device_started_.store(false);
                if (!SDL_PauseAudioStreamDevice(stream_))
                    ++write_errors_;
                const int queued = SDL_GetAudioStreamQueued(stream_);
                if (queued < 0)
                    ++write_errors_;
                if (!SDL_ClearAudioStream(stream_))
                    ++write_errors_;
                else if (queued > 0)
                    mode_discarded_.fetch_add(
                        static_cast<unsigned>(queued / 2));
                applied_ratio_ = 1.0f;
                if (!SDL_SetAudioStreamFrequencyRatio(stream_, 1.0f))
                    ++write_errors_;
                was_active = false;
                had_output = false;
                device_started = false;
            }
            std::this_thread::sleep_for(10ms);
            continue;
        }
        const float target_ratio = static_cast<float>(current_speed);
        if (target_ratio != applied_ratio_) {
            if (SDL_SetAudioStreamFrequencyRatio(stream_, target_ratio))
                applied_ratio_ = target_ratio;
            else
                ++write_errors_;
        }
        if (!was_active) {
            const EventWindow window = session_.event_window();
            // The event copy may advance beyond the separately read snapshot.
            const auto first_future = std::upper_bound(
                window.events.begin(), window.events.end(), snapshot.tick,
                [](long long tick, const ma17::EmulatorEvent &event) {
                    return tick < event.tick;
                });
            cursor = window.base_index + static_cast<std::size_t>(
                                            first_future -
                                            window.events.begin());
            source.seek_to(snapshot.tick, cursor);
            last_audio_tick = snapshot.tick;
            was_active = true;
            suspended_.store(false);
        }
        if (snapshot.tick > last_audio_tick) {
            constexpr long long max_gap_ticks = 495000;
            if (snapshot.tick - last_audio_tick > max_gap_ticks) {
                const EventWindow window = session_.event_window();
                const long long start_tick = snapshot.tick - max_gap_ticks / 2;
                const auto first = std::lower_bound(
                    window.events.begin(), window.events.end(), start_tick,
                    [](const ma17::EmulatorEvent &event, long long tick) {
                        return event.tick < tick;
                    });
                cursor = window.base_index +
                         static_cast<std::size_t>(
                             first - window.events.begin());
                source.seek_to(start_tick, cursor);
                dropped_.fetch_add(static_cast<unsigned long long>(
                    (snapshot.tick - last_audio_tick - max_gap_ticks / 2) *
                    44100 / 990000));
            }
            const auto delta = session_.events_since(cursor);
            const std::size_t base = std::max(cursor, delta.base_index);
            cursor = delta.next_index;
            const auto pcm = source.render_until(delta.events, snapshot.tick,
                                                 base);
            const int queued = SDL_GetAudioStreamQueued(stream_);
            bool queue_ready = queued >= 0;
            if (queued < 0) {
                ++write_errors_;
            } else if (queued >= 44100) {
                // Keep the newest physical events when device playback lags.
                device_started_.store(false);
                if (!SDL_PauseAudioStreamDevice(stream_))
                    ++write_errors_;
                if (SDL_ClearAudioStream(stream_))
                    dropped_.fetch_add(static_cast<unsigned>(queued / 2));
                else {
                    ++write_errors_;
                    queue_ready = false;
                }
                device_started = false;
                had_output = false;
            }
            if (queue_ready && !pcm.empty()) {
                if (queued == 0 && had_output && device_started)
                    ++empty_queue_observations_;
                if (!SDL_PutAudioStreamData(
                        stream_, pcm.data(),
                        static_cast<int>(pcm.size() * sizeof(std::int16_t)))) {
                    ++write_errors_;
                    recent_pcm_peak_.store(0);
                } else {
                    unsigned int peak = 0;
                    for (const std::int16_t sample : pcm)
                        peak = std::max(
                            peak, static_cast<unsigned int>(
                                      std::abs(static_cast<int>(sample))));
                    recent_pcm_peak_.store(peak);
                    if (peak > max_pcm_peak_.load())
                        max_pcm_peak_.store(peak);
                    had_output = true;
                    constexpr int startup_buffer_bytes = 4410;
                    if (!device_started && SDL_GetAudioStreamQueued(stream_) >=
                                               startup_buffer_bytes) {
                        device_started_.store(true);
                        if (SDL_ResumeAudioStreamDevice(stream_))
                            device_started = true;
                        else {
                            device_started_.store(false);
                            ++write_errors_;
                        }
                    }
                }
            } else if (!queue_ready) {
                recent_pcm_peak_.store(0);
                dropped_.fetch_add(pcm.size());
            }
            last_audio_tick = snapshot.tick;
        }
        std::this_thread::sleep_for(10ms);
    }
}

} // namespace lab
