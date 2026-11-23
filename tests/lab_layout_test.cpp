#include "lab/LabLayout.hpp"
#include "lab/SpeedSelector.hpp"
#include "lab/HelpText.hpp"
#include "lab/VolumeLabel.hpp"
#include "lab/TriggerWheel.hpp"
#include "lab/DuctColor.hpp"
#include "lab/SevelValves.hpp"
#include "lab/CycleRuler.hpp"
#include "lab/WidgetRects.hpp"
#include "lab/PistonShade.hpp"
#include "lab/RodSection.hpp"
#include "lab/ScopeGroups.hpp"
#include "lab/GaugeGeometry.hpp"
#include "lab/SevelInstrumentProfile.hpp"
#include "lab/EcuBadges.hpp"
#include "lab/PulseStats.hpp"
#include "lab/SliderGeometry.hpp"
#include "lab/LabButtons.hpp"
#include "lab/CalibrationView.hpp"
#include "lab/DynoView.hpp"
#include "lab/FixedTextScale.hpp"
#include "lab/ScopeLabel.hpp"

#include "lab/HeaderText.hpp"
#include <gtest/gtest.h>

#include <array>
#include <set>
#include <string>
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

namespace {
bool rects_intersect(const SDL_FRect &a, const SDL_FRect &b) {
    return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h &&
           b.y < a.y + a.h;
}
} // namespace

TEST(LabLayoutPure, ToolbarNeverIntersectsSceneOrScopeAndStaysInHeader) {
    const std::array<std::pair<float, float>, 3> sizes{
        {{1100.0f, 690.0f}, {1280.0f, 720.0f}, {1920.0f, 1080.0f}}};
    for (const auto &[w, h] : sizes) {
        const lab::LabLayout l = lab::LabLayout::compute({}, w, h);
        EXPECT_FALSE(rects_intersect(l.toolbar, l.scene)) << w << "x" << h;
        EXPECT_FALSE(rects_intersect(l.toolbar, l.scope)) << w << "x" << h;
        EXPECT_GE(l.toolbar.y, 0.0f);
        EXPECT_LE(l.toolbar.y + l.toolbar.h, l.header.h + 0.001f);
        EXPECT_FLOAT_EQ(l.toolbar.h, lab::kToolbarHeight);
        EXPECT_FLOAT_EQ(l.scene.y, l.header.h);
        EXPECT_LE(l.scene.y + l.scene.h, l.scope.y + 0.001f);
    }
}

// L6: a single table names every scope group; tab names are short enough for
// the narrowest tab and never collide.
TEST(ScopeGroups, SingleTableWithUniqueShortNames) {
    std::set<std::string> titles;
    std::set<std::string> shorts;
    for (const auto &group : lab::kScopeGroups) {
        EXPECT_GT(std::string(group.title).size(), 0u);
        EXPECT_LE(std::string(group.short_name).size(), 5u) << group.short_name;
        EXPECT_LE(std::string(group.short_name).size(),
                  std::string(group.title).size());
        titles.insert(group.title);
        shorts.insert(group.short_name);
    }
    EXPECT_EQ(titles.size(), lab::kScopeGroupCount);
    EXPECT_EQ(shorts.size(), lab::kScopeGroupCount);
    EXPECT_STREQ(lab::scope_group(-3).title, "LAMBDA");
    EXPECT_STREQ(lab::scope_group(99).short_name, "IDLE");
}

// G1: for every numeral angle the needle segment, drawn up to its limited tip,
// never enters the numeral's box.
TEST(GaugeGeometry, NeedleNeverEntersNumeralBoxes) {
    const float inner_r = 60.0f;
    for (const auto &[w, h] : std::array<std::pair<float, float>, 3>{
             {{10.0f, 9.0f}, {22.0f, 9.0f}, {34.0f, 12.0f}}}) {
        float edge_min = lab::kNoNumerals;
        for (int deg = 0; deg < 360; deg += 5) {
            const float th = static_cast<float>(deg) * 3.14159265f / 180.0f;
            edge_min = std::min(edge_min,
                                lab::gauge_numeral_inner_edge(inner_r, w, h, th));
        }
        const float tip = lab::gauge_needle_tip_limit(1000.0f, edge_min, 2.0f);
        for (int deg = 0; deg < 360; deg += 5) {
            const float th = static_cast<float>(deg) * 3.14159265f / 180.0f;
            const float c = std::cos(th), s = std::sin(th);
            const float rc = lab::gauge_numeral_center_radius(inner_r, w, h, th);
            const float bx = rc * c, by = rc * s; // numeral centre
            for (float r = 0.0f; r <= tip; r += 0.25f) {
                const float px = r * c, py = r * s;
                const bool inside = std::fabs(px - bx) < 0.5f * w &&
                                    std::fabs(py - by) < 0.5f * h;
                ASSERT_FALSE(inside) << "deg=" << deg << " r=" << r;
            }
        }
        EXPECT_LT(tip, inner_r);
    }
}

// L4: every short label is real, shorter than its title and unique.
TEST(InstrumentShortLabels, ShorterThanTheirTitleAndFoundById) {
    EXPECT_STREQ(lab::profile::short_label_for("manifold_pressure"), "MAP kPa");
    EXPECT_EQ(lab::profile::short_label_for("rpm"), nullptr);
    const lab::profile::Instrument *specs[] = {
        &lab::profile::manifold_pressure, &lab::profile::oxygen_voltage,
        &lab::profile::volumetric_efficiency};
    for (const auto *spec : specs) {
        const char *shortened = lab::profile::short_label_for(spec->id);
        ASSERT_NE(shortened, nullptr) << spec->id;
        EXPECT_LT(std::string(shortened).size(), std::string(spec->title).size());
    }
}

// L5: no dimensionless "1" unit, and out-of-range readings are not shown raw.
TEST(ScopeLabel, DropsDimensionlessUnitAndMarksOutOfRange) {
    EXPECT_STREQ(lab::scope_unit_text("1"), "");
    EXPECT_STREQ(lab::scope_unit_text("V"), "V");
    EXPECT_STREQ(lab::scope_unit_text(nullptr), "");
    EXPECT_EQ(lab::scope_value_text(1.20, 0.5, 1.5), "1.20");
    EXPECT_EQ(lab::scope_value_text(5.00, 0.5, 1.5), "> 1.50");
    EXPECT_EQ(lab::scope_value_text(0.1, 0.5, 1.5), "< 0.50");
}

TEST(ScopeLabel, ScaleEndsKeepDecimalsOnlyWhenNeeded) {
    EXPECT_EQ(lab::scale_end_text(0.0), "0");
    EXPECT_EQ(lab::scale_end_text(0.5), "0.5");
    EXPECT_EQ(lab::scale_end_text(1.5), "1.5");
    EXPECT_EQ(lab::scale_end_text(110.0), "110");
    EXPECT_EQ(lab::scale_end_text(16.0), "16");
}

// L1: chips are dropped lowest-priority first and counted; the fitted line is
// never wider than the budget (unless a single chip alone is).
TEST(HeaderChips, DropLeastImportantFirstAndCountThem) {
    const auto measure = [](const std::string &text) {
        return static_cast<float>(text.size()) * 8.0f;
    };
    const std::vector<lab::StatusChip> chips{{"RUN", 0},
                                             {"1.50 s", 1},
                                             {"TICK 1485000", 4},
                                             {"ROM BA5FB820", 2},
                                             {"KEY ON", 3},
                                             {"UI BENCH", 5}};
    const std::string full = lab::fit_status_chips(chips, measure, 10000.0f);
    EXPECT_EQ(full,
              "RUN | 1.50 s | TICK 1485000 | ROM BA5FB820 | KEY ON | UI BENCH");
    const std::string one_less =
        lab::fit_status_chips(chips, measure, measure(full) - 1.0f);
    EXPECT_EQ(one_less.find("UI BENCH"), std::string::npos);
    EXPECT_NE(one_less.find("+1"), std::string::npos);
    EXPECT_NE(one_less.find("TICK"), std::string::npos);
    for (float width : {400.0f, 300.0f, 200.0f, 120.0f}) {
        const std::string line = lab::fit_status_chips(chips, measure, width);
        EXPECT_LE(measure(line), width) << line;
        EXPECT_EQ(line.rfind("RUN", 0), 0u) << line; // mode chip is kept
    }
}

// L8: the scale depends on the box and the worst-case samples only, so two
// frames with different readings in the same box get the same scale.
TEST(FixedTextScale, DependsOnBoxNotOnTheReading) {
    const auto measure = [](const char *text) {
        return static_cast<float>(std::string(text).size()) * 6.0f;
    };
    const float a = lab::fixed_block_scale(measure, {"VAPOR: 888.8 mg", "PULSES: 8"},
                                           1.0f, 60.0f);
    const float b = lab::fixed_block_scale(measure, {"VAPOR: 888.8 mg", "PULSES: 8"},
                                           1.0f, 60.0f);
    EXPECT_FLOAT_EQ(a, b);
    EXPECT_NEAR(a, 60.0f / 90.0f, 1e-6f); // 15 chars * 6 = 90 units wide
    const float roomy = lab::fixed_block_scale(measure, {"VAPOR: 888.8 mg"}, 0.85f,
                                               1000.0f);
    EXPECT_FLOAT_EQ(roomy, 0.85f);     // capped by max_scale in a wide box
    EXPECT_GT(lab::fixed_block_scale(measure, {"X"}, 1.0f, 100.0f), 0.0f);
}

// D1: advance, MBT and their difference; "--" until an ignition event exists.
TEST(IgnitionAdvance, ShowsAdvanceMbtAndSignedDifference) {
    const auto text = lab::ignition_advance_text(true, 18.6, 27.4);
    EXPECT_EQ(text.advance, "ADV 18.6\xC2\xB0");
    EXPECT_EQ(text.mbt, "MBT 27.4\xC2\xB0");
    EXPECT_EQ(text.difference, "DIFF -8.8\xC2\xB0");
    EXPECT_EQ(lab::ignition_advance_text(true, 30.0, 27.0).difference,
              "DIFF +3.0\xC2\xB0");
    const auto none = lab::ignition_advance_text(false, 0.0, 0.0);
    EXPECT_EQ(none.advance, "ADV --");
    EXPECT_EQ(none.difference, "DIFF --");
    EXPECT_EQ(lab::ignition_advance_text(true, std::nan(""), 1.0).mbt, "MBT --");
}

// Y1 layout: four stacked panels, one shared rpm axis, one Y axis per panel,
// no overlap, all inside the area.
TEST(DynoLayout, StackedPanelsShareOneRpmAxisAndNeverOverlap) {
    for (const auto &[w, h] : std::array<std::pair<float, float>, 3>{
             {{760.0f, 300.0f}, {1000.0f, 400.0f}, {1400.0f, 620.0f}}}) {
        const SDL_FRect area{10.0f, 20.0f, w, h};
        const auto layout = lab::compute_dyno_layout(area, 1.0f);
        ASSERT_EQ(layout.panels.size(), 4u);
        for (std::size_t i = 0; i < layout.panels.size(); ++i) {
            const auto &p = layout.panels[i];
            EXPECT_GE(p.plot.x, area.x);
            EXPECT_LE(p.plot.x + p.plot.w, area.x + area.w);
            EXPECT_GE(p.plot.y, area.y);
            EXPECT_LE(p.plot.y + p.plot.h, area.y + area.h);
            EXPECT_GT(p.plot.h, 8.0f) << i;
            EXPECT_LT(p.y_min, p.y_max);
            // Shared x: every panel has the same horizontal extent.
            EXPECT_FLOAT_EQ(p.plot.x, layout.panels[0].plot.x);
            EXPECT_FLOAT_EQ(p.plot.w, layout.panels[0].plot.w);
            if (i > 0) {
                EXPECT_GE(p.plot.y, layout.panels[i - 1].plot.y +
                                        layout.panels[i - 1].plot.h);
            }
        }
        // The same rpm maps to the same x in every panel.
        const float x0 = layout.x_for_rpm(3000.0, layout.panels[0].plot);
        for (const auto &p : layout.panels)
            EXPECT_FLOAT_EQ(layout.x_for_rpm(3000.0, p.plot), x0);
        // y_for is monotonic within a panel.
        const auto &t = layout.panels[0];
        EXPECT_LT(lab::DynoLayout::y_for(130.0, t), lab::DynoLayout::y_for(100.0, t));
    }
}

// K1 layout: every cell of the largest catalog tables stays inside the area.
TEST(CalibrationGrid, CellsStayInsideTheAreaAtEverySize) {
    for (const auto &[w, h] : std::array<std::pair<float, float>, 3>{
             {{760.0f, 300.0f}, {1000.0f, 400.0f}, {1400.0f, 620.0f}}})
        for (const auto &[rows, cols] :
             std::array<std::pair<int, int>, 3>{{{8, 15}, {15, 15}, {3, 9}}}) {
            const SDL_FRect area{10.0f, 20.0f, w, h};
            const auto layout = lab::compute_calibration_grid(area, rows, cols, 1.0f);
            EXPECT_GT(layout.cell_w, 0.0f);
            EXPECT_FLOAT_EQ(layout.cell_w, layout.cell_h); // square cells
            const SDL_FRect first = layout.cell(0, 0);
            const SDL_FRect last = layout.cell(rows - 1, cols - 1);
            EXPECT_GE(first.x, area.x);
            EXPECT_GE(first.y, area.y);
            EXPECT_LE(last.x + last.w, area.x + area.w + 0.001f);
            EXPECT_LE(last.y + last.h, area.y + area.h + 0.001f);
        }
}

// C1: five distinguishable states and no solid-white "on" block.
TEST(ButtonVisual, FiveDistinctStatesAndAccentPerAction) {
    using lab::LabButtonAction;
    for (auto action : {LabButtonAction::Key, LabButtonAction::Pause,
                        LabButtonAction::Mute, LabButtonAction::Faster,
                        LabButtonAction::Starter}) {
        const auto normal = lab::compute_button_visual(action, false, false, false, true);
        const auto hover = lab::compute_button_visual(action, false, false, true, true);
        const auto pressed = lab::compute_button_visual(action, false, true, true, true);
        const auto on = lab::compute_button_visual(action, true, false, false, true);
        const auto disabled = lab::compute_button_visual(action, false, false, false, false);
        EXPECT_NE(normal.frame, hover.frame);
        EXPECT_NE(normal.fill, pressed.fill);
        EXPECT_NE(on.fill, normal.fill);
        EXPECT_NE(on.fill, pressed.fill);
        EXPECT_GT(on.bar_width, 0.0f);          // on = side bar
        EXPECT_EQ(normal.bar_width, 0.0f);
        EXPECT_LT(on.fill.r + on.fill.g + on.fill.b, 3 * 100); // never white
        EXPECT_LT(disabled.text.g, normal.text.g);              // dimmed text
        EXPECT_EQ(disabled.bar_width, 0.0f);
    }
    // KEY ON and PAUSE ON differ without reading the label: other accent.
    EXPECT_NE(lab::compute_button_visual(LabButtonAction::Key, true, false, false, true).bar,
              lab::compute_button_visual(LabButtonAction::Pause, true, false, false, true).bar);
    EXPECT_EQ(lab::lab_button_kind(LabButtonAction::Key), lab::LabButtonKind::Toggle);
    EXPECT_EQ(lab::lab_button_kind(LabButtonAction::Starter), lab::LabButtonKind::Momentary);
}

// C2: track, ticks, thumb, snap presets and wheel steps.
TEST(SliderGeometry, TrackTicksThumbAndPresets) {
    const SDL_FRect box{16.0f, 64.0f, 275.0f, 27.0f};
    for (const float scale : {1.0f, 1.5f, 2.0f}) {
        const auto geometry = lab::compute_slider_geometry(box, scale);
        EXPECT_GE(geometry.track.x, box.x);
        EXPECT_LE(geometry.track.x + geometry.track.w, box.x + box.w);
        EXPECT_LE(geometry.track.y + geometry.track.h, box.y + box.h);
        EXPECT_GT(geometry.track.h, 3.0f * scale - 0.001f);
        for (std::size_t i = 1; i < geometry.tick_x.size(); ++i)
            EXPECT_GT(geometry.tick_x[i], geometry.tick_x[i - 1]);
        EXPECT_FLOAT_EQ(geometry.tick_x[2], geometry.track.x + geometry.track.w * 0.5f);
        for (const float value : {0.0f, 0.33f, 1.0f}) {
            const auto thumb = lab::slider_thumb_rect(geometry, box, value, scale);
            EXPECT_GE(thumb.x, box.x);
            EXPECT_LE(thumb.x + thumb.w, box.x + box.w + 0.001f);
        }
    }
}

TEST(SliderGeometry, ClickSnapsToPresetsButDragValuesStay) {
    EXPECT_FLOAT_EQ(lab::snap_to_preset(0.251f, 275.0f), 0.25f); // 0.3 px away
    EXPECT_FLOAT_EQ(lab::snap_to_preset(0.74f, 275.0f), 0.75f);  // 2.75 px away
    EXPECT_FLOAT_EQ(lab::snap_to_preset(0.484f, 275.0f), 0.484f); // 4.4 px: no snap
    EXPECT_FLOAT_EQ(lab::snap_to_preset(0.999f, 275.0f), 1.0f);
}

TEST(SliderGeometry, WheelMovesOnePercentOrTenthWithShiftAndClamps) {
    EXPECT_NEAR(lab::slider_wheel_step(0.50f, 1.0f, false), 0.51f, 1e-6f);
    EXPECT_NEAR(lab::slider_wheel_step(0.50f, -3.0f, false), 0.49f, 1e-6f);
    EXPECT_NEAR(lab::slider_wheel_step(0.50f, 1.0f, true), 0.501f, 1e-6f);
    EXPECT_FLOAT_EQ(lab::slider_wheel_step(1.0f, 1.0f, false), 1.0f);
    EXPECT_FLOAT_EQ(lab::slider_wheel_step(0.0f, -1.0f, false), 0.0f);
    EXPECT_FLOAT_EQ(lab::slider_wheel_step(0.3f, 0.0f, false), 0.3f);
}

// C3: the multiplier text for every step the Slower/Faster buttons can reach.
TEST(SpeedMultiplier, ReadsCompactlyAtEveryStep) {
    EXPECT_EQ(lab::speed_multiplier_text(0.25), "0.25X");
    EXPECT_EQ(lab::speed_multiplier_text(0.5), "0.5X");
    EXPECT_EQ(lab::speed_multiplier_text(1.0), "1X");
    EXPECT_EQ(lab::speed_multiplier_text(2.0), "2X");
    EXPECT_EQ(lab::speed_multiplier_text(4.0), "4X");
    EXPECT_EQ(lab::speed_multiplier_text(16.0), "16X");
    EXPECT_EQ(lab::speed_multiplier_text(0.1), "0.1X");
}

// C5: every button has a shortcut; underlined ones are the label's first letter.
TEST(ButtonShortcuts, EveryButtonHasAShortcutAndUnderlinesMatchTheLabel) {
    ASSERT_EQ(lab::lab_button_shortcuts.size(), lab::lab_button_labels.size());
    std::set<std::string> keys;
    for (std::size_t i = 0; i < lab::lab_button_labels.size(); ++i) {
        const auto &shortcut = lab::lab_button_shortcuts[i];
        EXPECT_FALSE(shortcut.key.empty()) << i;
        keys.insert(std::string(shortcut.key));
        if (shortcut.underline_first) {
            EXPECT_EQ(lab::lab_button_labels[i].substr(0, 1), shortcut.key) << i;
        }
    }
    EXPECT_EQ(keys.size(), lab::lab_button_labels.size()); // no two share a key
}

// D2/D3: pulse width/period/duty from edges, polarity chosen by the caller.
TEST(PulseStats, WidthPeriodAndDutyFromEdges) {
    using ma17::EmulatorEvent;
    using ma17::EmulatorEventType;
    const auto edge = [](long long tick, bool high, unsigned channel = 0) {
        EmulatorEvent e;
        e.tick = tick;
        e.type = EmulatorEventType::IgnitionPin;
        e.channel = channel;
        e.high = high;
        return e;
    };
    // High 3 ms every 20 ms: rise 0, fall 2970, rise 19800, fall 22770.
    const std::vector<EmulatorEvent> events{
        edge(0, true), edge(2970, false), edge(19800, true), edge(22770, false),
        edge(40000, true, 1), edge(41000, false, 1)};
    const auto high = lab::last_pulse_stat(events, EmulatorEventType::IgnitionPin,
                                           0, 100000, true);
    ASSERT_TRUE(high.valid);
    EXPECT_NEAR(high.width_ms, 3.0, 1e-9);
    ASSERT_TRUE(high.has_period);
    EXPECT_NEAR(high.period_ms, 20.0, 1e-9);
    EXPECT_NEAR(high.duty_percent, 15.0, 1e-9);
    // The low level between pulses: 2970 -> 19800 = 17 ms.
    const auto low = lab::last_pulse_stat(events, EmulatorEventType::IgnitionPin,
                                          0, 100000, false);
    ASSERT_TRUE(low.valid);
    EXPECT_NEAR(low.width_ms, 17.0, 1e-9);
    // Channel 1 has one pulse, no period.
    const auto other = lab::last_pulse_stat(events, EmulatorEventType::IgnitionPin,
                                            1, 100000, true);
    EXPECT_TRUE(other.valid);
    EXPECT_FALSE(other.has_period);
    // Edges after the cutoff are ignored; an unfinished pulse is not a pulse.
    const auto early = lab::last_pulse_stat(events, EmulatorEventType::IgnitionPin,
                                            0, 19900, true);
    EXPECT_NEAR(early.width_ms, 3.0, 1e-9); // the second rise has no fall yet
    EXPECT_FALSE(lab::last_pulse_stat({}, EmulatorEventType::InjectorPin, 0, 1, true).valid);
    EXPECT_EQ(lab::injection_text(high), "TI 3.00 MS  DUTY 15.0%");
    EXPECT_EQ(lab::injection_text({}), "TI --");
    EXPECT_EQ(lab::coil_low_text(low), "LOW 17.00MS");
    EXPECT_EQ(lab::coil_low_text({}), "LOW --");
}

// D4: badges exist only for signals the snapshot carries; candidates say so.
TEST(EcuBadges, OnlySnapshotSignalsAndCandidatesAreMarked) {
    ma17::EmulatorSnapshot snapshot;
    auto badges = lab::ecu_badges(snapshot);
    ASSERT_EQ(badges.size(), 3u);
    EXPECT_FALSE(badges[0].active);
    EXPECT_FALSE(badges[1].active);
    EXPECT_FALSE(badges[2].active);
    EXPECT_EQ(badges[2].text, "DTC 0");
    EXPECT_TRUE(badges[1].candidate);
    EXPECT_NE(badges[1].text.find("cand."), std::string::npos);
    EXPECT_FALSE(badges[0].candidate);
    EXPECT_FALSE(badges[2].candidate);

    snapshot.throttle_available = true;
    snapshot.idle_contact_closed = true;
    snapshot.lamp_on_candidate = true;
    snapshot.ram27_faults = 0b101;
    snapshot.ram28_faults = 0b1;
    badges = lab::ecu_badges(snapshot);
    EXPECT_TRUE(badges[0].active);
    EXPECT_TRUE(badges[1].active);
    EXPECT_TRUE(badges[2].active);
    EXPECT_EQ(badges[2].text, "DTC 3");
    // The idle switch needs a valid throttle sample to be shown as active.
    snapshot.throttle_available = false;
    EXPECT_FALSE(lab::ecu_badges(snapshot)[0].active);
}

TEST(PulseStats, InjectionTextVariantsGetShorter) {
    lab::PulseStat stat;
    stat.valid = true;
    stat.width_ms = 1.45;
    stat.has_period = true;
    stat.period_ms = 6.1;
    stat.duty_percent = 23.7;
    const auto variants = lab::injection_text_variants(stat);
    ASSERT_EQ(variants.size(), 3u);
    EXPECT_EQ(variants[0], "TI 1.45 MS  DUTY 23.7%");
    EXPECT_EQ(variants[1], "TI 1.45MS 24%");
    EXPECT_EQ(variants[2], "TI 1.45MS");
    EXPECT_GT(variants[0].size(), variants[1].size());
    EXPECT_GT(variants[1].size(), variants[2].size());
    stat.has_period = false;
    EXPECT_EQ(lab::injection_text_variants(stat).size(), 1u);
    EXPECT_EQ(lab::injection_text_variants({}).front(), "TI --");
}

// D6: the readout says N/D for an invalid window and never fabricates values.
TEST(DynoReadout, ValidWindowFormatsAndInvalidSaysNd) {
    lab::DynoReadout readout;
    ASSERT_EQ(lab::dyno_readout_lines(readout).size(), 1u);
    EXPECT_EQ(lab::dyno_readout_lines(readout)[0], "LIVE N/D");
    readout = {true, 3001.0, 117.98, 37.1, 281.0, 0.84, 1.0};
    const auto lines = lab::dyno_readout_lines(readout);
    ASSERT_EQ(lines.size(), 2u);
    EXPECT_EQ(lines[0], "LIVE 3001 RPM  118.0 N.M  37.1 KW");
    EXPECT_EQ(lines[1], "BSFC 281  VE 0.84  LAM 1.00");
    readout.bsfc_g_kwh = 0.0; // power too low to define BSFC
    EXPECT_EQ(lab::dyno_readout_lines(readout)[1], "BSFC --  VE 0.84  LAM 1.00");
}

TEST(SparkQuality, NoReportBeforeTheFirstIgnition) {
    EXPECT_EQ(lab::spark_quality_text(false, 0.9, 0.1), "SPARK EFF --  RESIDUAL --");
    EXPECT_EQ(lab::spark_quality_text(true, 0.92, 0.11),
              "SPARK EFF 0.92  RESIDUAL 0.11");
    EXPECT_EQ(lab::spark_quality_text(true, std::nan(""), 0.1),
              "SPARK EFF --  RESIDUAL --");
}

// D8: the BENCH panel lines; an invalid window says N/D and invents nothing.
TEST(BenchPanel, OneValuePerLineAndNdForAnInvalidWindow) {
    EXPECT_EQ(lab::bench_panel_lines({}), (std::vector<std::string>{"N/D"}));
    const auto lines = lab::bench_panel_lines({true, 3001.0, 117.98, 37.1, 281.0, 0.84, 1.0});
    ASSERT_EQ(lines.size(), 5u);
    EXPECT_EQ(lines[0], "3001 RPM");
    EXPECT_EQ(lines[1], "118.0 N.M");
    EXPECT_EQ(lines[2], "37.1 KW");
    EXPECT_EQ(lines[3], "BSFC 281");
    EXPECT_EQ(lines[4], "VE 0.84  LAM 1.00");
    EXPECT_EQ(lab::bench_panel_lines({true, 900.0, 5.0, 0.5, 0.0, 0.3, 1.0})[3], "BSFC --");
}

// C3: speed presets and their hit testing.
TEST(SpeedSelector, ActivePresetAndHitTesting) {
    EXPECT_EQ(lab::active_speed_preset(0.25), 0);
    EXPECT_EQ(lab::active_speed_preset(1.0), 1);
    EXPECT_EQ(lab::active_speed_preset(4.0), 2);
    EXPECT_EQ(lab::active_speed_preset(2.0), -1); // after SPEED+: none claimed
    EXPECT_EQ(lab::speed_preset_at(5.0f, 5.0f, 0.0f, 0.0f, 40.0f, 20.0f), 0);
    EXPECT_EQ(lab::speed_preset_at(40.0f, 5.0f, 0.0f, 0.0f, 40.0f, 20.0f), 1);
    EXPECT_EQ(lab::speed_preset_at(119.9f, 19.9f, 0.0f, 0.0f, 40.0f, 20.0f), 2);
    EXPECT_EQ(lab::speed_preset_at(120.0f, 5.0f, 0.0f, 0.0f, 40.0f, 20.0f), -1);
    EXPECT_EQ(lab::speed_preset_at(5.0f, 20.0f, 0.0f, 0.0f, 40.0f, 20.0f), -1);
}

// C5: every button's tooltip names the key it is bound to (same keys as the
// shortcut tags and HELP).
TEST(LabButtonTooltips, EachNamesItsShortcut) {
    ASSERT_EQ(lab::lab_button_tooltips.size(), lab::lab_button_labels.size());
    const std::array<std::string_view, 9> expected{
        "(K)", "(S)", "DOWN", "UP ARROW", "(L)", "SPACE", "(-)", "(+)", "(M)"};
    for (std::size_t i = 0; i < expected.size(); ++i)
        EXPECT_NE(lab::lab_button_tooltips[i].find(expected[i]),
                  std::string_view::npos)
            << lab::lab_button_labels[i];
}

// HELP: every line fits the panel (it used to be a fixed 260 that hid the
// last two), and the overlay documents the shortcuts the controls show.
TEST(HelpText, PanelHoldsEveryLineAndNamesTheControlKeys) {
    const auto lines = lab::help_lines(false, false);
    const float height = lab::help_panel_height(lines.size());
    // the last line's top (48 + 26*(n-1)) plus a 16 px glyph row must fit
    EXPECT_GE(height, 48.0f + 26.0f * static_cast<float>(lines.size() - 1) + 16.0f);
    std::string all;
    for (const auto &line : lines)
        all += line + "\n";
    for (const char *needle : {"K KEY", "S START", "UP/DOWN PEDAL", "SPACE PAUSE",
                               "L LOAD", "M MUTE", "+/-", "CTRL+7..9 FONT",
                               "9 DYNO", "8 RUN WOT", "0.25X 1X 4X"})
        EXPECT_NE(all.find(needle), std::string::npos) << needle;
    EXPECT_EQ(all.find(" 0..3 UI"), std::string::npos); // never a bare 0..3
}

TEST(SliderPresets, MarkNamesMatchTheTicks) {
    ASSERT_EQ(lab::kPedalPresetLabels.size(), lab::kSliderPresets.size());
    EXPECT_STREQ(lab::kPedalPresetLabels.front(), "0");
    EXPECT_STREQ(lab::kPedalPresetLabels.back(), "WOT"); // 100 % = wide open
}

// C3: volume text and its state tag are separate; speed is no longer the label.
TEST(VolumeLabel, TextAndStateTagAreSeparate) {
    EXPECT_EQ(lab::volume_label(true, "on", 1.0).text, "VOL 100%");
    EXPECT_EQ(lab::volume_label(true, "on", 1.0).tag, "");
    EXPECT_EQ(lab::volume_label(true, "muted", 0.25).text, "VOL 25%");
    EXPECT_EQ(lab::volume_label(true, "muted", 0.25).tag, "MUTED");
    EXPECT_EQ(lab::volume_label(true, "speed", 1.0).tag, "SPD>1X");
    EXPECT_EQ(lab::volume_label(true, "key off", 1.0).tag, "KEY OFF");
    EXPECT_EQ(lab::volume_label(false, "off", 1.0).text, "AUDIO OFF");
    EXPECT_EQ(lab::volume_label(false, "unavailable", 1.0).text, "AUDIO N/D");
}

// 4.5: 60-2 wheel geometry.
TEST(TriggerWheel, FiftyEightTeethAndAGapEndingAtTheReference) {
    int teeth = 0;
    for (int p = 0; p < lab::kWheelPositions; ++p)
        teeth += lab::wheel_tooth_present(p) ? 1 : 0;
    EXPECT_EQ(teeth, 58);
    EXPECT_FALSE(lab::wheel_tooth_present(58));
    EXPECT_FALSE(lab::wheel_tooth_present(59));
    EXPECT_TRUE(lab::wheel_tooth_present(0));
    // Rotation is the crank angle relative to the TDC reference, wrapped.
    EXPECT_NEAR(lab::wheel_rotation_rad(0.5, 0.5), 0.0, 1e-12);
    EXPECT_NEAR(lab::wheel_rotation_rad(0.1, 0.3),
                2.0 * lab::kWheelPi - 0.2, 1e-12);
}

TEST(TriggerWheel, SensorSeesTheGapOncePerRevolution) {
    const double sensor = lab::kWheelPi / 2.0;
    int gap_steps = 0;
    int transitions = 0;
    bool previous = lab::wheel_sensor_sees_tooth(0.0, sensor);
    constexpr int steps = 3600; // 0.1 degree resolution
    for (int i = 1; i <= steps; ++i) {
        const double rotation = 2.0 * lab::kWheelPi * i / steps;
        const bool tooth = lab::wheel_sensor_sees_tooth(rotation, sensor);
        gap_steps += tooth ? 0 : 1;
        transitions += (tooth != previous) ? 1 : 0;
        previous = tooth;
    }
    // Two missing positions of 6 degrees: 12 degrees of the 360.
    EXPECT_NEAR(static_cast<double>(gap_steps), 120.0, 2.0);
    // One gap = one falling and one rising edge per revolution.
    EXPECT_EQ(transitions, 2);
}

// 4.4: the intake duct glow follows the manifold pressure.
TEST(DuctColor, IntakeAlphaFollowsManifoldPressure) {
    EXPECT_EQ(lab::intake_duct_alpha(0.0), 70);
    EXPECT_EQ(lab::intake_duct_alpha(-5.0), 70);
    EXPECT_EQ(lab::intake_duct_alpha(std::nan("")), 70); // no sample: dimmest
    EXPECT_EQ(lab::intake_duct_alpha(101325.0), 255);
    EXPECT_EQ(lab::intake_duct_alpha(200000.0), 255);    // clamped
    EXPECT_LT(lab::intake_duct_alpha(30000.0), lab::intake_duct_alpha(80000.0));
}

// Camshaft: lobes turn at half crank speed with the nose at the tappet at the
// middle of the lift.
TEST(CamShaft, NosePointsAtTheTappetAtPeakLiftAndTurnsAtHalfSpeed) {
    constexpr double pi = 3.14159265358979323846;
    for (std::size_t cylinder = 0; cylinder < 4; ++cylinder)
        for (const auto kind : {lab::ValveKind::Intake, lab::ValveKind::Exhaust}) {
            // Scan one cycle: the lift peaks where the cam angle is 0 (mod 2 pi).
            double best_angle = 0.0, best_lift = -1.0;
            for (int i = 0; i < 14400; ++i) {
                const double crank = 4.0 * pi * i / 14400.0;
                const double lift = lab::valve_lift_fraction(crank, cylinder, kind);
                if (lift > best_lift) {
                    best_lift = lift;
                    best_angle = crank;
                }
            }
            EXPECT_GT(best_lift, 0.999);
            double cam = lab::valve_cam_angle_rad(best_angle, cylinder, kind);
            cam = std::min(cam, 2.0 * pi - cam); // distance from 0
            EXPECT_LT(cam, 0.01) << cylinder;
            // Half speed: +60 deg of crank = +30 deg of cam.
            const double a = lab::valve_cam_angle_rad(1.0, cylinder, kind);
            const double b = lab::valve_cam_angle_rad(1.0 + pi / 3.0, cylinder, kind);
            double delta = std::fmod(b - a + 2.0 * pi, 2.0 * pi);
            EXPECT_NEAR(delta, pi / 6.0, 1e-9);
        }
}

// 4.5: the 0-720 ruler's schedule.
TEST(CycleRuler, ValveWindowsKeepTheirLengthAndWrapOnce) {
    for (std::size_t cylinder = 0; cylinder < 4; ++cylinder)
        for (const auto kind : {lab::ValveKind::Intake, lab::ValveKind::Exhaust}) {
            double total = 0.0;
            const auto spans = lab::valve_open_spans(cylinder, kind);
            ASSERT_GE(spans.size(), 1u);
            ASSERT_LE(spans.size(), 2u);
            for (const auto &span : spans) {
                EXPECT_GE(span.start_deg, 0.0);
                EXPECT_LE(span.end_deg, 720.0);
                EXPECT_LT(span.start_deg, span.end_deg);
                total += span.end_deg - span.start_deg;
            }
            EXPECT_NEAR(total, 222.0, 1e-9); // 353..575 and 143..365
        }
    // Cylinder 1 (offset 0): intake 353..575, exhaust 143..365.
    EXPECT_NEAR(lab::valve_open_spans(0, lab::ValveKind::Intake)[0].start_deg, 353.0, 1e-9);
    // Cylinder 2 (offset 540): intake 893 -> 173..., wraps: [173,395]
    const auto wrapped = lab::valve_open_spans(1, lab::ValveKind::Exhaust);
    EXPECT_EQ(wrapped.size(), 2u); // 143+540 = 683 .. 905 -> [683,720] + [0,185]
    EXPECT_NEAR(wrapped[0].start_deg, 683.0, 1e-9);
    EXPECT_NEAR(wrapped[1].end_deg, 185.0, 1e-9);
    EXPECT_NEAR(lab::cycle_angle_deg(0.0, 0.0), 0.0, 1e-12);
    EXPECT_NEAR(lab::cycle_angle_deg(-0.1, 0.0), 720.0 - 0.1 * 180.0 / 3.14159265358979323846, 1e-9);
    EXPECT_NEAR(lab::firing_mark_deg(3), 360.0, 1e-12);
}

// A valve is "open" on the ruler exactly where the lift model says it lifts.
TEST(CycleRuler, SpansAgreeWithTheLiftModel) {
    for (std::size_t cylinder = 0; cylinder < 4; ++cylinder)
        for (const auto kind : {lab::ValveKind::Intake, lab::ValveKind::Exhaust}) {
            const auto spans = lab::valve_open_spans(cylinder, kind);
            for (int degree = 0; degree < 720; degree += 3) {
                const double crank = degree * 3.14159265358979323846 / 180.0;
                const bool lifted =
                    lab::valve_lift_fraction(crank, cylinder, kind) > 0.0;
                bool in_span = false;
                for (const auto &span : spans)
                    // A span that starts at 0 is the tail of a window that
                    // wrapped past 720, so 0 itself is inside it.
                    in_span = in_span ||
                              ((degree > span.start_deg ||
                                (span.start_deg == 0.0 && degree == 0)) &&
                               degree < span.end_deg);
                EXPECT_EQ(lifted, in_span) << cylinder << " @" << degree;
            }
        }
}

TEST(CycleRuler, SparkSitsAdvanceDegreesBeforeTheFiringTdc) {
    EXPECT_NEAR(lab::spark_mark_deg(0, 26.6), 720.0 - 26.6, 1e-9); // wraps
    EXPECT_NEAR(lab::spark_mark_deg(3, 10.0), 350.0, 1e-9);        // 360 - 10
    EXPECT_NEAR(lab::spark_mark_deg(2, -5.0), 185.0, 1e-9);        // retard: after
    EXPECT_TRUE(std::isnan(lab::spark_mark_deg(1, std::nan(""))));
}

// Frente 0: widget rectangles as pure functions of layout and size.
TEST(WidgetRects, StayInsideTheWindowAndTheSpeedSelectorNeverTouchesFit) {
    const lab::LayoutState state{};
    for (const auto &size : std::vector<std::pair<int, int>>{
             {900, 620}, {1280, 720}, {1600, 900}, {1920, 1080}, {2560, 1440},
             {3440, 1440}}) {
        const int w = size.first, h = size.second;
        const float width = static_cast<float>(w), height = static_cast<float>(h);
        const SDL_FRect rects[] = {
            lab::view_selector_rect(state, w, h), lab::fit_button_rect(state, w, h),
            lab::pedal_slider_rect(state, w, h), lab::volume_slider_rect(state, w, h)};
        for (const SDL_FRect &r : rects) {
            EXPECT_GE(r.x, 0.0f) << w << "x" << h;
            EXPECT_GE(r.y, 0.0f);
            EXPECT_LE(r.x + r.w, width);
            EXPECT_LE(r.y + r.h, height);
            EXPECT_GT(r.w, 0.0f);
            EXPECT_GT(r.h, 0.0f);
        }
        if (lab::speed_selector_visible(state, w, h)) {
            const SDL_FRect speed = lab::speed_selector_rect(state, w, h);
            const SDL_FRect fit = lab::fit_button_rect(state, w, h);
            EXPECT_LT(speed.x + speed.w, fit.x) << w << "x" << h;
        }
        EXPECT_GE(lab::lab_ui_scale(w, h), 1.0f);
        EXPECT_LE(lab::lab_ui_scale(w, h), 2.0f);
    }
    // Below 1280x720 there is no speed selector at all.
    EXPECT_FALSE(lab::speed_selector_visible(state, 1100, 700));
}

TEST(WidgetRects, FixedUiScalePercentOverridesTheWindowSize) {
    lab::set_configured_ui_scale_percent(150);
    EXPECT_FLOAT_EQ(lab::lab_ui_scale(2560, 1440), 1.0f);
    lab::set_configured_ui_scale_percent(0);
    EXPECT_GT(lab::lab_ui_scale(2560, 1440), 1.0f);
}

// V1: cylindrical shading of the piston body.
TEST(PistonShade, DarkerAtTheEdgesSymmetricAndBounded) {
    EXPECT_EQ(lab::piston_shade_alpha(0.5), 0);
    EXPECT_EQ(lab::piston_shade_alpha(0.0), 150);
    EXPECT_EQ(lab::piston_shade_alpha(1.0), 150);
    EXPECT_EQ(lab::piston_shade_alpha(0.1), lab::piston_shade_alpha(0.9));
    EXPECT_LT(lab::piston_shade_alpha(0.3), lab::piston_shade_alpha(0.1));
    EXPECT_EQ(lab::piston_shade_alpha(-2.0), 150); // clamped
    EXPECT_GT(lab::piston_highlight_alpha(0.33), 40);
    EXPECT_EQ(lab::piston_highlight_alpha(0.7), 0);
    EXPECT_EQ(lab::piston_highlight_alpha(0.0), 0);
}

TEST(RodSection, NormalIsUnitAndPerpendicularAndSafeForAZeroBeam) {
    const lab::RodNormal n = lab::rod_normal(0.0f, 0.0f, 0.0f, 10.0f); // vertical beam
    EXPECT_NEAR(n.x, -1.0f, 1e-6);
    EXPECT_NEAR(n.y, 0.0f, 1e-6);
    const lab::RodNormal d = lab::rod_normal(1.0f, 2.0f, 4.0f, 6.0f);
    EXPECT_NEAR(std::hypot(d.x, d.y), 1.0f, 1e-6);
    EXPECT_NEAR(d.x * 3.0f + d.y * 4.0f, 0.0f, 1e-5); // perpendicular to (3,4)
    const lab::RodNormal zero = lab::rod_normal(5.0f, 5.0f, 5.0f, 5.0f);
    EXPECT_EQ(zero.x, 0.0f);
    EXPECT_EQ(zero.y, 0.0f);
}
