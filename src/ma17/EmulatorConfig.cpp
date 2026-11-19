#include "ma17/EmulatorConfig.hpp"

#include "engine/ControlLimits.hpp"
#include "ma17/DynoScenario.hpp"

#include <cerrno>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>

extern char **environ;

namespace ma17 {

std::optional<EmulatorConfig> parse_emulator_config(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Uso: %s <rom.bin> [--8052] [--physical-crank "
                        "--starter-ticks N --stop-ticks N "
                        "--vehicle-kmh 0..200] [--drivetrain --gear -1..5 "
                        "--clutch-percent 0..100 --vehicle-mass-kg 500..3000 "
                        "--clutch-max-nm 1..1000]\n", argv[0]);
        return std::nullopt;
    }

    EmulatorConfig config{argv[1]};
    bool drivetrain_options = false;
    auto parse_positive = [](const char *value, long long &target) {
        char *end = nullptr;
        const long long parsed = std::strtoll(value, &end, 10);
        if (!*value || *end != '\0' || parsed <= 0)
            return false;
        target = parsed;
        return true;
    };
    auto parse_millivolts = [](const char *value, long long &target) {
        errno = 0;
        char *end = nullptr;
        const long long parsed = std::strtoll(value, &end, 10);
        if (errno || !*value || *end != '\0' || parsed < 0 || parsed > 5000)
            return false;
        target = parsed;
        return true;
    };
    for (int index = 2; index < argc; ++index) {
        if (strcmp(argv[index], "--8052") == 0) continue;
        if (strcmp(argv[index], "--drivetrain") == 0) {
            config.drivetrain = true;
            continue;
        }
        int *drivetrain_target = nullptr;
        long minimum = 0, maximum = 0;
        if (strcmp(argv[index], "--gear") == 0) {
            drivetrain_target = &config.transmission_gear;
            minimum = -1; maximum = 5;
        } else if (strcmp(argv[index], "--clutch-percent") == 0) {
            drivetrain_target = &config.clutch_percent;
            maximum = 100;
        } else if (strcmp(argv[index], "--vehicle-mass-kg") == 0) {
            drivetrain_target = &config.vehicle_mass_kg;
            minimum = 500; maximum = 3000;
        } else if (strcmp(argv[index], "--clutch-max-nm") == 0) {
            drivetrain_target = &config.clutch_max_nm;
            minimum = 1; maximum = 1000;
        }
        if (drivetrain_target) {
            if (index + 1 >= argc) {
                fprintf(stderr, "Missing drivetrain option value\n");
                return std::nullopt;
            }
            const char *value = argv[++index];
            char *end = nullptr;
            errno = 0;
            const long parsed = std::strtol(value, &end, 10);
            if (errno || !*value || *end || parsed < minimum || parsed > maximum) {
                fprintf(stderr, "Invalid drivetrain option value: %s\n", value);
                return std::nullopt;
            }
            *drivetrain_target = static_cast<int>(parsed);
            drivetrain_options = true;
            continue;
        }
        if (strcmp(argv[index], "--physical-crank") == 0) {
            config.physical_crank = true;
            continue;
        }
        if (strcmp(argv[index], "--tps-bench-profile") == 0) {
            config.tps_bench_profile = true;
            continue;
        }
        if (strcmp(argv[index], "--physical-pty-realtime") == 0) {
            config.physical_pty_realtime = true;
            continue;
        }
        if (strcmp(argv[index], "--swap-ignition-coils") == 0) {
            config.swap_ignition_coils = true;
            continue;
        }
        if (strcmp(argv[index], "--idle-bridge-p15-p16") == 0) {
            config.idle_bridge_p15_p16 = true;
            continue;
        }
        if (strcmp(argv[index], "--idle-bridge-reverse") == 0) {
            config.idle_bridge_reverse = true;
            continue;
        }
        if (strcmp(argv[index], "--idle-contact-p43") == 0) {
            config.idle_contact_p43 = true;
            continue;
        }
        if (strcmp(argv[index], "--idle-contact-p46") == 0) {
            config.idle_contact_p46 = true;
            continue;
        }
        if (strcmp(argv[index], "--idle-contact-p46-high-closed") == 0) {
            config.idle_contact_p46_high_closed = true;
            continue;
        }
        if (strcmp(argv[index], "--pump-relay-p34") == 0) {
            config.pump_relay_p34 = true;
            continue;
        }
        if (index + 1 < argc &&
            strcmp(argv[index], "--idle-contact-open-tick") == 0 &&
            parse_positive(argv[++index], config.idle_contact_open_tick))
            continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--idle-contact-closed-tick") == 0 &&
            parse_positive(argv[++index], config.idle_contact_closed_tick))
            continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--idle-contact-restore-tick") == 0 &&
            parse_positive(argv[++index], config.idle_contact_restore_tick))
            continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--idle-motor-disconnect-tick") == 0 &&
            parse_positive(argv[++index], config.idle_motor_disconnect_tick))
            continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--idle-motor-reconnect-tick") == 0 &&
            parse_positive(argv[++index], config.idle_motor_reconnect_tick))
            continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--idle-motor-speed-mm-s") == 0) {
            errno = 0;
            char *end = nullptr;
            const long value = std::strtol(argv[++index], &end, 10);
            if (!errno && end != argv[index] && *end == '\0' &&
                value >= 1 && value <= 100) {
                config.idle_motor_speed_mm_s = static_cast<int>(value);
                continue;
            }
        }
        if (index + 1 < argc &&
            strcmp(argv[index], "--idle-min-stop-mrad") == 0) {
            errno = 0;
            char *end = nullptr;
            const long value = std::strtol(argv[++index], &end, 10);
            if (!errno && end != argv[index] && *end == '\0' &&
                value >= 0 && value <= 60) {
                config.idle_min_stop_mrad = static_cast<int>(value);
                continue;
            }
        }
        if (strcmp(argv[index], "--physical-plant") == 0) {
            config.physical_plant = true;
            continue;
        }
        if (strcmp(argv[index], "--legacy-throttle") == 0) {
            config.legacy_throttle = true;
            continue;
        }
        if (strcmp(argv[index], "--accessory-load") == 0) {
            config.accessory_load = true;
            continue;
        }
        if (strcmp(argv[index], "--legacy-plant") == 0) {
            config.physical_plant = false;
            continue;
        }
        if (index + 1 < argc &&
            strcmp(argv[index], "--throttle-leak-mm2") == 0) {
            errno = 0;
            char *end = nullptr;
            const long value = std::strtol(argv[++index], &end, 10);
            if (!errno && end != argv[index] && *end == '\0' &&
                value >= 0 && value <= 100) {
                config.throttle_leak_mm2 = static_cast<int>(value);
                continue;
            }
        }
        if (index + 1 < argc && strcmp(argv[index], "--starter-ticks") == 0 &&
            parse_positive(argv[++index], config.starter_ticks)) continue;
        if (index + 1 < argc && strcmp(argv[index], "--stop-ticks") == 0 &&
            parse_positive(argv[++index], config.stop_ticks)) continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--crank-sensor-open-tick") == 0 &&
            parse_positive(argv[++index], config.crank_sensor_open_tick))
            continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--crank-sensor-restore-tick") == 0 &&
            parse_positive(argv[++index], config.crank_sensor_restore_tick))
            continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--pedal-step-tick") == 0 &&
            parse_positive(argv[++index], config.pedal_step_tick)) continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--pedal-release-tick") == 0 &&
            parse_positive(argv[++index], config.pedal_release_tick)) continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--pedal-rise-ticks") == 0 &&
            parse_positive(argv[++index], config.pedal_rise_ticks)) continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--load-step-tick") == 0 &&
            parse_positive(argv[++index], config.load_step_tick)) continue;
        if (index + 1 < argc && strcmp(argv[index], "--load-nm") == 0) {
            long long torque_nm = 0;
            if (parse_positive(argv[++index], torque_nm) &&
                static_cast<double>(torque_nm) <= engine::max_brake_nm()) {
                config.load_torque_nm = static_cast<double>(torque_nm);
                continue;
            }
        }
        if (index + 1 < argc &&
            strcmp(argv[index], "--tps1-high-tick") == 0 &&
            parse_positive(argv[++index], config.tps1_high_tick)) continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--tps1-restore-tick") == 0 &&
            parse_positive(argv[++index], config.tps1_restore_tick)) continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--tps2-high-tick") == 0 &&
            parse_positive(argv[++index], config.tps2_high_tick)) continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--tps2-restore-tick") == 0 &&
            parse_positive(argv[++index], config.tps2_restore_tick)) continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--tps-open-tick") == 0 &&
            parse_positive(argv[++index], config.tps_open_tick)) continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--tps-restore-tick") == 0 &&
            parse_positive(argv[++index], config.tps_restore_tick)) continue;
        if (index + 1 < argc && strcmp(argv[index], "--tps-open-mv") == 0) {
            long long millivolts = 0;
            if (parse_millivolts(argv[++index], millivolts)) {
                config.tps_open_mv = static_cast<int>(millivolts);
                continue;
            }
        }
        if (index + 1 < argc && strcmp(argv[index], "--coolant-c") == 0) {
            char *end = nullptr;
            const long value = std::strtol(argv[++index], &end, 10);
            if (*argv[index] && *end == '\0' && value >= 0 && value <= 120) {
                config.initial_coolant_c = static_cast<double>(value);
                continue;
            }
        }
        if (index + 1 < argc && strcmp(argv[index], "--vehicle-kmh") == 0) {
            errno = 0;
            char *end = nullptr;
            const long value = std::strtol(argv[++index], &end, 10);
            if (!errno && end != argv[index] && *end == '\0' &&
                value >= 0 && value <= 200) {
                config.vehicle_speed_kmh = static_cast<double>(value);
                continue;
            }
        }
        if (index + 1 < argc && strcmp(argv[index], "--battery-mv") == 0) {
            errno = 0;
            char *end = nullptr;
            const long value = std::strtol(argv[++index], &end, 10);
            if (!errno && end != argv[index] && *end == '\0' &&
                value >= 6000 && value <= 16000) {
                config.battery_v = static_cast<double>(value) / 1000.0;
                continue;
            }
        }
        if (index + 1 < argc &&
            strcmp(argv[index], "--ethanol-percent") == 0) {
            errno = 0;
            char *end = nullptr;
            const long value = std::strtol(argv[++index], &end, 10);
            if (!errno && end != argv[index] && *end == '\0' &&
                value >= 0 && value <= 100) {
                config.ethanol_percent = static_cast<int>(value);
                continue;
            }
        }
        if (index + 1 < argc &&
            strcmp(argv[index], "--ect-open-tick") == 0 &&
            parse_positive(argv[++index], config.ect_open_tick)) continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--ect-restore-tick") == 0 &&
            parse_positive(argv[++index], config.ect_restore_tick)) continue;
        if (index + 1 < argc && strcmp(argv[index], "--adc4-mv") == 0) {
            errno = 0;
            char *end = nullptr;
            const long value = std::strtol(argv[++index], &end, 10);
            if (!errno && end != argv[index] && *end == '\0' &&
                value >= 0 && value <= 5000) {
                config.adc4_mv = static_cast<int>(value);
                continue;
            }
        }
        if (index + 1 < argc && strcmp(argv[index], "--adc7-mv") == 0) {
            long long millivolts = 0;
            if (parse_millivolts(argv[++index], millivolts)) {
                config.adc7_boundary_v =
                    static_cast<double>(millivolts) / 1000.0;
                continue;
            }
        }
        if (index + 1 < argc && strcmp(argv[index], "--adc7-step-mv") == 0) {
            long long millivolts = 0;
            if (parse_millivolts(argv[++index], millivolts)) {
                config.adc7_step_v = static_cast<double>(millivolts) / 1000.0;
                continue;
            }
        }
        if (index + 1 < argc &&
            strcmp(argv[index], "--adc7-step-tick") == 0 &&
            parse_positive(argv[++index], config.adc7_step_tick)) continue;
        if (index + 1 < argc && strcmp(argv[index], "--lambda-stuck-mv") == 0) {
            errno = 0;
            char *end = nullptr;
            const long value = std::strtol(argv[++index], &end, 10);
            if (!errno && end != argv[index] && *end == '\0' &&
                value >= 0 && value <= 5000) {
                config.lambda_stuck_v = static_cast<double>(value) / 1000.0;
                continue;
            }
        }
        if (index + 1 < argc &&
            strcmp(argv[index], "--lambda-stuck-tick") == 0 &&
            parse_positive(argv[++index], config.lambda_stuck_tick)) continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--lambda-restore-tick") == 0 &&
            parse_positive(argv[++index], config.lambda_restore_tick)) continue;
        if (index + 1 < argc && strcmp(argv[index], "--lambda-adc-gain") == 0) {
            errno = 0;
            char *end = nullptr;
            const long value = std::strtol(argv[++index], &end, 10);
            if (!errno && end != argv[index] && *end == '\0' &&
                value >= 1 && value <= 8) {
                config.lambda_adc_gain = static_cast<int>(value);
                continue;
            }
        }
        if (index + 1 < argc &&
            strcmp(argv[index], "--lambda-switch-slope") == 0) {
            errno = 0;
            char *end = nullptr;
            const long value = std::strtol(argv[++index], &end, 10);
            if (!errno && end != argv[index] && *end == '\0' &&
                value >= 1 && value <= 1000) {
                config.lambda_switch_slope = static_cast<int>(value);
                continue;
            }
        }
        if (index + 1 < argc &&
            strcmp(argv[index], "--injector-disconnect-tick") == 0 &&
            parse_positive(argv[++index], config.injector_disconnect_tick))
            continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--injector-reconnect-tick") == 0 &&
            parse_positive(argv[++index], config.injector_reconnect_tick))
            continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--coil-disconnect-tick") == 0 &&
            parse_positive(argv[++index], config.coil_disconnect_tick))
            continue;
        if (index + 1 < argc &&
            strcmp(argv[index], "--coil-reconnect-tick") == 0 &&
            parse_positive(argv[++index], config.coil_reconnect_tick))
            continue;
        if (index + 1 < argc && strcmp(argv[index], "--coil-channel") == 0) {
            const char *channel = argv[++index];
            if (strcmp(channel, "0") == 0 || strcmp(channel, "1") == 0) {
                config.coil_channel = channel[0] - '0';
                continue;
            }
        }
        if (index + 1 < argc &&
            strcmp(argv[index], "--tdc-reference-deg") == 0) {
            errno = 0;
            char *end = nullptr;
            const long value = std::strtol(argv[++index], &end, 10);
            if (!errno && end != argv[index] && *end == '\0' &&
                value >= 0 && value < 720) {
                config.tdc_reference_deg = static_cast<int>(value);
                continue;
            }
        }
        if (index + 1 < argc &&
            strcmp(argv[index], "--fluid-step-ticks") == 0) {
            long long step_ticks = 0;
            if (parse_positive(argv[++index], step_ticks) &&
                (step_ticks == 495 || step_ticks == 990)) {
                config.fluid_step_ticks = static_cast<int>(step_ticks);
                continue;
            }
        }
        if (index + 1 < argc && strcmp(argv[index], "--pedal-mm") == 0) {
            errno = 0;
            char *end = nullptr;
            const double millimetres = std::strtod(argv[++index], &end);
            if (!errno && end != argv[index] && *end == '\0' &&
                std::isfinite(millimetres) && millimetres > 0.0 &&
                millimetres / 1000.0 <= engine::max_pedal_pull_m()) {
                config.pedal_pull_m = millimetres / 1000.0;
                continue;
            }
        }
        if (index + 1 < argc && strcmp(argv[index], "--dyno-point") == 0) {
            errno = 0;
            char *end = nullptr;
            const double rpm = std::strtod(argv[++index], &end);
            if (!errno && end != argv[index] && *end == '\0' && rpm >= 800.0 && rpm <= 6500.0) {
                config.dyno_point_rpm = rpm;
                continue;
            }
        }
        if (index + 1 < argc && strcmp(argv[index], "--dyno-cycles") == 0) {
            errno = 0;
            char *end = nullptr;
            const double cycles = std::strtod(argv[++index], &end);
            if (!errno && end != argv[index] && *end == '\0' && cycles >= 4.0 && cycles <= 400.0) {
                config.dyno_cycles = cycles;
                continue;
            }
        }
        if (index + 1 < argc && strcmp(argv[index], "--exp") == 0) {
            const std::string kv = argv[++index];
            const auto eq = kv.find('=');
            if (eq != std::string::npos && eq > 0) {
                char *end = nullptr;
                const std::string value = kv.substr(eq + 1);
                const double number = std::strtod(value.c_str(), &end);
                if (end != value.c_str() && *end == '\0') {
                    config.experiments[kv.substr(0, eq)] = number;
                    continue;
                }
            }
        }
        if (strcmp(argv[index], "--dyno-scenario") == 0) {
            DynoScenario{}.apply(config); // later options override single fields
            continue;
        }
        if (strcmp(argv[index], "--pedal-full-open") == 0) {
            config.pedal_pull_m = engine::max_pedal_pull_m();
            continue;
        }
        fprintf(stderr, "Invalid emulator argument: %s\n", argv[index]);
        return std::nullopt;
    }
    if ((config.drivetrain && !config.physical_crank) ||
        (drivetrain_options && !config.drivetrain)) {
        fprintf(stderr, "Drivetrain options require --drivetrain --physical-crank\n");
        return std::nullopt;
    }
    if (config.physical_crank) {
        if ((config.tps_open_tick && config.tps_open_mv < 0) ||
            (!config.tps_open_tick &&
             (config.tps_open_mv >= 0 || config.tps_restore_tick)) ||
            (config.tps_open_tick &&
             config.tps_open_tick >= config.stop_ticks) ||
            (config.tps_restore_tick &&
             (config.tps_restore_tick <= config.tps_open_tick ||
              config.tps_restore_tick >= config.stop_ticks))) {
            fprintf(stderr, "TPS open test requires an explicit voltage "
                            "and ordered ticks within the run\n");
            return std::nullopt;
        }
        if (config.idle_motor_speed_mm_s > 0 &&
            !config.idle_bridge_p15_p16) {
            fprintf(stderr, "Idle motor speed requires P1.5/P1.6 binding\n");
            return std::nullopt;
        }
        if (config.idle_bridge_reverse && !config.idle_bridge_p15_p16) {
            fprintf(stderr, "Reverse idle bridge requires P1.5/P1.6 binding\n");
            return std::nullopt;
        }
        if ((config.idle_contact_p43 &&
             (config.idle_contact_p46 ||
              config.idle_contact_p46_high_closed)) ||
            (config.idle_contact_p46 &&
             config.idle_contact_p46_high_closed) ||
            ((config.idle_contact_p43 || config.idle_contact_p46 ||
              config.idle_contact_p46_high_closed) &&
             !config.idle_bridge_p15_p16)) {
            fprintf(stderr, "Choose one idle contact binding with bridge\n");
            return std::nullopt;
        }
        if ((config.idle_contact_open_tick &&
             config.idle_contact_closed_tick) ||
            ((config.idle_contact_open_tick ||
              config.idle_contact_closed_tick) &&
             !(config.idle_contact_p43 || config.idle_contact_p46 ||
               config.idle_contact_p46_high_closed)) ||
            config.idle_contact_open_tick >= config.stop_ticks ||
            config.idle_contact_closed_tick >= config.stop_ticks ||
            (config.idle_contact_restore_tick &&
             (!(config.idle_contact_open_tick ||
                config.idle_contact_closed_tick) ||
              config.idle_contact_restore_tick <=
                  (config.idle_contact_open_tick
                       ? config.idle_contact_open_tick
                       : config.idle_contact_closed_tick) ||
              config.idle_contact_restore_tick >= config.stop_ticks))) {
            fprintf(stderr, "Idle contact fault requires a wired contact "
                            "and ordered ticks within the run\n");
            return std::nullopt;
        }
        if (config.idle_min_stop_mrad >= 0 &&
            !config.idle_bridge_p15_p16) {
            fprintf(stderr, "Idle stop setting requires idle bridge\n");
            return std::nullopt;
        }
        if ((config.idle_motor_disconnect_tick &&
             !config.idle_bridge_p15_p16) ||
            config.idle_motor_disconnect_tick >= config.stop_ticks ||
            (config.idle_motor_reconnect_tick &&
             (!config.idle_motor_disconnect_tick ||
              config.idle_motor_reconnect_tick <=
                  config.idle_motor_disconnect_tick ||
              config.idle_motor_reconnect_tick >= config.stop_ticks))) {
            fprintf(stderr, "Idle motor fault requires bridge and ordered "
                            "ticks within the run\n");
            return std::nullopt;
        }
        if (!config.starter_ticks || !config.stop_ticks ||
            config.starter_ticks >= config.stop_ticks) {
            fprintf(stderr, "Physical crank requires 0 < starter-ticks "
                            "< stop-ticks\n");
            return std::nullopt;
        }
        if (config.crank_sensor_open_tick >= config.stop_ticks ||
            (config.crank_sensor_restore_tick &&
             (!config.crank_sensor_open_tick ||
              config.crank_sensor_restore_tick <=
                  config.crank_sensor_open_tick ||
              config.crank_sensor_restore_tick >= config.stop_ticks))) {
            fprintf(stderr, "Crank sensor fault ticks must be ordered "
                            "within the run\n");
            return std::nullopt;
        }
        if (config.dyno_point_rpm != 0.0 &&
            (config.pedal_step_tick || config.pedal_release_tick || config.pedal_pull_m != 0.0 ||
             config.load_step_tick || config.load_torque_nm != 0.0)) {
            fprintf(stderr, "--dyno-point owns the pedal and the brake: no pedal/load options\n");
            return std::nullopt;
        }
        const long long pedal_limit_tick = config.pedal_release_tick
                                               ? config.pedal_release_tick
                                               : config.stop_ticks;
        if ((config.pedal_step_tick != 0) !=
                (config.pedal_pull_m != 0.0) ||
            config.pedal_step_tick >= config.stop_ticks ||
            (config.pedal_rise_ticks &&
             (!config.pedal_step_tick ||
              config.pedal_rise_ticks >=
                  pedal_limit_tick - config.pedal_step_tick)) ||
            (config.pedal_release_tick &&
             (!config.pedal_step_tick ||
              config.pedal_release_tick <= config.pedal_step_tick ||
              config.pedal_release_tick >= config.stop_ticks)) ||
            config.tps1_high_tick >= config.stop_ticks ||
            (config.tps1_restore_tick &&
             (!config.tps1_high_tick ||
              config.tps1_restore_tick <= config.tps1_high_tick ||
              config.tps1_restore_tick >= config.stop_ticks)) ||
            config.tps2_high_tick >= config.stop_ticks ||
            (config.tps2_restore_tick &&
             (!config.tps2_high_tick ||
              config.tps2_restore_tick <= config.tps2_high_tick ||
              config.tps2_restore_tick >= config.stop_ticks))) {
            fprintf(stderr, "Pedal/fault ticks must be within the run; "
                            "pedal step requires both options\n");
            return std::nullopt;
        }
        if ((config.load_step_tick != 0) !=
                (config.load_torque_nm != 0.0) ||
            config.load_step_tick >= config.stop_ticks) {
            fprintf(stderr, "Load step requires a tick within the run and "
                            "a positive torque\n");
            return std::nullopt;
        }
        if (config.ect_open_tick >= config.stop_ticks ||
            (config.ect_restore_tick &&
             (!config.ect_open_tick ||
              config.ect_restore_tick <= config.ect_open_tick ||
              config.ect_restore_tick >= config.stop_ticks))) {
            fprintf(stderr, "ECT fault ticks must be ordered within the run\n");
            return std::nullopt;
        }
        if ((config.adc7_step_v >= 0.0) != (config.adc7_step_tick > 0) ||
            (config.adc7_step_tick &&
             (config.adc7_boundary_v < 0.0 ||
              config.adc7_step_tick >= config.stop_ticks))) {
            fprintf(stderr, "ADC7 step requires an initial voltage and "
                            "a tick within the run\n");
            return std::nullopt;
        }
        if ((config.lambda_stuck_tick && config.lambda_stuck_v < 0.0) ||
            config.lambda_stuck_tick >= config.stop_ticks ||
            (config.lambda_restore_tick &&
             (config.lambda_stuck_v < 0.0 ||
              config.lambda_restore_tick <= config.lambda_stuck_tick ||
              config.lambda_restore_tick >= config.stop_ticks))) {
            fprintf(stderr, "Lambda fault ticks require a voltage and "
                            "must be ordered within the run\n");
            return std::nullopt;
        }
        if (config.injector_disconnect_tick >= config.stop_ticks ||
            (config.injector_reconnect_tick &&
             (!config.injector_disconnect_tick ||
              config.injector_reconnect_tick <=
                  config.injector_disconnect_tick ||
              config.injector_reconnect_tick >= config.stop_ticks))) {
            fprintf(stderr, "Injector fault ticks must be ordered within "
                            "the run\n");
            return std::nullopt;
        }
        if ((config.coil_channel >= 0) !=
                (config.coil_disconnect_tick > 0) ||
            config.coil_disconnect_tick >= config.stop_ticks ||
            (config.coil_reconnect_tick &&
             (!config.coil_disconnect_tick ||
              config.coil_reconnect_tick <= config.coil_disconnect_tick ||
              config.coil_reconnect_tick >= config.stop_ticks))) {
            fprintf(stderr, "Coil fault requires channel 0/1 and ordered "
                            "ticks within the run\n");
            return std::nullopt;
        }
        for (char **entry = environ; *entry; ++entry) {
            if (strncmp(*entry, "MA17_", 5) == 0 &&
                strncmp(*entry, "MA17_TRACE_", 11) != 0 &&
                strncmp(*entry, "MA17_WARM_REBOOT_TICK=", 22) != 0 &&
                strncmp(*entry, "MA17_XRAM_STATE_FILE=", 21) != 0) {
                fprintf(stderr, "Physical crank rejects MA17_* override: "
                                "%.*s\n",
                        static_cast<int>(strcspn(*entry, "=")), *entry);
                return std::nullopt;
            }
        }
    } else if (config.physical_pty_realtime ||
               config.starter_ticks || config.stop_ticks ||
               config.crank_sensor_open_tick ||
               config.crank_sensor_restore_tick ||
               config.pedal_step_tick || config.pedal_release_tick ||
               config.pedal_rise_ticks ||
               config.pedal_pull_m != 0.0 || config.dyno_point_rpm != 0.0 ||
               config.tps_bench_profile ||
               config.idle_bridge_p15_p16 ||
               config.idle_bridge_reverse ||
               config.idle_contact_p43 ||
               config.idle_contact_p46 ||
               config.idle_contact_p46_high_closed ||
               config.pump_relay_p34 ||
               config.idle_contact_open_tick ||
               config.idle_contact_closed_tick ||
               config.idle_contact_restore_tick ||
               config.idle_motor_disconnect_tick ||
               config.idle_motor_reconnect_tick ||
               config.idle_motor_speed_mm_s > 0 ||
               config.idle_min_stop_mrad >= 0 ||
               config.throttle_leak_mm2 >= 0 || config.accessory_load || config.legacy_throttle ||
               config.load_step_tick || config.load_torque_nm != 0.0 ||
               config.tps1_high_tick || config.tps1_restore_tick ||
               config.tps2_high_tick || config.tps2_restore_tick ||
               config.tps_open_tick || config.tps_restore_tick ||
               config.tps_open_mv >= 0 ||
               config.initial_coolant_c != 20.0 ||
               config.vehicle_speed_kmh != 0.0 || config.ect_open_tick ||
               config.ect_restore_tick || config.adc4_mv >= 0 ||
               config.adc7_boundary_v >= 0.0 ||
               config.adc7_step_v >= 0.0 || config.adc7_step_tick ||
               config.lambda_stuck_v >= 0.0 ||
               config.lambda_stuck_tick || config.lambda_restore_tick ||
               config.lambda_adc_gain != 1 ||
               config.lambda_switch_slope != 25 ||
               config.injector_disconnect_tick ||
               config.injector_reconnect_tick ||
               config.coil_disconnect_tick ||
               config.coil_reconnect_tick || config.coil_channel >= 0 ||
               config.tdc_reference_deg >= 0 ||
               config.swap_ignition_coils ||
               config.fluid_step_ticks != 990) {
        fprintf(stderr, "Physical scenario options require --physical-crank\n");
        return std::nullopt;
    }
    // Size rejects the known 64 KiB Renault dump; it cannot identify another
    // 32 KiB image. The override still runs the Fiat clock and port model.
    fprintf(stderr,
            "[PROFILE] Fiat MA1.7/C517A harness: 11.88 MHz, P4 K-line, "
            "P1.0 crank input; verify hardware before using another ROM\n");
    std::error_code rom_size_error;
    const auto rom_size =
        std::filesystem::file_size(config.rom_path, rom_size_error);
    if (!rom_size_error && rom_size != 32768) {
        fprintf(stderr,
                "[PROFILE] ROM has %llu bytes (Fiat reference: 32768); "
                "clock and port stimuli are unverified for this image\n",
                static_cast<unsigned long long>(rom_size));
        const char *foreign_override = std::getenv("MA17_ALLOW_FOREIGN_ROM");
        if (!foreign_override || strcmp(foreign_override, "1") != 0) {
            fprintf(stderr,
                    "[PROFILE] Refusing Fiat hardware emulation for this ROM; "
                    "set MA17_ALLOW_FOREIGN_ROM=1 for experimental use\n");
            return std::nullopt;
        }
        fprintf(
            stderr,
            "[PROFILE] Experimental Fiat hardware profile override enabled\n");
    }

    if (const char *setting = std::getenv("MA17_CRANK_RPM")) {
        char *end = nullptr;
        const long rpm = std::strtol(setting, &end, 10);
        if (*setting && *end == '\0' && rpm >= 300 && rpm <= 6000)
            config.crank_rpm = static_cast<int>(rpm);
        else
            fprintf(stderr,
                    "[CRANKSHAFT] invalid MA17_CRANK_RPM=%s; using 1000\n",
                    setting);
    }
    config.crank_immediate = std::getenv("MA17_CRANK_IMMEDIATE") != nullptr;
    return config;
}

} // namespace ma17
