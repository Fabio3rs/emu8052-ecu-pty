#include "lab/DynoCurve.hpp"

#include <gtest/gtest.h>

#include <sstream>

namespace {
const std::string kDocs = LAB_DOCS_PATH;
}

TEST(DynoCurve, SplitsQuotedFieldsWithCommas) {
    const auto fields = lab::split_csv_record("a,\"[1.0, 2.0]\",\"say \"\"hi\"\"\",d");
    ASSERT_EQ(fields.size(), 4u);
    EXPECT_EQ(fields[1], "[1.0, 2.0]");
    EXPECT_EQ(fields[2], "say \"hi\"");
}

// Acceptance (v2 doc, section 8): with sweep_tdc120.csv loaded, the torque
// peak is 118.0 N.m (+-0.1) at 3000 rpm.
TEST(DynoCurve, RomSweepPeaksAt118NmAt3000Rpm) {
    const auto loaded =
        lab::load_dyno_csv(kDocs + "/dyno/rom/sweep_tdc120.csv", "ROM TDC 120");
    ASSERT_TRUE(loaded.curve) << loaded.error;
    const auto *peak = lab::peak_torque(*loaded.curve);
    ASSERT_NE(peak, nullptr);
    EXPECT_NEAR(peak->torque_nm, 118.0, 0.1);
    EXPECT_NEAR(peak->rpm, 3000.0, 5.0);
    EXPECT_EQ(lab::dyno_point_text(*peak), "3001 rpm  118.0 N.m  37.1 kW");
    ASSERT_TRUE(loaded.curve->provenance);
    EXPECT_FALSE(loaded.curve->provenance->code_sha.empty());
    EXPECT_EQ(loaded.curve->provenance->rom_sha256.size(), 64u);
    EXPECT_NEAR(loaded.curve->provenance->tdc_deg, 120.0, 1e-9);
}

// The 117..123 reference band: the TDC hypotheses give a spread at 3000 rpm.
TEST(DynoCurve, TdcHypothesesBracketTheReference) {
    double low = 1e9, high = 0.0;
    for (const char *name : {"117", "120", "123"}) {
        const auto loaded = lab::load_dyno_csv(
            kDocs + "/dyno/rom/sweep_tdc" + name + ".csv", name);
        ASSERT_TRUE(loaded.curve) << loaded.error;
        const auto *peak = lab::peak_torque(*loaded.curve);
        low = std::min(low, peak->torque_nm);
        high = std::max(high, peak->torque_nm);
    }
    EXPECT_LT(low, high);
    EXPECT_NEAR(low, 114.9, 0.3);   // document: 114.9 .. 120.2 N.m
    EXPECT_NEAR(high, 120.2, 0.3);
}

TEST(DynoCurve, ModelCsvLoadsWithoutProvenance) {
    const auto loaded = lab::load_dyno_csv(kDocs + "/dyno_wot_e0.csv", "model E0");
    ASSERT_TRUE(loaded.curve) << loaded.error;
    EXPECT_FALSE(loaded.curve->provenance);
    EXPECT_GT(loaded.curve->points.size(), 10u);
    const auto *peak = lab::peak_torque(*loaded.curve);
    EXPECT_NEAR(peak->torque_nm, 130.0, 0.5);
}

// Y2: a ROM sweep without provenance never becomes a curve.
TEST(DynoCurve, RejectsRomSweepWithoutProvenance) {
    std::istringstream csv(
        "state,mean_rpm,shaft_torque_nm,shaft_power_kw,code_sha,rom_sha256\n"
        "ACCEPTED,3000,118.0,37.1,,\n");
    const auto loaded = lab::parse_dyno_csv(csv, "bad");
    EXPECT_FALSE(loaded.curve);
    EXPECT_NE(loaded.error.find("provenance"), std::string::npos);
}

TEST(DynoCurve, OnlyAcceptedPointsAreCurvePoints) {
    std::istringstream csv(
        "state,mean_rpm,shaft_torque_nm,shaft_power_kw,code_sha,rom_sha256\n"
        "INVALID,2000,50.0,10.0,aa,bb\n"
        "ACCEPTED,3000,118.0,37.1,aa,bb\n");
    const auto loaded = lab::parse_dyno_csv(csv, "mix");
    ASSERT_TRUE(loaded.curve);
    ASSERT_EQ(loaded.curve->points.size(), 1u);
    EXPECT_EQ(loaded.curve->points[0].rpm, 3000.0);
}

// Freeze keeps a grey copy of the live curve for comparison with the next run.
TEST(DynoFreeze, CopiesTheLiveCurveAndReplacesAnEarlierCopy) {
    std::vector<lab::DynoCurve> curves(1);
    curves[0].label = "RUN WOT";
    EXPECT_FALSE(lab::freeze_curve(curves, "RUN WOT")); // empty: nothing to keep
    EXPECT_EQ(curves.size(), 1u);
    curves[0].points.push_back({3000.0, 130.0, 40.0});
    ASSERT_TRUE(lab::freeze_curve(curves, "RUN WOT"));
    ASSERT_EQ(curves.size(), 2u);
    EXPECT_TRUE(curves[1].frozen);
    EXPECT_EQ(curves[1].label, "FROZEN RUN WOT");
    EXPECT_FALSE(curves[0].frozen);
    // The live curve changes; freezing again replaces, never accumulates.
    curves[0].points[0].torque_nm = 140.0;
    ASSERT_TRUE(lab::freeze_curve(curves, "RUN WOT"));
    ASSERT_EQ(curves.size(), 2u);
    EXPECT_EQ(curves[1].points[0].torque_nm, 140.0);
    EXPECT_FALSE(lab::freeze_curve(curves, "NO SUCH CURVE"));
}
