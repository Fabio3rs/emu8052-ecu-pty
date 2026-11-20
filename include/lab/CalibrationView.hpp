#pragma once

#include "lab/CalibrationCatalog.hpp"
#include "lab/FontRenderer.hpp"

#include <SDL3/SDL_rect.h>
#include <SDL3/SDL_render.h>

#include <algorithm>
#include <cstdint>
#include <span>
#include <vector>

namespace lab {

// Grid placement of a rows x cols heatmap inside the area below the header
// block. Pure, so tests can check that every cell stays inside the area.
struct CalibrationGridLayout {
    SDL_FRect grid;     // bounding box of all cells
    float cell_w = 0.0f;
    float cell_h = 0.0f;
    SDL_FRect cell(int row, int col) const {
        return {grid.x + static_cast<float>(col) * cell_w,
                grid.y + static_cast<float>(row) * cell_h, cell_w, cell_h};
    }
};

inline CalibrationGridLayout
compute_calibration_grid(const SDL_FRect &area, int rows, int cols,
                         float ui_scale) {
    const float header_h = 54.0f * ui_scale; // title, seal, address, axes
    const float margin = 8.0f * ui_scale;
    const float avail_w = std::max(0.0f, area.w - 2.0f * margin);
    const float avail_h = std::max(0.0f, area.h - header_h - margin);
    const float cell = rows > 0 && cols > 0
                           ? std::min(avail_w / static_cast<float>(cols),
                                      avail_h / static_cast<float>(rows))
                           : 0.0f;
    const float width = cell * static_cast<float>(cols);
    const float height = cell * static_cast<float>(rows);
    return {{area.x + margin, area.y + header_h, width, height}, cell, cell};
}

// Draws one table. `index`/`count` are the selector position; the table is
// named only by its catalog id.
void draw_calibration_view(SDL_Renderer *renderer, FontRenderer &font,
                           const SDL_FRect &area,
                           const std::vector<CalibrationTable> &tables,
                           std::size_t index, const std::string &status,
                           float ui_scale,
                           std::span<const std::uint16_t> recent_reads = {},
                           std::span<const int> variant_diff = {},
                           const std::string &variant_label = {});

} // namespace lab
