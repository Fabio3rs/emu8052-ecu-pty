// Lab path of the control limits (GOAL_DYNO_ROM 4): a full-open request reaches 90 degrees
// and 300 N.m reaches the plant. LLM-written (Claude).
#include "engine/ControlLimits.hpp"
#include "lab/SimSession.hpp"

#include <chrono>
#include <cmath>
#include <cstdio>
#include <thread>

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    constexpr double half_pi = 1.5707963267948966;
    if (std::abs(engine::max_pedal_pull_m() - 0.04027) > 1e-5 || engine::max_brake_nm() != 400.0)
        return 3;
    lab::SimSession session({"lab_control_limits", argv[1], "--physical-crank", "--stop-ticks",
                             "3000000", "--starter-ticks", "495000"});
    session.set_speed(16.0);
    session.set_pedal(1.0);   // far beyond the cable: clamps to the travel, not to 25 mm
    session.set_load(300.0);  // beyond the old 60 N.m clamp
    session.start();
    ma17::EmulatorSnapshot s;
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(60);
    while (std::chrono::steady_clock::now() < deadline) {
        if (session.latest(s) && s.tick >= 200000) break;
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    if (s.tick < 200000) return 4;
    if (std::abs(s.pedal_pull_m - engine::max_pedal_pull_m()) > 1e-9) return 5;
    if (std::abs(s.throttle_angle_rad - half_pi) > 1e-6) return 6;
    if (std::abs(s.applied_load_nm - 300.0) > 1e-9) return 7;
    // The plant response, not just the command: 300 N.m stalls the engine.
    const auto stall_deadline = std::chrono::steady_clock::now() + std::chrono::seconds(90);
    while (std::chrono::steady_clock::now() < stall_deadline) {
        if (session.latest(s) && s.tick >= 2000000) break;
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    if (s.tick < 2000000) return 8;
    if (s.rpm > 1.0) return 9;
    std::printf("lab control limits ok: pull %.5f m, angle %.6f rad, load %.1f N.m\n",
                s.pedal_pull_m, s.throttle_angle_rad, s.applied_load_nm);
    return 0;
}
