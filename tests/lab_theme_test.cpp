#include "lab/LabTheme.hpp"

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <regex>
#include <sstream>
#include <string>
#include <vector>

namespace {
const std::filesystem::path kRepo = LAB_REPO_PATH;

std::string slurp(const std::filesystem::path &path) {
    std::ifstream in(path);
    std::ostringstream text;
    text << in.rdbuf();
    return text.str();
}
} // namespace

// T3: a role colour is spelled once, in the theme headers. A literal of an
// accent / alarm / flow colour anywhere else fails this test.
TEST(LabThemeAudit, RoleColoursAreNotSpelledOutsideTheThemeHeaders) {
    const std::vector<std::string> forbidden{"99, 211, 220", "238, 68, 69",
                                             "0.898f"};
    int scanned = 0;
    for (const char *dir : {"include/lab", "src/lab", "apps/sevel-ma17-lab"})
        for (const auto &entry :
             std::filesystem::directory_iterator(kRepo / dir)) {
            const std::string name = entry.path().filename().string();
            if (name == "LabTheme.hpp" || name == "ThemePalette.hpp")
                continue;
            const std::string ext = entry.path().extension().string();
            if (ext != ".hpp" && ext != ".cpp")
                continue;
            ++scanned;
            const std::string text = slurp(entry.path());
            for (const auto &literal : forbidden)
                EXPECT_EQ(text.find(literal), std::string::npos)
                    << name << " spells a themed colour: " << literal;
        }
    EXPECT_GT(scanned, 20);
}

TEST(LabTheme, RolesAreDistinctAndThemesSelectable) {
    using lab::kLabPalette;
    using lab::kOesPalette;
    for (const auto *palette : {&kLabPalette, &kOesPalette}) {
        EXPECT_NE(palette->intake, palette->exhaust);
        EXPECT_NE(palette->intake, palette->needle);
    }
    // Lab needle never matches the critical colour; the OES needle may.
    const std::array<float, 3> critical{
        static_cast<float>(lab::kCritical.r) / 255.0f,
        static_cast<float>(lab::kCritical.g) / 255.0f,
        static_cast<float>(lab::kCritical.b) / 255.0f};
    const auto distance = [&](const std::array<float, 3> &a) {
        float sum = 0.0f;
        for (std::size_t i = 0; i < 3; ++i)
            sum += (a[i] - critical[i]) * (a[i] - critical[i]);
        return sum;
    };
    EXPECT_GT(distance(kLabPalette.needle), 0.3f);
    // The accent differs from both flow colours and from critical.
    EXPECT_NE(lab::kAccent.r, lab::kCritical.r);
    EXPECT_NE(lab::kPairA.r, lab::kPairB.r);

    EXPECT_TRUE(lab::select_theme("oes"));
    EXPECT_STREQ(lab::palette().name, "oes");
    EXPECT_FALSE(lab::select_theme("nonexistent"));
    EXPECT_STREQ(lab::palette().name, "oes"); // unchanged
    EXPECT_TRUE(lab::select_theme("lab"));
    EXPECT_STREQ(lab::palette().name, "lab");
}

// L3: the drawing code uses the named text scales, not scattered literals. The
// old small-scale literals (0.55 / 0.60 / 0.65 / 0.68 / 0.70 / 0.72 / 0.75) must
// not be multiplied by a UI scale or used to size measured text again.
TEST(LabTextScaleAudit, NoScatteredSmallScaleLiteralsInDrawingCode) {
    const std::vector<std::string> small{"0.55f", "0.60f", "0.65f", "0.68f",
                                         "0.70f", "0.72f", "0.75f"};
    int scanned = 0;
    for (const char *dir : {"src/lab", "apps/sevel-ma17-lab"})
        for (const auto &entry : std::filesystem::directory_iterator(kRepo / dir)) {
            const std::string ext = entry.path().extension().string();
            const std::string name = entry.path().filename().string();
            if ((ext != ".cpp" && ext != ".hpp") || name == "DonorScene.cpp")
                continue;
            ++scanned;
            const std::string text = slurp(entry.path());
            for (const auto &literal : small)
                for (const char *tail : {" * ui_scale", " * scale"}) {
                    EXPECT_EQ(text.find(literal + tail), std::string::npos)
                        << name << ": " << literal << tail;
                }
        }
    EXPECT_GT(scanned, 8);
}

// L3: nothing sizes drawn text with a linear `font.measure(x) * scale`: the
// pixel face snaps to whole design pixels, so that estimate disagrees with the
// glyphs actually drawn. `font.width(x, scale)` is the snapped width.
TEST(LabTextScaleAudit, TextIsSizedWithTheSnappedWidthNotALinearMeasure) {
    const std::regex linear(R"(font\.measure\([^;]*\)\s*\*\s*[A-Za-z_])");
    int scanned = 0;
    for (const char *dir : {"src/lab", "apps/sevel-ma17-lab"})
        for (const auto &entry : std::filesystem::directory_iterator(kRepo / dir)) {
            const std::string ext = entry.path().extension().string();
            if (ext != ".cpp" && ext != ".hpp")
                continue;
            ++scanned;
            std::string text = slurp(entry.path());
            std::smatch found;
            EXPECT_FALSE(std::regex_search(text, found, linear))
                << entry.path().filename().string() << ": " << found.str();
        }
    EXPECT_GT(scanned, 8);
}
