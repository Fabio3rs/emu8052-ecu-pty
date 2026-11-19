#pragma once

#include <atomic>
#include <chrono>
#include "engine/Combustion.hpp"
#include "engine/PlantTelemetry.hpp"
#include "engine/ExhaustLambda.hpp"
#include "engine/IdleActuator.hpp"
#include "ecu_hw/Ma17IgnitionStage.hpp"
#include "ecu_hw/Ma17DiagnosticLamp.hpp"
#include "ecu_hw/Ma17Tachometer.hpp"
#include "ecu_hw/Ma17IdleBridge.hpp"
#include "ecu_hw/Ma17LambdaHeater.hpp"
#include "ma17/DynoBench.hpp"
#include "ma17/EmulatorSnapshot.hpp"
#include "ma17/EmulatorEvent.hpp"

struct em8051;
struct CrankshaftSimulator;
namespace engine { class CrankDynamics; }
namespace engine { class Drivetrain; }
namespace engine { class ThrottleAssembly; }
namespace engine { class ThermalState; }
namespace engine { class IntakeFuel; }
namespace ecu_hw { class Ma17TpsCircuit; }
namespace ecu_hw { class Ma17SensorCircuit; }
namespace ecu_hw { class Ma17InjectorStage; }

namespace ma17 {

struct EmulatorLoopContext;
using ControlCallback = void (*)(EmulatorLoopContext &, void *);

struct FiveBaudInjector;
struct PtyBridge;
struct PhysicalCrankInput;
class UartScheduler;

struct EmulatorLoopContext {
    em8051 &cpu;
    CrankshaftSimulator &crank;
    PtyBridge &bridge;
    UartScheduler &uart;
    FiveBaudInjector &slow_init;
    std::atomic<bool> &running;
    std::atomic<bool> &inject_5baud;
    long long &ticks;
    std::chrono::steady_clock::time_point startup_time;
    std::chrono::nanoseconds batch_duration;
    int steps_per_batch;
    bool trace_pc;
    SnapshotCallback on_snapshot = nullptr;
    void *snapshot_context = nullptr;
    EventCallback on_event = nullptr;
    void *event_context = nullptr;
    std::atomic<bool> *cancel = nullptr;
    ControlCallback on_control = nullptr;
    void *control_context = nullptr;
    engine::CrankDynamics *physical_crank = nullptr;
    engine::Drivetrain *drivetrain = nullptr; // Owned by the runner/controller.
    bool physical_pty_realtime = false;
    PhysicalCrankInput *physical_input = nullptr;
    long long starter_stop_tick = 0;
    bool key_on = true;
    long long physical_stop_tick = 0;
    long long crank_sensor_open_tick = 0;
    long long crank_sensor_restore_tick = 0;
    engine::ThrottleAssembly *throttle = nullptr;
    bool idle_bridge_candidate = false;
    long long idle_motor_disconnect_tick = 0;
    long long idle_motor_reconnect_tick = 0;
    bool idle_motor_connected = true;
    engine::IdleActuator idle_actuator{};
    ecu_hw::Ma17IdleBridge idle_bridge{};
    ecu_hw::Ma17TpsCircuit *tps_circuit = nullptr;
    long long pedal_step_tick = 0;
    long long pedal_release_tick = 0;
    long long pedal_rise_ticks = 0;
    double pedal_pull_m = 0.0;
    long long load_step_tick = 0;
    double load_torque_nm = 0.0;
    long long tps1_high_tick = 0;
    long long tps1_restore_tick = 0;
    long long tps2_high_tick = 0;
    long long tps2_restore_tick = 0;
    engine::ThermalState *thermal = nullptr;
    // Scenario speed when drivetrain is null; physical speed otherwise.
    double vehicle_speed_kmh = 0.0;
    double vehicle_speed_target_kmh = 0.0;
    ecu_hw::Ma17SensorCircuit *sensor_circuit = nullptr;
    engine::IntakeFuel *intake = nullptr;
    engine::Combustion combustion{};
    engine::PlantWindow plant_window{};
    DynoBench *bench = nullptr; // --dyno-point: brake + ROM bench state machine
    double combustion_integrated_j = 0.0; // per-tick integral of the pulse torque (energy check)
    // Oil-temperature friction (F-43) follows the coolant temperature when true.
    bool physical_plant_friction_temp = false;
    bool physical_plant_accessories = false; // F-45, --accessory-load
    double coolant_heat_pending_j = 0.0;
    engine::ExhaustLambda exhaust{};
    bool pump_relay_p34_candidate = false;
    ecu_hw::Ma17PumpRelay pump_relay{};
    ecu_hw::Ma17LambdaHeater lambda_heater{};
    double lambda_adc_pin_override_v = -1.0;
    long long lambda_stuck_tick = 0;
    long long lambda_restore_tick = 0;
    double exhaust_flow_kg_s = 0.0;
    ecu_hw::Ma17IgnitionStage ignition_stage{};
    ecu_hw::Ma17DiagnosticLamp diagnostic_lamp{};
    ecu_hw::Ma17Tachometer tachometer{};
    ecu_hw::Ma17InjectorStage *injector_stage = nullptr;
    double injected_mass_pending_kg = 0.0;
    long long injector_disconnect_tick = 0;
    long long injector_reconnect_tick = 0;
    long long coil_disconnect_tick = 0;
    long long coil_reconnect_tick = 0;
    unsigned coil_channel = 0;
    int fluid_step_ticks = 990;
    long long ect_open_tick = 0;
    long long ect_restore_tick = 0;
};

void run_emulator_loop(EmulatorLoopContext &context);

} // namespace ma17
