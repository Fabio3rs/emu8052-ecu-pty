#include "lab/FontRenderer.hpp"
#include "lab/HeaderText.hpp"

#include <gtest/gtest.h>

#include <cstdlib>
#include <string>

namespace {

const std::string kSilk = LAB_FONT_ASSET_PATH;
const std::string kFallback = LAB_FALLBACK_FONT_ASSET_PATH;

class LabFont : public ::testing::Test {
  protected:
    // The developer override must not leak into the default-selection checks.
    void SetUp() override { unsetenv("SEVEL_FONT"); }
};

} // namespace

TEST_F(LabFont, DefaultSelectionIsEmbeddedAndNeverProbesSystemFonts) {
    const int before = lab::FontRenderer::system_font_probes();
    lab::FontRenderer font(kSilk);
    ASSERT_TRUE(font.ready());
    EXPECT_TRUE(font.is_pixel_face());
    EXPECT_EQ(lab::FontRenderer::system_font_probes(), before);
    EXPECT_EQ(font.face_identity().find("/usr/share/fonts"), std::string::npos);
    EXPECT_NE(font.face_identity().find("Silkscreen"), std::string::npos);
    // Original TTF hash recorded in docs/SEVEL_LAB_REUSE.md.
    EXPECT_NE(
        font.face_identity().find(
            "201df110e8dd8f19da40e5ad953b25bcac34dcb1bd14c7b8e02c9ce0b5ac0ca3"),
        std::string::npos);
}

TEST_F(LabFont, DegreeAndLatin1AreMeasuredNotQuestionMarks) {
    lab::FontRenderer font(kSilk);
    ASSERT_TRUE(font.ready());
    EXPECT_GT(font.measure("\xC2\xB0"
                           "C"),
              0.0f);
    EXPECT_NE(font.measure("\xC2\xB0"
                           "C"),
              font.measure("??"));
    // Silkscreen has no λ; the embedded fallback must supply it.
    EXPECT_NE(font.measure("\xCE\xBB"), font.measure("?"));
    EXPECT_NE(font.measure("\xC3\xA7\xC3\xA3o"), font.measure("???"));
}

TEST_F(LabFont, MalformedUtf8NeverOverrunsOrStalls) {
    lab::FontRenderer font(kSilk);
    ASSERT_TRUE(font.ready());
    for (const char *text : {"\xC3", "\xE2\x82", "\xF0\x9F", "\xFF\xFE",
                             "a\x80z", "\xC0\xAF", ""}) {
        EXPECT_GE(font.measure(text), 0.0f);
    }
    EXPECT_EQ(font.measure("A\xC3"), font.measure("A?"));
}

TEST_F(LabFont, BaselineFollowsTheFace) {
    lab::FontRenderer silk(kSilk);
    lab::FontRenderer bundled(kSilk, {lab::FontSpec::Kind::Bundled, {}},
                              kFallback);
    ASSERT_TRUE(silk.ready());
    ASSERT_TRUE(bundled.ready());
    EXPECT_FALSE(bundled.is_pixel_face());
    EXPECT_NE(silk.face_identity(), bundled.face_identity());
    // The faces coincide at some sizes (both 13 at 14 px), so compare where
    // they differ and require the ascent to scale instead of staying fixed.
    EXPECT_NE(silk.ascent(28.0f), bundled.ascent(28.0f));
    EXPECT_NE(silk.ascent(40.0f), bundled.ascent(40.0f));
    EXPECT_GT(silk.ascent(40.0f), silk.ascent(14.0f));
    EXPECT_GT(bundled.ascent(40.0f), bundled.ascent(14.0f));
    EXPECT_GT(silk.line_height(14.0f), 0.0f);
    EXPECT_GE(bundled.line_height(14.0f), bundled.ascent(14.0f));
}

TEST_F(LabFont, EveryCharsetGlyphHasAnAtlasEntryInEveryFace) {
    lab::FontRenderer silk(kSilk);
    lab::FontRenderer bundled(kSilk, {lab::FontSpec::Kind::Bundled, {}},
                              kFallback);
    for (lab::FontRenderer *font : {&silk, &bundled}) {
        ASSERT_TRUE(font->ready());
        for (const char32_t cp : lab::FontRenderer::charset())
            for (const float px : {12.0f, 14.0f, 28.0f})
                EXPECT_TRUE(font->has_glyph(cp, px))
                    << font->face_identity() << " U+" << std::hex
                    << static_cast<unsigned>(cp) << " @" << px;
        EXPECT_TRUE(font->last_error().empty()) << font->last_error();
    }
}

TEST_F(LabFont, PixelFaceSnapsToWholeDesignPixels) {
    lab::FontRenderer font(kSilk);
    ASSERT_TRUE(font.ready());
    // 8.4 ppem per design-pixel cell: widths scale in whole-cell steps.
    const float a = font.measure_px("H", 14.0f);
    const float b = font.measure_px("H", 16.0f);
    EXPECT_EQ(a, b);
    EXPECT_LT(font.measure_px("H", 8.0f), font.measure_px("H", 30.0f));
}

TEST_F(LabFont, FontSpecTokensRoundTrip) {
    for (const char *token :
         {"embedded", "bundled", "system", "file:/tmp/a.ttf"}) {
        lab::FontSpec spec;
        ASSERT_TRUE(lab::font_spec_from_token(token, spec)) << token;
        EXPECT_EQ(lab::font_spec_to_token(spec), token);
    }
    lab::FontSpec spec;
    EXPECT_FALSE(lab::font_spec_from_token("", spec));
    EXPECT_FALSE(lab::font_spec_from_token("file:", spec));
    EXPECT_FALSE(lab::font_spec_from_token("comic", spec));
}

TEST_F(LabFont, EllipsisKeepsTitlesReadableAndNeverSplitsUtf8) {
    lab::FontRenderer font(kSilk);
    ASSERT_TRUE(font.ready());
    const float px = 12.0f; // legibility floor
    const std::string title = "MANIFOLD PRESSURE";
    const float full = font.measure_px(title, px);
    EXPECT_EQ(font.ellipsize(title, px, full), title);
    const std::string cut = font.ellipsize(title, px, full * 0.6f);
    EXPECT_NE(cut, title);
    EXPECT_EQ(cut.substr(cut.size() - 3), "...");
    EXPECT_LE(font.measure_px(cut, px), full * 0.6f);
    // Multi-byte characters are cut whole: result stays valid UTF-8.
    const std::string accented = "A\xC3\xA7\xC3\xA3o \xC2\xB0"
                                 "C longa";
    const std::string trimmed =
        font.ellipsize(accented, px, font.measure_px(accented, px) * 0.5f);
    for (std::size_t i = 0; i < trimmed.size(); ++i) {
        const auto b = static_cast<unsigned char>(trimmed[i]);
        if (b >= 0xC0U) {
            ASSERT_LT(i + 1, trimmed.size());
            EXPECT_EQ(static_cast<unsigned char>(trimmed[i + 1]) & 0xC0U,
                      0x80U);
        }
    }
    // Even an impossible width yields a visible marker, not an empty title.
    EXPECT_EQ(font.ellipsize(title, px, 0.0f), "...");
    // The legibility floor maps to a positive scale for any size factor.
    EXPECT_GT(font.scale_for_px(12.0f), 0.0f);
    EXPECT_NEAR(font.text_px(font.scale_for_px(12.0f)), 12.0f, 1e-4f);
}

TEST_F(LabFont, HeaderTitleFallsBackToShortFormThenEllipsis) {
    lab::FontRenderer font(kSilk);
    ASSERT_TRUE(font.ready());
    const float px = 14.0f;
    const std::string full = "FIAT TIPO 1.6 i.e. | SEVEL 1581 CM3 | SOHC 8V / 4 CIL / SPI";
    const std::string shortened = "FIAT TIPO | SEVEL MA1.7";
    const float full_w = font.measure_px(full, px);
    const float short_w = font.measure_px(shortened, px);
    ASSERT_GT(full_w, short_w);
    // Fits: unchanged.
    EXPECT_EQ(lab::fit_header_title(font, full, shortened, px, full_w + 1.0f), full);
    // Too narrow for the full title but not for the short one: short form.
    EXPECT_EQ(lab::fit_header_title(font, full, shortened, px, (full_w + short_w) * 0.5f),
              shortened);
    // Narrower than the short title: ellipsis, never wider than the room.
    const float room = short_w * 0.6f;
    const std::string cut = lab::fit_header_title(font, full, shortened, px, room);
    EXPECT_LE(font.measure_px(cut, px), room);
    EXPECT_EQ(cut.substr(cut.size() - 3), "...");
    // No short form given: the full title is ellipsized.
    const std::string only = lab::fit_header_title(font, full, "", px, full_w * 0.5f);
    EXPECT_LE(font.measure_px(only, px), full_w * 0.5f);
}
