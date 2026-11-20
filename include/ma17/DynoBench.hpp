#pragma once
// Crank-dyno bench around the real ROM (GOAL_DYNO_ROM phase 5). LLM-written (Claude).
// A speed-feedback brake holds one rpm point while the ROM controls injection and ignition.
// The controller sees the crank speed averaged over one firing interval (180 deg) and held until
// the next one, like a real dyno reading a tooth/encoder signal; it never sees RAM47 (quantised
// by the ECU). Everything is tick based (1 tick = 1/990000 s of emulated time), so a run is
// deterministic.
#include "engine/PlantTelemetry.hpp"
#include "engine/physics/Dynamics.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

namespace ma17 {

constexpr double bench_tick_s = 1.0 / 990000.0;

enum class DynoState { Crank, IdleSettle, Ramp, Stabilize, Measure, Accepted, Invalid };
enum class DynoInvalid {
    None, Timeout, BrakeSaturated, RpmOutOfBand, FuelCut, RevLimiter, Stall, DiagnosticFault,
    NotSteady, EnergyResidual
};

inline const char *dyno_state_name(DynoState s) {
    switch (s) {
    case DynoState::Crank: return "CRANK";
    case DynoState::IdleSettle: return "IDLE_SETTLE";
    case DynoState::Ramp: return "RAMP";
    case DynoState::Stabilize: return "STABILIZE";
    case DynoState::Measure: return "MEASURE";
    case DynoState::Accepted: return "ACCEPTED";
    case DynoState::Invalid: return "INVALID";
    }
    return "?";
}
inline const char *dyno_invalid_name(DynoInvalid r) {
    switch (r) {
    case DynoInvalid::None: return "none";
    case DynoInvalid::Timeout: return "timeout";
    case DynoInvalid::BrakeSaturated: return "brake_saturated";
    case DynoInvalid::RpmOutOfBand: return "rpm_out_of_band";
    case DynoInvalid::FuelCut: return "fuel_cut";
    case DynoInvalid::RevLimiter: return "rev_limiter";
    case DynoInvalid::Stall: return "stall";
    case DynoInvalid::DiagnosticFault: return "diagnostic_fault";
    case DynoInvalid::NotSteady: return "not_steady";
    case DynoInvalid::EnergyResidual: return "energy_residual";
    }
    return "?";
}

// Speed-feedback brake: DynoPi on the 180-degree sample-and-hold crank speed.
class DynoBrake {
  public:
    explicit DynoBrake(double omega_ref_rad_s = 0.0, engine::physics::DynoPi gains = {})
        : omega_ref_(omega_ref_rad_s), pi_(gains) {}
    void set_reference(double omega_ref_rad_s) { omega_ref_ = omega_ref_rad_s; }
    void engage(double omega_now) {
        engaged_ = true;
        if (omega_f_ <= 0.0) omega_f_ = omega_now;
    }
    bool engaged() const { return engaged_; }
    // One tick: the angle advanced since the previous call feeds the 180-degree filter.
    double step(double d_angle_rad, double dt_s) {
        acc_angle_ += d_angle_rad;
        acc_time_ += dt_s;
        if (acc_angle_ >= engine::physics::pi) {
            omega_f_ = acc_angle_ / acc_time_;
            acc_angle_ = acc_time_ = 0.0;
        }
        if (!engaged_) return 0.0;
        last_nm_ = engine::physics::dyno_brake_nm(pi_, omega_ref_, omega_f_, dt_s);
        return last_nm_;
    }
    double filtered_omega() const { return omega_f_; }
    double last_nm() const { return last_nm_; }
    double t_max() const { return pi_.t_max; }

  private:
    double omega_ref_;
    engine::physics::DynoPi pi_;
    bool engaged_ = false;
    double acc_angle_ = 0.0, acc_time_ = 0.0, omega_f_ = 0.0, last_nm_ = 0.0;
};

struct DynoBenchConfig {
    double target_rpm = 3000.0;
    double cycles = 40.0;                    // measurement window N (cycles of 4 pi)
    long long settle_end_tick = 12'000'000;  // free idle (brake off) until here
    long long ramp_ticks = 200'000;          // pedal ramp, >= 0.202 s
    long long stabilize_hold_ticks = 990'000; // filtered speed within the band for this long
    long long timeout_ticks = 30'000'000;    // from the ramp start to the end of MEASURE
    double stabilize_band = 0.02;            // +-2 % of the filtered speed
    double accept_band = 0.01;               // mean rpm within +-1 %
    double min_run_rpm = 300.0;              // below this after the crank phase: stall
    double rev_limit_rpm = 6500.0;
    bool ignore_diagnostic_fault = false; // --exp dyno_ignore_diag=1: keep measuring with F84E/F85E faults set
    long long fuel_cut_ticks = 400'000;      // no injector opening for this long: fuel cut
};

struct DynoPointResult {
    DynoState state = DynoState::Crank;
    DynoInvalid reason = DynoInvalid::None;
    engine::PlantWindowResult window{};
    double target_rpm = 0.0, mean_rpm = 0.0;
    double brake_mean_nm = 0.0, brake_peak_nm = 0.0, brake_saturated_s = 0.0;
    double kinetic_over_brake = 0.0;
    double adv_mean = 0.0, adv_min = 0.0, adv_max = 0.0, adv_std = 0.0;
    unsigned long long sparks = 0;
    double mbt_mean = 0.0, eta_mean = 0.0, xr_mean = 0.0, strength_mean = 0.0, strength_min = 0.0; // plant combustion model, per fired spark
    double spark_abs_deg[4] = {0, 0, 0, 0}; // mean absolute crank angle (0..720) per cylinder
    unsigned long long spark_cyl_count[4] = {0, 0, 0, 0};
    double inj_mass_mg = 0.0, inj_width_ms = 0.0, inj_freq_hz = 0.0, inj_duty = 0.0;
    unsigned long long inj_pulses = 0;
    int ram69_end = 0, ram69_min = 0, ram69_max = 0;
    int probe_tps1 = 0, probe_rpm47 = 0, probe_vbat61 = 0, probe_adc65 = 0, probe_xf8e8 = 0, probe_tps2 = 0, probe_6d = 0, probe_70 = 0;
    long long ramp_start_tick = 0, measure_start_tick = 0;
};

class DynoBench {
  public:
    explicit DynoBench(const DynoBenchConfig &cfg)
        : cfg_(cfg),
          brake_(cfg.target_rpm * 2.0 * engine::physics::pi / 60.0),
          window_(0.00158, 4, cfg.cycles) {}

    DynoState state() const { return state_; }
    DynoInvalid reason() const { return reason_; }
    bool done() const { return state_ == DynoState::Accepted || state_ == DynoState::Invalid; }
    const DynoBenchConfig &config() const { return cfg_; }
    const DynoBrake &brake() const { return brake_; }
    long long ramp_start_tick() const { return ramp_start_; }
    // Pedal schedule the loop must use (full open at the ramp start).
    long long pedal_step_tick() const { return cfg_.settle_end_tick; }

    // Called every tick before the crank step; returns the brake torque for this tick.
    double brake_for_tick(long long tick, double angle_rad, double omega_rad_s, double rpm,
                          bool diagnostic_fault) {
        const double d_angle = have_angle_ ? std::max(0.0, angle_rad - last_angle_) : 0.0;
        have_angle_ = true;
        last_angle_ = angle_rad;
        advance_state(tick, rpm, omega_rad_s, diagnostic_fault);
        const double nm = brake_.step(d_angle, bench_tick_s);
        brake_now_ = nm;
        if (state_ >= DynoState::Stabilize || state_ == DynoState::Ramp) {
            if (nm >= 0.999 * brake_.t_max()) saturated_ticks_++;
            peak_ = std::max(peak_, nm);
        }
        return nm;
    }

    void accumulate(long long tick, double d_angle, double omega_before, double omega_after,
                    const engine::TickTorques &t, double inertia) {
        if (state_ != DynoState::Measure) return;
        window_.set_inertia(inertia);
        window_.accumulate(tick, bench_tick_s, d_angle, omega_before, omega_after, t);
        brake_sum_ += t.brake_nm;
        ++brake_n_;
    }
    void add_mass(double air_kg, double injected_kg, double fuel_cyl_kg) {
        if (state_ == DynoState::Measure) window_.add_mass(air_kg, injected_kg, fuel_cyl_kg);
    }
    // Per-tick injector state: open when the injector stage delivered mass this tick.
    void injector_tick(long long tick, bool open, double mass_kg) {
        if (open) last_open_tick_ = tick;
        if (state_ != DynoState::Measure) { inj_prev_open_ = open; return; }
        if (open) {
            ++open_ticks_;
            inj_mass_kg_ += mass_kg;
            if (!inj_prev_open_) ++pulses_;
        }
        inj_prev_open_ = open;
    }
    void on_spark(double angle_rad, double advance_deg, unsigned cylinder, double mbt_deg = 0.0,
                  double eta = 0.0, double xr = 0.0, double strength = 1.0) {
        if (state_ != DynoState::Measure) return;
        str_sum_ += strength;
        str_min_ = advances_.empty() ? strength : std::min(str_min_, strength);
        mbt_sum_ += mbt_deg; eta_sum_ += eta; xr_sum_ += xr;
        advances_.push_back(advance_deg);
        constexpr double four_pi = 4.0 * engine::physics::pi;
        const double a = std::fmod(angle_rad, four_pi) * 180.0 / engine::physics::pi;
        if (cylinder < 4) {
            abs_sum_[cylinder] += a;
            ++abs_n_[cylinder];
        }
    }
    void on_probes(int tps1, int rpm47, int vbat, int adc65, int xf8e8, int tps2 = 0, int r6d = 0, int r70 = 0) {
        if (state_ != DynoState::Measure) return;
        p_tps1_ = tps1; p_rpm47_ = rpm47; p_vbat_ = vbat; p_adc65_ = adc65; p_xf8e8_ = xf8e8;
        p_tps2_ = tps2; p_6d_ = r6d; p_70_ = r70;
    }
    void on_ram69(int value) {
        if (state_ != DynoState::Measure) return;
        ram69_ = value;
        if (!ram_seen_) { ram_min_ = ram_max_ = value; ram_seen_ = true; }
        ram_min_ = std::min(ram_min_, value);
        ram_max_ = std::max(ram_max_, value);
    }
    // After accumulating: close MEASURE when the window is complete and judge it.
    void finish_measure_if_ready(long long tick, double rho_ref, double afr, double pci) {
        if (state_ != DynoState::Measure) return;
        if (!window_.finish_if_ready(rho_ref, afr, pci)) return;
        judge(tick);
    }

    DynoPointResult result() const {
        DynoPointResult r;
        r.state = state_;
        r.reason = reason_;
        r.window = window_.last();
        r.target_rpm = cfg_.target_rpm;
        r.mean_rpm = r.window.mean_rpm;
        r.brake_mean_nm = brake_n_ ? brake_sum_ / static_cast<double>(brake_n_) : 0.0;
        r.brake_peak_nm = peak_;
        r.brake_saturated_s = static_cast<double>(saturated_ticks_) * bench_tick_s;
        r.kinetic_over_brake = r.window.w_brake_j > 0.0
                                   ? std::abs(r.window.kinetic_j) / r.window.w_brake_j : 0.0;
        if (!advances_.empty()) {
            double s = 0, mn = advances_[0], mx = advances_[0];
            for (double a : advances_) { s += a; mn = std::min(mn, a); mx = std::max(mx, a); }
            const double m = s / static_cast<double>(advances_.size());
            double v = 0;
            for (double a : advances_) v += (a - m) * (a - m);
            r.adv_mean = m; r.adv_min = mn; r.adv_max = mx;
            r.adv_std = std::sqrt(v / static_cast<double>(advances_.size()));
        }
        r.sparks = advances_.size();
        if (!advances_.empty()) {
            const double n = static_cast<double>(advances_.size());
            r.mbt_mean = mbt_sum_ / n; r.eta_mean = eta_sum_ / n; r.xr_mean = xr_sum_ / n;
            r.strength_mean = str_sum_ / n; r.strength_min = str_min_;
        }
        for (int c = 0; c < 4; ++c) {
            r.spark_cyl_count[c] = abs_n_[c];
            r.spark_abs_deg[c] = abs_n_[c] ? abs_sum_[c] / static_cast<double>(abs_n_[c]) : 0.0;
        }
        const double t = r.window.window_s;
        r.inj_mass_mg = inj_mass_kg_ * 1e6;
        r.inj_pulses = pulses_;
        r.inj_width_ms = pulses_ ? static_cast<double>(open_ticks_) * bench_tick_s * 1e3 /
                                       static_cast<double>(pulses_) : 0.0;
        r.inj_freq_hz = t > 0.0 ? static_cast<double>(pulses_) / t : 0.0;
        r.inj_duty = t > 0.0 ? static_cast<double>(open_ticks_) * bench_tick_s / t : 0.0;
        r.probe_tps1 = p_tps1_; r.probe_rpm47 = p_rpm47_; r.probe_vbat61 = p_vbat_;
        r.probe_adc65 = p_adc65_; r.probe_tps2 = p_tps2_; r.probe_6d = p_6d_; r.probe_70 = p_70_; r.probe_xf8e8 = p_xf8e8_;
        r.ram69_end = ram69_; r.ram69_min = ram_min_; r.ram69_max = ram_max_;
        r.ramp_start_tick = ramp_start_;
        r.measure_start_tick = measure_start_;
        return r;
    }

  private:
    void invalid(DynoInvalid why) {
        if (done()) return;
        state_ = DynoState::Invalid;
        reason_ = why;
    }
    void advance_state(long long tick, double rpm, double omega, bool diag_fault) {
        if (done()) return;
        const bool running_phase = state_ >= DynoState::Ramp;
        if (running_phase) {
            if (diag_fault && !cfg_.ignore_diagnostic_fault) return invalid(DynoInvalid::DiagnosticFault);
            if (rpm < cfg_.min_run_rpm) return invalid(DynoInvalid::Stall);
            // Filtered (180 deg) speed: the instantaneous rpm swings a few percent within a cycle.
            if (brake_.filtered_omega() * 30.0 / engine::physics::pi > cfg_.rev_limit_rpm)
                return invalid(DynoInvalid::RevLimiter);
            if (tick - last_open_tick_ > cfg_.fuel_cut_ticks) return invalid(DynoInvalid::FuelCut);
            if (tick - ramp_start_ > cfg_.timeout_ticks) return invalid(DynoInvalid::Timeout);
            if (static_cast<double>(saturated_ticks_) * bench_tick_s > 0.05)
                return invalid(DynoInvalid::BrakeSaturated);
        }
        switch (state_) {
        case DynoState::Crank:
            if (rpm >= cfg_.min_run_rpm) state_ = DynoState::IdleSettle;
            else if (tick >= cfg_.settle_end_tick) invalid(DynoInvalid::Stall);
            break;
        case DynoState::IdleSettle:
            if (rpm < cfg_.min_run_rpm && tick > cfg_.settle_end_tick / 2)
                return invalid(DynoInvalid::Stall);
            if (tick >= cfg_.settle_end_tick) {
                state_ = DynoState::Ramp;
                ramp_start_ = tick;
                last_open_tick_ = tick;
                brake_.engage(omega);
            }
            break;
        case DynoState::Ramp:
            if (tick - ramp_start_ >= cfg_.ramp_ticks) {
                state_ = DynoState::Stabilize;
                in_band_since_ = -1;
            }
            break;
        case DynoState::Stabilize: {
            const double w = brake_.filtered_omega();
            const double ref = cfg_.target_rpm * 2.0 * engine::physics::pi / 60.0;
            const bool in_band = std::abs(w - ref) <= cfg_.stabilize_band * ref;
            if (!in_band) in_band_since_ = -1;
            else if (in_band_since_ < 0) in_band_since_ = tick;
            if (in_band_since_ >= 0 && tick - in_band_since_ >= cfg_.stabilize_hold_ticks) {
                state_ = DynoState::Measure;
                measure_start_ = tick;
                saturated_ticks_ = 0; // saturation is judged again over the measured window
                peak_ = 0.0;
            }
            break;
        }
        case DynoState::Measure:
        case DynoState::Accepted:
        case DynoState::Invalid: break;
        }
    }
    void judge(long long) {
        const auto &w = window_.last();
        const double band = std::abs(w.mean_rpm - cfg_.target_rpm) / cfg_.target_rpm;
        if (saturated_ticks_ > 0) return invalid(DynoInvalid::BrakeSaturated);
        if (band > cfg_.accept_band) return invalid(DynoInvalid::RpmOutOfBand);
        const double kin = w.w_brake_j > 0.0 ? std::abs(w.kinetic_j) / w.w_brake_j : 1.0;
        if (kin >= 0.01) return invalid(DynoInvalid::NotSteady);
        if (std::abs(w.energy_residual_rel) >= 0.005) return invalid(DynoInvalid::EnergyResidual);
        state_ = DynoState::Accepted;
    }

    DynoBenchConfig cfg_;
    DynoBrake brake_;
    engine::PlantWindow window_;
    DynoState state_ = DynoState::Crank;
    DynoInvalid reason_ = DynoInvalid::None;
    long long ramp_start_ = 0, measure_start_ = 0, in_band_since_ = -1, last_open_tick_ = 0;
    long long saturated_ticks_ = 0;
    double peak_ = 0.0, brake_now_ = 0.0, brake_sum_ = 0.0, last_angle_ = 0.0;
    long long brake_n_ = 0;
    bool have_angle_ = false;
    // injection
    long long open_ticks_ = 0;
    unsigned long long pulses_ = 0;
    double inj_mass_kg_ = 0.0;
    bool inj_prev_open_ = false;
    // ignition
    std::vector<double> advances_;
    int p_tps2_ = 0, p_6d_ = 0, p_70_ = 0, p_tps1_ = 0, p_rpm47_ = 0, p_vbat_ = 0, p_adc65_ = 0, p_xf8e8_ = 0;
    double str_sum_ = 0.0, str_min_ = 0.0, mbt_sum_ = 0.0, eta_sum_ = 0.0, xr_sum_ = 0.0;
    double abs_sum_[4] = {0, 0, 0, 0};
    unsigned long long abs_n_[4] = {0, 0, 0, 0};
    int ram69_ = 0, ram_min_ = 0, ram_max_ = 0;
    bool ram_seen_ = false;
};

} // namespace ma17
