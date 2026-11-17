#include "lab/FontRenderer.hpp"

#include "lab/MeshAsset.hpp"

#include <ft2build.h>
#include FT_FREETYPE_H

#include <array>
#include <vector>

namespace lab {

struct FontRenderer::Data {
    struct Glyph {
        std::vector<SDL_FRect> runs;
        float advance = 8.0f;
    };

    std::vector<unsigned char> bytes;
    FT_Library library = nullptr;
    FT_Face face = nullptr;
    std::array<Glyph, 128> glyphs;
    std::vector<SDL_FRect> rectangles;
    bool loaded = false;

    ~Data() {
        if (face)
            FT_Done_Face(face);
        if (library)
            FT_Done_FreeType(library);
    }
};

FontRenderer::FontRenderer(const std::string &path)
    : data_(std::make_unique<Data>()) {
    data_->bytes = decode_packaged_bytes(path, 18336);
    if (data_->bytes.empty() || FT_Init_FreeType(&data_->library) != 0)
        return;
    if (FT_New_Memory_Face(data_->library, data_->bytes.data(),
                           static_cast<FT_Long>(data_->bytes.size()), 0,
                           &data_->face) != 0 ||
        FT_Set_Pixel_Sizes(data_->face, 0, 14) != 0)
        return;
    for (int codepoint = 32; codepoint < 127; ++codepoint) {
        if (FT_Load_Char(data_->face, static_cast<FT_ULong>(codepoint),
                         FT_LOAD_RENDER) != 0)
            return;
        auto &glyph = data_->glyphs[static_cast<std::size_t>(codepoint)];
        const FT_GlyphSlot slot = data_->face->glyph;
        glyph.advance = static_cast<float>(slot->advance.x) / 64.0f;
        const FT_Bitmap &bitmap = slot->bitmap;
        const auto rows = static_cast<std::size_t>(bitmap.rows);
        const auto width = static_cast<std::size_t>(bitmap.width);
        const auto stride = static_cast<std::size_t>(
            bitmap.pitch < 0 ? -bitmap.pitch : bitmap.pitch);
        for (std::size_t row = 0; row < rows; ++row) {
            const std::size_t offset =
                (bitmap.pitch < 0 ? rows - row - 1 : row) * stride;
            std::size_t column = 0;
            while (column < width) {
                while (column < width && bitmap.buffer[offset + column] < 128)
                    ++column;
                const std::size_t first = column;
                while (column < width && bitmap.buffer[offset + column] >= 128)
                    ++column;
                if (column > first)
                    glyph.runs.push_back(
                        {static_cast<float>(slot->bitmap_left) +
                             static_cast<float>(first),
                         static_cast<float>(row) -
                             static_cast<float>(slot->bitmap_top),
                         static_cast<float>(column - first), 1.0f});
            }
        }
    }
    data_->rectangles.reserve(4096);
    data_->loaded = true;
}

FontRenderer::~FontRenderer() = default;

bool FontRenderer::ready() const { return data_->loaded; }

float FontRenderer::measure(const std::string &text) const {
    if (!ready())
        return 0.0f;
    float width = 0.0f;
    for (char character : text) {
        const auto codepoint = static_cast<unsigned char>(character);
        width += data_->glyphs[codepoint < 128 ? codepoint : '?'].advance;
    }
    return width;
}

void FontRenderer::draw(SDL_Renderer *renderer, float x, float y,
                        const std::string &text, SDL_Color color) {
    if (!ready())
        return;
    data_->rectangles.clear();
    float cursor = x;
    for (char character : text) {
        const auto codepoint = static_cast<unsigned char>(character);
        const auto &glyph = data_->glyphs[codepoint < 128 ? codepoint : '?'];
        for (const auto &run : glyph.runs)
            data_->rectangles.push_back(
                {cursor + run.x, y + 13.0f + run.y, run.w, run.h});
        cursor += glyph.advance;
    }
    SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);
    SDL_RenderFillRects(renderer, data_->rectangles.data(),
                        static_cast<int>(data_->rectangles.size()));
}

} // namespace lab
