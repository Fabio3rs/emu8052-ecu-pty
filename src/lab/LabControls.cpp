#include "lab/LabControls.hpp"
#include "lab/TextScale.hpp"

#include "engine/ControlLimits.hpp"
#include "lab/EcuBadges.hpp"
#include "lab/LabButtons.hpp"
#include "lab/LabTheme.hpp"
#include "lab/SliderGeometry.hpp"

#include <SDL3/SDL.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>

namespace lab {

// D4: a row of ECU state badges above the button grid. Solid = confirmed
// signal, dashed = candidate; active ones are tinted in the accent colour.
void draw_ecu_badges(SDL_Renderer *screen, FontRenderer &font, int width,
                     int height, float left_width, float scale,
                     const ma17::EmulatorSnapshot &snapshot) {
    if (width < 1100 || !lab_buttons_visible(width, height))
        return;
    const auto first = lab_button_rect(0, width, height, left_width);
    const float h = 18.0f * scale;
    const float y = first.y - h - 6.0f * scale;
    float x = first.x;
    const float text_scale = kTextSmall * scale;
    for (const EcuBadge &badge : ecu_badges(snapshot)) {
        const float w = font.width(badge.text, text_scale) + 12.0f * scale;
        if (x + w > left_width - 16.0f)
            break;
        const SDL_FRect box{x, y, w, h};
        const SDL_Color tint = badge.candidate ? kPairB : kAccent;
        if (badge.active) {
            SDL_SetRenderDrawColor(screen, static_cast<Uint8>(tint.r / 5),
                                   static_cast<Uint8>(tint.g / 5),
                                   static_cast<Uint8>(tint.b / 5), 255);
            SDL_RenderFillRect(screen, &box);
        }
        const SDL_Color frame = badge.active ? tint : SDL_Color{58, 66, 78, 255};
        set_draw_color(screen, frame);
        if (badge.candidate) { // dashed outline: not a confirmed state
            const float dash = 4.0f * scale;
            for (float dx = 0.0f; dx < w; dx += 2.0f * dash) {
                const float len = std::min(dash, w - dx);
                SDL_RenderLine(screen, x + dx, y, x + dx + len, y);
                SDL_RenderLine(screen, x + dx, y + h, x + dx + len, y + h);
            }
            for (float dy = 0.0f; dy < h; dy += 2.0f * dash) {
                const float len = std::min(dash, h - dy);
                SDL_RenderLine(screen, x, y + dy, x, y + dy + len);
                SDL_RenderLine(screen, x + w, y + dy, x + w, y + dy + len);
            }
        } else {
            SDL_RenderRect(screen, &box);
        }
        font.draw(screen, x + 6.0f * scale,
                  y + (h - font.line_height(font.text_px(text_scale))) * 0.5f,
                  badge.text,
                  badge.active ? SDL_Color{235, 241, 246, 255}
                               : SDL_Color{110, 122, 134, 255},
                  text_scale);
        x += w + 6.0f * scale;
    }
}

void draw_lab_buttons(SDL_Renderer *screen, FontRenderer &font, int width,
                      int height, float left_width, float scale,
                      const std::array<bool, 9> &selected,
                      const std::array<bool, 9> &enabled, double load_nm,
                      bool replay_locked) {
    if (!lab_buttons_visible(width, height))
        return;
    float mouse_x = 0.0f;
    float mouse_y = 0.0f;
    const auto mouse_state = SDL_GetMouseState(&mouse_x, &mouse_y);
    const bool has_pointer = SDL_RenderCoordinatesFromWindow(
        screen, mouse_x, mouse_y, &mouse_x, &mouse_y);
    const auto hovered =
        has_pointer
            ? hit_test_lab_button(mouse_x, mouse_y, width, height, left_width)
            : LabButtonAction::None;
    for (std::size_t index = 0; index < lab_button_labels.size(); ++index) {
        const auto action = static_cast<LabButtonAction>(index);
        const bool over = action == hovered;
        const bool held = over && (mouse_state & SDL_BUTTON_LMASK) != 0;
        const auto bounds = lab_button_rect(index, width, height, left_width);
        const SDL_FRect box{bounds.x, bounds.y, bounds.width, bounds.height};
        // C1: five states (normal, hover, pressed, on, disabled) with a
        // per-action accent; "on" is a tinted fill plus a side bar, never a
        // solid white block.
        const LabButtonVisual visual = compute_button_visual(
            action, selected[index], held, over, enabled[index]);
        const auto sdl_color = [](const ButtonRgba &color) {
            return SDL_Color{color.r, color.g, color.b, color.a};
        };
        const SDL_Color fill = sdl_color(visual.fill);
        const SDL_Color frame = sdl_color(visual.frame);
        SDL_SetRenderDrawColor(screen, fill.r, fill.g, fill.b, fill.a);
        SDL_RenderFillRect(screen, &box);
        SDL_SetRenderDrawColor(screen, frame.r, frame.g, frame.b, frame.a);
        SDL_RenderRect(screen, &box);
        if (visual.bar_width > 0.0f) {
            const SDL_Color bar = sdl_color(visual.bar);
            const SDL_FRect bar_rect{box.x, box.y, visual.bar_width * scale,
                                     box.h};
            SDL_SetRenderDrawColor(screen, bar.r, bar.g, bar.b, bar.a);
            SDL_RenderFillRect(screen, &bar_rect);
        }
        if (!enabled[index] && replay_locked) {
            // Padlock in the corner: replay owns the physical controls.
            const float lw = 6.0f * scale, lh = 5.0f * scale;
            const float lx = box.x + box.w - lw - 4.0f * scale;
            const float ly = box.y + box.h - lh - 4.0f * scale;
            const SDL_Color lock = sdl_color(visual.text);
            SDL_SetRenderDrawColor(screen, lock.r, lock.g, lock.b, lock.a);
            const SDL_FRect body{lx, ly, lw, lh};
            SDL_RenderFillRect(screen, &body);
            SDL_RenderLine(screen, lx + 1.0f * scale, ly, lx + 1.0f * scale,
                           ly - 2.0f * scale);
            SDL_RenderLine(screen, lx + lw - 1.0f * scale, ly,
                           lx + lw - 1.0f * scale, ly - 2.0f * scale);
            SDL_RenderLine(screen, lx + 1.0f * scale, ly - 2.0f * scale,
                           lx + lw - 1.0f * scale, ly - 2.0f * scale);
        }
        std::string label(lab_button_labels[index]);
        if (action == LabButtonAction::Load) {
            const SDL_FRect fill_bar{
                box.x + 2.0f, box.y + box.h - 5.0f * scale,
                (box.w - 4.0f) *
                    static_cast<float>(std::clamp(load_nm / engine::lab_load_slider_span_nm, 0.0, 1.0)),
                3.0f * scale};
            set_draw_color(screen, kAccent);
            SDL_RenderFillRect(screen, &fill_bar);
            char load_label[16];
            std::snprintf(load_label, sizeof(load_label), "LOAD %.0f", load_nm);
            label = load_label;
        }
        const SDL_Color label_color = sdl_color(visual.text);
        const float text_scale = bounds.height < 36.0f ? kTextSmall * scale : scale;
        if (action == LabButtonAction::Starter) {
            if (bounds.height < 36.0f) {
                font.draw(screen,
                          bounds.x + (bounds.width -
                                      font.width(label, text_scale)) /
                                         2.0f,
                          bounds.y + 6.0f * scale, label, label_color,
                          text_scale);
                continue;
            }
            font.draw(
                screen,
                bounds.x + (bounds.width - font.width(label, scale)) / 2.0f,
                bounds.y + bounds.height * 0.05f, label, label_color, scale);
            const std::string hint = "HOLD";
            const float hint_scale = kTextSmall * scale;
            font.draw(screen,
                      bounds.x +
                          (bounds.width - font.width(hint, hint_scale)) /
                              2.0f,
                      bounds.y + bounds.height * 0.60f, hint, label_color,
                      hint_scale);
            continue;
        }
        font.draw(screen,
                  bounds.x +
                      (bounds.width - font.width(label, text_scale)) / 2.0f,
                  bounds.y + (bounds.height - font.line_height(font.text_px(text_scale))) / 2.0f - 1.0f,
                  label, label_color, text_scale);
    }
    // C5: tooltip with the shortcut for the hovered button, above everything.
    if (hovered != LabButtonAction::None) {
        const auto index = static_cast<std::size_t>(hovered);
        const auto bounds = lab_button_rect(index, width, height, left_width);
        const std::string text(lab_button_tooltips[index]);
        const float tip_scale = kTextSmall * scale;
        const float w = font.width(text, tip_scale) + 10.0f * scale;
        const float h = font.line_height(font.text_px(tip_scale)) + 8.0f * scale;
        const float x = std::clamp(bounds.x, 4.0f, std::max(4.0f, left_width - w - 4.0f));
        const float y = bounds.y - h - 4.0f * scale;
        const SDL_FRect box{x, y, w, h};
        SDL_SetRenderDrawColor(screen, 10, 14, 20, 245);
        SDL_RenderFillRect(screen, &box);
        SDL_SetRenderDrawColor(screen, 90, 200, 215, 255);
        SDL_RenderRect(screen, &box);
        font.draw(screen, x + 5.0f * scale, y + 4.0f * scale, text,
                  {235, 241, 246, 255}, tip_scale);
    }
    // C5: shortcut hints, drawn over the finished buttons.
    for (std::size_t index = 0; index < lab_button_labels.size(); ++index) {
        const auto bounds = lab_button_rect(index, width, height, left_width);
        if (bounds.height < 30.0f || bounds.width < 52.0f * scale ||
            !enabled[index])
            continue;
        const auto &shortcut = lab_button_shortcuts[index];
        const float hint_scale = kTextTiny * scale;
        const SDL_Color dim{145, 177, 190, 255};
        if (shortcut.underline_first) {
            // Underline the first letter of the label where it is drawn.
            std::string label(lab_button_labels[index]);
            if (static_cast<LabButtonAction>(index) == LabButtonAction::Load) {
                char load_label[16];
                std::snprintf(load_label, sizeof(load_label), "LOAD %.0f",
                              load_nm);
                label = load_label;
            }
            const float text_scale = scale;
            // Same condition as the label drawing: START is two lines only on
            // buttons at least 36 px tall.
            const bool two_line =
                static_cast<LabButtonAction>(index) == LabButtonAction::Starter &&
                bounds.height >= 36.0f;
            const float text_y =
                two_line ? bounds.y + bounds.height * 0.05f
                         : bounds.y +
                               (bounds.height -
                                font.line_height(font.text_px(text_scale))) /
                                   2.0f -
                               1.0f;
            const float x0 =
                bounds.x +
                (bounds.width - font.width(label, text_scale)) / 2.0f;
            const float first_w =
                font.width(label.substr(0, 1), text_scale);
            const float y = text_y + font.line_height(font.text_px(text_scale));
            SDL_SetRenderDrawColor(screen, dim.r, dim.g, dim.b, 255);
            SDL_RenderLine(screen, x0, y, x0 + first_w, y);
        } else {
            const std::string tag(shortcut.key);
            font.draw(screen,
                      bounds.x + bounds.width -
                          font.width(tag, hint_scale) - 4.0f * scale,
                      bounds.y + 3.0f * scale, tag, dim, hint_scale);
        }
    }
}

// C2: visible groove, 0/25/50/75/100 ticks, filled part and a thumb.
void draw_slider_track(SDL_Renderer *screen, const SDL_FRect &box,
                       float fraction, bool enabled, float scale) {
    const SliderGeometry geometry = compute_slider_geometry(box, scale);
    const SDL_Color accent = enabled ? kAccent
                                     : SDL_Color{80, 92, 100, 255};
    SDL_SetRenderDrawColor(screen, 14, 20, 28, 255);
    SDL_RenderFillRect(screen, &geometry.track);
    SDL_SetRenderDrawColor(screen, 58, 70, 84, 255);
    for (const float x : geometry.tick_x)
        SDL_RenderLine(screen, x, geometry.tick_top, x, geometry.track.y);
    const SDL_FRect fill{geometry.track.x, geometry.track.y,
                         geometry.track.w * std::clamp(fraction, 0.0f, 1.0f),
                         geometry.track.h};
    SDL_SetRenderDrawColor(screen, accent.r, accent.g, accent.b, 255);
    SDL_RenderFillRect(screen, &fill);
    const SDL_FRect thumb = slider_thumb_rect(geometry, box, fraction, scale);
    SDL_SetRenderDrawColor(screen, enabled ? 235 : 130, enabled ? 241 : 140,
                           enabled ? 246 : 150, 255);
    SDL_RenderFillRect(screen, &thumb);
    SDL_SetRenderDrawColor(screen, accent.r, accent.g, accent.b, 255);
    SDL_RenderRect(screen, &thumb);
}

} // namespace lab
