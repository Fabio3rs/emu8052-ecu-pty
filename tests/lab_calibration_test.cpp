#include "lab/CalibrationCatalog.hpp"

#include <gtest/gtest.h>

namespace {
const std::string kRepo = LAB_REPO_PATH;
}

TEST(MiniJson, ParsesNestedValuesAndEscapes) {
    const auto json = lab::parse_json(
        R"({"a":[1,2.5,-3e2],"b":{"c":"x\"y°"},"d":true,"e":null})");
    ASSERT_TRUE(json);
    EXPECT_EQ(json->get("a")->array.size(), 3u);
    EXPECT_DOUBLE_EQ(json->get("a")->array[2].number, -300.0);
    EXPECT_EQ(json->get("b")->get("c")->string, "x\"y\xC2\xB0");
    EXPECT_TRUE(json->get("d")->boolean);
}

TEST(MiniJson, RejectsMalformedAndTooDeepInput) {
    EXPECT_FALSE(lab::parse_json("{\"a\":"));
    EXPECT_FALSE(lab::parse_json("[1,2,]x"));
    EXPECT_FALSE(lab::parse_json("\"unterminated"));
    EXPECT_FALSE(lab::parse_json(std::string(200, '[') + std::string(200, ']')));
}

// K1: the catalog's 34 two-dimensional tables, with real ROM bytes.
TEST(CalibrationCatalog, LoadsThe34TwoDimensionalTablesWithRomBytes) {
    const auto loaded = lab::load_calibration_catalog(
        kRepo + "/docs/MA17_CALIBRATION_CATALOG.json",
        kRepo + "/FiatTipo_MA17_dump_27c256.bin");
    EXPECT_EQ(loaded.error, "");
    ASSERT_EQ(loaded.tables.size(), 34u);
    const lab::CalibrationTable *table = nullptr;
    for (const auto &t : loaded.tables)
        if (t.id == "flag_selected_matrix_7cae")
            table = &t;
    ASSERT_NE(table, nullptr);
    EXPECT_EQ(table->start, 0x7CAEu);
    EXPECT_EQ(table->rows, 8);
    EXPECT_EQ(table->cols, 15);
    EXPECT_EQ(table->bytes.size(), 120u);
    EXPECT_GT(table->different_bytes_vs_g.at("S88"), 0);
    EXPECT_FALSE(table->row_axis.empty()); // raw source text, not a physical name
}

// Honesty: nothing is named by a physical function the catalog does not give.
TEST(CalibrationCatalog, PhysicalFunctionStaysUnknownWhereTheCatalogSaysSo) {
    const auto loaded = lab::load_calibration_catalog(
        kRepo + "/docs/MA17_CALIBRATION_CATALOG.json",
        kRepo + "/FiatTipo_MA17_dump_27c256.bin");
    int unknown = 0;
    for (const auto &t : loaded.tables) {
        const auto seal = lab::confidence_seal(t);
        if (!seal.physical_known)
            ++unknown;
        // The shown name is the catalog id; no ignition/injection naming.
        for (const char *forbidden : {"ignition", "injection", "lambda_map"})
            EXPECT_EQ(t.id.find(forbidden), std::string::npos) << t.id;
    }
    EXPECT_GE(unknown, 33);
    // The 7CAE table: layout confirmed, function unknown.
    for (const auto &t : loaded.tables)
        if (t.id == "flag_selected_matrix_7cae") {
            const auto seal = lab::confidence_seal(t);
            EXPECT_EQ(seal.physical, "FUNCTION UNKNOWN");
            EXPECT_FALSE(seal.physical_known);
        }
}

TEST(CalibrationCatalog, HeatmapIntensityIsMonotonicAndBounded) {
    EXPECT_FLOAT_EQ(lab::heatmap_intensity(0, 0, 200), 0.0f);
    EXPECT_FLOAT_EQ(lab::heatmap_intensity(200, 0, 200), 1.0f);
    EXPECT_LT(lab::heatmap_intensity(50, 0, 200), lab::heatmap_intensity(51, 0, 200));
    EXPECT_FLOAT_EQ(lab::heatmap_intensity(7, 7, 7), 0.0f); // flat table
}

TEST(CalibrationCatalog, TablesOutsideTheRomAreSkippedWithAnError) {
    const std::string catalog =
        R"({"tables":[{"id":"x","start":"0xFFF0","dimensions":[4,4],"axes":[],
            "confidence":{"physical_function":"unknown"}}]})";
    const auto loaded = lab::parse_calibration_catalog(catalog,
                                                       std::vector<std::uint8_t>(64, 0));
    EXPECT_TRUE(loaded.tables.empty());
    EXPECT_NE(loaded.error.find("outside"), std::string::npos);
}

// K2: addresses map to (row, col); the newest read decides the active table.
TEST(CalibrationTrace, MapsReadAddressesToCellsAndPicksTheNewestTable) {
    lab::CalibrationTable a;
    a.id = "a";
    a.start = 0x7000;
    a.rows = 2;
    a.cols = 3;
    a.bytes.assign(6, 0);
    lab::CalibrationTable b = a;
    b.id = "b";
    b.start = 0x7100;
    const std::vector<lab::CalibrationTable> tables{a, b};
    const auto cell = lab::locate_cell(a, 0x7004);
    ASSERT_TRUE(cell);
    EXPECT_EQ(cell->row, 1);
    EXPECT_EQ(cell->col, 1);
    EXPECT_FALSE(lab::locate_cell(a, 0x6FFF));
    EXPECT_FALSE(lab::locate_cell(a, 0x7006)); // one past the end
    const std::vector<std::uint16_t> reads{0x7101, 0x7000, 0x9999, 0x7005};
    EXPECT_EQ(lab::most_recent_table(tables, reads), 1u); // 0x7101 is newest
    const auto in_a = lab::active_cells(a, reads);
    ASSERT_EQ(in_a.size(), 2u);
    EXPECT_EQ(in_a[0].row, 0); // 0x7000, newest first among table a's cells
    EXPECT_EQ(in_a[1].row, 1);
    EXPECT_FALSE(lab::most_recent_table(tables, std::vector<std::uint16_t>{0x1}));
}

// K3: the per-cell diff reproduces the catalog's own per-table byte counts for
// every variant whose ROM image is in the repository.
TEST(CalibrationVariants, CellDiffCountsMatchTheCatalog) {
    const auto loaded = lab::load_calibration_catalog(
        kRepo + "/docs/MA17_CALIBRATION_CATALOG.json",
        kRepo + "/FiatTipo_MA17_dump_27c256.bin");
    ASSERT_EQ(loaded.tables.size(), 34u);
    ASSERT_FALSE(loaded.variant_sha256.empty());
    const std::vector<std::pair<std::string, std::string>> roms{
        {"A+", kRepo + "/firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin"},
        {"S36", kRepo + "/firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 36fd.bin"},
        {"S37", kRepo + "/firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 37a5.bin"},
        {"S88", kRepo + "/firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin"}};
    const auto read = [](const std::string &path) {
        std::ifstream f(path, std::ios::binary);
        return std::vector<std::uint8_t>((std::istreambuf_iterator<char>(f)),
                                         std::istreambuf_iterator<char>());
    };
    const auto g = read(kRepo + "/FiatTipo_MA17_dump_27c256.bin");
    ASSERT_EQ(g.size(), 32768u);
    int compared = 0;
    for (const auto &[variant, path] : roms) {
        const auto other = read(path);
        ASSERT_EQ(other.size(), 32768u) << path;
        for (const auto &table : loaded.tables) {
            const auto expected = table.different_bytes_vs_g.find(variant);
            if (expected == table.different_bytes_vs_g.end())
                continue;
            const auto diff = lab::table_diff_cells(table, g, other);
            EXPECT_EQ(lab::count_changed_cells(diff), expected->second)
                << variant << " " << table.id;
            ++compared;
        }
    }
    EXPECT_GT(compared, 100);
    // A table never differs from itself.
    EXPECT_EQ(lab::count_changed_cells(
                  lab::table_diff_cells(loaded.tables[0], g, g)), 0);
}

// A table whose catalog entry has no layout key is "not stated", never
// "unverified": the seal reports only what the catalog says.
TEST(CalibrationCatalog, MissingLayoutKeyIsNotStatedNeverUnverified) {
    lab::CalibrationTable none;
    EXPECT_EQ(lab::confidence_seal(none).layout, "LAYOUT NOT STATED");
    lab::CalibrationTable confirmed;
    confirmed.layout_confidence = "confirmed_all_six";
    EXPECT_EQ(lab::confidence_seal(confirmed).layout, "LAYOUT CONFIRMED");
    lab::CalibrationTable open;
    open.layout_confidence = "unverified";
    EXPECT_EQ(lab::confidence_seal(open).layout, "LAYOUT UNVERIFIED");
    const auto loaded = lab::load_calibration_catalog(
        kRepo + "/docs/MA17_CALIBRATION_CATALOG.json",
        kRepo + "/FiatTipo_MA17_dump_27c256.bin");
    int not_stated = 0;
    for (const auto &table : loaded.tables)
        if (lab::confidence_seal(table).layout == "LAYOUT NOT STATED")
            ++not_stated;
    EXPECT_EQ(not_stated, 16); // the tables the catalog documents differently
}
