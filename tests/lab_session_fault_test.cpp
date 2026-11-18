// A model exception on the simulation thread must not reach std::terminate:
// the session stops, is paused, and publishes the fault with its reason.
#include "lab/SimSession.hpp"

#include <chrono>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <thread>

namespace {

bool wait_for(const std::function<bool()> &condition) {
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(30);
    while (std::chrono::steady_clock::now() < deadline) {
        if (condition())
            return true;
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    return false;
}

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            std::fprintf(stderr, "CHECK failed: %s (line %d)\n", #condition,   \
                         __LINE__);                                            \
            return 1;                                                          \
        }                                                                      \
    } while (false)

} // namespace

int main(int argc, char **argv) {
    if (argc != 2)
        return 2;
    lab::SimSession session({"lab_session_fault", argv[1], "--physical-crank",
                             "--drivetrain", "--stop-ticks", "20000000",
                             "--starter-ticks", "495000"});
    session.set_speed(16.0);
    int batches = 0;
    // The models throw std::invalid_argument for invalid drivetrain input;
    // raise the same type on the simulation thread after a valid warm-up.
    session.set_loop_hook_for_test([&batches] {
        if (++batches == 2000)
            throw std::invalid_argument("invalid drivetrain step (injected)");
    });
    session.start();
    CHECK(wait_for([&] { return session.finished(); }));
    // Reaching this line at all proves the process survived the exception.
    CHECK(session.faulted());
    CHECK(session.result() != 0);
    CHECK(
        std::strstr(session.fault_reason().c_str(), "invalid drivetrain step"));
    CHECK(session.paused());

    ma17::EmulatorSnapshot snapshot;
    CHECK(session.latest(snapshot));
    CHECK(snapshot.simulation_fault);
    CHECK(!snapshot.drivetrain_available);
    CHECK(snapshot.tick > 0); // last valid values are kept, flagged as faulted
    session.stop();           // joining a finished worker is safe

    // A healthy run never reports a fault.
    lab::SimSession healthy({"lab_session_fault", argv[1], "--physical-crank",
                             "--stop-ticks", "600000", "--starter-ticks",
                             "495000"});
    healthy.set_speed(16.0);
    healthy.start();
    CHECK(wait_for([&] { return healthy.finished(); }));
    CHECK(!healthy.faulted());
    CHECK(healthy.fault_reason().empty());
    ma17::EmulatorSnapshot ok;
    CHECK(healthy.latest(ok) && !ok.simulation_fault);
    std::printf("[LAB-SIM-FAULT-TEST] reason=\"%s\" batches=%d\n",
                session.fault_reason().c_str(), batches);
    return 0;
}
