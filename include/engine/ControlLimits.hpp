#pragma once
// Single source of the operator-control limits (GOAL_DYNO_ROM phase 4). LLM-written (Claude).
// Pedal travel follows the throttle geometry and the brake limit follows the dyno controller,
// so the Lab, scheduled controls, replay and the CLI cannot disagree about what is reachable.
#include "engine/ThrottleAssembly.hpp"
#include "engine/physics/Dynamics.hpp"

namespace engine {

// Cable pull that opens the throttle to its maximum angle: free play + r * theta_max (~40.27 mm).
constexpr double max_pedal_pull_m(const ThrottleParameters &p = {}) {
    return p.cable_free_play_m + p.cable_radius_m * p.maximum_angle_rad;
}
// Largest torque the dyno brake / scenario load can apply (DynoPi::t_max, 400 N.m).
constexpr double max_brake_nm(const physics::DynoPi &c = {}) { return c.t_max; }
// Lab slider resolution only; never a validation limit.
constexpr double lab_load_slider_span_nm = 60.0;

} // namespace engine
