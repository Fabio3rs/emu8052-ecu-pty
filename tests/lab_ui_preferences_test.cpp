// UI-39: invalid or out-of-range presentation preferences must never be
// accepted; the defaults themselves must be valid.
#include "lab/LabUiPreferences.hpp"

#include <gtest/gtest.h>

#include <functional>
#include <limits>
#include <string>
#include <unistd.h>
#include <vector>

namespace {

using lab::LabUiPreferences;

LabUiPreferences with(const std::function<void(LabUiPreferences &)> &edit) {
    LabUiPreferences value;
    edit(value);
    return value;
}

} // namespace

TEST(LabUiPreferences, DefaultsAreValidAndEmbeddedFont) {
    const LabUiPreferences defaults;
    EXPECT_TRUE(lab::valid_ui_preferences(defaults));
    EXPECT_EQ(defaults.font, "embedded");
    EXPECT_EQ(defaults.theme, "lab");
    EXPECT_EQ(defaults.scale_percent, 0);
    EXPECT_EQ(defaults.font_percent, 100);
}

TEST(LabUiPreferences, EveryOutOfRangeFieldIsRejected) {
    const float nan = std::numeric_limits<float>::quiet_NaN();
    const float inf = std::numeric_limits<float>::infinity();
    const std::vector<std::pair<const char *, LabUiPreferences>> invalid{
        {"scale 120", with([](auto &v) { v.scale_percent = 120; })},
        {"left 0", with([](auto &v) { v.left_fraction = 0.0f; })},
        {"left nan", with([&](auto &v) { v.left_fraction = nan; })},
        {"right <= left", with([](auto &v) { v.right_fraction = 0.2f; })},
        {"right 1", with([](auto &v) { v.right_fraction = 1.0f; })},
        {"mode 3", with([](auto &v) { v.mode = 3; })},
        {"mode -1", with([](auto &v) { v.mode = -1; })},
        {"scope fraction 1", with([](auto &v) { v.scope_fraction = 1.0f; })},
        {"scope fraction -0.5",
         with([](auto &v) { v.scope_fraction = -0.5f; })},
        {"scope mode 2", with([](auto &v) { v.scope_mode = 2; })},
        {"analog group 11", with([](auto &v) { v.analog_group = 11; })},
        {"analog span too short",
         with([](auto &v) { v.analog_span_ticks = 1; })},
        {"digital span too long",
         with([](auto &v) { v.digital_span_ticks = 99999999; })},
        {"digital mask 16", with([](auto &v) { v.digital_channel_mask = 16; })},
        {"view mode 4", with([](auto &v) { v.view_mode = 4; })},
        {"shaft zoom 0.1", with([](auto &v) { v.shaft_zoom = 0.1f; })},
        {"axial zoom inf", with([&](auto &v) { v.axial_zoom = inf; })},
        {"pan x 2", with([](auto &v) { v.shaft_pan_x = 2.0f; })},
        {"pan y nan", with([&](auto &v) { v.axial_pan_y = nan; })},
        {"font percent 107", with([](auto &v) { v.font_percent = 107; })},
        {"units 2", with([](auto &v) { v.display_units = 2; })},
        {"camera pane negative",
         with([](auto &v) { v.camera_pane_width = -1.0f; })},
        {"camera scene too tall",
         with([](auto &v) { v.camera_scene_height = 5000.0f; })},
        {"font unknown", with([](auto &v) { v.font = "comic-sans"; })},
        {"theme unknown", with([](auto &v) { v.theme = "neon"; })},
        {"theme empty", with([](auto &v) { v.theme = ""; })},
        {"font file empty", with([](auto &v) { v.font = "file:"; })},
        {"font file with space",
         with([](auto &v) { v.font = "file:/a b.ttf"; })},
    };
    for (const auto &[name, value] : invalid)
        EXPECT_FALSE(lab::valid_ui_preferences(value)) << name;
}

TEST(LabUiPreferences, EveryPromisedModeAndScaleIsAccepted) {
    for (const int scale : {0, 100, 150, 200})
        for (const int mode : {0, 1, 2})
            for (const int font : {100, 105, 110})
                EXPECT_TRUE(lab::valid_ui_preferences(with([&](auto &v) {
                    v.scale_percent = scale;
                    v.mode = mode;
                    v.font_percent = font;
                })));
    for (const char *token : {"embedded", "bundled", "system", "file:/x/y.ttf"})
        EXPECT_TRUE(lab::valid_ui_preferences(with([&](auto &v) {
            v.font = token;
        }))) << token;
}

// ---- UI-09: persistence, legacy migration and layout restore --------------

#include "lab/LabLayout.hpp"

#include <cstdlib>
#include <filesystem>
#include <fstream>

namespace {

class PrefsDir : public ::testing::Test {
  protected:
    void SetUp() override {
        dir_ = std::filesystem::temp_directory_path() /
               ("sevel-prefs-" + std::to_string(::getpid()));
        std::filesystem::remove_all(dir_);
        std::filesystem::create_directories(dir_);
        setenv("XDG_DATA_HOME", dir_.c_str(), 1);
    }
    void TearDown() override { std::filesystem::remove_all(dir_); }
    std::filesystem::path file() const { return lab::ui_preferences_path(); }
    std::filesystem::path dir_;
};

bool same_prefs(const LabUiPreferences &a, const LabUiPreferences &b) {
    return a.scale_percent == b.scale_percent &&
           a.left_fraction == b.left_fraction &&
           a.right_fraction == b.right_fraction && a.mode == b.mode &&
           a.scope_fraction == b.scope_fraction &&
           a.scope_mode == b.scope_mode && a.analog_group == b.analog_group &&
           a.font_percent == b.font_percent &&
           a.display_units == b.display_units && a.view_mode == b.view_mode &&
           a.font == b.font && a.theme == b.theme && a.digital_channel_mask == b.digital_channel_mask;
}

} // namespace

TEST_F(PrefsDir, EveryPromisedCombinationSurvivesSaveAndLoad) {
    int combinations = 0;
    for (const int scale : {0, 100, 150, 200})
        for (const int mode : {0, 1, 2})
            for (const int units : {0, 1})
                for (const char *font : {"embedded", "bundled", "system"}) {
                    LabUiPreferences saved;
                    saved.scale_percent = scale;
                    saved.mode = mode;
                    saved.display_units = units;
                    saved.font = font;
                    saved.left_fraction = 0.3f;
                    saved.right_fraction = 0.7f;
                    saved.scope_fraction = mode == 1 ? 0.4f : -1.0f;
                    saved.analog_group = mode;
                    saved.view_mode = units + 1;
                    ASSERT_TRUE(lab::save_ui_preferences(saved));
                    const LabUiPreferences loaded = lab::load_ui_preferences();
                    EXPECT_TRUE(same_prefs(saved, loaded))
                        << scale << "/" << mode << "/" << units << "/" << font;
                    ++combinations;
                }
    EXPECT_EQ(combinations, 72);
}

// T1: the theme survives save/load, and a v10 file (no theme) loads as "lab".
TEST_F(PrefsDir, ThemeSurvivesSaveAndLoadAndV10DefaultsToLab) {
    LabUiPreferences saved;
    saved.theme = "oes";
    ASSERT_TRUE(lab::save_ui_preferences(saved));
    EXPECT_EQ(lab::load_ui_preferences().theme, "oes");
    std::ofstream(file(), std::ios::trunc)
        << "v10 150 0.24 0.66 0 -1 1 0 4950000 1980000 15 1 0 "
           "0.78 0 0 0.78 0 0 100 0 0 0 embedded\n";
    const LabUiPreferences loaded = lab::load_ui_preferences();
    EXPECT_EQ(loaded.scale_percent, 150);
    EXPECT_EQ(loaded.theme, "lab");
}

TEST_F(PrefsDir, InvalidSaveIsRefusedAndNeverCorruptsTheFile) {
    LabUiPreferences good;
    good.scale_percent = 150;
    ASSERT_TRUE(lab::save_ui_preferences(good));
    LabUiPreferences bad = good;
    bad.mode = 9;
    EXPECT_FALSE(lab::save_ui_preferences(bad));
    EXPECT_EQ(lab::load_ui_preferences().scale_percent, 150)
        << "previous file intact";
    // A hand-edited file with a bad field falls back to defaults, not to
    // partial garbage.
    std::ofstream(file(), std::ios::trunc)
        << "v10 999 0.24 0.66 0 -1 1 0 4950000 1980000 15 1 0 "
           "0.78 0 0 0.78 0 0 100 0 0 0 embedded\n";
    EXPECT_TRUE(same_prefs(lab::load_ui_preferences(), LabUiPreferences{}));
    std::ofstream(file(), std::ios::trunc) << "garbage\n";
    EXPECT_TRUE(same_prefs(lab::load_ui_preferences(), LabUiPreferences{}));
    std::ofstream(file(), std::ios::trunc) << "v99 100\n";
    EXPECT_TRUE(same_prefs(lab::load_ui_preferences(), LabUiPreferences{}));
}

TEST_F(PrefsDir, EveryLegacyVersionLoadsWithNewFieldsDefaulted) {
    struct Legacy {
        const char *line;
        int scale;
        float left;
        int mode;
    };
    const Legacy legacy[] = {
        {"v1 150\n", 150, 0.24f, 0},
        {"v2 150 0.3 0.7\n", 150, 0.3f, 0},
        {"v3 150 0.3 0.7 2\n", 150, 0.3f, 2},
        {"v4 100 0.3 0.7 1 -1\n", 100, 0.3f, 1},
        {"v5 200 0.3 0.7 1 -1 1 0 4950000 1980000 15\n", 200, 0.3f, 1},
        {"v9 0 0.24 0.66 0 -1 1 0 4950000 1980000 15 1 0 0.899232 0 0.177775 "
         "0.829993 0 0.202474 100 0 722.4 810.6\n",
         0, 0.24f, 0},
    };
    for (const Legacy &entry : legacy) {
        std::ofstream(file(), std::ios::trunc) << entry.line;
        const LabUiPreferences loaded = lab::load_ui_preferences();
        EXPECT_TRUE(lab::valid_ui_preferences(loaded)) << entry.line;
        EXPECT_EQ(loaded.scale_percent, entry.scale) << entry.line;
        EXPECT_FLOAT_EQ(loaded.left_fraction, entry.left) << entry.line;
        EXPECT_EQ(loaded.mode, entry.mode) << entry.line;
        EXPECT_EQ(loaded.font, "embedded") << entry.line; // field added in v10
        EXPECT_EQ(loaded.theme, "lab") << entry.line;     // field added in v11
    }
}

TEST(LabLayoutRestore, RestoreLayoutReturnsToTheDocumentedDefaults) {
    // "Restaurar layout" (SdlDisplay) resets exactly these fields.
    const lab::LayoutState defaults;
    EXPECT_FLOAT_EQ(defaults.left_fraction, 0.24f);
    EXPECT_FLOAT_EQ(defaults.right_fraction, 0.66f);
    EXPECT_LT(defaults.scope_fraction, 0.0f);
    EXPECT_EQ(defaults.mode, lab::LabPresentationMode::Bench);
    const LabUiPreferences prefs;
    EXPECT_FLOAT_EQ(prefs.left_fraction, defaults.left_fraction);
    EXPECT_FLOAT_EQ(prefs.right_fraction, defaults.right_fraction);
    EXPECT_FLOAT_EQ(prefs.scope_fraction, defaults.scope_fraction);
    // A dragged layout is a different state that restore must undo.
    const lab::LayoutState dragged = lab::LabLayout::with_divider_moved(
        defaults, 1, 500.0f, 400.0f, 1920.0f, 1080.0f);
    EXPECT_NE(dragged.left_fraction, defaults.left_fraction);
}
