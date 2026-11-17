#pragma once

#include "ma17/EmulatorEvent.hpp"
#include "ma17/EmulatorSnapshot.hpp"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace ma17 {
struct EmulatorLoopContext;
}

namespace lab {

enum class ControlType { Pedal, Load, Starter, Key };

struct AppliedControl {
    long long tick = 0;
    ControlType type = ControlType::Pedal;
    double value = 0.0;
};

struct ControlTraceMetadata {
    bool present = false;
    std::uint64_t rom_size = 0;
    std::uint64_t rom_hash = 0;
    std::vector<std::string> scenario_args;
};

bool save_control_trace(const std::string &path,
                        const std::vector<AppliedControl> &controls,
                        const ControlTraceMetadata *metadata = nullptr);
bool load_control_trace(const std::string &path,
                        std::vector<AppliedControl> &controls,
                        ControlTraceMetadata *metadata = nullptr);

struct EventWindow {
    std::size_t base_index = 0;
    std::vector<ma17::EmulatorEvent> events;
};

class SimSession {
  public:
    explicit SimSession(std::vector<std::string> args,
                        std::size_t event_capacity = 65536);
    ~SimSession();
    SimSession(const SimSession &) = delete;
    SimSession &operator=(const SimSession &) = delete;

    void start();
    void stop();
    void set_paused(bool paused);
    void set_speed(double speed);
    void set_pedal(double pull_m);
    void set_load(double torque_nm);
    void set_starter(bool engaged);
    void set_key(bool on);
    void schedule_control(AppliedControl control);
    bool paused() const;
    double speed() const;
    bool latest(ma17::EmulatorSnapshot &snapshot) const;
    bool finished() const { return finished_.load(); }
    int result() const { return result_.load(); }
    std::vector<ma17::EmulatorEvent> events() const;
    EventWindow event_window() const;
    std::vector<AppliedControl> control_history() const;
    unsigned long long event_overflow() const;

  private:
    static void receive_snapshot(const ma17::EmulatorSnapshot &snapshot,
                                 void *context);
    static void receive_event(const ma17::EmulatorEvent &event, void *context);
    static void apply_controls(ma17::EmulatorLoopContext &context, void *raw);
    void run();

    std::vector<std::string> args_;
    std::thread worker_;
    mutable std::mutex mutex_;
    std::condition_variable wake_;
    ma17::EmulatorSnapshot snapshot_{};
    bool has_snapshot_ = false;
    bool paused_ = false;
    double speed_ = 1.0;
    double pedal_pull_m_ = 0.0;
    double load_torque_nm_ = 0.0;
    bool pedal_override_ = false;
    bool load_override_ = false;
    bool starter_override_ = false;
    bool starter_engaged_ = false;
    long long previous_tick_ = 0;
    std::chrono::steady_clock::time_point pace_deadline_{};
    unsigned long long pace_generation_ = 0;
    std::vector<AppliedControl> pending_controls_;
    std::vector<AppliedControl> control_history_;
    const std::size_t event_capacity_;
    std::vector<ma17::EmulatorEvent> events_;
    std::size_t event_head_ = 0;
    std::size_t event_base_index_ = 0;
    unsigned long long event_overflow_ = 0;
    std::atomic<bool> cancel_{false};
    std::atomic<bool> finished_{false};
    std::atomic<int> result_{0};
};

} // namespace lab
