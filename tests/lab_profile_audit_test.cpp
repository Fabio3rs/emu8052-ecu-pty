// UI-22: audit every instrument's scale, bands, labels, text and unit
// conversion so no dial can ship with an inconsistent scale.
#include "lab/DisplayUnits.hpp"
#include "lab/SevelInstrumentProfile.hpp"

#include <gtest/gtest.h>

#include <cctype>
#include <cmath>
#include <set>
#include <string>

namespace {

using lab::DisplayUnits;
using lab::profile::Instrument;

bool near_multiple(double value, double step) {
    const double ratio = value / step;
    return std::fabs(ratio - std::round(ratio)) < 1e-6;
}

bool is_dial(const Instrument &i) { return i.maximum > i.minimum; }

void check_scale(const Instrument &i, const char *context) {
    SCOPED_TRACE(std::string(i.id) + " " + context);
    ASSERT_TRUE(std::isfinite(i.minimum) && std::isfinite(i.maximum));
    if (!is_dial(i))
        return;
    EXPECT_GT(i.major_step, 0.0);
    EXPECT_GT(i.minor_step, 0.0);
    EXPECT_GE(i.major_step, i.minor_step - 1e-9);
    EXPECT_TRUE(near_multiple(i.major_step, i.minor_step))
        << "ticks must align";
    EXPECT_TRUE(near_multiple(i.maximum - i.minimum, i.minor_step))
        << "the last tick must land on the maximum";
    ASSERT_LE(i.band_count, i.bands.size());
    for (std::size_t b = 0; b < i.band_count; ++b) {
        EXPECT_LT(i.bands[b].start, i.bands[b].end);
        EXPECT_GE(i.bands[b].start, i.minimum - 1e-9);
        EXPECT_LE(i.bands[b].end, i.maximum + 1e-9);
        EXPECT_GT(i.bands[b].color.a, 0);
    }
    if (i.label_step > 0.0) {
        EXPECT_GT(i.label_divisor, 0.0);
        EXPECT_TRUE(near_multiple(i.label_step, i.major_step))
            << "numerals sit on major ticks";
        EXPECT_LE(i.label_step, i.maximum - i.minimum + 1e-9);
    }
}

} // namespace

TEST(LabProfileAudit, EveryInstrumentHasIdentityTextAndAUnit) {
    std::set<std::string> ids;
    for (const Instrument *i : lab::profile::all_instruments) {
        ASSERT_NE(i->id, nullptr);
        const std::string id = i->id;
        EXPECT_FALSE(id.empty());
        EXPECT_TRUE(ids.insert(id).second) << "duplicate id " << id;
        for (const char c : id)
            EXPECT_TRUE(std::islower(static_cast<unsigned char>(c)) ||
                        std::isdigit(static_cast<unsigned char>(c)) || c == '_')
                << id;
        ASSERT_NE(i->title, nullptr);
        EXPECT_FALSE(std::string(i->title).empty()) << id;
        EXPECT_LE(std::string(i->title).size(), 20U)
            << id << ": title must fit a card";
        ASSERT_NE(i->unit, nullptr) << id;
        ASSERT_NE(i->source, nullptr) << id;
        EXPECT_FALSE(std::string(i->source).empty())
            << id << ": tooltip origin";
        // Titles are uppercase technical English (decision A.7).
        for (const char c : std::string(i->title))
            EXPECT_FALSE(std::islower(static_cast<unsigned char>(c)))
                << i->title;
    }
}

TEST(LabProfileAudit, EveryScaleIsConsistentInMetricAndImperial) {
    for (const Instrument *i : lab::profile::all_instruments) {
        check_scale(*i, "metric");
        check_scale(lab::display_profile(*i, DisplayUnits::Imperial),
                    "imperial");
    }
}

TEST(LabProfileAudit, UnavailableInstrumentsAreMarkedNotZeroed) {
    // VE now comes from the plant window (GOAL_SEVEL_FISICA); no instrument is
    // left without a model. An instrument may still be marked undefined later,
    // in which case it must say so in its source instead of being zeroed.
    const auto &ve = lab::profile::volumetric_efficiency;
    EXPECT_FALSE(ve.undefined);
    EXPECT_NE(std::string(ve.source).find("plant window"), std::string::npos);
    for (const Instrument *i : lab::profile::all_instruments)
        if (i->undefined)
            EXPECT_STREQ(i->source, "unavailable") << i->title;
}

TEST(LabProfileAudit, SpecScalesMatchTheDocument) {
    // docs/SEVEL_TIPO_16_SPECS.md: tachometer 0-8000, speedometer 0-200,
    // coolant 50-90-130.
    EXPECT_EQ(lab::profile::rpm.maximum, 8000.0);
    EXPECT_EQ(lab::profile::speed.maximum, 200.0);
    EXPECT_EQ(lab::profile::coolant.minimum, 50.0);
    EXPECT_EQ(lab::profile::coolant.maximum, 130.0);
    EXPECT_EQ(lab::profile::coolant.label_step, 40.0);
    // Conversions keep the numerals on the converted major ticks.
    const auto mph =
        lab::display_profile(lab::profile::speed, DisplayUnits::Imperial);
    EXPECT_NEAR(mph.maximum, 200.0 * 0.621371192237334, 1e-9);
    const auto fahrenheit =
        lab::display_profile(lab::profile::coolant, DisplayUnits::Imperial);
    EXPECT_NEAR(fahrenheit.minimum, 122.0, 1e-9);
    EXPECT_NEAR(fahrenheit.maximum, 266.0, 1e-9);
}
