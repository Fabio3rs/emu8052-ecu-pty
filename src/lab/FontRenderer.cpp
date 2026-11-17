#include "lab/FontRenderer.hpp"

#include "lab/MeshAsset.hpp"

#include <ft2build.h>
#include FT_FREETYPE_H

#include <array>
#include <cstdint>
#include <vector>

namespace lab {

struct FontRenderer::Data {
    struct Glyph {
        SDL_FRect src{0.0f, 0.0f, 0.0f, 0.0f};
        float left = 0.0f;
        float top = 0.0f;
        float advance = 8.0f;
    };

    std::vector<unsigned char> bytes;
    std::vector<std::uint32_t> atlas_pixels;
    int atlas_w = 512;
    int atlas_h = 256;
    SDL_Texture *texture = nullptr;
    SDL_Renderer *cached_renderer = nullptr;
    FT_Library library = nullptr;
    FT_Face face = nullptr;
    std::array<Glyph, 128> glyphs{};
    bool loaded = false;

    ~Data() {
        if (texture)
            SDL_DestroyTexture(texture);
        if (face)
            FT_Done_Face(face);
        if (library)
            FT_Done_FreeType(library);
    }
};

FontRenderer::FontRenderer(const std::string &path)
    : data_(std::make_unique<Data>()) {
    if (FT_Init_FreeType(&data_->library) != 0)
        return;

    constexpr const char *kSystemFonts[] = {
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf"
    };
    bool face_loaded = false;
    for (const char *sys_path : kSystemFonts) {
        if (FT_New_Face(data_->library, sys_path, 0, &data_->face) == 0) {
            face_loaded = true;
            break;
        }
    }
    if (!face_loaded) {
        data_->bytes = decode_packaged_bytes(path, 18336);
        if (data_->bytes.empty() ||
            FT_New_Memory_Face(data_->library, data_->bytes.data(),
                               static_cast<FT_Long>(data_->bytes.size()), 0,
                               &data_->face) != 0)
            return;
    }
    if (FT_Set_Pixel_Sizes(data_->face, 0, 14) != 0)
        return;

    data_->atlas_pixels.assign(static_cast<std::size_t>(data_->atlas_w * data_->atlas_h), 0);
    int pen_x = 1;
    int pen_y = 1;
    int row_h = 0;

    for (int codepoint = 32; codepoint < 127; ++codepoint) {
        if (FT_Load_Char(data_->face, static_cast<FT_ULong>(codepoint),
                         FT_LOAD_RENDER) != 0)
            return;
        auto &glyph = data_->glyphs[static_cast<std::size_t>(codepoint)];
        const FT_GlyphSlot slot = data_->face->glyph;
        glyph.advance = static_cast<float>(slot->advance.x) / 64.0f;
        glyph.left = static_cast<float>(slot->bitmap_left);
        glyph.top = static_cast<float>(slot->bitmap_top);

        const FT_Bitmap &bitmap = slot->bitmap;
        const auto width = static_cast<int>(bitmap.width);
        const auto rows = static_cast<int>(bitmap.rows);
        if (width > 0 && rows > 0) {
            if (pen_x + width + 1 >= data_->atlas_w) {
                pen_x = 1;
                pen_y += row_h + 1;
                row_h = 0;
            }
            if (pen_y + rows + 1 >= data_->atlas_h)
                break;
            if (rows > row_h)
                row_h = rows;

            glyph.src = {static_cast<float>(pen_x), static_cast<float>(pen_y),
                         static_cast<float>(width), static_cast<float>(rows)};

            const auto stride = bitmap.pitch < 0 ? -bitmap.pitch : bitmap.pitch;
            for (int r = 0; r < rows; ++r) {
                const auto offset = static_cast<std::size_t>(
                    (bitmap.pitch < 0 ? rows - r - 1 : r) * stride);
                for (int c = 0; c < width; ++c) {
                    const std::uint8_t alpha = bitmap.buffer[offset + static_cast<std::size_t>(c)];
                    data_->atlas_pixels[static_cast<std::size_t>((pen_y + r) * data_->atlas_w + (pen_x + c))] =
                        (static_cast<std::uint32_t>(alpha) << 24) | 0x00FFFFFFU;
                }
            }
            pen_x += width + 1;
        }
    }
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
                        const std::string &text, SDL_Color color, float scale) {
    if (!ready() || !renderer)
        return;
    if (data_->texture == nullptr || data_->cached_renderer != renderer) {
        if (data_->texture)
            SDL_DestroyTexture(data_->texture);
        data_->cached_renderer = renderer;
        data_->texture = SDL_CreateTexture(
            renderer, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_STATIC,
            data_->atlas_w, data_->atlas_h);
        if (data_->texture) {
            SDL_UpdateTexture(data_->texture, nullptr, data_->atlas_pixels.data(),
                              data_->atlas_w * 4);
            SDL_SetTextureBlendMode(data_->texture, SDL_BLENDMODE_BLEND);
            SDL_SetTextureScaleMode(data_->texture, SDL_SCALEMODE_LINEAR);
        }
    }
    if (!data_->texture)
        return;

    SDL_SetTextureColorMod(data_->texture, color.r, color.g, color.b);
    SDL_SetTextureAlphaMod(data_->texture, color.a);

    float cursor = x;
    for (char character : text) {
        const auto codepoint = static_cast<unsigned char>(character);
        const auto &glyph = data_->glyphs[codepoint < 128 ? codepoint : '?'];
        if (glyph.src.w > 0.0f && glyph.src.h > 0.0f) {
            const SDL_FRect dst{cursor + glyph.left * scale,
                                y + (12.0f - glyph.top) * scale,
                                glyph.src.w * scale, glyph.src.h * scale};
            SDL_RenderTexture(renderer, data_->texture, &glyph.src, &dst);
        }
        cursor += glyph.advance * scale;
    }
}

} // namespace lab
