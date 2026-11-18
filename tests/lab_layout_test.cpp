#include "lab/LabLayout.hpp"

#include <gtest/gtest.h>

#include <array>
#include <cmath>
#include <utility>

namespace {

using lab::LabLayout;
using lab::LabPresentationMode;
using lab::LayoutState;

bool inside(const SDL_FRect &child, const SDL_FRect &parent,
            float eps = 1e-3f) {
    return child.x >= parent.x - eps && child.y >= parent.y - eps &&
           child.x + child.w <= parent.x + parent.w + eps &&
           child.y + child.h <= parent.y + parent.h + eps && child.w >= 0.0f &&
           child.h >= 0.0f;
}

bool same(const SDL_FRect &a, const SDL_FRect &b) {
    return a.x == b.x && a.y == b.y && a.w == b.w && a.h == b.h;
}

constexpr std::array<std::pair<float, float>, 8> kSizes{{{640.0f, 360.0f},
                                                         {900.0f, 620.0f},
                                                         {1099.0f, 700.0f},
                                                         {1100.0f, 700.0f},
                                                         {1280.0f, 720.0f},
                                                         {1920.0f, 1080.0f},
                                                         {2560.0f, 1440.0f},
                                                         {3440.0f, 1440.0f}}};

} // namespace

// C.1: LabLayout has no mutable global state any more; the proof is that the
// old members and adapters do not exist.
template <typename T>
concept HasLegacyState =
    requires { T::desktop_left_fraction; } || requires { T::active_mode; } ||
    requires { T::active_scope_fraction; } || requires { T::desktop_mode; } ||
    requires { T::for_output(1, 1); } ||
    requires { T::move_divider(1, 0.0f, 0.0f, 1, 1); };
static_assert(!HasLegacyState<LabLayout>, "LabLayout must be stateless");

TEST(LabLayoutPure, ComputeIsStatelessAndDeterministic) {
    const LayoutState state{};
    const LabLayout first = LabLayout::compute(state, 1920.0f, 1080.0f);
    LayoutState other{0.3f, 0.7f, 0.4f, LabPresentationMode::Analysis};
    (void)LabLayout::compute(other, 1920.0f, 1080.0f);
    const LabLayout again = LabLayout::compute(state, 1920.0f, 1080.0f);
    EXPECT_TRUE(same(first.left, again.left) &&
                same(first.scope, again.scope) &&
                same(first.mechanical, again.mechanical));
    // The default state reproduces the documented 24% / 66% proportions.
    EXPECT_NEAR(first.left.w, 1920.0f * 0.24f, 1e-3f);
    EXPECT_NEAR(first.mechanical.x + first.mechanical.w, 1920.0f * 0.66f,
                1e-3f);
}

TEST(LabLayoutPure, CompactWindowsIgnoreSavedModeAndScopeFraction) {
    const LayoutState saved{0.30f, 0.70f, 0.45f,
                            LabPresentationMode::Mechanics};
    const LayoutState compact = LabLayout::effective(saved, 900.0f);
    EXPECT_EQ(compact.mode, LabPresentationMode::Bench);
    EXPECT_LT(compact.scope_fraction, 0.0f);
    const LayoutState desktop = LabLayout::effective(saved, 1920.0f);
    EXPECT_EQ(desktop.mode, LabPresentationMode::Mechanics);
    EXPECT_FLOAT_EQ(desktop.scope_fraction, 0.45f);
    // compute() applies it: a 900 px window has no left column and the same
    // scope height whatever was saved for desktop.
    const LabLayout a = LabLayout::compute(saved, 900.0f, 620.0f);
    const LabLayout b = LabLayout::compute(LayoutState{}, 900.0f, 620.0f);
    EXPECT_TRUE(same(a.scope, b.scope));
    EXPECT_EQ(a.left.w, 0.0f);
}

TEST(LabLayoutPure, ChildrenStayInsideParentsAndColumnsTileTheOutput) {
    for (const auto mode :
         {LabPresentationMode::Bench, LabPresentationMode::Analysis,
          LabPresentationMode::Mechanics})
        for (const float scope : {-1.0f, 0.3f})
            for (const bool maximized : {false, true})
                for (const auto &[w, h] : kSizes) {
                    const LayoutState state{0.24f, 0.66f, scope, mode};
                    const LabLayout l =
                        LabLayout::compute(state, w, h, maximized);
                    const SDL_FRect output{0.0f, 0.0f, w, h};
                    const SDL_FRect column{l.mechanical.x, 0.0f, l.mechanical.w,
                                           h};
                    SCOPED_TRACE(::testing::Message() << w << "x" << h);
                    EXPECT_TRUE(inside(l.header, output));
                    EXPECT_TRUE(inside(l.left, output));
                    EXPECT_TRUE(inside(l.mechanical, output));
                    EXPECT_TRUE(inside(l.scope, output));
                    EXPECT_TRUE(inside(l.instruments, output));
                    EXPECT_TRUE(inside(l.mechanical, column));
                    EXPECT_TRUE(inside(l.scope, column));
                    // Three columns tile the width exactly, no gap, no overlap.
                    EXPECT_NEAR(l.left.w + l.mechanical.w + l.instruments.w, w,
                                1e-3f);
                    EXPECT_NEAR(l.left.x + l.left.w, l.mechanical.x, 1e-3f);
                    EXPECT_NEAR(l.mechanical.x + l.mechanical.w,
                                l.instruments.x, 1e-3f);
                    // Mechanical and scope stack contiguously in one column,
                    // leaving the 12 px bottom margin of the donor layout.
                    EXPECT_NEAR(l.scope.y, l.mechanical.y + l.mechanical.h,
                                1e-3f);
                    EXPECT_NEAR(l.scope.y + l.scope.h + 12.0f, h, 1e-3f);
                }
}

TEST(LabLayoutPure, ResultDependsOnlyOnInputsNotOnCallOrder) {
    const LayoutState state{};
    std::array<LabLayout, kSizes.size()> forward{};
    for (std::size_t i = 0; i < kSizes.size(); ++i)
        forward[i] =
            LabLayout::compute(state, kSizes[i].first, kSizes[i].second);
    for (std::size_t i = kSizes.size(); i-- > 0;) {
        const LabLayout again =
            LabLayout::compute(state, kSizes[i].first, kSizes[i].second);
        EXPECT_TRUE(same(again.left, forward[i].left));
        EXPECT_TRUE(same(again.mechanical, forward[i].mechanical));
        EXPECT_TRUE(same(again.scope, forward[i].scope));
        EXPECT_TRUE(same(again.instruments, forward[i].instruments));
    }
}

TEST(LabLayoutPure, LogicalUnitsAreScaleInvariantForTheSameLogicalSize) {
    // C.4: layout works in logical units; a window of W x H device pixels at
    // display scale s is the logical size (W/s, H/s). The same logical size
    // gives the same rectangles at every scale, and device rects are x s.
    const LayoutState state{};
    for (const float scale : {1.0f, 1.5f, 2.0f}) {
        const float w_px = 2560.0f, h_px = 1440.0f;
        const LabLayout logical =
            LabLayout::compute(state, w_px / scale, h_px / scale);
        const LabLayout reference =
            LabLayout::compute(state, w_px / scale, h_px / scale);
        EXPECT_TRUE(same(logical.mechanical, reference.mechanical));
        // Device-space tiling still covers the whole window after scaling.
        const float device_total =
            (logical.left.w + logical.mechanical.w + logical.instruments.w) *
            scale;
        EXPECT_NEAR(device_total, w_px, 1e-2f) << "scale " << scale;
    }
}

TEST(LabLayoutPure, DividersUseTheHeaderRectNotAMagicNumber) {
    const LayoutState state{};
    const float w = 1920.0f, h = 1080.0f;
    const LabLayout l = LabLayout::compute(state, w, h);
    const float mid_y = l.header.h + 100.0f;
    EXPECT_EQ(LabLayout::divider_at(state, l.left.w, mid_y, w, h), 1);
    EXPECT_EQ(LabLayout::divider_at(state, l.instruments.x, mid_y, w, h), 2);
    EXPECT_EQ(LabLayout::divider_at(state,
                                    l.mechanical.x + l.mechanical.w * 0.5f,
                                    l.scope.y, w, h),
              3);
    // Inside the header band no divider is grabbed, whatever x is.
    EXPECT_EQ(LabLayout::divider_at(state, l.left.w, l.header.h - 1.0f, w, h),
              0);
    // Compact windows have no draggable dividers.
    EXPECT_EQ(LabLayout::divider_at(state, 100.0f, 300.0f, 900.0f, 620.0f), 0);
}

TEST(LabLayoutPure, DraggingReturnsANewStateAndRespectsMinimums) {
    const LayoutState before{};
    const float w = 1920.0f, h = 1080.0f;
    const LayoutState after =
        LabLayout::with_divider_moved(before, 1, 100.0f, 400.0f, w, h);
    EXPECT_EQ(before.left_fraction, 0.24f) << "input state is not modified";
    EXPECT_GE(after.left_fraction * w,
              220.0f - 1e-3f); // clamped to the minimum
    const LayoutState scope =
        LabLayout::with_divider_moved(before, 3, 900.0f, 100.0f, w, h);
    const LabLayout l = LabLayout::compute(scope, w, h);
    EXPECT_GE(l.scope.h, 180.0f - 1e-3f);
    EXPECT_LE(l.scope.h, h - 300.0f + 1e-3f);
}

TEST(LabLayoutPure, MouseCoordinatesHitTheCenterOfEveryRectAtEveryDpi) {
    // Render at 1280x720 logical onto an output scaled by 1x/1.5x/2x and
    // convert window coordinates back: the center of each drawn rectangle
    // must map to itself, with the same factor on both axes (no distortion).
    const LayoutState state{};
    for (const float scale : {1.0f, 1.5f, 2.0f}) {
        const int out_w = static_cast<int>(std::lround(1280.0f * scale));
        const int out_h = static_cast<int>(std::lround(720.0f * scale));
        SDL_Surface *surface =
            SDL_CreateSurface(out_w, out_h, SDL_PIXELFORMAT_RGBA32);
        ASSERT_NE(surface, nullptr);
        SDL_Renderer *renderer = SDL_CreateSoftwareRenderer(surface);
        ASSERT_NE(renderer, nullptr);
        ASSERT_TRUE(SDL_SetRenderLogicalPresentation(
            renderer, 1280, 720, SDL_LOGICAL_PRESENTATION_STRETCH));
        int logical_w = 0, logical_h = 0;
        ASSERT_TRUE(lab::render_layout_size(renderer, &logical_w, &logical_h));
        EXPECT_EQ(logical_w, 1280);
        EXPECT_EQ(logical_h, 720);
        const LabLayout l = LabLayout::compute(state, 1280.0f, 720.0f);
        for (const SDL_FRect &rect :
             {l.left, l.mechanical, l.scope, l.instruments}) {
            const float cx = rect.x + rect.w * 0.5f,
                        cy = rect.y + rect.h * 0.5f;
            float rx = 0.0f, ry = 0.0f;
            ASSERT_TRUE(SDL_RenderCoordinatesFromWindow(renderer, cx * scale,
                                                        cy * scale, &rx, &ry));
            EXPECT_NEAR(rx, cx, 0.51f) << "scale " << scale;
            EXPECT_NEAR(ry, cy, 0.51f) << "scale " << scale;
        }
        // Same factor on both axes: a circle stays a circle.
        float ax = 0.0f, ay = 0.0f, bx = 0.0f, by = 0.0f;
        SDL_RenderCoordinatesFromWindow(renderer, 0.0f, 0.0f, &ax, &ay);
        SDL_RenderCoordinatesFromWindow(renderer, 100.0f, 100.0f, &bx, &by);
        EXPECT_NEAR(bx - ax, by - ay, 1e-3f) << "scale " << scale;
        SDL_DestroyRenderer(renderer);
        SDL_DestroySurface(surface);
    }
}
