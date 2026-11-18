#include "lab/SdlDisplay.hpp"

#include "lab/AnalogTrigger.hpp"
#include "lab/DigitalScopeExport.hpp"
#include "lab/DonorScene.hpp"
#include "lab/DrivetrainExport.hpp"
#include "lab/FontRenderer.hpp"
#include "lab/LabButtons.hpp"
#include "lab/LabInstruments.hpp"
#include "lab/LabLayout.hpp"
#include "lab/LabUiPreferences.hpp"
#include "lab/LiveAudio.hpp"
#include "lab/MeshAsset.hpp"
#include "lab/PixelSnap.hpp"
#include "lab/RecordingRenderer.hpp"
#include "lab/SceneCameraFit.hpp"
#include "lab/SceneColor.hpp"
#include "lab/ScopeCursor.hpp"
#include "lab/SevelInstrumentProfile.hpp"
#include "lab/SevelTransmission.hpp"
#include "lab/SimSession.hpp"

#include "gauge.h"
#include "gear_card_layout.h"
#include "sdl_gpu_renderer.h"
#include "ui_button_style.h"

#include <SDL3/SDL.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iterator>
#include <limits>
#include <memory>
#include <string_view>
#include <vector>

#ifdef SEVEL_LAB_PNG
#include <png.h>
#endif

namespace {

int configured_ui_scale_percent = 0;

enum class TriggerMode { Off, Auto, Normal, Single };

struct ScopeTriggerMetadata {
    TriggerMode mode = TriggerMode::Off;
    lab::TriggerSlope slope = lab::TriggerSlope::Rising;
    std::size_t channel = 0;
    int event_source = -1;
    double level = 0.0;
    double pre_fraction = 0.25;
    long long tick = -1;
};

#ifdef SEVEL_LAB_PNG
bool embed_png_text(const std::filesystem::path &png_path, const char *keyword,
                    const std::string &text);
#endif
// Face identity of the running UI font, recorded in every saved PNG.
std::string g_font_identity;

bool save_frame(SDL_Surface *surface, const std::string &path) {
#ifdef SEVEL_LAB_PNG
    if (path.ends_with(".png")) {
        SDL_Surface *rgba = SDL_ConvertSurface(surface, SDL_PIXELFORMAT_RGBA32);
        if (!rgba)
            return false;
        png_image image{};
        image.version = PNG_IMAGE_VERSION;
        image.width = static_cast<png_uint_32>(rgba->w);
        image.height = static_cast<png_uint_32>(rgba->h);
        image.format = PNG_FORMAT_RGBA;
        const bool saved =
            png_image_write_to_file(&image, path.c_str(), 0, rgba->pixels,
                                    rgba->pitch, nullptr) != 0;
        png_image_free(&image);
        SDL_DestroySurface(rgba);
        if (saved && !g_font_identity.empty())
            embed_png_text(path, "SEVEL Font", g_font_identity);
        return saved;
    }
#endif
    if (path.ends_with(".png"))
        return false;
    return SDL_SaveBMP(surface, path.c_str());
}

#ifdef SEVEL_LAB_PNG
bool embed_png_text(const std::filesystem::path &png_path, const char *keyword,
                    const std::string &metadata) {
    if (metadata.empty())
        return false;
    std::ifstream input(png_path, std::ios::binary);
    const std::vector<unsigned char> png{std::istreambuf_iterator<char>(input),
                                         std::istreambuf_iterator<char>()};
    constexpr std::array<unsigned char, 8> signature{137, 80, 78, 71,
                                                     13,  10, 26, 10};
    if (png.size() < 33 ||
        !std::equal(signature.begin(), signature.end(), png.begin()) ||
        png[8] != 0 || png[9] != 0 || png[10] != 0 || png[11] != 13 ||
        png[12] != 'I' || png[13] != 'H' || png[14] != 'D' || png[15] != 'R')
        return false;
    std::vector<unsigned char> chunk{'t', 'E', 'X', 't'};
    chunk.insert(chunk.end(), keyword, keyword + std::strlen(keyword) + 1U);
    chunk.insert(chunk.end(), metadata.begin(), metadata.end());
    std::uint32_t crc = 0xffffffffU;
    for (const unsigned char byte : chunk) {
        crc ^= byte;
        for (int bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1U) ? 0xedb88320U : 0U);
    }
    std::vector<unsigned char> output;
    output.reserve(png.size() + chunk.size() + 8);
    output.insert(output.end(), png.begin(), png.begin() + 33);
    const auto chunk_size = static_cast<std::uint32_t>(chunk.size() - 4);
    for (int shift = 24; shift >= 0; shift -= 8)
        output.push_back(static_cast<unsigned char>(chunk_size >> shift));
    output.insert(output.end(), chunk.begin(), chunk.end());
    crc = ~crc;
    for (int shift = 24; shift >= 0; shift -= 8)
        output.push_back(static_cast<unsigned char>(crc >> shift));
    output.insert(output.end(), png.begin() + 33, png.end());
    std::filesystem::path temporary = png_path;
    temporary += ".tmp";
    std::ofstream file(temporary, std::ios::binary | std::ios::trunc);
    file.write(reinterpret_cast<const char *>(output.data()),
               static_cast<std::streamsize>(output.size()));
    file.close();
    if (!file) {
        std::error_code ignored;
        std::filesystem::remove(temporary, ignored);
        return false;
    }
    std::error_code error;
    std::filesystem::rename(temporary, png_path, error);
    const bool renamed = !error;
    if (!renamed) {
        std::error_code ignored;
        std::filesystem::remove(temporary, ignored);
    }
    return renamed;
}

bool embed_scope_png_metadata(const std::filesystem::path &png_path,
                              const std::filesystem::path &csv_path) {
    std::ifstream csv(csv_path);
    std::string metadata;
    for (std::string line; std::getline(csv, line) && line.starts_with('#');)
        metadata += line + '\n';
    return embed_png_text(png_path, "SEVEL Scope", metadata);
}
#endif

std::filesystem::path gpu_scene_path(std::filesystem::path path) {
    path.replace_filename(path.stem().string() + "-gpu" +
                          path.extension().string());
    return path;
}

// B.14: the same scene and viewport through the SDL_Renderer path (recorded
// triangles replayed with the donor blend) so it can be compared with the
// donor GPU capture of that scene.
bool save_sdl_scene_equivalent(const lab::RecordingRenderer &recorded,
                               int width, int height,
                               const std::filesystem::path &path) {
    SDL_Surface *surface =
        SDL_CreateSurface(width, height, SDL_PIXELFORMAT_RGBA32);
    if (!surface)
        return false;
    SDL_Renderer *renderer = SDL_CreateSoftwareRenderer(surface);
    if (!renderer) {
        SDL_DestroySurface(surface);
        return false;
    }
    const SDL_FColor clear = lab::scene_fcolor(recorded.clear_color());
    SDL_SetRenderDrawColorFloat(renderer, clear.r, clear.g, clear.b, 1.0f);
    SDL_RenderClear(renderer);
    SDL_SetRenderDrawBlendMode(renderer, lab::kSceneBlendMode);
    std::vector<SDL_Vertex> vertices;
    recorded.for_each_triangle([&](const auto &points, const ysVector &color) {
        for (const auto &point : points) {
            SDL_Vertex vertex{};
            vertex.position = {point.x, point.y};
            vertex.color = lab::scene_fcolor(color);
            vertices.push_back(vertex);
        }
    });
    bool ok = vertices.empty() ||
              SDL_RenderGeometry(renderer, nullptr, vertices.data(),
                                 static_cast<int>(vertices.size()), nullptr, 0);
    SDL_RenderPresent(renderer);
    ok = ok && save_frame(surface, path.string());
    SDL_DestroyRenderer(renderer);
    SDL_DestroySurface(surface);
    return ok;
}

void save_gpu_scene(SdlGpuRenderer &renderer,
                    const std::filesystem::path &main_path, long long tick) {
    const auto path = gpu_scene_path(main_path);
    std::vector<std::uint8_t> pixels;
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    std::string error;
    bool saved = false;
    if (renderer.captureSceneRgba(pixels, width, height, error) &&
        width <=
            static_cast<std::uint32_t>(std::numeric_limits<int>::max() / 4) &&
        height <= static_cast<std::uint32_t>(std::numeric_limits<int>::max())) {
        SDL_Surface *surface = SDL_CreateSurfaceFrom(
            static_cast<int>(width), static_cast<int>(height),
            SDL_PIXELFORMAT_RGBA32, pixels.data(), static_cast<int>(width * 4));
        saved = surface && save_frame(surface, path.string());
        if (surface)
            SDL_DestroySurface(surface);
    }
    if (saved)
        std::fprintf(stdout, "[LAB-GPU] scene_capture=%s tick=%lld\n",
                     path.string().c_str(), tick);
    else
        std::fprintf(stderr, "SDL GPU scene capture failed: %s\n",
                     error.empty() ? SDL_GetError() : error.c_str());
}

} // namespace

namespace lab {
namespace {

bool save_scope_csv(const std::filesystem::path &path,
                    const std::vector<ma17::EmulatorSnapshot> &history,
                    int group, long long first_tick, long long last_tick,
                    long long view_first_tick, long long view_last_tick,
                    const ControlTraceMetadata *metadata,
                    ScopeTriggerMetadata trigger, DisplayUnits display_units,
                    SimSession::SnapshotRetention retention) {
    const auto first =
        std::lower_bound(history.begin(), history.end(), first_tick,
                         [](const ma17::EmulatorSnapshot &sample,
                            long long tick) { return sample.tick < tick; });
    const auto last = std::upper_bound(
        first, history.end(), last_tick,
        [](long long tick, const ma17::EmulatorSnapshot &sample) {
            return tick < sample.tick;
        });
    if (first == last)
        return false;
    const bool has_drivetrain =
        std::any_of(first, last, [](const auto &sample) {
            return sample.drivetrain_available;
        });
    std::size_t gaps_over_250ms = 0;
    for (auto sample = std::next(first); sample != last; ++sample) {
        if (sample->tick - std::prev(sample)->tick > 247500LL)
            ++gaps_over_250ms;
    }
    std::ofstream out(path);
    if (!out)
        return false;
    out << std::setprecision(17);
    out << "# format=sevel-ma17-scope-v1\n"
        << "# vehicle=" << profile::vehicle << '\n'
        << "# engine=" << profile::engine << '\n'
        << "# ecu=" << profile::ecu << '\n'
        << "# group=" << group << '\n'
        << "# selection_first_tick=" << first_tick << '\n'
        << "# selection_last_tick=" << last_tick << '\n'
        << "# view_first_tick=" << view_first_tick << '\n'
        << "# view_last_tick=" << view_last_tick << '\n'
        << "# data_units=canonical_metric\n"
        << "# view_units="
        << (display_units == DisplayUnits::Metric ? "metric" : "imperial")
        << '\n'
        << "# clock_hz=990000\n"
        << "# first_tick=" << first->tick << '\n'
        << "# last_tick=" << std::prev(last)->tick << '\n'
        << "# retained_sample_count=" << std::distance(first, last) << '\n'
        << "# gaps_over_250ms=" << gaps_over_250ms << '\n'
        << "# raw_evicted_total=" << retention.raw_evicted << '\n'
        << "# archive_evicted_total=" << retention.archive_evicted << '\n'
        << "# sample_policy=retained_snapshots_and_archive_extrema\n";
    constexpr std::array<const char *, 4> modes{"off", "auto", "normal",
                                                "single"};
    out << "# trigger_mode=" << modes[static_cast<std::size_t>(trigger.mode)]
        << '\n';
    if (trigger.mode != TriggerMode::Off) {
        if (trigger.event_source >= 0) {
            constexpr std::array<const char *, 5> sources{
                "ignition_pin_0", "ignition_pin_1", "injector_pin",
                "spark_pair_1_4", "spark_pair_2_3"};
            out << "# trigger_channel="
                << sources[static_cast<std::size_t>(trigger.event_source)]
                << '\n';
        } else {
            const auto &channel =
                analog_scope_instrument(group, trigger.channel);
            out << "# trigger_channel=" << channel.id << '\n'
                << "# trigger_level=" << trigger.level << '\n';
        }
        if (trigger.event_source < 3)
            out << "# trigger_slope="
                << (trigger.slope == TriggerSlope::Rising ? "rising"
                                                          : "falling")
                << '\n';
        out << "# trigger_pre_fraction=" << trigger.pre_fraction << '\n'
            << "# trigger_tick=" << trigger.tick << '\n';
    }
    if (metadata && metadata->present) {
        out << "# rom_size=" << metadata->rom_size << '\n'
            << "# rom_fnv64=" << std::hex << metadata->rom_hash << std::dec
            << '\n';
        for (std::size_t index = 0; index < metadata->scenario_args.size();
             ++index) {
            std::string arg = metadata->scenario_args[index];
            std::replace_if(
                arg.begin(), arg.end(),
                [](char c) { return c == '\r' || c == '\n'; }, ' ');
            out << "# scenario_arg_" << index << '=' << std::quoted(arg)
                << '\n';
        }
    }
    for (std::size_t signal = 0; signal < analog_scope_signal_count(group);
         ++signal) {
        const auto &spec = analog_scope_instrument(group, signal);
        out << "# channel_" << signal << '=' << spec.id << '|' << spec.title
            << '|' << spec.unit << '|' << spec.source << '\n';
    }
    if (group == 2)
        out << "# channel_3=fan_on_sampled|FAN SAMPLED|state|physical thermal "
               "model\n";
    if (group >= 6 && group <= 9)
        out << "# rom_iram_60_67=raw ECU lower RAM; byte interpretation "
               "unverified\n";
    out << "tick,time_s";
    for (std::size_t signal = 0; signal < analog_scope_signal_count(group);
         ++signal) {
        const auto &spec = analog_scope_instrument(group, signal);
        out << ',' << spec.id << '_' << spec.unit;
    }
    if (group == 2)
        out << ",fan_on_sampled";
    if (group >= 6 && group <= 9) {
        for (std::size_t signal = group == 9 ? 1U : 0U; signal < 2; ++signal) {
            const int channel = adc_scope_channel(group, signal);
            out << ",adc" << channel << "_count,adc" << channel
                << "_conversion_tick,adc" << channel << "_age_ms";
        }
        for (std::size_t index = 0; index < 8; ++index)
            out << ",rom_iram_" << std::hex << (0x60 + index) << std::dec
                << "_u8";
    }
    if (has_drivetrain)
        write_drivetrain_csv_header(out);
    out << '\n';
    for (auto sample = first; sample != last; ++sample) {
        out << sample->tick << ','
            << static_cast<double>(sample->tick) / 990000.0;
        for (std::size_t signal = 0; signal < analog_scope_signal_count(group);
             ++signal) {
            out << ',';
            if (const auto value = analog_scope_value(*sample, group, signal))
                out << *value;
        }
        if (group == 2) {
            out << ',';
            if (sample->thermal_available)
                out << (sample->radiator_fan_on ? 1 : 0);
        }
        if (group >= 6 && group <= 9) {
            for (std::size_t signal = group == 9 ? 1U : 0U; signal < 2;
                 ++signal) {
                const auto channel =
                    static_cast<std::size_t>(adc_scope_channel(group, signal));
                const auto &adc = sample->adc_last_conversion[channel];
                out << ',';
                if (adc.sampled) {
                    out << adc.count << ',' << adc.tick << ','
                        << static_cast<double>(
                               sample->tick -
                               static_cast<long long>(adc.tick)) /
                               990.0;
                } else {
                    out << ",,";
                }
            }
            for (const uint8_t value : sample->rom_iram_60_67)
                out << ',' << static_cast<unsigned>(value);
        }
        if (has_drivetrain)
            write_drivetrain_csv_row(out, *sample);
        out << '\n';
    }
    return out.good();
}

bool save_digital_scope_csv(const std::filesystem::path &path,
                            const std::vector<ma17::EmulatorEvent> &events,
                            const std::vector<ma17::EmulatorSnapshot> &history,
                            long long first_tick, long long last_tick,
                            long long view_first_tick, long long view_last_tick,
                            const ControlTraceMetadata *metadata,
                            unsigned long long event_overflow,
                            std::size_t event_base_index,
                            const std::array<bool, 4> &channels_visible) {
    const auto rows =
        selected_digital_records(events, history, first_tick, last_tick);
    if (rows.empty())
        return false;
    std::ofstream out(path);
    if (!out)
        return false;
    out << std::setprecision(17);
    out << "# format=sevel-ma17-digital-scope-v1\n"
        << "# vehicle=" << profile::vehicle << '\n'
        << "# engine=" << profile::engine << '\n'
        << "# ecu=" << profile::ecu << '\n'
        << "# selection_first_tick=" << first_tick << '\n'
        << "# selection_last_tick=" << last_tick << '\n'
        << "# view_first_tick=" << view_first_tick << '\n'
        << "# view_last_tick=" << view_last_tick << '\n'
        << "# clock_hz=990000\n"
        << "# first_tick=" << rows.front().tick << '\n'
        << "# last_tick=" << rows.back().tick << '\n'
        << "# retained_record_count=" << rows.size() << '\n'
        << "# event_overflow_total=" << event_overflow << '\n'
        << "# event_base_index=" << event_base_index << '\n'
        << "# visible_channel_mask=";
    for (const bool visible : channels_visible)
        out << (visible ? '1' : '0');
    out << '\n'
        << "# exported_channels=all_retained_digital_sources\n"
        << "# sample_policy=retained_events_and_contact_transitions\n"
        << "# contact_transition_tick=first_valid_snapshot_observing_change\n"
        << "# channel_0=cc3|CC3|high_low|ECU injector output event\n"
        << "# channel_1=p5_0|P5.0|high_low|ECU ignition output event\n"
        << "# channel_2=p5_1|P5.1|high_low|ECU ignition output event\n"
        << "# channel_3=idle_switch|IDLE SW SAMP|open_closed|physical throttle "
           "contact snapshot\n";
    if (metadata && metadata->present) {
        out << "# rom_size=" << metadata->rom_size << '\n'
            << "# rom_fnv64=" << std::hex << metadata->rom_hash << std::dec
            << '\n';
        for (std::size_t index = 0; index < metadata->scenario_args.size();
             ++index) {
            std::string arg = metadata->scenario_args[index];
            std::replace_if(
                arg.begin(), arg.end(),
                [](char c) { return c == '\r' || c == '\n'; }, ' ');
            out << "# scenario_arg_" << index << '=' << std::quoted(arg)
                << '\n';
        }
    }
    out << "tick,time_s,kind,channel,state,source\n";
    for (const auto &row : rows) {
        out << row.tick << ',' << static_cast<double>(row.tick) / 990000.0;
        if (!row.event) {
            out << ",idle_contact_sample,idle_switch,"
                << (row.contact_closed ? "closed" : "open")
                << ",physical throttle contact snapshot\n";
            continue;
        }
        const auto &event = *row.event;
        switch (event.type) {
        case ma17::EmulatorEventType::InjectorPin:
            out << ",injector_pin,cc3," << (event.high ? "high" : "low")
                << ",ECU injector output event";
            break;
        case ma17::EmulatorEventType::IgnitionPin:
            out << ",ignition_pin," << (event.channel == 0 ? "p5_0" : "p5_1")
                << ',' << (event.high ? "high" : "low")
                << ",ECU ignition output event";
            break;
        case ma17::EmulatorEventType::Spark:
            out << ",spark,"
                << (event.pair_index == 0 ? "pair_1_4" : "pair_2_3")
                << ",,ignition stage event";
            break;
        case ma17::EmulatorEventType::Combustion:
        case ma17::EmulatorEventType::Misfire:
            out << (event.type == ma17::EmulatorEventType::Misfire
                        ? ",misfire,cyl_"
                        : ",combustion,cyl_")
                << event.cylinder_index + 1 << ",,physical combustion event";
            break;
        case ma17::EmulatorEventType::LampCandidate:
            continue;
        }
        out << '\n';
    }
    return out.good();
}

void draw_shaft_mechanical_details(SDL_Renderer *screen,
                                   const ma17::EmulatorSnapshot &snapshot,
                                   SceneCamera camera, float scene_width,
                                   float scene_height, float ui_scale) {
    if (scene_width <= 0.0f || scene_height <= 0.0f)
        return;
    const SceneDimensions dimensions{};
    const float pitch =
        static_cast<float>(dimensions.visual_estimate_cylinder_pitch_m);
    const ysMatrix projection = scene_fit_projection(
        camera, scene_width, scene_height, 3.4f * pitch + 0.08f, 0.34f);
    const auto project = [&](float wx, float wy) -> SDL_FPoint {
        const float cx = projection.m[0][0] * wx + projection.m[0][3];
        const float cy = projection.m[1][1] * wy + projection.m[1][3];
        return {(cx + 1.0f) * scene_width * 0.5f,
                (1.0f - cy) * scene_height * 0.5f};
    };

    const SevelVisualGeometry geometry{};
    constexpr float bore_m = 0.0864f;
    const float head_y =
        static_cast<float>(geometry.visual_estimate_rod_length_m +
                           SevelVisualGeometry::crank_radius_m +
                           dimensions.visual_estimate_head_height_m);
    const float cam_y = head_y + 0.042f;
    constexpr float crank_r =
        static_cast<float>(SevelVisualGeometry::crank_radius_m);
    const float crank_base_angle =
        static_cast<float>(snapshot.crank_angle_rad - snapshot.tdc_phase_rad);
    const auto poses = sevel_cylinder_poses(
        snapshot.crank_angle_rad - snapshot.tdc_phase_rad, geometry);
    constexpr float pi = 3.14159265f;

    // 1. Stylized intake (electric cyan) & exhaust (electric magenta) runners
    for (int cylinder = 0; cylinder < 4; ++cylinder) {
        const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
        const SDL_FPoint in_port = project(center - 0.021f, cam_y + 0.008f);
        const SDL_FPoint in_sweep = project(center - 0.038f, cam_y + 0.030f);
        const SDL_FPoint ex_port = project(center + 0.021f, cam_y + 0.008f);
        const SDL_FPoint ex_sweep = project(center + 0.038f, cam_y + 0.030f);

        SDL_SetRenderDrawColor(screen, 0, 229, 255, 180);
        SDL_RenderLine(screen, in_port.x, in_port.y, in_sweep.x, in_sweep.y);
        SDL_RenderLine(screen, in_port.x + 1.0f, in_port.y, in_sweep.x + 1.0f,
                       in_sweep.y);

        SDL_SetRenderDrawColor(screen, 255, 64, 129, 180);
        SDL_RenderLine(screen, ex_port.x, ex_port.y, ex_sweep.x, ex_sweep.y);
        SDL_RenderLine(screen, ex_port.x + 1.0f, ex_port.y, ex_sweep.x + 1.0f,
                       ex_sweep.y);
    }

    // 2. Dynamic valve springs (compressing/expanding with cam lift)
    for (int cylinder = 0; cylinder < 4; ++cylinder) {
        const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
        for (int valve = 0; valve < 2; ++valve) {
            const auto kind =
                valve == 0 ? ValveKind::Intake : ValveKind::Exhaust;
            const float x = center + (valve == 0 ? -0.021f : 0.021f);
            const float lift = static_cast<float>(
                valve_lift_fraction(snapshot.crank_angle_rad,
                                    static_cast<std::size_t>(cylinder), kind,
                                    snapshot.tdc_phase_rad) *
                dimensions.visual_estimate_valve_lift_m);
            const float top_y = head_y + 0.027f;
            const float bot_y = head_y + 0.007f - lift * 0.4f;
            const SDL_FPoint p_top = project(x, top_y);
            const SDL_FPoint p_bot = project(x, bot_y);

            const float spring_h = p_bot.y - p_top.y;
            constexpr int coils = 5;
            const float coil_w = 4.0f * ui_scale;

            SDL_SetRenderDrawColor(screen, 160, 175, 190, 220);
            SDL_FPoint prev = {p_top.x, p_top.y};
            for (int c = 1; c <= coils; ++c) {
                const float frac =
                    static_cast<float>(c) / static_cast<float>(coils);
                const float cy = p_top.y + spring_h * frac;
                const float cx = p_top.x + ((c % 2 == 1) ? coil_w : -coil_w);
                SDL_RenderLine(screen, prev.x, prev.y, cx, cy);
                prev = {cx, cy};
            }
            SDL_RenderLine(screen, prev.x, prev.y, p_bot.x, p_bot.y);
        }
    }

    // 3. Articulated kinematics, counterweights, and piston details
    for (int cylinder = 0; cylinder < 4; ++cylinder) {
        const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
        const auto &pose = poses[static_cast<std::size_t>(cylinder)];
        const float cyl_phase = (cylinder == 0 || cylinder == 3)
                                    ? crank_base_angle
                                    : crank_base_angle + pi;

        const float crank_y = crank_r * std::cos(cyl_phase);
        const float throw_x = crank_r * std::sin(cyl_phase) * 0.35f;
        const float piston_y = static_cast<float>(pose.piston_pin_y_m);

        const SDL_FPoint p_crank = project(center + throw_x, crank_y);
        const SDL_FPoint p_wrist = project(center, piston_y);
        const SDL_FPoint p_main = project(center, 0.0f);

        const float counter_y = -crank_r * std::cos(cyl_phase) * 0.85f;
        const float counter_x = -crank_r * std::sin(cyl_phase) * 0.30f;
        const SDL_FPoint p_counter = project(center + counter_x, counter_y);

        // Counterweight web
        SDL_SetRenderDrawColor(screen, 85, 95, 110, 255);
        const float cw_thick = 3.5f * ui_scale;
        SDL_RenderLine(screen, p_main.x - cw_thick, p_main.y,
                       p_counter.x - cw_thick, p_counter.y);
        SDL_RenderLine(screen, p_main.x, p_main.y, p_counter.x, p_counter.y);
        SDL_RenderLine(screen, p_main.x + cw_thick, p_main.y,
                       p_counter.x + cw_thick, p_counter.y);

        // Connecting rod articulated beam
        SDL_SetRenderDrawColor(screen, 215, 225, 235, 255);
        SDL_RenderLine(screen, p_crank.x - 1.0f, p_crank.y, p_wrist.x - 1.0f,
                       p_wrist.y);
        SDL_RenderLine(screen, p_crank.x, p_crank.y, p_wrist.x, p_wrist.y);
        SDL_RenderLine(screen, p_crank.x + 1.0f, p_crank.y, p_wrist.x + 1.0f,
                       p_wrist.y);

        // Big-end journal cap
        SDL_SetRenderDrawColor(screen, 240, 245, 250, 255);
        const float r_big = 3.5f * ui_scale;
        const SDL_FRect big_journal{p_crank.x - r_big, p_crank.y - r_big,
                                    r_big * 2.0f, r_big * 2.0f};
        SDL_RenderFillRect(screen, &big_journal);

        // Piston details: wrist pin & dual compression rings
        const SDL_FPoint p_crown = project(center, piston_y + 0.010f);
        const float bore_px = project(center + bore_m * 0.38f, piston_y).x -
                              project(center - bore_m * 0.38f, piston_y).x;

        SDL_SetRenderDrawColor(screen, 38, 40, 48, 255);
        const float ring_w = bore_px * 0.90f;
        SDL_RenderLine(screen, p_crown.x - ring_w * 0.5f,
                       p_crown.y + 2.0f * ui_scale, p_crown.x + ring_w * 0.5f,
                       p_crown.y + 2.0f * ui_scale);
        SDL_RenderLine(screen, p_crown.x - ring_w * 0.5f,
                       p_crown.y + 5.0f * ui_scale, p_crown.x + ring_w * 0.5f,
                       p_crown.y + 5.0f * ui_scale);

        // Wrist pin hole
        const float r_pin = 2.5f * ui_scale;
        const SDL_FRect pin_rect{p_wrist.x - r_pin, p_wrist.y - r_pin,
                                 r_pin * 2.0f, r_pin * 2.0f};
        SDL_SetRenderDrawColor(screen, 28, 30, 36, 255);
        SDL_RenderFillRect(screen, &pin_rect);
        SDL_SetRenderDrawColor(screen, 180, 195, 210, 255);
        SDL_RenderRect(screen, &pin_rect);
    }
}

void draw_combustion_order(SDL_Renderer *screen, FontRenderer &font,
                           float left_width, int height, float ui_scale,
                           const std::array<ScenePulse, 4> &pulses,
                           const std::array<float, 2> &spark_glows,
                           const std::array<int, 2> &spark_channels,
                           int focus_cylinder) {
    if (left_width < 400.0f || height < 900)
        return;
    const SDL_FRect panel{
        16.0f, static_cast<float>(height) - 270.0f - 47.0f * ui_scale,
        left_width - 32.0f, 47.0f * ui_scale};
    SDL_SetRenderDrawColor(screen, 20, 20, 24, 255);
    SDL_RenderFillRect(screen, &panel);
    SDL_SetRenderDrawColor(screen, 42, 42, 50, 255);
    SDL_RenderRect(screen, &panel);
    font.draw(screen, panel.x + 9.0f * ui_scale, panel.y + 8.0f * ui_scale,
              "BURNS 1 > 3 > 4 > 2", {235, 241, 246, 255}, 0.75f * ui_scale);
    char spark_label[96];
    std::snprintf(spark_label, sizeof(spark_label), "P5.%c 1/4  P5.%c 2/3 ?",
                  spark_channels[0] < 0 ? '?' : '0' + spark_channels[0],
                  spark_channels[1] < 0 ? '?' : '0' + spark_channels[1]);
    font.draw(screen, panel.x + 9.0f * ui_scale, panel.y + 27.0f * ui_scale,
              spark_label, {145, 177, 190, 255}, 0.75f * ui_scale);
    constexpr std::array<unsigned, 4> firing_order{0, 2, 3, 1};
    constexpr std::size_t edges = 24;
    constexpr float tau = 6.28318530718f;
    for (std::size_t order = 0; order < firing_order.size(); ++order) {
        const auto cylinder = firing_order[order];
        const float spark_glow =
            spark_glows[cylinder == 0 || cylinder == 3 ? 0 : 1];
        const float x =
            left_width * (0.585f + 0.098f * static_cast<float>(order));
        const float y = panel.y + 23.0f * ui_scale;
        const float glow = std::clamp(pulses[cylinder].strength, 0.0f, 1.0f);
        const SDL_FColor hot = pulses[cylinder].misfire
                                   ? SDL_FColor{0.95f, 0.24f, 0.22f, 1.0f}
                                   : SDL_FColor{0.98f, 0.74f, 0.38f, 1.0f};
        const SDL_FColor color{(24.0f / 255.0f) * (1.0f - glow) + hot.r * glow,
                               (36.0f / 255.0f) * (1.0f - glow) + hot.g * glow,
                               (49.0f / 255.0f) * (1.0f - glow) + hot.b * glow,
                               1.0f};
        std::array<SDL_Vertex, edges * 3> fill{};
        std::array<SDL_FPoint, edges + 1> outline{};
        for (std::size_t edge = 0; edge < edges; ++edge) {
            const float angle =
                tau * static_cast<float>(edge) / static_cast<float>(edges);
            const float next_angle =
                tau * static_cast<float>(edge + 1) / static_cast<float>(edges);
            const auto point = [x, y, ui_scale](float a) {
                return SDL_FPoint{x + 11.0f * ui_scale * std::cos(a),
                                  y + 11.0f * ui_scale * std::sin(a)};
            };
            fill[edge * 3] = {{x, y}, color, {0.0f, 0.0f}};
            fill[edge * 3 + 1] = {point(angle), color, {0.0f, 0.0f}};
            fill[edge * 3 + 2] = {point(next_angle), color, {0.0f, 0.0f}};
            outline[edge] = point(angle);
        }
        outline[edges] = outline[0];
        if (glow > 0.0f)
            SDL_RenderGeometry(screen, nullptr, fill.data(), fill.size(),
                               nullptr, 0);
        SDL_SetRenderDrawColor(
            screen, 90, static_cast<Uint8>(128.0f + 93.0f * spark_glow),
            static_cast<Uint8>(142.0f + 101.0f * spark_glow), 255);
        SDL_RenderLines(screen, outline.data(), outline.size());
        if (focus_cylinder == static_cast<int>(cylinder + 1)) {
            std::array<SDL_FPoint, edges + 1> focus_outline{};
            for (std::size_t edge = 0; edge <= edges; ++edge) {
                const float angle =
                    tau * static_cast<float>(edge) / static_cast<float>(edges);
                focus_outline[edge] = {x + 15.0f * ui_scale * std::cos(angle),
                                       y + 15.0f * ui_scale * std::sin(angle)};
            }
            SDL_SetRenderDrawColor(screen, 184, 210, 140, 255);
            SDL_RenderLines(screen, focus_outline.data(), focus_outline.size());
        }
        const std::string numeral = std::to_string(cylinder + 1);
        font.draw(screen, x - font.measure(numeral) * ui_scale * 0.5f,
                  y - 5.0f * ui_scale, numeral, {235, 241, 246, 255}, ui_scale);
    }
}

float lab_ui_scale(int width, int height) {
    if (configured_ui_scale_percent != 0)
        return 1.0f;
    return std::clamp(std::min(static_cast<float>(width) / 1280.0f,
                               static_cast<float>(height) / 720.0f),
                      1.0f, 2.0f);
}

// Layout at an integer output size; the saved state is owned by the caller.
static LabLayout layout_for(const LayoutState &state, int width, int height,
                            bool scope_maximized = false) {
    return LabLayout::compute(state, static_cast<float>(width),
                              static_cast<float>(height), scope_maximized);
}

SDL_FRect instrument_cluster_rect(const LayoutState &layout_state, int width,
                                  int height) {
    const LabLayout layout = layout_for(layout_state, width, height);
    const float scale = lab_ui_scale(width, height);
    return {layout.instruments.x, 8.0f * scale,
            layout.instruments.w - 8.0f * scale,
            static_cast<float>(height) - 16.0f * scale};
}

SDL_FRect view_selector_rect(const LayoutState &layout_state, int width,
                             int height) {
    if (width < 1280 || height < 720) {
        const SDL_FRect mechanical =
            layout_for(layout_state, width, height).mechanical;
        return {mechanical.x + mechanical.w - 116.0f, 64.0f, 52.0f, 27.0f};
    }
    const float scale = lab_ui_scale(width, height);
    const SDL_FRect mechanical =
        layout_for(layout_state, width, height).mechanical;
    const float right = mechanical.x + mechanical.w - 15.0f * scale;
    return {right - (122.0f + 8.0f + 80.0f) * scale,
            height < 900 ? 64.0f : 82.0f, 122.0f * scale, 30.0f * scale};
}

SDL_FRect fit_button_rect(const LayoutState &layout_state, int width,
                          int height) {
    const SDL_FRect selector = view_selector_rect(layout_state, width, height);
    if (width < 1280 || height < 720)
        return {selector.x + 58.0f, selector.y, 42.0f, selector.h};
    const float scale = lab_ui_scale(width, height);
    return {selector.x - 78.0f * scale, selector.y, 70.0f * scale, selector.h};
}

SDL_FRect fullscreen_button_rect(const LayoutState &layout_state, int width,
                                 int height) {
    const SDL_FRect selector = view_selector_rect(layout_state, width, height);
    const float scale = lab_ui_scale(width, height);
    return {selector.x + selector.w + 8.0f * scale, selector.y, 80.0f * scale,
            selector.h};
}

SDL_FRect pedal_slider_rect(const LayoutState &layout_state, int width,
                            int height);
SDL_FRect volume_slider_rect(const LayoutState &layout_state, int width,
                             int height);

// OES LoadSimulationCluster::drawCurrentGear uses title/up/body/down bands.
SDL_FRect gear_widget_rect(const LayoutState &layout_state, int width,
                           int height) {
    if (width < 900 && height < 620 && lab_buttons_visible(width, height)) {
        const auto mute = lab_button_rect(8, width, height);
        const float x = mute.x + mute.width + 6.0f;
        return {x, mute.y,
                layout_for(layout_state, width, height).mechanical.w - x - 8.0f,
                mute.height};
    }
    if (width >= 900 && width < 1100 && lab_buttons_visible(width, height)) {
        const SDL_FRect volume =
            volume_slider_rect(layout_state, width, height);
        const SDL_FRect pedal = pedal_slider_rect(layout_state, width, height);
        const float x = volume.x + volume.w + 6.0f;
        return {x, volume.y, pedal.x - x - 6.0f, std::min(volume.h, pedal.h)};
    }
    if (width < 1100 || height < 700)
        return {};
    const float scale = lab_ui_scale(width, height);
    const float top = 410.0f * scale + 8.0f;
    const float bottom = static_cast<float>(height) - 340.0f;
    const float panel_w = layout_for(layout_state, width, height).left.w;
    if (width >= 1800 && height >= 1000 && bottom - top >= 64.0f) {
        // OES desktop 2048x816: each load-cluster cell is W/9 by H/6.
        constexpr float donor_aspect = (2048.0f / 9.0f) / (816.0f / 6.0f);
        const float gap = 8.0f * scale;
        const float cell_w = std::min((panel_w - 32.0f * scale - gap) * 0.5f,
                                      (bottom - top) * donor_aspect);
        return {panel_w * 0.5f + gap * 0.5f, top, cell_w,
                cell_w / donor_aspect};
    }
    const float card_w = std::min(90.0f * scale, panel_w - 32.0f);
    if (bottom - top >= 64.0f)
        return {(panel_w - card_w) * 0.5f, top, card_w, bottom - top};
    // Keep the donor gear control below the volume bar on shorter desktops.
    return {(panel_w - card_w) * 0.5f, static_cast<float>(height) - 92.0f,
            card_w, 84.0f};
}

SDL_FRect gear_widget_inner_rect(const SDL_FRect &box, float scale) {
    const float inset = std::min({10.0f * scale, box.w * 0.12f, box.h * 0.12f});
    return {box.x + inset, box.y + inset, box.w - 2.0f * inset,
            box.h - 2.0f * inset};
}

GearCardLayout gear_widget_layout(const SDL_FRect &box, float scale) {
    const SDL_FRect inner = gear_widget_inner_rect(box, scale);
    return gear_card_layout(Bounds(0.0f, box.w, 0.0f, box.h), inner.x - box.x);
}

int gear_widget_step(const LayoutState &layout_state, float x, float y,
                     int width, int height) {
    const SDL_FRect box = gear_widget_rect(layout_state, width, height);
    if (box.w <= 0.0f)
        return 0;
    const SDL_FRect inner =
        gear_widget_inner_rect(box, lab_ui_scale(width, height));
    if (x < inner.x || x >= inner.x + inner.w || y < inner.y ||
        y >= inner.y + inner.h)
        return 0;
    if (width < 1100)
        return x < inner.x + inner.w * 0.25f    ? -1
               : x >= inner.x + inner.w * 0.75f ? 1
                                                : 0;
    const GearCardLayout layout =
        gear_widget_layout(box, lab_ui_scale(width, height));
    const Point donor_point(x - box.x, box.h - (y - box.y));
    if (layout.up.overlaps(donor_point))
        return 1;
    return layout.down.overlaps(donor_point) ? -1 : 0;
}

void draw_gear_widget(const LayoutState &layout_state, SDL_Renderer *screen,
                      FontRenderer &font, int width, int height,
                      int selected_gear, bool physical) {
    const SDL_FRect box = gear_widget_rect(layout_state, width, height);
    if (box.w <= 0.0f)
        return;
    const float scale = lab_ui_scale(width, height);
    SDL_SetRenderDrawColor(screen, 14, 14, 18, 255);
    SDL_RenderFillRect(screen, &box);
    SDL_SetRenderDrawColor(screen, 150, 157, 163, 255);
    SDL_RenderRect(screen, &box);
    const SDL_FRect inner = gear_widget_inner_rect(box, scale);
    char digit[2]{selected_gear == -1  ? 'R'
                  : selected_gear == 0 ? 'N'
                                       : static_cast<char>('0' + selected_gear),
                  '\0'};
    if (width < 1100) {
        char label[16];
        std::snprintf(label, sizeof(label),
                      box.w < 120.0f ? "%s %s" : "GEAR %s %s", digit,
                      physical ? "" : "REF");
        const float text_scale = 0.68f * scale;
        font.draw(screen,
                  inner.x + (inner.w - font.measure(label) * text_scale) * 0.5f,
                  inner.y + (inner.h - 14.0f * text_scale) * 0.5f, label,
                  {235, 241, 246, 255}, text_scale);
        SDL_SetRenderDrawColor(screen, 235, 241, 246, 255);
        const float cy = inner.y + inner.h * 0.5f;
        const float arrow = std::min(4.0f * scale, inner.h * 0.22f);
        for (const bool up : {false, true}) {
            const float cx = inner.x + inner.w * (up ? 0.88f : 0.12f);
            const float tip = cx + (up ? arrow : -arrow);
            const float base = cx + (up ? -arrow : arrow);
            SDL_RenderLine(screen, base, cy - arrow, tip, cy);
            SDL_RenderLine(screen, tip, cy, base, cy + arrow);
        }
        return;
    }
    const GearCardLayout layout = gear_widget_layout(box, scale);
    const auto band_center_y = [&](const Bounds &band) {
        return box.y + box.h - band.center_v();
    };
    const auto centered = [&](const char *label, float center_y,
                              float text_scale) {
        font.draw(screen,
                  inner.x + (inner.w - font.measure(label) * text_scale) * 0.5f,
                  center_y - 7.0f * text_scale, label, {235, 241, 246, 255},
                  text_scale);
    };
    const float title_scale =
        std::min({24.0f / 14.0f * scale, inner.h * 0.14f * 0.8f / 14.0f,
                  inner.w / std::max(1.0f, font.measure("GEAR"))});
    const float digit_scale =
        std::min({64.0f / 14.0f * scale, inner.h * 0.40f * 0.8f / 14.0f,
                  inner.w / std::max(1.0f, font.measure(digit))});
    centered("GEAR", band_center_y(layout.title), title_scale);
    centered(digit, band_center_y(layout.body), digit_scale);
    const float cx = inner.x + inner.w * 0.5f;
    SDL_SetRenderDrawColor(screen, 235, 241, 246, 255);
    for (const bool up : {true, false}) {
        const Bounds &band = up ? layout.up : layout.down;
        const float size = gear_chevron_half_width(band);
        const float cy = band_center_y(band);
        const float tip = cy + (up ? -size * 0.65f : size * 0.65f);
        const float base = cy + (up ? size * 0.65f : -size * 0.65f);
        for (int stroke = -1; stroke <= 1; ++stroke) {
            const float offset = static_cast<float>(stroke) * scale;
            SDL_RenderLine(screen, cx - size + offset, base, cx + offset, tip);
            SDL_RenderLine(screen, cx + offset, tip, cx + size + offset, base);
        }
    }
}

void draw_gear_tooltip(const LayoutState &layout_state, SDL_Renderer *screen,
                       FontRenderer &font, int width, int height,
                       int selected_gear, double engine_rpm,
                       bool crank_available, bool physical) {
    const SDL_FRect gear = gear_widget_rect(layout_state, width, height);
    if (gear.w <= 0.0f)
        return;
    float window_x = 0.0f, window_y = 0.0f;
    SDL_GetMouseState(&window_x, &window_y);
    float x = 0.0f, y = 0.0f;
    if (!SDL_RenderCoordinatesFromWindow(screen, window_x, window_y, &x, &y) ||
        x < gear.x || x >= gear.x + gear.w || y < gear.y ||
        y >= gear.y + gear.h)
        return;
    char ratio[80];
    if (selected_gear == -1)
        std::snprintf(ratio, sizeof(ratio), "GEAR R | TOTAL %.3f",
                      lab::transmission::overall_ratio(-1));
    else if (selected_gear <= 0 ||
             selected_gear >=
                 static_cast<int>(lab::transmission::gear_ratios.size()))
        std::snprintf(ratio, sizeof(ratio), "GEAR N | NEUTRAL");
    else
        std::snprintf(ratio, sizeof(ratio), "GEAR %d | %.3f x %.4f = %.3f",
                      selected_gear,
                      lab::transmission::gear_ratios[static_cast<std::size_t>(
                          selected_gear)],
                      lab::transmission::final_drive_ratio,
                      lab::transmission::overall_ratio(selected_gear));
    char wheel[80];
    const auto ideal_wheel =
        crank_available
            ? lab::transmission::wheel_rpm(engine_rpm, selected_gear)
            : std::nullopt;
    const auto ideal_speed =
        crank_available ? lab::transmission::ideal_speed_kmh(
                              engine_rpm, selected_gear,
                              lab::transmission::reference_tire_radius_m)
                        : std::nullopt;
    if (selected_gear == 0)
        std::snprintf(wheel, sizeof(wheel), "IDEAL WHEEL: N/D IN NEUTRAL");
    else if (!ideal_wheel || !ideal_speed)
        std::snprintf(wheel, sizeof(wheel),
                      "IDEAL WHEEL: -- (ENGINE RPM MISSING)");
    else
        std::snprintf(wheel, sizeof(wheel), "IDEAL: %.1f W-RPM | %.1f KM/H",
                      *ideal_wheel, *ideal_speed);
    constexpr const char *source = "FIAT RATIOS | EST. TIRE R=0.29 M";
    const char *limit =
        physical             ? "ROAD: PHYSICS | IDEAL ASSUMES NO CLUTCH SLIP"
        : selected_gear == 0 ? "NO DRIVE IN NEUTRAL | ROAD: SCENARIO"
                             : "CLUTCH ASSUMED ENGAGED | ROAD: SCENARIO";
    const float scale = lab_ui_scale(width, height);
    const float text_scale =
        std::min(0.8f * scale,
                 (static_cast<float>(width) - 32.0f) /
                     std::max({font.measure(ratio), font.measure(wheel),
                               font.measure(source), font.measure(limit)}));
    const float panel_w =
        (std::max({font.measure(ratio), font.measure(wheel),
                   font.measure(source), font.measure(limit)}) *
         text_scale) +
        16.0f * scale;
    const float panel_h = 69.0f * scale;
    const SDL_FRect panel{
        std::clamp(x + 12.0f, 8.0f,
                   std::max(8.0f, static_cast<float>(width) - panel_w - 8.0f)),
        std::clamp(y + 12.0f, 8.0f,
                   std::max(8.0f, static_cast<float>(height) - panel_h - 8.0f)),
        panel_w, panel_h};
    SDL_SetRenderDrawColor(screen, 20, 25, 31, 250);
    SDL_RenderFillRect(screen, &panel);
    SDL_SetRenderDrawColor(screen, 99, 211, 220, 255);
    SDL_RenderRect(screen, &panel);
    const std::array<const char *, 4> lines{ratio, wheel, source, limit};
    for (std::size_t row = 0; row < lines.size(); ++row)
        font.draw(screen, panel.x + 8.0f * scale,
                  panel.y + (4.0f + 16.0f * static_cast<float>(row)) * scale,
                  lines[row],
                  row == 0 ? SDL_Color{235, 241, 246, 255}
                           : SDL_Color{145, 177, 190, 255},
                  text_scale);
}

void draw_lab_buttons(const LayoutState &layout_state, SDL_Renderer *screen,
                      FontRenderer &font, int width, int height,
                      const std::array<bool, 9> &selected,
                      const std::array<bool, 9> &enabled, double load_nm) {
    if (!lab_buttons_visible(width, height))
        return;
    float mouse_x = 0.0f;
    float mouse_y = 0.0f;
    const auto mouse_state = SDL_GetMouseState(&mouse_x, &mouse_y);
    const bool has_pointer = SDL_RenderCoordinatesFromWindow(
        screen, mouse_x, mouse_y, &mouse_x, &mouse_y);
    const float left_width = layout_for(layout_state, width, height).left.w;
    const auto hovered =
        has_pointer
            ? hit_test_lab_button(mouse_x, mouse_y, width, height, left_width)
            : LabButtonAction::None;
    const float scale = lab_ui_scale(width, height);
    for (std::size_t index = 0; index < lab_button_labels.size(); ++index) {
        const auto action = static_cast<LabButtonAction>(index);
        const bool over = action == hovered;
        const bool held = over && (mouse_state & SDL_BUTTON_LMASK) != 0;
        const auto bounds = lab_button_rect(index, width, height, left_width);
        const SDL_FRect box{bounds.x, bounds.y, bounds.width, bounds.height};
        const auto style = oes::button_style({235.0f, 241.0f, 246.0f, 255.0f},
                                             {14.0f, 16.0f, 18.0f, 255.0f},
                                             selected[index], held, over);
        const auto sdl_color = [](const oes::ButtonColor &color) {
            return SDL_Color{
                static_cast<Uint8>(color[0]), static_cast<Uint8>(color[1]),
                static_cast<Uint8>(color[2]), static_cast<Uint8>(color[3])};
        };
        const SDL_Color fill = !enabled[index] ? SDL_Color{24, 30, 38, 255}
                                               : sdl_color(style.fill);
        const SDL_Color frame = !enabled[index] ? SDL_Color{65, 75, 82, 255}
                                                : sdl_color(style.foreground);
        SDL_SetRenderDrawColor(screen, fill.r, fill.g, fill.b, fill.a);
        SDL_RenderFillRect(screen, &box);
        SDL_SetRenderDrawColor(screen, frame.r, frame.g, frame.b, frame.a);
        SDL_RenderRect(screen, &box);
        std::string label(lab_button_labels[index]);
        if (action == LabButtonAction::Load) {
            const SDL_FRect fill_bar{
                box.x + 2.0f, box.y + box.h - 5.0f * scale,
                (box.w - 4.0f) *
                    static_cast<float>(std::clamp(load_nm / 60.0, 0.0, 1.0)),
                3.0f * scale};
            SDL_SetRenderDrawColor(screen, 99, 211, 220, 255);
            SDL_RenderFillRect(screen, &fill_bar);
            char load_label[16];
            std::snprintf(load_label, sizeof(load_label), "LOAD %.0f", load_nm);
            label = load_label;
        }
        const SDL_Color label_color = enabled[index]
                                          ? sdl_color(style.foreground)
                                          : SDL_Color{94, 108, 116, 255};
        const float text_scale = bounds.height < 36.0f ? 0.68f * scale : scale;
        if (action == LabButtonAction::Starter) {
            if (bounds.height < 36.0f) {
                font.draw(screen,
                          bounds.x + (bounds.width -
                                      font.measure(label) * text_scale) /
                                         2.0f,
                          bounds.y + 6.0f * scale, label, label_color,
                          text_scale);
                continue;
            }
            font.draw(
                screen,
                bounds.x + (bounds.width - font.measure(label) * scale) / 2.0f,
                bounds.y + bounds.height * 0.05f, label, label_color, scale);
            const std::string hint = "HOLD";
            const float hint_scale = 0.65f * scale;
            font.draw(screen,
                      bounds.x +
                          (bounds.width - font.measure(hint) * hint_scale) /
                              2.0f,
                      bounds.y + bounds.height * 0.60f, hint, label_color,
                      hint_scale);
            continue;
        }
        font.draw(screen,
                  bounds.x +
                      (bounds.width - font.measure(label) * text_scale) / 2.0f,
                  bounds.y + (bounds.height - 14.0f * text_scale) / 2.0f - 1.0f,
                  label, label_color, text_scale);
    }
}

SDL_FRect pedal_slider_rect(const LayoutState &layout_state, int width,
                            int height) {
    const float scale = lab_ui_scale(width, height);
    if (width < 1100 && height < 620) {
        const float scene_width =
            layout_for(layout_state, width, height).mechanical.w;
        return {scene_width * 0.5f + 3.0f, width < 900 ? 120.0f : 94.0f,
                scene_width * 0.5f - 19.0f, width < 900 ? 20.0f : 22.0f};
    }
    if (width >= 1100) {
        const float left_width = layout_for(layout_state, width, height).left.w;
        return {16.0f, 64.0f * scale, left_width - 32.0f, 27.0f * scale};
    }
    return {250.0f, 64.0f * scale,
            std::min(static_cast<float>(width) * 0.30f, 220.0f), 27.0f * scale};
}

SDL_FRect volume_slider_rect(const LayoutState &layout_state, int width,
                             int height) {
    const float scale = lab_ui_scale(width, height);
    if (width < 1100 && height < 620) {
        const float scene_width =
            layout_for(layout_state, width, height).mechanical.w;
        return {16.0f, width < 900 ? 120.0f : 94.0f,
                width < 900 ? scene_width * 0.5f - 19.0f
                            : scene_width * 0.5f - 110.0f,
                width < 900 ? 20.0f : 22.0f};
    }
    if (width >= 1100) {
        const float left_width = layout_for(layout_state, width, height).left.w;
        return {16.0f, static_cast<float>(height) - 126.0f, left_width - 32.0f,
                27.0f * scale};
    }
    return {16.0f, 64.0f * scale,
            width >= 900 ? 130.0f
                         : std::min(static_cast<float>(width) * 0.30f, 220.0f),
            27.0f * scale};
}

void draw_volume_slider(const LayoutState &layout_state, SDL_Renderer *screen,
                        FontRenderer &font, int width, int height, float volume,
                        bool enabled, std::string_view sound_state,
                        bool show_diagnostics, unsigned int pcm_peak,
                        unsigned long long shortfall,
                        unsigned long long dropped) {
    if (!lab_buttons_visible(width, height))
        return;
    const SDL_FRect box = volume_slider_rect(layout_state, width, height);
    const float scale = lab_ui_scale(width, height);
    SDL_SetRenderDrawColor(screen, 29, 43, 55, 255);
    SDL_RenderFillRect(screen, &box);
    SDL_SetRenderDrawColor(screen, enabled ? 99 : 65, enabled ? 211 : 75,
                           enabled ? 220 : 82, 255);
    SDL_RenderRect(screen, &box);
    const SDL_FRect fill{box.x + 2.0f, box.y + box.h - 5.0f * scale,
                         (box.w - 4.0f) * volume, 3.0f * scale};
    SDL_RenderFillRect(screen, &fill);
    char label[32];
    if (!enabled)
        std::snprintf(label, sizeof(label), "AUDIO %s",
                      sound_state == "off" ? "OFF" : "N/D");
    else
        std::snprintf(label, sizeof(label), "%s %.0f%%",
                      sound_state == "muted"       ? "MUTED"
                      : sound_state == "paused"    ? "PAUSED"
                      : sound_state == "key off"   ? "KEY OFF"
                      : sound_state == "speed"     ? "SUSP>1X"
                      : sound_state == "suspended" ? "SUSP"
                                                   : "VOLUME",
                      static_cast<double>(volume) * 100.0);
    const bool short_slider = box.h < 25.0f * scale;
    const float label_scale = short_slider ? 0.8f * scale : scale;
    font.draw(screen, box.x + 8.0f,
              box.y + (short_slider ? 2.0f : 5.0f) * scale, label,
              enabled ? SDL_Color{235, 241, 246, 255}
                      : SDL_Color{94, 108, 116, 255},
              label_scale);
    if (show_diagnostics && enabled && width >= 1100 && height >= 690) {
        const SDL_FRect gear = gear_widget_rect(layout_state, width, height);
        const float detail_y = box.y + box.h + 4.0f * scale;
        if (gear.w > 0.0f && detail_y + 30.0f * scale > gear.y &&
            detail_y < gear.y + gear.h) {
            const float right_x = gear.x + gear.w + 5.0f * scale;
            const float left_space = gear.x - box.x - 8.0f * scale;
            const float right_space =
                layout_for(layout_state, width, height).left.w - right_x -
                8.0f * scale;
            const auto draw_fit = [&](float x, float y, const char *text,
                                      SDL_Color color, float available_width) {
                const float text_scale =
                    std::min(scale, available_width /
                                        std::max(1.0f, font.measure(text)));
                font.draw(screen, x, y, text, color, text_scale);
            };
            char peak[32], shortage[40], drops[32];
            std::snprintf(peak, sizeof(peak), "PCM %.1f%%",
                          100.0 * static_cast<double>(pcm_peak) / 32768.0);
            std::snprintf(shortage, sizeof(shortage), "SHORT~%llu", shortfall);
            std::snprintf(drops, sizeof(drops), "DROP %llu", dropped);
            draw_fit(box.x + 4.0f, detail_y, peak,
                     pcm_peak > 0 ? SDL_Color{99, 211, 220, 255}
                                  : SDL_Color{145, 177, 190, 255},
                     left_space);
            const SDL_Color health = shortfall > 0 || dropped > 0
                                         ? SDL_Color{249, 190, 96, 255}
                                         : SDL_Color{145, 177, 190, 255};
            draw_fit(right_x, detail_y, shortage, health, right_space);
            draw_fit(right_x, detail_y + 18.0f * scale, drops, health,
                     right_space);
            return;
        }
        char signal[48];
        std::snprintf(signal, sizeof(signal), "PCM PEAK %.1f%%",
                      100.0 * static_cast<double>(pcm_peak) / 32768.0);
        font.draw(screen, box.x + 4.0f, box.y + box.h + 4.0f * scale, signal,
                  pcm_peak > 0 ? SDL_Color{99, 211, 220, 255}
                               : SDL_Color{145, 177, 190, 255},
                  scale);
        char health[80];
        std::snprintf(health, sizeof(health), "STREAM SHORT~%llu  DROP %llu",
                      shortfall, dropped);
        font.draw(screen, box.x + 4.0f, box.y + box.h + 22.0f * scale, health,
                  shortfall > 0 || dropped > 0 ? SDL_Color{249, 190, 96, 255}
                                               : SDL_Color{145, 177, 190, 255},
                  scale);
    }
}

void draw_pedal_slider(const LayoutState &layout_state, SDL_Renderer *screen,
                       FontRenderer &font, int width, int height,
                       double pedal_pull_m, bool enabled,
                       bool replay_controls) {
    if (!lab_buttons_visible(width, height))
        return;
    const SDL_FRect box = pedal_slider_rect(layout_state, width, height);
    const float scale = lab_ui_scale(width, height);
    const float fraction =
        static_cast<float>(std::clamp(pedal_pull_m / 0.025, 0.0, 1.0));
    SDL_SetRenderDrawColor(screen, 29, 43, 55, 255);
    SDL_RenderFillRect(screen, &box);
    SDL_SetRenderDrawColor(screen, enabled ? 99 : 65, enabled ? 211 : 75,
                           enabled ? 220 : 82, 255);
    SDL_RenderRect(screen, &box);
    const SDL_FRect fill{box.x + 2.0f, box.y + box.h - 5.0f * scale,
                         (box.w - 4.0f) * fraction, 3.0f * scale};
    SDL_RenderFillRect(screen, &fill);
    char label[32];
    if (replay_controls)
        std::snprintf(label, sizeof(label), "PEDAL %.0f MM | REPLAY",
                      pedal_pull_m * 1000.0);
    else
        std::snprintf(label, sizeof(label), "PEDAL CMD %.0f%%",
                      static_cast<double>(fraction) * 100.0);
    font.draw(screen, box.x + 8.0f, box.y + 5.0f * scale, label,
              enabled ? SDL_Color{235, 241, 246, 255}
                      : SDL_Color{94, 108, 116, 255},
              scale);
}

} // namespace

bool show_sdl_display(const ma17::EmulatorSnapshot &snapshot, int frame_limit,
                      const std::string &screenshot_path, SimSession *session,
                      long long capture_after_tick,
                      const std::vector<ma17::EmulatorEvent> *captured_events,
                      bool replay_controls, bool gpu_preview, bool enable_audio,
                      int frame_delay_ms, bool bench_preset,
                      const ControlTraceMetadata *metadata,
                      int ui_scale_percent) {
    if (!SDL_Init(SDL_INIT_VIDEO |
                  (session && enable_audio ? SDL_INIT_AUDIO : 0U))) {
        std::fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
        return false;
    }
    // Finite-frame captures stay reproducible unless they request a scale.
    LabUiPreferences ui_preferences;
    if (frame_limit <= 0) {
        ui_preferences = load_ui_preferences();
        if (ui_scale_percent == 0)
            ui_scale_percent = ui_preferences.scale_percent;
        if (ui_scale_percent == ui_preferences.scale_percent &&
            ui_scale_percent != 0)
            std::fprintf(stdout, "[LAB-UI-SCALE] source=prefs percent=%d\n",
                         ui_scale_percent);
    }
    LayoutState layout_state;
    layout_state.left_fraction = ui_preferences.left_fraction;
    layout_state.right_fraction = ui_preferences.right_fraction;
    layout_state.scope_fraction = ui_preferences.scope_fraction;
    layout_state.mode = static_cast<LabPresentationMode>(ui_preferences.mode);
    DisplayUnits display_units =
        static_cast<DisplayUnits>(ui_preferences.display_units);
    if (frame_limit <= 0)
        std::fprintf(stdout,
                     "[LAB-LAYOUT] source=prefs left=%.3f right=%.3f mode=%d "
                     "scope=%.3f\n",
                     static_cast<double>(ui_preferences.left_fraction),
                     static_cast<double>(ui_preferences.right_fraction),
                     ui_preferences.mode,
                     static_cast<double>(ui_preferences.scope_fraction));
    configured_ui_scale_percent = ui_scale_percent;
    SDL_Window *window =
        SDL_CreateWindow("FIAT TIPO 1.6 i.e. | SEVEL MA1.7 Lab", 1280, 720,
                         SDL_WINDOW_RESIZABLE);
    SDL_Renderer *screen =
        window ? SDL_CreateRenderer(window, nullptr) : nullptr;
    if (!screen && window) {
        std::fprintf(stderr, "SDL preferred renderer: %s; trying software\n",
                     SDL_GetError());
        screen = SDL_CreateRenderer(window, "software");
    }
    if (!screen) {
        std::fprintf(stderr, "SDL renderer: %s\n", SDL_GetError());
        if (window)
            SDL_DestroyWindow(window);
        SDL_Quit();
        return false;
    }

    // Effective state for the scope helpers at the current output size.
    const auto layout_in_force = [&]() {
        int output_w = 0;
        int output_h = 0;
        return LabLayout::effective(
            layout_state, render_layout_size(screen, &output_w, &output_h)
                              ? static_cast<float>(output_w)
                              : 0.0f);
    };
    const char *renderer_name = SDL_GetRendererName(screen);
    // Record the device that actually rasterizes: GL renderers expose it as
    // GL_RENDERER; others report "n/a" (the DRI node is checked externally).
    std::string video_device = "n/a";
    if (SDL_GL_GetCurrentContext()) {
        using GlGetString = const unsigned char *(*)(unsigned);
        const SDL_FunctionPointer address =
            SDL_GL_GetProcAddress("glGetString");
        GlGetString gl_get_string = nullptr;
        std::memcpy(&gl_get_string, &address, sizeof(gl_get_string));
        if (gl_get_string) {
            constexpr unsigned kGlRenderer = 0x1F01U;
            if (const unsigned char *text = gl_get_string(kGlRenderer))
                video_device = reinterpret_cast<const char *>(text);
        }
    }
    const char *video_driver = SDL_GetCurrentVideoDriver();
    std::fprintf(stdout, "[LAB-VIDEO] renderer=%s video=%s device=%s\n",
                 renderer_name ? renderer_name : "unknown",
                 video_driver ? video_driver : "unknown", video_device.c_str());
    AuthoredMeshLibrary meshes;
    const char *base_path = SDL_GetBasePath();
    const auto mesh_path = base_path ? std::filesystem::path(base_path) /
                                           "assets/authored_meshes.obj.zlib.b64"
                                     : std::filesystem::path{};
    if (!base_path || !load_packaged_meshes(meshes, mesh_path.string())) {
        std::fprintf(stderr, "Cannot load packaged donor meshes: %s\n",
                     mesh_path.string().c_str());
        SDL_DestroyRenderer(screen);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return false;
    }
    const auto font_path =
        std::filesystem::path(base_path) / "assets/slkscr.ttf.zlib.b64";
    FontSpec font_spec;
    if (!font_spec_from_token(ui_preferences.font, font_spec))
        font_spec = {};
    FontRenderer font(font_path.string(), font_spec);
    g_font_identity = font.face_identity();
    font.set_size_factor(static_cast<float>(ui_preferences.font_percent) /
                         100.0f);
    if (!font.ready()) {
        std::fprintf(stderr, "Cannot load packaged donor font: %s\n",
                     font_path.string().c_str());
        SDL_DestroyRenderer(screen);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return false;
    }
    SDL_Window *gpu_window = nullptr;
    std::unique_ptr<SdlGpuRenderer> gpu_renderer;
    if (gpu_preview) {
        gpu_window = SDL_CreateWindow("SEVEL donor GPU scene", 960, 640,
                                      SDL_WINDOW_RESIZABLE);
        if (gpu_window) {
            gpu_renderer = std::make_unique<SdlGpuRenderer>();
            const auto shader_path =
                std::filesystem::path(base_path) / "assets/shaders";
            if (!gpu_renderer->initialize(gpu_window, shader_path.string())) {
                std::fprintf(stderr, "SDL GPU preview unavailable: %s\n",
                             gpu_renderer->lastError());
                gpu_renderer.reset();
            } else {
                std::fprintf(stdout, "[LAB-GPU] preview_ready=1 shaders=%s\n",
                             shader_path.string().c_str());
            }
        } else {
            std::fprintf(stderr, "SDL GPU preview window: %s\n",
                         SDL_GetError());
        }
        if (!gpu_renderer && gpu_window) {
            SDL_DestroyWindow(gpu_window);
            gpu_window = nullptr;
        }
    }
    bool running = true;
    bool captured = screenshot_path.empty();
    bool gpu_capture_attempted = false;
    bool manual_capture_requested = false;
    unsigned long long manual_capture_index = 0;
    bool scope_csv_requested = false;
    unsigned long long scope_csv_index = 0;
    SDL_AudioStream *audio_stream = nullptr;
    std::unique_ptr<LiveAudio> audio_source;
    if (session && enable_audio) {
        const SDL_AudioSpec spec{SDL_AUDIO_S16, 1, 44100};
        audio_stream = SDL_OpenAudioDeviceStream(
            SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, &spec, nullptr, nullptr);
        if (audio_stream) {
            const char *audio_driver = SDL_GetCurrentAudioDriver();
            std::fprintf(stdout,
                         "[LAB-AUDIO] stream_open=1 driver=%s format=S16 "
                         "channels=1 rate=44100\n",
                         audio_driver ? audio_driver : "unknown");
            audio_source = std::make_unique<LiveAudio>(*session, audio_stream);
            audio_source->start();
        } else {
            std::fprintf(stderr, "SDL audio unavailable: %s\n", SDL_GetError());
        }
    }
    double pedal_pull_m = snapshot.pedal_pull_m;
    double pedal_applied_m = pedal_pull_m;
    double load_nm = snapshot.applied_load_nm;
    double road_speed_target_kmh = snapshot.vehicle_speed_kmh;
    int selected_gear =
        snapshot.drivetrain_available ? snapshot.transmission_gear : 0;
    std::optional<double> requested_clutch_pressure;
    int compact_instrument_page = 0;
    double remembered_load_nm = load_nm > 0.0 ? load_nm : 24.0;
    bool pedal_user_override = false;
    bool load_user_override = false;
    bool key_on = snapshot.key_on;
    bool sound_muted = false;
    bool keyboard_starter_held = false;
    bool mouse_starter_held = false;
    bool pedal_dragging = false;
    bool load_dragging = false;
    bool volume_dragging = false;
    int layout_divider_dragging = 0;
    std::array<bool, 4> scope_channels_visible{
        (ui_preferences.digital_channel_mask & 1U) != 0,
        (ui_preferences.digital_channel_mask & 2U) != 0,
        (ui_preferences.digital_channel_mask & 4U) != 0,
        (ui_preferences.digital_channel_mask & 8U) != 0};
    long long scope_span_ticks = ui_preferences.digital_span_ticks;
    long long analog_span_ticks = ui_preferences.analog_span_ticks;
    bool analog_scope = ui_preferences.scope_mode != 0;
    bool scope_maximized = false;
    int analog_group = ui_preferences.analog_group;
    std::optional<ScopeAxisRanges> fitted_scope_axes;
    bool fit_scope_axes_requested = false;
    if (frame_limit <= 0)
        std::fprintf(stdout,
                     "[LAB-SCOPE-PREF] source=prefs analog=%d group=%d "
                     "analog_span=%lld digital_span=%lld mask=%u\n",
                     analog_scope ? 1 : 0, analog_group, analog_span_ticks,
                     scope_span_ticks, ui_preferences.digital_channel_mask);
    bool analog_frozen = false;
    bool digital_frozen = false;
    long long frozen_digital_tick = snapshot.tick;
    long long digital_capture_tick = snapshot.tick;
    std::vector<ma17::EmulatorEvent> frozen_digital_events;
    std::vector<ma17::EmulatorSnapshot> frozen_digital_history;
    std::size_t frozen_event_base_index = 0;
    unsigned long long frozen_event_overflow = 0;
    ma17::EmulatorSnapshot frozen_scope_snapshot = snapshot;
    ma17::EmulatorSnapshot analog_scope_displayed = snapshot;
    long long analog_scope_end_tick = snapshot.tick;
    std::optional<long long> analog_navigation_end_tick;
    TriggerMode trigger_mode = TriggerMode::Off;
    TriggerSlope trigger_slope = TriggerSlope::Rising;
    std::size_t trigger_channel = 0;
    int trigger_event_source = -1;
    double trigger_level = 1.0;
    double trigger_pre_fraction = 0.25;
    bool trigger_latched = false;
    long long frozen_scope_end_tick = snapshot.tick;
    bool trigger_waiting = false;
    bool last_trigger_waiting = false;
    long long active_trigger_tick = -1;
    long long trigger_armed_tick = snapshot.tick;
    struct NormalTriggerCapture {
        long long armed_tick = -1;
        long long trigger_tick = -1;
        long long span = 0;
        long long end = 0;
        ma17::EmulatorSnapshot snapshot;
        std::vector<ma17::EmulatorSnapshot> history;
    } normal_capture;
    std::array<long long, 2> scope_cursor_ticks{-1, -1};
    std::array<std::optional<DigitalScopeCursor>, 2> digital_cursors{};
    float sound_volume = 1.0f;
    SceneCamera camera;
    camera.zoom = 0.78f;
    SceneCamera axial_camera = camera;
    float fitted_scene_height = -1.0f;
    float fitted_pane_width = -1.0f;
    int fitted_focus = -1;
    bool restore_camera_pending = ui_preferences.camera_saved != 0;
    const auto reset_cameras = [&] {
        restore_camera_pending = false;
        camera = {};
        axial_camera = {};
        camera.zoom = axial_camera.zoom = 0.78f;
        fitted_scene_height = -1.0f;
    };
    int view_mode = ui_preferences.view_mode;
    bool show_help = false;
    bool show_debug = false;
    std::array<Gauge, 3> gauges{};
    std::vector<ma17::EmulatorSnapshot> analog_history;
    std::vector<ma17::EmulatorSnapshot> digital_history;
    Uint64 last_frame_ticks = SDL_GetTicks();
    Uint64 last_snapshot_wall_ms = last_frame_ticks;
    long long last_snapshot_tick = snapshot.tick;
    long long last_pedal_tick = snapshot.tick;
    ma17::EmulatorSnapshot displayed = snapshot;
    const auto click_digital_cursor =
        [&](float x, float y, int scope_width, int view_height, bool is_frozen,
            long long frozen_tick,
            const std::vector<ma17::EmulatorEvent> &frozen_events,
            const std::vector<ma17::EmulatorSnapshot> &frozen_history) {
            const long long end_tick = is_frozen ? frozen_tick : displayed.tick;
            const auto recorded = is_frozen ? frozen_events
                                  : session ? session->event_window().events
                                  : captured_events
                                      ? *captured_events
                                      : std::vector<ma17::EmulatorEvent>{};
            const auto history =
                is_frozen ? frozen_history
                : session ? session->snapshot_window(std::max(
                                0LL, end_tick - scope_span_ticks - 247500LL))
                          : std::vector<ma17::EmulatorSnapshot>{displayed};
            return digital_scope_cursor_at(layout_in_force(), x, y, scope_width,
                                           view_height, end_tick,
                                           scope_span_ticks, recorded, history);
        };
    const auto capture_digital_window = [&] {
        frozen_digital_tick = digital_capture_tick = displayed.tick;
        const auto captured_window =
            session ? session->event_window()
                    : EventWindow{0, captured_events
                                         ? *captured_events
                                         : std::vector<ma17::EmulatorEvent>{}};
        frozen_digital_events = captured_window.events;
        frozen_event_base_index = captured_window.base_index;
        frozen_event_overflow = session ? session->event_overflow() : 0ULL;
        frozen_digital_history =
            session ? session->snapshot_window(
                          std::max(0LL, displayed.tick - 5197500LL))
                    : std::vector<ma17::EmulatorSnapshot>{displayed};
        digital_frozen = true;
    };
    std::vector<SDL_Vertex> scene_vertices;
    constexpr std::size_t scene_batch_vertices = 8190;
    scene_vertices.reserve(scene_batch_vertices);
    gauges[0].m_max = static_cast<float>(profile::rpm.maximum);
    gauges[1].m_max = 90.0f;
    gauges[2].m_max = static_cast<float>(profile::lambda.maximum);
    gauges[0].m_minorStep = static_cast<int>(profile::rpm.minor_step);
    gauges[0].m_majorStep = static_cast<int>(profile::rpm.major_step);
    gauges[0].m_thetaMin = 1.2f * 3.14159265f;
    gauges[0].m_thetaMax = -0.2f * 3.14159265f;
    gauges[0].m_needleWidth = 4.0f;
    gauges[0].m_needleTimeConstant = 0.2f;
    gauges[1].m_minorStep = 5;
    gauges[1].m_majorStep = 10;
    gauges[2].m_minorStep = 1;
    gauges[2].m_majorStep = 1;
    for (auto &gauge : gauges) {
        gauge.m_minorTickLength = 6.0f;
        gauge.m_majorTickLength = 14.0f;
    }
    gauges[0].reset(static_cast<float>(displayed.rpm));
    gauges[1].reset(static_cast<float>(displayed.throttle_angle_rad * 57.2958));
    gauges[2].reset(static_cast<float>(displayed.lambda));
    const auto activate_button = [&](LabButtonAction action) {
        if (!session)
            return;
        if (replay_controls && (action == LabButtonAction::Key ||
                                action == LabButtonAction::PedalDown ||
                                action == LabButtonAction::PedalUp ||
                                action == LabButtonAction::Load))
            return;
        switch (action) {
        case LabButtonAction::Key:
            key_on = !key_on;
            session->set_key(key_on);
            break;
        case LabButtonAction::PedalDown:
        case LabButtonAction::PedalUp: {
            pedal_user_override = true;
            // A first step must move past the modeled cable free play.
            constexpr double pedal_step_m = 0.002;
            pedal_pull_m =
                std::clamp(pedal_pull_m + (action == LabButtonAction::PedalUp
                                               ? pedal_step_m
                                               : -pedal_step_m),
                           0.0, 0.025);
            break;
        }
        case LabButtonAction::Load:
            load_user_override = true;
            if (load_nm > 0.0) {
                remembered_load_nm = load_nm;
                load_nm = 0.0;
            } else {
                load_nm = remembered_load_nm;
            }
            session->set_load(load_nm);
            break;
        case LabButtonAction::Pause:
            session->set_paused(!session->paused());
            break;
        case LabButtonAction::Slower:
            session->set_speed(session->speed() / 2.0);
            break;
        case LabButtonAction::Faster:
            session->set_speed(session->speed() * 2.0);
            break;
        case LabButtonAction::Mute:
            sound_muted = !sound_muted;
            if (audio_stream)
                SDL_SetAudioStreamGain(audio_stream,
                                       sound_muted ? 0.0f : sound_volume);
            break;
        case LabButtonAction::Starter:
        case LabButtonAction::None:
            break;
        }
    };
    int windowed_width = 0;
    int windowed_height = 0;
    const auto toggle_fullscreen = [&] {
        const bool fullscreen =
            (SDL_GetWindowFlags(window) & SDL_WINDOW_FULLSCREEN) != 0;
        if (!fullscreen)
            SDL_GetWindowSize(window, &windowed_width, &windowed_height);
        if (!SDL_SetWindowFullscreen(window, !fullscreen))
            std::fprintf(stderr, "SDL fullscreen: %s\n", SDL_GetError());
        else {
            if (!SDL_SyncWindow(window))
                std::fprintf(stderr, "SDL fullscreen sync: %s\n",
                             SDL_GetError());
        }
    };
    const auto set_pedal_from_pointer = [&](float x, int width, int height) {
        const SDL_FRect box = pedal_slider_rect(layout_state, width, height);
        pedal_user_override = true;
        pedal_pull_m = 0.025 * static_cast<double>(
                                   std::clamp((x - box.x) / box.w, 0.0f, 1.0f));
    };
    const auto set_load_from_pointer = [&](float x, int width, int height) {
        const auto box = lab_button_rect(
            static_cast<std::size_t>(LabButtonAction::Load), width, height,
            layout_for(layout_state, width, height).left.w);
        load_user_override = true;
        load_nm = 60.0 * static_cast<double>(
                             std::clamp((x - box.x) / box.width, 0.0f, 1.0f));
        if (load_nm > 0.0)
            remembered_load_nm = load_nm;
        session->set_load(load_nm);
    };
    const auto set_volume_from_pointer = [&](float x, int width, int height) {
        const SDL_FRect box = volume_slider_rect(layout_state, width, height);
        sound_volume = std::clamp((x - box.x) / box.w, 0.0f, 1.0f);
        SDL_SetAudioStreamGain(audio_stream, sound_muted ? 0.0f : sound_volume);
    };
    int presentation_width = 0;
    int presentation_height = 0;
    const auto update_presentation = [&] {
        if (ui_scale_percent == 0) {
            if (presentation_width != 0 &&
                !SDL_SetRenderLogicalPresentation(
                    screen, 0, 0, SDL_LOGICAL_PRESENTATION_DISABLED))
                return false;
            presentation_width = presentation_height = 0;
            return true;
        }
        int pixel_width = 0;
        int pixel_height = 0;
        if (!SDL_GetRenderOutputSize(screen, &pixel_width, &pixel_height))
            return false;
        if (pixel_width == presentation_width &&
            pixel_height == presentation_height)
            return true;
        const int logical_width =
            std::max(1, pixel_width * 100 / ui_scale_percent);
        const int logical_height =
            std::max(1, pixel_height * 100 / ui_scale_percent);
        if (!SDL_SetRenderLogicalPresentation(screen, logical_width,
                                              logical_height,
                                              SDL_LOGICAL_PRESENTATION_STRETCH))
            return false;
        presentation_width = pixel_width;
        presentation_height = pixel_height;
        return true;
    };
    for (int frame = 0; running && (frame_limit <= 0 || frame < frame_limit);
         ++frame) {
        if (!update_presentation()) {
            std::fprintf(stderr, "SDL logical presentation: %s\n",
                         SDL_GetError());
            running = false;
            break;
        }
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                (event.key.mod & SDL_KMOD_CTRL) != 0 &&
                event.key.key >= SDLK_0 && event.key.key <= SDLK_3) {
                ui_scale_percent =
                    event.key.key == SDLK_0
                        ? 0
                        : 50 + 50 * static_cast<int>(event.key.key - SDLK_0);
                configured_ui_scale_percent = ui_scale_percent;
                if (ui_scale_percent != 0)
                    presentation_width = 0;
                ui_preferences.scale_percent = ui_scale_percent;
                const bool saved = save_ui_preferences(ui_preferences);
                std::fprintf(stdout,
                             "[LAB-UI-SCALE] source=key percent=%d saved=%d\n",
                             ui_scale_percent, saved ? 1 : 0);
                continue;
            }
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                (event.key.mod & SDL_KMOD_CTRL) != 0 &&
                event.key.key == SDLK_U) {
                display_units = display_units == DisplayUnits::Metric
                                    ? DisplayUnits::Imperial
                                    : DisplayUnits::Metric;
                fitted_scope_axes.reset();
                ui_preferences.display_units = static_cast<int>(display_units);
                const bool saved =
                    frame_limit <= 0 && save_ui_preferences(ui_preferences);
                std::fprintf(stdout, "[LAB-UNITS] mode=%s saved=%d\n",
                             display_units == DisplayUnits::Metric ? "metric"
                                                                   : "imperial",
                             saved ? 1 : 0);
                continue;
            }
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                (event.key.mod & SDL_KMOD_CTRL) != 0 &&
                event.key.key >= SDLK_7 && event.key.key <= SDLK_9) {
                ui_preferences.font_percent =
                    100 + 5 * static_cast<int>(event.key.key - SDLK_7);
                font.set_size_factor(
                    static_cast<float>(ui_preferences.font_percent) / 100.0f);
                const bool saved =
                    frame_limit <= 0 && save_ui_preferences(ui_preferences);
                std::fprintf(stdout, "[LAB-FONT] percent=%d saved=%d\n",
                             ui_preferences.font_percent, saved ? 1 : 0);
                continue;
            }
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                (event.key.mod & SDL_KMOD_CTRL) != 0 &&
                event.key.key >= SDLK_4 && event.key.key <= SDLK_6) {
                ui_preferences.mode = static_cast<int>(event.key.key - SDLK_4);
                layout_state.mode =
                    static_cast<LabPresentationMode>(ui_preferences.mode);
                ui_preferences.scope_fraction = layout_state.scope_fraction =
                    -1.0f;
                scope_maximized = false;
                const bool saved =
                    frame_limit <= 0 && save_ui_preferences(ui_preferences);
                std::fprintf(stdout,
                             "[LAB-LAYOUT] source=mode mode=%d saved=%d\n",
                             ui_preferences.mode, saved ? 1 : 0);
                continue;
            }
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                (event.key.mod & SDL_KMOD_CTRL) != 0 &&
                event.key.key == SDLK_R) {
                ui_preferences.left_fraction = layout_state.left_fraction =
                    0.24f;
                ui_preferences.right_fraction = layout_state.right_fraction =
                    0.66f;
                ui_preferences.mode = 0;
                layout_state.mode = LabPresentationMode::Bench;
                ui_preferences.scope_fraction = layout_state.scope_fraction =
                    -1.0f;
                scope_maximized = false;
                const bool saved =
                    frame_limit <= 0 && save_ui_preferences(ui_preferences);
                std::fprintf(stdout,
                             "[LAB-LAYOUT] source=reset left=0.240 right=0.660 "
                             "mode=0 saved=%d\n",
                             saved ? 1 : 0);
                continue;
            }
            if ((event.type == SDL_EVENT_WINDOW_RESIZED ||
                 event.type == SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED ||
                 event.type == SDL_EVENT_WINDOW_DISPLAY_SCALE_CHANGED) &&
                event.window.windowID == SDL_GetWindowID(window) &&
                !update_presentation()) {
                std::fprintf(stderr, "SDL logical resize: %s\n",
                             SDL_GetError());
                running = false;
                break;
            }
            if (event.type == SDL_EVENT_WINDOW_LEAVE_FULLSCREEN &&
                event.window.windowID == SDL_GetWindowID(window) &&
                windowed_width > 1 && windowed_height > 1 &&
                SDL_GetCurrentVideoDriver() &&
                std::string_view(SDL_GetCurrentVideoDriver()) == "x11") {
                // Refresh the X11/SDL pixel buffer after leaving fullscreen.
                SDL_SetWindowSize(window, windowed_width - 1,
                                  windowed_height - 1);
                SDL_SyncWindow(window);
                SDL_SetWindowSize(window, windowed_width, windowed_height);
                SDL_SyncWindow(window);
            }
            if (event.type == SDL_EVENT_MOUSE_MOTION ||
                event.type == SDL_EVENT_MOUSE_WHEEL ||
                event.type == SDL_EVENT_MOUSE_BUTTON_DOWN ||
                event.type == SDL_EVENT_MOUSE_BUTTON_UP) {
                const SDL_WindowID mouse_window =
                    event.type == SDL_EVENT_MOUSE_WHEEL ? event.wheel.windowID
                    : event.type == SDL_EVENT_MOUSE_MOTION
                        ? event.motion.windowID
                        : event.button.windowID;
                if (mouse_window != SDL_GetWindowID(window)) {
                    // A drag can end over the GPU preview or outside the UI.
                    if (event.type != SDL_EVENT_MOUSE_BUTTON_UP ||
                        event.button.button != SDL_BUTTON_LEFT)
                        continue;
                } else if (!SDL_ConvertEventToRenderCoordinates(screen,
                                                                &event)) {
                    continue;
                }
            }
            if (event.type == SDL_EVENT_WINDOW_CLOSE_REQUESTED) {
                if (event.window.windowID == SDL_GetWindowID(window))
                    running = false;
                else if (gpu_window &&
                         event.window.windowID == SDL_GetWindowID(gpu_window)) {
                    gpu_renderer.reset();
                    SDL_DestroyWindow(gpu_window);
                    gpu_window = nullptr;
                }
                continue;
            }
            if (event.type == SDL_EVENT_QUIT ||
                (event.type == SDL_EVENT_KEY_DOWN &&
                 event.key.key == SDLK_ESCAPE))
                running = false;
            if (event.type == SDL_EVENT_MOUSE_WHEEL && event.wheel.y != 0.0f) {
                int view_width = 0;
                int view_height = 0;
                const bool has_output =
                    render_layout_size(screen, &view_width, &view_height);
                const LabLayout active_layout =
                    layout_for(layout_state, view_width, view_height,
                               analog_scope && scope_maximized);
                const bool in_scope =
                    has_output &&
                    event.wheel.mouse_x >= active_layout.scope.x + 16.0f &&
                    event.wheel.mouse_x <
                        active_layout.scope.x + active_layout.scope.w - 16.0f &&
                    event.wheel.mouse_y >=
                        active_layout.scope.y + (analog_scope ? 0.0f : 12.0f) &&
                    event.wheel.mouse_y < active_layout.scope.y +
                                              active_layout.scope.h +
                                              (analog_scope ? 0.0f : 12.0f);
                const float direction =
                    event.wheel.direction == SDL_MOUSEWHEEL_FLIPPED
                        ? -event.wheel.y
                        : event.wheel.y;
                if (in_scope) {
                    if (analog_scope) {
                        constexpr std::array<long long, 6> windows{
                            990000LL,      5LL * 990000,  10LL * 990000,
                            30LL * 990000, 60LL * 990000, 300LL * 990000};
                        auto selected = std::lower_bound(
                            windows.begin(), windows.end(), analog_span_ticks);
                        if (direction > 0.0f && selected != windows.begin())
                            --selected;
                        else if (direction < 0.0f &&
                                 selected != windows.end() &&
                                 *selected == analog_span_ticks)
                            ++selected;
                        if (selected != windows.end()) {
                            const auto anchor = analog_scope_tick_at(
                                layout_in_force(),
                                event.wheel.mouse_x -
                                    active_layout.mechanical.x,
                                event.wheel.mouse_y,
                                static_cast<int>(active_layout.mechanical.w),
                                view_height, analog_scope_end_tick,
                                analog_span_ticks, scope_maximized);
                            const long long first = std::max(
                                0LL, analog_scope_end_tick - analog_span_ticks);
                            const double fraction =
                                anchor ? static_cast<double>(*anchor - first) /
                                             static_cast<double>(std::max(
                                                 1LL,
                                                 analog_scope_end_tick - first))
                                       : 0.5;
                            if (*selected != analog_span_ticks) {
                                analog_span_ticks = *selected;
                                const long long end =
                                    (anchor ? *anchor
                                            : first + (analog_scope_end_tick -
                                                       first) /
                                                          2) +
                                    static_cast<long long>(
                                        std::llround((1.0 - fraction) *
                                                     static_cast<double>(
                                                         analog_span_ticks)));
                                analog_navigation_end_tick =
                                    std::clamp(end, 0LL, displayed.tick);
                            }
                            trigger_armed_tick = displayed.tick;
                            normal_capture = {};
                            if (trigger_latched) {
                                analog_frozen = false;
                                trigger_latched = false;
                            }
                        }
                    } else {
                        constexpr std::array<long long, 8> windows{
                            9900LL,   19800LL,  49500LL,   99000LL,
                            247500LL, 990000LL, 1980000LL, 4950000LL};
                        auto selected = std::lower_bound(
                            windows.begin(), windows.end(), scope_span_ticks);
                        if (direction > 0.0f && selected != windows.begin())
                            --selected;
                        else if (direction < 0.0f &&
                                 selected != windows.end() &&
                                 *selected == scope_span_ticks)
                            ++selected;
                        if (selected != windows.end() &&
                            *selected != scope_span_ticks) {
                            const float local_x = event.wheel.mouse_x -
                                                  active_layout.mechanical.x;
                            const long long end = digital_frozen
                                                      ? frozen_digital_tick
                                                      : displayed.tick;
                            const auto anchor = digital_scope_tick_at(
                                layout_in_force(), local_x, event.wheel.mouse_y,
                                static_cast<int>(active_layout.mechanical.w),
                                view_height, end, scope_span_ticks);
                            if (anchor) {
                                if (!digital_frozen)
                                    capture_digital_window();
                                const double fraction =
                                    static_cast<double>(
                                        *anchor - (end - scope_span_ticks)) /
                                    static_cast<double>(scope_span_ticks);
                                const long long new_end =
                                    *anchor +
                                    static_cast<long long>(std::llround(
                                        (1.0 - std::clamp(fraction, 0.0, 1.0)) *
                                        static_cast<double>(*selected)));
                                scope_span_ticks = *selected;
                                const long long earliest_end = std::min(
                                    digital_capture_tick,
                                    std::max(0LL, digital_capture_tick -
                                                      5197500LL +
                                                      scope_span_ticks));
                                frozen_digital_tick =
                                    std::clamp(new_end, earliest_end,
                                               digital_capture_tick);
                            }
                        }
                    }
                } else if (has_output &&
                           event.wheel.mouse_x >= active_layout.mechanical.x &&
                           event.wheel.mouse_x < active_layout.instruments.x &&
                           event.wheel.mouse_y >= 90.0f &&
                           event.wheel.mouse_y < active_layout.mechanical.h) {
                    const bool left_pane =
                        event.wheel.mouse_x <
                        active_layout.mechanical.x +
                            active_layout.mechanical.w * 0.5f;
                    SceneCamera &target =
                        (left_pane == (view_mode != 0)) ? axial_camera : camera;
                    target.zoom = std::clamp(
                        target.zoom * (direction > 0.0f ? 1.1f : 1.0f / 1.1f),
                        0.5f, 3.0f);
                }
            }
            if (event.type == SDL_EVENT_MOUSE_MOTION &&
                (event.motion.state & SDL_BUTTON_MMASK)) {
                int view_width = 0;
                int view_height = 0;
                if (render_layout_size(screen, &view_width, &view_height)) {
                    const LabLayout active_layout =
                        layout_for(layout_state, view_width, view_height,
                                   analog_scope && scope_maximized);
                    if (analog_scope && !analog_frozen) {
                        const long long end =
                            analog_navigation_end_tick.value_or(
                                analog_scope_end_tick);
                        const float local_x =
                            event.motion.x - active_layout.mechanical.x;
                        const auto current = analog_scope_tick_at(
                            layout_in_force(), local_x, event.motion.y,
                            static_cast<int>(active_layout.mechanical.w),
                            view_height, end, analog_span_ticks,
                            scope_maximized);
                        const auto previous = analog_scope_tick_at(
                            layout_in_force(), local_x - event.motion.xrel,
                            event.motion.y,
                            static_cast<int>(active_layout.mechanical.w),
                            view_height, end, analog_span_ticks,
                            scope_maximized);
                        if (current && previous) {
                            analog_navigation_end_tick =
                                std::clamp(end + *previous - *current, 0LL,
                                           displayed.tick);
                            continue;
                        }
                    }
                    if (!analog_scope) {
                        const float local_x =
                            event.motion.x - active_layout.mechanical.x;
                        const int scope_width =
                            static_cast<int>(active_layout.mechanical.w);
                        const long long end = digital_frozen
                                                  ? frozen_digital_tick
                                                  : displayed.tick;
                        const auto current = digital_scope_tick_at(
                            layout_in_force(), local_x, event.motion.y,
                            scope_width, view_height, end, scope_span_ticks);
                        const auto previous = digital_scope_tick_at(
                            layout_in_force(), local_x - event.motion.xrel,
                            event.motion.y, scope_width, view_height, end,
                            scope_span_ticks);
                        if (current && previous) {
                            if (!digital_frozen)
                                capture_digital_window();
                            const long long earliest_end = std::min(
                                digital_capture_tick,
                                std::max(0LL, digital_capture_tick - 5197500LL +
                                                  scope_span_ticks));
                            frozen_digital_tick = std::clamp(
                                frozen_digital_tick + *previous - *current,
                                earliest_end, digital_capture_tick);
                            continue;
                        }
                    }
                    if (event.motion.x >= active_layout.mechanical.x &&
                        event.motion.x < active_layout.instruments.x &&
                        event.motion.y >= 90.0f &&
                        event.motion.y < active_layout.mechanical.h) {
                        const bool left_pane =
                            event.motion.x <
                            active_layout.mechanical.x +
                                active_layout.mechanical.w * 0.5f;
                        SceneCamera &target = (left_pane == (view_mode != 0))
                                                  ? axial_camera
                                                  : camera;
                        target.pan_x += event.motion.xrel;
                        target.pan_y += event.motion.yrel;
                    }
                }
            }
            if (layout_divider_dragging &&
                event.type == SDL_EVENT_MOUSE_MOTION &&
                (event.motion.state & SDL_BUTTON_LMASK)) {
                int view_width = 0;
                int view_height = 0;
                if (render_layout_size(screen, &view_width, &view_height))
                    layout_state = LabLayout::with_divider_moved(
                        layout_state, layout_divider_dragging, event.motion.x,
                        event.motion.y, static_cast<float>(view_width),
                        static_cast<float>(view_height));
                continue;
            }
            if (pedal_dragging && event.type == SDL_EVENT_MOUSE_MOTION &&
                (event.motion.state & SDL_BUTTON_LMASK)) {
                int view_width = 0;
                int view_height = 0;
                if (render_layout_size(screen, &view_width, &view_height))
                    set_pedal_from_pointer(event.motion.x, view_width,
                                           view_height);
            }
            if (load_dragging && event.type == SDL_EVENT_MOUSE_MOTION &&
                (event.motion.state & SDL_BUTTON_LMASK)) {
                int view_width = 0;
                int view_height = 0;
                if (render_layout_size(screen, &view_width, &view_height))
                    set_load_from_pointer(event.motion.x, view_width,
                                          view_height);
            }
            if (volume_dragging && event.type == SDL_EVENT_MOUSE_MOTION &&
                (event.motion.state & SDL_BUTTON_LMASK)) {
                int view_width = 0;
                int view_height = 0;
                if (render_layout_size(screen, &view_width, &view_height))
                    set_volume_from_pointer(event.motion.x, view_width,
                                            view_height);
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN &&
                event.button.button == SDL_BUTTON_LEFT) {
                int view_width = 0;
                int view_height = 0;
                if (render_layout_size(screen, &view_width, &view_height)) {
                    layout_divider_dragging = LabLayout::divider_at(
                        layout_state, event.button.x, event.button.y,
                        static_cast<float>(view_width),
                        static_cast<float>(view_height));
                    if (layout_divider_dragging) {
                        SDL_CaptureMouse(true);
                        continue;
                    }
                    const LabLayout pointer_layout =
                        layout_for(layout_state, view_width, view_height,
                                   analog_scope && scope_maximized);
                    if (view_width < 900 && view_height < 500) {
                        const SDL_FRect cluster = instrument_cluster_rect(
                            layout_state, view_width, view_height);
                        bool selected_tab = false;
                        for (int tab = 0; tab < 3; ++tab) {
                            const SDL_FRect rect =
                                compact_instrument_tab_rect(cluster, tab);
                            if (event.button.x >= rect.x &&
                                event.button.x < rect.x + rect.w &&
                                event.button.y >= rect.y &&
                                event.button.y < rect.y + rect.h) {
                                compact_instrument_page = tab;
                                std::fprintf(stdout,
                                             "[LAB-INSTRUMENT-TAB] page=%d\n",
                                             tab);
                                selected_tab = true;
                                break;
                            }
                        }
                        if (selected_tab)
                            continue;
                    }
                    if (analog_scope) {
                        if (analog_scope_maximize_at(
                                layout_in_force(),
                                event.button.x - pointer_layout.mechanical.x,
                                event.button.y,
                                static_cast<int>(pointer_layout.mechanical.w),
                                view_height, scope_maximized)) {
                            scope_maximized = !scope_maximized;
                            continue;
                        }
                        if (analog_scope_fit_at(
                                layout_in_force(),
                                event.button.x - pointer_layout.mechanical.x,
                                event.button.y,
                                static_cast<int>(pointer_layout.mechanical.w),
                                view_height, scope_maximized)) {
                            if (fitted_scope_axes)
                                fitted_scope_axes.reset();
                            else
                                fit_scope_axes_requested = true;
                            continue;
                        }
                        const int selected_group = analog_scope_group_at(
                            layout_in_force(),
                            event.button.x - pointer_layout.mechanical.x,
                            event.button.y,
                            static_cast<int>(pointer_layout.mechanical.w),
                            view_height, scope_maximized);
                        if (selected_group >= 0) {
                            analog_group = selected_group;
                            fitted_scope_axes.reset();
                            trigger_channel = 0;
                            trigger_event_source = -1;
                            trigger_armed_tick = displayed.tick;
                            normal_capture = {};
                            const auto &spec =
                                analog_scope_instrument(analog_group, 0);
                            trigger_level = (spec.minimum + spec.maximum) * 0.5;
                            if (trigger_latched) {
                                analog_frozen = false;
                                trigger_latched = false;
                            }
                            continue;
                        }
                    }
                    if (analog_scope && event.button.clicks >= 2 &&
                        analog_scope_tick_at(
                            layout_in_force(),
                            event.button.x - pointer_layout.mechanical.x,
                            event.button.y,
                            static_cast<int>(pointer_layout.mechanical.w),
                            view_height, analog_scope_end_tick,
                            analog_span_ticks, scope_maximized)) {
                        analog_span_ticks = 5LL * 990000;
                        analog_navigation_end_tick.reset();
                        analog_frozen = trigger_latched = false;
                        scope_cursor_ticks = {-1, -1};
                        trigger_armed_tick = displayed.tick;
                        normal_capture = {};
                        continue;
                    }
                    if (!analog_scope && event.button.clicks >= 2 &&
                        digital_scope_tick_at(
                            layout_in_force(),
                            event.button.x - pointer_layout.mechanical.x,
                            event.button.y,
                            static_cast<int>(pointer_layout.mechanical.w),
                            view_height,
                            digital_frozen ? frozen_digital_tick
                                           : displayed.tick,
                            scope_span_ticks)) {
                        scope_span_ticks = 1980000LL;
                        digital_frozen = false;
                        digital_cursors = {};
                        continue;
                    }
                    const SDL_FRect view_selector = view_selector_rect(
                        layout_state, view_width, view_height);
                    const SDL_FRect fit_button =
                        fit_button_rect(layout_state, view_width, view_height);
                    const SDL_FRect fullscreen = fullscreen_button_rect(
                        layout_state, view_width, view_height);
                    const float click_ui_scale =
                        lab_ui_scale(view_width, view_height);
                    const float click_scene_w =
                        layout_for(layout_state, view_width, view_height)
                            .instruments.x;
                    const float click_panel_w =
                        std::min(static_cast<float>(view_width) - 32.0f,
                                 click_scene_w - 32.0f);
                    const float click_help_x =
                        16.0f + click_panel_w - 75.0f * click_ui_scale;
                    const float click_debug_x =
                        click_help_x - 85.0f * click_ui_scale;
                    if (event.button.y >= 16.0f &&
                        event.button.y <= 42.0f * click_ui_scale) {
                        if (event.button.x >= click_help_x &&
                            event.button.x <= 16.0f + click_panel_w) {
                            show_help = !show_help;
                            continue;
                        }
                        if (event.button.x >= click_debug_x &&
                            event.button.x < click_help_x) {
                            show_debug = !show_debug;
                            continue;
                        }
                    }
                    if (view_width >= 1280 && view_height >= 720 &&
                        event.button.x >= fullscreen.x &&
                        event.button.x < fullscreen.x + fullscreen.w &&
                        event.button.y >= fullscreen.y &&
                        event.button.y < fullscreen.y + fullscreen.h) {
                        toggle_fullscreen();
                        continue;
                    }
                    if (lab_buttons_visible(view_width, view_height) &&
                        event.button.x >= fit_button.x &&
                        event.button.x < fit_button.x + fit_button.w &&
                        event.button.y >= fit_button.y &&
                        event.button.y < fit_button.y + fit_button.h) {
                        std::fprintf(
                            stderr,
                            "[LAB-VIEW-FIT] zoom_before=%.3f tick=%lld\n",
                            static_cast<double>(camera.zoom), displayed.tick);
                        reset_cameras();
                        continue;
                    }
                    if (lab_buttons_visible(view_width, view_height) &&
                        event.button.x >= view_selector.x &&
                        event.button.x < view_selector.x + view_selector.w &&
                        event.button.y >= view_selector.y &&
                        event.button.y < view_selector.y + view_selector.h) {
                        view_mode = (view_mode + 1) % 4;
                        continue;
                    }
                    if (session && !replay_controls) {
                        const int step = gear_widget_step(
                            layout_state, event.button.x, event.button.y,
                            view_width, view_height);
                        if (step != 0) {
                            selected_gear = std::clamp(
                                selected_gear + step,
                                displayed.drivetrain_available ? -1 : 0, 5);
                            if (displayed.drivetrain_available)
                                session->set_gear(selected_gear);
                            continue;
                        }
                    }
                    const auto action = hit_test_lab_button(
                        event.button.x, event.button.y, view_width, view_height,
                        pointer_layout.left.w);
                    if (action == LabButtonAction::Starter) {
                        if (session && !replay_controls) {
                            mouse_starter_held = true;
                            SDL_CaptureMouse(true);
                            session->set_starter(true);
                        }
                    } else if (action == LabButtonAction::Load && session &&
                               !replay_controls) {
                        load_dragging = true;
                        set_load_from_pointer(event.button.x, view_width,
                                              view_height);
                    } else if (action == LabButtonAction::None) {
                        const SDL_FRect pedal_slider = pedal_slider_rect(
                            layout_state, view_width, view_height);
                        const SDL_FRect volume_slider = volume_slider_rect(
                            layout_state, view_width, view_height);
                        if (session && !replay_controls &&
                            lab_buttons_visible(view_width, view_height) &&
                            event.button.x >= pedal_slider.x &&
                            event.button.x < pedal_slider.x + pedal_slider.w &&
                            event.button.y >= pedal_slider.y &&
                            event.button.y < pedal_slider.y + pedal_slider.h) {
                            pedal_dragging = true;
                            set_pedal_from_pointer(event.button.x, view_width,
                                                   view_height);
                        } else if (audio_stream &&
                                   lab_buttons_visible(view_width,
                                                       view_height) &&
                                   event.button.x >= volume_slider.x &&
                                   event.button.x <
                                       volume_slider.x + volume_slider.w &&
                                   event.button.y >= volume_slider.y &&
                                   event.button.y <
                                       volume_slider.y + volume_slider.h) {
                            volume_dragging = true;
                            set_volume_from_pointer(event.button.x, view_width,
                                                    view_height);
                        } else {
                            const float scope_x =
                                event.button.x - pointer_layout.mechanical.x;
                            const int scope_w =
                                static_cast<int>(pointer_layout.mechanical.w);
                            if (analog_scope) {
                                const auto tick = analog_scope_tick_at(
                                    layout_in_force(), scope_x, event.button.y,
                                    scope_w, view_height, analog_scope_end_tick,
                                    analog_span_ticks, scope_maximized);
                                if (tick)
                                    scope_cursor_ticks[0] = *tick;
                            } else {
                                const int channel = scope_channel_at(
                                    layout_in_force(), scope_x, event.button.y,
                                    scope_w, view_height);
                                if (channel >= 0)
                                    scope_channels_visible
                                        [static_cast<std::size_t>(channel)] ^=
                                        true;
                                else
                                    digital_cursors[0] = click_digital_cursor(
                                        scope_x, event.button.y, scope_w,
                                        view_height, digital_frozen,
                                        frozen_digital_tick,
                                        frozen_digital_events,
                                        frozen_digital_history);
                            }
                        }
                    } else {
                        activate_button(action);
                    }
                }
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN &&
                event.button.button == SDL_BUTTON_RIGHT) {
                int view_width = 0;
                int view_height = 0;
                if (render_layout_size(screen, &view_width, &view_height)) {
                    const LabLayout pointer_layout = layout_for(
                        layout_state, view_width, view_height, scope_maximized);
                    const float scope_x =
                        event.button.x - pointer_layout.mechanical.x;
                    const int scope_w =
                        static_cast<int>(pointer_layout.mechanical.w);
                    if (analog_scope) {
                        const auto tick = analog_scope_tick_at(
                            layout_in_force(), scope_x, event.button.y, scope_w,
                            view_height, analog_scope_end_tick,
                            analog_span_ticks, scope_maximized);
                        if (tick)
                            scope_cursor_ticks[1] = *tick;
                    } else
                        digital_cursors[1] = click_digital_cursor(
                            scope_x, event.button.y, scope_w, view_height,
                            digital_frozen, frozen_digital_tick,
                            frozen_digital_events, frozen_digital_history);
                }
            }
            if (session && event.type == SDL_EVENT_MOUSE_BUTTON_UP &&
                event.button.button == SDL_BUTTON_LEFT && mouse_starter_held) {
                mouse_starter_held = false;
                SDL_CaptureMouse(false);
                session->set_starter(keyboard_starter_held);
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_UP &&
                event.button.button == SDL_BUTTON_LEFT) {
                if (layout_divider_dragging) {
                    ui_preferences.left_fraction = layout_state.left_fraction;
                    ui_preferences.right_fraction = layout_state.right_fraction;
                    ui_preferences.scope_fraction = layout_state.scope_fraction;
                    const bool saved =
                        frame_limit <= 0 && save_ui_preferences(ui_preferences);
                    std::fprintf(
                        stdout,
                        "[LAB-LAYOUT] left=%.3f right=%.3f scope=%.3f "
                        "saved=%d\n",
                        static_cast<double>(layout_state.left_fraction),
                        static_cast<double>(layout_state.right_fraction),
                        static_cast<double>(layout_state.scope_fraction),
                        saved ? 1 : 0);
                    SDL_CaptureMouse(false);
                    layout_divider_dragging = 0;
                }
                pedal_dragging = false;
                load_dragging = false;
                volume_dragging = false;
            }
            if (session && event.type == SDL_EVENT_WINDOW_FOCUS_LOST &&
                (mouse_starter_held || keyboard_starter_held)) {
                mouse_starter_held = false;
                keyboard_starter_held = false;
                SDL_CaptureMouse(false);
                session->set_starter(false);
            }
            if (event.type == SDL_EVENT_WINDOW_FOCUS_LOST) {
                if (layout_divider_dragging)
                    SDL_CaptureMouse(false);
                layout_divider_dragging = 0;
                pedal_dragging = false;
                load_dragging = false;
                volume_dragging = false;
            }
            if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_R)
                reset_cameras();
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.key == SDLK_V)
                view_mode = (view_mode + 1) % 4;
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                event.key.key == SDLK_H)
                show_help = !show_help;
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                event.key.key == SDLK_D)
                show_debug = !show_debug;
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                event.key.key == SDLK_A)
                analog_scope = !analog_scope;
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                event.key.key == SDLK_Z) {
                analog_scope = true;
                scope_maximized = !scope_maximized;
            }
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                event.key.key == SDLK_G) {
                analog_group = (analog_group + 1) % 11;
                fitted_scope_axes.reset();
                analog_scope = true;
                trigger_channel = 0;
                trigger_event_source = -1;
                trigger_armed_tick = displayed.tick;
                normal_capture = {};
                const auto &spec = analog_scope_instrument(analog_group, 0);
                trigger_level = (spec.minimum + spec.maximum) * 0.5;
                if (trigger_latched) {
                    analog_frozen = false;
                    trigger_latched = false;
                }
            }
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                event.key.key == SDLK_O && analog_scope) {
                if (fitted_scope_axes)
                    fitted_scope_axes.reset();
                else
                    fit_scope_axes_requested = true;
            }
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) && analog_scope) {
                bool changed_trigger = true;
                switch (event.key.key) {
                case SDLK_T:
                    trigger_mode = static_cast<TriggerMode>(
                        (static_cast<int>(trigger_mode) + 1) % 4);
                    break;
                case SDLK_U:
                    if (trigger_event_source >= 0) {
                        if (trigger_event_source == 4) {
                            trigger_event_source = -1;
                            trigger_channel = 0;
                        } else {
                            ++trigger_event_source;
                        }
                    } else if (trigger_channel + 1 <
                               analog_scope_signal_count(analog_group)) {
                        ++trigger_channel;
                    } else {
                        trigger_event_source = 0;
                    }
                    if (trigger_event_source < 0) {
                        const auto &spec = analog_scope_instrument(
                            analog_group, trigger_channel);
                        trigger_level = (spec.minimum + spec.maximum) * 0.5;
                    }
                    break;
                case SDLK_Y:
                    trigger_slope = trigger_slope == TriggerSlope::Rising
                                        ? TriggerSlope::Falling
                                        : TriggerSlope::Rising;
                    break;
                case SDLK_I:
                case SDLK_J: {
                    if (trigger_event_source >= 0) {
                        changed_trigger = false;
                        break;
                    }
                    const auto &spec =
                        analog_scope_instrument(analog_group, trigger_channel);
                    const double step = (spec.maximum - spec.minimum) / 20.0;
                    trigger_level =
                        std::clamp(trigger_level +
                                       (event.key.key == SDLK_I ? step : -step),
                                   spec.minimum, spec.maximum);
                    break;
                }
                case SDLK_B:
                    trigger_pre_fraction = trigger_pre_fraction == 0.10 ? 0.25
                                           : trigger_pre_fraction == 0.25
                                               ? 0.50
                                               : 0.10;
                    break;
                default:
                    changed_trigger = false;
                }
                if (changed_trigger && trigger_latched) {
                    analog_frozen = false;
                    trigger_latched = false;
                }
                if (changed_trigger) {
                    analog_navigation_end_tick.reset();
                    trigger_armed_tick = displayed.tick;
                    normal_capture = {};
                    std::fprintf(
                        stdout,
                        "[LAB-TRIGGER] mode=%d group=%d channel=%zu source=%d "
                        "level=%.3f slope=%c pre=%.2f armed=%lld\n",
                        static_cast<int>(trigger_mode), analog_group,
                        trigger_channel, trigger_event_source, trigger_level,
                        trigger_slope == TriggerSlope::Rising ? '+' : '-',
                        trigger_pre_fraction, trigger_armed_tick);
                }
            }
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                event.key.key == SDLK_X) {
                if (!analog_scope) {
                    if (digital_frozen) {
                        digital_frozen = false;
                        std::fprintf(
                            stdout,
                            "[LAB-SCOPE-FREEZE] mode=digital live=%lld\n",
                            displayed.tick);
                    } else if (displayed.tick > 0) {
                        capture_digital_window();
                        std::fprintf(
                            stdout,
                            "[LAB-SCOPE-FREEZE] mode=digital end=%lld\n",
                            frozen_digital_tick);
                    }
                } else if (analog_navigation_end_tick) {
                    analog_navigation_end_tick.reset();
                } else if (!analog_frozen && displayed.tick > 0 &&
                           !analog_history.empty()) {
                    frozen_scope_snapshot = analog_scope_displayed;
                    frozen_scope_end_tick = analog_scope_end_tick;
                    analog_frozen = true;
                } else if (analog_frozen) {
                    analog_frozen = false;
                    trigger_latched = false;
                    trigger_armed_tick = displayed.tick;
                    normal_capture = {};
                }
            }
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                event.key.key == SDLK_C) {
                scope_csv_requested = true;
                std::fprintf(stdout, "[LAB-SCOPE-REQUEST] tick=%lld group=%d\n",
                             displayed.tick, analog_scope ? analog_group : -1);
            }
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                (event.key.key == SDLK_F || event.key.key == SDLK_F11))
                toggle_fullscreen();
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                event.key.key == SDLK_F12) {
                std::fprintf(stdout,
                             "[LAB-KEY] F12 received! displayed.tick=%lld\n",
                             displayed.tick);
                std::fflush(stdout);
                manual_capture_requested = true;
            }
            if (session && event.type == SDL_EVENT_KEY_DOWN &&
                !event.key.repeat) {
                if (event.key.key == SDLK_SPACE) {
                    std::fprintf(stdout,
                                 "[LAB-KEY] SPACE received! session->paused=%d "
                                 "displayed.tick=%lld\n",
                                 session->paused(), displayed.tick);
                    std::fflush(stdout);
                    activate_button(LabButtonAction::Pause);
                } else if (event.key.key == SDLK_PERIOD)
                    session->step_time(std::chrono::milliseconds(10));
                else if (event.key.key == SDLK_COMMA)
                    session->step_until_event(
                        ma17::EmulatorEventType::IgnitionPin, 990000);
                else if (event.key.key == SDLK_EQUALS ||
                         event.key.key == SDLK_PLUS)
                    activate_button(LabButtonAction::Faster);
                else if (event.key.key == SDLK_MINUS)
                    activate_button(LabButtonAction::Slower);
                else if (event.key.key == SDLK_UP)
                    activate_button(LabButtonAction::PedalUp);
                else if (event.key.key == SDLK_DOWN)
                    activate_button(LabButtonAction::PedalDown);
                else if (event.key.key == SDLK_L)
                    activate_button(LabButtonAction::Load);
                else if (!replay_controls &&
                         (event.key.key == SDLK_Q || event.key.key == SDLK_E)) {
                    selected_gear = std::clamp(
                        selected_gear + (event.key.key == SDLK_E ? 1 : -1),
                        displayed.drivetrain_available ? -1 : 0, 5);
                    if (displayed.drivetrain_available)
                        session->set_gear(selected_gear);
                } else if (!replay_controls &&
                           (event.key.key == SDLK_PAGEUP ||
                            event.key.key == SDLK_PAGEDOWN)) {
                    if (displayed.drivetrain_available) {
                        requested_clutch_pressure = std::clamp(
                            requested_clutch_pressure.value_or(
                                displayed.clutch_pressure) +
                                (event.key.key == SDLK_PAGEUP ? 0.1 : -0.1),
                            0.0, 1.0);
                        session->set_clutch_pressure(
                            *requested_clutch_pressure);
                    } else {
                        road_speed_target_kmh = std::clamp(
                            road_speed_target_kmh +
                                (event.key.key == SDLK_PAGEUP ? 10.0 : -10.0),
                            0.0, 200.0);
                        session->set_vehicle_speed(road_speed_target_kmh);
                    }
                } else if (!replay_controls && event.key.key == SDLK_S) {
                    keyboard_starter_held = true;
                    session->set_starter(true);
                } else if (event.key.key == SDLK_K)
                    activate_button(LabButtonAction::Key);
                else if (event.key.key == SDLK_M)
                    activate_button(LabButtonAction::Mute);
                else if (event.key.key == SDLK_LEFTBRACKET ||
                         event.key.key == SDLK_RIGHTBRACKET) {
                    const float step =
                        event.key.key == SDLK_RIGHTBRACKET ? 0.1f : -0.1f;
                    sound_volume = std::clamp(sound_volume + step, 0.0f, 1.0f);
                    if (audio_stream && !sound_muted)
                        SDL_SetAudioStreamGain(audio_stream, sound_volume);
                }
            }
            if (session && !replay_controls && event.type == SDL_EVENT_KEY_UP &&
                event.key.key == SDLK_S && keyboard_starter_held) {
                keyboard_starter_held = false;
                session->set_starter(mouse_starter_held);
            }
        }
        if (session && session->latest(displayed)) {
            if (!captured) {
                ma17::EmulatorSnapshot target_snapshot;
                if (session->capture_snapshot(target_snapshot))
                    displayed = target_snapshot;
            }
            if (!pedal_user_override) {
                pedal_pull_m = displayed.pedal_pull_m;
                pedal_applied_m = pedal_pull_m;
            }
            if (!load_user_override)
                load_nm = displayed.applied_load_nm;
        }
        EventWindow event_window;
        if (session)
            event_window = session->event_window();
        else if (captured_events)
            event_window.events = *captured_events;
        const auto &events = event_window.events;
        if (!analog_scope && !digital_frozen) {
            const long long first_history_tick =
                std::max(0LL, displayed.tick - scope_span_ticks - 247500LL);
            digital_history =
                session ? session->snapshot_window(first_history_tick)
                        : std::vector<ma17::EmulatorSnapshot>{displayed};
        }
        const auto &digital_events =
            digital_frozen ? frozen_digital_events : events;
        const auto &digital_scope_history =
            digital_frozen ? frozen_digital_history : digital_history;
        const long long digital_scope_end_tick =
            digital_frozen ? frozen_digital_tick : displayed.tick;
        if (analog_scope && !analog_frozen) {
            const long long retention = trigger_mode == TriggerMode::Off
                                            ? analog_span_ticks
                                            : 2LL * analog_span_ticks;
            const long long first_history_tick =
                analog_navigation_end_tick
                    ? std::max(0LL, *analog_navigation_end_tick -
                                        analog_span_ticks - 247500LL)
                    : displayed.tick - retention;
            analog_history =
                session ? session->snapshot_window(first_history_tick)
                        : std::vector<ma17::EmulatorSnapshot>{displayed};
        }
        analog_scope_displayed =
            analog_frozen ? frozen_scope_snapshot : displayed;
        analog_scope_end_tick =
            analog_frozen ? frozen_scope_end_tick
                          : analog_navigation_end_tick.value_or(displayed.tick);
        if (analog_navigation_end_tick && !analog_history.empty()) {
            const auto after = std::upper_bound(
                analog_history.begin(), analog_history.end(),
                analog_scope_end_tick,
                [](long long tick, const ma17::EmulatorSnapshot &sample) {
                    return tick < sample.tick;
                });
            if (after != analog_history.begin())
                analog_scope_displayed = *std::prev(after);
        }
        trigger_waiting = false;
        if (!analog_frozen)
            active_trigger_tick = -1;
        if (analog_scope && !analog_frozen && !analog_navigation_end_tick &&
            trigger_mode != TriggerMode::Off && !analog_history.empty()) {
            const TriggerSearchWindow search =
                trigger_search_window(analog_span_ticks, trigger_pre_fraction,
                                      analog_history.front().tick,
                                      displayed.tick, trigger_armed_tick);
            const long long pre_ticks = search.pre_ticks;
            const long long post_ticks = search.post_ticks;
            const long long first_candidate = search.first_candidate;
            const long long last_candidate = search.last_candidate;
            const auto occurrence = trigger_mode == TriggerMode::Single
                                        ? TriggerOccurrence::First
                                        : TriggerOccurrence::Latest;
            std::optional<long long> crossing;
            if (trigger_event_source >= 0)
                crossing = find_event_trigger(
                    events,
                    static_cast<EventTriggerSource>(trigger_event_source),
                    trigger_slope, first_candidate, last_candidate, occurrence);
            else
                crossing = find_analog_trigger(
                    analog_history,
                    [&](const ma17::EmulatorSnapshot &sample) {
                        return analog_scope_value(sample, analog_group,
                                                  trigger_channel);
                    },
                    trigger_level, trigger_slope, first_candidate,
                    last_candidate, 247500, occurrence);
            if (crossing) {
                active_trigger_tick = *crossing;
                analog_scope_end_tick = *crossing + post_ticks;
                const auto after = std::upper_bound(
                    analog_history.begin(), analog_history.end(),
                    analog_scope_end_tick,
                    [](long long tick, const ma17::EmulatorSnapshot &sample) {
                        return tick < sample.tick;
                    });
                if (after != analog_history.begin())
                    analog_scope_displayed = *std::prev(after);
                if (trigger_mode == TriggerMode::Normal &&
                    (normal_capture.armed_tick != trigger_armed_tick ||
                     normal_capture.trigger_tick != *crossing ||
                     normal_capture.span != analog_span_ticks)) {
                    normal_capture = {
                        trigger_armed_tick,     *crossing,
                        analog_span_ticks,      analog_scope_end_tick,
                        analog_scope_displayed, analog_history};
                }
                if (trigger_mode == TriggerMode::Single) {
                    frozen_scope_snapshot = analog_scope_displayed;
                    frozen_scope_end_tick = analog_scope_end_tick;
                    trigger_latched = analog_frozen = true;
                    std::fprintf(
                        stdout,
                        "[LAB-TRIGGER] single tick=%lld end=%lld group=%d "
                        "channel=%zu source=%d span=%lld pre=%lld "
                        "history_first=%lld available_end=%lld\n",
                        *crossing, analog_scope_end_tick, analog_group,
                        trigger_channel, trigger_event_source,
                        analog_span_ticks, pre_ticks,
                        analog_history.front().tick, displayed.tick);
                }
            } else {
                trigger_waiting = trigger_mode != TriggerMode::Auto;
                if (trigger_mode == TriggerMode::Normal) {
                    const bool retained =
                        normal_capture.armed_tick == trigger_armed_tick &&
                        normal_capture.span == analog_span_ticks;
                    if (retained) {
                        analog_history = normal_capture.history;
                        analog_scope_displayed = normal_capture.snapshot;
                        analog_scope_end_tick = normal_capture.end;
                        active_trigger_tick = normal_capture.trigger_tick;
                    } else {
                        analog_history.clear();
                    }
                }
            }
        }
        if (trigger_waiting && !last_trigger_waiting)
            std::fprintf(stdout,
                         "[LAB-TRIGGER] waiting group=%d channel=%zu "
                         "level=%.3f source=%d shown_samples=%zu\n",
                         analog_group, trigger_channel, trigger_level,
                         trigger_event_source, analog_history.size());
        last_trigger_waiting = trigger_waiting;
        const Uint64 frame_ticks = SDL_GetTicks();
        const int applied_gear = displayed.drivetrain_available
                                     ? displayed.transmission_gear
                                     : selected_gear;
        if (displayed.tick != last_snapshot_tick) {
            last_snapshot_tick = displayed.tick;
            last_snapshot_wall_ms = frame_ticks;
        }
        const bool stale_snapshot =
            session && captured && !session->finished() && !session->paused() &&
            frame_ticks - last_snapshot_wall_ms > 1500;
        const float frame_dt =
            static_cast<float>(frame_ticks - last_frame_ticks) / 1000.0f;
        last_frame_ticks = frame_ticks;
        const long long pedal_elapsed_ticks =
            std::max(0LL, displayed.tick - last_pedal_tick);
        last_pedal_tick = displayed.tick;
        if (session && pedal_user_override && !replay_controls &&
            !session->paused()) {
            // Limit each command as well as the cable speed: a sudden pedal
            // step can trigger the ROM's transient fault with the contact open.
            const double step_m = std::min(
                0.0005,
                0.016 * static_cast<double>(pedal_elapsed_ticks) / 990000.0);
            const double change_m =
                std::clamp(pedal_pull_m - pedal_applied_m, -step_m, step_m);
            if (std::abs(change_m) > 1e-9) {
                pedal_applied_m += change_m;
                session->set_pedal(pedal_applied_m);
            }
        }
        gauges[0].m_value = static_cast<float>(displayed.rpm);
        gauges[1].m_value =
            static_cast<float>(displayed.throttle_angle_rad * 57.2958);
        gauges[2].m_value = static_cast<float>(displayed.lambda);
        for (auto &gauge : gauges)
            gauge.update(frame_dt);
        int width = 0;
        int height = 0;
        if (!render_layout_size(screen, &width, &height) || width <= 0 ||
            height <= 0) {
            running = false;
            break;
        }
        char title[288];
        char clutch_label[24] = "CLUTCH --";
        if (displayed.drivetrain_available)
            std::snprintf(clutch_label, sizeof(clutch_label), "CLUTCH %.0f%%",
                          displayed.clutch_pressure * 100.0);
        constexpr std::array<const char *, 4> view_names{
            "SHAFT", "RADIAL", "AXIAL 1/4", "AXIAL 2/3"};
        constexpr std::array<const char *, 11> scope_names{
            "LAMBDA",      "TPS",     "THERMAL", "INTAKE",
            "ENGINE",      "FUEL",    "ADC TPS", "ADC BAT/LAMBDA",
            "ADC IAT/ECT", "BATTERY", "IDLE"};
        const bool radial_view = view_mode != 0;
        const int focus_cylinder = view_mode >= 2 ? view_mode - 1 : 0;
        char rpm_label[24];
        if (displayed.crank_available && std::isfinite(displayed.rpm))
            std::snprintf(rpm_label, sizeof(rpm_label), "%.0f rpm",
                          displayed.rpm);
        else
            std::snprintf(rpm_label, sizeof(rpm_label), "-- rpm");
        std::snprintf(
            title, sizeof(title),
            "%s | %s | %s SCOPE%s | %s @%lld | %s | GEAR %c | %s | RAM47=%u | "
            "tick %lld | "
            "V view, K key, S starter, arrows pedal, Q/E gear, L load, "
            "Space pause, . 10ms, , next ignition",
            profile::vehicle, view_names[static_cast<std::size_t>(view_mode)],
            analog_scope ? scope_names[static_cast<std::size_t>(analog_group)]
                         : "ECU",
            analog_scope && scope_maximized ? " MAX" : "",
            (analog_scope && analog_frozen) || (!analog_scope && digital_frozen)
                ? "FROZEN"
                : "LIVE",
            analog_scope && analog_frozen     ? frozen_scope_snapshot.tick
            : !analog_scope && digital_frozen ? frozen_digital_tick
                                              : displayed.tick,
            rpm_label,
            applied_gear == -1  ? 'R'
            : applied_gear == 0 ? 'N'
                                : static_cast<char>('0' + applied_gear),
            clutch_label, static_cast<unsigned>(displayed.ram47),
            displayed.tick);
        SDL_SetWindowTitle(window, title);
        RecordingRenderer geometry;
        const LabLayout layout = layout_for(layout_state, width, height,
                                            analog_scope && scope_maximized);
        const float scene_x = layout.mechanical.x;
        const float scene_width = layout.mechanical.w;
        const float scene_height = layout.mechanical.h;
        const float pane_width = scene_width * 0.5f;
        const float ui_scale = lab_ui_scale(width, height);
        camera.pan_x =
            std::clamp(camera.pan_x, -scene_width * 0.5f, scene_width * 0.5f);
        camera.pan_y =
            std::clamp(camera.pan_y, -scene_height * 0.5f, scene_height * 0.5f);
        axial_camera.pan_x = std::clamp(axial_camera.pan_x, -scene_width * 0.5f,
                                        scene_width * 0.5f);
        axial_camera.pan_y = std::clamp(
            axial_camera.pan_y, -scene_height * 0.5f, scene_height * 0.5f);
        const bool compact_view = width < 1100;
        const float fit_top =
            (compact_view
                 ? (height < 620 ? (width < 900 ? 166.0f : 150.0f) : 130.0f)
                 : 108.0f) *
            ui_scale;
        float fit_bottom = scene_height - 16.0f * ui_scale;
        if (compact_view && height >= 620 && lab_buttons_visible(width, height))
            fit_bottom = std::min(fit_bottom,
                                  lab_button_rect(0, width, height).y - 12.0f);
        const bool viewport_changed = fitted_scene_height != scene_height ||
                                      fitted_pane_width != pane_width;
        if (fit_bottom > fit_top + 40.0f &&
            (viewport_changed || fitted_focus != focus_cylinder)) {
            const float fit_width = compact_view ? 0.72f : 0.80f;
            const SDL_FRect target{pane_width * (1.0f - fit_width) * 0.5f,
                                   fit_top, pane_width * fit_width,
                                   fit_bottom - fit_top};
            if (viewport_changed)
                fit_scene_camera(
                    camera, displayed, pane_width, scene_height, target,
                    [&](RecordingRenderer &probe,
                        const ma17::EmulatorSnapshot &sample,
                        SceneCamera candidate) {
                        render_sevel_scene_donor(probe, sample, pane_width,
                                                 scene_height, {}, {},
                                                 candidate, &meshes);
                    });
            fit_scene_camera(
                axial_camera, displayed, pane_width, scene_height, target,
                [&](RecordingRenderer &probe,
                    const ma17::EmulatorSnapshot &sample,
                    SceneCamera candidate) {
                    render_sevel_radial_donor(probe, sample, pane_width,
                                              scene_height, meshes, {}, {},
                                              candidate, {}, focus_cylinder);
                });
            fitted_scene_height = scene_height;
            fitted_pane_width = pane_width;
            fitted_focus = focus_cylinder;
            if (restore_camera_pending) {
                const bool compatible_viewport =
                    ui_scale_percent == ui_preferences.scale_percent &&
                    ui_preferences.camera_pane_width > 0.0f &&
                    ui_preferences.camera_scene_height > 0.0f &&
                    std::abs(ui_preferences.camera_pane_width - pane_width) <=
                        pane_width * 0.10f &&
                    std::abs(ui_preferences.camera_scene_height -
                             scene_height) <= scene_height * 0.10f;
                if (compatible_viewport) {
                    camera.zoom = ui_preferences.shaft_zoom;
                    camera.pan_x = ui_preferences.shaft_pan_x * pane_width;
                    camera.pan_y = ui_preferences.shaft_pan_y * scene_height;
                    axial_camera.zoom = ui_preferences.axial_zoom;
                    axial_camera.pan_x =
                        ui_preferences.axial_pan_x * pane_width;
                    axial_camera.pan_y =
                        ui_preferences.axial_pan_y * scene_height;
                }
                restore_camera_pending = false;
                std::fprintf(stdout,
                             "[LAB-CAMERA-PREF] %s view=%d "
                             "shaft=%.3f/%.3f/%.3f axial=%.3f/%.3f/%.3f\n",
                             compatible_viewport ? "restored" : "fitted",
                             view_mode, static_cast<double>(camera.zoom),
                             static_cast<double>(ui_preferences.shaft_pan_x),
                             static_cast<double>(ui_preferences.shaft_pan_y),
                             static_cast<double>(axial_camera.zoom),
                             static_cast<double>(ui_preferences.axial_pan_x),
                             static_cast<double>(ui_preferences.axial_pan_y));
            }
        }
        SceneCamera render_camera = camera;
        SceneCamera radial_camera = axial_camera;
        // Visual afterglow only; electrical pin widths remain in the event
        // trace.
        constexpr long long pulse_span_ticks = 49500;
        constexpr long long spark_span_ticks = 24750;
        std::array<ScenePulse, 4> pulses{};
        std::array<bool, 4> seen{};
        std::array<float, 2> spark_glows{};
        std::array<bool, 2> spark_seen{};
        std::array<float, 2> pin_glows{};
        std::array<bool, 2> pin_seen{};
        std::array<int, 2> spark_channels{-1, -1};
        for (auto it = events.rbegin(); it != events.rend(); ++it) {
            if (it->type == ma17::EmulatorEventType::Spark &&
                it->tick <= displayed.tick && it->pair_index < 2 &&
                it->channel < 2 && spark_channels[it->pair_index] < 0)
                spark_channels[it->pair_index] = static_cast<int>(it->channel);
            if (spark_channels[0] >= 0 && spark_channels[1] >= 0)
                break;
        }
        for (auto it = events.rbegin(); it != events.rend(); ++it) {
            if (it->tick > displayed.tick)
                continue;
            if (displayed.tick - it->tick > pulse_span_ticks)
                break;
            if (it->type == ma17::EmulatorEventType::IgnitionPin) {
                for (std::size_t pair = 0; pair < pin_glows.size(); ++pair) {
                    if (!pin_seen[pair] &&
                        spark_channels[pair] == static_cast<int>(it->channel)) {
                        pin_glows[pair] =
                            1.0f -
                            static_cast<float>(displayed.tick - it->tick) /
                                static_cast<float>(pulse_span_ticks);
                        pin_seen[pair] = true;
                    }
                }
                continue;
            }
            if (it->type == ma17::EmulatorEventType::Spark &&
                it->pair_index < spark_glows.size()) {
                const auto pair = it->pair_index;
                if (!spark_seen[pair] &&
                    displayed.tick - it->tick <= spark_span_ticks) {
                    spark_glows[pair] =
                        1.0f - static_cast<float>(displayed.tick - it->tick) /
                                   static_cast<float>(spark_span_ticks);
                    spark_seen[pair] = true;
                }
                continue;
            }
            if ((it->type != ma17::EmulatorEventType::Combustion &&
                 it->type != ma17::EmulatorEventType::Misfire) ||
                it->cylinder_index >= pulses.size() || seen[it->cylinder_index])
                continue;
            const auto cylinder = it->cylinder_index;
            seen[cylinder] = true;
            pulses[cylinder] = {
                1.0f - static_cast<float>(displayed.tick - it->tick) /
                           static_cast<float>(pulse_span_ticks),
                it->type == ma17::EmulatorEventType::Misfire};
        }
        pulses[0].spark_strength = pulses[3].spark_strength = spark_glows[0];
        pulses[1].spark_strength = pulses[2].spark_strength = spark_glows[1];
        pulses[0].pin_strength = pulses[3].pin_strength = pin_glows[0];
        pulses[1].pin_strength = pulses[2].pin_strength = pin_glows[1];
        RecordingRenderer secondary_geometry;
        if (radial_view) {
            render_sevel_radial_donor(geometry, displayed, pane_width,
                                      scene_height, meshes, {}, {},
                                      radial_camera, pulses, focus_cylinder);
            render_sevel_scene_donor(secondary_geometry, displayed, pane_width,
                                     scene_height, {}, {}, render_camera,
                                     &meshes, pulses);
        } else {
            render_sevel_scene_donor(geometry, displayed, pane_width,
                                     scene_height, {}, {}, render_camera,
                                     &meshes, pulses);
            render_sevel_radial_donor(secondary_geometry, displayed, pane_width,
                                      scene_height, meshes, {}, {},
                                      radial_camera, pulses, 1);
        }
        if (gpu_renderer) {
            int gpu_width = 0;
            int gpu_height = 0;
            if (SDL_GetWindowSizeInPixels(gpu_window, &gpu_width,
                                          &gpu_height) &&
                gpu_width > 0 && gpu_height > 0) {
                SceneCamera gpu_camera =
                    radial_view ? radial_camera : render_camera;
                if (radial_view)
                    render_sevel_radial_donor(
                        *gpu_renderer, displayed, static_cast<float>(gpu_width),
                        static_cast<float>(gpu_height), meshes, {}, {},
                        gpu_camera, pulses, focus_cylinder);
                else
                    render_sevel_scene_donor(*gpu_renderer, displayed,
                                             static_cast<float>(gpu_width),
                                             static_cast<float>(gpu_height), {},
                                             {}, gpu_camera, &meshes, pulses);
                if (!gpu_renderer->failed() && !gpu_capture_attempted &&
                    !captured && displayed.tick >= capture_after_tick) {
                    gpu_capture_attempted = true;
                    save_gpu_scene(*gpu_renderer,
                                   std::filesystem::path(screenshot_path),
                                   displayed.tick);
                    RecordingRenderer same_scene;
                    if (radial_view)
                        render_sevel_radial_donor(
                            same_scene, displayed,
                            static_cast<float>(gpu_width),
                            static_cast<float>(gpu_height), meshes, {}, {},
                            gpu_camera, pulses, focus_cylinder);
                    else
                        render_sevel_scene_donor(same_scene, displayed,
                                                 static_cast<float>(gpu_width),
                                                 static_cast<float>(gpu_height),
                                                 {}, {}, gpu_camera, &meshes,
                                                 pulses);
                    auto sdl_path =
                        gpu_scene_path(std::filesystem::path(screenshot_path));
                    sdl_path.replace_filename(
                        sdl_path.stem().string().substr(
                            0, sdl_path.stem().string().size() - 4) +
                        "-sdlscene" + sdl_path.extension().string());
                    if (save_sdl_scene_equivalent(same_scene, gpu_width,
                                                  gpu_height, sdl_path))
                        std::fprintf(
                            stdout,
                            "[LAB-GPU] sdl_scene_capture=%s tick=%lld\n",
                            sdl_path.string().c_str(), displayed.tick);
                }
                if (gpu_renderer->failed()) {
                    std::fprintf(stderr, "SDL GPU preview stopped: %s\n",
                                 gpu_renderer->lastError());
                    gpu_renderer.reset();
                    SDL_DestroyWindow(gpu_window);
                    gpu_window = nullptr;
                }
            }
        }
        SDL_SetRenderDrawColor(screen, 10, 10, 12, 255);
        SDL_RenderClear(screen);
        scene_vertices.clear();
        bool geometry_ok = true;
        const auto flush_geometry = [&] {
            if (!scene_vertices.empty() &&
                !SDL_RenderGeometry(screen, nullptr, scene_vertices.data(),
                                    static_cast<int>(scene_vertices.size()),
                                    nullptr, 0))
                geometry_ok = false;
            scene_vertices.clear();
        };
        const std::array<RecordingRenderer *, 2> views{&geometry,
                                                       &secondary_geometry};
        // Scene colors keep their alpha; blend like the donor GPU pipeline.
        SDL_BlendMode previous_blend = SDL_BLENDMODE_NONE;
        SDL_GetRenderDrawBlendMode(screen, &previous_blend);
        SDL_SetRenderDrawBlendMode(screen, kSceneBlendMode);
        for (std::size_t view = 0; view < views.size(); ++view) {
            const float offset_x =
                scene_x + pane_width * static_cast<float>(view);
            const PixelSpan span = pixel_span(offset_x, pane_width);
            const SDL_Rect clip{span.x, 0, span.w,
                                static_cast<int>(std::lround(scene_height))};
            SDL_SetRenderClipRect(screen, &clip);
            views[view]->for_each_triangle(
                [&](const auto &points, const ysVector &color) {
                    if (!geometry_ok)
                        return;
                    for (const auto &point : points) {
                        SDL_Vertex vertex{};
                        vertex.position = {offset_x + point.x, point.y};
                        vertex.color = scene_fcolor(color);
                        scene_vertices.push_back(vertex);
                    }
                    if (scene_vertices.size() == scene_batch_vertices)
                        flush_geometry();
                });
            if (geometry_ok)
                flush_geometry();
        }
        SDL_SetRenderClipRect(screen, nullptr);
        SDL_SetRenderDrawBlendMode(screen, previous_blend);
        if (!geometry_ok) {
            std::fprintf(stderr, "SDL scene geometry: %s\n", SDL_GetError());
            running = false;
            continue;
        }
        const bool compact_overlay = width < 1100 || height < 690;
        const float status_panel_h =
            (compact_overlay ? 44.0f : 52.0f) * ui_scale;
        const SDL_FRect status_panel{
            16.0f, 16.0f,
            std::min(static_cast<float>(width) - 32.0f,
                     layout.left.w + scene_width - 32.0f),
            status_panel_h};
        SDL_SetRenderDrawColor(screen, 20, 20, 24, 255);
        SDL_RenderFillRect(screen, &status_panel);
        SDL_SetRenderDrawColor(screen, 45, 45, 55, 255);
        SDL_RenderRect(screen, &status_panel);
        const SDL_Rect shaft_viewport{
            static_cast<int>(scene_x) +
                (radial_view ? static_cast<int>(pane_width) : 0),
            0, static_cast<int>(pane_width), static_cast<int>(scene_height)};
        SDL_SetRenderViewport(screen, &shaft_viewport);
        draw_shaft_mechanical_details(screen, displayed, render_camera,
                                      pane_width, scene_height, ui_scale);
        SDL_SetRenderViewport(screen, nullptr);
        SDL_SetRenderDrawColor(screen, 55, 60, 68, 255);
        SDL_RenderLine(screen, scene_x + pane_width, 92.0f * ui_scale,
                       scene_x + pane_width, scene_height);
        const float scene_label_y =
            (compact_view && height < 620 ? (width < 900 ? 144.0f : 122.0f)
                                          : 94.0f) *
            ui_scale;
        font.draw(screen, scene_x + 14.0f * ui_scale, scene_label_y,
                  radial_view ? "PERFIL / AXIAL" : "LONGITUDINAL / 4 CIL",
                  {176, 218, 226, 255}, 0.72f * ui_scale);
        font.draw(screen, scene_x + pane_width + 14.0f * ui_scale,
                  scene_label_y,
                  radial_view ? "LONGITUDINAL / 4 CIL" : "PERFIL / CIL 1",
                  {176, 218, 226, 255}, 0.72f * ui_scale);
        if (lab_buttons_visible(width, height)) {
            const SDL_FRect selector =
                view_selector_rect(layout_state, width, height);
            SDL_SetRenderDrawColor(screen, radial_view ? 35 : 20,
                                   radial_view ? 50 : 20, radial_view ? 60 : 24,
                                   255);
            SDL_RenderFillRect(screen, &selector);
            SDL_SetRenderDrawColor(screen, 70, 70, 85, 255);
            SDL_RenderRect(screen, &selector);
            const bool compact_selector = width < 1280 || height < 720;
            font.draw(
                screen,
                selector.x +
                    (compact_selector
                         ? (selector.w - font.measure("VIEW") * ui_scale) * 0.5f
                         : 8.0f * ui_scale),
                selector.y + (compact_selector ? 6.0f : 8.0f * ui_scale),
                compact_selector ? "VIEW"
                : view_mode == 0 ? "V: SHAFT"
                : view_mode == 1 ? "V: RADIAL"
                : view_mode == 2 ? "V: 1/4"
                                 : "V: 2/3",
                {145, 177, 190, 255}, ui_scale);
            const SDL_FRect fit_button =
                fit_button_rect(layout_state, width, height);
            SDL_SetRenderDrawColor(screen, 20, 20, 24, 255);
            SDL_RenderFillRect(screen, &fit_button);
            SDL_SetRenderDrawColor(screen, 70, 70, 85, 255);
            SDL_RenderRect(screen, &fit_button);
            const char *fit_label = compact_selector ? "FIT" : "R: FIT";
            font.draw(
                screen,
                fit_button.x +
                    (fit_button.w - font.measure(fit_label) * ui_scale) * 0.5f,
                fit_button.y + (compact_selector ? 6.0f : 8.0f * ui_scale),
                fit_label, {145, 177, 190, 255}, ui_scale);
            if (width >= 1280 && height >= 720) {
                const SDL_FRect fullscreen =
                    fullscreen_button_rect(layout_state, width, height);
                SDL_SetRenderDrawColor(screen, 20, 20, 24, 255);
                SDL_RenderFillRect(screen, &fullscreen);
                SDL_SetRenderDrawColor(screen, 70, 70, 85, 255);
                SDL_RenderRect(screen, &fullscreen);
                font.draw(screen, fullscreen.x + 8.0f * ui_scale,
                          fullscreen.y + 8.0f * ui_scale,
                          (SDL_GetWindowFlags(window) & SDL_WINDOW_FULLSCREEN)
                              ? "F: EXIT"
                              : "F: FULL",
                          {145, 177, 190, 255}, ui_scale);
            }
        }
        if (view_mode == 1 && !compact_view) {
            constexpr std::array<const char *, 4> labels{"CYL 1", "CYL 2",
                                                         "CYL 3", "CYL 4"};
            const SevelVisualGeometry geometry_size{};
            const SceneDimensions scene_size{};
            const float head_y =
                static_cast<float>(geometry_size.visual_estimate_rod_length_m +
                                   SevelVisualGeometry::crank_radius_m +
                                   scene_size.visual_estimate_head_height_m);
            const ysMatrix radial_projection = scene_fit_projection(
                radial_camera, pane_width, scene_height,
                3.0f * visual_estimate_radial_section_spacing_m + 0.14f, 0.34f);
            const float label_y =
                scene_height *
                    (1.0f - radial_projection.m[1][1] * (head_y + 0.07f) -
                     radial_projection.m[1][3]) *
                    0.5f -
                18.0f * ui_scale;
            const float label_pitch =
                std::abs(pane_width * radial_projection.m[0][0] *
                         visual_estimate_radial_section_spacing_m * 0.5f);
            const float label_scale =
                std::min(ui_scale, label_pitch * 0.85f /
                                       std::max(1.0f, font.measure("CYL 4")));
            for (std::size_t cylinder = 0; cylinder < labels.size();
                 ++cylinder) {
                const float center = (static_cast<float>(cylinder) - 1.5f) *
                                     visual_estimate_radial_section_spacing_m;
                const float x =
                    scene_x + pane_width *
                                  (1.0f + radial_projection.m[0][0] * center +
                                   radial_projection.m[0][3]) *
                                  0.5f;
                font.draw(screen,
                          x - font.measure(labels[cylinder]) * label_scale /
                                  2.0f,
                          label_y, labels[cylinder],
                          cylinder == 0 || cylinder == 3
                              ? SDL_Color{99, 211, 220, 255}
                              : SDL_Color{234, 165, 100, 255},
                          label_scale);
            }
        }
        if (focus_cylinder != 0) {
            const char *label = focus_cylinder == 1 ? "AXIAL 1/4  |  CYL 1"
                                                    : "AXIAL 2/3  |  CYL 2";
            font.draw(screen, scene_x + 24.0f * ui_scale,
                      status_panel.y + status_panel.h + 10.0f * ui_scale, label,
                      {176, 218, 226, 255}, ui_scale);
        }
        const SDL_FRect cluster_bounds =
            instrument_cluster_rect(layout_state, width, height);
        draw_oes_right_cluster(screen, font, cluster_bounds, displayed, pulses,
                               spark_glows, ui_scale, &gauges, stale_snapshot,
                               compact_instrument_page, display_units);
        const SDL_FRect left_bounds{8.0f * ui_scale, 90.0f * ui_scale,
                                    layout.left.w - 16.0f * ui_scale,
                                    320.0f * ui_scale};
        draw_oes_left_cluster(screen, font, left_bounds, displayed, ui_scale,
                              stale_snapshot, applied_gear, display_units);
        draw_gear_widget(layout_state, screen, font, width, height,
                         applied_gear, displayed.drivetrain_available);
        const char *sound_state = "on";
        if (!audio_stream || !audio_source)
            sound_state = enable_audio ? "unavailable" : "off";
        else if (sound_muted)
            sound_state = "muted";
        else if (!displayed.key_on)
            sound_state = "key off";
        else if (session && session->paused())
            sound_state = "paused";
        else if (session && session->speed() > 1.0)
            sound_state = "speed";
        else if (audio_source->suspended())
            sound_state = "suspended";
        draw_volume_slider(
            layout_state, screen, font, width, height, sound_volume,
            audio_stream != nullptr, sound_state, show_debug,
            audio_source ? audio_source->recent_pcm_peak() : 0U,
            audio_source ? audio_source->device_need_samples() : 0ULL,
            audio_source ? audio_source->dropped_samples() : 0ULL);
        draw_pedal_slider(layout_state, screen, font, width, height,
                          pedal_pull_m, session && !replay_controls,
                          replay_controls);
        const SDL_Rect scope_viewport{static_cast<int>(scene_x), 0,
                                      static_cast<int>(scene_width), height};
        SDL_SetRenderViewport(screen, &scope_viewport);
        if (analog_scope) {
            if (fit_scope_axes_requested) {
                fitted_scope_axes = fit_analog_scope_axes(
                    analog_history, analog_group,
                    std::max(0LL, analog_scope_end_tick - analog_span_ticks),
                    analog_scope_end_tick, display_units);
                fit_scope_axes_requested = false;
                if (fitted_scope_axes)
                    std::fprintf(
                        stdout,
                        "[LAB-SCOPE-Y] group=%d tick=%lld min=%.6f max=%.6f\n",
                        analog_group, analog_scope_end_tick,
                        (*fitted_scope_axes)[0].minimum,
                        (*fitted_scope_axes)[0].maximum);
            }
            char trigger_status[48] = "T:OFF";
            if (trigger_mode != TriggerMode::Off) {
                const char mode = trigger_mode == TriggerMode::Auto     ? 'A'
                                  : trigger_mode == TriggerMode::Normal ? 'N'
                                                                        : 'S';
                const char *state = trigger_waiting   ? " WAIT"
                                    : trigger_latched ? " HOLD"
                                                      : "";
                const int pre = static_cast<int>(trigger_pre_fraction * 100.0);
                if (trigger_event_source >= 0) {
                    constexpr std::array<const char *, 5> names{
                        "IG0", "IG1", "INJ", "SP14", "SP23"};
                    const bool spark = trigger_event_source >= 3;
                    std::snprintf(
                        trigger_status, sizeof(trigger_status),
                        "T:%c%s %s%c/%d%%", mode, state,
                        names[static_cast<std::size_t>(trigger_event_source)],
                        spark                                   ? ' '
                        : trigger_slope == TriggerSlope::Rising ? '^'
                                                                : 'v',
                        pre);
                } else {
                    std::snprintf(
                        trigger_status, sizeof(trigger_status),
                        "T:%c%s %zu%c%.1f%s/%d%%", mode, state,
                        trigger_channel + 1,
                        trigger_slope == TriggerSlope::Rising ? '^' : 'v',
                        display_value(trigger_level,
                                      analog_scope_instrument(analog_group,
                                                              trigger_channel),
                                      display_units),
                        unit_transform(analog_scope_instrument(analog_group,
                                                               trigger_channel),
                                       display_units)
                            .unit,
                        pre);
                }
            }
            const auto retention = session ? session->snapshot_retention()
                                           : SimSession::SnapshotRetention{};
            draw_lab_analog_scope(
                layout_in_force(), screen, font, static_cast<int>(scene_width),
                height, analog_scope_displayed, analog_history, analog_group,
                analog_span_ticks,
                analog_frozen || analog_navigation_end_tick.has_value() ||
                    (trigger_waiting && trigger_mode == TriggerMode::Normal),
                scope_cursor_ticks, analog_scope_end_tick, active_trigger_tick,
                trigger_status, retention.raw_evicted,
                retention.archive_evicted, scope_maximized, display_units,
                focus_cylinder,
                fitted_scope_axes ? &*fitted_scope_axes : nullptr);
        } else
            draw_lab_scope(
                layout_in_force(), screen, font, static_cast<int>(scene_width),
                height, digital_scope_end_tick, digital_events,
                digital_scope_history, scope_channels_visible, scope_span_ticks,
                digital_cursors, digital_frozen, focus_cylinder);
        SDL_SetRenderViewport(screen, nullptr);
        const float order_scale =
            width >= 2400 && height >= 1000 && width > 2 * height
                ? std::min(ui_scale, 1.2f)
                : ui_scale;
        draw_combustion_order(screen, font, layout.left.w, height, order_scale,
                              pulses, spark_glows, spark_channels,
                              focus_cylinder);
        const std::array<bool, 9> button_selected{
            displayed.key_on,
            keyboard_starter_held || mouse_starter_held,
            false,
            false,
            load_nm > 0.0,
            session && session->paused(),
            session && session->speed() < 1.0,
            session && session->speed() > 1.0,
            sound_muted};
        const bool physical_controls_enabled = session && !replay_controls;
        const std::array<bool, 9> button_enabled{
            physical_controls_enabled, physical_controls_enabled,
            physical_controls_enabled, physical_controls_enabled,
            physical_controls_enabled, session != nullptr,
            session != nullptr,        session != nullptr,
            session != nullptr};
        draw_lab_buttons(layout_state, screen, font, width, height,
                         button_selected, button_enabled, load_nm);
        constexpr std::array<SDL_Color, 7> status_colors{
            {{235, 241, 246, 255},
             {176, 218, 226, 255},
             {241, 198, 126, 255},
             {157, 182, 196, 255},
             {176, 218, 226, 255},
             {157, 182, 196, 255},
             {157, 182, 196, 255}}};
        const SDL_FRect selector =
            view_selector_rect(layout_state, width, height);
        const SDL_FRect debug_panel{
            layout.mechanical.x + 8.0f * ui_scale,
            compact_overlay
                ? std::max(status_panel.y + status_panel.h + 8.0f * ui_scale,
                           (lab_buttons_visible(width, height)
                                ? lab_button_rect(0, width, height).y
                                : layout.mechanical.h) -
                               98.0f * ui_scale)
                : selector.y + selector.h + 8.0f * ui_scale,
            layout.mechanical.w - 16.0f * ui_scale,
            (compact_overlay ? 88.0f : 130.0f) * ui_scale};
        if (show_debug) {
            SDL_SetRenderDrawColor(screen, 20, 25, 31, 248);
            SDL_RenderFillRect(screen, &debug_panel);
            SDL_SetRenderDrawColor(screen, 99, 211, 220, 255);
            SDL_RenderRect(screen, &debug_panel);
            const char *inspector_title =
                stale_snapshot ? "ECU INSPECTOR | STALE | D: CLOSE"
                : bench_preset ? "ECU INSPECTOR | BENCH* | D: CLOSE"
                               : "ECU INSPECTOR | D: CLOSE";
            const float title_width =
                std::max(1.0f, debug_panel.w - 116.0f * ui_scale);
            const float title_scale = std::min(
                ui_scale,
                title_width / std::max(1.0f, font.measure(inspector_title)));
            font.draw(screen, debug_panel.x + 8.0f * ui_scale,
                      debug_panel.y + 4.0f * ui_scale, inspector_title,
                      {99, 211, 220, 255}, title_scale);
        }
        const auto draw_status = [&](int row, const char *line) {
            const bool inspector_row = show_debug && row >= 2;
            const float text_scale =
                inspector_row
                    ? std::min(ui_scale, (debug_panel.w - 16.0f * ui_scale) /
                                             std::max(1.0f, font.measure(line)))
                : row == 1
                    ? std::min(ui_scale,
                               (status_panel.x + status_panel.w - 32.0f) /
                                   std::max(1.0f, font.measure(line)))
                    : ui_scale;
            font.draw(
                screen, inspector_row ? debug_panel.x + 8.0f * ui_scale : 24.0f,
                inspector_row
                    ? debug_panel.y +
                          (22.0f + 20.0f * static_cast<float>(row - 2)) *
                              ui_scale
                    : 24.0f + 16.0f * ui_scale * static_cast<float>(row),
                line, status_colors[static_cast<std::size_t>(row)], text_scale);
        };
        char status[160];
        std::array<std::array<char, 24>, 6> readings{};
        const auto format_reading = [&](std::size_t index, bool available,
                                        double value, int precision) {
            if (available && std::isfinite(value))
                std::snprintf(readings[index].data(), readings[index].size(),
                              "%.*f", precision, value);
            else
                std::snprintf(readings[index].data(), readings[index].size(),
                              "--");
        };
        format_reading(0, displayed.crank_available, displayed.rpm, 0);
        format_reading(
            4, displayed.crank_available && displayed.exhaust_sample_available,
            displayed.lambda, 2);
        format_reading(
            5, displayed.thermal_available,
            display_value(displayed.coolant_c, profile::coolant, display_units),
            1);
        const auto coolant_unit =
            unit_transform(profile::coolant, display_units).unit;
        const char *fan_state = !displayed.thermal_available ? "--"
                                : displayed.radiator_fan_on  ? "ON"
                                                             : "off";
        if (compact_overlay)
            std::snprintf(status, sizeof(status), "%s",
                          width < 800 ? "FIAT TIPO | SEVEL MA1.7"
                                      : "FIAT TIPO 1.6 i.e. | SEVEL MA1.7");
        else
            std::snprintf(status, sizeof(status), "%s | %s", profile::vehicle,
                          profile::engine);
        const char *help_hint = show_help ? "H: CLOSE" : "H: HELP";
        const char *debug_hint = show_debug ? "D: VITAL" : "D: DEBUG";
        const float help_x = status_panel.x + status_panel.w -
                             (font.measure(help_hint) + 12.0f) * ui_scale;
        const float debug_x =
            help_x - (font.measure(debug_hint) + 14.0f) * ui_scale;
        {
            // The title must end before the right-aligned hints, whatever the
            // face: fall back to the short title, then to an ellipsis.
            const float title_px = font.text_px(ui_scale);
            const float title_max = debug_x - 24.0f - 8.0f * ui_scale;
            std::string header_title = status;
            if (font.measure_px(header_title, title_px) > title_max)
                header_title = "FIAT TIPO | SEVEL MA1.7";
            header_title = font.ellipsize(header_title, title_px, title_max);
            draw_status(0, header_title.c_str());
        }
        font.draw(screen, help_x, 24.0f, help_hint, {99, 211, 220, 255},
                  ui_scale);
        font.draw(screen, debug_x, 24.0f, debug_hint,
                  show_debug ? SDL_Color{249, 190, 96, 255}
                             : SDL_Color{99, 211, 220, 255},
                  ui_scale);
        if (!show_debug) {
            const char *layout_name =
                layout_state.mode == LabPresentationMode::Analysis ? "ANALYSIS"
                : layout_state.mode == LabPresentationMode::Mechanics
                    ? "MECHANICS"
                    : "BENCH";
            const char *run_state =
                displayed.simulation_fault ? "SIM FAULT"
                : stale_snapshot           ? "STALE"
                : session && session->paused()
                    ? (replay_controls ? "PAUSED REPLAY" : "PAUSED")
                : replay_controls                ? "REPLAY"
                : session && session->finished() ? "DONE"
                : session                        ? "RUN"
                                                 : "CAPTURE";
            const double sim_seconds =
                static_cast<double>(displayed.tick) / 990000.0;
            if (width < 800)
                std::snprintf(status, sizeof(status),
                              "%s %.2fs | RPM %s | ECT %s%s", run_state,
                              sim_seconds, readings[0].data(),
                              readings[5].data(), coolant_unit);
            else if (compact_overlay)
                std::snprintf(status, sizeof(status),
                              "%s %.2fs | RPM %s ECT %s%s LAM %s FAN %s",
                              run_state, sim_seconds, readings[0].data(),
                              readings[5].data(), coolant_unit,
                              readings[4].data(), fan_state);
            else if (metadata && metadata->present)
                std::snprintf(status, sizeof(status),
                              "%s | %s | %.2f s / TICK %lld | ROM %08llX | KEY "
                              "%s | UI %s",
                              run_state, bench_preset ? "BENCH" : "CLI",
                              sim_seconds, displayed.tick,
                              static_cast<unsigned long long>(
                                  metadata->rom_hash & 0xffffffffULL),
                              displayed.key_on ? "ON" : "off", layout_name);
            else
                std::snprintf(
                    status, sizeof(status),
                    "%s | %.2f s / TICK %lld | ROM N/D | KEY %s | UI %s",
                    run_state, sim_seconds, displayed.tick,
                    displayed.key_on ? "ON" : "off", layout_name);
            draw_status(1, status);
        } else {
            char injector_count[24], burn_count[24];
            char lost_count[24];
            if (session)
                std::snprintf(lost_count, sizeof(lost_count), "%llu",
                              session->event_overflow());
            else
                std::snprintf(lost_count, sizeof(lost_count), "--");
            if (displayed.injector_available)
                std::snprintf(injector_count, sizeof(injector_count), "%llu",
                              displayed.injector_pulses);
            else
                std::snprintf(injector_count, sizeof(injector_count), "--");
            if (displayed.crank_available)
                std::snprintf(burn_count, sizeof(burn_count), "%llu",
                              displayed.burns);
            else
                std::snprintf(burn_count, sizeof(burn_count), "--");
            if (width < 1100)
                std::snprintf(
                    status, sizeof(status),
                    "key %s  INJ PULSES %s  burns %s  RAM27/28 %02X/%02X  "
                    "lost %s  sound %s",
                    displayed.key_on ? "ON" : "off", injector_count, burn_count,
                    static_cast<unsigned>(displayed.ram27_faults),
                    static_cast<unsigned>(displayed.ram28_faults), lost_count,
                    sound_state);
            else
                std::snprintf(
                    status, sizeof(status),
                    "KEY %s  INJ PULSES %s  BURNS %s  RAM27/28 %02X/%02X  "
                    "LOST %s  SOUND %s %.0f%%",
                    displayed.key_on ? "ON" : "off", injector_count, burn_count,
                    static_cast<unsigned>(displayed.ram27_faults),
                    static_cast<unsigned>(displayed.ram28_faults), lost_count,
                    sound_state, static_cast<double>(sound_volume) * 100.0);
            draw_status(1, status);
            constexpr double degrees_per_radian =
                180.0 / 3.14159265358979323846;
            char phase[12] = "--";
            if (displayed.crank_available &&
                std::isfinite(displayed.crank_angle_rad) &&
                std::isfinite(displayed.tdc_phase_rad)) {
                double cycle_phase = std::fmod(
                    (displayed.crank_angle_rad - displayed.tdc_phase_rad) *
                        degrees_per_radian,
                    720.0);
                if (cycle_phase < 0.0)
                    cycle_phase += 720.0;
                std::snprintf(phase, sizeof(phase), "%03u",
                              static_cast<unsigned>(cycle_phase));
            }
            std::snprintf(
                status, sizeof(status),
                "tick %lld  phase~%s/720  PC %04X  CC3 %u  "
                "P5.0 %u  P5.1 %u  "
                "lamp candidate %s",
                displayed.tick, phase, static_cast<unsigned>(displayed.pc),
                displayed.cc3_high ? 1U : 0U, displayed.p50_high ? 1U : 0U,
                displayed.p51_high ? 1U : 0U,
                displayed.lamp_on_candidate ? "ON" : "off");
            draw_status(2, status);
            if (!compact_overlay) {
                std::snprintf(
                    status, sizeof(status),
                    "ROM IRAM RAW 60-67: %02X %02X %02X %02X  "
                    "%02X %02X %02X %02X",
                    static_cast<unsigned>(displayed.rom_iram_60_67[0]),
                    static_cast<unsigned>(displayed.rom_iram_60_67[1]),
                    static_cast<unsigned>(displayed.rom_iram_60_67[2]),
                    static_cast<unsigned>(displayed.rom_iram_60_67[3]),
                    static_cast<unsigned>(displayed.rom_iram_60_67[4]),
                    static_cast<unsigned>(displayed.rom_iram_60_67[5]),
                    static_cast<unsigned>(displayed.rom_iram_60_67[6]),
                    static_cast<unsigned>(displayed.rom_iram_60_67[7]));
                draw_status(4, status);
                const auto numeric_or_missing =
                    [](char *buffer, std::size_t capacity, double value,
                       bool available) {
                        if (available && std::isfinite(value))
                            std::snprintf(buffer, capacity, "%.1f", value);
                        else
                            std::snprintf(buffer, capacity, "--");
                    };
                char pedal_value[20], load_value[20];
                char film_value[20], vapor_value[20];
                numeric_or_missing(pedal_value, sizeof(pedal_value),
                                   displayed.pedal_pull_m * 1000.0,
                                   displayed.throttle_available);
                numeric_or_missing(load_value, sizeof(load_value),
                                   displayed.applied_load_nm,
                                   displayed.crank_available);
                numeric_or_missing(film_value, sizeof(film_value),
                                   displayed.fuel_film_kg * 1e6,
                                   displayed.intake_available);
                numeric_or_missing(vapor_value, sizeof(vapor_value),
                                   displayed.fuel_vapor_kg * 1e6,
                                   displayed.intake_available);
                std::snprintf(
                    status, sizeof(status),
                    "PEDAL %s mm  LOAD %s Nm  FILM %s mg  VAPOR %s mg",
                    pedal_value, load_value, film_value, vapor_value);
                draw_status(5, status);
            }
            std::snprintf(
                status, sizeof(status),
                "%sROM PUB F84E-50 %02X/%02X/%02X  "
                "HIST F85E-60 %02X/%02X/%02X",
                replay_controls ? "REPLAY | " : "",
                static_cast<unsigned>(displayed.rom_current_fault_banks[0]),
                static_cast<unsigned>(displayed.rom_current_fault_banks[1]),
                static_cast<unsigned>(displayed.rom_current_fault_banks[2]),
                static_cast<unsigned>(displayed.rom_history_fault_banks[0]),
                static_cast<unsigned>(displayed.rom_history_fault_banks[1]),
                static_cast<unsigned>(displayed.rom_history_fault_banks[2]));
            draw_status(3, status);
            char tach_value[24] = "--";
            char tach_pulses[24] = "--";
            if (displayed.tachometer_available &&
                std::isfinite(displayed.tachometer_rpm)) {
                std::snprintf(tach_value, sizeof(tach_value), "%.0f",
                              displayed.tachometer_rpm);
                std::snprintf(tach_pulses, sizeof(tach_pulses), "%llu",
                              displayed.tachometer_pulses);
            }
            // RAM values are raw retained bytes, not a fresh timer capture.
            std::snprintf(
                status, sizeof(status),
                "RPM PHY %s | RAM47 %u | IDLE46 %u | P1.1? %s (%s pulses)",
                readings[0].data(),
                static_cast<unsigned>(displayed.ram47) * 25U,
                static_cast<unsigned>(displayed.ram46) * 25U, tach_value,
                tach_pulses);
            draw_status(compact_overlay ? 4 : 6, status);
        }
        if (show_debug) {
            const SDL_FRect lamp_square{debug_panel.x + debug_panel.w -
                                            19.0f * ui_scale,
                                        debug_panel.y + 6.0f * ui_scale,
                                        11.0f * ui_scale, 11.0f * ui_scale};
            if (displayed.lamp_on_candidate)
                SDL_SetRenderDrawColor(screen, 255, 176, 59, 255);
            else
                SDL_SetRenderDrawColor(screen, 75, 83, 87, 255);
            SDL_RenderFillRect(screen, &lamp_square);
            font.draw(screen, debug_panel.x + debug_panel.w - 98.0f * ui_scale,
                      debug_panel.y + 4.0f * ui_scale, "LAMP? CAND.",
                      {235, 241, 246, 255}, 0.8f * ui_scale);
        }
        if (show_help) {
            const float panel_width = std::min(
                640.0f * ui_scale, std::max(1.0f, scene_width - 32.0f));
            const float panel_height =
                std::min(260.0f * ui_scale,
                         std::max(1.0f, static_cast<float>(height) - 32.0f));
            float panel_y = (static_cast<float>(height) - panel_height) / 2.0f;
            if (lab_buttons_visible(width, height))
                panel_y =
                    std::min(panel_y, lab_button_rect(0, width, height).y -
                                          panel_height - 16.0f * ui_scale);
            panel_y = std::max(panel_y, status_panel.y + status_panel.h +
                                            8.0f * ui_scale);
            const SDL_FRect panel{(scene_width - panel_width) / 2.0f, panel_y,
                                  panel_width, panel_height};
            SDL_SetRenderDrawColor(screen, 23, 34, 46, 255);
            SDL_RenderFillRect(screen, &panel);
            SDL_SetRenderDrawColor(screen, 99, 211, 220, 255);
            SDL_RenderRect(screen, &panel);
            font.draw(
                screen, panel.x + 16.0f * ui_scale, panel.y + 16.0f * ui_scale,
                "SEVEL MA1.7 LAB  |  H: CLOSE", {99, 211, 220, 255}, ui_scale);
            const std::array<const char *, 8> help_lines{
                "K KEY  |  HOLD S START  |  UP/DOWN PEDAL  |  Q/E GEAR",
                "SPACE PAUSE  |  . STEP 10MS  |  , NEXT IGNITION",
                displayed.drivetrain_available
                    ? "+/- SIM | PGUP/DN CLUTCH +10/-10% | L LOAD | M MUTE"
                    : "+/- SIM | PGUP/DN ROAD INPUT | L LOAD | M MUTE",
                "V SHAFT/RADIAL/AXIAL PAIRS  |  WHEEL ZOOM  |  MIDDLE PAN",
#ifdef SEVEL_LAB_PNG
                "G GROUP  |  A ECU/ANALOG  |  X FREEZE  |  C CSV+PNG",
#else
                "G GROUP  |  A ECU/ANALOG  |  X FREEZE  |  C CSV",
#endif
                "SCOPE Z MAX O FIT Y WHEEL/MID PAN/2X FIT | T MODE U CH Y EDGE",
                "TRIGGER I/J LEVEL B PRE  |  F11 FULL  F12 PNG  R FIT",
                "CTRL+U UNITS  0..3 UI  4..6 LAYOUT  7..9 FONT"};
            for (std::size_t line = 0; line < help_lines.size(); ++line) {
                const float y =
                    panel.y +
                    (48.0f + 26.0f * static_cast<float>(line)) * ui_scale;
                if (y + 16.0f * ui_scale < panel.y + panel.h)
                    font.draw(screen, panel.x + 16.0f * ui_scale, y,
                              help_lines[line], {235, 241, 246, 255}, ui_scale);
            }
        }
        if (width >= 1100) {
            SDL_SetRenderDrawColor(screen, 109, 121, 132, 255);
            for (const float x : {layout.left.w, layout.instruments.x}) {
                SDL_RenderLine(screen, x, 90.0f, x,
                               static_cast<float>(height) - 16.0f);
                SDL_FRect grip{x - 2.0f,
                               static_cast<float>(height) * 0.5f - 18.0f, 4.0f,
                               36.0f};
                SDL_RenderFillRect(screen, &grip);
            }
            const float center_x =
                layout.mechanical.x + layout.mechanical.w * 0.5f;
            SDL_RenderLine(screen, layout.mechanical.x + 16.0f, layout.scope.y,
                           layout.instruments.x - 16.0f, layout.scope.y);
            const SDL_FRect grip{center_x - 18.0f, layout.scope.y - 2.0f, 36.0f,
                                 4.0f};
            SDL_RenderFillRect(screen, &grip);
        }
        if (!show_help)
            draw_gear_tooltip(layout_state, screen, font, width, height,
                              applied_gear, displayed.rpm,
                              displayed.crank_available,
                              displayed.drivetrain_available);
        if (width >= 1800 && height >= 1000) {
            const SDL_FRect gear =
                gear_widget_rect(layout_state, width, height);
            const SDL_FRect clutch{gear.x - gear.w - 8.0f * ui_scale, gear.y,
                                   gear.w, gear.h};
            if (clutch.w >= 100.0f && clutch.h >= 90.0f)
                draw_clutch(screen, font, clutch, displayed, ui_scale,
                            stale_snapshot);
        }
        if (!captured && displayed.tick >= capture_after_tick) {
            SDL_Surface *surface = SDL_RenderReadPixels(screen, nullptr);
            captured = surface && save_frame(surface, screenshot_path);
            if (surface)
                SDL_DestroySurface(surface);
            if (captured)
                std::fprintf(stdout,
                             "[LAB-CAPTURE] saved=%s tick=%lld "
                             "digital_span_ticks=%lld\n",
                             screenshot_path.c_str(), displayed.tick,
                             analog_scope ? -1LL : scope_span_ticks);
            if (captured && analog_scope && trigger_mode != TriggerMode::Off)
                std::fprintf(
                    stdout,
                    "[LAB-TRIGGER-VIEW] mode=%d waiting=%d trigger=%lld "
                    "end=%lld samples=%zu first=%lld last=%lld live=%lld\n",
                    static_cast<int>(trigger_mode), trigger_waiting ? 1 : 0,
                    active_trigger_tick, analog_scope_end_tick,
                    analog_history.size(),
                    analog_history.empty() ? -1LL : analog_history.front().tick,
                    analog_history.empty() ? -1LL : analog_history.back().tick,
                    displayed.tick);
        }
        if (scope_csv_requested) {
            const long long end_tick =
                analog_scope ? analog_scope_end_tick : digital_scope_end_tick;
            const long long view_first_tick =
                std::max(0LL, end_tick - (analog_scope ? analog_span_ticks
                                                       : scope_span_ticks));
            long long first_tick = view_first_tick;
            long long last_tick = end_tick;
            if (!analog_scope && digital_cursors[0] && digital_cursors[1] &&
                digital_cursors[0]->edge.tick >= view_first_tick &&
                digital_cursors[1]->edge.tick >= view_first_tick &&
                digital_cursors[0]->edge.tick <= end_tick &&
                digital_cursors[1]->edge.tick <= end_tick) {
                first_tick = std::min(digital_cursors[0]->edge.tick,
                                      digital_cursors[1]->edge.tick);
                last_tick = std::max(digital_cursors[0]->edge.tick,
                                     digital_cursors[1]->edge.tick);
            } else if (analog_scope && scope_cursor_ticks[0] >= 0 &&
                       scope_cursor_ticks[1] >= 0) {
                const auto a =
                    nearest_scope_sample(analog_history, scope_cursor_ticks[0],
                                         view_first_tick, end_tick);
                const auto b =
                    nearest_scope_sample(analog_history, scope_cursor_ticks[1],
                                         view_first_tick, end_tick);
                if (a && b) {
                    first_tick = std::min(analog_history[*a].tick,
                                          analog_history[*b].tick);
                    last_tick = std::max(analog_history[*a].tick,
                                         analog_history[*b].tick);
                } else {
                    first_tick =
                        std::max(first_tick, std::min(scope_cursor_ticks[0],
                                                      scope_cursor_ticks[1]));
                    last_tick =
                        std::min(last_tick, std::max(scope_cursor_ticks[0],
                                                     scope_cursor_ticks[1]));
                }
            }
            const std::filesystem::path directory = ".work/gui-review";
            std::error_code error;
            std::filesystem::create_directories(directory, error);
            std::filesystem::path path;
            std::filesystem::path png_path;
            if (!error) {
                do {
                    path = directory /
                           ("sevel-scope-" +
                            (analog_scope ? "g" + std::to_string(analog_group)
                                          : std::string("digital")) +
                            "-" + std::to_string(end_tick) + "-" +
                            std::to_string(++scope_csv_index) + ".csv");
                    png_path = path;
                    png_path.replace_extension(".png");
                } while (std::filesystem::exists(path) ||
                         std::filesystem::exists(png_path));
            }
            const bool saved =
                !error && first_tick <= last_tick &&
                (analog_scope
                     ? save_scope_csv(
                           path, analog_history, analog_group, first_tick,
                           last_tick, view_first_tick, end_tick, metadata,
                           {trigger_mode, trigger_slope, trigger_channel,
                            trigger_event_source, trigger_level,
                            trigger_pre_fraction, active_trigger_tick},
                           display_units,
                           session ? session->snapshot_retention()
                                   : SimSession::SnapshotRetention{})
                     : save_digital_scope_csv(
                           path, digital_events, digital_scope_history,
                           first_tick, last_tick, view_first_tick, end_tick,
                           metadata,
                           digital_frozen ? frozen_event_overflow
                           : session      ? session->event_overflow()
                                          : 0ULL,
                           digital_frozen ? frozen_event_base_index
                                          : event_window.base_index,
                           scope_channels_visible));
            std::fprintf(
                saved ? stdout : stderr,
                "[LAB-SCOPE-CSV] %s=%s group=%d first=%lld last=%lld\n",
                saved ? "saved" : "failed", path.string().c_str(),
                analog_scope ? analog_group : -1, first_tick, last_tick);
#ifdef SEVEL_LAB_PNG
            if (saved) {
                const SDL_Rect panel{
                    static_cast<int>(std::lround(layout.scope.x + 16.0f)),
                    static_cast<int>(std::lround(layout.scope.y)),
                    static_cast<int>(std::lround(layout.scope.w - 32.0f)),
                    static_cast<int>(std::lround(layout.scope.h))};
                SDL_Surface *surface = SDL_RenderReadPixels(screen, &panel);
                const bool png_saved = surface &&
                                       save_frame(surface, png_path.string()) &&
                                       embed_scope_png_metadata(png_path, path);
                if (surface)
                    SDL_DestroySurface(surface);
                if (!png_saved) {
                    std::error_code ignored;
                    std::filesystem::remove(png_path, ignored);
                }
                std::fprintf(
                    png_saved ? stdout : stderr,
                    "[LAB-SCOPE-PNG] %s=%s group=%d first=%lld last=%lld\n",
                    png_saved ? "saved" : "failed", png_path.string().c_str(),
                    analog_scope ? analog_group : -1, first_tick, last_tick);
            }
#endif
            scope_csv_requested = false;
        }
        if (manual_capture_requested) {
#ifdef SEVEL_LAB_PNG
            constexpr const char *extension = ".png";
#else
            constexpr const char *extension = ".bmp";
#endif
            std::filesystem::path path;
            do {
                path = "sevel-ma17-lab-" + std::to_string(displayed.tick) +
                       "-" + std::to_string(++manual_capture_index) + extension;
            } while (std::filesystem::exists(path) ||
                     (gpu_renderer &&
                      std::filesystem::exists(gpu_scene_path(path))));
            SDL_Surface *surface = SDL_RenderReadPixels(screen, nullptr);
            const bool saved = surface && save_frame(surface, path.string());
            if (surface)
                SDL_DestroySurface(surface);
            if (saved) {
                std::fprintf(stdout, "[LAB-CAPTURE] saved=%s tick=%lld\n",
                             path.string().c_str(), displayed.tick);
                if (gpu_renderer)
                    save_gpu_scene(*gpu_renderer, path, displayed.tick);
            } else
                std::fprintf(stderr, "[LAB-CAPTURE] failed=%s error=%s\n",
                             path.string().c_str(), SDL_GetError());
            manual_capture_requested = false;
        }
        SDL_RenderPresent(screen);
        SDL_Delay(static_cast<Uint32>(frame_delay_ms));
        if (session && session->finished() && frame_limit > 0) {
            ma17::EmulatorSnapshot final_snapshot;
            const bool needs_final_frame =
                !captured && session->latest(final_snapshot) &&
                displayed.tick < capture_after_tick &&
                final_snapshot.tick >= capture_after_tick;
            if (!needs_final_frame)
                running = false;
        }
    }
    if (audio_source)
        audio_source->stop();
    if (frame_limit <= 0) {
        ui_preferences.scope_mode = analog_scope ? 1 : 0;
        ui_preferences.analog_group = analog_group;
        ui_preferences.analog_span_ticks = analog_span_ticks;
        ui_preferences.digital_span_ticks = scope_span_ticks;
        ui_preferences.digital_channel_mask = 0;
        for (std::size_t channel = 0; channel < scope_channels_visible.size();
             ++channel) {
            if (scope_channels_visible[channel])
                ui_preferences.digital_channel_mask |= 1U << channel;
        }
        ui_preferences.view_mode = view_mode;
        if (ui_scale_percent == ui_preferences.scale_percent &&
            fitted_pane_width > 0.0f && fitted_scene_height > 0.0f) {
            ui_preferences.camera_saved = 1;
            ui_preferences.camera_pane_width = fitted_pane_width;
            ui_preferences.camera_scene_height = fitted_scene_height;
            ui_preferences.shaft_zoom = camera.zoom;
            ui_preferences.shaft_pan_x =
                std::clamp(camera.pan_x / fitted_pane_width, -1.0f, 1.0f);
            ui_preferences.shaft_pan_y =
                std::clamp(camera.pan_y / fitted_scene_height, -0.5f, 0.5f);
            ui_preferences.axial_zoom = axial_camera.zoom;
            ui_preferences.axial_pan_x =
                std::clamp(axial_camera.pan_x / fitted_pane_width, -1.0f, 1.0f);
            ui_preferences.axial_pan_y = std::clamp(
                axial_camera.pan_y / fitted_scene_height, -0.5f, 0.5f);
        }
        const bool saved = save_ui_preferences(ui_preferences);
        std::fprintf(stdout,
                     "[LAB-SCOPE-PREF] saved=%d analog=%d group=%d "
                     "analog_span=%lld digital_span=%lld mask=%u\n",
                     saved ? 1 : 0, ui_preferences.scope_mode,
                     ui_preferences.analog_group,
                     ui_preferences.analog_span_ticks,
                     ui_preferences.digital_span_ticks,
                     ui_preferences.digital_channel_mask);
    }
    if (session)
        std::fprintf(
            stdout,
            "[LAB-LIVE] audio_dropped_samples=%llu "
            "audio_empty_queue=%llu audio_write_errors=%llu "
            "audio_mode_discarded_samples=%llu "
            "audio_device_need_samples=%llu audio_pcm_max_peak=%u\n",
            audio_source ? audio_source->dropped_samples() : 0ULL,
            audio_source ? audio_source->empty_queue_observations() : 0ULL,
            audio_source ? audio_source->write_errors() : 0ULL,
            audio_source ? audio_source->mode_discarded_samples() : 0ULL,
            audio_source ? audio_source->device_need_samples() : 0ULL,
            audio_source ? audio_source->max_pcm_peak() : 0U);
    audio_source.reset();
    if (audio_stream)
        SDL_DestroyAudioStream(audio_stream);
    gpu_renderer.reset();
    if (gpu_window)
        SDL_DestroyWindow(gpu_window);
    SDL_DestroyRenderer(screen);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return captured;
}

} // namespace lab
