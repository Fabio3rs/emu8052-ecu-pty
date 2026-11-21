#pragma once

#include "Lifetime.hpp"

#include <SDL3/SDL.h>

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace lab {

// Which face the Lab UI uses. Embedded (Silkscreen) is the default; system and
// file faces are explicit user/developer choices only.
struct FontSpec {
    enum class Kind { Embedded, Bundled, System, File };
    Kind kind = Kind::Embedded;
    std::string path; // Kind::File only

    bool operator==(const FontSpec &other) const {
        return kind == other.kind && path == other.path;
    }
};

// Persisted token: "embedded", "bundled", "system" or "file:<ttf path>".
std::string font_spec_to_token(const FontSpec &spec);
bool font_spec_from_token(const std::string &token, FontSpec &out);

class FontRenderer {
  public:
    // Logical text height that scale == 1.0 maps to.
    static constexpr float kNominalPx = 14.0f;

    // `path` is the packaged Silkscreen asset. The glyph fallback is the
    // packaged DejaVu Sans Mono Bold beside it unless `fallback_path` is set.
    explicit FontRenderer(const std::string &path, const FontSpec &spec = {},
                          const std::string &fallback_path = {});
    ~FontRenderer();
    FontRenderer(const FontRenderer &) = delete;
    FontRenderer &operator=(const FontRenderer &) = delete;

    bool ready() const;
    void set_size_factor(float factor);
    // Device pixels per logical unit (SDL display scale x UI preference).
    void set_device_scale(float scale);

    // Width of `utf8` at scale 1.0 (kNominalPx logical units).
    float measure(const std::string &utf8) const;
    void draw(SDL_Renderer *renderer, float x, float y, const std::string &utf8,
              SDL_Color color, float scale = 1.0f);

    // Metrics in logical units for a text height of `px` logical units.
    float ascent(float px) const;
    float line_height(float px) const;
    float measure_px(const std::string &utf8, float px) const;
    // Trims whole UTF-8 code points and appends "..." until the text fits in
    // `max_width` at `px`; the text is returned unchanged when it already fits.
    std::string ellipsize(const std::string &utf8, float px,
                          float max_width) const;
    // Logical text height for `scale`, and the scale that yields `px`.
    float text_px(float scale) const {
        return kNominalPx * scale * size_factor_;
    }
    // Width of `utf8` as it is DRAWN at `scale` (the pixel face snaps to whole
    // design pixels, so a linear measure(utf8) * scale can be wider than the
    // glyphs): use this for centring, right-aligning and sizing boxes (L3).
    float width(const std::string &utf8, float scale) const {
        return measure_px(utf8, text_px(scale));
    }
    float scale_for_px(float px) const {
        return px / (kNominalPx * size_factor_);
    }

    bool is_pixel_face() const;
    // Whether a drawable atlas entry exists for `cp` in the bucket for `px`.
    bool has_glyph(char32_t cp, float px) const;
    // "<family> sha256=<hex>[ +fallback <family> sha256=<hex>]"
    const std::string &face_identity() const EMU_LIFETIMEBOUND;
    // Empty unless a bucket could not be built (e.g. atlas out of space).
    const std::string &last_error() const EMU_LIFETIMEBOUND;

    static const std::vector<char32_t> &charset();
    // Number of times any system font path was probed in this process.
    static int system_font_probes();

  private:
    struct Data;
    struct Bucket;
    Bucket &bucket_for(float device_px) const EMU_LIFETIMEBOUND;
    float snap_device_px(float device_px) const;

    std::unique_ptr<Data> data_;
    float size_factor_ = 1.0f;
    float device_scale_ = 1.0f;
};

} // namespace lab
