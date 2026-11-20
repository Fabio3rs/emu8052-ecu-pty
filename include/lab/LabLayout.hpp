#pragma once

#include <SDL3/SDL_rect.h>
#include <SDL3/SDL_render.h>

#include <algorithm>
#include <cmath>

namespace lab {

enum class LabPresentationMode { Bench, Analysis, Mechanics };

inline bool render_layout_size(SDL_Renderer *renderer, int *width,
                               int *height) {
    SDL_RendererLogicalPresentation mode{};
    if (!SDL_GetRenderLogicalPresentation(renderer, width, height, &mode))
        return false;
    if (mode != SDL_LOGICAL_PRESENTATION_DISABLED && *width > 0 && *height > 0)
        return true;
    return SDL_GetCurrentRenderOutputSize(renderer, width, height);
}

// Everything the layout depends on besides the output size. Lives in the
// application (LabUiPreferences carries the same fields); LabLayout::compute
// reads it and never writes it.
struct LayoutState {
    float left_fraction = 0.24f;
    float right_fraction = 0.66f;
    float scope_fraction = -1.0f; // <= 0 selects the mode's default height
    LabPresentationMode mode = LabPresentationMode::Bench;
};

// Layout thresholds and minimums, in logical units.
inline constexpr float kDesktopMinWidth = 1100.0f;
inline constexpr float kHeaderHeight = 100.0f; // status panel (to y=68) + toolbar band
inline constexpr float kToolbarHeight = 30.0f; // R/V/F buttons + view titles

struct LabLayout {
    SDL_FRect header{}; // status panel row above the three columns
    SDL_FRect left{};
    SDL_FRect mechanical{};
    SDL_FRect scope{};
    SDL_FRect instruments{};
    // Toolbar (R: FIT / V: / F: and the view titles) sits at the bottom of the
    // header over the mechanical column; `scene` is the mechanical panel below
    // it, so no button or title can intersect the engine viewports (L2).
    SDL_FRect toolbar{};
    SDL_FRect scene{};

    // --- Pure layout (no global state) ------------------------------------
    // The state that is actually in force at an output width: compact windows
    // (< kDesktopMinWidth) ignore the saved mode and scope fraction.
    static LayoutState effective(const LayoutState &state, float output_w) {
        if (output_w >= kDesktopMinWidth)
            return state;
        return {state.left_fraction, state.right_fraction, -1.0f,
                LabPresentationMode::Bench};
    }

    // `state` must already be effective for the output width (see effective()).
    static float scope_height(const LayoutState &state, float panel_width,
                              float height, bool maximized = false) {
        if (maximized)
            return std::max(0.0f, height - 112.0f);
        if (state.scope_fraction > 0.0f) {
            const float maximum = std::max(120.0f, height - 300.0f);
            return std::clamp(height * state.scope_fraction,
                              std::min(180.0f, maximum), maximum);
        }
        if (state.mode == LabPresentationMode::Analysis)
            return std::min(height * 0.56f, std::max(0.0f, height - 112.0f));
        if (state.mode == LabPresentationMode::Mechanics)
            return std::min(std::max(180.0f, height * 0.25f),
                            std::max(0.0f, height - 112.0f));
        if (height < 620.0f)
            return std::min(std::max(96.0f, height * 0.28f),
                            std::max(0.0f, height - 112.0f));
        const float requested =
            panel_width < 460.0f ? 146.0f : std::max(248.0f, height * 0.40f);
        return std::min(requested, std::max(0.0f, height - 112.0f));
    }

    static LabLayout compute(const LayoutState &saved, float w, float h,
                             bool scope_maximized = false) {
        const LayoutState state = effective(saved, w);
        const bool desktop = w >= kDesktopMinWidth;
        const float left_w =
            desktop ? std::clamp(w * state.left_fraction, 220.0f, w - 640.0f)
                    : 0.0f;
        const float mechanical_w =
            desktop ? std::clamp(w * state.right_fraction, left_w + 360.0f,
                                 w - 280.0f) -
                          left_w
                    : w * 0.66f;
        const float scope_h =
            scope_height(state, mechanical_w, h, scope_maximized);
        const float mechanical_h = std::max(0.0f, h - scope_h - 12.0f);
        const float header_h = std::min(kHeaderHeight, h);
        const float toolbar_h = std::min(kToolbarHeight, header_h);
        const float toolbar_y = header_h - toolbar_h;
        const float scene_h = std::max(0.0f, mechanical_h - header_h);
        return {{0.0f, 0.0f, w, header_h},
                {0.0f, 0.0f, left_w, h},
                {left_w, 0.0f, mechanical_w, mechanical_h},
                {left_w, mechanical_h, mechanical_w, scope_h},
                {left_w + mechanical_w, 0.0f, w - left_w - mechanical_w, h},
                {left_w, toolbar_y, mechanical_w, toolbar_h},
                {left_w, header_h, mechanical_w, scene_h}};
    }

    // Which divider (1 left, 2 right, 3 scope) is under (x, y); 0 for none.
    static int divider_at(const LayoutState &state, float x, float y, float w,
                          float h) {
        if (w < kDesktopMinWidth || y < kHeaderHeight || y >= h - 16.0f)
            return 0;
        const LabLayout layout = compute(state, w, h);
        if (std::abs(x - layout.left.w) <= 7.0f)
            return 1;
        if (std::abs(x - layout.instruments.x) <= 7.0f)
            return 2;
        if (x >= layout.mechanical.x + 16.0f &&
            x < layout.instruments.x - 16.0f &&
            std::abs(y - layout.scope.y) <= 7.0f)
            return 3;
        return 0;
    }

    // New state after dragging `divider` to (x, y); the input is unchanged.
    static LayoutState with_divider_moved(LayoutState state, int divider,
                                          float x, float y, float w, float h) {
        if (w < kDesktopMinWidth)
            return state;
        if (divider == 1)
            state.left_fraction =
                std::clamp(x, 220.0f, w * state.right_fraction - 360.0f) / w;
        else if (divider == 2)
            state.right_fraction =
                std::clamp(x, w * state.left_fraction + 360.0f, w - 280.0f) / w;
        else if (divider == 3) {
            const float maximum = std::max(120.0f, h - 300.0f);
            const float minimum = std::min(180.0f, maximum);
            state.scope_fraction =
                std::clamp(h - y - 12.0f, minimum, maximum) / h;
        }
        return state;
    }
};

} // namespace lab
