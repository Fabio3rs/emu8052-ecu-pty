#pragma once

#include "ma17/EmulatorEvent.hpp"
#include "ma17/EmulatorSnapshot.hpp"

#include <atomic>

namespace ma17 {

struct EmulatorLoopContext;
using ControlCallback = void (*)(EmulatorLoopContext &, void *);

struct RunObserver {
    SnapshotCallback on_snapshot = nullptr;
    EventCallback on_event = nullptr;
    void *context = nullptr;
    std::atomic<bool> *cancel = nullptr;
    ControlCallback on_control = nullptr;
};

// Runs the existing Fiat MA1.7 harness in the calling thread.
int run_cli(int argc, char **argv, RunObserver observer = {});

} // namespace ma17
