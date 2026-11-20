#pragma once

#include "ma17/EmulatorSnapshot.hpp"

#include <bit>
#include <string>
#include <vector>

namespace lab {

// D4: ECU state badges, only for what the snapshot actually carries. Confirmed
// states are solid; a state that is only a candidate is dashed and says
// "cand.". Closed loop, DFCO and WOT enrichment are not in the snapshot, so
// there is no badge for them (an invented state would be worse than none).
struct EcuBadge {
    std::string text;
    bool active = false;
    bool candidate = false;
};

inline std::vector<EcuBadge> ecu_badges(const ma17::EmulatorSnapshot &snapshot) {
    const int fault_bits = std::popcount(snapshot.ram27_faults) +
                           std::popcount(snapshot.ram28_faults);
    return {
        {"IDLE SW", snapshot.throttle_available && snapshot.idle_contact_closed,
         false},
        {"LAMP cand.", snapshot.lamp_on_candidate, true},
        {fault_bits > 0 ? "DTC " + std::to_string(fault_bits) : "DTC 0",
         fault_bits > 0, false},
    };
}

} // namespace lab
