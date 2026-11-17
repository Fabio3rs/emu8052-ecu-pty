#include "lab/SimSession.hpp"

#include <chrono>
#include <cmath>
#include <cstdio>
#include <thread>

int main(int argc, char **argv) {
    if (argc != 2)
        return 2;
    lab::SimSession session({"lab_live_determinism",
                             argv[1],
                             "--physical-crank",
                             "--stop-ticks",
                             "10000000",
                             "--starter-ticks",
                             "495000",
                             "--adc7-mv",
                             "1232",
                             "--idle-bridge-p15-p16",
                             "--idle-contact-p46",
                             "--coolant-c",
                             "90",
                             "--idle-min-stop-mrad",
                             "5",
                             "--throttle-leak-mm2",
                             "9",
                             "--load-step-tick",
                             "800000",
                             "--load-nm",
                             "24",
                             "--lambda-adc-gain",
                             "5"});
    session.set_speed(16.0);
    session.start();
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(20);
    while (!session.finished() && std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    if (!session.finished()) {
        session.stop();
        return 1;
    }
    ma17::EmulatorSnapshot snapshot;
    if (!session.latest(snapshot) || session.result() != 0 ||
        snapshot.tick != 10000000 || std::abs(snapshot.rpm - 821.758) > 0.01 ||
        snapshot.ram47 != 32 || snapshot.injector_pulses != 266 ||
        session.events().empty() || session.event_overflow() != 0)
        return 1;
    std::printf("[LAB-DETERMINISM] tick=%lld rpm=%.3f ram47=%u "
                "cc3=%llu events=%zu\n",
                snapshot.tick, snapshot.rpm,
                static_cast<unsigned>(snapshot.ram47), snapshot.injector_pulses,
                session.events().size());
    return 0;
}
