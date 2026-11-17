#include "lab/SimSession.hpp"

#include <chrono>
#include <cmath>
#include <cstdio>
#include <string>
#include <thread>
#include <vector>

namespace {

bool wait_for_tick(lab::SimSession &session, long long tick,
                   ma17::EmulatorSnapshot &snapshot) {
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (std::chrono::steady_clock::now() < deadline) {
        if (session.latest(snapshot) && snapshot.tick >= tick)
            return true;
        if (session.finished())
            return false;
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    return false;
}

bool wait_for_key(lab::SimSession &session, bool key_on,
                  ma17::EmulatorSnapshot &snapshot) {
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (std::chrono::steady_clock::now() < deadline) {
        if (session.latest(snapshot) && snapshot.key_on == key_on)
            return true;
        if (session.finished())
            return false;
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    return false;
}

} // namespace

int main(int argc, char **argv) {
    if (argc != 2)
        return 2;
    lab::SimSession session({"lab_session_smoke", argv[1], "--physical-crank",
                             "--stop-ticks", "5000000", "--starter-ticks",
                             "495000"});
    session.set_speed(16.0);
    session.start();
    ma17::EmulatorSnapshot first;
    if (!wait_for_tick(session, 150000, first) || first.pedal_pull_m != 0.0 ||
        first.applied_load_nm != 0.0)
        return 1;
    session.set_paused(true);
    std::this_thread::sleep_for(std::chrono::milliseconds(60));
    ma17::EmulatorSnapshot paused;
    if (!session.latest(paused))
        return 1;
    std::this_thread::sleep_for(std::chrono::milliseconds(60));
    ma17::EmulatorSnapshot still_paused;
    if (!session.latest(still_paused) || still_paused.tick != paused.tick)
        return 1;
    session.set_pedal(0.008);
    session.set_load(24.0);
    session.set_starter(true);
    session.set_paused(false);
    ma17::EmulatorSnapshot active;
    if (!wait_for_tick(session, paused.tick + 20000, active) ||
        std::abs(active.pedal_pull_m - 0.008) > 1e-9 ||
        std::abs(active.applied_load_nm - 24.0) > 1e-9 ||
        active.throttle_angle_rad <= first.throttle_angle_rad ||
        active.tps_track1_v <= first.tps_track1_v ||
        active.tps_track2_v <= first.tps_track2_v ||
        active.tps_track1_v > 5.0 || active.tps_track2_v > 5.0)
        return 1;
    const auto history = session.control_history();
    if (history.size() < 3 || history[0].type != lab::ControlType::Pedal ||
        history[1].type != lab::ControlType::Load ||
        history[2].type != lab::ControlType::Starter ||
        history[0].tick < paused.tick || history[0].tick != history[1].tick ||
        history[1].tick != history[2].tick)
        return 1;
    session.set_starter(false);
    session.set_key(false);
    ma17::EmulatorSnapshot key_off;
    if (!wait_for_key(session, false, key_off))
        return 1;
    ma17::EmulatorSnapshot coasting;
    if (!wait_for_tick(session, key_off.tick + 100000, coasting) ||
        coasting.key_on || coasting.pc != key_off.pc ||
        coasting.injector_pulses != key_off.injector_pulses ||
        coasting.burns != key_off.burns || coasting.rpm > key_off.rpm)
        return 1;
    session.set_key(true);
    ma17::EmulatorSnapshot key_on;
    if (!wait_for_key(session, true, key_on))
        return 1;
    ma17::EmulatorSnapshot resumed;
    if (!wait_for_tick(session, key_on.tick + 100000, resumed) ||
        !resumed.key_on || resumed.pc == coasting.pc)
        return 1;
    session.stop();
    if (session.result() != 0 || !session.finished())
        return 1;
    lab::SimSession scenario(
        {"lab_session_smoke", argv[1], "--physical-crank", "--stop-ticks",
         "600000", "--starter-ticks", "495000", "--pedal-step-tick", "100000",
         "--pedal-mm", "8", "--load-step-tick", "100000", "--load-nm", "24"});
    scenario.set_speed(16.0);
    scenario.start();
    ma17::EmulatorSnapshot physical;
    if (!wait_for_tick(scenario, 150000, physical) ||
        std::abs(physical.pedal_pull_m - 0.008) > 1e-9 ||
        std::abs(physical.applied_load_nm - 24.0) > 1e-9)
        return 1;
    scenario.stop();
    if (scenario.result() != 0 || !scenario.finished())
        return 1;
    lab::SimSession cooling({"lab_session_smoke",
                             argv[1],
                             "--physical-crank",
                             "--stop-ticks",
                             "16000000",
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
    cooling.set_speed(16.0);
    cooling.start();
    ma17::EmulatorSnapshot hot;
    if (!wait_for_tick(cooling, 3000000, hot) || hot.rpm < 500.0 ||
        hot.fuel_film_kg <= 0.0)
        return 1;
    cooling.set_key(false);
    ma17::EmulatorSnapshot off;
    if (!wait_for_key(cooling, false, off))
        return 1;
    ma17::EmulatorSnapshot cooled;
    if (!wait_for_tick(cooling, off.tick + 5000000, cooled) || cooled.key_on ||
        cooled.pc != off.pc || cooled.injector_pulses != off.injector_pulses ||
        cooled.burns != off.burns || cooled.coolant_c >= off.coolant_c - 0.01 ||
        cooled.fuel_film_kg >= off.fuel_film_kg * 0.5)
        return 1;
    cooling.set_load(0.0);
    cooling.set_key(true);
    cooling.set_starter(true);
    ma17::EmulatorSnapshot rekey;
    if (!wait_for_key(cooling, true, rekey) || rekey.applied_load_nm != 0.0 ||
        std::abs(rekey.coolant_c - cooled.coolant_c) > 0.01)
        return 1;
    ma17::EmulatorSnapshot cranking_again;
    if (!wait_for_tick(cooling, rekey.tick + 495000, cranking_again) ||
        cranking_again.rpm < 100.0)
        return 1;
    cooling.set_starter(false);
    ma17::EmulatorSnapshot restarted;
    if (!wait_for_tick(cooling, cranking_again.tick + 3000000, restarted) ||
        restarted.rpm < 500.0 || restarted.burns <= cooled.burns ||
        restarted.injector_pulses <= cooled.injector_pulses)
        return 1;
    cooling.set_load(24.0);
    ma17::EmulatorSnapshot later;
    if (!wait_for_tick(cooling, 15500000, later) ||
        later.applied_load_nm != 24.0 || later.rpm < 700.0 ||
        later.rpm > 1100.0 || later.burns <= restarted.burns ||
        cooling.event_overflow() != 0)
        return 1;
    cooling.stop();
    if (cooling.result() != 0 || !cooling.finished())
        return 1;
    std::printf("[LAB-SESSION-TEST] paused_tick=%lld resumed_tick=%lld "
                "coast_rpm=%.3f scenario_tick=%lld coolant=%.3f->%.3f "
                "film=%.9f->%.9f restart_rpm=%.1f later_rpm=%.1f events=%zu\n",
                paused.tick, resumed.tick, coasting.rpm, physical.tick,
                off.coolant_c, cooled.coolant_c, off.fuel_film_kg,
                cooled.fuel_film_kg, restarted.rpm, later.rpm,
                session.events().size());
    return 0;
}
