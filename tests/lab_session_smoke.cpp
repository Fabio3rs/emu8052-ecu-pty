#include "lab/SimSession.hpp"

#include <chrono>
#include <cmath>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {

bool wait_for_tick(lab::SimSession &session, long long tick,
                   ma17::EmulatorSnapshot &snapshot) {
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(30);
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
        std::chrono::steady_clock::now() + std::chrono::seconds(30);
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
    try {
        session.start();
        return 1;
    } catch (const std::logic_error &) {
    }
    ma17::EmulatorSnapshot first;
    if (!wait_for_tick(session, 600000, first) || first.pedal_pull_m != 0.0 ||
        first.applied_load_nm != 0.0 ||
        std::abs(first.tdc_phase_rad - 2.0 * 3.14159265358979323846 / 3.0) >
            1e-12)
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
    if (session.step_ticks(0) || !session.step_ticks(7))
        return 1;
    ma17::EmulatorSnapshot first_step;
    if (!wait_for_tick(session, paused.tick + 7, first_step) ||
        first_step.tick != paused.tick + 7)
        return 1;
    if (!session.step_ticks(1203))
        return 1;
    ma17::EmulatorSnapshot second_step;
    if (!wait_for_tick(session, first_step.tick + 1203, second_step) ||
        second_step.tick != first_step.tick + 1203)
        return 1;
    std::this_thread::sleep_for(std::chrono::milliseconds(40));
    ma17::EmulatorSnapshot stationary;
    if (!session.latest(stationary) || stationary.tick != second_step.tick)
        return 1;
    if (!session.step_until_event(ma17::EmulatorEventType::IgnitionPin, 500000))
        return 1;
    ma17::EmulatorSnapshot event_step;
    long long ignition_tick = 0;
    const auto event_deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (std::chrono::steady_clock::now() < event_deadline) {
        for (const auto &event : session.events()) {
            if (event.type == ma17::EmulatorEventType::IgnitionPin &&
                event.tick > second_step.tick) {
                ignition_tick = event.tick;
                break;
            }
        }
        if (ignition_tick && session.latest(event_step) &&
            event_step.tick >= ignition_tick)
            break;
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    if (!ignition_tick || event_step.tick != ignition_tick)
        return 1;
    std::this_thread::sleep_for(std::chrono::milliseconds(40));
    if (!session.latest(stationary) || stationary.tick != ignition_tick)
        return 1;
    if (session.step_time(std::chrono::milliseconds(0)) ||
        !session.step_time(std::chrono::milliseconds(3)))
        return 1;
    ma17::EmulatorSnapshot time_step;
    if (!wait_for_tick(session, ignition_tick + 2970, time_step) ||
        time_step.tick != ignition_tick + 2970)
        return 1;
    if (!session.step_until_event(ma17::EmulatorEventType::Combustion, 3))
        return 1;
    ma17::EmulatorSnapshot bounded_step;
    if (!wait_for_tick(session, time_step.tick + 3, bounded_step) ||
        bounded_step.tick != time_step.tick + 3)
        return 1;
    session.set_pedal(0.008);
    session.set_load(24.0);
    session.set_starter(true);
    session.set_paused(false);
    ma17::EmulatorSnapshot active;
    if (!wait_for_tick(session, bounded_step.tick + 20000, active) ||
        std::abs(active.pedal_pull_m - 0.008) > 1e-9 ||
        std::abs(active.applied_load_nm - 24.0) > 1e-9 ||
        active.throttle_angle_rad <= first.throttle_angle_rad ||
        active.tps_track1_v <= first.tps_track1_v ||
        active.tps_track2_v <= first.tps_track2_v ||
        active.tps_track1_v > 5.0 || active.tps_track2_v > 5.0)
        return 1;
    const auto history = session.control_history();
    if (history.size() != 10 || history[0].type != lab::ControlType::Pause ||
        history[0].tick != paused.tick ||
        history[1].type != lab::ControlType::StepTicks ||
        history[1].tick != paused.tick || history[1].value != 7.0 ||
        history[2].type != lab::ControlType::StepTicks ||
        history[2].tick != first_step.tick || history[2].value != 1203.0 ||
        history[3].type != lab::ControlType::StepIgnition ||
        history[3].tick != second_step.tick ||
        history[4].type != lab::ControlType::StepTicks ||
        history[4].tick != ignition_tick || history[4].value != 2970.0 ||
        history[5].type != lab::ControlType::StepCombustion ||
        history[5].tick != time_step.tick ||
        history[6].type != lab::ControlType::Resume ||
        history[6].tick != bounded_step.tick ||
        history[7].type != lab::ControlType::Pedal ||
        history[8].type != lab::ControlType::Load ||
        history[9].type != lab::ControlType::Starter ||
        history[7].tick != history[8].tick ||
        history[8].tick != history[9].tick)
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
    lab::SimSession replay({"lab_session_smoke", argv[1], "--physical-crank",
                            "--stop-ticks", std::to_string(active.tick),
                            "--starter-ticks", "495000"});
    for (const auto &control : history)
        replay.schedule_control(control);
    replay.set_speed(16.0);
    replay.start();
    ma17::EmulatorSnapshot replayed;
    if (!wait_for_tick(replay, active.tick, replayed) ||
        replayed.tick != active.tick || replayed.pc != active.pc ||
        replayed.ram47 != active.ram47 ||
        replayed.injector_pulses != active.injector_pulses ||
        replayed.burns != active.burns ||
        std::abs(replayed.rpm - active.rpm) > 1e-9 ||
        std::abs(replayed.crank_angle_rad - active.crank_angle_rad) > 1e-9)
        return 1;
    replay.stop();
    lab::SimSession reference({"lab_session_smoke", argv[1], "--physical-crank",
                               "--stop-ticks", std::to_string(second_step.tick),
                               "--starter-ticks", "495000"});
    reference.set_speed(16.0);
    reference.start();
    ma17::EmulatorSnapshot continuous;
    if (!wait_for_tick(reference, second_step.tick, continuous) ||
        continuous.tick != second_step.tick ||
        continuous.pc != second_step.pc ||
        continuous.ram47 != second_step.ram47 ||
        continuous.injector_pulses != second_step.injector_pulses ||
        continuous.burns != second_step.burns ||
        std::abs(continuous.rpm - second_step.rpm) > 1e-9 ||
        std::abs(continuous.crank_angle_rad - second_step.crank_angle_rad) >
            1e-9)
        return 1;
    reference.stop();
    lab::SimSession event_reference(
        {"lab_session_smoke", argv[1], "--physical-crank", "--stop-ticks",
         std::to_string(ignition_tick), "--starter-ticks", "495000"});
    event_reference.set_speed(16.0);
    event_reference.start();
    ma17::EmulatorSnapshot continuous_event;
    if (!wait_for_tick(event_reference, ignition_tick, continuous_event) ||
        continuous_event.tick != event_step.tick ||
        continuous_event.pc != event_step.pc ||
        continuous_event.ram47 != event_step.ram47 ||
        continuous_event.injector_pulses != event_step.injector_pulses ||
        continuous_event.burns != event_step.burns ||
        std::abs(continuous_event.rpm - event_step.rpm) > 1e-9 ||
        std::abs(continuous_event.crank_angle_rad -
                 event_step.crank_angle_rad) > 1e-9)
        return 1;
    event_reference.stop();
    lab::SimSession initial_pause({"lab_session_smoke", argv[1],
                                   "--physical-crank", "--stop-ticks", "600000",
                                   "--starter-ticks", "495000"});
    initial_pause.set_paused(true);
    initial_pause.start();
    std::this_thread::sleep_for(std::chrono::milliseconds(40));
    ma17::EmulatorSnapshot initial;
    if (initial_pause.latest(initial) || !initial_pause.step_ticks(7) ||
        !wait_for_tick(initial_pause, 7, initial) || initial.tick != 7)
        return 1;
    initial_pause.stop();
    lab::SimSession cancelled_pause({"lab_session_smoke", argv[1],
                                     "--physical-crank", "--stop-ticks",
                                     "600000", "--starter-ticks", "495000"});
    cancelled_pause.set_paused(true);
    cancelled_pause.start();
    cancelled_pause.stop();
    if (cancelled_pause.latest(initial) || !cancelled_pause.finished() ||
        cancelled_pause.result() != 0)
        return 1;
    lab::SimSession starter_step({"lab_session_smoke", argv[1],
                                  "--physical-crank", "--stop-ticks", "600000",
                                  "--starter-ticks", "495000"});
    starter_step.schedule_control({0, lab::ControlType::Starter, 1.0});
    starter_step.schedule_control({500007, lab::ControlType::Load, 24.0});
    starter_step.set_paused(true);
    starter_step.start();
    ma17::EmulatorSnapshot short_step;
    if (!starter_step.step_ticks(7) ||
        !wait_for_tick(starter_step, 7, short_step) || short_step.tick != 7 ||
        !starter_step.step_ticks(500003) ||
        !wait_for_tick(starter_step, 500010, short_step) ||
        short_step.tick != 500010)
        return 1;
    starter_step.stop();
    const auto stepped_history = starter_step.control_history();
    if (stepped_history.size() != 5 ||
        stepped_history.back().type != lab::ControlType::Load ||
        stepped_history.back().tick != 500007 ||
        std::abs(short_step.applied_load_nm - 24.0) > 1e-9)
        return 1;
    lab::SimSession starter_reference({"lab_session_smoke", argv[1],
                                       "--physical-crank", "--stop-ticks",
                                       "500010", "--starter-ticks", "495000"});
    starter_reference.schedule_control({0, lab::ControlType::Starter, 1.0});
    starter_reference.schedule_control({500007, lab::ControlType::Load, 24.0});
    starter_reference.set_speed(16.0);
    starter_reference.start();
    ma17::EmulatorSnapshot starter_continuous;
    if (!wait_for_tick(starter_reference, 500010, starter_continuous) ||
        starter_continuous.tick != short_step.tick ||
        starter_continuous.pc != short_step.pc ||
        std::abs(starter_continuous.rpm - short_step.rpm) > 1e-9 ||
        std::abs(starter_continuous.crank_angle_rad -
                 short_step.crank_angle_rad) > 1e-9)
        return 1;
    starter_reference.stop();
    lab::SimSession scenario(
        {"lab_session_smoke", argv[1], "--physical-crank", "--stop-ticks",
         "600000", "--starter-ticks", "495000", "--pedal-step-tick", "100000",
         "--pedal-mm", "8", "--load-step-tick", "100000", "--load-nm", "24"});
    scenario.set_speed(16.0);
    scenario.start();
    ma17::EmulatorSnapshot physical;
    if (!wait_for_tick(scenario, 150000, physical) ||
        std::abs(physical.pedal_pull_m - 0.008) > 1e-9 ||
        std::abs(physical.applied_load_nm - 24.0) > 1e-9 ||
        physical.idle_bridge_candidate)
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
        hot.fuel_film_kg <= 0.0 || !hot.idle_bridge_candidate ||
        !std::isfinite(hot.idle_stem_m) || hot.idle_stem_m < 0.0 ||
        hot.idle_stem_m > 0.03)
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
    std::size_t spark_count = 0;
    for (const auto &event : cooling.events()) {
        if (event.type != ma17::EmulatorEventType::Spark)
            continue;
        if (event.pair_index > 1 || event.pair_index != event.channel)
            return 1;
        ++spark_count;
    }
    if (spark_count == 0)
        return 1;
    std::printf("[LAB-SESSION-TEST] paused_tick=%lld resumed_tick=%lld "
                "coast_rpm=%.3f scenario_tick=%lld coolant=%.3f->%.3f "
                "film=%.9f->%.9f restart_rpm=%.1f later_rpm=%.1f "
                "events=%zu sparks=%zu\n",
                paused.tick, resumed.tick, coasting.rpm, physical.tick,
                off.coolant_c, cooled.coolant_c, off.fuel_film_kg,
                cooled.fuel_film_kg, restarted.rpm, later.rpm,
                session.events().size(), spark_count);
    return 0;
}
