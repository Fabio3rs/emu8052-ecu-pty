#pragma once

#include "lab/MiniJson.hpp"

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iterator>
#include <map>
#include <optional>
#include <span>
#include <sstream>
#include <string>
#include <vector>

namespace lab {

// K1: the two-dimensional calibration tables of docs/MA17_CALIBRATION_CATALOG
// .json, with the cell bytes read from the ROM at each table's address. The
// catalog knows layouts and bytes, but for almost every table it records the
// physical meaning as "unknown"; the view must say so and never invent a name.
struct CalibrationTable {
    std::string id;          // the catalog id: the only name shown
    unsigned start = 0;      // ROM address of the first cell
    int rows = 0;
    int cols = 0;
    std::string row_axis;    // raw source of the row index, as the catalog says
    std::string col_axis;
    std::string layout_confidence;   // e.g. "confirmed_all_six"
    std::string physical_function;   // e.g. "unknown"
    std::map<std::string, int> different_bytes_vs_g; // variant -> byte count
    std::vector<std::uint8_t> bytes; // rows * cols, row-major

    std::uint8_t cell(int row, int col) const {
        return bytes[static_cast<std::size_t>(row * cols + col)];
    }
};

// The confidence seal printed on the heatmap. Derived only from the catalog's
// `confidence.physical_function` and layout fields.
struct ConfidenceSeal {
    std::string layout;   // "LAYOUT CONFIRMED" / "LAYOUT UNVERIFIED"
    std::string physical; // "FUNCTION UNKNOWN" / "FUNCTION CONFIRMED" / "N/A"
    bool physical_known = false;
};

inline ConfidenceSeal confidence_seal(const CalibrationTable &table) {
    ConfidenceSeal seal;
    const std::string &layout = table.layout_confidence;
    // Only what the catalog says: a recognised layout key that is confirmed,
    // one that is not, or no layout key at all (16 of the 34 tables record
    // their confirmations under other keys, which is not "unverified").
    seal.layout = layout.empty()                    ? "LAYOUT NOT STATED"
                  : layout.rfind("confirmed", 0) == 0 ? "LAYOUT CONFIRMED"
                                                      : "LAYOUT UNVERIFIED";
    const std::string &fn = table.physical_function;
    if (fn.rfind("confirmed", 0) == 0) {
        seal.physical = "FUNCTION CONFIRMED";
        seal.physical_known = true;
    } else if (fn == "not_applicable") {
        seal.physical = "N/A";
    } else {
        seal.physical = "FUNCTION UNKNOWN"; // "unknown", missing, hypotheses
    }
    return seal;
}

// Single-hue sequential scale: 0 (light) .. 1 (dark) from a raw byte.
inline float heatmap_intensity(std::uint8_t value, std::uint8_t minimum,
                               std::uint8_t maximum) {
    if (maximum <= minimum)
        return 0.0f;
    return static_cast<float>(value - minimum) /
           static_cast<float>(maximum - minimum);
}

// K2: which table cell a program-memory read address falls on.
struct CellRef {
    int row = 0;
    int col = 0;
};

inline std::optional<CellRef> locate_cell(const CalibrationTable &table,
                                          std::uint16_t address) {
    if (address < table.start)
        return std::nullopt;
    const unsigned offset = address - table.start;
    if (offset >= table.bytes.size())
        return std::nullopt;
    return CellRef{static_cast<int>(offset) / table.cols,
                   static_cast<int>(offset) % table.cols};
}

// Index of the table that holds the most recently read address (newest first
// in `addresses`), or nullopt when none of the reads falls in a catalog table.
inline std::optional<std::size_t>
most_recent_table(const std::vector<CalibrationTable> &tables,
                  std::span<const std::uint16_t> addresses) {
    for (const std::uint16_t address : addresses)
        for (std::size_t i = 0; i < tables.size(); ++i)
            if (locate_cell(tables[i], address))
                return i;
    return std::nullopt;
}

// The cells of `table` hit by the recent reads, newest first.
inline std::vector<CellRef>
active_cells(const CalibrationTable &table,
             std::span<const std::uint16_t> addresses) {
    std::vector<CellRef> cells;
    for (const std::uint16_t address : addresses)
        if (const auto cell = locate_cell(table, address))
            cells.push_back(*cell);
    return cells;
}

namespace detail {
inline std::string first_axis_text(const Json &axes, std::size_t index) {
    if (!axes.is_array() || index >= axes.array.size())
        return "";
    const Json &axis = axes.array[index];
    if (axis.is_object() && !axis.object.empty() &&
        axis.object.front().is_string())
        return axis.object.front().string;
    return "";
}
inline std::string string_or(const Json *value, const std::string &fallback) {
    return value && value->is_string() ? value->string : fallback;
}
} // namespace detail

struct CalibrationLoadResult {
    std::vector<CalibrationTable> tables;
    std::string error;
    // K3: catalog variant name (G, A, A+, S88, S37, S36) -> ROM SHA-256.
    std::map<std::string, std::string> variant_sha256;
};

// K3: per-cell signed difference (other - base) of a table between two ROM
// images, at the table's own address. Cells outside either image read as 0.
inline std::vector<int> table_diff_cells(const CalibrationTable &table,
                                         const std::vector<std::uint8_t> &base,
                                         const std::vector<std::uint8_t> &other) {
    std::vector<int> diff(table.bytes.size(), 0);
    for (std::size_t i = 0; i < diff.size(); ++i) {
        const std::size_t address = table.start + i;
        if (address < base.size() && address < other.size())
            diff[i] = static_cast<int>(other[address]) - static_cast<int>(base[address]);
    }
    return diff;
}

inline CalibrationLoadResult calibration_error(const std::string &message) {
    CalibrationLoadResult result;
    result.error = message;
    return result;
}

inline int count_changed_cells(const std::vector<int> &diff) {
    return static_cast<int>(std::count_if(diff.begin(), diff.end(),
                                          [](int d) { return d != 0; }));
}

inline CalibrationLoadResult parse_calibration_catalog(
    const std::string &catalog_json, const std::vector<std::uint8_t> &rom) {
    const auto root = parse_json(catalog_json);
    if (!root || !root->is_object())
        return calibration_error("catalog is not valid JSON");
    const Json *tables = root->get("tables");
    if (!tables || !tables->is_array())
        return calibration_error("catalog has no tables array");
    CalibrationLoadResult result;
    if (const Json *shas = root->get("rom_sha256"); shas && shas->is_object())
        for (const Json &sha : shas->object)
            if (sha.is_string())
                result.variant_sha256[sha.key] = sha.string;
    for (const Json &entry : tables->array) {
        const Json *dims = entry.get("dimensions");
        const Json *id = entry.get("id");
        const Json *start = entry.get("start");
        if (!dims || !dims->is_array() || dims->array.size() != 2 || !id ||
            !id->is_string() || !start || !start->is_string())
            continue;
        CalibrationTable table;
        table.rows = static_cast<int>(dims->array[0].number);
        table.cols = static_cast<int>(dims->array[1].number);
        if (table.rows < 2 || table.cols < 2)
            continue; // one-dimensional curves are not heatmaps
        table.id = id->string;
        table.start = static_cast<unsigned>(
            std::strtoul(start->string.c_str(), nullptr, 16));
        const std::size_t count =
            static_cast<std::size_t>(table.rows) * static_cast<std::size_t>(table.cols);
        if (table.start + count > rom.size()) {
            result.error = "table " + table.id + " lies outside the ROM";
            continue;
        }
        if (const Json *axes = entry.get("axes")) {
            table.row_axis = detail::first_axis_text(*axes, 0);
            table.col_axis = detail::first_axis_text(*axes, 1);
        }
        if (const Json *confidence = entry.get("confidence");
            confidence && confidence->is_object()) {
            table.physical_function =
                detail::string_or(confidence->get("physical_function"), "unknown");
            for (const char *key : {"layout_and_bytes", "bytes_and_pointer",
                                    "layout", "layout_in_G", "pointer_layout",
                                    "structure_and_bytes", "bytes_all_six"})
                if (const Json *v = confidence->get(key);
                    v && v->is_string() && table.layout_confidence.empty())
                    table.layout_confidence = v->string;
        }
        if (const Json *diff = entry.get("different_bytes_vs_G");
            diff && diff->is_object())
            for (const auto &variant : diff->object)
                table.different_bytes_vs_g[variant.key] =
                    static_cast<int>(variant.number);
        table.bytes.assign(rom.begin() + table.start,
                           rom.begin() + static_cast<long>(table.start + count));
        result.tables.push_back(std::move(table));
    }
    return result;
}

inline CalibrationLoadResult load_calibration_catalog(
    const std::string &catalog_path, const std::string &rom_path) {
    std::ifstream catalog(catalog_path);
    if (!catalog)
        return calibration_error("cannot open " + catalog_path);
    std::ostringstream text;
    text << catalog.rdbuf();
    std::ifstream rom_file(rom_path, std::ios::binary);
    if (!rom_file)
        return calibration_error("cannot open " + rom_path);
    const std::vector<std::uint8_t> rom((std::istreambuf_iterator<char>(rom_file)),
                                        std::istreambuf_iterator<char>());
    return parse_calibration_catalog(text.str(), rom);
}

} // namespace lab
