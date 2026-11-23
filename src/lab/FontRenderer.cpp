#include "lab/FontRenderer.hpp"
#include "ma17/Diagnostics.hpp"

#include "lab/MeshAsset.hpp"

#include <ft2build.h>
#include FT_FREETYPE_H

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iterator>
#include <map>
#include <string_view>
#include <unordered_map>
#include <unordered_set>

namespace lab {
namespace {

std::atomic<int> g_system_probes{0};

// Silkscreen draws on a pixel grid: cap height is 5 design pixels of 125 font
// units on a 1050-unit em, so a design pixel is exactly 8.4 / 8.4 ppem.
constexpr float kPixelFaceUnitsPerEm = 1050.0f / 125.0f;
// DejaVu cap height / Silkscreen cap height at equal em.
constexpr float kFallbackScale = 0.82f;
constexpr int kAtlasWidth = 1024;
constexpr int kAtlasMaxHeight = 4096;

// --- SHA-256 (FIPS 180-4), used only for face identity ----------------------
std::string sha256_hex(const std::vector<unsigned char> &data) {
    static constexpr std::array<std::uint32_t, 64> k{
        0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U, 0x3956c25bU,
        0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U, 0xd807aa98U, 0x12835b01U,
        0x243185beU, 0x550c7dc3U, 0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U,
        0xc19bf174U, 0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU,
        0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU, 0x983e5152U,
        0xa831c66dU, 0xb00327c8U, 0xbf597fc7U, 0xc6e00bf3U, 0xd5a79147U,
        0x06ca6351U, 0x14292967U, 0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU,
        0x53380d13U, 0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
        0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U, 0xd192e819U,
        0xd6990624U, 0xf40e3585U, 0x106aa070U, 0x19a4c116U, 0x1e376c08U,
        0x2748774cU, 0x34b0bcb5U, 0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU,
        0x682e6ff3U, 0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U,
        0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U};
    std::array<std::uint32_t, 8> h{0x6a09e667U, 0xbb67ae85U, 0x3c6ef372U,
                                   0xa54ff53aU, 0x510e527fU, 0x9b05688cU,
                                   0x1f83d9abU, 0x5be0cd19U};
    std::vector<unsigned char> msg = data;
    const std::uint64_t bit_len = static_cast<std::uint64_t>(data.size()) * 8U;
    msg.push_back(0x80U);
    while (msg.size() % 64U != 56U)
        msg.push_back(0U);
    for (int shift = 56; shift >= 0; shift -= 8)
        msg.push_back(static_cast<unsigned char>((bit_len >> shift) & 0xffU));
    const auto rotr = [](std::uint32_t v, unsigned n) {
        return (v >> n) | (v << (32U - n));
    };
    for (std::size_t chunk = 0; chunk < msg.size(); chunk += 64U) {
        std::array<std::uint32_t, 64> w{};
        for (std::size_t i = 0; i < 16U; ++i) {
            const std::size_t j = chunk + i * 4U;
            w[i] = (static_cast<std::uint32_t>(msg[j]) << 24U) |
                   (static_cast<std::uint32_t>(msg[j + 1U]) << 16U) |
                   (static_cast<std::uint32_t>(msg[j + 2U]) << 8U) |
                   static_cast<std::uint32_t>(msg[j + 3U]);
        }
        for (std::size_t i = 16U; i < 64U; ++i) {
            const auto s0 = rotr(w[i - 15U], 7U) ^ rotr(w[i - 15U], 18U) ^
                            (w[i - 15U] >> 3U);
            const auto s1 = rotr(w[i - 2U], 17U) ^ rotr(w[i - 2U], 19U) ^
                            (w[i - 2U] >> 10U);
            w[i] = w[i - 16U] + s0 + w[i - 7U] + s1;
        }
        auto a = h;
        for (std::size_t i = 0; i < 64U; ++i) {
            const auto s1 = rotr(a[4], 6U) ^ rotr(a[4], 11U) ^ rotr(a[4], 25U);
            const auto ch = (a[4] & a[5]) ^ (~a[4] & a[6]);
            const auto t1 = a[7] + s1 + ch + k[i] + w[i];
            const auto s0 = rotr(a[0], 2U) ^ rotr(a[0], 13U) ^ rotr(a[0], 22U);
            const auto mj = (a[0] & a[1]) ^ (a[0] & a[2]) ^ (a[1] & a[2]);
            const auto t2 = s0 + mj;
            a = {t1 + t2, a[0], a[1], a[2], a[3] + t1, a[4], a[5], a[6]};
        }
        for (std::size_t i = 0; i < 8U; ++i)
            h[i] += a[i];
    }
    char out[65];
    for (std::size_t i = 0; i < 8U; ++i)
        std::snprintf(out + i * 8U, 9, "%08x", static_cast<unsigned>(h[i]));
    return std::string(out, 64);
}

std::vector<unsigned char> read_file_bytes(const std::string &path) {
    std::ifstream input(path, std::ios::binary);
    if (!input)
        return {};
    return std::vector<unsigned char>(std::istreambuf_iterator<char>(input),
                                      {});
}

// Decodes one UTF-8 code point; malformed input yields U+FFFD and consumes one
// byte so a bad sequence can never stall or overrun the string.
char32_t next_codepoint(std::string_view text, std::size_t &index) {
    const auto byte = [&](std::size_t i) {
        return static_cast<unsigned char>(text[i]);
    };
    const unsigned char lead = byte(index);
    int extra = 0;
    char32_t value = 0;
    if (lead < 0x80U) {
        ++index;
        return lead;
    } else if (lead >= 0xC2U && lead <= 0xDFU) {
        extra = 1;
        value = lead & 0x1FU;
    } else if (lead >= 0xE0U && lead <= 0xEFU) {
        extra = 2;
        value = lead & 0x0FU;
    } else if (lead >= 0xF0U && lead <= 0xF4U) {
        extra = 3;
        value = lead & 0x07U;
    } else {
        ++index;
        return 0xFFFDU;
    }
    if (index + static_cast<std::size_t>(extra) >= text.size()) {
        ++index;
        return 0xFFFDU;
    }
    for (int i = 1; i <= extra; ++i) {
        const unsigned char cont = byte(index + static_cast<std::size_t>(i));
        if ((cont & 0xC0U) != 0x80U) {
            ++index;
            return 0xFFFDU;
        }
        value = (value << 6U) | (cont & 0x3FU);
    }
    index += static_cast<std::size_t>(extra) + 1U;
    return value;
}

} // namespace

std::string font_spec_to_token(const FontSpec &spec) {
    switch (spec.kind) {
    case FontSpec::Kind::Embedded:
        return "embedded";
    case FontSpec::Kind::Bundled:
        return "bundled";
    case FontSpec::Kind::System:
        return "system";
    case FontSpec::Kind::File:
        return "file:" + spec.path;
    }
    return "embedded";
}

bool font_spec_from_token(const std::string &token, FontSpec &out) {
    if (token == "embedded")
        out = {FontSpec::Kind::Embedded, {}};
    else if (token == "bundled")
        out = {FontSpec::Kind::Bundled, {}};
    else if (token == "system")
        out = {FontSpec::Kind::System, {}};
    else if (token.size() > 5 && token.compare(0, 5, "file:") == 0)
        out = {FontSpec::Kind::File, token.substr(5)};
    else
        return false;
    return true;
}

struct FontRenderer::Data {
    struct Glyph {
        SDL_FRect src{0.0f, 0.0f, 0.0f, 0.0f};
        float left = 0.0f;
        float top = 0.0f;
        float advance = 0.0f;
        bool present = false;
    };

    struct Face {
        std::vector<unsigned char> bytes;
        FT_Face face = nullptr;
        std::string family;
        // SHA-256 of the face bytes, computed on first use: hashing the 334 KB
        // fallback at construction cost ~45 ms of UI startup.
        mutable std::string sha;
        const std::string &sha256() const EMU_LIFETIMEBOUND {
            if (sha.empty())
                sha = sha256_hex(bytes);
            return sha;
        }
    };

    FT_Library library = nullptr;
    Face primary;
    Face fallback;
    bool pixel = false;
    bool loaded = false;
    mutable std::string identity;
    std::string error;
    mutable std::unordered_set<char32_t> reported_missing;
    mutable std::map<int, std::unique_ptr<Bucket>> buckets;

    bool open(Face &target, std::vector<unsigned char> bytes) {
        if (bytes.empty())
            return false;
        target.bytes = std::move(bytes);
        if (FT_New_Memory_Face(library, target.bytes.data(),
                               static_cast<FT_Long>(target.bytes.size()), 0,
                               &target.face) != 0) {
            target.face = nullptr;
            return false;
        }
        target.family =
            target.face->family_name ? target.face->family_name : "?";
        return true;
    }

    ~Data();
};

struct FontRenderer::Bucket {
    float em_px = 0.0f;
    int width = kAtlasWidth;
    int height = 0;
    std::vector<std::uint32_t> pixels;
    std::unordered_map<char32_t, Data::Glyph> glyphs;
    float ascent = 0.0f;
    float line_height = 0.0f;
    SDL_Texture *texture = nullptr;
    SDL_Renderer *owner = nullptr;
    ~Bucket() {
        if (texture)
            SDL_DestroyTexture(texture);
    }
};

FontRenderer::Data::~Data() {
    buckets.clear();
    if (primary.face)
        FT_Done_Face(primary.face);
    if (fallback.face)
        FT_Done_Face(fallback.face);
    if (library)
        FT_Done_FreeType(library);
}

const std::vector<char32_t> &FontRenderer::charset() {
    static const std::vector<char32_t> set = [] {
        std::vector<char32_t> v;
        for (char32_t c = 32; c <= 126; ++c)
            v.push_back(c);
        for (char32_t c = 160; c <= 255; ++c) // Latin-1 incl. ° ± µ ·
            v.push_back(c);
        v.push_back(0x3BB); // λ
        v.push_back(0x394); // Δ
        return v;
    }();
    return set;
}

int FontRenderer::system_font_probes() { return g_system_probes.load(); }

FontRenderer::FontRenderer(const std::string &path, const FontSpec &spec,
                           const std::string &fallback_path)
    : data_(std::make_unique<Data>()) {
    if (FT_Init_FreeType(&data_->library) != 0)
        return;

    // SEVEL_FONT is a development override: retro|slkscr, modern, or a TTF
    // path.
    FontSpec effective = spec;
    if (const char *env = std::getenv("SEVEL_FONT")) {
        const std::string_view value(env);
        if (value == "retro" || value == "slkscr")
            effective = {FontSpec::Kind::Embedded, {}};
        else if (value == "modern")
            effective = {FontSpec::Kind::System, {}};
        else if (!value.empty())
            effective = {FontSpec::Kind::File, std::string(value)};
    }

    std::string fallback = fallback_path;
    if (fallback.empty() && !path.empty()) {
        const auto slash = path.find_last_of('/');
        fallback = (slash == std::string::npos ? std::string()
                                               : path.substr(0, slash + 1)) +
                   "DejaVuSansMono-Bold.ttf.zlib.b64";
    }
    const auto packaged = [](const std::string &file) {
        return file.empty() ? std::vector<unsigned char>()
                            : decode_packaged_bytes(file, 0);
    };

    bool opened = false;
    switch (effective.kind) {
    case FontSpec::Kind::Embedded:
        opened = data_->open(data_->primary, packaged(path));
        data_->pixel = opened;
        break;
    case FontSpec::Kind::Bundled:
        opened = data_->open(data_->primary, packaged(fallback));
        break;
    case FontSpec::Kind::System: {
        static constexpr const char *kSystemFonts[] = {
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf",
            // clang-format off
            "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf",
            // clang-format on
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"};
        for (const char *candidate : kSystemFonts) {
            g_system_probes.fetch_add(1);
            if (data_->open(data_->primary, read_file_bytes(candidate))) {
                opened = true;
                break;
            }
        }
        break;
    }
    case FontSpec::Kind::File:
        opened = data_->open(data_->primary, read_file_bytes(effective.path));
        break;
    }
    if (!opened) {
        // An explicit choice that cannot be honoured must not leave the UI
        // textless: fall back to the embedded face and say so.
        std::fprintf(stderr,
                     "[LAB-FONT] cannot load '%s'; using embedded face\n",
                     font_spec_to_token(effective).c_str());
        opened = data_->open(data_->primary, packaged(path));
        data_->pixel = opened;
    }
    if (!opened)
        return;
    if (!data_->primary.face)
        return;
    // Glyph fallback is always the packaged DejaVu (never a system lookup).
    // When DejaVu is itself the primary there is nothing further to fall to.
    {
        Data::Face probe;
        if (data_->open(probe, packaged(fallback)) &&
            probe.bytes != data_->primary.bytes) {
            data_->fallback = std::move(probe);
        } else if (probe.face) {
            FT_Done_Face(probe.face);
        }
    }
    // Startup logs the primary face only; the fallback hash is computed when
    // face_identity() is first requested (PNG metadata, manifests).
    ma17::diagnostic_log(stderr, "[LAB-FONT] face=%s sha256=%s%s%s pixel=%d\n",
                 data_->primary.family.c_str(), data_->primary.sha256().c_str(),
                 data_->fallback.face ? " +fallback " : "",
                 data_->fallback.face ? data_->fallback.family.c_str() : "",
                 data_->pixel ? 1 : 0);
    data_->loaded = true;
}

FontRenderer::~FontRenderer() = default;

void FontRenderer::release_textures() {
    if (data_) data_->buckets.clear();
}

bool FontRenderer::ready() const { return data_->loaded; }
bool FontRenderer::is_pixel_face() const { return data_->pixel; }
const std::string &FontRenderer::face_identity() const {
    if (data_->identity.empty() && data_->primary.face) {
        data_->identity =
            data_->primary.family + " sha256=" + data_->primary.sha256();
        if (data_->fallback.face)
            data_->identity += " +fallback " + data_->fallback.family +
                               " sha256=" + data_->fallback.sha256();
    }
    return data_->identity;
}
const std::string &FontRenderer::last_error() const { return data_->error; }

void FontRenderer::set_size_factor(float factor) {
    if (std::isfinite(factor) && factor > 0.0f)
        size_factor_ = factor;
}

void FontRenderer::set_device_scale(float scale) {
    if (std::isfinite(scale) && scale > 0.0f)
        device_scale_ = scale;
}

float FontRenderer::snap_device_px(float device_px) const {
    device_px = std::clamp(device_px, 6.0f, 256.0f);
    if (!data_->pixel)
        return std::round(device_px);
    const float cells =
        std::max(1.0f, std::round(device_px / kPixelFaceUnitsPerEm));
    return cells * kPixelFaceUnitsPerEm;
}

FontRenderer::Bucket &FontRenderer::bucket_for(float device_px) const {
    const float em = snap_device_px(device_px);
    const int key = static_cast<int>(std::lround(em * 64.0f));
    auto found = data_->buckets.find(key);
    if (found != data_->buckets.end())
        return *found->second;

    auto bucket = std::make_unique<Bucket>();
    bucket->em_px = em;
    FT_Face primary = data_->primary.face;
    FT_Face fallback = data_->fallback.face;
    const auto set_size = [](FT_Face face, float ppem) {
        return FT_Set_Char_Size(
                   face, 0, static_cast<FT_F26Dot6>(std::lround(ppem * 64.0f)),
                   72, 72) == 0;
    };
    if (!set_size(primary, em)) {
        data_->error = "FT_Set_Char_Size failed";
        return *data_->buckets.emplace(key, std::move(bucket)).first->second;
    }
    bucket->ascent =
        std::round(static_cast<float>(primary->size->metrics.ascender) / 64.0f);
    bucket->line_height =
        std::round(static_cast<float>(primary->size->metrics.height) / 64.0f);
    if (fallback)
        set_size(fallback, data_->pixel ? em * kFallbackScale : em);

    struct Pending {
        char32_t cp;
        int w, h;
        std::vector<std::uint8_t> alpha;
        Data::Glyph glyph;
    };
    std::vector<Pending> pending;
    for (const char32_t cp : charset()) {
        FT_Face face = primary;
        bool use_mono = data_->pixel;
        if (FT_Get_Char_Index(face, cp) == 0) {
            if (fallback && FT_Get_Char_Index(fallback, cp) != 0) {
                face = fallback;
                use_mono = false;
            } else {
                if (data_->reported_missing.insert(cp).second)
                    std::fprintf(stderr, "[LAB-FONT] U+%04X missing in '%s'\n",
                                 static_cast<unsigned>(cp),
                                 data_->primary.family.c_str());
                continue; // drawn as '?'
            }
        }
        const FT_Int32 flags =
            FT_LOAD_RENDER | (use_mono ? FT_LOAD_TARGET_MONO : 0);
        if (FT_Load_Char(face, static_cast<FT_ULong>(cp), flags) != 0)
            continue;
        const FT_GlyphSlot slot = face->glyph;
        Pending item;
        item.cp = cp;
        item.glyph.present = true;
        item.glyph.advance = static_cast<float>(slot->advance.x) / 64.0f;
        item.glyph.left = static_cast<float>(slot->bitmap_left);
        item.glyph.top = static_cast<float>(slot->bitmap_top);
        item.w = static_cast<int>(slot->bitmap.width);
        item.h = static_cast<int>(slot->bitmap.rows);
        item.alpha.assign(static_cast<std::size_t>(item.w * item.h), 0U);
        const int pitch = std::abs(slot->bitmap.pitch);
        for (int r = 0; r < item.h; ++r) {
            for (int c = 0; c < item.w; ++c) {
                const unsigned char *row =
                    slot->bitmap.buffer +
                    static_cast<std::ptrdiff_t>(r) * pitch;
                std::uint8_t a = 0U;
                if (slot->bitmap.pixel_mode == FT_PIXEL_MODE_MONO)
                    a = ((row[c / 8] >> (7 - (c % 8))) & 1U) != 0U ? 255U : 0U;
                else
                    a = row[c];
                item.alpha[static_cast<std::size_t>(r * item.w + c)] = a;
            }
        }
        pending.push_back(std::move(item));
    }

    // Pack row by row, growing the atlas height up to the cap; running out of
    // space is an explicit error, never a silently truncated atlas.
    int pen_x = 1, pen_y = 1, row_h = 0;
    for (auto &item : pending) {
        if (item.w <= 0 || item.h <= 0) {
            bucket->glyphs[item.cp] = item.glyph;
            continue;
        }
        if (pen_x + item.w + 1 >= kAtlasWidth) {
            pen_x = 1;
            pen_y += row_h + 1;
            row_h = 0;
        }
        if (pen_y + item.h + 1 > kAtlasMaxHeight) {
            data_->error =
                "font atlas out of space at " + std::to_string(em) + " px";
            std::fprintf(stderr, "[LAB-FONT] %s\n", data_->error.c_str());
            break;
        }
        item.glyph.src = {static_cast<float>(pen_x), static_cast<float>(pen_y),
                          static_cast<float>(item.w),
                          static_cast<float>(item.h)};
        bucket->height = std::max(bucket->height, pen_y + item.h + 1);
        row_h = std::max(row_h, item.h);
        pen_x += item.w + 1;
    }
    bucket->height = std::max(bucket->height, 1);
    bucket->pixels.assign(
        static_cast<std::size_t>(bucket->width * bucket->height), 0U);
    for (auto &item : pending) {
        if (item.w > 0 && item.h > 0 && item.glyph.src.w == 0.0f)
            continue; // did not fit
        for (int r = 0; r < item.h; ++r)
            for (int c = 0; c < item.w; ++c) {
                const auto x = static_cast<int>(item.glyph.src.x) + c;
                const auto y = static_cast<int>(item.glyph.src.y) + r;
                bucket
                    ->pixels[static_cast<std::size_t>(y * bucket->width + x)] =
                    (static_cast<std::uint32_t>(
                         item.alpha[static_cast<std::size_t>(r * item.w + c)])
                     << 24U) |
                    0x00FFFFFFU;
            }
        bucket->glyphs[item.cp] = item.glyph;
    }
    return *data_->buckets.emplace(key, std::move(bucket)).first->second;
}

bool FontRenderer::has_glyph(char32_t cp, float px) const {
    if (!ready())
        return false;
    const Bucket &b = bucket_for(px * device_scale_);
    const auto it = b.glyphs.find(cp);
    return it != b.glyphs.end() && it->second.present &&
           (cp == U' ' || cp == 0xA0U || it->second.src.w > 0.0f);
}

float FontRenderer::ascent(float px) const {
    return ready() ? bucket_for(px * device_scale_).ascent / device_scale_
                   : 0.0f;
}

float FontRenderer::line_height(float px) const {
    return ready() ? bucket_for(px * device_scale_).line_height / device_scale_
                   : 0.0f;
}

namespace {
// Glyph lookup with the '?' substitution for anything outside the charset.
template <typename Map>
const typename Map::mapped_type *
glyph_for(const Map &glyphs EMU_LIFETIMEBOUND, char32_t cp) {
    auto it = glyphs.find(cp);
    if (it == glyphs.end() || !it->second.present)
        it = glyphs.find(U'?');
    return it == glyphs.end() ? nullptr : &it->second;
}
} // namespace

float FontRenderer::measure_px(const std::string &utf8, float px) const {
    if (!ready())
        return 0.0f;
    const Bucket &b = bucket_for(px * device_scale_);
    float width = 0.0f;
    FT_Face face = data_->primary.face;
    const bool kerning = FT_HAS_KERNING(face);
    char32_t previous = 0;
    for (std::size_t i = 0; i < utf8.size();) {
        const char32_t cp = next_codepoint(utf8, i);
        const auto *glyph = glyph_for(b.glyphs, cp);
        if (!glyph)
            continue;
        if (kerning && previous != 0) {
            FT_Vector delta{0, 0};
            FT_Get_Kerning(face, FT_Get_Char_Index(face, previous),
                           FT_Get_Char_Index(face, cp), FT_KERNING_DEFAULT,
                           &delta);
            width += static_cast<float>(delta.x) / 64.0f;
        }
        width += glyph->advance;
        previous = cp;
    }
    return width / device_scale_;
}

std::string FontRenderer::ellipsize(const std::string &utf8, float px,
                                    float max_width) const {
    if (measure_px(utf8, px) <= max_width)
        return utf8;
    std::string cut = utf8;
    while (!cut.empty()) {
        do {
            cut.pop_back();
        } while (!cut.empty() &&
                 (static_cast<unsigned char>(cut.back()) & 0xC0U) == 0x80U);
        if (measure_px(cut + "...", px) <= max_width)
            return cut + "...";
    }
    return "...";
}

float FontRenderer::measure(const std::string &utf8) const {
    return measure_px(utf8, kNominalPx * size_factor_);
}

void FontRenderer::draw(SDL_Renderer *renderer, float x, float y,
                        const std::string &utf8, SDL_Color color, float scale) {
    if (!ready() || !renderer)
        return;
    const float px = kNominalPx * scale * size_factor_;
    Bucket &b = bucket_for(px * device_scale_);
    if (b.pixels.empty())
        return;
    if (b.texture == nullptr || b.owner != renderer) {
        if (b.texture)
            SDL_DestroyTexture(b.texture);
        b.owner = renderer;
        b.texture =
            SDL_CreateTexture(renderer, SDL_PIXELFORMAT_ARGB8888,
                              SDL_TEXTUREACCESS_STATIC, b.width, b.height);
        if (b.texture) {
            SDL_UpdateTexture(b.texture, nullptr, b.pixels.data(), b.width * 4);
            SDL_SetTextureBlendMode(b.texture, SDL_BLENDMODE_BLEND);
            SDL_SetTextureScaleMode(b.texture, data_->pixel
                                                   ? SDL_SCALEMODE_NEAREST
                                                   : SDL_SCALEMODE_LINEAR);
        }
    }
    if (!b.texture)
        return;
    SDL_SetTextureColorMod(b.texture, color.r, color.g, color.b);
    SDL_SetTextureAlphaMod(b.texture, color.a);

    FT_Face face = data_->primary.face;
    const bool kerning = FT_HAS_KERNING(face);
    const float inv = 1.0f / device_scale_;
    float cursor = x;
    char32_t previous = 0;
    for (std::size_t i = 0; i < utf8.size();) {
        const char32_t cp = next_codepoint(utf8, i);
        const auto *glyph = glyph_for(b.glyphs, cp);
        if (!glyph)
            continue;
        if (kerning && previous != 0) {
            FT_Vector delta{0, 0};
            FT_Get_Kerning(face, FT_Get_Char_Index(face, previous),
                           FT_Get_Char_Index(face, cp), FT_KERNING_DEFAULT,
                           &delta);
            cursor += static_cast<float>(delta.x) / 64.0f * inv;
        }
        if (glyph->src.w > 0.0f && glyph->src.h > 0.0f) {
            // L3: the pixel face is sampled with NEAREST, so a fractional
            // origin drops or doubles source pixels (THROTTLE -> TFCTILE on
            // llvmpipe). Put every glyph on a whole device pixel: 1:1 blit.
            float gx = cursor + glyph->left * inv;
            float gy = y + (b.ascent - glyph->top) * inv;
            if (data_->pixel) {
                gx = std::round(gx * device_scale_) * inv;
                gy = std::round(gy * device_scale_) * inv;
            }
            const SDL_FRect dst{gx, gy, glyph->src.w * inv, glyph->src.h * inv};
            SDL_RenderTexture(renderer, b.texture, &glyph->src, &dst);
        }
        cursor += glyph->advance * inv;
        previous = cp;
    }
}

} // namespace lab
