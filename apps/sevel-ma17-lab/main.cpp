#include "lab/AcousticAdapter.hpp"
#include "lab/RecordingRenderer.hpp"
#include "lab/SevelScene.hpp"
#include "lab/SimSession.hpp"
#include "lab/WavWriter.hpp"
#ifdef SEVEL_LAB_SDL3
#include "lab/SdlDisplay.hpp"
#endif
#include "ma17/Diagnostics.hpp"
#include "ma17/Runner.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <cerrno>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <optional>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace {

struct CaptureState {
    long long target_tick = 1485000;
    ma17::EmulatorSnapshot snapshot;
    bool captured = false;
    std::vector<ma17::EmulatorEvent> events;
    unsigned long long event_overflow = 0;
};

void on_snapshot(const ma17::EmulatorSnapshot &snapshot, void *raw) {
    auto &state = *static_cast<CaptureState *>(raw);
    if (!state.captured && snapshot.tick >= state.target_tick) {
        state.snapshot = snapshot;
        state.captured = true;
    }
}

void on_event(const ma17::EmulatorEvent &event, void *raw) {
    auto &state = *static_cast<CaptureState *>(raw);
    if (state.events.size() < 65536)
        state.events.push_back(event);
    else
        ++state.event_overflow;
}

bool parse_tick(const char *text, long long &tick, long long minimum = 1) {
    if (!text || !*text)
        return false;
    errno = 0;
    char *end = nullptr;
    const long long parsed = std::strtoll(text, &end, 10);
    if (errno || *end != '\0' || parsed < minimum)
        return false;
    tick = parsed;
    return true;
}

void hash_word(std::uint64_t &hash, std::uint64_t value) {
    for (unsigned shift = 0; shift < 64; shift += 8) {
        hash ^= (value >> shift) & 0xffU;
        hash *= 1099511628211ULL;
    }
}

void print_lab_state(const ma17::EmulatorSnapshot &snapshot,
                     const lab::EventWindow &window,
                     unsigned long long overflow) {
    std::uint64_t state_hash = 14695981039346656037ULL;
    const auto real = [&state_hash](double value) {
        hash_word(state_hash, std::bit_cast<std::uint64_t>(value));
    };
    hash_word(state_hash, static_cast<std::uint64_t>(snapshot.tick));
    for (double value :
         {snapshot.crank_angle_rad, snapshot.rpm, snapshot.throttle_angle_rad,
          snapshot.pedal_pull_m, snapshot.applied_load_nm,
          snapshot.fuel_film_kg, snapshot.fuel_vapor_kg, snapshot.tps_track1_v,
          snapshot.tps_track2_v, snapshot.lambda, snapshot.lambda_voltage_v,
          snapshot.coolant_c, snapshot.vehicle_speed_kmh,
          snapshot.thermostat_open_fraction})
        real(value);
    for (std::uint64_t value : std::array<std::uint64_t, 13>{
             snapshot.pc, snapshot.ram47, snapshot.ram27_faults,
             snapshot.ram28_faults, snapshot.cc3_high, snapshot.p50_high,
             snapshot.p51_high, snapshot.lamp_on_candidate, snapshot.key_on,
             snapshot.injector_pulses, snapshot.burns, snapshot.missed_sparks,
             snapshot.radiator_fan_on})
        hash_word(state_hash, value);
    for (auto burns : snapshot.burns_by_cylinder)
        hash_word(state_hash, burns);
    for (auto value : snapshot.rom_current_fault_banks)
        hash_word(state_hash, value);
    for (auto value : snapshot.rom_history_fault_banks)
        hash_word(state_hash, value);
    std::uint64_t event_hash = 14695981039346656037ULL;
    hash_word(event_hash, static_cast<std::uint64_t>(window.base_index));
    for (const auto &event : window.events) {
        for (std::uint64_t value : std::array<std::uint64_t, 5>{
                 static_cast<std::uint64_t>(event.tick),
                 static_cast<std::uint64_t>(event.type), event.channel,
                 event.high, event.cylinder_index})
            hash_word(event_hash, value);
        for (double value :
             {event.crank_angle_rad, event.rpm, event.burned_fuel_kg})
            hash_word(event_hash, std::bit_cast<std::uint64_t>(value));
    }
    std::printf("[LAB-STATE] tick=%lld rpm=%.17g ram47=%u cc3=%llu "
                "burns=%llu state=%016llx events=%zu event_hash=%016llx "
                "overflow=%llu\n",
                snapshot.tick, snapshot.rpm,
                static_cast<unsigned>(snapshot.ram47), snapshot.injector_pulses,
                snapshot.burns, static_cast<unsigned long long>(state_hash),
                window.events.size(),
                static_cast<unsigned long long>(event_hash), overflow);
}

bool trace_metadata(const std::vector<std::string> &args,
                    lab::ControlTraceMetadata &metadata) {
    std::ifstream rom(args[1], std::ios::binary);
    if (!rom)
        return false;
    metadata.present = true;
    metadata.rom_hash = 14695981039346656037ULL;
    std::array<char, 4096> bytes{};
    while (rom.read(bytes.data(), bytes.size()) || rom.gcount() > 0) {
        const auto count = rom.gcount();
        metadata.rom_size += static_cast<std::uint64_t>(count);
        for (std::size_t index = 0; index < static_cast<std::size_t>(count);
             ++index) {
            metadata.rom_hash ^= static_cast<unsigned char>(bytes[index]);
            metadata.rom_hash *= 1099511628211ULL;
        }
    }
    if (!rom.eof())
        return false;
    for (std::size_t index = 3; index < args.size(); ++index) {
        if (args[index] == "--stop-ticks") {
            ++index;
            continue;
        }
        metadata.scenario_args.push_back(args[index]);
    }
    return true;
}

void usage(const char *program) {
    std::fprintf(stderr,
                 "Usage: %s ROM [--headless] [--capture-tick N] [--capture-svg PATH] "
                 "[--capture-wav PATH] [--screenshot PATH.png] "
                 "[--window-frames N] [--live] [--auto-start] [--gpu-preview] "
                 "[--cad-assets DIRECTORY|MANIFEST|bundled] [--cad-panel|--no-cad] [--cad-preset JSON] [--bench-preset|--no-bench-preset] "
                 "[--no-audio] [--frame-delay-ms N] [--verbose] "
                 "[--ui-scale 100|150|200] "
                 "[--save-controls PATH] [--replay-controls PATH] "
                 "[MA1.7 physical scenario options]\n"
                 "Interactive defaults: live, bundled CAD panel, warm bench preset, uncapped frame pacing.\n",
                 program);
}

} // namespace

int main(int argc, char **argv) {
    // Keep diagnostic records intact and timely when a launcher combines both streams.
    std::setvbuf(stdout, nullptr, _IOLBF, 0);
    if (argc < 2) {
        usage(argv[0]);
        return 2;
    }
    CaptureState capture;
    std::string svg_path;
    std::string wav_path;
    std::string screenshot_path;
    std::string save_controls_path;
    std::string replay_controls_path;
    bool headless = false;
    bool live = false;
    bool auto_start = false;
    std::optional<bool> bench_option;
    bool disable_cad = false;
    bool capture_tick_requested = false;
    bool gpu_preview = false;
    std::string cad_assets;
    std::string cad_preset;
    bool cad_panel = false;
    bool enable_audio = true;
    int window_frames = 0;
    std::optional<int> frame_delay_ms;
    int ui_scale_percent = 0;
    ma17::verbose_diagnostics = false;
    // The calibration view reads the table bytes from the same ROM.
    setenv("SEVEL_ROM_PATH", argv[1], 1);
    std::vector<std::string> harness_args{argv[0], argv[1], "--physical-crank"};
    for (int index = 2; index < argc; ++index) {
        const std::string option = argv[index];
        if (option == "--headless") {
            headless = true;
        } else if (option == "--live") {
            live = true;
        } else if (option == "--verbose") {
            ma17::verbose_diagnostics = true;
        } else if (option == "--auto-start") {
            auto_start = true;
        } else if (option == "--bench-preset" || option == "--no-bench-preset") {
            bench_option = option == "--bench-preset";
        } else if (option == "--no-cad") {
            disable_cad = true;
        } else if (option == "--gpu-preview") {
            gpu_preview = true;
        } else if (option == "--cad-assets" && index+1 < argc) {
            cad_assets = argv[++index];
            gpu_preview = true;
        } else if (option == "--cad-preset" && index+1 < argc) {
            cad_preset = argv[++index];
        } else if (option == "--cad-panel") {
            cad_panel = true;
            gpu_preview = true;
            if (cad_assets.empty()) cad_assets = "bundled";
        } else if (option == "--no-audio") {
            enable_audio = false;
        } else if (option == "--frame-delay-ms" && index + 1 < argc) {
            long long parsed = 0;
            if (!parse_tick(argv[++index], parsed, 0) || parsed > 1000) {
                usage(argv[0]);
                return 2;
            }
            frame_delay_ms = static_cast<int>(parsed);
        } else if (option == "--ui-scale" && index + 1 < argc) {
            long long parsed = 0;
            if (!parse_tick(argv[++index], parsed) ||
                (parsed != 100 && parsed != 150 && parsed != 200)) {
                usage(argv[0]);
                return 2;
            }
            ui_scale_percent = static_cast<int>(parsed);
        } else if (option == "--save-controls" && index + 1 < argc) {
            save_controls_path = argv[++index];
        } else if (option == "--replay-controls" && index + 1 < argc) {
            replay_controls_path = argv[++index];
        } else if (option == "--capture-tick" && index + 1 < argc) {
            capture_tick_requested = true;
            if (!parse_tick(argv[++index], capture.target_tick)) {
                usage(argv[0]);
                return 2;
            }
        } else if (option == "--capture-svg" && index + 1 < argc) {
            svg_path = argv[++index];
        } else if (option == "--capture-wav" && index + 1 < argc) {
            wav_path = argv[++index];
        } else if (option == "--screenshot" && index + 1 < argc) {
            screenshot_path = argv[++index];
        } else if (option == "--window-frames" && index + 1 < argc) {
            long long parsed = 0;
            if (!parse_tick(argv[++index], parsed) || parsed > 1000000) {
                usage(argv[0]);
                return 2;
            }
            window_frames = static_cast<int>(parsed);
        } else {
            harness_args.push_back(option);
        }
    }
    const bool interactive = !headless && !capture_tick_requested &&
        screenshot_path.empty() && svg_path.empty() && wav_path.empty();
    live |= interactive;
    if (interactive && !disable_cad && !gpu_preview) {
        gpu_preview = cad_panel = true;
        cad_assets = "bundled";
    }
    if ((disable_cad && (gpu_preview || !cad_preset.empty())) ||
        (headless && svg_path.empty() && wav_path.empty()) ||
        (auto_start && !live) || (gpu_preview && !live) || (headless && live) ||
        (!cad_preset.empty() && cad_assets.empty()) ||
        (!live && !headless &&
         (!save_controls_path.empty() || !replay_controls_path.empty())) ||
        (!live && (!enable_audio || frame_delay_ms.has_value())) ||
        (headless && !save_controls_path.empty() &&
         replay_controls_path.empty())) {
        usage(argv[0]);
        return 2;
    }
#ifndef SEVEL_LAB_SDL3
    if (!headless || !screenshot_path.empty() || window_frames != 0 ||
        gpu_preview) {
        usage(argv[0]);
        return 2;
    }
#endif
    std::vector<lab::AppliedControl> replay_controls;
    lab::ControlTraceMetadata recorded_metadata;
    if (!replay_controls_path.empty() &&
        !lab::load_control_trace(replay_controls_path, replay_controls,
                                 &recorded_metadata)) {
        std::fprintf(stderr, "Invalid control trace: %s\n",
                     replay_controls_path.c_str());
        return 1;
    }
    bool bench_preset = bench_option.value_or(interactive && replay_controls_path.empty());
    if (interactive && !bench_option.has_value() && recorded_metadata.present) {
        // A trace recorded before the interactive defaults may use the raw scenario.
        auto raw_args = harness_args;
        if (std::find(raw_args.begin(), raw_args.end(), "--starter-ticks") == raw_args.end())
            raw_args.insert(raw_args.end(), {"--starter-ticks", "495000"});
        lab::ControlTraceMetadata raw;
        if (!trace_metadata(raw_args, raw)) return 1;
        bench_preset = raw.scenario_args != recorded_metadata.scenario_args;
    }
    if (bench_preset) {
        const auto has_option = [](const std::vector<std::string> &args,
                                   const char *option) {
            return std::find(args.begin(), args.end(), option) != args.end();
        };
        if (!has_option(harness_args, "--idle-contact-p43") &&
            !has_option(harness_args, "--idle-contact-p46"))
            harness_args.emplace_back("--idle-contact-p46");
        if (!has_option(harness_args, "--idle-bridge-p15-p16"))
            harness_args.emplace_back("--idle-bridge-p15-p16");
        if (!has_option(harness_args, "--tps-bench-profile"))
            harness_args.emplace_back("--tps-bench-profile");
        const std::array<std::pair<const char *, const char *>, 7> values{{
            {"--adc7-mv", "1232"},
            {"--coolant-c", "90"},
            {"--idle-min-stop-mrad", "5"},
            {"--idle-motor-speed-mm-s", "50"},
            // No-load hot idle of the calibrated plant (docs/SEVEL_PHYSICS_CALIBRATION.md
            // s.3): lambda 1.01, ~908 rpm, brake torque ~0 with accessories on. When a
            // scenario sets an external load (--load-nm, e.g. the 24 N.m of the live
            // tests) that load stands in for the accessories and needs 8 mm2
            // (tests/sevel_preset.py), so the leak is 8 and accessories stay off.
            {"--throttle-leak-mm2", has_option(harness_args, "--load-nm") ? "14" : "9"},
            // Candidate TDC reference. The manual gives 120 deg (no tolerance, edge not
            // stated); 117 deg is a FIT to the manual idle advance of 6 +-2 deg (5.7
            // measured), not a measurement: 115-119 deg fit equally.
            {"--tdc-reference-deg", "117"},
            {"--lambda-adc-gain", "5"},
        }};
        if (!has_option(harness_args, "--accessory-load") &&
            !has_option(harness_args, "--load-nm"))
            harness_args.emplace_back("--accessory-load"); // F-45: alternator + pump
        for (const auto &[option, value] : values) {
            if (!has_option(harness_args, option)) {
                harness_args.emplace_back(option);
                harness_args.emplace_back(value);
            }
        }
        std::printf("[LAB-BENCH] candidate warm bindings enabled\n");
    }
    if (std::find(harness_args.begin(), harness_args.end(),
                  "--starter-ticks") == harness_args.end()) {
        harness_args.emplace_back("--starter-ticks");
        harness_args.emplace_back("495000");
    }
    const auto stop_option =
        std::find(harness_args.begin(), harness_args.end(), "--stop-ticks");
    if (headless && !replay_controls_path.empty() &&
        stop_option != harness_args.end()) {
        long long stop_tick = 0;
        if (stop_option + 1 == harness_args.end() ||
            !parse_tick((stop_option + 1)->c_str(), stop_tick) ||
            stop_tick != capture.target_tick) {
            std::fprintf(stderr,
                         "Headless replay stop tick must equal capture tick\n");
            return 2;
        }
    }
    if (std::find(harness_args.begin(), harness_args.end(), "--stop-ticks") ==
        harness_args.end()) {
        harness_args.emplace_back("--stop-ticks");
        harness_args.push_back(
            std::to_string(live ? 1000000000000LL : capture.target_tick));
    }
    lab::ControlTraceMetadata current_metadata;
    if ((live || !save_controls_path.empty() || recorded_metadata.present) &&
        !trace_metadata(harness_args, current_metadata)) {
        std::fprintf(stderr, "Could not read ROM for control trace metadata\n");
        return 1;
    }
    if (recorded_metadata.present &&
        (recorded_metadata.rom_size != current_metadata.rom_size ||
         recorded_metadata.rom_hash != current_metadata.rom_hash ||
         recorded_metadata.scenario_args != current_metadata.scenario_args)) {
        std::fprintf(
            stderr,
            "Control trace ROM or physical scenario differs from replay\n");
        return 2;
    }
#ifdef SEVEL_LAB_SDL3
    if (live) {
        lab::SimSession session(std::move(harness_args), 65536,
                                screenshot_path.empty() ? 0
                                                        : capture.target_tick);
        ma17::EmulatorSnapshot initial;
        if (!auto_start) {
            initial.key_on = false;
            if (replay_controls_path.empty())
                session.set_key(false);
        }
        if (!replay_controls_path.empty()) {
            for (const auto &control : replay_controls)
                session.schedule_control(control);
        }
        session.start();
        const bool shown = lab::show_sdl_display(
            initial, window_frames, screenshot_path, &session,
            capture.target_tick, nullptr, !replay_controls_path.empty(),
            gpu_preview, enable_audio, frame_delay_ms.value_or(window_frames > 0 ? 16 : 0), bench_preset,
            &current_metadata, ui_scale_percent, cad_assets, cad_preset, cad_panel);
        session.stop();
        ma17::EmulatorSnapshot final_snapshot;
        if (!session.latest(final_snapshot))
            return 1;
        print_lab_state(final_snapshot, session.event_window(),
                        session.event_overflow());
        if (!save_controls_path.empty() &&
            !lab::save_control_trace(
                save_controls_path, session.control_history(),
                replay_controls_path.empty()
                    ? &current_metadata
                    : (recorded_metadata.present ? &recorded_metadata
                                                 : nullptr))) {
            std::fprintf(stderr, "Could not save control trace: %s\n",
                         save_controls_path.c_str());
            return 1;
        }
        if ((!svg_path.empty() || !wav_path.empty()) && shown) {
            if (!svg_path.empty()) {
                lab::RecordingRenderer final_renderer;
                lab::render_sevel_scene(final_renderer, final_snapshot, 1280.0f,
                                        720.0f);
                if (!final_renderer.save_svg(svg_path))
                    return 1;
            }
            if (!wav_path.empty()) {
                const auto pcm = lab::render_combustion_audio(
                    session.events(), final_snapshot.tick);
                if (pcm.empty() ||
                    !lab::save_mono_wav(wav_path, pcm, lab::audio_sample_rate))
                    return 1;
            }
        }
        return shown ? session.result() : 1;
    }
#endif
    if (headless && !replay_controls_path.empty()) {
        lab::SimSession session(std::move(harness_args));
        for (const auto &control : replay_controls)
            session.schedule_control(control);
        session.set_speed(16.0);
        session.start();
        while (!session.finished())
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        session.stop();
        ma17::EmulatorSnapshot final_snapshot;
        if (session.result() != 0 || !session.latest(final_snapshot) ||
            final_snapshot.tick < capture.target_tick)
            return 1;
        print_lab_state(final_snapshot, session.event_window(),
                        session.event_overflow());
        if (!svg_path.empty()) {
            lab::RecordingRenderer final_renderer;
            lab::render_sevel_scene(final_renderer, final_snapshot, 1280.0f,
                                    720.0f);
            if (!final_renderer.save_svg(svg_path))
                return 1;
        }
        if (!wav_path.empty()) {
            const auto pcm = lab::render_combustion_audio(session.events(),
                                                          final_snapshot.tick);
            if (pcm.empty() ||
                !lab::save_mono_wav(wav_path, pcm, lab::audio_sample_rate))
                return 1;
        }
        if (!save_controls_path.empty() &&
            !lab::save_control_trace(
                save_controls_path, session.control_history(),
                recorded_metadata.present ? &recorded_metadata : nullptr))
            return 1;
        std::printf("[LAB-REPLAY] tick=%lld controls=%zu events=%zu\n",
                    final_snapshot.tick, session.control_history().size(),
                    session.events().size());
        return 0;
    }
    std::vector<char *> harness_argv;
    harness_argv.reserve(harness_args.size());
    for (auto &arg : harness_args)
        harness_argv.push_back(arg.data());
    capture.events.reserve(65536);
    const int result =
        ma17::run_cli(static_cast<int>(harness_argv.size()),
                      harness_argv.data(), {on_snapshot, on_event, &capture});
    if (result != 0)
        return result;
    if (!capture.captured) {
        std::fprintf(stderr, "Capture tick %lld was not reached\n",
                     capture.target_tick);
        return 1;
    }
    lab::RecordingRenderer renderer;
    lab::render_sevel_scene(renderer, capture.snapshot, 1280.0f, 720.0f);
    if (!svg_path.empty() && !renderer.save_svg(svg_path)) {
        std::fprintf(stderr, "Could not write capture: %s\n", svg_path.c_str());
        return 1;
    }
    if (!wav_path.empty()) {
        const auto pcm =
            lab::render_combustion_audio(capture.events, capture.snapshot.tick);
        if (pcm.empty() ||
            !lab::save_mono_wav(wav_path, pcm, lab::audio_sample_rate)) {
            std::fprintf(stderr, "Could not write WAV capture: %s\n",
                         wav_path.c_str());
            return 1;
        }
        std::printf("[LAB-AUDIO] samples=%zu wav=%s\n", pcm.size(),
                    wav_path.c_str());
    }
#ifdef SEVEL_LAB_SDL3
    if (!headless &&
        !lab::show_sdl_display(capture.snapshot, window_frames, screenshot_path,
                               nullptr, 0, &capture.events, false, false, true,
                               16, bench_preset, nullptr, ui_scale_percent))
        return 1;
#endif
    std::printf("[LAB-CAPTURE] tick=%lld rpm=%.3f ram47=%u "
                "draw_calls=%d triangles=%zu events=%zu event_overflow=%llu "
                "svg=%s drawn_calls=%zu\n",
                capture.snapshot.tick, capture.snapshot.rpm,
                static_cast<unsigned>(capture.snapshot.ram47),
                renderer.draw_calls(), renderer.triangle_count(),
                capture.events.size(), capture.event_overflow, svg_path.c_str(),
                renderer.drawn_call_count());
    return 0;
}
