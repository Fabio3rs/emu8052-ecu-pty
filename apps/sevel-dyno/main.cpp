// sevel-dyno: speed-controlled engine-dyno sweep of the SEVEL plant, writing a
// CSV that compares the simulator with the expected (approximate) curves.
// Plant under test = the real engine::IntakeFuel + engine::Combustion + crank
// friction constants (no ROM): lambda and spark are set by the tool, so the
// result is the plant's capability ceiling. Time is simulated time only.
// GOAL_SEVEL_FISICA fase 3. LLM-written (Claude).
#include "engine/Combustion.hpp"
#include "engine/CrankDynamics.hpp"
#include "engine/FuelBlend.hpp"
#include "engine/IntakeFuel.hpp"
#include "engine/physics/Combustion.hpp"
#include "engine/physics/Gas.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

namespace {
constexpr double pi = 3.14159265358979323846;

struct Options {
    int ethanol_percent = 22;
    double rpm_min = 1000.0, rpm_max = 6500.0, rpm_step = 250.0;
    double throttle_rad = 1.5707; // plant limit is pi/2
    double leak_mm2 = 1.0;        // IntakeFuelParameters default
    double lambda = 1.0;
    double spark_btdc_deg = 11.5; // plant optimum (Combustion::spark)
    double ambient_kpa = 100.0, ambient_c = 20.0;
    double settle_s = 2.0;
    int measure_cycles = 40;      // >= 20 cycles (F-48)
    bool legacy = false;          // old constant-VE / 0.24-efficiency plant
    bool mbt = true;              // spark follows the plant MBT (else fixed)
    std::vector<std::pair<std::string, double>> overrides; // --set key=value
    std::string out;
    std::string preset;  // "acceptance": E22 + E0 full-load sweeps in one call
    std::string out_dir; // with --preset: where the CSVs go
};

// Expected curve: CEE power read from PhotosECU/curva_potencia.png (reading
// error of a few percent) times 1.1 to represent the 82 cv Brazilian tune.
// Goal section 8.3. Replace by the redigitised CSV when it exists.
double expected_power_kw(double rpm) {
    static const double n[] = {1000, 1500, 3000, 4000, 5000, 6000, 6400};
    static const double p[] = {10.0, 16.0, 40.0, 48.0, 52.0, 55.0, 52.0};
    if (rpm <= n[0]) return p[0] * 1.1 * rpm / n[0];
    for (int i = 1; i < 7; ++i)
        if (rpm <= n[i])
            return 1.1 * (p[i - 1] + (p[i] - p[i - 1]) * (rpm - n[i - 1]) /
                                         (n[i] - n[i - 1]));
    return 1.1 * p[6];
}

struct Row {
    double rpm, torque, kw, cv, map_kpa, ve, lambda, bsfc, bmep_bar, imep_bar,
        fmep_nm, pump_nm, ind_nm, air_g_s, fuel_g_s, air_mg_cyl, adv, mbt, eta_i, xr;
};

Row run_point(const Options &o, double rpm) {
    engine::IntakeFuelParameters ip;
    ip.ambient_pressure_pa = o.ambient_kpa * 1000.0;
    ip.ambient_temperature_c = o.ambient_c;
    ip.throttle_leak_area_m2 = o.leak_mm2 * 1e-6;
    ip.ve_map = !o.legacy;
    if (!o.legacy) ip.exhaust_back_pressure_k = 3.78e6; // calibrado: 15 kPa a 63 g/s (F-41)
    engine::CombustionParameters cparams;
    for (const auto &[k, v] : o.overrides) {
        if (k == "eta_max") ip.ve_curve.eta_max = v;
        else if (k == "cb") ip.ve_curve.cb = v;
        else if (k == "nb") ip.ve_curve.nb = v;
        else if (k == "z0") ip.ve_curve.z0 = v;
        else if (k == "kz") ip.ve_curve.kz = v;
        else if (k == "ci") ip.ve_curve.ci = v;
        else if (k == "wot_map_pa") ip.wot_manifold_pressure_pa = v;
        else if (k == "eta_ref") cparams.eta_ref = v;
        else if (k == "burn0") cparams.burn_duration0_deg = v;
        else if (k == "burn_kr") cparams.burn_residual_gain = v;
        else { std::fprintf(stderr, "unknown --set key %s\n", k.c_str()); std::exit(2); }
    }
    engine::IntakeFuel intake{ip};
    const auto fuel = engine::FuelBlend::from_ethanol_percent(o.ethanol_percent);
    cparams.physical_efficiency = !o.legacy;
    engine::Combustion comb{cparams, fuel};
    const engine::CrankParameters cp;
    const double afr = fuel.stoichiometric_air_fuel_ratio();
    const double omega = rpm * 2.0 * pi / 60.0;
    const double dt = 1e-4;
    const double tdc = comb.tdc_phase_rad();
    double adv = o.spark_btdc_deg * pi / 180.0;
    if (!o.legacy && o.mbt) adv = 20.0 * pi / 180.0; // refined from the plant MBT
    const double temp_c = o.ambient_c;

    double theta = 0.0;
    long long next_k = 0;      // next half-revolution index to fire
    double last_air_cyl = 0.0;
    double w_ind = 0.0, w_pump = 0.0, w_fric = 0.0;
    double air0 = 0, fuel0 = 0, inj0 = 0, burned0 = 0, dtheta = 0, mapsum = 0;
    long long nsteps = 0;
    const double total_t = o.settle_s;
    const double settle_theta = omega * total_t;
    const double meas_theta = o.measure_cycles * 4.0 * pi;
    bool measuring = false;
    double theta_start = 0.0;

    while (theta < settle_theta + meas_theta) {
        if (!measuring && theta >= settle_theta) {
            measuring = true;
            theta_start = theta;
            air0 = intake.air_delivered_total_kg();
            fuel0 = intake.fuel_delivered_total_kg();
            inj0 = intake.injected_total_kg();
            burned0 = comb.burned_fuel_kg();
        }
        const double inj = last_air_cyl / (afr * o.lambda);
        const auto step =
            intake.step(dt, rpm, o.throttle_rad, temp_c, 90.0, inj);
        last_air_cyl = step.air_to_cylinders_kg;
        comb.admit(step, theta);
        comb.set_operating_point(rpm, intake.pressure_pa(), intake.exhaust_pressure_pa());
        const double new_theta = theta + omega * dt;
        // Spark when the crank passes (TDC + k*pi - advance).
        for (;;) {
            const double fire = tdc + static_cast<double>(next_k) * pi - adv;
            if (fire >= new_theta) break;
            if (fire >= theta) {
                const unsigned channel = static_cast<unsigned>(next_k % 2);
                comb.spark(fire, channel, 1.0);
                if (!o.legacy && o.mbt && comb.last_mbt_deg() > 0.0)
                    adv = std::clamp(comb.last_mbt_deg(), 0.0, 40.0) * pi / 180.0;
            }
            ++next_k;
        }
        const double tau = comb.torque_nm(theta);
        const double pump = intake.pumping_torque_nm();
        const double fric = cp.running_friction_nm +
                            cp.viscous_friction_nm_per_rad_s * omega;
        if (measuring) {
            w_ind += tau * omega * dt;
            w_pump += pump * omega * dt;
            w_fric += fric * omega * dt;
            mapsum += intake.pressure_pa();
            ++nsteps;
        }
        theta = new_theta;
    }
    dtheta = theta - theta_start;
    constexpr double vd = 0.001580;
    const double t_ind = w_ind / dtheta, t_pump = w_pump / dtheta,
                 t_fric = w_fric / dtheta;
    const double t_b = t_ind - t_pump - t_fric;
    const double kw = engine::physics::power_kw(t_b, rpm);
    const double dt_win = dtheta / omega;
    const double air = intake.air_delivered_total_kg() - air0;
    const double fl = intake.fuel_delivered_total_kg() - fuel0;
    const double inj_win = intake.injected_total_kg() - inj0;
    const double rho_ref = ip.ambient_pressure_pa / (287.05 * (o.ambient_c + 273.15));
    Row r{};
    r.rpm = rpm;
    r.torque = t_b;
    r.kw = kw;
    r.cv = engine::physics::kw_to_cv(kw);
    r.map_kpa = mapsum / static_cast<double>(nsteps) / 1000.0;
    r.ve = air / (rho_ref * vd * dtheta / (4.0 * pi));
    r.lambda = fl > 0 ? air / (fl * afr) : 0.0;
    r.bsfc = kw > 0 ? (inj_win / dt_win) * 3.6e9 / kw : 0.0;
    r.bmep_bar = engine::physics::bmep_pa(t_b, vd) / 1e5;
    r.imep_bar = engine::physics::bmep_pa(t_ind, vd) / 1e5;
    r.fmep_nm = t_fric;
    r.pump_nm = t_pump;
    r.ind_nm = t_ind;
    r.air_g_s = air / dt_win * 1e3;
    r.fuel_g_s = inj_win / dt_win * 1e3;
    r.air_mg_cyl = air / (4.0 * dtheta / (4.0 * pi)) * 1e6;
    r.adv = comb.last_spark_advance_deg();
    r.mbt = comb.last_mbt_deg();
    r.eta_i = comb.last_spark_efficiency();
    r.xr = comb.last_residual_fraction();
    (void)burned0;
    return r;
}
struct Summary { double best_p, best_p_n, best_t, best_t_n, max_shape_err; };

Summary sweep(const Options &o) {
    std::ofstream file;
    if (!o.out.empty()) file.open(o.out);
    std::ostream &out = o.out.empty() ? std::cout : file;
    char line[512];
    out << "rpm,torque_nm,power_kw,power_cv,map_kpa,ve_ambient,lambda,bsfc_g_kwh,"
           "bmep_bar,imep_bar,indicated_nm,friction_nm,pumping_nm,air_g_s,fuel_g_s,"
           "air_mg_cyl_cycle,spark_deg,mbt_deg,eta_i,residual,expected_power_kw,expected_torque_nm,power_error_pct\n";
    double best_p = 0, best_p_n = 0, best_t = 0, best_t_n = 0, max_err = 0;
    for (double n = o.rpm_min; n <= o.rpm_max + 1e-9; n += o.rpm_step) {
        const Row r = run_point(o, n);
        const double ep = expected_power_kw(n);
        const double et = ep * 9549.3 / n;
        std::snprintf(line, sizeof line,
                      "%.0f,%.2f,%.2f,%.1f,%.1f,%.4f,%.3f,%.0f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.3f,%.1f,%.1f,%.1f,%.3f,%.3f,%.2f,%.1f,%.1f\n",
                      r.rpm, r.torque, r.kw, r.cv, r.map_kpa, r.ve, r.lambda, r.bsfc,
                      r.bmep_bar, r.imep_bar, r.ind_nm, r.fmep_nm, r.pump_nm,
                      r.air_g_s, r.fuel_g_s, r.air_mg_cyl, r.adv, r.mbt, r.eta_i, r.xr, ep, et,
                      100.0 * (r.kw - ep) / ep);
        out << line;
        if (n >= 2000.0 && n <= 6000.0) max_err = std::max(max_err, std::fabs(100.0 * (r.kw - ep) / ep));
        if (r.kw > best_p) { best_p = r.kw; best_p_n = n; }
        if (r.torque > best_t) { best_t = r.torque; best_t_n = n; }
    }
    std::fprintf(stderr,
                 "[DYNO] E%d peak power %.1f kW (%.0f cv) @ %.0f rpm  (target 60.3 kW / 82 cv @ 5750-6000)\n"
                 "[DYNO] peak torque %.1f N.m @ %.0f rpm  (target 125-133 @ 2750-3250)\n",
                 o.ethanol_percent, best_p, engine::physics::kw_to_cv(best_p), best_p_n,
                 best_t, best_t_n);
    return {best_p, best_p_n, best_t, best_t_n, max_err};
}
} // namespace

int main(int argc, char **argv) {
    Options o;
    for (int i = 1; i < argc; ++i) {
        auto need = [&](const char *name) -> const char * {
            if (std::strcmp(argv[i], name) != 0) return nullptr;
            if (i + 1 >= argc) { std::fprintf(stderr, "missing value for %s\n", name); std::exit(2); }
            return argv[++i];
        };
        const char *v;
        if ((v = need("--ethanol"))) o.ethanol_percent = std::atoi(v);
        else if ((v = need("--rpm-min"))) o.rpm_min = std::atof(v);
        else if ((v = need("--rpm-max"))) o.rpm_max = std::atof(v);
        else if ((v = need("--rpm-step"))) o.rpm_step = std::atof(v);
        else if ((v = need("--throttle-deg"))) o.throttle_rad = std::min(1.5707, std::atof(v) * pi / 180.0);
        else if ((v = need("--throttle-leak-mm2"))) o.leak_mm2 = std::atof(v);
        else if ((v = need("--lambda"))) o.lambda = std::atof(v);
        else if ((v = need("--spark-btdc-deg"))) o.spark_btdc_deg = std::atof(v);
        else if ((v = need("--ambient-kpa"))) o.ambient_kpa = std::atof(v);
        else if ((v = need("--ambient-c"))) o.ambient_c = std::atof(v);
        else if ((v = need("--cycles"))) o.measure_cycles = std::atoi(v);
        else if ((v = need("--out"))) o.out = v;
        else if ((v = need("--preset"))) o.preset = v;
        else if ((v = need("--out-dir"))) o.out_dir = v;
        else if ((v = need("--set"))) {
            const std::string kv = v;
            const auto eq = kv.find('=');
            if (eq == std::string::npos) { std::fprintf(stderr, "--set key=value\n"); return 2; }
            o.overrides.emplace_back(kv.substr(0, eq), std::atof(kv.c_str() + eq + 1));
        }
        else if (std::strcmp(argv[i], "--legacy-plant") == 0) o.legacy = true;
        else if (std::strcmp(argv[i], "--fixed-spark") == 0) o.mbt = false;
        else { std::fprintf(stderr, "unknown option %s\n", argv[i]); return 2; }
    }
    if (o.rpm_step <= 0 || o.rpm_max < o.rpm_min || o.measure_cycles < 20) {
        std::fprintf(stderr, "invalid sweep (cycles must be >= 20)\n");
        return 2;
    }
    if (!o.preset.empty()) {
        if (o.preset != "acceptance") {
            std::fprintf(stderr, "unknown preset %s (known: acceptance)\n", o.preset.c_str());
            return 2;
        }
        // Goal section 8: full-load sweeps for E22 and E0 in one call.
        const std::string dir = o.out_dir.empty() ? "." : o.out_dir;
        std::ofstream summary(dir + "/dyno_summary.csv");
        summary << "ethanol_percent,peak_power_kw,peak_power_cv,peak_power_rpm,peak_torque_nm,"
                   "peak_torque_rpm,max_abs_shape_error_pct_2000_6000\n";
        for (int e : {22, 0}) {
            Options po = o;
            po.ethanol_percent = e;
            po.rpm_min = 1000.0; po.rpm_max = 6500.0; po.rpm_step = 250.0;
            po.out = dir + "/dyno_wot_e" + std::to_string(e) + ".csv";
            const Summary r = sweep(po);
            char line[256];
            std::snprintf(line, sizeof line, "%d,%.2f,%.1f,%.0f,%.2f,%.0f,%.1f\n", e,
                          r.best_p, engine::physics::kw_to_cv(r.best_p), r.best_p_n,
                          r.best_t, r.best_t_n, r.max_shape_err);
            summary << line;
        }
        return 0;
    }
    sweep(o);
    return 0;
}
