#pragma once
// Explicit crank-dyno scenario (GOAL_DYNO_ROM phase 4). LLM-written (Claude).
// Nothing here is implied by --load-nm or any other option: the scenario is applied only by
// --dyno-scenario, and every field is then visible in the run manifest.
#include "ma17/EmulatorConfig.hpp"

namespace ma17 {

struct DynoScenario {
    int ethanol_percent = 22;       // fuel E22 (Brazilian pump gasoline)
    int throttle_leak_mm2 = 9;      // closed-throttle leak of the dyno runs
    bool accessories = true;        // alternator + water pump on the crank
    double coolant_c = 90.0;        // warm engine
    double ambient_c = 20.0;        // recorded, plant default
    int tdc_reference_deg = 120;    // PMS hypothesis (manual B.500.837)

    void apply(EmulatorConfig &c) const {
        c.ethanol_percent = ethanol_percent;
        c.throttle_leak_mm2 = throttle_leak_mm2;
        c.accessory_load = accessories;
        c.initial_coolant_c = coolant_c;
        c.tdc_reference_deg = tdc_reference_deg;
    }
};

} // namespace ma17
