#include "ma17/Runner.hpp"

#include <array>
#include <cstdio>
#include <string>
#include <vector>

namespace {

struct Observation {
    ma17::EmulatorSnapshot latest;
    long long previous_tick = 0;
    int count = 0;
    bool ordered = true;
    long long previous_event_tick = 0;
    int ignition_edges = 0;
    bool events_ordered = true;
    bool saw_tps1_adc_fault = false;
    bool saw_tps1_adc_restore = false;
};

void receive_snapshot(const ma17::EmulatorSnapshot &snapshot, void *raw) {
    auto &observation = *static_cast<Observation *>(raw);
    observation.ordered &= snapshot.tick > observation.previous_tick;
    observation.previous_tick = snapshot.tick;
    observation.latest = snapshot;
    const auto &adc6 = snapshot.adc_last_conversion[6];
    if (adc6.sampled && adc6.voltage_available &&
        snapshot.tick >= 550000 && snapshot.tick < 700000 &&
        adc6.tick >= 500000 &&
        adc6.tick <= static_cast<uint64_t>(snapshot.tick))
        observation.saw_tps1_adc_fault |=
            adc6.pin_voltage_v == 5.0 && snapshot.tps_track1_v < 5.0;
    if (adc6.sampled && adc6.voltage_available &&
        snapshot.tick >= 800000 && adc6.tick >= 700000)
        observation.saw_tps1_adc_restore |= adc6.pin_voltage_v < 5.0;
    ++observation.count;
}

void receive_event(const ma17::EmulatorEvent &event, void *raw) {
    auto &observation = *static_cast<Observation *>(raw);
    observation.events_ordered &= event.tick >= observation.previous_event_tick;
    observation.previous_event_tick = event.tick;
    if (event.type == ma17::EmulatorEventType::IgnitionPin)
        ++observation.ignition_edges;
}

} // namespace

int main(int argc, char **argv) {
    if (argc != 2 && argc != 3)
        return 2;
    const bool adc_fault = argc == 3 && std::string{argv[2]} == "adc_fault";
    if (argc == 3 && !adc_fault)
        return 2;
    std::vector<std::string> words{
        argv[0],  argv[1],        "--physical-crank", "--starter-ticks",
        "495000", "--stop-ticks", "1485000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5"};
    if (adc_fault)
        words.insert(words.end(), {"--tps1-high-tick", "500000",
                                   "--tps1-restore-tick", "700000"});
    std::vector<char *> harness_argv(words.size());
    for (std::size_t index = 0; index < words.size(); ++index)
        harness_argv[index] = words[index].data();

    Observation observation;
    const int result = ma17::run_cli(
        static_cast<int>(harness_argv.size()), harness_argv.data(),
        {receive_snapshot, receive_event, &observation});
    if (result != 0 || !observation.ordered || !observation.events_ordered ||
        observation.ignition_edges < 2 || observation.count < 100 ||
        observation.latest.tick != 1485000 ||
        (!adc_fault && (observation.latest.rpm < 300.0 ||
                        observation.latest.crank_angle_rad < 6.28 ||
                        observation.latest.ram47 == 0)) ||
        (adc_fault && (!observation.saw_tps1_adc_fault ||
                       !observation.saw_tps1_adc_restore))) {
        std::fprintf(stderr,
                     "snapshot failed: result=%d count=%d tick=%lld "
                     "rpm=%.3f angle=%.3f ram47=%u ordered=%d fault=%d restore=%d\n",
                     result, observation.count, observation.latest.tick,
                     observation.latest.rpm, observation.latest.crank_angle_rad,
                     static_cast<unsigned>(observation.latest.ram47),
                     observation.ordered, observation.saw_tps1_adc_fault,
                     observation.saw_tps1_adc_restore);
        return 1;
    }
    return 0;
}
