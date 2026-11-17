#include "lab/SdlDisplay.hpp"

#include "lab/DonorScene.hpp"
#include "lab/FontRenderer.hpp"
#include "lab/LabButtons.hpp"
#include "lab/LabInstruments.hpp"
#include "lab/LiveAudio.hpp"
#include "lab/MeshAsset.hpp"
#include "lab/RecordingRenderer.hpp"
#include "lab/SimSession.hpp"

#include "gauge.h"
#include "sdl_gpu_renderer.h"

#include <SDL3/SDL.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <limits>
#include <memory>
#include <vector>

#ifdef SEVEL_LAB_PNG
#include <png.h>
#endif

namespace {

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
        return saved;
    }
#endif
    if (path.ends_with(".png"))
        return false;
    return SDL_SaveBMP(surface, path.c_str());
}

std::filesystem::path gpu_scene_path(std::filesystem::path path) {
    path.replace_filename(path.stem().string() + "-gpu" +
                          path.extension().string());
    return path;
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
        width <= static_cast<std::uint32_t>(
                     std::numeric_limits<int>::max() / 4) &&
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

void draw_axial_crank_views(SDL_Renderer *screen, FontRenderer &font,
                            const ma17::EmulatorSnapshot &snapshot,
                            const AuthoredMeshLibrary &meshes,
                            float scene_width, int height, float ui_scale) {
    if (scene_width < 650.0f || height < 600)
        return;
    const bool compact = scene_width < 800.0f || height < 690;
    const float scale = compact ? 1.0f : ui_scale;
    const float panel_size = (compact ? 64.0f : 104.0f) * scale;
    const float viewport_size = (compact ? 52.0f : 88.0f) * scale;
    const float inset_x = (compact ? 6.0f : 12.0f) * scale;
    const float inset_y = (compact ? 8.0f : 14.0f) * scale;
    std::vector<SDL_Vertex> vertices;
    const auto *mesh = meshes.find("Crankshaft");
    if (!mesh)
        return;
    vertices.reserve(mesh->indices.size());
    for (int pair = 0; pair < 2; ++pair) {
        const float step = panel_size + 4.0f * scale;
        const float panel_y = 238.0f * scale + step * static_cast<float>(pair);
        const SDL_FRect panel{(compact ? 8.0f : 16.0f) * scale, panel_y,
                              panel_size, panel_size};
        SDL_SetRenderDrawColor(screen, 24, 36, 49, 255);
        SDL_RenderFillRect(screen, &panel);
        font.draw(screen, panel.x + (compact ? 5.0f : 8.0f) * scale,
                  panel.y + 3.0f * scale,
                  pair == 0 ? (compact ? "1/4" : "AXIAL 1/4")
                            : (compact ? "2/3" : "AXIAL 2/3"),
                  {145, 177, 190, 255}, scale);
        RecordingRenderer axial;
        render_axial_crank_donor(axial, snapshot, viewport_size, meshes,
                                 pair + 1);
        vertices.clear();
        axial.for_each_triangle([&](const auto &points, const ysVector &color) {
            for (const auto &point : points)
                vertices.push_back(
                    {{panel.x + inset_x + point.x, panel.y + inset_y + point.y},
                     {color.x, color.y, color.z, 1.0f},
                     {0.0f, 0.0f}});
        });
        SDL_RenderGeometry(screen, nullptr, vertices.data(),
                           static_cast<int>(vertices.size()), nullptr, 0);
    }
}

void draw_combustion_order(SDL_Renderer *screen, FontRenderer &font,
                           float scene_width, int height, float ui_scale,
                           const std::array<ScenePulse, 4> &pulses,
                           const std::array<float, 2> &spark_glows,
                           const std::array<int, 2> &spark_channels) {
    if (scene_width < 800.0f || height < 690)
        return;
    const SDL_FRect panel{
        16.0f, static_cast<float>(height) - 218.0f - 47.0f * ui_scale,
        scene_width - 32.0f, 47.0f * ui_scale};
    SDL_SetRenderDrawColor(screen, 24, 36, 49, 255);
    SDL_RenderFillRect(screen, &panel);
    font.draw(screen, panel.x + 9.0f * ui_scale, panel.y + 8.0f * ui_scale,
              "BURNS  1 > 3 > 4 > 2", {235, 241, 246, 255}, ui_scale);
    char spark_label[96];
    std::snprintf(spark_label, sizeof(spark_label),
                  "SPARK  P5.%c > 1/4  +  P5.%c > 2/3  |  CANDIDATE PAIRS",
                  spark_channels[0] < 0 ? '?' : '0' + spark_channels[0],
                  spark_channels[1] < 0 ? '?' : '0' + spark_channels[1]);
    font.draw(screen, panel.x + 9.0f * ui_scale, panel.y + 27.0f * ui_scale,
              spark_label, {145, 177, 190, 255}, ui_scale);
    constexpr std::array<unsigned, 4> firing_order{0, 2, 3, 1};
    constexpr std::size_t edges = 24;
    constexpr float tau = 6.28318530718f;
    for (std::size_t order = 0; order < firing_order.size(); ++order) {
        const auto cylinder = firing_order[order];
        const float spark_glow =
            spark_glows[cylinder == 0 || cylinder == 3 ? 0 : 1];
        const float x =
            scene_width * (0.43f + 0.14f * static_cast<float>(order));
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
        font.draw(screen, x + 19.0f * ui_scale, y - 5.0f * ui_scale,
                  std::to_string(cylinder + 1), {235, 241, 246, 255}, ui_scale);
    }
}

float lab_ui_scale(int width, int height) {
    return std::clamp(std::min(static_cast<float>(width) / 1280.0f,
                               static_cast<float>(height) / 720.0f),
                      1.0f, 2.0f);
}

SDL_FRect view_selector_rect(int width, int height) {
    if (width < 1280 || height < 720)
        return {static_cast<float>(width) * 0.78f,
                static_cast<float>(height) * 0.45f - 34.0f,
                static_cast<float>(width) * 0.20f, 30.0f};
    return {static_cast<float>(width) * 0.76f - 225.0f,
            height < 900 ? 64.0f : 82.0f, 122.0f, 30.0f};
}

SDL_FRect fullscreen_button_rect(int width, int height) {
    return {static_cast<float>(width) * 0.76f - 95.0f,
            view_selector_rect(width, height).y, 80.0f, 30.0f};
}

void draw_lab_buttons(SDL_Renderer *screen, FontRenderer &font, int width,
                      int height, const std::array<bool, 9> &selected,
                      const std::array<bool, 9> &enabled, double load_nm) {
    if (!lab_buttons_visible(width, height))
        return;
    float mouse_x = 0.0f;
    float mouse_y = 0.0f;
    const auto mouse_state = SDL_GetMouseState(&mouse_x, &mouse_y);
    const auto hovered = hit_test_lab_button(mouse_x, mouse_y, width, height);
    const float scale = lab_ui_scale(width, height);
    for (std::size_t index = 0; index < lab_button_labels.size(); ++index) {
        const auto action = static_cast<LabButtonAction>(index);
        const bool over = action == hovered;
        const bool held = over && (mouse_state & SDL_BUTTON_LMASK) != 0;
        const auto bounds = lab_button_rect(index, width, height);
        const SDL_FRect box{bounds.x, bounds.y, bounds.width, bounds.height};
        const SDL_Color fill = !enabled[index]   ? SDL_Color{24, 30, 38, 255}
                               : selected[index] ? SDL_Color{58, 93, 104, 255}
                               : held            ? SDL_Color{47, 67, 76, 255}
                               : over            ? SDL_Color{38, 56, 67, 255}
                                                 : SDL_Color{29, 43, 55, 255};
        const SDL_Color frame = !enabled[index] ? SDL_Color{65, 75, 82, 255}
                                : selected[index]
                                    ? SDL_Color{99, 211, 220, 255}
                                    : SDL_Color{100, 139, 151, 255};
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
        font.draw(
            screen,
            bounds.x + (bounds.width - font.measure(label) * scale) / 2.0f,
            bounds.y + (bounds.height - 14.0f * scale) / 2.0f - 1.0f, label,
            enabled[index] ? SDL_Color{235, 241, 246, 255}
                           : SDL_Color{94, 108, 116, 255},
            scale);
    }
}

SDL_FRect pedal_slider_rect(int width, int height) {
    const float scale = lab_ui_scale(width, height);
    return {static_cast<float>(width) * 0.78f,
            static_cast<float>(height) * 0.62f,
            static_cast<float>(width) * 0.20f, 27.0f * scale};
}

SDL_FRect volume_slider_rect(int width, int height) {
    const float scale = lab_ui_scale(width, height);
    return {static_cast<float>(width) * 0.78f,
            static_cast<float>(height) * 0.45f,
            static_cast<float>(width) * 0.20f, 27.0f * scale};
}

void draw_volume_slider(SDL_Renderer *screen, FontRenderer &font, int width,
                        int height, float volume, bool enabled,
                        unsigned int pcm_peak,
                        unsigned long long shortfall,
                        unsigned long long dropped) {
    if (!lab_buttons_visible(width, height))
        return;
    const SDL_FRect box = volume_slider_rect(width, height);
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
    std::snprintf(label, sizeof(label), "VOLUME %.0f%%", volume * 100.0f);
    font.draw(screen, box.x + 8.0f, box.y + 5.0f * scale, label,
              enabled ? SDL_Color{235, 241, 246, 255}
                      : SDL_Color{94, 108, 116, 255},
              scale);
    if (enabled && width >= 1100 && height >= 690) {
        char signal[48];
        std::snprintf(signal, sizeof(signal), "PCM PEAK %.1f%%",
                      100.0 * static_cast<double>(pcm_peak) / 32768.0);
        font.draw(screen, box.x + 4.0f, box.y - 34.0f * scale, signal,
                  pcm_peak > 0 ? SDL_Color{99, 211, 220, 255}
                               : SDL_Color{145, 177, 190, 255},
                  scale);
        char health[80];
        std::snprintf(health, sizeof(health),
                      "STREAM SHORT~%llu  DROP %llu", shortfall, dropped);
        font.draw(screen, box.x + 4.0f, box.y - 16.0f * scale, health,
                  shortfall > 0 || dropped > 0
                      ? SDL_Color{249, 190, 96, 255}
                      : SDL_Color{145, 177, 190, 255},
                  scale);
    }
}

void draw_pedal_slider(SDL_Renderer *screen, FontRenderer &font, int width,
                       int height, double pedal_pull_m, bool enabled) {
    if (!lab_buttons_visible(width, height))
        return;
    const SDL_FRect box = pedal_slider_rect(width, height);
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
    std::snprintf(label, sizeof(label), "PEDAL %.0f%%", fraction * 100.0f);
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
                      int frame_delay_ms, bool bench_preset) {
    if (!SDL_Init(SDL_INIT_VIDEO |
                  (session && enable_audio ? SDL_INIT_AUDIO : 0U))) {
        std::fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
        return false;
    }
    SDL_Window *window =
        SDL_CreateWindow("SEVEL MA1.7 Lab", 1280, 720, SDL_WINDOW_RESIZABLE);
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
    const char *renderer_name = SDL_GetRendererName(screen);
    std::fprintf(stdout, "[LAB-VIDEO] renderer=%s\n",
                 renderer_name ? renderer_name : "unknown");
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
    FontRenderer font(font_path.string());
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
    double pedal_pull_m = 0.0;
    double load_nm = snapshot.applied_load_nm;
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
    std::array<bool, 3> scope_channels_visible{true, true, true};
    long long scope_span_ticks = 2LL * 990000;
    float sound_volume = 1.0f;
    SceneCamera camera;
    int view_mode = 0; // Shaft, four sections, axial 1/4, axial 2/3.
    bool show_help = false;
    std::array<Gauge, 3> gauges{};
    std::deque<TrendPoint> trends;
    Uint64 last_frame_ticks = SDL_GetTicks();
    ma17::EmulatorSnapshot displayed = snapshot;
    std::vector<SDL_Vertex> scene_vertices;
    constexpr std::size_t scene_batch_vertices = 8190;
    scene_vertices.reserve(scene_batch_vertices);
    gauges[0].m_max = 7000.0f;
    gauges[1].m_max = 90.0f;
    gauges[2].m_max = 5.0f;
    gauges[0].m_minorStep = 100;
    gauges[0].m_majorStep = 1000;
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
        case LabButtonAction::PedalUp:
            pedal_user_override = true;
            pedal_pull_m = std::clamp(
                pedal_pull_m +
                    (action == LabButtonAction::PedalUp ? 0.001 : -0.001),
                0.0, 0.025);
            session->set_pedal(pedal_pull_m);
            break;
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
    const auto toggle_fullscreen = [&] {
        const bool fullscreen =
            (SDL_GetWindowFlags(window) & SDL_WINDOW_FULLSCREEN) != 0;
        if (!SDL_SetWindowFullscreen(window, !fullscreen))
            std::fprintf(stderr, "SDL fullscreen: %s\n", SDL_GetError());
    };
    const auto set_pedal_from_pointer = [&](float x, int width, int height) {
        const SDL_FRect box = pedal_slider_rect(width, height);
        pedal_user_override = true;
        pedal_pull_m = 0.025 * std::clamp((x - box.x) / box.w, 0.0f, 1.0f);
        session->set_pedal(pedal_pull_m);
    };
    const auto set_load_from_pointer = [&](float x, int width, int height) {
        const auto box = lab_button_rect(
            static_cast<std::size_t>(LabButtonAction::Load), width, height);
        load_user_override = true;
        load_nm = 60.0 * std::clamp((x - box.x) / box.width, 0.0f, 1.0f);
        if (load_nm > 0.0)
            remembered_load_nm = load_nm;
        session->set_load(load_nm);
    };
    const auto set_volume_from_pointer = [&](float x, int width, int height) {
        const SDL_FRect box = volume_slider_rect(width, height);
        sound_volume = std::clamp((x - box.x) / box.w, 0.0f, 1.0f);
        SDL_SetAudioStreamGain(audio_stream, sound_muted ? 0.0f : sound_volume);
    };
    for (int frame = 0; running && (frame_limit <= 0 || frame < frame_limit);
         ++frame) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
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
                const bool in_scope =
                    SDL_GetRenderOutputSize(screen, &view_width,
                                            &view_height) &&
                    event.wheel.mouse_x >= 16.0f &&
                    event.wheel.mouse_x <
                        static_cast<float>(view_width) - 16.0f &&
                    event.wheel.mouse_y >=
                        static_cast<float>(view_height) - 158.0f &&
                    event.wheel.mouse_y <
                        static_cast<float>(view_height) - 12.0f;
                const float direction =
                    event.wheel.direction == SDL_MOUSEWHEEL_FLIPPED
                        ? -event.wheel.y
                        : event.wheel.y;
                if (in_scope)
                    scope_span_ticks =
                        std::clamp(direction > 0.0f ? scope_span_ticks / 2
                                                    : scope_span_ticks * 2,
                                   247500LL, 3960000LL);
                else
                    camera.zoom = std::clamp(
                        camera.zoom * (direction > 0.0f ? 1.1f : 1.0f / 1.1f),
                        0.5f, 3.0f);
            }
            if (event.type == SDL_EVENT_MOUSE_MOTION &&
                (event.motion.state & SDL_BUTTON_MMASK)) {
                camera.pan_x += event.motion.xrel;
                camera.pan_y += event.motion.yrel;
            }
            if (pedal_dragging && event.type == SDL_EVENT_MOUSE_MOTION &&
                (event.motion.state & SDL_BUTTON_LMASK)) {
                int view_width = 0;
                int view_height = 0;
                if (SDL_GetRenderOutputSize(screen, &view_width, &view_height))
                    set_pedal_from_pointer(event.motion.x, view_width,
                                           view_height);
            }
            if (load_dragging && event.type == SDL_EVENT_MOUSE_MOTION &&
                (event.motion.state & SDL_BUTTON_LMASK)) {
                int view_width = 0;
                int view_height = 0;
                if (SDL_GetRenderOutputSize(screen, &view_width, &view_height))
                    set_load_from_pointer(event.motion.x, view_width,
                                          view_height);
            }
            if (volume_dragging && event.type == SDL_EVENT_MOUSE_MOTION &&
                (event.motion.state & SDL_BUTTON_LMASK)) {
                int view_width = 0;
                int view_height = 0;
                if (SDL_GetRenderOutputSize(screen, &view_width, &view_height))
                    set_volume_from_pointer(event.motion.x, view_width,
                                            view_height);
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN &&
                event.button.button == SDL_BUTTON_LEFT) {
                int view_width = 0;
                int view_height = 0;
                if (SDL_GetRenderOutputSize(screen, &view_width,
                                            &view_height)) {
                    const SDL_FRect view_selector =
                        view_selector_rect(view_width, view_height);
                    const SDL_FRect fullscreen =
                        fullscreen_button_rect(view_width, view_height);
                    if (view_width >= 1280 && view_height >= 720 &&
                        event.button.x >= fullscreen.x &&
                        event.button.x < fullscreen.x + fullscreen.w &&
                        event.button.y >= fullscreen.y &&
                        event.button.y < fullscreen.y + fullscreen.h) {
                        toggle_fullscreen();
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
                    const auto action =
                        hit_test_lab_button(event.button.x, event.button.y,
                                            view_width, view_height);
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
                        const SDL_FRect pedal_slider =
                            pedal_slider_rect(view_width, view_height);
                        const SDL_FRect volume_slider =
                            volume_slider_rect(view_width, view_height);
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
                            const int channel =
                                scope_channel_at(event.button.x, event.button.y,
                                                 view_width, view_height);
                            if (channel >= 0)
                                scope_channels_visible[static_cast<std::size_t>(
                                    channel)] ^= true;
                        }
                    } else {
                        activate_button(action);
                    }
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
                pedal_dragging = false;
                load_dragging = false;
                volume_dragging = false;
            }
            if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_R)
                camera = {};
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.key == SDLK_V)
                view_mode = (view_mode + 1) % 4;
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                event.key.key == SDLK_H)
                show_help = !show_help;
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                (event.key.key == SDLK_F || event.key.key == SDLK_F11))
                toggle_fullscreen();
            if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
                event.key.windowID == SDL_GetWindowID(window) &&
                event.key.key == SDLK_F12)
                manual_capture_requested = true;
            if (session && event.type == SDL_EVENT_KEY_DOWN &&
                !event.key.repeat) {
                if (event.key.key == SDLK_SPACE)
                    activate_button(LabButtonAction::Pause);
                else if (event.key.key == SDLK_PERIOD)
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
                else if (!replay_controls && event.key.key == SDLK_S) {
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
            if (!pedal_user_override)
                pedal_pull_m = displayed.pedal_pull_m;
            if (!load_user_override)
                load_nm = displayed.applied_load_nm;
        }
        if (trends.empty() || trends.back().tick < displayed.tick)
            trends.push_back({displayed.tick, displayed.rpm, displayed.lambda});
        while (trends.size() > 600 ||
               (!trends.empty() &&
                displayed.tick - trends.front().tick > 5LL * 990000))
            trends.pop_front();
        const Uint64 frame_ticks = SDL_GetTicks();
        const float frame_dt =
            static_cast<float>(frame_ticks - last_frame_ticks) / 1000.0f;
        last_frame_ticks = frame_ticks;
        gauges[0].m_value = static_cast<float>(displayed.rpm);
        gauges[1].m_value =
            static_cast<float>(displayed.throttle_angle_rad * 57.2958);
        gauges[2].m_value = static_cast<float>(displayed.lambda);
        for (auto &gauge : gauges)
            gauge.update(frame_dt);
        EventWindow event_window;
        if (session)
            event_window = session->event_window();
        else if (captured_events)
            event_window.events = *captured_events;
        const auto &events = event_window.events;
        int width = 0;
        int height = 0;
        if (!SDL_GetRenderOutputSize(screen, &width, &height) || width <= 0 ||
            height <= 0) {
            running = false;
            break;
        }
        char title[160];
        constexpr std::array<const char *, 4> view_names{
            "SHAFT", "RADIAL", "AXIAL 1/4", "AXIAL 2/3"};
        const bool radial_view = view_mode != 0;
        const int focus_cylinder = view_mode >= 2 ? view_mode - 1 : 0;
        std::snprintf(title, sizeof(title),
                      "SEVEL MA1.7 | %s | %.0f rpm | RAM47=%u | tick %lld | "
                      "V view, K key, S starter, arrows pedal, L load, "
                      "Space pause, . 10ms, , next ignition",
                      view_names[static_cast<std::size_t>(view_mode)],
                      displayed.rpm,
                      static_cast<unsigned>(displayed.ram47), displayed.tick);
        SDL_SetWindowTitle(window, title);
        RecordingRenderer geometry;
        const float scene_width = static_cast<float>(width) * 0.76f;
        const float scene_height = static_cast<float>(height) * 0.80f;
        camera.pan_x =
            std::clamp(camera.pan_x, -scene_width * 0.5f, scene_width * 0.5f);
        camera.pan_y =
            std::clamp(camera.pan_y, -scene_height * 0.5f, scene_height * 0.5f);
        // Fit the radial head and crankweights between status and controls.
        SceneCamera radial_camera = camera;
        const float short_height = std::max(0.0f, 864.0f - scene_height);
        radial_camera.zoom *= std::max(0.8f, 1.0f - short_height / 1440.0f);
        radial_camera.pan_y -= std::min(65.0f, short_height / 4.4f);
        const float extra_height = std::max(0.0f, scene_height - 864.0f);
        radial_camera.zoom *= std::max(0.7f, 1.0f - extra_height / 2880.0f);
        radial_camera.pan_y -= extra_height / 4.0f;
        if (focus_cylinder != 0) {
            radial_camera = camera;
            radial_camera.zoom *= scene_height < 690.0f ? 0.9f : 1.0f;
        }
        // Visual afterglow only; electrical pin widths remain in the event
        // trace.
        constexpr long long pulse_span_ticks = 49500;
        constexpr long long spark_span_ticks = 24750;
        std::array<ScenePulse, 4> pulses{};
        std::array<bool, 4> seen{};
        std::array<float, 2> spark_glows{};
        std::array<bool, 2> spark_seen{};
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
        if (radial_view)
            render_sevel_radial_donor(geometry, displayed, scene_width,
                                      scene_height, meshes, {}, {},
                                      radial_camera, pulses, focus_cylinder);
        else
            render_sevel_scene_donor(geometry, displayed, scene_width,
                                     scene_height, {}, {}, camera, &meshes,
                                     pulses);
        if (gpu_renderer) {
            int gpu_width = 0;
            int gpu_height = 0;
            if (SDL_GetWindowSizeInPixels(gpu_window, &gpu_width,
                                          &gpu_height) &&
                gpu_width > 0 && gpu_height > 0) {
                SceneCamera gpu_camera = radial_view ? radial_camera : camera;
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
        SDL_SetRenderDrawColor(screen, 15, 22, 34, 255);
        SDL_RenderClear(screen);
        const SDL_Rect scene_clip{0, 0, static_cast<int>(scene_width),
                                  static_cast<int>(scene_height)};
        SDL_SetRenderClipRect(screen, &scene_clip);
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
        geometry.for_each_triangle(
            [&](const auto &points, const ysVector &color) {
                if (!geometry_ok)
                    return;
                for (const auto &point : points) {
                    SDL_Vertex vertex{};
                    vertex.position = {point.x, point.y};
                    vertex.color = {std::clamp(color.x, 0.0f, 1.0f),
                                    std::clamp(color.y, 0.0f, 1.0f),
                                    std::clamp(color.z, 0.0f, 1.0f), 1.0f};
                    scene_vertices.push_back(vertex);
                }
                if (scene_vertices.size() == scene_batch_vertices)
                    flush_geometry();
            });
        if (geometry_ok)
            flush_geometry();
        SDL_SetRenderClipRect(screen, nullptr);
        if (!geometry_ok) {
            std::fprintf(stderr, "SDL scene geometry: %s\n", SDL_GetError());
            running = false;
            continue;
        }
        const float ui_scale = lab_ui_scale(width, height);
        const bool compact_overlay = width < 1100 || height < 690;
        const SDL_FRect status_panel{
            16.0f, 16.0f,
            std::min(static_cast<float>(width) - 32.0f, scene_width + 48.0f),
            (compact_overlay ? 72.0f : 100.0f) * ui_scale};
        SDL_SetRenderDrawColor(screen, 23, 34, 46, 255);
        SDL_RenderFillRect(screen, &status_panel);
        SDL_SetRenderDrawColor(screen, 65, 91, 104, 255);
        SDL_RenderRect(screen, &status_panel);
        if (!radial_view)
            draw_axial_crank_views(screen, font, displayed, meshes, scene_width,
                                   height, ui_scale);
        if (lab_buttons_visible(width, height)) {
            const SDL_FRect selector = view_selector_rect(width, height);
            SDL_SetRenderDrawColor(screen, radial_view ? 40 : 24,
                                   radial_view ? 64 : 36, 49, 255);
            SDL_RenderFillRect(screen, &selector);
            SDL_SetRenderDrawColor(screen, 90, 128, 142, 255);
            SDL_RenderRect(screen, &selector);
            font.draw(screen, selector.x + 8.0f, selector.y + 8.0f,
                      view_mode == 0   ? "V: SHAFT"
                      : view_mode == 1 ? "V: RADIAL"
                      : view_mode == 2 ? "V: 1/4"
                                       : "V: 2/3",
                      {145, 177, 190, 255});
            if (width >= 1280 && height >= 720) {
                const SDL_FRect fullscreen =
                    fullscreen_button_rect(width, height);
                SDL_SetRenderDrawColor(screen, 24, 36, 49, 255);
                SDL_RenderFillRect(screen, &fullscreen);
                SDL_SetRenderDrawColor(screen, 90, 128, 142, 255);
                SDL_RenderRect(screen, &fullscreen);
                font.draw(screen, fullscreen.x + 8.0f, fullscreen.y + 8.0f,
                          (SDL_GetWindowFlags(window) & SDL_WINDOW_FULLSCREEN)
                              ? "F: EXIT"
                              : "F: FULL",
                          {145, 177, 190, 255});
            }
        }
        if (view_mode == 1) {
            constexpr std::array<const char *, 4> labels{"CYL 1", "CYL 2",
                                                         "CYL 3", "CYL 4"};
            const SevelVisualGeometry geometry_size{};
            const SceneDimensions scene_size{};
            const float head_y =
                static_cast<float>(geometry_size.visual_estimate_rod_length_m +
                                   SevelVisualGeometry::crank_radius_m +
                                   scene_size.visual_estimate_head_height_m);
            const float label_y =
                scene_height *
                    (0.81f - 2.0f * radial_camera.zoom * (head_y + 0.07f)) +
                radial_camera.pan_y - 18.0f * ui_scale;
            for (std::size_t cylinder = 0; cylinder < labels.size();
                 ++cylinder) {
                const float center = (static_cast<float>(cylinder) - 1.5f) *
                                     visual_estimate_radial_section_spacing_m;
                const float x =
                    scene_width * (0.5f + 2.0f * radial_camera.zoom * center) +
                    radial_camera.pan_x;
                font.draw(screen,
                          x - font.measure(labels[cylinder]) * ui_scale / 2.0f,
                          label_y, labels[cylinder],
                          cylinder == 0 || cylinder == 3
                              ? SDL_Color{99, 211, 220, 255}
                              : SDL_Color{234, 165, 100, 255},
                          ui_scale);
            }
        }
        if (focus_cylinder != 0) {
            const char *label = focus_cylinder == 1
                                    ? "AXIAL 1/4  |  CYL 1"
                                    : "AXIAL 2/3  |  CYL 2";
            font.draw(screen, 24.0f * ui_scale,
                      status_panel.y + status_panel.h + 10.0f * ui_scale,
                      label, {176, 218, 226, 255}, ui_scale);
        }
        draw_lab_gauge(screen, font, static_cast<float>(width) * 0.86f,
                       static_cast<float>(height) * 0.35f, 105.0f * ui_scale,
                       displayed.rpm, 7000.0, "RPM",
                       SDL_Color{249, 190, 96, 255}, gauges[0].needlePosition(),
                       ui_scale, &gauges[0]);
        draw_lab_gauge(screen, font, static_cast<float>(width) * 0.81f,
                       static_cast<float>(height) * 0.58f, 52.0f * ui_scale,
                       displayed.throttle_angle_rad * 57.2958, 90.0, "TPS",
                       SDL_Color{99, 211, 220, 255}, gauges[1].needlePosition(),
                       ui_scale, &gauges[1]);
        draw_lab_gauge(screen, font, static_cast<float>(width) * 0.92f,
                       static_cast<float>(height) * 0.58f, 52.0f * ui_scale,
                       displayed.lambda, 5.0, "LAM",
                       SDL_Color{200, 144, 232, 255},
                       gauges[2].needlePosition(), ui_scale, &gauges[2]);
        if (focus_cylinder == 0 && width >= 2400 && height >= 1000 &&
            width > 2 * height) {
            const float gauge_y =
                static_cast<float>(height) * (radial_view ? 0.77f : 0.73f);
            const float radius = 62.0f * ui_scale;
            draw_lab_gauge(
                screen, font, scene_width * 0.52f, gauge_y, radius,
                displayed.coolant_c, 120.0, "COOLANT C",
                SDL_Color{236, 173, 106, 255},
                std::clamp(static_cast<float>(displayed.coolant_c / 120.0),
                           0.0f, 1.0f),
                ui_scale);
            draw_lab_gauge(
                screen, font, scene_width * 0.70f, gauge_y, radius,
                displayed.applied_load_nm, 60.0, "LOAD NM",
                SDL_Color{153, 194, 221, 255},
                std::clamp(static_cast<float>(displayed.applied_load_nm / 60.0),
                           0.0f, 1.0f),
                ui_scale);
            const double film_mg = displayed.fuel_film_kg * 1e6;
            draw_lab_gauge(
                screen, font, scene_width * 0.88f, gauge_y, radius, film_mg,
                100.0, "FILM MG", SDL_Color{184, 210, 140, 255},
                std::clamp(static_cast<float>(film_mg / 100.0), 0.0f, 1.0f),
                ui_scale);
        }
        draw_volume_slider(
            screen, font, width, height, sound_volume, audio_stream != nullptr,
            audio_source ? audio_source->recent_pcm_peak() : 0U,
            audio_source ? audio_source->device_need_samples() : 0ULL,
            audio_source ? audio_source->dropped_samples() : 0ULL);
        draw_pedal_slider(screen, font, width, height, pedal_pull_m,
                          session && !replay_controls);
        if (width >= 1000 && height >= 690) {
            const SDL_FRect trend_panel{static_cast<float>(width) * 0.77f,
                                        static_cast<float>(height) * 0.66f,
                                        static_cast<float>(width) * 0.21f,
                                        static_cast<float>(height) * 0.11f};
            draw_lab_trends(screen, font, trend_panel, displayed.tick, trends);
        }
        draw_lab_scope(screen, font, width, height, displayed.tick, events,
                       scope_channels_visible, scope_span_ticks);
        const float order_scale =
            width >= 2400 && height >= 1000 && width > 2 * height
                ? std::min(ui_scale, 1.2f)
                : ui_scale;
        draw_combustion_order(screen, font, scene_width, height, order_scale,
                              pulses, spark_glows, spark_channels);
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
        draw_lab_buttons(screen, font, width, height, button_selected,
                         button_enabled, load_nm);
        constexpr std::array<SDL_Color, 6> status_colors{
            {{235, 241, 246, 255},
             {176, 218, 226, 255},
             {241, 198, 126, 255},
             {157, 182, 196, 255},
             {176, 218, 226, 255},
             {157, 182, 196, 255}}};
        const auto draw_status = [&](int row, const char *line) {
            font.draw(screen, 24.0f,
                      24.0f + 16.0f * ui_scale * static_cast<float>(row), line,
                      status_colors[static_cast<std::size_t>(row)], ui_scale);
        };
        char status[160];
        if (compact_overlay)
            std::snprintf(status, sizeof(status),
                          "RPM %.0f  TPS %.1fD  T1m %.2fV  T2m %.2fV  "
                          "LAM %.2f  ECT %.0fC",
                          displayed.rpm,
                          displayed.throttle_angle_rad * 57.2958,
                          displayed.tps_track1_v, displayed.tps_track2_v,
                          displayed.lambda, displayed.coolant_c);
        else
            std::snprintf(status, sizeof(status),
                          "RPM %.0f  TPS %.1f deg  lambda %.2f  coolant %.1f C",
                          displayed.rpm,
                          displayed.throttle_angle_rad * 57.2958,
                          displayed.lambda, displayed.coolant_c);
        draw_status(0, status);
        const char *help_hint = show_help ? "H: CLOSE" : "H: HELP";
        font.draw(screen,
                  status_panel.x + status_panel.w -
                      (font.measure(help_hint) + 12.0f) * ui_scale,
                  24.0f, help_hint, {99, 211, 220, 255}, ui_scale);
        const char *sound_state = "on";
        if (!audio_source)
            sound_state = enable_audio ? "unavailable" : "off";
        else if (sound_muted)
            sound_state = "muted";
        else if (audio_source->suspended())
            sound_state = "paused";
        if (width < 1100)
            std::snprintf(
                status, sizeof(status),
                "key %s  CC3 %llu  burns %llu  RAM27/28 %02X/%02X  "
                "lost %llu  sound %s",
                displayed.key_on ? "ON" : "off", displayed.injector_pulses,
                displayed.burns, static_cast<unsigned>(displayed.ram27_faults),
                static_cast<unsigned>(displayed.ram28_faults),
                session ? session->event_overflow() : 0ULL, sound_state);
        else
            std::snprintf(
                status, sizeof(status),
                "key %s  CC3 %llu  burns %llu  RAM27/28 %02X/%02X  "
                "lost %llu  lag %llu  skip %llu  short~%llu  empty %llu  "
                "sound %s %.0f%%",
                displayed.key_on ? "ON" : "off", displayed.injector_pulses,
                displayed.burns, static_cast<unsigned>(displayed.ram27_faults),
                static_cast<unsigned>(displayed.ram28_faults),
                session ? session->event_overflow() : 0ULL,
                audio_source ? audio_source->dropped_samples() : 0ULL,
                audio_source ? audio_source->mode_discarded_samples() : 0ULL,
                audio_source ? audio_source->device_need_samples() : 0ULL,
                audio_source ? audio_source->empty_queue_observations() : 0ULL,
                sound_state, sound_volume * 100.0f);
        draw_status(1, status);
        constexpr double degrees_per_radian =
            180.0 / 3.14159265358979323846;
        double cycle_phase =
            std::fmod((displayed.crank_angle_rad - displayed.tdc_phase_rad) *
                          degrees_per_radian,
                      720.0);
        if (cycle_phase < 0.0)
            cycle_phase += 720.0;
        std::snprintf(status, sizeof(status),
                      "tick %lld  phase~%03u/720  PC %04X  CC3 %u  "
                      "P5.0 %u  P5.1 %u  "
                      "lamp candidate %s",
                      displayed.tick, static_cast<unsigned>(cycle_phase),
                      static_cast<unsigned>(displayed.pc),
                      displayed.cc3_high ? 1U : 0U,
                      displayed.p50_high ? 1U : 0U,
                      displayed.p51_high ? 1U : 0U,
                      displayed.lamp_on_candidate ? "ON" : "off");
        draw_status(2, status);
        if (!compact_overlay) {
            std::snprintf(status, sizeof(status),
                          "TPS1 model %.2f V  TPS2 model %.2f V  "
                          "lambda model %.2f V",
                          displayed.tps_track1_v, displayed.tps_track2_v,
                          displayed.lambda_voltage_v);
            draw_status(4, status);
            char idle_status[72] = "  IAC? NO BINDING";
            if (displayed.idle_bridge_candidate)
                std::snprintf(
                    idle_status, sizeof(idle_status),
                    "  IAC? P1.5/6 %u/%u STEM~%.1fMM CT %s%s",
                    displayed.p15_high ? 1U : 0U,
                    displayed.p16_high ? 1U : 0U,
                    displayed.idle_stem_m * 1000.0,
                    displayed.idle_contact_closed ? "closed" : "open",
                    displayed.idle_motor_connected ? "" : " DISC");
            std::snprintf(
                status, sizeof(status),
                "pedal %.1f mm  load %.0f Nm  film model %.1f mg  vapor %.1f "
                "mg%s",
                displayed.pedal_pull_m * 1000.0, displayed.applied_load_nm,
                displayed.fuel_film_kg * 1e6, displayed.fuel_vapor_kg * 1e6,
                idle_status);
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
        const SDL_FRect lamp_panel{
            static_cast<float>(width) * 0.78f, 88.0f * ui_scale,
            std::min(260.0f * ui_scale,
                     static_cast<float>(width) * 0.22f - 16.0f * ui_scale),
            32.0f * ui_scale};
        SDL_SetRenderDrawColor(screen, 32, 46, 59, 255);
        SDL_RenderFillRect(screen, &lamp_panel);
        const SDL_FRect lamp_square{lamp_panel.x + 8.0f * ui_scale,
                                    lamp_panel.y + 8.0f * ui_scale,
                                    16.0f * ui_scale, 16.0f * ui_scale};
        if (displayed.lamp_on_candidate)
            SDL_SetRenderDrawColor(screen, 255, 176, 59, 255);
        else
            SDL_SetRenderDrawColor(screen, 75, 83, 87, 255);
        SDL_RenderFillRect(screen, &lamp_square);
        SDL_SetRenderDrawColor(screen, 235, 241, 246, 255);
        font.draw(screen, lamp_panel.x + 32.0f * ui_scale,
                  lamp_panel.y + 12.0f * ui_scale,
                  width < 1100 ? "LAMP? CAND." : "MA1.7 LAMP? CANDIDATE",
                  {235, 241, 246, 255}, ui_scale);
        if (bench_preset) {
            const SDL_FRect bench_panel{
                lamp_panel.x, lamp_panel.y + lamp_panel.h + 4.0f * ui_scale,
                lamp_panel.w, 22.0f * ui_scale};
            SDL_SetRenderDrawColor(screen, 46, 39, 30, 255);
            SDL_RenderFillRect(screen, &bench_panel);
            font.draw(screen, bench_panel.x + 8.0f * ui_scale,
                      bench_panel.y + 6.0f * ui_scale,
                      width < 1100 ? "WARM BENCH*"
                                   : "WARM BENCH / CANDIDATE I/O",
                      {249, 190, 96, 255}, ui_scale);
        }
        if (show_help) {
            const float panel_width = std::min(
                640.0f * ui_scale, std::max(1.0f, scene_width - 32.0f));
            const float panel_height = std::min(
                260.0f * ui_scale,
                std::max(1.0f, static_cast<float>(height) - 32.0f));
            float panel_y = (static_cast<float>(height) - panel_height) / 2.0f;
            if (lab_buttons_visible(width, height))
                panel_y = std::min(
                    panel_y, lab_button_rect(0, width, height).y -
                                 panel_height - 16.0f * ui_scale);
            panel_y = std::max(panel_y, status_panel.y + status_panel.h +
                                           8.0f * ui_scale);
            const SDL_FRect panel{(scene_width - panel_width) / 2.0f, panel_y,
                                  panel_width, panel_height};
            SDL_SetRenderDrawColor(screen, 23, 34, 46, 255);
            SDL_RenderFillRect(screen, &panel);
            SDL_SetRenderDrawColor(screen, 99, 211, 220, 255);
            SDL_RenderRect(screen, &panel);
            font.draw(screen, panel.x + 16.0f * ui_scale,
                      panel.y + 16.0f * ui_scale, "SEVEL MA1.7 LAB  |  H: CLOSE",
                      {99, 211, 220, 255}, ui_scale);
            constexpr std::array<const char *, 7> help_lines{
                "K KEY  |  HOLD S START  |  UP/DOWN PEDAL  |  L LOAD",
                "SPACE PAUSE  |  . STEP 10MS  |  , NEXT IGNITION",
                "+/- SPEED  |  M MUTE  |  [ ] VOLUME",
                "V SHAFT/RADIAL/AXIAL PAIRS  |  WHEEL ZOOM  |  MIDDLE PAN",
                "WHEEL ON SCOPE: TIMEBASE  |  CLICK LABEL: CHANNEL",
                "F/F11 FULLSCREEN  |  F12 CAPTURE  |  R RESET  |  ESC EXIT",
                "MOUSE: BUTTONS AND PEDAL/LOAD/VOLUME SLIDERS"};
            for (std::size_t line = 0; line < help_lines.size(); ++line) {
                const float y = panel.y +
                                (48.0f + 26.0f * static_cast<float>(line)) *
                                    ui_scale;
                if (y + 16.0f * ui_scale < panel.y + panel.h)
                    font.draw(screen, panel.x + 16.0f * ui_scale, y,
                              help_lines[line], {235, 241, 246, 255}, ui_scale);
            }
        }
        if (!captured && displayed.tick >= capture_after_tick) {
            SDL_Surface *surface = SDL_RenderReadPixels(screen, nullptr);
            captured = surface && save_frame(surface, screenshot_path);
            if (surface)
                SDL_DestroySurface(surface);
            if (captured)
                std::fprintf(stdout, "[LAB-CAPTURE] saved=%s tick=%lld\n",
                             screenshot_path.c_str(), displayed.tick);
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
    if (audio_stream)
        SDL_DestroyAudioStream(audio_stream);
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
    gpu_renderer.reset();
    if (gpu_window)
        SDL_DestroyWindow(gpu_window);
    SDL_DestroyRenderer(screen);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return captured;
}

} // namespace lab
