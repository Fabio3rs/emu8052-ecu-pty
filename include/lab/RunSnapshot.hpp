#pragma once

#include "lab/MiniJson.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace lab {

// K4: a run snapshot is what makes two runs comparable: which ROM and which
// code produced it (SHA-256 / commit), the scenario, steady-state metrics, the
// dyno curve and the calibration table bytes. Two snapshots give signed deltas
// with units ("Delta torque +4.2 N.m @3000 rpm").

inline std::string sha256_hex(const std::vector<std::uint8_t> &data) {
    static constexpr std::array<std::uint32_t, 64> k{
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
        0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
        0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
        0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
        0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
        0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
        0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
    std::array<std::uint32_t, 8> h{0x6a09e667, 0xbb67ae85, 0x3c6ef372,
                                   0xa54ff53a, 0x510e527f, 0x9b05688c,
                                   0x1f83d9ab, 0x5be0cd19};
    std::vector<std::uint8_t> message = data;
    const std::uint64_t bit_length = static_cast<std::uint64_t>(data.size()) * 8u;
    message.push_back(0x80);
    while (message.size() % 64 != 56)
        message.push_back(0);
    for (int shift = 56; shift >= 0; shift -= 8)
        message.push_back(static_cast<std::uint8_t>(bit_length >> shift));
    const auto rotr = [](std::uint32_t x, int n) { return (x >> n) | (x << (32 - n)); };
    for (std::size_t block = 0; block < message.size(); block += 64) {
        std::array<std::uint32_t, 64> w{};
        for (std::size_t i = 0; i < 16; ++i)
            w[i] = (static_cast<std::uint32_t>(message[block + 4 * i]) << 24) |
                   (static_cast<std::uint32_t>(message[block + 4 * i + 1]) << 16) |
                   (static_cast<std::uint32_t>(message[block + 4 * i + 2]) << 8) |
                   static_cast<std::uint32_t>(message[block + 4 * i + 3]);
        for (std::size_t i = 16; i < 64; ++i) {
            const std::uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
            const std::uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }
        auto v = h;
        for (std::size_t i = 0; i < 64; ++i) {
            const std::uint32_t s1 = rotr(v[4], 6) ^ rotr(v[4], 11) ^ rotr(v[4], 25);
            const std::uint32_t ch = (v[4] & v[5]) ^ (~v[4] & v[6]);
            const std::uint32_t t1 = v[7] + s1 + ch + k[i] + w[i];
            const std::uint32_t s0 = rotr(v[0], 2) ^ rotr(v[0], 13) ^ rotr(v[0], 22);
            const std::uint32_t maj = (v[0] & v[1]) ^ (v[0] & v[2]) ^ (v[1] & v[2]);
            const std::uint32_t t2 = s0 + maj;
            v = {t1 + t2, v[0], v[1], v[2], v[3] + t1, v[4], v[5], v[6]};
        }
        for (std::size_t i = 0; i < 8; ++i)
            h[i] += v[i];
    }
    char hex[65];
    for (std::size_t i = 0; i < 8; ++i)
        std::snprintf(hex + 8 * i, 9, "%08x", h[i]);
    return hex;
}

struct SteadyMetrics {
    double rpm = std::nan("");
    double map_kpa = std::nan("");
    double lambda = std::nan("");
    double advance_deg = std::nan("");
    double ti_ms = std::nan("");
    double bsfc_g_kwh = std::nan("");
    double torque_nm = std::nan("");
};

struct CurvePoint {
    double rpm = 0.0;
    double torque_nm = 0.0;
};

struct RunSnapshot {
    std::string label;
    std::string rom_sha256;
    std::string code_sha;
    std::string scenario;
    SteadyMetrics metrics;
    std::vector<CurvePoint> curve;
    std::map<std::string, std::vector<std::uint8_t>> tables; // catalog id -> bytes
};

namespace detail {
inline std::string json_number(double value) {
    if (!std::isfinite(value))
        return "null";
    char text[40];
    std::snprintf(text, sizeof(text), "%.9g", value);
    return text;
}
inline std::string json_string(const std::string &text) {
    std::string out = "\"";
    for (const char c : text) {
        if (c == '"' || c == '\\')
            out += '\\';
        if (static_cast<unsigned char>(c) < 0x20)
            out += ' ';
        else
            out += c;
    }
    return out + "\"";
}
inline double json_double(const Json *value) {
    return value && value->type == Json::Type::Number ? value->number : std::nan("");
}
} // namespace detail

inline std::string snapshot_to_json(const RunSnapshot &s) {
    using detail::json_number;
    using detail::json_string;
    std::ostringstream out;
    out << "{\"schema\":\"sevel-run-snapshot-v1\",\"label\":" << json_string(s.label)
        << ",\"rom_sha256\":" << json_string(s.rom_sha256)
        << ",\"code_sha\":" << json_string(s.code_sha)
        << ",\"scenario\":" << json_string(s.scenario) << ",\"metrics\":{"
        << "\"rpm\":" << json_number(s.metrics.rpm)
        << ",\"map_kpa\":" << json_number(s.metrics.map_kpa)
        << ",\"lambda\":" << json_number(s.metrics.lambda)
        << ",\"advance_deg\":" << json_number(s.metrics.advance_deg)
        << ",\"ti_ms\":" << json_number(s.metrics.ti_ms)
        << ",\"bsfc_g_kwh\":" << json_number(s.metrics.bsfc_g_kwh)
        << ",\"torque_nm\":" << json_number(s.metrics.torque_nm)
        << "},\"curve\":[";
    for (std::size_t i = 0; i < s.curve.size(); ++i)
        out << (i ? "," : "") << "[" << json_number(s.curve[i].rpm) << ","
            << json_number(s.curve[i].torque_nm) << "]";
    out << "],\"tables\":{";
    bool first = true;
    for (const auto &[id, bytes] : s.tables) {
        out << (first ? "" : ",") << json_string(id) << ":\"";
        for (const std::uint8_t b : bytes) {
            char hex[3];
            std::snprintf(hex, sizeof(hex), "%02x", b);
            out << hex;
        }
        out << "\"";
        first = false;
    }
    out << "}}";
    return out.str();
}

inline std::optional<RunSnapshot> snapshot_from_json(const std::string &text) {
    const auto root = parse_json(text);
    if (!root || !root->is_object())
        return std::nullopt;
    const Json *schema = root->get("schema");
    if (!schema || !schema->is_string() || schema->string != "sevel-run-snapshot-v1")
        return std::nullopt;
    RunSnapshot s;
    const auto str = [&](const char *key) {
        const Json *v = root->get(key);
        return v && v->is_string() ? v->string : std::string();
    };
    s.label = str("label");
    s.rom_sha256 = str("rom_sha256");
    s.code_sha = str("code_sha");
    s.scenario = str("scenario");
    if (const Json *m = root->get("metrics"); m && m->is_object()) {
        s.metrics.rpm = detail::json_double(m->get("rpm"));
        s.metrics.map_kpa = detail::json_double(m->get("map_kpa"));
        s.metrics.lambda = detail::json_double(m->get("lambda"));
        s.metrics.advance_deg = detail::json_double(m->get("advance_deg"));
        s.metrics.ti_ms = detail::json_double(m->get("ti_ms"));
        s.metrics.bsfc_g_kwh = detail::json_double(m->get("bsfc_g_kwh"));
        s.metrics.torque_nm = detail::json_double(m->get("torque_nm"));
    }
    if (const Json *c = root->get("curve"); c && c->is_array())
        for (const Json &pair : c->array)
            if (pair.is_array() && pair.array.size() == 2)
                s.curve.push_back({pair.array[0].number, pair.array[1].number});
    if (const Json *t = root->get("tables"); t && t->is_object())
        for (const Json &entry : t->object) {
            std::vector<std::uint8_t> bytes;
            if (entry.is_string() && entry.string.size() % 2 == 0)
                for (std::size_t i = 0; i < entry.string.size(); i += 2)
                    bytes.push_back(static_cast<std::uint8_t>(
                        std::strtoul(entry.string.substr(i, 2).c_str(), nullptr, 16)));
            s.tables[entry.key] = std::move(bytes);
        }
    return s;
}

inline bool save_run_snapshot(const std::string &path, const RunSnapshot &s) {
    std::ofstream out(path, std::ios::trunc);
    out << snapshot_to_json(s) << "\n";
    return out.good();
}

inline std::optional<RunSnapshot> load_run_snapshot(const std::string &path) {
    std::ifstream in(path);
    if (!in)
        return std::nullopt;
    std::ostringstream text;
    text << in.rdbuf();
    return snapshot_from_json(text.str());
}

// Torque of a curve at `rpm`, linearly interpolated; nullopt outside the curve.
inline std::optional<double> curve_torque_at(const std::vector<CurvePoint> &curve,
                                             double rpm) {
    for (std::size_t i = 1; i < curve.size(); ++i)
        if (rpm >= curve[i - 1].rpm && rpm <= curve[i].rpm &&
            curve[i].rpm > curve[i - 1].rpm) {
            const double t = (rpm - curve[i - 1].rpm) / (curve[i].rpm - curve[i - 1].rpm);
            return curve[i - 1].torque_nm + t * (curve[i].torque_nm - curve[i - 1].torque_nm);
        }
    return std::nullopt;
}

// "Delta torque +4.2 N.m @3000 rpm" style lines, B relative to A. Only values
// both snapshots have are compared; the provenance difference is stated first.
inline std::vector<std::string> compare_snapshots(const RunSnapshot &a,
                                                  const RunSnapshot &b) {
    std::vector<std::string> lines;
    char text[96];
    if (a.rom_sha256 != b.rom_sha256)
        lines.push_back("ROM DIFFERS");
    if (a.code_sha != b.code_sha)
        lines.push_back("CODE DIFFERS");
    if (a.scenario != b.scenario)
        lines.push_back("SCENARIO DIFFERS");
    for (const double rpm : {3000.0}) {
        const auto ta = curve_torque_at(a.curve, rpm);
        const auto tb = curve_torque_at(b.curve, rpm);
        if (ta && tb) {
            std::snprintf(text, sizeof(text), "D TORQUE %+.1f N.M @%.0f RPM",
                          *tb - *ta, rpm);
            lines.push_back(text);
        }
    }
    const auto delta = [&](const char *name, double va, double vb, const char *unit,
                           int decimals) {
        if (!std::isfinite(va) || !std::isfinite(vb))
            return;
        char value[40];
        std::snprintf(value, sizeof(value), "%+.*f", decimals, vb - va);
        std::snprintf(text, sizeof(text), "D %s %s%s", name, value, unit);
        lines.push_back(text);
    };
    delta("ADVANCE", a.metrics.advance_deg, b.metrics.advance_deg, " DEG", 1);
    delta("LAMBDA", a.metrics.lambda, b.metrics.lambda, "", 2);
    delta("TI", a.metrics.ti_ms, b.metrics.ti_ms, " MS", 2);
    delta("BSFC", a.metrics.bsfc_g_kwh, b.metrics.bsfc_g_kwh, " G/KWH", 0);
    delta("MAP", a.metrics.map_kpa, b.metrics.map_kpa, " KPA", 1);
    int changed_tables = 0;
    for (const auto &[id, bytes_a] : a.tables) {
        const auto it = b.tables.find(id);
        if (it != b.tables.end() && it->second != bytes_a)
            ++changed_tables;
    }
    if (changed_tables > 0) {
        std::snprintf(text, sizeof(text), "%d TABLES CHANGED", changed_tables);
        lines.push_back(text);
    }
    return lines;
}

} // namespace lab
