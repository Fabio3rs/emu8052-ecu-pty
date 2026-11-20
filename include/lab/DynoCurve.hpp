#pragma once

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

namespace lab {

// Y1/Y2: data layer of the dyno view. A curve is a list of steady-state points
// (rpm, torque, power, advance, MBT, lambda) loaded from the sweep CSVs in
// docs/. Curves from the ROM sweep must carry provenance (code_sha and
// rom_sha256); a curve without it is rejected and never reaches the plot.
struct DynoPoint {
    double rpm = 0.0;
    double torque_nm = 0.0;
    double power_kw = 0.0;
    double advance_deg = std::nan("");
    double mbt_deg = std::nan("");
    double lambda = std::nan("");
};

struct DynoProvenance {
    std::string code_sha;
    std::string rom_sha256;
    std::string scenario;
    double tdc_deg = std::nan("");
};

struct DynoCurve {
    std::string label;
    std::vector<DynoPoint> points;
    std::optional<DynoProvenance> provenance; // set for ROM sweeps
    bool frozen = false;                      // a kept copy, drawn grey
};

// Freeze: keep a copy of the curve labelled `live_label` as "FROZEN <label>"
// (replacing an earlier frozen copy) so the next run can be compared with it.
// Returns false, changing nothing, when there is no such curve or it is empty.
inline bool freeze_curve(std::vector<DynoCurve> &curves,
                         const std::string &live_label) {
    const auto live = std::find_if(
        curves.begin(), curves.end(), [&](const DynoCurve &curve) {
            return !curve.frozen && curve.label == live_label;
        });
    if (live == curves.end() || live->points.empty())
        return false;
    DynoCurve copy = *live;
    copy.label = "FROZEN " + live_label;
    copy.frozen = true;
    curves.erase(std::remove_if(curves.begin(), curves.end(),
                                [&](const DynoCurve &curve) {
                                    return curve.label == copy.label;
                                }),
                 curves.end());
    curves.push_back(std::move(copy));
    return true;
}

// One CSV record, honouring double-quoted fields that contain commas.
inline std::vector<std::string> split_csv_record(const std::string &line) {
    std::vector<std::string> fields;
    std::string current;
    bool quoted = false;
    for (std::size_t i = 0; i < line.size(); ++i) {
        const char c = line[i];
        if (quoted) {
            if (c == '"' && i + 1 < line.size() && line[i + 1] == '"') {
                current += '"';
                ++i;
            } else if (c == '"') {
                quoted = false;
            } else {
                current += c;
            }
        } else if (c == '"') {
            quoted = true;
        } else if (c == ',') {
            fields.push_back(current);
            current.clear();
        } else if (c != '\r') {
            current += c;
        }
    }
    fields.push_back(current);
    return fields;
}

struct DynoLoadResult {
    std::optional<DynoCurve> curve;
    std::string error;
};

inline DynoLoadResult parse_dyno_csv(std::istream &in, const std::string &label) {
    std::string header_line;
    if (!std::getline(in, header_line))
        return {std::nullopt, "empty file"};
    const auto header = split_csv_record(header_line);
    std::map<std::string, std::size_t> column;
    for (std::size_t i = 0; i < header.size(); ++i)
        column[header[i]] = i;
    const auto find = [&](std::initializer_list<const char *> names)
        -> std::optional<std::size_t> {
        for (const char *name : names)
            if (const auto it = column.find(name); it != column.end())
                return it->second;
        return std::nullopt;
    };
    const auto rpm_col = find({"mean_rpm", "rpm"});
    const auto torque_col = find({"shaft_torque_nm", "torque_nm"});
    const auto power_col = find({"shaft_power_kw", "power_kw"});
    if (!rpm_col || !torque_col || !power_col)
        return {std::nullopt, "missing rpm/torque/power columns"};
    const auto adv_col = find({"adv_mean_deg", "spark_deg"});
    const auto mbt_col = find({"mbt_mean_deg", "mbt_deg"});
    const auto lambda_col = find({"lambda"});
    const auto state_col = find({"state"});
    const auto code_col = find({"code_sha"});
    const auto rom_col = find({"rom_sha256"});
    const auto scenario_col = find({"scenario"});
    const auto tdc_col = find({"tdc_deg"});
    const bool is_rom_sweep = state_col.has_value();

    DynoCurve curve;
    curve.label = label;
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty())
            continue;
        const auto fields = split_csv_record(line);
        const auto text = [&](std::optional<std::size_t> index) -> std::string {
            return index && *index < fields.size() ? fields[*index] : "";
        };
        const auto number = [&](std::optional<std::size_t> index) {
            const std::string value = text(index);
            if (value.empty())
                return std::nan("");
            char *end = nullptr;
            const double parsed = std::strtod(value.c_str(), &end);
            return end == value.c_str() ? std::nan("") : parsed;
        };
        if (is_rom_sweep && text(state_col) != "ACCEPTED")
            continue; // only accepted steady-state points are curve points
        DynoPoint point;
        point.rpm = number(rpm_col);
        point.torque_nm = number(torque_col);
        point.power_kw = number(power_col);
        point.advance_deg = number(adv_col);
        point.mbt_deg = number(mbt_col);
        point.lambda = number(lambda_col);
        if (!std::isfinite(point.rpm) || !std::isfinite(point.torque_nm))
            continue;
        curve.points.push_back(point);
        if (is_rom_sweep && !curve.provenance) {
            DynoProvenance provenance;
            provenance.code_sha = text(code_col);
            provenance.rom_sha256 = text(rom_col);
            provenance.scenario = text(scenario_col);
            provenance.tdc_deg = number(tdc_col);
            curve.provenance = provenance;
        }
    }
    if (curve.points.empty())
        return {std::nullopt, "no usable points"};
    if (is_rom_sweep &&
        (!curve.provenance || curve.provenance->code_sha.empty() ||
         curve.provenance->rom_sha256.empty()))
        return {std::nullopt, "ROM sweep without code_sha/rom_sha256 provenance"};
    std::sort(curve.points.begin(), curve.points.end(),
              [](const DynoPoint &a, const DynoPoint &b) { return a.rpm < b.rpm; });
    return {curve, ""};
}

inline DynoLoadResult load_dyno_csv(const std::string &path,
                                    const std::string &label) {
    std::ifstream file(path);
    if (!file)
        return {std::nullopt, "cannot open " + path};
    return parse_dyno_csv(file, label);
}

inline const DynoPoint *peak_torque(const DynoCurve &curve) {
    const auto it = std::max_element(
        curve.points.begin(), curve.points.end(),
        [](const DynoPoint &a, const DynoPoint &b) {
            return a.torque_nm < b.torque_nm;
        });
    return it == curve.points.end() ? nullptr : &*it;
}

// The tooltip of a curve point: "3001 rpm  118.0 N.m  37.1 kW".
inline std::string dyno_point_text(const DynoPoint &point) {
    char text[64];
    std::snprintf(text, sizeof(text), "%.0f rpm  %.1f N.m  %.1f kW", point.rpm,
                  point.torque_nm, point.power_kw);
    return text;
}

} // namespace lab
