#include "lab/SimSession.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <thread>

namespace {

struct Result {
    ma17::EmulatorSnapshot snapshot;
    std::vector<ma17::EmulatorEvent> events;
    std::vector<lab::AppliedControl> history;
    std::vector<ma17::EmulatorSnapshot> samples;
    unsigned long long raw_evicted = 0;
    std::size_t event_base_index = 0;
    unsigned long long event_overflow = 0;
};

bool run(const char *rom, const std::vector<lab::AppliedControl> &controls,
         Result &result, std::size_t event_capacity = 65536,
         bool drivetrain = false, long long stop_tick = 1200000) {
    std::vector<std::string> args{"lab_control_replay", rom, "--physical-crank",
                             "--stop-ticks", std::to_string(stop_tick), "--starter-ticks",
                             "495000", "--idle-contact-p46",
                             "--idle-bridge-p15-p16", "--adc7-mv", "1232"};
    if (drivetrain)
        args.push_back("--drivetrain");
    lab::SimSession session(args, event_capacity);
    for (const auto &control : controls)
        session.schedule_control(control);
    session.set_speed(16.0);
    session.start();
    const auto deadline =
        std::chrono::steady_clock::now() +
        std::chrono::seconds(stop_tick > 1200000 ? 120 : 30);
    while (!session.finished() && std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    if (!session.finished()) {
        session.stop();
        return false;
    }
    if (session.result() != 0 || !session.latest(result.snapshot))
        return false;
    const auto window = session.event_window();
    result.events = window.events;
    result.event_base_index = window.base_index;
    result.event_overflow = session.event_overflow();
    result.history = session.control_history();
    result.samples = session.snapshot_window(0);
    result.raw_evicted = session.snapshot_retention().raw_evicted;
    return true;
}

} // namespace

int main(int argc, char **argv) {
    if (argc != 2)
        return 2;
    const std::vector<lab::AppliedControl> drive_commands{
        {495000, lab::ControlType::Gear, 1.0},
        {495000, lab::ControlType::ClutchPressure, 0.1},
        {800000, lab::ControlType::ClutchPressure, 0.0},
        {800000, lab::ControlType::Gear, 2.0},
        {900000, lab::ControlType::ClutchPressure, 0.1}};
    Result driven, driven_replay;
    std::vector<lab::AppliedControl> drive_loaded;
    if (!run(argv[1], drive_commands, driven, 65536, true) ||
        !driven.snapshot.drivetrain_available ||
        driven.snapshot.transmission_gear != 2 ||
        driven.snapshot.clutch_pressure != 0.1 ||
        driven.snapshot.vehicle_speed_kmh <= 0.0 ||
        driven.snapshot.clutch_heat_j <= 0.0 ||
        !lab::save_control_trace("lab-drive-controls.txt", driven.history) ||
        !lab::load_control_trace("lab-drive-controls.txt", drive_loaded) ||
        !run(argv[1], drive_loaded, driven_replay, 65536, true) ||
        driven_replay.snapshot.vehicle_speed_kmh != driven.snapshot.vehicle_speed_kmh ||
        driven_replay.snapshot.clutch_heat_j != driven.snapshot.clutch_heat_j ||
        driven_replay.snapshot.clutch_crank_torque_nm != driven.snapshot.clutch_crank_torque_nm ||
        driven_replay.snapshot.rpm != driven.snapshot.rpm ||
        driven_replay.history.size() != drive_commands.size())
        return 1;
    for (std::size_t index = 0; index < drive_commands.size(); ++index) {
        if (driven_replay.history[index].tick != drive_commands[index].tick ||
            driven_replay.history[index].type != drive_commands[index].type ||
            driven_replay.history[index].value != drive_commands[index].value)
            return 1;
    }
    Result drive_archive;
    if (!run(argv[1], drive_commands, drive_archive, 65536, true, 10000000) ||
        drive_archive.raw_evicted == 0 || driven.raw_evicted != 0)
        return 1;
    const auto retained = [&](const ma17::EmulatorSnapshot &sample) {
        const auto found = std::lower_bound(
            drive_archive.samples.begin(), drive_archive.samples.end(), sample.tick,
            [](const auto &entry, long long tick) { return entry.tick < tick; });
        return found != drive_archive.samples.end() && found->tick == sample.tick &&
            found->transmission_gear == sample.transmission_gear &&
            found->vehicle_speed_kmh == sample.vehicle_speed_kmh &&
            found->clutch_pressure == sample.clutch_pressure &&
            found->clutch_crank_torque_nm == sample.clutch_crank_torque_nm &&
            found->clutch_heat_j == sample.clutch_heat_j;
    };
    for (std::size_t index = 1; index < driven.samples.size(); ++index) {
        if (driven.samples[index].transmission_gear !=
                driven.samples[index - 1].transmission_gear &&
            (!retained(driven.samples[index - 1]) || !retained(driven.samples[index])))
            return 1;
    }
    // Compare each complete 100 ms acquisition bucket against the unabridged run.
    for (long long start = driven.samples.front().tick;
         start + 99000 < 1200000; start += 99000) {
        const auto begin = std::lower_bound(driven.samples.begin(), driven.samples.end(), start,
            [](const auto &entry, long long tick) { return entry.tick < tick; });
        const auto end = std::lower_bound(begin, driven.samples.end(), start + 99000,
            [](const auto &entry, long long tick) { return entry.tick < tick; });
        if (begin == end)
            return 1;
        for (auto field : {&ma17::EmulatorSnapshot::vehicle_speed_kmh,
                           &ma17::EmulatorSnapshot::clutch_pressure,
                           &ma17::EmulatorSnapshot::clutch_crank_torque_nm,
                           &ma17::EmulatorSnapshot::clutch_heat_j}) {
            const auto less = [field](const auto &a, const auto &b) {
                return a.*field < b.*field;
            };
            if (!retained(*std::min_element(begin, end, less)) ||
                !retained(*std::max_element(begin, end, less)))
                return 1;
        }
    }
    const std::array<lab::AppliedControl, 11> commands{{
        {0, lab::ControlType::Key, 0.0},
        {50000, lab::ControlType::Key, 1.0},
        {50000, lab::ControlType::Pause, 0.0},
        {50000, lab::ControlType::StepTicks, 7.0},
        {50007, lab::ControlType::Starter, 1.0},
        {50007, lab::ControlType::Resume, 0.0},
        {400000, lab::ControlType::Starter, 0.0},
        {500000, lab::ControlType::Pedal, 0.008},
        {700000, lab::ControlType::Load, 24.0},
        {800000, lab::ControlType::VehicleSpeed, 60.0},
        {900000, lab::ControlType::Pedal, 0.0},
    }};
    Result original;
    if (!run(argv[1], {commands.begin(), commands.end()}, original) ||
        original.history.size() != commands.size() ||
        original.history[4].tick != 50007 ||
        original.snapshot.crank_angle_rad <= 0.0 ||
        original.snapshot.vehicle_speed_kmh <= 0.0 ||
        original.events.empty() ||
        original.event_overflow != 0)
        return 1;
    const char *trace_path = "lab-control-trace-test.txt";
    std::vector<lab::AppliedControl> loaded;
    if (!lab::save_control_trace(trace_path, original.history) ||
        !lab::load_control_trace(trace_path, loaded) ||
        loaded.size() != original.history.size())
        return 1;
    lab::ControlTraceMetadata metadata;
    metadata.present = true;
    metadata.rom_size = 32768;
    metadata.rom_hash = 0x1234abcd;
    metadata.scenario_args = {"--adc7-mv", "1232", "option with spaces"};
    const char *v2_path = "lab-control-trace-v2-test.txt";
    lab::ControlTraceMetadata loaded_metadata;
    if (!lab::save_control_trace(v2_path, loaded, &metadata) ||
        !lab::load_control_trace(v2_path, loaded, &loaded_metadata) ||
        !loaded_metadata.present ||
        loaded_metadata.rom_size != metadata.rom_size ||
        loaded_metadata.rom_hash != metadata.rom_hash ||
        loaded_metadata.scenario_args != metadata.scenario_args ||
        loaded.size() != original.history.size())
        return 1;
    Result replay;
    if (!run(argv[1], loaded, replay) || replay.event_overflow != 0 ||
        replay.history.size() != original.history.size() ||
        replay.snapshot.tick != original.snapshot.tick ||
        replay.snapshot.pc != original.snapshot.pc ||
        replay.snapshot.rpm != original.snapshot.rpm ||
        replay.snapshot.crank_angle_rad != original.snapshot.crank_angle_rad ||
        replay.snapshot.vehicle_speed_kmh !=
            original.snapshot.vehicle_speed_kmh ||
        replay.snapshot.ram47 != original.snapshot.ram47 ||
        replay.snapshot.injector_pulses != original.snapshot.injector_pulses ||
        replay.snapshot.burns != original.snapshot.burns ||
        replay.events.size() != original.events.size())
        return 1;
    for (std::size_t i = 0; i < replay.history.size(); ++i)
        if (replay.history[i].tick != original.history[i].tick ||
            replay.history[i].type != original.history[i].type ||
            replay.history[i].value != original.history[i].value)
            return 1;
    for (std::size_t i = 0; i < replay.events.size(); ++i)
        if (replay.events[i].tick != original.events[i].tick ||
            replay.events[i].type != original.events[i].type ||
            replay.events[i].channel != original.events[i].channel ||
            replay.events[i].high != original.events[i].high ||
            replay.events[i].burned_fuel_kg !=
                original.events[i].burned_fuel_kg)
            return 1;
    Result bounded;
    if (original.events.size() < 8 || !run(argv[1], loaded, bounded, 8) ||
        bounded.events.size() != 8 ||
        bounded.event_base_index != original.events.size() - 8 ||
        bounded.event_overflow != original.events.size() - 8)
        return 1;
    for (std::size_t index = 0; index < bounded.events.size(); ++index) {
        const auto &expected =
            original.events[bounded.event_base_index + index];
        const auto &actual = bounded.events[index];
        if (actual.tick != expected.tick || actual.type != expected.type ||
            actual.channel != expected.channel || actual.high != expected.high)
            return 1;
    }
    {
        std::ofstream invalid("lab-control-trace-invalid.txt");
        invalid << "sevel-ma17-controls-v1\n50000 starter 2\n";
    }
    if (lab::load_control_trace("lab-control-trace-invalid.txt", loaded) ||
        loaded.size() != original.history.size())
        return 1;
    {
        std::ofstream invalid("lab-control-trace-invalid-v2.txt");
        invalid << "sevel-ma17-controls-v2\nrom 32768 1234abcd\n"
                   "args 1\narg unquoted\ncontrols\n";
    }
    if (lab::load_control_trace("lab-control-trace-invalid-v2.txt", loaded,
                                &loaded_metadata) ||
        loaded.size() != original.history.size() ||
        loaded_metadata.scenario_args != metadata.scenario_args)
        return 1;
    lab::SimSession terminal_pause({"lab_control_replay", argv[1],
                                    "--physical-crank", "--stop-ticks", "50000",
                                    "--starter-ticks", "1000"});
    terminal_pause.set_pedal_target(0.010);
    terminal_pause.schedule_control({50000, lab::ControlType::Pause, 0.0});
    terminal_pause.set_speed(16.0);
    terminal_pause.start();
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (!terminal_pause.finished() &&
           std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    ma17::EmulatorSnapshot terminal_snapshot;
    if (!terminal_pause.finished() || terminal_pause.result() != 0 ||
        !terminal_pause.latest(terminal_snapshot) ||
        terminal_snapshot.tick != 50000 ||
        terminal_snapshot.pedal_pull_m < 0.0006 ||
        terminal_snapshot.pedal_pull_m > 0.0010)
        return 1;
    terminal_pause.stop();
    std::printf("[LAB-REPLAY] tick=%lld rpm=%.3f controls=%zu events=%zu\n",
                replay.snapshot.tick, replay.snapshot.rpm,
                replay.history.size(), replay.events.size());
    return 0;
}
