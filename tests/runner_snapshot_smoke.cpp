#include "ma17/Runner.hpp"

#include <array>
#include <cstdio>
#include <string>

namespace {

struct Observation {
    ma17::EmulatorSnapshot latest;
    long long previous_tick = 0;
    int count = 0;
    bool ordered = true;
    long long previous_event_tick = 0;
    int ignition_edges = 0;
    bool events_ordered = true;
};

void receive_snapshot(const ma17::EmulatorSnapshot &snapshot, void *raw) {
    auto &observation = *static_cast<Observation *>(raw);
    observation.ordered &= snapshot.tick > observation.previous_tick;
    observation.previous_tick = snapshot.tick;
    observation.latest = snapshot;
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
    if (argc != 2)
        return 2;
    std::array<std::string, 7> words{
        argv[0],  argv[1],        "--physical-crank", "--starter-ticks",
        "495000", "--stop-ticks", "1485000"};
    std::array<char *, 7> harness_argv{};
    for (std::size_t index = 0; index < words.size(); ++index)
        harness_argv[index] = words[index].data();

    Observation observation;
    const int result = ma17::run_cli(
        static_cast<int>(harness_argv.size()), harness_argv.data(),
        {receive_snapshot, receive_event, &observation});
    if (result != 0 || !observation.ordered || !observation.events_ordered ||
        observation.ignition_edges < 2 || observation.count < 100 ||
        observation.latest.tick != 1485000 || observation.latest.rpm < 300.0 ||
        observation.latest.crank_angle_rad < 6.28 ||
        observation.latest.ram47 == 0) {
        std::fprintf(stderr,
                     "snapshot failed: result=%d count=%d tick=%lld "
                     "rpm=%.3f angle=%.3f ram47=%u ordered=%d\n",
                     result, observation.count, observation.latest.tick,
                     observation.latest.rpm, observation.latest.crank_angle_rad,
                     static_cast<unsigned>(observation.latest.ram47),
                     observation.ordered);
        return 1;
    }
    return 0;
}
