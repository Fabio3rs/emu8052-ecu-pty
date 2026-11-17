#pragma once

#include <SDL3/SDL_audio.h>

#include <atomic>
#include <thread>

namespace lab {

class SimSession;

class LiveAudio final {
  public:
    LiveAudio(SimSession &session, SDL_AudioStream *stream);
    ~LiveAudio();
    LiveAudio(const LiveAudio &) = delete;
    LiveAudio &operator=(const LiveAudio &) = delete;

    void start();
    void stop();
    unsigned long long dropped_samples() const { return dropped_.load(); }
    unsigned long long empty_queue_observations() const {
        return empty_queue_observations_.load();
    }
    unsigned long long write_errors() const { return write_errors_.load(); }
    bool suspended() const { return suspended_.load(); }

  private:
    void run();

    SimSession &session_;
    SDL_AudioStream *stream_;
    std::thread worker_;
    std::atomic<bool> stop_{false};
    std::atomic<bool> suspended_{false};
    std::atomic<unsigned long long> dropped_{0};
    std::atomic<unsigned long long> empty_queue_observations_{0};
    std::atomic<unsigned long long> write_errors_{0};
};

} // namespace lab
