#include "lab/LiveAudio.hpp"
#include "lab/SimSession.hpp"

#include <SDL3/SDL.h>

#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <thread>

namespace {

template <typename Predicate> bool wait_until(Predicate ready) {
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (std::chrono::steady_clock::now() < deadline) {
        if (ready())
            return true;
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    return false;
}

} // namespace

int main(int argc, char **argv) {
    if (argc != 2 || !SDL_Init(SDL_INIT_AUDIO))
        return 2;
    const SDL_AudioSpec spec{SDL_AUDIO_S16, 1, 44100};
    SDL_AudioStream *stream = SDL_OpenAudioDeviceStream(
        SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, &spec, nullptr, nullptr);
    if (!stream) {
        SDL_Quit();
        return 2;
    }
    lab::SimSession session({"lab_live_audio_smoke", argv[1],
                             "--physical-crank", "--stop-ticks", "4000000",
                             "--starter-ticks", "495000"});
    session.start();
    lab::LiveAudio audio(session, stream);
    audio.start();
    ma17::EmulatorSnapshot snapshot;
    const bool started = wait_until(
        [&] { return session.latest(snapshot) && snapshot.tick >= 100000; });
    const bool mode_queue_paused = SDL_PauseAudioStreamDevice(stream);
    const std::array<std::int16_t, 4410> queued_audio{};
    const bool mode_queue_filled = SDL_PutAudioStreamData(
        stream, queued_audio.data(),
        static_cast<int>(queued_audio.size() * sizeof(std::int16_t)));
    const auto mode_discarded_before = audio.mode_discarded_samples();
    session.set_speed(2.0);
    const bool fast_suspended = wait_until([&] { return audio.suspended(); });
    const bool mode_discarded =
        audio.mode_discarded_samples() > mode_discarded_before;
    session.set_paused(true);
    session.set_speed(1.0);
    const bool pause_suspended = wait_until([&] { return audio.suspended(); });
    session.set_paused(false);
    const bool resumed = wait_until([&] { return !audio.suspended(); });
    const bool playback_started =
        wait_until([&] { return !SDL_AudioStreamDevicePaused(stream); });
    const auto dropped_before_backlog = audio.dropped_samples();
    const bool backlog_paused = SDL_PauseAudioStreamDevice(stream);
    const bool backlog_recovered = wait_until([&] {
        return audio.dropped_samples() > dropped_before_backlog &&
               !SDL_AudioStreamDevicePaused(stream) &&
               SDL_GetAudioStreamQueued(stream) < 44100;
    });
    session.set_key(false);
    const bool key_suspended = wait_until([&] {
        return audio.suspended() && SDL_AudioStreamDevicePaused(stream) &&
               SDL_GetAudioStreamQueued(stream) == 0 &&
               audio.recent_pcm_peak() == 0;
    });
    session.set_key(true);
    session.set_starter(true);
    const bool key_resumed = wait_until([&] {
        return !audio.suspended() && !SDL_AudioStreamDevicePaused(stream);
    });
    session.set_starter(false);
    audio.stop();
    session.stop();
    const bool clean = audio.write_errors() == 0 && session.result() == 0;
    SDL_DestroyAudioStream(stream);
    SDL_Quit();
    if (!started || !mode_queue_paused || !mode_queue_filled ||
        !fast_suspended || !mode_discarded || !pause_suspended || !resumed ||
        !playback_started || !backlog_paused || !backlog_recovered ||
        !key_suspended || !key_resumed || !clean)
        return 1;
    std::printf("[LAB-AUDIO-THREAD] empty_queue=%llu dropped=%llu mode=%llu\n",
                audio.empty_queue_observations(), audio.dropped_samples(),
                audio.mode_discarded_samples());
    return 0;
}
