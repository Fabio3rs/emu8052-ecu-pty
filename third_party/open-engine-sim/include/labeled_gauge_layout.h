#ifndef ATG_ENGINE_SIM_LABELED_GAUGE_LAYOUT_H
#define ATG_ENGINE_SIM_LABELED_GAUGE_LAYOUT_H

#include "ui_math.h"

#include <algorithm>

// Presentation-only layout from LabeledGauge::render. The Lab supplies its
// own text renderer and SEVEL data without constructing EngineSimApplication.
struct LabeledGaugeLayout {
    Bounds title;
    Bounds gauge;
    Bounds value;
    Point center;
    float radius;
    float needle_inner_radius;
    float needle_outer_radius;
    float value_font_size;
};

inline LabeledGaugeLayout labeled_gauge_layout(const Bounds &frame,
                                                float margin = 10.0f,
                                                float center_offset = -20.0f) {
    const Bounds bounds = frame.inset(margin);
    const Bounds title = bounds.verticalSplit(0.9f, 1.0f);
    const Bounds gauge = bounds.verticalSplit(0.0f, 0.9f);
    const float radius = std::min(gauge.width(), gauge.height()) / 2.0f;
    return {title, gauge, gauge.verticalSplit(0.0f, 2.0f / 8.0f),
            gauge.getPosition(Bounds::center) + Point(0.0f, center_offset),
            radius, radius * 0.1f, radius * 0.7f, gauge.height() / 8.0f};
}

#endif /* ATG_ENGINE_SIM_LABELED_GAUGE_LAYOUT_H */
