#pragma once

namespace ma17 {

enum class EmulatorEventType {
    IgnitionPin,
    InjectorPin,
    Combustion,
    Misfire,
    LampCandidate,
};

struct EmulatorEvent {
    long long tick = 0;
    EmulatorEventType type = EmulatorEventType::IgnitionPin;
    unsigned channel = 0;
    bool high = false;
    double crank_angle_rad = 0.0;
    double rpm = 0.0;
    double burned_fuel_kg = 0.0;
    unsigned cylinder_index = 0;
};

using EventCallback = void (*)(const EmulatorEvent &, void *);

} // namespace ma17
