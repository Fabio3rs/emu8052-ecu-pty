#pragma once

#include "lab/ThemePalette.hpp"
#include "lab/SevelGeometry.hpp"
#include "lab/SevelValves.hpp"
#include "ma17/EmulatorSnapshot.hpp"
#include "render_math.h"

#include <cstddef>
#include <string>

namespace lab {

struct SceneDimensions {
    double visual_estimate_cylinder_pitch_m = 0.095;
    double visual_estimate_valve_lift_m = 0.007;
};

struct NoGroups {
    void operator()(const std::string &) const {}
};

// `begin_group(id)` is called before each logical piece (cyl1-piston, head,
// ...), so a recorder can label the geometry that follows.
template <typename Sink, typename GroupSink = NoGroups>
void for_each_sevel_segment(const ma17::EmulatorSnapshot &snapshot,
                            SevelVisualGeometry geometry,
                            SceneDimensions dimensions, Sink &&add_segment,
                            GroupSink &&begin_group = GroupSink{}) {
    const ysVector metal{0.80f, 0.83f, 0.88f, 1.0f};
    const ysVector piston_color{0.92f, 0.94f, 0.96f, 1.0f};
    const ysVector housing{0.20f, 0.22f, 0.26f, 1.0f};
    const auto &colors = palette();
    const ysVector intake_color{colors.intake[0], colors.intake[1],
                                colors.intake[2], 1.0f};
    const ysVector exhaust_color{colors.exhaust[0], colors.exhaust[1],
                                 colors.exhaust[2], 1.0f};
    constexpr float bore_m = 0.0864f;
    const float pitch =
        static_cast<float>(dimensions.visual_estimate_cylinder_pitch_m);
    const float head_y =
        static_cast<float>(sevel_head_face_y_m(geometry));
    const float liner_bottom_y =
        static_cast<float>(sevel_liner_bottom_y_m(geometry));
    const auto poses = sevel_cylinder_poses(
        snapshot.crank_angle_rad - snapshot.tdc_phase_rad, geometry);
    begin_group("crankshaft");
    add_segment(-1.6f * pitch, 0.0f, 1.6f * pitch, 0.0f, 0.012f, metal);
    begin_group("head");
    // 18 mm plate whose underside is the head face.
    add_segment(-1.7f * pitch, head_y + 0.009f, 1.7f * pitch, head_y + 0.009f,
                0.018f, housing);
    for (int cylinder = 0; cylinder < 4; ++cylinder) {
        const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
        const auto &pose = poses[static_cast<std::size_t>(cylinder)];
        const float crank_y = static_cast<float>(pose.crank_pin_y_m);
        const float piston_y = static_cast<float>(pose.piston_pin_y_m);
        const std::string tag = "cyl" + std::to_string(cylinder + 1);
        begin_group(tag + "-liner");
        add_segment(center - bore_m / 2.0f, liner_bottom_y, center - bore_m / 2.0f,
                    head_y, 0.003f, housing);
        add_segment(center + bore_m / 2.0f, liner_bottom_y, center + bore_m / 2.0f,
                    head_y, 0.003f, housing);
        begin_group(tag + "-crank");
        // Longitudinal view: the crank's radial x motion is depth here.
        // When the throw points into the screen, show its journal end-on.
        if (std::abs(crank_y) < 0.001f)
            add_segment(center - 0.0055f, crank_y, center + 0.0055f, crank_y,
                        0.011f, metal);
        else
            add_segment(center, 0.0f, center, crank_y, 0.011f, metal);
        begin_group(tag + "-rod");
        add_segment(center, crank_y, center, piston_y, 0.010f, metal);
        begin_group(tag + "-piston");
        add_segment(center - bore_m * 0.38f, piston_y, center + bore_m * 0.38f,
                    piston_y, 0.016f, piston_color);
    }
    const float cam_y = head_y + 0.042f;
    begin_group("camshaft");
    add_segment(-1.6f * pitch, cam_y, 1.6f * pitch, cam_y, 0.007f, metal);
    for (int cylinder = 0; cylinder < 4; ++cylinder) {
        const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
        begin_group("cyl" + std::to_string(cylinder + 1) + "-valves");
        for (int valve = 0; valve < 2; ++valve) {
            const auto kind =
                valve == 0 ? ValveKind::Intake : ValveKind::Exhaust;
            const float x = center + (valve == 0 ? -0.021f : 0.021f);
            const float lift = static_cast<float>(
                valve_lift_fraction(snapshot.crank_angle_rad,
                                    static_cast<std::size_t>(cylinder), kind,
                                    snapshot.tdc_phase_rad) *
                dimensions.visual_estimate_valve_lift_m);
            const float tip_y = head_y + 0.002f - lift;
            const ysVector color = valve == 0 ? intake_color : exhaust_color;
            add_segment(x, head_y + 0.030f, x, tip_y, 0.003f, metal);
            add_segment(x - 0.010f, tip_y, x + 0.010f, tip_y, 0.005f, color);
            add_segment(x, cam_y, x, cam_y - 0.009f - lift * 0.35f, 0.008f,
                        color);
        }
    }

    // M2: counterweight webs as scene geometry (they reach the SVG export and
    // scale with the view). Appended last so the draw-call order and the
    // indices of every earlier segment are unchanged.
    for (int cylinder = 0; cylinder < 4; ++cylinder) {
        const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
        const float web_y =
            -0.85f * static_cast<float>(
                         poses[static_cast<std::size_t>(cylinder)].crank_pin_y_m);
        begin_group("cyl" + std::to_string(cylinder + 1) + "-web");
        add_segment(center, 0.0f, center, web_y, 0.007f,
                    {0.333f, 0.373f, 0.431f, 1.0f});
    }
}

} // namespace lab
