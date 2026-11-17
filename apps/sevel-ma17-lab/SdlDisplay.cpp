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
#include <cmath>
#include <cstdio>
#include <filesystem>
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

} // namespace

namespace lab {
namespace {

void draw_axial_crank_views(SDL_Renderer *screen, FontRenderer &font,
                            const ma17::EmulatorSnapshot &snapshot,
                            const AuthoredMeshLibrary &meshes,
                            float scene_width, int height) {
    if (scene_width < 800.0f || height < 690)
        return;
    std::vector<SDL_Vertex> vertices;
    const auto *mesh = meshes.find("Crankshaft");
    if (!mesh)
        return;
    vertices.reserve(mesh->indices.size());
    for (int pair = 0; pair < 2; ++pair) {
        const SDL_FRect panel{16.0f, 238.0f + 108.0f * static_cast<float>(pair),
                              104.0f, 104.0f};
        SDL_SetRenderDrawColor(screen, 24, 36, 49, 255);
        SDL_RenderFillRect(screen, &panel);
        font.draw(screen, panel.x + 8.0f, panel.y + 3.0f,
                  pair == 0 ? "AXIAL 1/4" : "AXIAL 2/3", {145, 177, 190, 255});
        RecordingRenderer axial;
        render_axial_crank_donor(axial, snapshot, 88.0f, meshes, pair + 1);
        vertices.clear();
        axial.for_each_triangle([&](const auto &points, const ysVector &color) {
            for (const auto &point : points)
                vertices.push_back(
                    {{panel.x + 12.0f + point.x, panel.y + 14.0f + point.y},
                     {color.x, color.y, color.z, 1.0f},
                     {0.0f, 0.0f}});
        });
        SDL_RenderGeometry(screen, nullptr, vertices.data(),
                           static_cast<int>(vertices.size()), nullptr, 0);
    }
}

void draw_combustion_order(SDL_Renderer *screen, FontRenderer &font,
                           float scene_width, int height,
                           const std::array<ScenePulse, 4> &pulses) {
    if (scene_width < 800.0f || height < 690)
        return;
    const SDL_FRect panel{16.0f, static_cast<float>(height) - 265.0f,
                          scene_width - 32.0f, 47.0f};
    SDL_SetRenderDrawColor(screen, 24, 36, 49, 255);
    SDL_RenderFillRect(screen, &panel);
    font.draw(screen, 25.0f, panel.y + 8.0f, "BURNS  1 > 3 > 4 > 2",
              {235, 241, 246, 255});
    font.draw(screen, 25.0f, panel.y + 27.0f, "SPARK PAIRS  1/4  +  2/3",
              {145, 177, 190, 255});
    constexpr std::array<unsigned, 4> firing_order{0, 2, 3, 1};
    constexpr std::size_t edges = 24;
    constexpr float tau = 6.28318530718f;
    for (std::size_t order = 0; order < firing_order.size(); ++order) {
        const auto cylinder = firing_order[order];
        const float x =
            scene_width * (0.43f + 0.14f * static_cast<float>(order));
        const float y = panel.y + 23.0f;
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
            const auto point = [x, y](float a) {
                return SDL_FPoint{x + 11.0f * std::cos(a),
                                  y + 11.0f * std::sin(a)};
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
        SDL_SetRenderDrawColor(screen, 90, 128, 142, 255);
        SDL_RenderLines(screen, outline.data(), outline.size());
        font.draw(screen, x + 19.0f, y - 5.0f, std::to_string(cylinder + 1),
                  {235, 241, 246, 255});
    }
}

void draw_lab_buttons(SDL_Renderer *screen, FontRenderer &font, int width,
                      int height, const std::array<bool, 9> &selected,
                      const std::array<bool, 9> &enabled) {
    if (!lab_buttons_visible(width, height))
        return;
    float mouse_x = 0.0f;
    float mouse_y = 0.0f;
    const auto mouse_state = SDL_GetMouseState(&mouse_x, &mouse_y);
    const auto hovered = hit_test_lab_button(mouse_x, mouse_y, width, height);
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
        const std::string label(lab_button_labels[index]);
        font.draw(screen,
                  bounds.x + (bounds.width - font.measure(label)) / 2.0f,
                  bounds.y + 12.0f, label,
                  enabled[index] ? SDL_Color{235, 241, 246, 255}
                                 : SDL_Color{94, 108, 116, 255});
    }
}

SDL_FRect pedal_slider_rect(int width, int height) {
    return {static_cast<float>(width) * 0.78f,
            static_cast<float>(height) * 0.62f,
            static_cast<float>(width) * 0.20f, 27.0f};
}

void draw_pedal_slider(SDL_Renderer *screen, FontRenderer &font, int width,
                       int height, double pedal_pull_m, bool enabled) {
    if (!lab_buttons_visible(width, height))
        return;
    const SDL_FRect box = pedal_slider_rect(width, height);
    const float fraction =
        static_cast<float>(std::clamp(pedal_pull_m / 0.025, 0.0, 1.0));
    SDL_SetRenderDrawColor(screen, 29, 43, 55, 255);
    SDL_RenderFillRect(screen, &box);
    SDL_SetRenderDrawColor(screen, enabled ? 99 : 65, enabled ? 211 : 75,
                           enabled ? 220 : 82, 255);
    SDL_RenderRect(screen, &box);
    const SDL_FRect fill{box.x + 2.0f, box.y + box.h - 5.0f,
                         (box.w - 4.0f) * fraction, 3.0f};
    SDL_RenderFillRect(screen, &fill);
    char label[32];
    std::snprintf(label, sizeof(label), "PEDAL %.0f%%", fraction * 100.0f);
    font.draw(screen, box.x + 8.0f, box.y + 5.0f, label,
              enabled ? SDL_Color{235, 241, 246, 255}
                      : SDL_Color{94, 108, 116, 255});
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
    bool load_engaged = false;
    bool pedal_user_override = false;
    bool load_user_override = false;
    bool key_on = snapshot.key_on;
    bool sound_muted = false;
    bool keyboard_starter_held = false;
    bool mouse_starter_held = false;
    bool pedal_dragging = false;
    std::array<bool, 3> scope_channels_visible{true, true, true};
    float sound_volume = 1.0f;
    SceneCamera camera;
    std::array<Gauge, 3> gauges{};
    std::deque<TrendPoint> trends;
    Uint64 last_frame_ticks = SDL_GetTicks();
    ma17::EmulatorSnapshot displayed = snapshot;
    gauges[0].m_max = 7000.0f;
    gauges[1].m_max = 90.0f;
    gauges[2].m_max = 5.0f;
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
            load_engaged = !load_engaged;
            session->set_load(load_engaged ? 24.0 : 0.0);
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
    const auto set_pedal_from_pointer = [&](float x, int width, int height) {
        const SDL_FRect box = pedal_slider_rect(width, height);
        pedal_user_override = true;
        pedal_pull_m = 0.025 * std::clamp((x - box.x) / box.w, 0.0f, 1.0f);
        session->set_pedal(pedal_pull_m);
    };
    for (int frame = 0; running && (frame_limit <= 0 || frame < frame_limit);
         ++frame) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
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
            if (event.type == SDL_EVENT_MOUSE_WHEEL && event.wheel.y != 0.0f)
                camera.zoom = std::clamp(
                    camera.zoom * (event.wheel.y > 0.0f ? 1.1f : 1.0f / 1.1f),
                    0.5f, 3.0f);
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
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN &&
                event.button.button == SDL_BUTTON_LEFT) {
                int view_width = 0;
                int view_height = 0;
                if (SDL_GetRenderOutputSize(screen, &view_width,
                                            &view_height)) {
                    const auto action =
                        hit_test_lab_button(event.button.x, event.button.y,
                                            view_width, view_height);
                    if (action == LabButtonAction::Starter) {
                        if (session && !replay_controls) {
                            mouse_starter_held = true;
                            session->set_starter(true);
                        }
                    } else if (action == LabButtonAction::None) {
                        const SDL_FRect slider =
                            pedal_slider_rect(view_width, view_height);
                        if (session && !replay_controls &&
                            lab_buttons_visible(view_width, view_height) &&
                            event.button.x >= slider.x &&
                            event.button.x < slider.x + slider.w &&
                            event.button.y >= slider.y &&
                            event.button.y < slider.y + slider.h) {
                            pedal_dragging = true;
                            set_pedal_from_pointer(event.button.x, view_width,
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
                session->set_starter(keyboard_starter_held);
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_UP &&
                event.button.button == SDL_BUTTON_LEFT)
                pedal_dragging = false;
            if (session && event.type == SDL_EVENT_WINDOW_FOCUS_LOST &&
                (mouse_starter_held || keyboard_starter_held)) {
                mouse_starter_held = false;
                keyboard_starter_held = false;
                session->set_starter(false);
            }
            if (event.type == SDL_EVENT_WINDOW_FOCUS_LOST)
                pedal_dragging = false;
            if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_R)
                camera = {};
            if (session && event.type == SDL_EVENT_KEY_DOWN &&
                !event.key.repeat) {
                if (event.key.key == SDLK_SPACE)
                    activate_button(LabButtonAction::Pause);
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
            if (!pedal_user_override)
                pedal_pull_m = displayed.pedal_pull_m;
            if (!load_user_override)
                load_engaged = displayed.applied_load_nm > 0.0;
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
        char title[128];
        std::snprintf(title, sizeof(title),
                      "SEVEL MA1.7 | %.0f rpm | RAM47=%u | tick %lld | "
                      "K key, S starter, arrows pedal, L load, Space pause",
                      displayed.rpm, static_cast<unsigned>(displayed.ram47),
                      displayed.tick);
        SDL_SetWindowTitle(window, title);
        RecordingRenderer geometry;
        const float scene_width = static_cast<float>(width) * 0.76f;
        const float scene_height = static_cast<float>(height) * 0.80f;
        camera.pan_x =
            std::clamp(camera.pan_x, -scene_width * 0.5f, scene_width * 0.5f);
        camera.pan_y =
            std::clamp(camera.pan_y, -scene_height * 0.5f, scene_height * 0.5f);
        // Visual afterglow only; electrical pin widths remain in the event
        // trace.
        constexpr long long pulse_span_ticks = 148500;
        std::array<ScenePulse, 4> pulses{};
        std::array<bool, 4> seen{};
        for (auto it = events.rbegin(); it != events.rend(); ++it) {
            if (it->tick > displayed.tick)
                continue;
            if (displayed.tick - it->tick > pulse_span_ticks)
                break;
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
        render_sevel_scene_donor(geometry, displayed, scene_width, scene_height,
                                 {}, {}, camera, &meshes, pulses);
        if (gpu_renderer) {
            int gpu_width = 0;
            int gpu_height = 0;
            if (SDL_GetWindowSizeInPixels(gpu_window, &gpu_width,
                                          &gpu_height) &&
                gpu_width > 0 && gpu_height > 0)
                render_sevel_scene_donor(*gpu_renderer, displayed,
                                         static_cast<float>(gpu_width),
                                         static_cast<float>(gpu_height), {}, {},
                                         camera, &meshes, pulses);
        }
        SDL_SetRenderDrawColor(screen, 15, 22, 34, 255);
        SDL_RenderClear(screen);
        const SDL_Rect scene_clip{0, 0, static_cast<int>(scene_width),
                                  static_cast<int>(scene_height)};
        SDL_SetRenderClipRect(screen, &scene_clip);
        geometry.for_each_triangle([screen](const auto &points,
                                            const ysVector &color) {
            std::array<SDL_Vertex, 3> vertices{};
            for (std::size_t index = 0; index < vertices.size(); ++index) {
                vertices[index].position = {points[index].x, points[index].y};
                vertices[index].color = {std::clamp(color.x, 0.0f, 1.0f),
                                         std::clamp(color.y, 0.0f, 1.0f),
                                         std::clamp(color.z, 0.0f, 1.0f), 1.0f};
            }
            SDL_RenderGeometry(screen, nullptr, vertices.data(),
                               static_cast<int>(vertices.size()), nullptr, 0);
        });
        SDL_SetRenderClipRect(screen, nullptr);
        draw_axial_crank_views(screen, font, displayed, meshes, scene_width,
                               height);
        draw_lab_gauge(
            screen, font, static_cast<float>(width) * 0.86f,
            static_cast<float>(height) * 0.35f, 105.0f, displayed.rpm, 7000.0,
            "RPM", SDL_Color{249, 190, 96, 255}, gauges[0].needlePosition());
        draw_lab_gauge(screen, font, static_cast<float>(width) * 0.81f,
                       static_cast<float>(height) * 0.58f, 52.0f,
                       displayed.throttle_angle_rad * 57.2958, 90.0, "TPS",
                       SDL_Color{99, 211, 220, 255},
                       gauges[1].needlePosition());
        draw_lab_gauge(
            screen, font, static_cast<float>(width) * 0.92f,
            static_cast<float>(height) * 0.58f, 52.0f, displayed.lambda, 5.0,
            "LAM", SDL_Color{200, 144, 232, 255}, gauges[2].needlePosition());
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
                       scope_channels_visible);
        draw_combustion_order(screen, font, scene_width, height, pulses);
        const std::array<bool, 9> button_selected{
            displayed.key_on,
            keyboard_starter_held || mouse_starter_held,
            false,
            false,
            load_engaged,
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
                         button_enabled);
        SDL_SetRenderDrawColor(screen, 235, 241, 246, 255);
        char status[160];
        std::snprintf(status, sizeof(status),
                      "RPM %.0f  TPS %.1f deg  lambda %.2f  coolant %.1f C",
                      displayed.rpm, displayed.throttle_angle_rad * 57.2958,
                      displayed.lambda, displayed.coolant_c);
        font.draw(screen, 24.0f, 24.0f, status, {235, 241, 246, 255});
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
                "key %s  CC3 %llu  burns %llu  faults %02X/%02X  "
                "lost %llu  sound %s",
                displayed.key_on ? "ON" : "off", displayed.injector_pulses,
                displayed.burns, displayed.ram27_faults, displayed.ram28_faults,
                session ? session->event_overflow() : 0ULL, sound_state);
        else
            std::snprintf(
                status, sizeof(status),
                "key %s  CC3 %llu  burns %llu  faults %02X/%02X  "
                "events lost %llu  audio drops %llu  queue empty %llu  "
                "sound %s %.0f%%",
                displayed.key_on ? "ON" : "off", displayed.injector_pulses,
                displayed.burns, displayed.ram27_faults, displayed.ram28_faults,
                session ? session->event_overflow() : 0ULL,
                audio_source ? audio_source->dropped_samples() : 0ULL,
                audio_source ? audio_source->empty_queue_observations() : 0ULL,
                sound_state, sound_volume * 100.0f);
        font.draw(screen, 24.0f, 40.0f, status, {235, 241, 246, 255});
        std::snprintf(status, sizeof(status),
                      "tick %lld  PC %04X  CC3 %u  P5.0 %u  P5.1 %u  "
                      "lamp candidate %s",
                      displayed.tick, static_cast<unsigned>(displayed.pc),
                      displayed.cc3_high ? 1U : 0U,
                      displayed.p50_high ? 1U : 0U,
                      displayed.p51_high ? 1U : 0U,
                      displayed.lamp_on_candidate ? "ON" : "off");
        font.draw(screen, 24.0f, 56.0f, status, {235, 241, 246, 255});
        if (session && !replay_controls && width < 1100)
            font.draw(screen, 24.0f, 72.0f,
                      "K key | S start | arrows pedal | L load | "
                      "Space pause | +/- speed | M mute | Esc exit",
                      {235, 241, 246, 255});
        else if (session && !replay_controls)
            font.draw(screen, 24.0f, 72.0f,
                      "Space pause | K key | S starter | arrows pedal | "
                      "L load | +/- speed | M mute | [ ] volume | "
                      "wheel zoom | middle drag pan | R reset | Esc exit",
                      {235, 241, 246, 255});
        else if (replay_controls)
            font.draw(screen, 24.0f, 72.0f,
                      "REPLAY: engine controls locked | "
                      "Space pause | +/- speed | M mute",
                      {235, 241, 246, 255});
        if (width < 1100)
            std::snprintf(
                status, sizeof(status),
                "TPS1 %.2f  TPS2 %.2f  LAM %.2f V  DROPS %llu  QEMPTY %llu",
                displayed.tps_track1_v, displayed.tps_track2_v,
                displayed.lambda_voltage_v,
                audio_source ? audio_source->dropped_samples() : 0ULL,
                audio_source ? audio_source->empty_queue_observations() : 0ULL);
        else
            std::snprintf(status, sizeof(status),
                          "TPS1 model %.2f V  TPS2 model %.2f V  "
                          "lambda model %.2f V",
                          displayed.tps_track1_v, displayed.tps_track2_v,
                          displayed.lambda_voltage_v);
        font.draw(screen, 24.0f, 88.0f, status, {235, 241, 246, 255});
        std::snprintf(
            status, sizeof(status),
            "pedal %.1f mm  load %.0f Nm  film model %.1f mg  vapor %.1f mg",
            displayed.pedal_pull_m * 1000.0, displayed.applied_load_nm,
            displayed.fuel_film_kg * 1e6, displayed.fuel_vapor_kg * 1e6);
        font.draw(screen, 24.0f, 104.0f, status, {235, 241, 246, 255});
        const SDL_FRect lamp_panel{
            static_cast<float>(width) * 0.78f, 88.0f,
            std::min(210.0f, static_cast<float>(width) * 0.22f - 16.0f), 32.0f};
        SDL_SetRenderDrawColor(screen, 32, 46, 59, 255);
        SDL_RenderFillRect(screen, &lamp_panel);
        const SDL_FRect lamp_square{lamp_panel.x + 8.0f, 96.0f, 16.0f, 16.0f};
        if (displayed.lamp_on_candidate)
            SDL_SetRenderDrawColor(screen, 255, 176, 59, 255);
        else
            SDL_SetRenderDrawColor(screen, 75, 83, 87, 255);
        SDL_RenderFillRect(screen, &lamp_square);
        SDL_SetRenderDrawColor(screen, 235, 241, 246, 255);
        font.draw(screen, lamp_panel.x + 32.0f, 100.0f,
                  width < 1100 ? "LAMP? CAND." : "MA1.7 LAMP? CANDIDATE",
                  {235, 241, 246, 255});
        if (bench_preset) {
            const SDL_FRect bench_panel{lamp_panel.x, 124.0f, lamp_panel.w,
                                        22.0f};
            SDL_SetRenderDrawColor(screen, 46, 39, 30, 255);
            SDL_RenderFillRect(screen, &bench_panel);
            font.draw(screen, bench_panel.x + 8.0f, bench_panel.y + 6.0f,
                      width < 1100 ? "WARM BENCH*"
                                   : "WARM BENCH / CANDIDATE I/O",
                      {249, 190, 96, 255});
        }
        if (!captured && displayed.tick >= capture_after_tick) {
            SDL_Surface *surface = SDL_RenderReadPixels(screen, nullptr);
            captured = surface && save_frame(surface, screenshot_path);
            if (surface)
                SDL_DestroySurface(surface);
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
        std::fprintf(stdout,
                     "[LAB-LIVE] audio_dropped_samples=%llu "
                     "audio_empty_queue=%llu audio_write_errors=%llu\n",
                     audio_source ? audio_source->dropped_samples() : 0ULL,
                     audio_source ? audio_source->empty_queue_observations()
                                  : 0ULL,
                     audio_source ? audio_source->write_errors() : 0ULL);
    gpu_renderer.reset();
    if (gpu_window)
        SDL_DestroyWindow(gpu_window);
    SDL_DestroyRenderer(screen);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return captured;
}

} // namespace lab
