#include "lab/RunSnapshot.hpp"

#include <gtest/gtest.h>

#include <filesystem>

TEST(Sha256, MatchesTheStandardVectors) {
    EXPECT_EQ(lab::sha256_hex({}),
              "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    const std::string abc = "abc";
    EXPECT_EQ(lab::sha256_hex({abc.begin(), abc.end()}),
              "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    // Crosses the 56-byte padding boundary.
    const std::string long_text(64, 'a');
    EXPECT_EQ(lab::sha256_hex({long_text.begin(), long_text.end()}),
              "ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb");
}

namespace {
lab::RunSnapshot sample(const std::string &label, double torque, double advance) {
    lab::RunSnapshot s;
    s.label = label;
    s.rom_sha256 = std::string(64, 'a');
    s.code_sha = "cf0cdda";
    s.scenario = "wot e0 tdc120";
    s.metrics.advance_deg = advance;
    s.metrics.lambda = 1.0;
    s.curve = {{2000.0, torque - 5.0}, {3000.0, torque}, {4000.0, torque - 2.0}};
    s.tables["t1"] = {1, 2, 3, 4};
    return s;
}
} // namespace

TEST(RunSnapshot, JsonRoundTripKeepsEverythingIncludingNaN) {
    auto s = sample("A", 118.0, 18.6);
    s.metrics.ti_ms = std::nan(""); // not measured
    const auto loaded = lab::snapshot_from_json(lab::snapshot_to_json(s));
    ASSERT_TRUE(loaded);
    EXPECT_EQ(loaded->label, "A");
    EXPECT_EQ(loaded->rom_sha256, s.rom_sha256);
    EXPECT_DOUBLE_EQ(loaded->metrics.advance_deg, 18.6);
    EXPECT_TRUE(std::isnan(loaded->metrics.ti_ms));
    ASSERT_EQ(loaded->curve.size(), 3u);
    EXPECT_DOUBLE_EQ(loaded->curve[1].torque_nm, 118.0);
    EXPECT_EQ(loaded->tables.at("t1"), (std::vector<std::uint8_t>{1, 2, 3, 4}));
    EXPECT_FALSE(lab::snapshot_from_json("{\"schema\":\"other\"}"));
    EXPECT_FALSE(lab::snapshot_from_json("not json"));
}

TEST(RunSnapshot, FileSaveAndLoad) {
    const auto path = std::filesystem::temp_directory_path() / "sevel-snap-test.json";
    ASSERT_TRUE(lab::save_run_snapshot(path.string(), sample("B", 120.0, 20.0)));
    const auto loaded = lab::load_run_snapshot(path.string());
    ASSERT_TRUE(loaded);
    EXPECT_EQ(loaded->label, "B");
    std::filesystem::remove(path);
    EXPECT_FALSE(lab::load_run_snapshot("/nonexistent/x.json"));
}

// Acceptance (v2 doc, K4): deltas with unit and sign.
TEST(RunSnapshot, DeltasHaveUnitAndSign) {
    const auto a = sample("A", 118.0, 18.6);
    auto b = sample("B", 122.2, 21.1);
    b.tables["t1"] = {1, 2, 9, 4};
    b.code_sha = "abc1234";
    const auto lines = lab::compare_snapshots(a, b);
    const auto has = [&](const std::string &needle) {
        return std::find(lines.begin(), lines.end(), needle) != lines.end();
    };
    EXPECT_TRUE(has("CODE DIFFERS"));
    EXPECT_FALSE(has("ROM DIFFERS"));
    EXPECT_TRUE(has("D TORQUE +4.2 N.M @3000 RPM"));
    EXPECT_TRUE(has("D ADVANCE +2.5 DEG"));
    EXPECT_TRUE(has("D LAMBDA +0.00"));
    EXPECT_TRUE(has("1 TABLES CHANGED"));
    EXPECT_FALSE(std::any_of(lines.begin(), lines.end(),
                             [](const std::string &l) { return l.find("TI") != std::string::npos &&
                                                               l.find("D TI") == 0; }))
        << "TI was not measured in either snapshot";
}
