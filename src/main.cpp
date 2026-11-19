// Fiat Tipo Bosch Monomotronic MA1.7, 27C256, SAB80C517A harness.
// Renault MA1.7 uses a different clock and port wiring; no Renault runtime
// profile is configured here.

#include "engine/ControlLimits.hpp"
#include <atomic>
#include <array>
#include <cerrno>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <numbers>
#include <string>

extern "C" {
#include <signal.h>
#include <unistd.h>
}

#include "CrankshaftSimulator.hpp"
#include "engine/CrankDynamics.hpp"
#include "engine/Drivetrain.hpp"
#include <optional>
#include "engine/IdleActuator.hpp"
#include "engine/ThrottleAssembly.hpp"
#include "engine/ThermalState.hpp"
#include "engine/IntakeFuel.hpp"
#include "ecu_hw/Ma17TpsCircuit.hpp"
#include "ecu_hw/Ma17SensorCircuit.hpp"
#include "ecu_hw/Ma17InjectorStage.hpp"
#include "ma17/AdcSimulator.hpp"
#include "ma17/CrankInput.hpp"
#include "ma17/CpuContext.hpp"
#include "ma17/CpuHooks.hpp"
#include "ma17/EmulatorConfig.hpp"
#include "ma17/EmulatorLoop.hpp"
#include "ma17/FirmwareLoader.hpp"
#include "ma17/FiveBaudInjector.hpp"
#include "ma17/PortController.hpp"
#include "ma17/PtyBridge.hpp"
#include "ma17/Runner.hpp"
#include "ma17/UartScheduler.hpp"

static constexpr int SFR_SCON = 0x98; // SM0..RI
static constexpr int SFR_SBUF = 0x99; // buffer
struct TpsSources {
    engine::ThrottleAssembly &throttle;
    ecu_hw::Ma17TpsCircuit &circuit;
    engine::ThermalState &thermal;
    ecu_hw::Ma17SensorCircuit &sensors;
    engine::ExhaustLambda *exhaust;
    long long &ticks;
    long long high_tick;
    long long restore_tick;
    long long tps2_high_tick;
    long long tps2_restore_tick;
    long long tps_open_tick;
    long long tps_restore_tick;
    double tps_open_v;
    long long ect_open_tick;
    long long ect_restore_tick;
    double adc4_voltage_v;
    double adc7_boundary_v;
    double adc7_step_v;
    long long adc7_step_tick;
    double lambda_stuck_v;
    long long lambda_stuck_tick;
    long long lambda_restore_tick;
};

static bool read_tps_voltage(uint8_t channel, void *context,
                             double &voltage) {
    auto &sources = *static_cast<TpsSources *>(context);
    if ((channel == 0 || channel == 6) && sources.tps_open_tick &&
        sources.ticks >= sources.tps_open_tick &&
        (!sources.tps_restore_tick ||
         sources.ticks < sources.tps_restore_tick)) {
        voltage = sources.tps_open_v;
        return true;
    }
    if (channel == 0)
        voltage = sources.tps2_high_tick &&
                          sources.ticks >= sources.tps2_high_tick &&
                          (!sources.tps2_restore_tick ||
                           sources.ticks < sources.tps2_restore_tick)
                      ? sources.circuit.reference_voltage()
                      : sources.circuit.track2_voltage(
                            sources.throttle.angle_rad());
    else if (channel == 1)
        voltage = sources.sensors.battery_voltage();
    else if (channel == 2)
        voltage = sources.sensors.air_voltage(sources.thermal.air_sensor_c());
    else if (channel == 3)
        voltage = sources.ect_open_tick &&
                          sources.ticks >= sources.ect_open_tick &&
                          (!sources.ect_restore_tick ||
                           sources.ticks < sources.ect_restore_tick)
                      ? 5.0
                      : sources.sensors.coolant_voltage(
                            sources.thermal.coolant_sensor_c());
    else if (channel == 4)
        voltage = sources.adc4_voltage_v;
    else if (channel == 5)
        // Electrical fault stimulus; exhaust composition still evolves.
        voltage = sources.lambda_stuck_v >= 0.0 &&
                          sources.ticks >= sources.lambda_stuck_tick &&
                          (!sources.lambda_restore_tick ||
                           sources.ticks < sources.lambda_restore_tick)
                      ? sources.lambda_stuck_v
                      : sources.sensors.lambda_adc_voltage(
                            sources.exhaust->voltage_v());
    else if (channel == 6)
        voltage = sources.high_tick && sources.ticks >= sources.high_tick &&
                          (!sources.restore_tick ||
                           sources.ticks < sources.restore_tick)
                      ? sources.circuit.reference_voltage()
                      : sources.circuit.track1_voltage(sources.throttle.angle_rad());
    else if (channel == 7 && sources.adc7_boundary_v >= 0.0)
        voltage = sources.adc7_step_tick &&
                          sources.ticks >= sources.adc7_step_tick
                      ? sources.adc7_step_v
                      : sources.adc7_boundary_v;
    else
        return false;
    return true;
}

static bool read_idle_contact(void *context) {
    return static_cast<engine::ThrottleAssembly *>(context)->contact_closed();
}

// The PTY transport calls this C callback, which forwards to UartScheduler.
static void uart_on_scanner_byte(uint8_t b);

using UartBridge = ma17::PtyBridge;

static UartBridge g_uart{uart_on_scanner_byte};
static std::atomic<bool> g_running{true};
static std::atomic<bool> g_inject_5baud{
    false}; // Trigger 5-baud init via SIGUSR1

// Historical name: counts tick() calls, including extra machine cycles of
// multi-cycle instructions. Timing and trace offsets use emulated ticks.
static long long g_instr_counter = 0;
static ma17::UartScheduler g_uart_scheduler{g_uart, g_instr_counter};
static std::chrono::steady_clock::time_point start;
static long long p46_low_start_tick() {
    const char *raw = std::getenv("MA17_P4_6_LOW_FROM_TICK");
    if (!raw)
        return -1;
    errno = 0;
    char *end = nullptr;
    const long long value = std::strtoll(raw, &end, 10);
    if (errno || end == raw || *end != '\0' || value < 0) {
        std::fprintf(stderr, "Invalid MA17_P4_6_LOW_FROM_TICK: %s\n", raw);
        std::exit(2);
    }
    return value;
}
// SAB80C517 Port 4 GPIO input: experimental low pin stimuli, not a claim
// about the Fiat board wiring. The P4 output latch remains untouched.
static ma17::PortController g_ports{
    g_uart, g_instr_counter, start,
    std::getenv("MA17_P4_6_FORCE_LOW") != nullptr,
    std::getenv("MA17_P4_7_FORCE_LOW") != nullptr,
    p46_low_start_tick(),
    std::getenv("MA17_P4_3_FORCE_LOW") != nullptr};

static void uart_on_scanner_byte(uint8_t byte) {
    g_uart_scheduler.on_scanner_byte(byte);
}

static ma17::FiveBaudInjector g_5baud_injector{g_uart};

static void sigint_handler(int) { g_running = false; }

static void sigusr1_handler(int) {
    g_inject_5baud = true;
    // Note: Don't start injector here - signal handlers should be minimal
    // Will be started in main loop when g_inject_5baud is detected
}

// P4 port handling for K-line RX bit sampling
static constexpr int SFR_P4 = 0xE8;
static constexpr std::array<char, 8> xram_state_magic{
    'M', 'A', '1', '7', 'X', 'R', 'M', '1'};
static constexpr std::streamsize retained_xram_size = 0x400;

static bool load_xram_state(em8051 &cpu, const char *path, bool &loaded) {
    loaded = false;
    if (!path) return true;
    if (!*path) return false;
    std::error_code error;
    if (!std::filesystem::exists(path, error)) {
        if (error) return false;
        fprintf(stderr, "[XRAM-STATE] fresh file: %s\n", path);
        return true;
    }
    if (std::filesystem::file_size(path, error) !=
            static_cast<std::uintmax_t>(xram_state_magic.size() +
                                        retained_xram_size) || error)
        return false;
    std::ifstream input(path, std::ios::binary);
    std::array<char, 8> magic{};
    input.read(magic.data(), static_cast<std::streamsize>(magic.size()));
    if (magic != xram_state_magic) return false;
    input.read(reinterpret_cast<char *>(cpu.mExtData + 0xF800),
               retained_xram_size);
    if (!input) return false;
    loaded = true;
    fprintf(stderr, "[XRAM-STATE] loaded: %s\n", path);
    return true;
}

static bool save_xram_state(const em8051 &cpu, const char *path) {
    if (!path) return true;
    const std::string temporary =
        std::string(path) + ".tmp." + std::to_string(getpid());
    std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
    if (!output) return false;
    output.write(xram_state_magic.data(),
                 static_cast<std::streamsize>(xram_state_magic.size()));
    output.write(reinterpret_cast<const char *>(cpu.mExtData + 0xF800),
                 retained_xram_size);
    output.close();
    if (!output) return false;
    std::error_code error;
    std::filesystem::rename(temporary, path, error);
    if (error) return false;
    fprintf(stderr, "[XRAM-STATE] saved: %s\n", path);
    return true;
}

int ma17::run_cli(int argc, char **argv, RunObserver observer) {
    g_running.store(true);
    g_inject_5baud.store(false);
    g_instr_counter = 0;
    g_uart_scheduler.reset_for_run();
    g_ports.set_idle_contact_provider(nullptr, nullptr);
    g_5baud_injector.active = false;
    g_5baud_injector.current_bit = 0;
    g_5baud_injector.bit_end_instruction = 0;
    const auto config = ma17::parse_emulator_config(argc, argv);
    if (!config)
        return 2;
    const char *rompath = config->rom_path;
    start = std::chrono::steady_clock::now();
    CrankshaftSimulator sim;
    engine::CrankDynamics physical_crank;
    std::optional<engine::Drivetrain> drivetrain;
    std::optional<ma17::DynoBench> dyno_bench;
    if (config->drivetrain) {
        drivetrain.emplace(config->vehicle_mass_kg,
            engine::transmission::reference_tire_radius_m, config->clutch_max_nm,
            config->vehicle_speed_kmh / 3.6);
        drivetrain->set_gear(config->transmission_gear);
        drivetrain->set_clutch_pressure(config->clutch_percent / 100.0);
        // Provisional road-load estimates, separate from donor calibration.
        drivetrain->set_road_resistance(100.0, 1.184, 0.32, 2.0);
        fprintf(stderr, "Drivetrain estimates: mass=%d kg radius=0.29 m "
                        "clutch=%d Nm rolling=100 N rho=1.184 Cd=0.32 A=2 m2\n",
                config->vehicle_mass_kg, config->clutch_max_nm);
    }
    ma17::PhysicalCrankInput physical_input;
    engine::ThrottleAssembly throttle;
    if (config->idle_contact_p43 || config->idle_contact_p46 ||
        config->idle_contact_p46_high_closed)
        g_ports.set_idle_contact_provider(
            read_idle_contact, &throttle,
            config->idle_contact_p46_high_closed,
            config->idle_contact_p43 ? 0x08u : 0x40u);
    g_ports.set_idle_contact_open_fault(config->idle_contact_open_tick,
                                        config->idle_contact_restore_tick);
    g_ports.set_idle_contact_closed_fault(config->idle_contact_closed_tick);
    ecu_hw::Ma17TpsCircuit tps_circuit{
        config->tps_bench_profile
            ? ecu_hw::TpsCircuitParameters::bench_typical()
            : ecu_hw::TpsCircuitParameters{}};
    engine::ThermalState thermal{20.0, config->initial_coolant_c};
    engine::IntakeFuelParameters intake_parameters;
    if (config->throttle_leak_mm2 >= 0)
        intake_parameters.throttle_leak_area_m2 =
            static_cast<double>(config->throttle_leak_mm2) * 1e-6;
    intake_parameters.ve_map = config->physical_plant;
    intake_parameters.compressible_throttle =
        config->physical_plant && !config->legacy_throttle;
    if (config->physical_plant)
        intake_parameters.exhaust_back_pressure_k = 3.78e6; // calibrado: 15 kPa a 63 g/s (F-41)
    engine::IntakeFuel intake{intake_parameters};
    ecu_hw::SensorCircuitParameters sensor_parameters;
    sensor_parameters.battery_v = config->battery_v;
    sensor_parameters.lambda_adc_gain = config->lambda_adc_gain;
    ecu_hw::Ma17SensorCircuit sensor_circuit{sensor_parameters};
    // Fuel composition is a scenario input; the ROM's intended blend is unknown.
    const auto fuel = engine::FuelBlend::from_ethanol_percent(
        config->ethanol_percent);
    ecu_hw::InjectorStageParameters injector_parameters;
    injector_parameters.fuel_density_kg_m3 = fuel.density_kg_m3();
    ecu_hw::Ma17InjectorStage injector_stage{injector_parameters};
    TpsSources tps_sources{throttle, tps_circuit, thermal, sensor_circuit,
                           nullptr,
                           g_instr_counter, config->tps1_high_tick,
                           config->tps1_restore_tick, config->tps2_high_tick,
                           config->tps2_restore_tick, config->tps_open_tick,
                           config->tps_restore_tick,
                           static_cast<double>(config->tps_open_mv) / 1000.0,
                           config->ect_open_tick,
                           config->ect_restore_tick,
                           config->adc4_mv >= 0
                               ? static_cast<double>(config->adc4_mv) / 1000.0
                               : 1.760, // Unknown board source; legacy ADC=90.
                           config->adc7_boundary_v,
                           config->adc7_step_v, config->adc7_step_tick,
                           config->lambda_stuck_v,
                           config->lambda_stuck_tick,
                           config->lambda_restore_tick};
    sim.target_rpm = config->crank_rpm;
    sim.update_pulse_interval(990000); // 11.88 MHz / 12 = 990k ticks/sec
    if (config->crank_immediate)
        sim.startup_delay_instrs = 0;

    // Inicializa PTY
    fprintf(stderr, "[DEBUG] Iniciando abertura de PTY...\n");
    fflush(stderr);

    if (!g_uart.open_pty_4800_8N1()) {
        fprintf(stderr, "[ERRO] Falha ao abrir PTY\n");
        return 1;
    }

    fprintf(stdout, "[emu8051-pty] PTY pronto em: %s (4800 8N1)\n",
            g_uart.slave_path.c_str());
    fprintf(stdout,
            "Conecte seu scanner a esse dispositivo. Ctrl+C para sair.\n");
    fflush(stdout);

    // Keep ROM, XRAM and upper IRAM alive for all core callbacks.
    static ma17::CpuContext context;
    em8051 &cpu = context.cpu;
    ma17::CpuHooks hooks{g_uart_scheduler, g_ports, g_instr_counter};
    hooks.install_uart(cpu);

    // Reset - agora é seguro chamar com aWipe=true
    fprintf(stderr, "[DEBUG] Chamando reset()...\n");
    fflush(stderr);
    reset(&cpu, true);
    const char *xram_state_file = std::getenv("MA17_XRAM_STATE_FILE");
    bool xram_state_loaded = false;
    if (!load_xram_state(cpu, xram_state_file, xram_state_loaded)) {
        fprintf(stderr, "[XRAM-STATE] invalid or unreadable state file\n");
        return 2;
    }
    if (xram_state_loaded)
        cpu.mSFR[REG_PCON] &= static_cast<uint8_t>(~0x10u); // Warm: POF=0.

    // Legacy startup marker; reset() clears XRAM before this initialization.
    // MOVX @R1 with P2=F8h addresses page F8h, not page 00h.
    // The firmware clears RAM[47h] during boot, so this does not prevent
    // its control-loop restart while RPM remains zero.
    if (!config->physical_crank) {
        cpu.mExtData[0xF8F8] = 0xFF; // Legacy startup marker
        cpu.mLowerData[0x47] = 0xFF;
        fprintf(stderr, "[XRAM] Initialized XRAM[0xF8F8]=0xFF, "
                        "RAM_47=0xFF (legacy startup marker)\n");
        fflush(stderr);
    }

    // Timer 2 support now fully implemented via PR #40
    // (https://github.com/jarikomppa/emu8051/pull/40)
    fprintf(
        stderr,
        "[8052] Timer 2 support enabled (T2CON, TL2, TH2, RCAP2L, RCAP2H)\n");
    fflush(stderr);

    // Carrega ROM sobre a memória zerada
    fprintf(stderr, "[DEBUG] Carregando ROM de: %s\n", rompath);
    fflush(stderr);
    if (!ma17::load_bin_to_code(&cpu, rompath, 0x0000))
        return 1;

    // DEBUG: Verify ROM was loaded correctly
    fprintf(stderr, "[DEBUG] ROM verification: mCodeMem=%p\n",
            static_cast<void *>(cpu.mCodeMem));
    fprintf(stderr,
            "[DEBUG] ROM[0x0000]=0x%02X ROM[0x0001]=0x%02X ROM[0x0002]=0x%02X "
            "(reset vector)\n",
            cpu.mCodeMem[0x0000], cpu.mCodeMem[0x0001], cpu.mCodeMem[0x0002]);
    fprintf(stderr,
            "[DEBUG] ROM[0x002B]=0x%02X ROM[0x002D]=0x%02X (Timer 2 ISR)\n",
            cpu.mCodeMem[0x002B], cpu.mCodeMem[0x002D]);
    fflush(stderr);

    hooks.install_fiat_peripherals(cpu);
    if (config->physical_crank)
        ma17::set_adc_voltage_provider(read_tps_voltage, &tps_sources);

    // SCON modo 1 (8-bit UART, variável): SM0=0, SM1=1 por padrão de muitas
    // ROMs Forçar estado limpo: Mode 1, REN=1, flags TI/RI limpos Isso evita
    // que a ROM fique presa aguardando um byte lido durante reset
    cpu.mSFR[SFR_SCON - 0x80] = 0x50; // SM1=1, REN=1, TI/RI clear

    // Initialize dual SBUF registers (TX and RX separate!)
    g_uart_scheduler.reset_buffers();
    cpu.mSFR[SFR_SBUF - 0x80] = 0x00; // SFR array init (compatibility)

    // K-line 5-baud initialization setup
    // RAM_17 @ 0x17: Enable K-line detection (must be non-zero per ROM @
    // 0x4C44)
    if (!config->physical_crank) {
        cpu.mLowerData[0x17] = 0x7F;
        fprintf(stderr, "[K-LINE] Habilitado detecção 5-baud "
                        "(RAM_17=0x7F)\n");
    }

    // P4 @ 0xE8: Initialize port (initial value from ROM @ 0x085E)
    cpu.mSFR[SFR_P4 - 0x80] = 0xEA;
    fprintf(stderr, "[K-LINE] P4 inicializado (0x%02X)\n",
            cpu.mSFR[SFR_P4 - 0x80]);
    fflush(stderr);

    // Loop principal: step e serviço de UART
    signal(SIGINT, sigint_handler);
    signal(SIGUSR1, sigusr1_handler);

    fprintf(stderr, "[DEBUG] Iniciando loop principal de emulação...\n");
    fprintf(stderr,
            "[DEBUG] Send SIGUSR1 to inject 5-baud init: kill -USR1 %d\n",
            getpid());
    fprintf(stderr, "[DEBUG] PC inicial: 0x%04X\n", cpu.mPC);
    fprintf(stderr,
            "[CRANKSHAFT] Waiting %lld ticks before pulse injection "
            "(RPM=%d)...\n",
            sim.startup_delay_instrs, sim.target_rpm);
    fflush(stderr);

    // Debug: Mostra estado da UART periodicamente
    // int debug_counter = 0;  // DISABLED: not needed when verbose logging is
    // off

    // Fiat clock model: 11.88 MHz / 12 = 990,000 machine-cycle ticks/s.
    constexpr int64_t machine_cycles_per_second = 990000;
    const int steps_per_tick = 500;
    constexpr std::chrono::nanoseconds tick_duration_ns =
        std::chrono::nanoseconds(std::chrono::seconds(1)) /
        (machine_cycles_per_second / steps_per_tick);

    fprintf(stderr, "[DEBUG] Emulation timing: %d steps/tick, ~%lld ns/step\n",
            steps_per_tick,
            static_cast<long long>(tick_duration_ns.count() /
                                   static_cast<long long>(steps_per_tick)));

    const bool trace_pc = getenv("MA17_TRACE_PC") != nullptr;
    ma17::EmulatorLoopContext loop{cpu,
                                   sim,
                                   g_uart,
                                   g_uart_scheduler,
                                   g_5baud_injector,
                                   g_running,
                                   g_inject_5baud,
                                   g_instr_counter,
                                   start,
                                   tick_duration_ns,
                                   steps_per_tick,
                                   trace_pc};
    loop.on_snapshot = observer.on_snapshot;
    loop.snapshot_context = observer.context;
    loop.on_event = observer.on_event;
    loop.event_context = observer.context;
    loop.cancel = observer.cancel;
    loop.on_control = observer.on_control;
    loop.control_context = observer.context;
    if (config->physical_crank) {
        loop.physical_crank = &physical_crank;
        loop.drivetrain = drivetrain ? &*drivetrain : nullptr;
        loop.physical_pty_realtime = config->physical_pty_realtime;
        loop.physical_plant_friction_temp = config->physical_plant;
        loop.physical_plant_accessories = config->physical_plant && config->accessory_load;
        auto experiment = [&](const char *key, double fallback) {
            const auto it = config->experiments.find(key);
            return it == config->experiments.end() ? fallback : it->second;
        };
        loop.accessory_params.alternator_scale = experiment("acc_alt_scale", 1.0);
        loop.accessory_params.pump_scale = experiment("acc_pump_scale", 1.0);
        if (const char *cycles = std::getenv("SEVEL_PLANT_WINDOW_CYCLES"))
            loop.plant_window.set_window_cycles(std::atof(cycles));
        loop.physical_input = &physical_input;
        if (config->tdc_reference_deg >= 0 || config->swap_ignition_coils ||
            config->ethanol_percent != 0 || config->physical_plant) {
            engine::CombustionParameters parameters;
            if (config->tdc_reference_deg >= 0)
                parameters.tdc_phase_rad =
                    static_cast<double>(config->tdc_reference_deg) *
                    std::numbers::pi / 180.0;
            parameters.swap_coil_channels = config->swap_ignition_coils;
            parameters.physical_efficiency = config->physical_plant;
            parameters.exp_force_mbt = experiment("adv_force_mbt", 0.0) != 0.0;
            parameters.exp_torque_saturate = experiment("spark_torque_saturate", 0.0) != 0.0;
            parameters.exp_adv_offset_deg = experiment("adv_offset_deg", 0.0);
            loop.combustion = engine::Combustion{parameters, fuel};
        }
        engine::ExhaustParameters exhaust_parameters;
        exhaust_parameters.fuel = fuel;
        exhaust_parameters.narrowband_slope = config->lambda_switch_slope;
        loop.exhaust = engine::ExhaustLambda{exhaust_parameters};
        loop.starter_stop_tick = config->starter_ticks;
        loop.physical_stop_tick = config->stop_ticks;
        loop.crank_sensor_open_tick = config->crank_sensor_open_tick;
        loop.crank_sensor_restore_tick = config->crank_sensor_restore_tick;
        loop.throttle = &throttle;
        loop.idle_bridge_candidate = config->idle_bridge_p15_p16;
        loop.idle_bridge = ecu_hw::Ma17IdleBridge{
            config->battery_v, config->idle_bridge_reverse};
        loop.idle_motor_disconnect_tick = config->idle_motor_disconnect_tick;
        loop.idle_motor_reconnect_tick = config->idle_motor_reconnect_tick;
        if (config->idle_min_stop_mrad >= 0 ||
            config->idle_motor_speed_mm_s > 0) {
            engine::IdleActuatorParameters parameters;
            if (config->idle_min_stop_mrad >= 0) {
                parameters.base_stop_rad =
                    static_cast<double>(config->idle_min_stop_mrad) / 1000.0;
                parameters.initial_stem_m =
                    (throttle.stop_angle_rad() - parameters.base_stop_rad) /
                    parameters.lever_rad_per_m;
            }
            if (config->idle_motor_speed_mm_s > 0)
                parameters.maximum_speed_m_s =
                    static_cast<double>(config->idle_motor_speed_mm_s) / 1000.0;
            loop.idle_actuator = engine::IdleActuator{parameters};
        }
        loop.tps_circuit = &tps_circuit;
        loop.pedal_step_tick = config->pedal_step_tick;
        loop.pedal_release_tick = config->pedal_release_tick;
        loop.pedal_rise_ticks = config->pedal_rise_ticks;
        loop.pedal_pull_m = config->pedal_pull_m;
        if (config->dyno_point_rpm != 0.0) {
            ma17::DynoBenchConfig bench_config;
            bench_config.target_rpm = config->dyno_point_rpm;
            bench_config.cycles = config->dyno_cycles;
            if (experiment("dyno_settle_ticks", 0.0) > 0.0)
                bench_config.settle_end_tick =
                    static_cast<long long>(experiment("dyno_settle_ticks", 0.0));
            dyno_bench.emplace(bench_config);
            loop.bench = &*dyno_bench;
            loop.pedal_step_tick = bench_config.settle_end_tick; // full open at the ramp start
            loop.pedal_rise_ticks = bench_config.ramp_ticks;
            loop.pedal_pull_m = engine::max_pedal_pull_m();
        }
        loop.load_step_tick = config->load_step_tick;
        loop.load_torque_nm = config->load_torque_nm;
        loop.tps1_high_tick = config->tps1_high_tick;
        loop.tps1_restore_tick = config->tps1_restore_tick;
        loop.tps2_high_tick = config->tps2_high_tick;
        loop.tps2_restore_tick = config->tps2_restore_tick;
        loop.thermal = &thermal;
        loop.vehicle_speed_target_kmh = config->vehicle_speed_kmh;
        loop.sensor_circuit = &sensor_circuit;
        loop.pump_relay_p34_candidate = config->pump_relay_p34;
        loop.lambda_adc_pin_override_v = config->lambda_stuck_v;
        loop.lambda_stuck_tick = config->lambda_stuck_tick;
        loop.lambda_restore_tick = config->lambda_restore_tick;
        loop.intake = &intake;
        tps_sources.exhaust = &loop.exhaust;
        loop.injector_stage = &injector_stage;
        loop.injector_disconnect_tick = config->injector_disconnect_tick;
        loop.injector_reconnect_tick = config->injector_reconnect_tick;
        loop.coil_disconnect_tick = config->coil_disconnect_tick;
        loop.coil_reconnect_tick = config->coil_reconnect_tick;
        if (config->coil_channel >= 0)
            loop.coil_channel = static_cast<unsigned>(config->coil_channel);
        loop.fluid_step_ticks = config->fluid_step_ticks;
        loop.ect_open_tick = config->ect_open_tick;
        loop.ect_restore_tick = config->ect_restore_tick;
    }
    ma17::run_emulator_loop(loop);
    if (config->physical_crank)
        ma17::set_adc_voltage_provider(nullptr, nullptr);
    if (!save_xram_state(cpu, xram_state_file)) {
        fprintf(stderr, "[XRAM-STATE] could not save state file\n");
        return 2;
    }

    printf("\n[emu8051-pty] Encerrando.\n");
    return 0;
}
