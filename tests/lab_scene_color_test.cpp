#include "lab/PixelSnap.hpp"
#include "lab/SceneColor.hpp"

#include <gtest/gtest.h>

#include <cmath>
#include <limits>

namespace {

struct Rgba {
    float x, y, z, w;
};

// Renders one full-surface triangle pair with `fill` over `background` using
// the software renderer and returns the resulting pixel.
SDL_Color render_over(SDL_Color background, SDL_FColor fill,
                      SDL_BlendMode mode) {
    SDL_Surface *surface = SDL_CreateSurface(8, 8, SDL_PIXELFORMAT_RGBA32);
    EXPECT_NE(surface, nullptr);
    SDL_Renderer *renderer = SDL_CreateSoftwareRenderer(surface);
    EXPECT_NE(renderer, nullptr);
    SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_NONE);
    SDL_SetRenderDrawColor(renderer, background.r, background.g, background.b,
                           background.a);
    SDL_RenderClear(renderer);
    SDL_SetRenderDrawBlendMode(renderer, mode);
    const SDL_Vertex vertices[6] = {{{-1, -1}, fill, {}}, {{9, -1}, fill, {}},
                                    {{9, 9}, fill, {}},   {{-1, -1}, fill, {}},
                                    {{9, 9}, fill, {}},   {{-1, 9}, fill, {}}};
    EXPECT_TRUE(SDL_RenderGeometry(renderer, nullptr, vertices, 6, nullptr, 0));
    SDL_Color out{};
    SDL_Surface *pixels = SDL_RenderReadPixels(renderer, nullptr);
    EXPECT_NE(pixels, nullptr);
    SDL_ReadSurfacePixel(pixels, 4, 4, &out.r, &out.g, &out.b, &out.a);
    SDL_DestroySurface(pixels);
    SDL_DestroyRenderer(renderer);
    SDL_DestroySurface(surface);
    return out;
}

} // namespace

TEST(LabSceneColor, KeepsAlphaAndClampsOutOfRangeAndNaN) {
    const SDL_FColor kept = lab::scene_fcolor(Rgba{0.85f, 0.22f, 0.18f, 0.70f});
    EXPECT_FLOAT_EQ(kept.a, 0.70f); // was forced to 1.0 before
    EXPECT_FLOAT_EQ(kept.r, 0.85f);
    const SDL_FColor clamped = lab::scene_fcolor(Rgba{2.0f, -1.0f, 0.5f, 7.0f});
    EXPECT_FLOAT_EQ(clamped.r, 1.0f);
    EXPECT_FLOAT_EQ(clamped.g, 0.0f);
    EXPECT_FLOAT_EQ(clamped.a, 1.0f);
    const float nan = std::numeric_limits<float>::quiet_NaN();
    const SDL_FColor safe = lab::scene_fcolor(Rgba{nan, nan, nan, nan});
    EXPECT_FLOAT_EQ(safe.r, 0.0f);
    EXPECT_FLOAT_EQ(safe.a, 0.0f);
}

TEST(LabSceneColor, SceneBlendMatchesTheDonorGpuPipeline) {
    // Donor: color = src * a + dst * (1 - a). Red a=0.5 over opaque blue.
    const SDL_Color blended = render_over(
        {0, 0, 255, 255}, {1.0f, 0.0f, 0.0f, 0.5f}, lab::kSceneBlendMode);
    EXPECT_NEAR(blended.r, 127.5, 2.0);
    EXPECT_NEAR(blended.b, 127.5, 2.0);
    EXPECT_EQ(blended.g, 0);
    // Without blending the alpha is ignored (the previous behavior): pure red.
    const SDL_Color opaque = render_over(
        {0, 0, 255, 255}, {1.0f, 0.0f, 0.0f, 0.5f}, SDL_BLENDMODE_NONE);
    EXPECT_EQ(opaque.r, 255);
    EXPECT_EQ(opaque.b, 0);
    // Fully transparent leaves the background untouched.
    const SDL_Color clear = render_over(
        {10, 20, 30, 255}, {1.0f, 1.0f, 1.0f, 0.0f}, lab::kSceneBlendMode);
    EXPECT_EQ(clear.r, 10);
    EXPECT_EQ(clear.g, 20);
    EXPECT_EQ(clear.b, 30);
}

TEST(LabPixelSnap, AdjacentViewsShareAnEdgeWithoutGapOrOverlap) {
    // Fractional pane widths at many origins: the old per-field truncation left
    // gaps/overlaps; rounding both edges never does.
    for (float origin = 0.0f; origin < 40.0f; origin += 0.37f) {
        for (float width = 100.0f; width < 140.0f; width += 0.61f) {
            const lab::PixelSpan first = lab::pixel_span(origin, width);
            const lab::PixelSpan second =
                lab::pixel_span(origin + width, width);
            ASSERT_EQ(first.x + first.w, second.x)
                << "origin=" << origin << " width=" << width;
            // Each span is within one pixel of the exact width.
            EXPECT_LE(std::fabs(static_cast<float>(first.w) - width), 1.0f);
        }
    }
    // The previous scheme demonstrably misaligned: truncate x and width apart.
    int misaligned = 0;
    for (float width = 100.0f; width < 140.0f; width += 0.61f) {
        const int a = static_cast<int>(10.3f);
        const int a_w = static_cast<int>(width);
        const int b = static_cast<int>(10.3f + width);
        if (a + a_w != b)
            ++misaligned;
    }
    EXPECT_GT(misaligned, 0);
}

TEST(LabPixelSnap, InvalidInputsYieldAnEmptySpan) {
    const float nan = std::numeric_limits<float>::quiet_NaN();
    EXPECT_EQ(lab::pixel_span(nan, 10.0f).w, 0);
    EXPECT_EQ(lab::pixel_span(5.0f, -3.0f).w, 0);
    EXPECT_EQ(lab::pixel_span(5.0f, 0.0f).w, 0);
}
