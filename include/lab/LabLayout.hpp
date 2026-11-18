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
    if (mode != SDL_LOGICAL_PRESENTATION_DISABLED &&
        *width > 0 && *height > 0)
        return true;
    return SDL_GetCurrentRenderOutputSize(renderer, width, height);
}

struct LabLayout {
    SDL_FRect left{};
    SDL_FRect mechanical{};
    SDL_FRect scope{};
    SDL_FRect instruments{};

    inline static float desktop_left_fraction = 0.24f;
    inline static float desktop_right_fraction = 0.66f;
    inline static float desktop_scope_fraction = -1.0f;
    inline static float active_scope_fraction = -1.0f;
    inline static LabPresentationMode desktop_mode = LabPresentationMode::Bench;
    inline static LabPresentationMode active_mode = LabPresentationMode::Bench;

    static int divider_at(float x, float y, int width, int height) {
        if (width < 1100 || y < 90.0f ||
            y >= static_cast<float>(height) - 16.0f)
            return 0;
        const LabLayout layout = for_output(width, height);
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

    static void move_divider(int divider, float x, float y,
                             int width, int height) {
        if (width < 1100)
            return;
        const float w = static_cast<float>(width);
        if (divider == 1)
            desktop_left_fraction =
                std::clamp(x, 220.0f, w * desktop_right_fraction - 360.0f) / w;
        else if (divider == 2)
            desktop_right_fraction =
                std::clamp(x, w * desktop_left_fraction + 360.0f,
                           w - 280.0f) / w;
        else if (divider == 3) {
            const float h = static_cast<float>(height);
            const float maximum = std::max(120.0f, h - 300.0f);
            const float minimum = std::min(180.0f, maximum);
            desktop_scope_fraction =
                std::clamp(h - y - 12.0f, minimum, maximum) / h;
        }
    }

    static float scope_panel_height(float panel_width, float height,
                                    bool maximized = false) {
        if (maximized)
            return std::max(0.0f, height - 112.0f);
        if (active_scope_fraction > 0.0f) {
            const float maximum = std::max(120.0f, height - 300.0f);
            return std::clamp(height * active_scope_fraction,
                              std::min(180.0f, maximum), maximum);
        }
        if (active_mode == LabPresentationMode::Analysis)
            return std::min(height * 0.56f,
                            std::max(0.0f, height - 112.0f));
        if (active_mode == LabPresentationMode::Mechanics)
            return std::min(std::max(180.0f, height * 0.25f),
                            std::max(0.0f, height - 112.0f));
        if (height < 620.0f)
            return std::min(std::max(96.0f, height * 0.28f),
                            std::max(0.0f, height - 112.0f));
        const float requested = panel_width < 460.0f
                                    ? 146.0f
                                    : std::max(248.0f, height * 0.40f);
        return std::min(requested, std::max(0.0f, height - 112.0f));
    }

    static LabLayout for_output(int width, int height,
                                bool scope_maximized = false) {
        active_mode = width >= 1100 ? desktop_mode
                                    : LabPresentationMode::Bench;
        active_scope_fraction = width >= 1100 ? desktop_scope_fraction : -1.0f;
        const float w = static_cast<float>(width);
        const float h = static_cast<float>(height);
        const float left_w = width >= 1100
                                 ? std::clamp(w * desktop_left_fraction,
                                              220.0f, w - 640.0f)
                                 : 0.0f;
        const float mechanical_w = width >= 1100
                                       ? std::clamp(w * desktop_right_fraction,
                                                    left_w + 360.0f,
                                                    w - 280.0f) - left_w
                                       : w * 0.66f;
        const float scope_h = scope_panel_height(mechanical_w, h,
                                                  scope_maximized);
        const float mechanical_h = std::max(0.0f, h - scope_h - 12.0f);
        return {{0.0f, 0.0f, left_w, h},
                {left_w, 0.0f, mechanical_w, mechanical_h},
                {left_w, mechanical_h, mechanical_w, scope_h},
                {left_w + mechanical_w, 0.0f,
                 w - left_w - mechanical_w, h}};
    }
};

} // namespace lab
