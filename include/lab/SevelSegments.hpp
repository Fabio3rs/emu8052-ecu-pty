#pragma once

#include "lab/SevelGeometry.hpp"
#include "lab/SevelValves.hpp"
#include "ma17/EmulatorSnapshot.hpp"
#include "render_math.h"

#include <cstddef>

namespace lab {

struct SceneDimensions {
    double visual_estimate_cylinder_pitch_m = 0.095;
    double visual_estimate_head_height_m = 0.025;
    double visual_estimate_valve_lift_m = 0.007;
};

template <typename Sink>
void for_each_sevel_segment(const ma17::EmulatorSnapshot &snapshot,
                            SevelVisualGeometry geometry,
                            SceneDimensions dimensions, Sink &&add_segment) {
    const ysVector metal{0.55f, 0.67f, 0.72f, 1.0f};
    const ysVector piston_color{0.91f, 0.76f, 0.49f, 1.0f};
    const ysVector housing{0.20f, 0.34f, 0.42f, 1.0f};
    const ysVector intake_color{0.38f, 0.79f, 0.81f, 1.0f};
    const ysVector exhaust_color{0.78f, 0.52f, 0.41f, 1.0f};
    constexpr float bore_m = 0.0864f;
    const float pitch =
        static_cast<float>(dimensions.visual_estimate_cylinder_pitch_m);
    const float head_y =
        static_cast<float>(geometry.visual_estimate_rod_length_m +
                           SevelVisualGeometry::crank_radius_m +
                           dimensions.visual_estimate_head_height_m);
    const auto poses = sevel_cylinder_poses(snapshot.crank_angle_rad, geometry);
    add_segment(-1.6f * pitch, 0.0f, 1.6f * pitch, 0.0f, 0.012f, metal);
    add_segment(-1.7f * pitch, head_y, 1.7f * pitch, head_y, 0.018f, housing);
    for (int cylinder = 0; cylinder < 4; ++cylinder) {
        const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
        const auto &pose = poses[static_cast<std::size_t>(cylinder)];
        const float crank_y = static_cast<float>(pose.crank_pin_y_m);
        const float piston_y = static_cast<float>(pose.piston_pin_y_m);
        add_segment(center - bore_m / 2.0f, -0.045f, center - bore_m / 2.0f,
                    head_y, 0.003f, housing);
        add_segment(center + bore_m / 2.0f, -0.045f, center + bore_m / 2.0f,
                    head_y, 0.003f, housing);
        // Longitudinal view: the crank's radial x motion is depth here.
        // When the throw points into the screen, show its journal end-on.
        if (std::abs(crank_y) < 0.001f)
            add_segment(center - 0.0055f, crank_y, center + 0.0055f, crank_y,
                        0.011f, metal);
        else
            add_segment(center, 0.0f, center, crank_y, 0.011f, metal);
        add_segment(center, crank_y, center, piston_y, 0.010f, metal);
        add_segment(center - bore_m * 0.38f, piston_y, center + bore_m * 0.38f,
                    piston_y, 0.016f, piston_color);
    }
    const float cam_y = head_y + 0.042f;
    add_segment(-1.6f * pitch, cam_y, 1.6f * pitch, cam_y, 0.007f, metal);
    for (int cylinder = 0; cylinder < 4; ++cylinder) {
        const float center = (static_cast<float>(cylinder) - 1.5f) * pitch;
        for (int valve = 0; valve < 2; ++valve) {
            const auto kind =
                valve == 0 ? ValveKind::Intake : ValveKind::Exhaust;
            const float x = center + (valve == 0 ? -0.021f : 0.021f);
            const float lift = static_cast<float>(
                valve_lift_fraction(snapshot.crank_angle_rad,
                                    static_cast<std::size_t>(cylinder), kind) *
                dimensions.visual_estimate_valve_lift_m);
            const float tip_y = head_y + 0.002f - lift;
            const ysVector color = valve == 0 ? intake_color : exhaust_color;
            add_segment(x, head_y + 0.030f, x, tip_y, 0.003f, metal);
            add_segment(x - 0.010f, tip_y, x + 0.010f, tip_y, 0.005f, color);
            add_segment(x, cam_y, x, cam_y - 0.009f - lift * 0.35f, 0.008f,
                        color);
        }
    }
}

} // namespace lab
