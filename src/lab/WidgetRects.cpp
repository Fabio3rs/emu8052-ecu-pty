#include "lab/WidgetRects.hpp"

#include "lab/LabButtons.hpp"

#include <algorithm>

namespace lab {

namespace {
int g_configured_ui_scale_percent = 0;
} // namespace

void set_configured_ui_scale_percent(int percent) {
    g_configured_ui_scale_percent = percent;
}

float lab_ui_scale(int width, int height) {
    if (g_configured_ui_scale_percent != 0)
        return 1.0f;
    return std::clamp(std::min(static_cast<float>(width) / 1280.0f,
                               static_cast<float>(height) / 720.0f),
                      1.0f, 2.0f);
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
    // L2: every toolbar button lives inside LabLayout::toolbar. The header
    // (status panel, toolbar, view titles) scales with the UI scale, so the
    // toolbar band does too.
    const LabLayout layout = layout_for(layout_state, width, height);
    const SDL_FRect toolbar = layout.toolbar;
    const float scale = lab_ui_scale(width, height);
    const float inset = 2.0f;
    const float top = (toolbar.y + inset) * scale;
    const float band_h = (toolbar.h - 2.0f * inset) * scale;
    if (width < 1280 || height < 720) {
        const SDL_FRect mechanical = layout.mechanical;
        return {mechanical.x + mechanical.w - 116.0f, top, 52.0f, band_h};
    }
    const float right = layout.mechanical.x + layout.mechanical.w - 15.0f * scale;
    return {right - (122.0f + 8.0f + 80.0f) * scale, top, 122.0f * scale,
            band_h};
}

SDL_FRect fit_button_rect(const LayoutState &layout_state, int width,
                          int height) {
    const SDL_FRect selector = view_selector_rect(layout_state, width, height);
    if (width < 1280 || height < 720)
        return {selector.x + 58.0f, selector.y, 42.0f, selector.h};
    const float scale = lab_ui_scale(width, height);
    return {selector.x - 78.0f * scale, selector.y, 70.0f * scale, selector.h};
}

// C3: three equal segments at the left of the toolbar band (desktop sizes).
SDL_FRect speed_selector_rect(const LayoutState &layout_state, int width,
                              int height) {
    const SDL_FRect selector = view_selector_rect(layout_state, width, height);
    const LabLayout layout = layout_for(layout_state, width, height);
    const float scale = lab_ui_scale(width, height);
    return {layout.mechanical.x + 15.0f * scale, selector.y, 186.0f * scale,
            selector.h};
}

// The selector is shown (and clickable) only when it ends before the FIT
// button; in a narrow mechanical column it would overlap the view buttons.
bool speed_selector_visible(const LayoutState &layout_state, int width,
                            int height) {
    if (width < 1280 || height < 720)
        return false;
    const SDL_FRect speed = speed_selector_rect(layout_state, width, height);
    const SDL_FRect fit = fit_button_rect(layout_state, width, height);
    return speed.x + speed.w + 8.0f * lab_ui_scale(width, height) <= fit.x;
}

SDL_FRect fullscreen_button_rect(const LayoutState &layout_state, int width,
                                 int height) {
    const SDL_FRect selector = view_selector_rect(layout_state, width, height);
    const float scale = lab_ui_scale(width, height);
    return {selector.x + selector.w + 8.0f * scale, selector.y, 80.0f * scale,
            selector.h};
}

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
    // L7: GEAR sits in the right half of the left column and CLUTCH (drawn by
    // clutch_widget_rect) in the left half, so neither is isolated.
    const float gap = 8.0f * scale;
    const float card_w =
        std::min(90.0f * scale, (panel_w - 32.0f * scale - gap) * 0.5f);
    const float gear_x = panel_w * 0.5f + gap * 0.5f;
    if (bottom - top >= 64.0f)
        return {gear_x, top, card_w, bottom - top};
    // Keep the donor gear control below the volume bar on shorter desktops.
    return {gear_x, static_cast<float>(height) - 92.0f, card_w, 84.0f};
}

// The clutch dial next to GEAR for desktops below the 1800x1000 layout (that
// layout draws it from the same gear rect).
SDL_FRect clutch_widget_rect(const LayoutState &layout_state, int width,
                             int height) {
    const SDL_FRect gear = gear_widget_rect(layout_state, width, height);
    if (gear.w <= 0.0f || width < 1100 || height < 700)
        return {};
    const float scale = lab_ui_scale(width, height);
    return {gear.x - gear.w - 8.0f * scale, gear.y, gear.w, gear.h};
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

} // namespace lab
