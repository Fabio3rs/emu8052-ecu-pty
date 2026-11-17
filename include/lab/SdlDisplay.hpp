#pragma once

#include "ma17/EmulatorEvent.hpp"
#include "ma17/EmulatorSnapshot.hpp"

#include <string>
#include <vector>

namespace lab {

class SimSession;

bool show_sdl_display(
    const ma17::EmulatorSnapshot &snapshot, int frame_limit,
    const std::string &screenshot_path, SimSession *session = nullptr,
    long long capture_after_tick = 0,
    const std::vector<ma17::EmulatorEvent> *captured_events = nullptr,
    bool replay_controls = false, bool gpu_preview = false,
    bool enable_audio = true, int frame_delay_ms = 16,
    bool bench_preset = false);

} // namespace lab
