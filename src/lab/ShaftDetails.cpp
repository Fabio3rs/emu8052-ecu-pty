#include "lab/ShaftDetails.hpp"

#include "lab/LabTheme.hpp"
#include "lab/DuctColor.hpp"
#include "lab/PistonShade.hpp"
#include "lab/RodSection.hpp"
#include "lab/SevelGeometry.hpp"
#include "lab/SevelSegments.hpp"
#include "lab/SevelValves.hpp"

#include <SDL3/SDL.h>

#include <algorithm>
#include <array>
#include <cmath>

namespace lab {

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
        static_cast<float>(sevel_head_face_y_m(geometry));
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

        SDL_SetRenderDrawColor(screen, 0, 229, 255,
                               intake_duct_alpha(snapshot.manifold_pressure_pa));
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

    // 2b. SOHC camshaft: one lobe per valve turning at half crank speed, its
    // nose at the tappet exactly at the middle of the lift.
    {
        constexpr float base_r = 0.0085f;
        constexpr float nose_r = 0.0135f;
        constexpr int segments = 36;
        SDL_SetRenderDrawColor(screen, 130, 150, 170, 200);
        const SDL_FPoint axis_a = project(-1.5f * pitch - 0.021f, cam_y);
        const SDL_FPoint axis_b = project(1.5f * pitch + 0.021f, cam_y);
        SDL_RenderLine(screen, axis_a.x, axis_a.y, axis_b.x, axis_b.y);
        for (int cylinder = 0; cylinder < 4; ++cylinder) {
            const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
            for (int valve = 0; valve < 2; ++valve) {
                const auto kind =
                    valve == 0 ? ValveKind::Intake : ValveKind::Exhaust;
                const float x = center + (valve == 0 ? -0.021f : 0.021f);
                const float nose = static_cast<float>(valve_cam_angle_rad(
                    snapshot.crank_angle_rad, static_cast<std::size_t>(cylinder),
                    kind, snapshot.tdc_phase_rad));
                SDL_SetRenderDrawColor(screen, 175, 190, 205, 230);
                SDL_FPoint previous{};
                for (int step = 0; step <= segments; ++step) {
                    const float theta = 2.0f * pi * static_cast<float>(step) /
                                        static_cast<float>(segments);
                    // theta is measured from straight down; the lobe bulges
                    // towards `nose`.
                    const float bump =
                        std::max(0.0f, std::cos(theta - nose));
                    const float r = base_r + (nose_r - base_r) * bump * bump *
                                                 bump * bump;
                    const SDL_FPoint point =
                        project(x + r * std::sin(theta), cam_y - r * std::cos(theta));
                    if (step > 0)
                        SDL_RenderLine(screen, previous.x, previous.y, point.x,
                                       point.y);
                    previous = point;
                }
            }
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
        // M2: one orthographic projection. The throw's depth (sin) is not
        // drawn as an x-offset: that oblique shift is what made the rod lines
        // miss the scene's rods and show up as '///'.
        const float throw_x = 0.0f;
        const float piston_y = static_cast<float>(pose.piston_pin_y_m);

        const SDL_FPoint p_crank = project(center + throw_x, crank_y);
        const SDL_FPoint p_wrist = project(center, piston_y);

        const float counter_y = -crank_r * std::cos(cyl_phase) * 0.85f;

        // Counterweight web: a filled quad in metres (it scales with zoom and
        // matches the scene's cylN-web segment), not three pixel-wide lines.
        {
            constexpr float half_width_m = 0.0035f;
            const SDL_FColor web{85.0f / 255.0f, 95.0f / 255.0f, 110.0f / 255.0f,
                                 1.0f};
            const SDL_FPoint a = project(center - half_width_m, 0.0f);
            const SDL_FPoint b = project(center + half_width_m, 0.0f);
            const SDL_FPoint c = project(center + half_width_m, counter_y);
            const SDL_FPoint d = project(center - half_width_m, counter_y);
            const SDL_Vertex quad[6] = {{a, web, {}}, {b, web, {}}, {c, web, {}},
                                        {a, web, {}}, {c, web, {}}, {d, web, {}}};
            SDL_RenderGeometry(screen, nullptr, quad, 6, nullptr, 0);
        }

        // Connecting rod beam as an "I": bright flanges either side of a
        // darker web.
        {
            const RodNormal normal =
                rod_normal(p_crank.x, p_crank.y, p_wrist.x, p_wrist.y);
            const float flange = 2.2f * ui_scale;
            SDL_SetRenderDrawColor(screen, 120, 132, 146, 255); // web
            SDL_RenderLine(screen, p_crank.x, p_crank.y, p_wrist.x, p_wrist.y);
            SDL_SetRenderDrawColor(screen, 225, 233, 242, 255); // flanges
            for (const float side : {-1.0f, 1.0f})
                SDL_RenderLine(screen, p_crank.x + normal.x * flange * side,
                               p_crank.y + normal.y * flange * side,
                               p_wrist.x + normal.x * flange * side,
                               p_wrist.y + normal.y * flange * side);
        }

        // Big-end journal cap
        SDL_SetRenderDrawColor(screen, 240, 245, 250, 255);
        const float r_big = 3.5f * ui_scale;
        const SDL_FRect big_journal{p_crank.x - r_big, p_crank.y - r_big,
                                    r_big * 2.0f, r_big * 2.0f};
        SDL_RenderFillRect(screen, &big_journal);
        // Cap bolts either side of the journal.
        SDL_SetRenderDrawColor(screen, 52, 58, 68, 255);
        for (const float side : {-1.0f, 1.0f}) {
            const SDL_FRect bolt{p_crank.x + side * r_big * 1.9f - 1.0f * ui_scale,
                                 p_crank.y - 1.0f * ui_scale, 2.0f * ui_scale,
                                 2.0f * ui_scale};
            SDL_RenderFillRect(screen, &bolt);
        }

        // Cylindrical shading of the piston body: edges darker, a highlight
        // a third of the way in (vertical strips across its width).
        {
            constexpr int strips = 12;
            constexpr float half_width_m = 0.042f;
            const SDL_FPoint top_left =
                project(center - half_width_m, piston_y + 0.023f);
            const SDL_FPoint bottom_right =
                project(center + half_width_m, piston_y - 0.040f);
            const float strip_w = (bottom_right.x - top_left.x) /
                                  static_cast<float>(strips);
            SDL_SetRenderDrawBlendMode(screen, SDL_BLENDMODE_BLEND);
            for (int strip = 0; strip < strips; ++strip) {
                const double t = (strip + 0.5) / strips;
                const SDL_FRect band{top_left.x + strip_w * static_cast<float>(strip),
                                     top_left.y, strip_w + 1.0f,
                                     bottom_right.y - top_left.y};
                const unsigned char dark = piston_shade_alpha(t);
                if (dark > 0) {
                    SDL_SetRenderDrawColor(screen, 0, 0, 0, dark);
                    SDL_RenderFillRect(screen, &band);
                }
                const unsigned char light = piston_highlight_alpha(t);
                if (light > 0) {
                    SDL_SetRenderDrawColor(screen, 255, 255, 255, light);
                    SDL_RenderFillRect(screen, &band);
                }
            }
        }

        // Piston details: wrist pin & the three rings (2 compression + oil),
        // placed by metres below the crown so they follow the camera zoom.
        const float bore_px = project(center + bore_m * 0.38f, piston_y).x -
                              project(center - bore_m * 0.38f, piston_y).x;

        SDL_SetRenderDrawColor(screen, 38, 40, 48, 255);
        const float ring_w = bore_px * 0.90f;
        for (const double depth : kSevelPistonRingDepthsM) {
            const SDL_FPoint ring =
                project(center, piston_y + 0.010f - static_cast<float>(depth));
            SDL_RenderLine(screen, ring.x - ring_w * 0.5f, ring.y,
                           ring.x + ring_w * 0.5f, ring.y);
        }

        // Wrist pin boss (the thickened piston wall round the pin) and hole
        const float r_pin = 2.5f * ui_scale;
        {
            const SDL_FRect boss{p_wrist.x - r_pin * 2.6f, p_wrist.y - r_pin * 1.5f,
                                 r_pin * 5.2f, r_pin * 3.0f};
            SDL_SetRenderDrawColor(screen, 92, 100, 112, 255);
            SDL_RenderFillRect(screen, &boss);
        }
        const SDL_FRect pin_rect{p_wrist.x - r_pin, p_wrist.y - r_pin,
                                 r_pin * 2.0f, r_pin * 2.0f};
        SDL_SetRenderDrawColor(screen, 28, 30, 36, 255);
        SDL_RenderFillRect(screen, &pin_rect);
        SDL_SetRenderDrawColor(screen, 180, 195, 210, 255);
        SDL_RenderRect(screen, &pin_rect);
    }
}

} // namespace lab
