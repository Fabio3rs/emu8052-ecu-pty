#include "lab/CalibrationView.hpp"
#include "lab/TextScale.hpp"
#include "lab/LabTheme.hpp"

#include <algorithm>
#include <cstdio>

namespace lab {
namespace {

SDL_Color heat_color(float t) {
    // Single hue, light to dark (sequential scale, never red/green).
    const auto mix = [t](float light, float dark) {
        return static_cast<Uint8>(light + (dark - light) * t);
    };
    return {mix(228.0f, 22.0f), mix(238.0f, 70.0f), mix(248.0f, 128.0f), 255};
}

} // namespace

void draw_calibration_view(SDL_Renderer *renderer, FontRenderer &font,
                           const SDL_FRect &area,
                           const std::vector<CalibrationTable> &tables,
                           std::size_t index, const std::string &status,
                           float ui_scale,
                           std::span<const std::uint16_t> recent_reads,
                           std::span<const int> variant_diff,
                           const std::string &variant_label) {
    SDL_SetRenderDrawColor(renderer, 14, 14, 18, 255);
    SDL_RenderFillRect(renderer, &area);
    SDL_SetRenderDrawColor(renderer, 42, 42, 50, 255);
    SDL_RenderRect(renderer, &area);
    const float text = kTextSmall * ui_scale;
    const float x0 = area.x + 8.0f * ui_scale;
    const float max_w = area.w - 16.0f * ui_scale;
    if (tables.empty() || index >= tables.size()) {
        font.draw(renderer, x0, area.y + 6.0f * ui_scale,
                  status.empty() ? "NO CALIBRATION TABLES" : status,
                  kCritical, text);
        return;
    }
    const CalibrationTable &table = tables[index];
    const ConfidenceSeal seal = confidence_seal(table);

    char head[96];
    std::snprintf(head, sizeof(head), "CALIBRATION %zu/%zu  %s", index + 1,
                  tables.size(), table.id.c_str());
    font.draw(renderer, x0, area.y + 4.0f * ui_scale,
              font.ellipsize(head, font.text_px(text), max_w),
              {210, 218, 226, 255}, text);

    // Confidence seal: layout and physical function are separate claims.
    const SDL_Color layout_color = seal.layout == "LAYOUT CONFIRMED"
                                       ? kAccent
                                       : SDL_Color{249, 190, 96, 255};
    const SDL_Color function_color = seal.physical_known
                                         ? kAccent
                                         : SDL_Color{249, 190, 96, 255};
    float x = x0;
    font.draw(renderer, x, area.y + 16.0f * ui_scale, seal.layout, layout_color,
              text);
    x += font.measure_px(seal.layout, font.text_px(text)) + 12.0f * ui_scale;
    font.draw(renderer, x, area.y + 16.0f * ui_scale, seal.physical,
              function_color, text);

    char address[64];
    std::snprintf(address, sizeof(address), "ADDR 0x%04X  %d x %d  RAW BYTES",
                  table.start, table.rows, table.cols);
    font.draw(renderer, x0, area.y + 28.0f * ui_scale, address,
              {145, 177, 190, 255}, text);
    // Axes are shown as the catalog's raw source text, not as physical units.
    const std::string axes =
        "ROWS: " + (table.row_axis.empty() ? "?" : table.row_axis) +
        "  COLS: " + (table.col_axis.empty() ? "?" : table.col_axis);
    font.draw(renderer, x0, area.y + 40.0f * ui_scale,
              font.ellipsize(axes, font.text_px(text), max_w),
              {145, 177, 190, 255}, text);

    // K3: with a variant selected the cells show the signed difference to that
    // ROM instead of the raw byte (diverging scale, gray at zero).
    const bool diffing = variant_diff.size() == table.bytes.size();
    int max_abs_diff = 1;
    if (diffing) {
        for (const int d : variant_diff)
            max_abs_diff = std::max(max_abs_diff, std::abs(d));
        const int changed = static_cast<int>(std::count_if(
            variant_diff.begin(), variant_diff.end(), [](int d) { return d != 0; }));
        char diff_head[64];
        std::snprintf(diff_head, sizeof(diff_head), "DIFF vs %s: %d CELLS",
                      variant_label.c_str(), changed);
        font.draw(renderer,
                  area.x + area.w -
                      font.measure_px(diff_head, font.text_px(text)) -
                      8.0f * ui_scale,
                  area.y + 4.0f * ui_scale, diff_head, kPairB, text);
    }
    const auto layout =
        compute_calibration_grid(area, table.rows, table.cols, ui_scale);
    const auto [low, high] =
        std::minmax_element(table.bytes.begin(), table.bytes.end());
    for (int row = 0; row < table.rows; ++row)
        for (int col = 0; col < table.cols; ++col) {
            const SDL_FRect cell = layout.cell(row, col);
            const std::uint8_t value = table.cell(row, col);
            const float t = heatmap_intensity(value, *low, *high);
            const int diff_value =
                diffing ? variant_diff[static_cast<std::size_t>(row * table.cols + col)]
                        : 0;
            SDL_Color color = heat_color(t);
            if (diffing) {
                // gray at 0; blue for lower, amber for higher
                const float m = static_cast<float>(std::abs(diff_value)) /
                                static_cast<float>(max_abs_diff);
                const SDL_Color gray{64, 68, 76, 255};
                const SDL_Color end = diff_value < 0 ? SDL_Color{70, 130, 220, 255}
                                                     : SDL_Color{236, 160, 90, 255};
                color = {static_cast<Uint8>(gray.r + (end.r - gray.r) * m),
                         static_cast<Uint8>(gray.g + (end.g - gray.g) * m),
                         static_cast<Uint8>(gray.b + (end.b - gray.b) * m), 255};
            }
            SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, 255);
            SDL_RenderFillRect(renderer, &cell);
            if (cell.w >= 17.0f * ui_scale) {
                char hex[8];
                if (diffing)
                    std::snprintf(hex, sizeof(hex), "%+d", diff_value);
                else
                    std::snprintf(hex, sizeof(hex), "%02X", value);
                const SDL_Color ink = diffing ? SDL_Color{240, 244, 248, 255}
                                      : t > 0.55f ? SDL_Color{240, 244, 248, 255}
                                                  : SDL_Color{20, 30, 44, 255};
                const float scale = std::min(text, cell.w / 26.0f);
                font.draw(renderer,
                          cell.x + (cell.w - font.width(hex, scale)) * 0.5f,
                          cell.y + (cell.h - 8.0f * scale) * 0.5f, hex, ink,
                          scale);
            }
        }
    // K2: cells the firmware just read with MOVC. The newest is outlined in
    // the accent colour, the others in white, so the live operating point
    // moves across the table as the regime changes.
    const auto active = active_cells(table, recent_reads);
    for (std::size_t i = active.size(); i-- > 0;) {
        const SDL_FRect cell = layout.cell(active[i].row, active[i].col);
        const SDL_FRect inner{cell.x + 1.0f, cell.y + 1.0f, cell.w - 2.0f,
                              cell.h - 2.0f};
        if (i == 0)
            set_draw_color(renderer, kPairB); // amber: red is for alarms
        else
            SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
        SDL_RenderRect(renderer, &cell);
        SDL_RenderRect(renderer, &inner);
    }
    char live[40];
    std::snprintf(live, sizeof(live), "LIVE %zu CELLS", active.size());
    font.draw(renderer,
              area.x + area.w - font.measure_px(live, font.text_px(text)) -
                  8.0f * ui_scale,
              area.y + 16.0f * ui_scale, live,
              active.empty() ? SDL_Color{110, 122, 134, 255}
                             : SDL_Color{235, 241, 246, 255},
              text);
    SDL_SetRenderDrawColor(renderer, 58, 64, 76, 255);
    SDL_RenderRect(renderer, &layout.grid);
    char legend[48];
    std::snprintf(legend, sizeof(legend), "MIN %02X  MAX %02X", *low, *high);
    font.draw(renderer, x0, area.y + area.h - 11.0f * ui_scale, legend,
              {145, 177, 190, 255}, text);
}

} // namespace lab
