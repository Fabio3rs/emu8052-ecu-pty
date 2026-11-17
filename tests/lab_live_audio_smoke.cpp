#include "lab/LiveAudio.hpp"
#include "lab/SimSession.hpp"

#include <SDL3/SDL.h>

#include <chrono>
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
                             "--physical-crank", "--stop-ticks", "2000000",
                             "--starter-ticks", "495000"});
    session.start();
    lab::LiveAudio audio(session, stream);
    audio.start();
    ma17::EmulatorSnapshot snapshot;
    const bool started = wait_until(
        [&] { return session.latest(snapshot) && snapshot.tick >= 100000; });
    session.set_speed(2.0);
    const bool fast_suspended = wait_until([&] { return audio.suspended(); });
    session.set_paused(true);
    session.set_speed(1.0);
    const bool pause_suspended = wait_until([&] { return audio.suspended(); });
    session.set_paused(false);
    const bool resumed = wait_until([&] { return !audio.suspended(); });
    session.set_key(false);
    const bool key_suspended = wait_until([&] { return audio.suspended(); });
    audio.stop();
    session.stop();
    const bool clean = audio.write_errors() == 0 && session.result() == 0;
    SDL_DestroyAudioStream(stream);
    SDL_Quit();
    if (!started || !fast_suspended || !pause_suspended || !resumed ||
        !key_suspended || !clean)
        return 1;
    std::printf("[LAB-AUDIO-THREAD] empty_queue=%llu dropped=%llu\n",
                audio.empty_queue_observations(), audio.dropped_samples());
    return 0;
}
