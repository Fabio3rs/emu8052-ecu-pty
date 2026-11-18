#ifndef ATG_ENGINE_SIM_RIGHT_GAUGE_LAYOUT_H
#define ATG_ENGINE_SIM_RIGHT_GAUGE_LAYOUT_H

#include "ui_math.h"

// Cell hierarchy from RightGaugeCluster::renderTachSpeedCluster,
// renderFuelAirCluster and AfrCluster::render.
struct RightGaugeLayout {
    Bounds tachometer;
    Bounds speedometer;
    Bounds ignition;
    Bounds throttle;
    Bounds oxygen_voltage;
    Bounds lambda;
    Bounds fuel;
    Bounds manifold_pressure;
    Bounds air_flow;
    Bounds volumetric_efficiency;
};

inline RightGaugeLayout right_gauge_layout(const Bounds &frame) {
    const Bounds top = frame.verticalSplit(0.5f, 1.0f);
    const Bounds bottom = frame.verticalSplit(0.0f, 0.5f);
    const Bounds top_left = top.horizontalSplit(0.0f, 0.5f);
    const Bounds bottom_left = bottom.horizontalSplit(0.0f, 0.5f);
    const Bounds bottom_right = bottom.horizontalSplit(0.5f, 1.0f);
    const Bounds fuel_section = bottom_left.verticalSplit(0.0f, 0.5f);
    const Bounds afr = fuel_section.horizontalSplit(0.0f, 0.5f);
    return {
        top_left.verticalSplit(0.5f, 1.0f),
        top_left.verticalSplit(0.0f, 0.5f),
        top.horizontalSplit(0.5f, 1.0f),
        bottom_left.verticalSplit(0.5f, 1.0f),
        afr.verticalSplit(0.5f, 1.0f),
        afr.verticalSplit(0.0f, 0.5f),
        fuel_section.horizontalSplit(0.5f, 1.0f),
        bottom_right.verticalSplit(2.0f / 3.0f, 1.0f),
        bottom_right.verticalSplit(1.0f / 3.0f, 2.0f / 3.0f),
        bottom_right.verticalSplit(0.0f, 1.0f / 3.0f)};
}

// Relative throttle-control frame from RightGaugeCluster::throttleControlBounds.
// The input is the throttle cell; Bounds use the donor's bottom-up Y axis.
inline Bounds right_gauge_throttle_control(const Bounds &throttle) {
    return throttle.horizontalSplit(0.84f, 0.96f)
        .verticalSplit(0.12f, 0.82f);
}

#endif /* ATG_ENGINE_SIM_RIGHT_GAUGE_LAYOUT_H */
