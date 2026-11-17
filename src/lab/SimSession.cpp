#include "lab/SimSession.hpp"

#include "engine/ThrottleAssembly.hpp"
#include "lab/AcousticAdapter.hpp"
#include "ma17/EmulatorLoop.hpp"
#include "ma17/Runner.hpp"

#include <algorithm>
#include <charconv>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace lab {
namespace {

const char *control_name(ControlType type) {
    switch (type) {
    case ControlType::Pedal:
        return "pedal";
    case ControlType::Load:
        return "load";
    case ControlType::VehicleSpeed:
        return "vehicle_speed";
    case ControlType::Starter:
        return "starter";
    case ControlType::Key:
        return "key";
    case ControlType::Pause:
        return "pause";
    case ControlType::Resume:
        return "resume";
    case ControlType::StepTicks:
        return "step_ticks";
    case ControlType::StepIgnition:
        return "step_ignition";
    case ControlType::StepInjector:
        return "step_injector";
    case ControlType::StepSpark:
        return "step_spark";
    case ControlType::StepCombustion:
        return "step_combustion";
    case ControlType::StepMisfire:
        return "step_misfire";
    case ControlType::StepLamp:
        return "step_lamp";
    }
    return nullptr;
}

bool parse_control_name(const std::string &name, ControlType &type) {
    for (ControlType candidate :
         {ControlType::Pedal, ControlType::Load, ControlType::VehicleSpeed,
          ControlType::Starter,
          ControlType::Key, ControlType::Pause, ControlType::Resume,
          ControlType::StepTicks, ControlType::StepIgnition,
          ControlType::StepInjector, ControlType::StepSpark,
          ControlType::StepCombustion, ControlType::StepMisfire,
          ControlType::StepLamp}) {
        if (name == control_name(candidate)) {
            type = candidate;
            return true;
        }
    }
    return false;
}

bool valid_control(const AppliedControl &control) {
    if (control.tick < 0 || !std::isfinite(control.value) ||
        !control_name(control.type))
        return false;
    switch (control.type) {
    case ControlType::Pedal:
        return control.value >= 0.0 && control.value <= 0.025;
    case ControlType::Load:
        return control.value >= 0.0 && control.value <= 60.0;
    case ControlType::VehicleSpeed:
        return control.value >= 0.0 && control.value <= 200.0;
    case ControlType::Starter:
    case ControlType::Key:
        return control.value == 0.0 || control.value == 1.0;
    case ControlType::Pause:
    case ControlType::Resume:
        return control.value == 0.0;
    case ControlType::StepTicks:
    case ControlType::StepIgnition:
    case ControlType::StepInjector:
    case ControlType::StepSpark:
    case ControlType::StepCombustion:
    case ControlType::StepMisfire:
    case ControlType::StepLamp:
        return control.value >= 1.0 && control.value <= 9007199254740991.0 &&
               std::trunc(control.value) == control.value;
    }
    return false;
}

} // namespace

bool save_control_trace(const std::string &path,
                        const std::vector<AppliedControl> &controls,
                        const ControlTraceMetadata *metadata) {
    if (!std::all_of(controls.begin(), controls.end(), valid_control))
        return false;
    if (metadata && metadata->present &&
        (metadata->scenario_args.size() > 128 ||
         std::any_of(metadata->scenario_args.begin(),
                     metadata->scenario_args.end(), [](const auto &arg) {
                         return arg.empty() || arg.size() > 4096 ||
                                arg.find_first_of("\r\n") != std::string::npos;
                     })))
        return false;
    std::ofstream out(path);
    if (!out)
        return false;
    if (metadata && metadata->present) {
        out << "sevel-ma17-controls-v2\nrom " << metadata->rom_size << ' '
            << std::hex << metadata->rom_hash << std::dec << "\nargs "
            << metadata->scenario_args.size() << '\n';
        for (const auto &arg : metadata->scenario_args)
            out << "arg " << std::quoted(arg) << '\n';
        out << "controls\n";
    } else {
        out << "sevel-ma17-controls-v1\n";
    }
    out << std::setprecision(17);
    for (const auto &control : controls) {
        out << control.tick << ' ' << control_name(control.type) << ' '
            << control.value << '\n';
    }
    return static_cast<bool>(out);
}

bool load_control_trace(const std::string &path,
                        std::vector<AppliedControl> &controls,
                        ControlTraceMetadata *metadata) {
    std::ifstream in(path);
    std::string line;
    if (!std::getline(in, line))
        return false;
    ControlTraceMetadata parsed_metadata;
    if (line == "sevel-ma17-controls-v2") {
        parsed_metadata.present = true;
        if (!std::getline(in, line))
            return false;
        std::istringstream rom(line);
        std::string tag;
        if (!(rom >> tag >> parsed_metadata.rom_size) || tag != "rom" ||
            !(rom >> std::hex >> parsed_metadata.rom_hash) ||
            !(rom >> std::ws).eof())
            return false;
        if (!std::getline(in, line))
            return false;
        std::istringstream count_row(line);
        std::size_t count = 0;
        if (!(count_row >> tag >> count) || tag != "args" || count > 128 ||
            !(count_row >> std::ws).eof())
            return false;
        parsed_metadata.scenario_args.reserve(count);
        for (std::size_t index = 0; index < count; ++index) {
            if (!std::getline(in, line))
                return false;
            std::istringstream arg_row(line);
            std::string arg;
            if (!(arg_row >> tag) || tag != "arg" ||
                (arg_row >> std::ws).peek() != '"' ||
                !(arg_row >> std::quoted(arg)) || arg.empty() ||
                arg.size() > 4096 || !(arg_row >> std::ws).eof())
                return false;
            parsed_metadata.scenario_args.push_back(std::move(arg));
        }
        if (!std::getline(in, line) || line != "controls")
            return false;
    } else if (line != "sevel-ma17-controls-v1") {
        return false;
    }
    std::vector<AppliedControl> parsed;
    parsed.reserve(256);
    while (std::getline(in, line)) {
        AppliedControl control;
        std::string type;
        std::istringstream row(line);
        if (!(row >> control.tick >> type >> control.value) ||
            !parse_control_name(type, control.type) || !valid_control(control))
            return false;
        row >> std::ws;
        if (!row.eof())
            return false;
        parsed.push_back(control);
    }
    if (!in.eof())
        return false;
    controls = std::move(parsed);
    if (metadata)
        *metadata = std::move(parsed_metadata);
    return true;
}

SimSession::SimSession(std::vector<std::string> args,
                       std::size_t event_capacity, long long capture_tick)
    : args_(std::move(args)), event_capacity_(event_capacity),
      capture_tick_(capture_tick) {
    if (event_capacity_ == 0)
        throw std::invalid_argument("event capacity must be positive");
    pending_controls_.reserve(128);
    pending_session_actions_.reserve(16);
    control_history_.reserve(4096);
    events_.reserve(event_capacity_);
    for (std::size_t index = 0; index + 1 < args_.size(); ++index) {
        if (args_[index] != "--stop-ticks")
            continue;
        const auto &text = args_[index + 1];
        long long parsed = 0;
        const auto [end, error] =
            std::from_chars(text.data(), text.data() + text.size(), parsed);
        if (error == std::errc{} && end == text.data() + text.size() &&
            parsed > 0)
            stop_tick_ = parsed;
    }
}

SimSession::~SimSession() { stop(); }

void SimSession::start() {
    if (worker_.joinable() || cancel_.load() || finished_.load())
        throw std::logic_error("simulation session already started or stopped");
    worker_ = std::thread(&SimSession::run, this);
}

void SimSession::stop() {
    cancel_.store(true);
    wake_.notify_all();
    if (worker_.joinable())
        worker_.join();
}

void SimSession::set_paused(bool paused) {
    std::lock_guard lock(mutex_);
    if (paused_ != paused) {
        record_session_action(paused ? ControlType::Pause : ControlType::Resume,
                              0.0);
        ++pace_generation_;
        if (!paused) {
            pace_deadline_ = std::chrono::steady_clock::now();
            step_ticks_remaining_ = 0;
            step_event_mode_ = false;
        }
    }
    paused_ = paused;
    wake_.notify_all();
}

bool SimSession::step_ticks(long long ticks) {
    std::lock_guard lock(mutex_);
    if (!paused_ || step_event_mode_ || finished_.load() || cancel_.load() ||
        ticks <= 0 || ticks > 9007199254740991LL ||
        ticks > std::numeric_limits<long long>::max() - step_ticks_remaining_)
        return false;
    record_session_action(ControlType::StepTicks, static_cast<double>(ticks));
    step_ticks_remaining_ += ticks;
    wake_.notify_all();
    return true;
}

bool SimSession::step_time(std::chrono::milliseconds duration) {
    static_assert(emulator_ticks_per_second % 1000 == 0);
    constexpr long long ticks_per_millisecond =
        emulator_ticks_per_second / 1000;
    if (duration.count() <= 0 ||
        duration.count() >
            std::numeric_limits<long long>::max() / ticks_per_millisecond)
        return false;
    return step_ticks(duration.count() * ticks_per_millisecond);
}

bool SimSession::step_until_event(ma17::EmulatorEventType type,
                                  long long max_ticks) {
    std::lock_guard lock(mutex_);
    if (!paused_ || finished_.load() || cancel_.load() || max_ticks <= 0 ||
        max_ticks > 9007199254740991LL || step_ticks_remaining_ != 0 ||
        step_batch_active_)
        return false;
    ControlType control_type;
    switch (type) {
    case ma17::EmulatorEventType::IgnitionPin:
        control_type = ControlType::StepIgnition;
        break;
    case ma17::EmulatorEventType::InjectorPin:
        control_type = ControlType::StepInjector;
        break;
    case ma17::EmulatorEventType::Spark:
        control_type = ControlType::StepSpark;
        break;
    case ma17::EmulatorEventType::Combustion:
        control_type = ControlType::StepCombustion;
        break;
    case ma17::EmulatorEventType::Misfire:
        control_type = ControlType::StepMisfire;
        break;
    case ma17::EmulatorEventType::LampCandidate:
        control_type = ControlType::StepLamp;
        break;
    default:
        return false;
    }
    record_session_action(control_type, static_cast<double>(max_ticks));
    step_ticks_remaining_ = max_ticks;
    step_event_type_ = type;
    step_event_mode_ = true;
    wake_.notify_all();
    return true;
}

void SimSession::set_speed(double speed) {
    std::lock_guard lock(mutex_);
    const double adjusted = std::clamp(speed, 0.1, 16.0);
    if (speed_ != adjusted) {
        speed_ = adjusted;
        pace_deadline_ = std::chrono::steady_clock::now();
        ++pace_generation_;
    }
    wake_.notify_all();
}

void SimSession::set_pedal(double pull_m) {
    schedule_control({0, ControlType::Pedal, std::clamp(pull_m, 0.0, 0.025)});
}

void SimSession::set_load(double torque_nm) {
    schedule_control({0, ControlType::Load, std::clamp(torque_nm, 0.0, 60.0)});
}

void SimSession::set_vehicle_speed(double kmh) {
    schedule_control({0, ControlType::VehicleSpeed,
                      std::clamp(kmh, 0.0, 200.0)});
}

void SimSession::set_starter(bool engaged) {
    schedule_control({0, ControlType::Starter, engaged ? 1.0 : 0.0});
}

void SimSession::set_key(bool on) {
    schedule_control({0, ControlType::Key, on ? 1.0 : 0.0});
}

void SimSession::schedule_control(AppliedControl control) {
    if (!valid_control(control))
        throw std::invalid_argument("invalid scheduled control");
    std::lock_guard lock(mutex_);
    const auto position = std::upper_bound(
        pending_controls_.begin(), pending_controls_.end(), control.tick,
        [](long long tick, const AppliedControl &queued) {
            return tick < queued.tick;
        });
    pending_controls_.insert(position, control);
}

bool SimSession::paused() const {
    std::lock_guard lock(mutex_);
    return paused_;
}

double SimSession::speed() const {
    std::lock_guard lock(mutex_);
    return speed_;
}

bool SimSession::latest(ma17::EmulatorSnapshot &snapshot) const {
    std::lock_guard lock(mutex_);
    if (!has_snapshot_)
        return false;
    snapshot = snapshot_;
    return true;
}

bool SimSession::capture_snapshot(ma17::EmulatorSnapshot &snapshot) const {
    std::lock_guard lock(mutex_);
    if (!has_capture_snapshot_)
        return false;
    snapshot = capture_snapshot_;
    return true;
}

std::vector<ma17::EmulatorEvent> SimSession::events() const {
    return event_window().events;
}

EventWindow SimSession::event_window() const {
    std::lock_guard lock(mutex_);
    EventWindow window;
    window.base_index = event_base_index_;
    window.events.reserve(events_.size());
    const auto head =
        events_.begin() + static_cast<std::ptrdiff_t>(event_head_);
    window.events.insert(window.events.end(), head, events_.end());
    window.events.insert(window.events.end(), events_.begin(), head);
    return window;
}

std::vector<AppliedControl> SimSession::control_history() const {
    std::lock_guard lock(mutex_);
    return control_history_;
}

unsigned long long SimSession::event_overflow() const {
    std::lock_guard lock(mutex_);
    return event_overflow_;
}

int SimSession::batch_steps_to_next_control(long long tick,
                                            int max_steps) const {
    long long steps = max_steps;
    if (!pending_controls_.empty() && pending_controls_.front().tick > tick)
        steps = std::min(steps, pending_controls_.front().tick - tick);
    if (!has_capture_snapshot_ && capture_tick_ > tick)
        steps = std::min(steps, capture_tick_ - tick);
    return static_cast<int>(steps);
}

void SimSession::record_session_action(ControlType type, double value) {
    if (worker_waiting_ && loop_context_)
        control_history_.push_back({loop_context_->ticks, type, value});
    else
        pending_session_actions_.push_back({0, type, value});
}

void SimSession::flush_session_actions(long long tick) {
    for (auto action : pending_session_actions_) {
        action.tick = tick;
        control_history_.push_back(action);
    }
    pending_session_actions_.clear();
}

void SimSession::receive_snapshot(const ma17::EmulatorSnapshot &snapshot,
                                  void *context) {
    auto &self = *static_cast<SimSession *>(context);
    std::unique_lock lock(self.mutex_);
    self.snapshot_ = snapshot;
    self.has_snapshot_ = true;
    if (!self.has_capture_snapshot_ && self.capture_tick_ > 0 &&
        snapshot.tick >= self.capture_tick_) {
        self.capture_snapshot_ = snapshot;
        self.has_capture_snapshot_ = true;
    }
    self.wake_.notify_all();
    const bool first = self.previous_tick_ == 0;
    const long long elapsed = snapshot.tick - self.previous_tick_;
    self.previous_tick_ = snapshot.tick;
    if (self.step_batch_active_) {
        self.step_ticks_remaining_ -=
            std::min(self.step_ticks_remaining_, elapsed);
        self.step_batch_active_ = false;
        if (self.step_ticks_remaining_ == 0)
            self.step_event_mode_ = false;
    }
    const auto next_step = [&self] {
        if (self.step_ticks_remaining_ <= 0)
            return false;
        const int requested = static_cast<int>(
            std::min(self.step_ticks_remaining_,
                     static_cast<long long>(self.normal_batch_steps_)));
        self.loop_context_->steps_per_batch =
            self.batch_steps_to_next_control(self.snapshot_.tick, requested);
        self.step_batch_active_ = true;
        return true;
    };
    self.flush_session_actions(snapshot.tick);
    if (self.stop_tick_ > 0 && snapshot.tick >= self.stop_tick_)
        return;
    while (self.paused_ && !self.cancel_.load()) {
        if (next_step()) {
            self.worker_waiting_ = false;
            return;
        }
        self.worker_waiting_ = true;
        self.wake_.wait(lock);
    }
    self.worker_waiting_ = false;
    if (self.cancel_.load())
        return;
    self.loop_context_->steps_per_batch = self.batch_steps_to_next_control(
        self.snapshot_.tick, self.normal_batch_steps_);
    const auto now = std::chrono::steady_clock::now();
    if (first)
        self.pace_deadline_ = now;
    self.pace_deadline_ +=
        std::chrono::duration_cast<std::chrono::steady_clock::duration>(
            std::chrono::duration<double>(
                static_cast<double>(elapsed) /
                (emulator_ticks_per_second * self.speed_)));
    if (self.pace_deadline_ + std::chrono::milliseconds(100) < now)
        self.pace_deadline_ = now;
    const auto generation = self.pace_generation_;
    if (self.pace_deadline_ > now + std::chrono::milliseconds(2))
        self.wake_.wait_until(lock, self.pace_deadline_, [&self, generation] {
            return self.cancel_.load() || self.paused_ ||
                   self.pace_generation_ != generation;
        });
    self.flush_session_actions(snapshot.tick);
    while (self.paused_ && !self.cancel_.load()) {
        if (next_step()) {
            self.worker_waiting_ = false;
            return;
        }
        self.worker_waiting_ = true;
        self.wake_.wait(lock);
    }
    self.worker_waiting_ = false;
    self.loop_context_->steps_per_batch = self.batch_steps_to_next_control(
        self.snapshot_.tick, self.normal_batch_steps_);
}

void SimSession::receive_event(const ma17::EmulatorEvent &event,
                               void *context) {
    auto &self = *static_cast<SimSession *>(context);
    std::lock_guard lock(self.mutex_);
    if (self.events_.size() == self.event_capacity_) {
        self.events_[self.event_head_] = event;
        self.event_head_ = (self.event_head_ + 1) % self.event_capacity_;
        ++self.event_base_index_;
        ++self.event_overflow_;
    } else {
        self.events_.push_back(event);
    }
    if (self.step_event_mode_ && self.step_batch_active_ &&
        event.type == self.step_event_type_) {
        const long long consumed = event.tick - self.previous_tick_;
        if (consumed > 0 && consumed <= self.loop_context_->steps_per_batch) {
            self.loop_context_->steps_per_batch = static_cast<int>(consumed);
            self.step_ticks_remaining_ =
                std::min(self.step_ticks_remaining_, consumed);
        }
    }
}

void SimSession::apply_controls(ma17::EmulatorLoopContext &context, void *raw) {
    auto &self = *static_cast<SimSession *>(raw);
    std::unique_lock lock(self.mutex_);
    if (!self.loop_context_) {
        self.loop_context_ = &context;
        self.normal_batch_steps_ = context.steps_per_batch;
    }
    const auto ready = std::upper_bound(
        self.pending_controls_.begin(), self.pending_controls_.end(),
        context.ticks, [](long long tick, const AppliedControl &queued) {
            return tick < queued.tick;
        });
    for (auto command = self.pending_controls_.begin(); command != ready;
         ++command) {
        self.control_history_.push_back(
            {context.ticks, command->type, command->value});
        switch (command->type) {
        case ControlType::Pedal:
            self.pedal_pull_m_ = command->value;
            self.pedal_override_ = true;
            break;
        case ControlType::Load:
            self.load_torque_nm_ = command->value;
            self.load_override_ = true;
            break;
        case ControlType::VehicleSpeed:
            context.vehicle_speed_target_kmh = command->value;
            break;
        case ControlType::Starter:
            self.starter_engaged_ = command->value != 0.0;
            self.starter_override_ = true;
            break;
        case ControlType::Key:
            context.key_on = command->value != 0.0;
            if (!context.key_on) {
                self.starter_engaged_ = false;
                self.starter_override_ = true;
            }
            break;
        case ControlType::Pause:
            self.paused_ = true;
            ++self.pace_generation_;
            break;
        case ControlType::Resume:
            self.paused_ = false;
            self.step_ticks_remaining_ = 0;
            self.step_event_mode_ = false;
            self.pace_deadline_ = std::chrono::steady_clock::now();
            ++self.pace_generation_;
            break;
        case ControlType::StepTicks:
        case ControlType::StepIgnition:
        case ControlType::StepInjector:
        case ControlType::StepSpark:
        case ControlType::StepCombustion:
        case ControlType::StepMisfire:
        case ControlType::StepLamp: {
            const auto amount = static_cast<long long>(command->value);
            if (amount > std::numeric_limits<long long>::max() -
                             self.step_ticks_remaining_) {
                context.running.store(false);
                break;
            }
            self.step_ticks_remaining_ += amount;
            if (command->type == ControlType::StepTicks) {
                self.step_event_mode_ = false;
            } else {
                self.step_event_mode_ = true;
                switch (command->type) {
                case ControlType::StepIgnition:
                    self.step_event_type_ =
                        ma17::EmulatorEventType::IgnitionPin;
                    break;
                case ControlType::StepInjector:
                    self.step_event_type_ =
                        ma17::EmulatorEventType::InjectorPin;
                    break;
                case ControlType::StepSpark:
                    self.step_event_type_ = ma17::EmulatorEventType::Spark;
                    break;
                case ControlType::StepCombustion:
                    self.step_event_type_ = ma17::EmulatorEventType::Combustion;
                    break;
                case ControlType::StepMisfire:
                    self.step_event_type_ = ma17::EmulatorEventType::Misfire;
                    break;
                case ControlType::StepLamp:
                    self.step_event_type_ =
                        ma17::EmulatorEventType::LampCandidate;
                    break;
                case ControlType::Pedal:
                case ControlType::Load:
                case ControlType::VehicleSpeed:
                case ControlType::Starter:
                case ControlType::Key:
                case ControlType::Pause:
                case ControlType::Resume:
                case ControlType::StepTicks:
                    break;
                }
            }
            break;
        }
        }
    }
    self.pending_controls_.erase(self.pending_controls_.begin(), ready);
    self.flush_session_actions(context.ticks);
    if (self.pedal_override_ && context.throttle)
        context.throttle->set_cable_pull_m(self.pedal_pull_m_);
    if (self.load_override_) {
        context.load_step_tick = 1;
        context.load_torque_nm = self.load_torque_nm_;
    }
    if (self.starter_override_)
        context.starter_stop_tick =
            self.starter_engaged_ && context.key_on
                ? context.ticks + 2 * self.normal_batch_steps_
                : 0;
    if (context.ticks == 0) {
        while (self.paused_ && !self.cancel_.load()) {
            if (self.step_ticks_remaining_ > 0) {
                const int requested = static_cast<int>(
                    std::min(self.step_ticks_remaining_,
                             static_cast<long long>(self.normal_batch_steps_)));
                context.steps_per_batch =
                    self.batch_steps_to_next_control(context.ticks, requested);
                self.step_batch_active_ = true;
                self.worker_waiting_ = false;
                break;
            }
            self.worker_waiting_ = true;
            self.wake_.wait(lock);
        }
        self.worker_waiting_ = false;
        if (self.cancel_.load())
            context.running.store(false);
    }
    if (!self.paused_)
        context.steps_per_batch = self.batch_steps_to_next_control(
            context.ticks, self.normal_batch_steps_);
}

void SimSession::run() {
    std::vector<char *> argv;
    argv.reserve(args_.size());
    for (auto &arg : args_)
        argv.push_back(arg.data());
    result_.store(ma17::run_cli(
        static_cast<int>(argv.size()), argv.data(),
        {receive_snapshot, receive_event, this, &cancel_, apply_controls}));
    finished_.store(true);
    wake_.notify_all();
}

} // namespace lab
