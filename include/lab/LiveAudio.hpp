#pragma once

#include "Lifetime.hpp"

#include <SDL3/SDL_audio.h>

#include <atomic>
#include <thread>

namespace lab {

class SimSession;

class LiveAudio final {
  public:
    LiveAudio(SimSession &session EMU_LIFETIMEBOUND,
              SDL_AudioStream *stream EMU_LIFETIMEBOUND);
    ~LiveAudio();
    LiveAudio(const LiveAudio &) = delete;
    LiveAudio &operator=(const LiveAudio &) = delete;

    void start();
    void stop();
    unsigned long long dropped_samples() const { return dropped_.load(); }
    unsigned long long mode_discarded_samples() const {
        return mode_discarded_.load();
    }
    unsigned long long empty_queue_observations() const {
        return empty_queue_observations_.load();
    }
    unsigned long long device_need_samples() const {
        return device_need_samples_.load();
    }
    unsigned long long write_errors() const { return write_errors_.load(); }
    unsigned int recent_pcm_peak() const { return recent_pcm_peak_.load(); }
    unsigned int max_pcm_peak() const { return max_pcm_peak_.load(); }
    bool suspended() const { return suspended_.load(); }

  private:
    static void SDLCALL on_stream_get(void *userdata, SDL_AudioStream *stream,
                                      int additional_amount, int total_amount);
    void run();

    SimSession &session_;
    SDL_AudioStream *stream_;
    std::thread worker_;
    bool callback_installed_ = false;
    std::atomic<bool> stop_{false};
    std::atomic<bool> suspended_{false};
    std::atomic<bool> device_started_{false};
    std::atomic<unsigned long long> dropped_{0};
    std::atomic<unsigned long long> mode_discarded_{0};
    std::atomic<unsigned long long> empty_queue_observations_{0};
    std::atomic<unsigned long long> device_need_samples_{0};
    std::atomic<unsigned long long> write_errors_{0};
    std::atomic<unsigned int> recent_pcm_peak_{0};
    std::atomic<unsigned int> max_pcm_peak_{0};
};

} // namespace lab
