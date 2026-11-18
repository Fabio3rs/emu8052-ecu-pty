#ifndef ATG_ENGINE_SIM_GEAR_CARD_LAYOUT_H
#define ATG_ENGINE_SIM_GEAR_CARD_LAYOUT_H

#include "ui_math.h"

#include <algorithm>

// Bands and click zones from LoadSimulationCluster::drawCurrentGear and
// onMouseClick. Bounds use the donor's bottom-up Y axis.
struct GearCardLayout {
    Bounds inner;
    Bounds title;
    Bounds up;
    Bounds body;
    Bounds down;
};

inline GearCardLayout gear_card_layout(const Bounds &frame, float margin) {
    const Bounds inner = frame.inset(margin);
    return {inner,
            inner.verticalSplit(0.86f, 1.0f),
            inner.verticalSplit(0.62f, 0.86f),
            inner.verticalSplit(0.22f, 0.62f),
            inner.verticalSplit(0.0f, 0.22f)};
}

inline float gear_chevron_half_width(const Bounds &band) {
    return std::min(band.width(), band.height()) * 0.28f;
}

#endif /* ATG_ENGINE_SIM_GEAR_CARD_LAYOUT_H */
