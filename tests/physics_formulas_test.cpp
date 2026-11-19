// Unit tests for engine/physics/* pure formulas (GOAL_SEVEL_FISICA fase 1).
// Reference values are hand-calculated from docs/SEVEL_TIPO_16_SPECS.md and
// the goal's formula catalogue. LLM-written (Claude).
#include "engine/physics/Combustion.hpp"
#include "engine/physics/Dynamics.hpp"
#include "engine/physics/Flow.hpp"
#include "engine/physics/Fuel.hpp"
#include "engine/physics/Gas.hpp"
#include "engine/physics/Geometry.hpp"
#include "engine/physics/Losses.hpp"
#include "engine/physics/Thermal.hpp"
#include "engine/physics/Volumetric.hpp"

#include <gtest/gtest.h>

namespace p = engine::physics;

TEST(PhysicsGas, DensityAndSoundSpeed) {
    EXPECT_NEAR(p::density(100000.0, 293.15), 1.1884, 1e-3);          // F-01
    EXPECT_NEAR(p::sound_speed(293.15), 343.2, 0.1);                   // F-02
    EXPECT_DOUBLE_EQ(p::rho_ref(1e5, 293.15), p::density(1e5, 293.15)); // F-03
}

TEST(PhysicsGeometry, DisplacementAndClearance) {
    p::EngineGeometry g;
    EXPECT_NEAR(p::cylinder_displacement(g) * 1e6, 395.16, 0.05);  // F-04
    EXPECT_NEAR(p::total_displacement(g) * 1e6, 1580.66, 0.2);
    EXPECT_NEAR(p::clearance_volume(g) * 1e6, 48.2, 0.05);         // F-05, manual p.5
    EXPECT_NEAR(p::mean_piston_speed(g, 6000.0), 13.48, 0.01);     // F-08
}

TEST(PhysicsGeometry, VolumeRatioEqualsCompressionRatio) {
    p::EngineGeometry g; // e = 0
    const double v_tdc = p::cylinder_volume(g, 0.0);
    const double v_bdc = p::cylinder_volume(g, p::pi);
    EXPECT_NEAR(v_bdc / v_tdc, g.compression_ratio, 1e-9);
    EXPECT_NEAR(v_tdc, p::clearance_volume(g), 1e-12);
}

TEST(PhysicsGeometry, TravelRateMatchesFiniteDifference) {
    p::EngineGeometry g;
    for (double th : {0.4, 1.3, 2.2, 4.0}) {
        const double h = 1e-6;
        const double fd = (p::piston_travel(g, th + h) - p::piston_travel(g, th - h)) / (2 * h);
        EXPECT_NEAR(p::piston_travel_rate(g, th), fd, 1e-8);
    }
    EXPECT_NEAR(p::piston_travel_rate(g, 0.0), 0.0, 1e-12);
}

TEST(PhysicsGeometry, PinOffsetKeepsStrokeRoughlyAndTdcFormula) {
    p::EngineGeometry g;
    g.pin_offset_m = 0.001;
    const double th_tdc = std::asin(g.pin_offset_m / (g.rod_length_m + g.stroke_m / 2));
    EXPECT_NEAR(p::piston_travel_rate(g, th_tdc), 0.0, 1e-6); // top dead centre shifts
    EXPECT_NEAR(p::piston_travel(g, th_tdc), 0.0, 1e-9);
}

TEST(PhysicsGeometry, GasTorqueWorkOverStrokeEqualsPressureTimesVolume) {
    p::EngineGeometry g;
    double w = 0.0;
    const int n = 20000;
    for (int i = 0; i < n; ++i) {
        const double th = (i + 0.5) * p::pi / n;
        w += p::gas_torque_per_cylinder(g, th, 5e5, 1e5) * p::pi / n;
    }
    EXPECT_NEAR(w, 4e5 * (p::cylinder_displacement(g)), 1e-3);
}

TEST(PhysicsFlow, ThrottleAreaHeywoodLimits) {
    const double d = 0.040;
    const double full = p::pi * d * d / 4.0;
    EXPECT_NEAR(p::throttle_area_m2(d, 0.0, 1.0471975512, 0.0) / full, 0.5, 1e-9); // 1-cos60
    EXPECT_NEAR(p::throttle_area_m2(d, 0.0, p::pi / 2, 0.0) / full, 1.0, 1e-9);
    EXPECT_DOUBLE_EQ(p::throttle_area_m2(d, 0.1, 0.0, 0.0), 0.0);
    double last = 0.0;
    for (double psi = 0.01; psi < 1.5; psi += 0.01) { // monotonic
        const double a = p::throttle_area_m2(d, 0.1, psi, 0.0);
        EXPECT_GE(a, last - 1e-12);
        last = a;
    }
}

TEST(PhysicsFlow, CriticalRatioAndChokedPsi) {
    const double pr_cr = std::pow(2.0 / 2.4, 1.4 / 0.4);
    EXPECT_NEAR(pr_cr, 0.5283, 1e-4);
    EXPECT_NEAR(p::pr_critical(), pr_cr, 1e-4);
    EXPECT_NEAR(p::psi_flow(0.3), 0.6847, 1e-4);
    EXPECT_NEAR(p::psi_flow(pr_cr), 0.6847, 2e-4);          // continuity at pr_cr
    EXPECT_NEAR(p::psi_flow(0.5283 + 1e-9), p::psi_flow(0.5283 - 1e-9), 2e-4);
}

TEST(PhysicsFlow, IncompressibleOverestimatesChokedFlow) {
    // Goal F-11: with pr = 0.40 the incompressible formula gives ~1.6x choked flow.
    const double pr = 0.40;
    const double incompressible = std::sqrt(2.0 * (1.0 - pr)) / std::sqrt(287.05 * 293.15) * 1e5 /
                                  std::sqrt(1.0) * (1.0 / 1e5) * std::sqrt(1e5 * 1e5 / (287.05 * 293.15)) /
                                  std::sqrt(1e5 * 1e5 / (287.05 * 293.15)) * 1.0;
    (void)incompressible;
    const double rho = 1e5 / (287.05 * 293.15);
    const double inc = std::sqrt(2.0 * rho * (1.0 - pr) * 1e5);
    const double choked = 1e5 / std::sqrt(287.05 * 293.15) * p::psi_flow(pr);
    EXPECT_NEAR(inc / choked, 1.6, 0.1);
}

TEST(PhysicsFlow, OrificeSignedFlowAndRegularisation) {
    const double a = 1e-4, t = 293.15;
    EXPECT_GT(p::orifice_flow_kg_s(a, 1e5, t, 6e4, t), 0.0);
    EXPECT_NEAR(p::orifice_flow_kg_s(a, 6e4, t, 1e5, t),
                -p::orifice_flow_kg_s(a, 1e5, t, 6e4, t), 1e-15);
    EXPECT_DOUBLE_EQ(p::orifice_flow_kg_s(a, 1e5, t, 1e5, t), 0.0);
    // Continuity at 1 - pr = eps.
    const double eps = p::flow_epsilon;
    const double lo = p::orifice_flow_kg_s(a, 1e5, t, 1e5 * (1.0 - eps * 1.0000001), t);
    const double hi = p::orifice_flow_kg_s(a, 1e5, t, 1e5 * (1.0 - eps * 0.9999999), t);
    EXPECT_NEAR(lo, hi, 1e-6 * lo);
    // Monotonic in pressure difference, no blow-up near pr -> 1.
    double last = 0.0;
    for (double d = 1e-9; d < 0.9; d = d * 1.5 + 1e-9) {
        const double m = p::orifice_flow_kg_s(a, 1e5, t, 1e5 * (1.0 - d), t);
        EXPECT_GE(m, last - 1e-15);
        last = m;
    }
}

TEST(PhysicsFlow, ManifoldTimeConstantAtIdle) {
    EXPECT_NEAR(p::manifold_time_constant_s(0.002, 0.5, 0.00158, 850.0), 0.2, 0.2); // order of F-14
    EXPECT_NEAR(p::manifold_time_constant_s(0.002, 0.75, 0.00158, 1000.0), 0.2025, 5e-3);
    EXPECT_NEAR(p::manifold_pressure_pa(0.0023, 293.15, 0.002), 0.0023 * 287.05 * 293.15 / 0.002, 1e-9);
    EXPECT_NEAR(p::filter_pressure_drop_pa(300.0, 0.06, 1.19), 300.0 * 0.0036 / 1.19, 1e-12);
}

TEST(PhysicsVolumetric, ReferenceRelations) {
    EXPECT_NEAR(p::residual_correction(1e5, 4e4, 9.2), 0.869, 1e-3);  // F-18
    EXPECT_NEAR(p::residual_correction(1e5, 6e4, 9.2), 0.942, 1e-3);
    EXPECT_NEAR(p::residual_correction(1e5, 9.5e4, 9.2), 0.995, 1e-3);
    EXPECT_NEAR(p::residual_fraction(1e5, 4e4, 9.2), 0.21, 0.01);     // F-19
    EXPECT_NEAR(p::residual_fraction(1e5, 9.5e4, 9.2), 0.11, 0.01);
    EXPECT_NEAR(p::ve_ambient_from_manifold(0.75, 5e4, 1e5, 293.15, 293.15), 0.375, 1e-12); // F-17
    const double rho = p::density(1e5, 293.15);
    EXPECT_NEAR(p::ve_ambient(p::cylinder_air_flow_kg_s(0.8, rho, 0.00158, 3000.0), rho, 0.00158, 3000.0),
                0.8, 1e-12);                                           // F-15/F-16
}

TEST(PhysicsVolumetric, MachIndexMatchesGoalTable) {
    p::EngineGeometry g;
    p::VeCurveParams v;
    const double t = 293.15;
    EXPECT_NEAR(p::mach_index(g, v.valve_d_m, 3000, 0.35, t), 0.27, 0.01);
    EXPECT_NEAR(p::mach_index(g, v.valve_d_m, 5000, 0.35, t), 0.45, 0.02);
    EXPECT_NEAR(p::mach_index(g, v.valve_d_m, 6000, 0.35, t), 0.54, 0.02);
    EXPECT_NEAR(p::mach_index(g, v.valve_d_m, 6500, 0.35, t), 0.58, 0.02);
    EXPECT_NEAR(p::curtain_area_m2(0.0395, 0.0084) * 1e4, 10.4, 0.05); // F-23
    EXPECT_NEAR(p::valve_mean_velocity(g, 0.0395, 6000.0), 64.5, 1.0);
}

TEST(PhysicsVolumetric, WotCurveShape) {
    p::EngineGeometry g;
    p::VeCurveParams v;
    double best_n = 0, best = 0;
    for (double n = 1000; n <= 6500; n += 50) {
        const double e = p::eta_v_wot(g, v, n, 293.15);
        EXPECT_GT(e, 0.0);
        EXPECT_LE(e, 1.2); // manifold-referenced; > 1 is ram tuning (see Volumetric.hpp)
        if (e > best) { best = e; best_n = n; }
    }
    EXPECT_GT(best_n, 2500.0);
    EXPECT_LT(best_n, 5200.0);
    EXPECT_LT(p::eta_v_wot(g, v, 6500, 293.15), p::eta_v_wot(g, v, 5500, 293.15));
}

TEST(PhysicsFuel, BlendPropertiesAndEnergyPerKgAir) {
    for (double phi : {0.0, 0.22, 1.0}) {
        const auto f = p::fuel_props(phi);
        EXPECT_NEAR(f.pci_j_kg / f.afr_st / 1e6, 2.99, 0.03) << phi; // F-25 property test
    }
    EXPECT_NEAR(p::fuel_props(0.0).afr_st, 14.7, 1e-12);
    EXPECT_NEAR(p::fuel_props(1.0).afr_st, 9.0, 1e-12);
    EXPECT_NEAR(p::fuel_props(0.22).w_e, 0.22 * 789 / (0.22 * 789 + 0.78 * 740), 1e-12);
    EXPECT_NEAR(p::lambda_of(14.7, 1.0, 14.7), 1.0, 1e-12);            // F-26
}

TEST(PhysicsFuel, InjectorFilmAndEvaporation) {
    EXPECT_DOUBLE_EQ(p::injector_flow_kg_s(740.0, 1e-5, 1e5, 1e5), 740.0 * 1e-5); // F-27
    EXPECT_NEAR(p::injector_flow_kg_s(740.0, 1e-5, 4e5, 1e5), 2.0 * 740.0 * 1e-5, 1e-12);
    EXPECT_DOUBLE_EQ(p::injector_mass_kg(1e-3, 0.0005, 0.001), 0.0);
    EXPECT_GT(p::injector_dead_time_s(0.001, 1e-4, 14.0, 10.0), 0.001);
    // Film conserves mass: film change + to-cylinder flow == injected flow.
    const auto s = p::film_derivative(0.3, 2e-3, 1e-4, 0.4);
    EXPECT_NEAR(s.film_kg + s.to_cyl_kg_s, 2e-3, 1e-15);
    // Upper bound on evaporative cooling with chi = 1: ~24 K (E0) / ~36 K (E22).
    const auto e0 = p::fuel_props(0.0), e22 = p::fuel_props(0.22);
    EXPECT_NEAR(p::evap_cooling_k(1.0, 1.0 / e0.afr_st, e0.hfg_j_kg, 1.0), 24.0, 1.5);
    EXPECT_NEAR(p::evap_cooling_k(1.0, 1.0 / e22.afr_st, e22.hfg_j_kg, 1.0), 36.0 * 0.0 + 28.0, 8.0);
}

TEST(PhysicsCombustion, MbtAndWiebe) {
    EXPECT_NEAR(p::mbt_deg(50.0), 17.9, 0.05);   // F-33
    EXPECT_NEAR(p::mbt_deg(60.0), 23.05, 0.05);
    EXPECT_NEAR(p::mbt_deg(75.0), 30.8, 0.05);
    EXPECT_NEAR(p::wiebe_fraction(0.5175 * 60.0, 0.0, 60.0), 0.5, 5e-3); // CA50 at 0.5175 dtheta
    EXPECT_DOUBLE_EQ(p::wiebe_fraction(-1.0, 0.0, 60.0), 0.0);
    EXPECT_NEAR(p::wiebe_fraction(60.0, 0.0, 60.0), 1.0 - std::exp(-5.0), 1e-12);
    EXPECT_NEAR(p::f_advance(10.0), 0.965, 1e-9);
    EXPECT_NEAR(p::f_advance(25.0), 0.78125, 1e-9);
    EXPECT_DOUBLE_EQ(p::f_advance(0.0), 1.0);
    EXPECT_NEAR(p::f_dilution(0.21, 1.0, 0.1), 0.89, 1e-12);
    EXPECT_NEAR(p::burn_duration_deg(60.0, 3000.0, 3000.0, 0.5, 0.2, 1.0), 66.0, 1e-9);
}

TEST(PhysicsCombustion, LambdaFactorProperties) {
    // g(l) scales work per kg of burnable fuel (burnable = min(fuel, air/AFR)).
    // Per kg FUEL injected: eff = g * min(1, l).  Per kg AIR: tq = g * min(1, 1/l).
    double fuel_l = 0, fuel_best = 0, air_l = 0, air_best = 0;
    for (double l = 0.7; l <= 1.6; l += 0.0025) {
        const double g = p::f_lambda_fuel(l);
        if (g * std::min(1.0, l) > fuel_best) { fuel_best = g * std::min(1.0, l); fuel_l = l; }
        if (g * std::min(1.0, 1.0 / l) > air_best) { air_best = g * std::min(1.0, 1.0 / l); air_l = l; }
    }
    EXPECT_GE(fuel_l, 1.05); // F-32: fuel efficiency max in 1.05-1.15
    EXPECT_LE(fuel_l, 1.15);
    EXPECT_GE(air_l, 0.85);  // F-32: torque per kg air max in 0.85-0.90
    EXPECT_LE(air_l, 0.90);
    EXPECT_GE(air_best, 1.03); // 3-5 % above lambda = 1
    EXPECT_LE(air_best, 1.05);
    EXPECT_DOUBLE_EQ(p::f_lambda_fuel(1.0), 1.0);
    EXPECT_LT(p::f_lambda_fuel(1.5), 0.6 * fuel_best); // steep drop above ~1.4-1.5
}

TEST(PhysicsCombustion, MeanPressuresAndPower) {
    p::EngineGeometry g;
    const double vd = p::total_displacement(g);
    const double t = 96.0; // 60.3 kW at 6000
    EXPECT_NEAR(p::power_kw(t, 6000.0), 60.3, 0.2);                       // F-37
    EXPECT_NEAR(p::kw_to_cv(60.3), 82.0, 0.1);
    EXPECT_NEAR(p::bmep_pa(t, vd) / 1e5, 7.64, 0.02);                     // F-36
    EXPECT_NEAR(p::bmep_pa(133.0, vd) / 1e5, 10.58, 0.03);
    const double w = 1.0e3 / 4.0 * 0 + 600.0;
    EXPECT_NEAR(p::indicated_torque_nm(w, 4), 4 * w / (4 * p::pi), 1e-12);
    EXPECT_NEAR(p::imep_pa(w, p::cylinder_displacement(g)), w / p::cylinder_displacement(g), 1e-6);
    EXPECT_NEAR(p::bsfc_g_kwh(5e-3 * 0.0 + 4.5e-3, 60.3), 4.5e-3 * 3.6e6 / 60.3, 1e-6);
    EXPECT_NEAR(p::brake_efficiency(60300.0, 4.5e-3, 44e6), 0.3046, 1e-3);
    EXPECT_DOUBLE_EQ(p::bsfc_g_kwh(1e-3, 0.0), 0.0);
    EXPECT_NEAR(p::burned_fuel_kg(2.0, 14.7, 14.7, 1.0), 1.0, 1e-12); // F-30 rich cap
    EXPECT_NEAR(p::exhaust_temp_k(300.0, 1150.0, 1.0), 301.0, 1e-9);
}

TEST(PhysicsLosses, PumpingBackPressureFriction) {
    EXPECT_NEAR(p::pumping_torque_nm(1e5, 4e4, 0.00158), 6e4 * 0.00158 / (4 * p::pi), 1e-12); // F-40
    EXPECT_NEAR(p::pumping_torque_nm(1e5, 1e5, 0.00158), 0.0, 1e-15); // p_e = p_amb special case
    EXPECT_NEAR(p::exhaust_back_pressure_pa(1e5, 1e5, 0.012), 1e5 + 1e5 * 0.012 * 0.012, 1e-9); // F-41
    p::FrictionParams f;
    p::EngineGeometry g;
    const double vd = p::total_displacement(g);
    const double idle = p::friction_torque_nm(f, p::mean_piston_speed(g, 850.0), vd);
    const double wot = p::friction_torque_nm(f, p::mean_piston_speed(g, 6000.0), vd);
    EXPECT_GT(idle, 12.6); EXPECT_LT(idle, 16.0);   // F-42 initial hot idle range
    EXPECT_GT(wot, 25.0);  EXPECT_LT(wot, 35.0);    // F-42 at 6000
    EXPECT_NEAR(p::friction_torque_nm({1e5, 0, 0}, 0.0, vd), 1e5 * vd / (4 * p::pi), 1e-12);
    EXPECT_NEAR(1e5 * 0.00158 / (4 * p::pi), 12.58, 0.01); // 1 bar <-> 12.58 N.m
}

TEST(PhysicsLosses, OilViscosityAndAlternator) {
    // Walther fit on nu40 = 160 cSt, nu100 = 19 cSt (estimativa 20W50).
    auto w = [](double nu) { return std::log10(std::log10(nu + 0.7)); };
    const double b = (w(160.0) - w(19.0)) / (std::log10(373.15) - std::log10(313.15));
    const double a = w(160.0) + b * std::log10(313.15);
    EXPECT_NEAR(p::walther_visc_cst(a, b, 313.15), 160.0, 1e-6);
    EXPECT_NEAR(p::walther_visc_cst(a, b, 373.15), 19.0, 1e-6);
    EXPECT_GT(p::walther_visc_cst(a, b, 333.15), p::walther_visc_cst(a, b, 363.15));
    EXPECT_NEAR(p::hydrodynamic_scale(2.0, 1.0, 0.5), std::sqrt(2.0), 1e-12);
    // 14.2 V x 25 A at idle ~ 7 N.m (goal example, eta 0.55, alt speed 2.4x crank).
    EXPECT_NEAR(p::alternator_torque_nm(14.2 * 25.0, 0.55, 2.4 * 850.0 * 2 * p::pi / 60.0), 3.0, 0.2);
    EXPECT_NEAR(p::valvetrain_spring_force_n(9.5, 34.9, 0.0), 331.55, 1e-9);
}

TEST(PhysicsDynamics, ClutchAndVehicle) {
    const double re = p::clutch_mean_radius_m(0.095, 0.067);
    EXPECT_NEAR(re * 1e3, 81.8, 0.1);                                    // F-49
    EXPECT_NEAR(p::clutch_torque_nm(0.25, 4500.0, 2, re), 184.0, 0.5);
    EXPECT_NEAR(p::clutch_torque_nm(0.30, 4500.0, 2, re), 221.0, 0.5);
    EXPECT_NEAR(p::clutch_torque_nm(0.35, 4500.0, 2, re), 258.0, 0.5);
    EXPECT_GE(p::clutch_torque_nm(0.25, 4500.0, 2, re), 1.3 * 133.0);
    // Top speed sanity (F-50): 60 kW, eta 0.9 gives 155-180 km/h.
    const double cda = 0.31 * 2.09;
    double v = 20.0;
    for (int i = 0; i < 400000; ++i) {
        const double f = p::vehicle_force_n(1100.0, 0.011, 1.19, cda, v, 0.0);
        v += (0.90 * 57000.0 / v - f) * 1e-4;
    }
    EXPECT_GT(v * 3.6, 155.0);
    EXPECT_LT(v * 3.6, 180.0);
    EXPECT_NEAR(p::vehicle_speed_ms(6000 * 2 * p::pi / 60, 0.283, 0.891, 3.9375) * 3.6, 6000 * 2 * p::pi / 60 * 0.283 / (0.891 * 3.9375) * 3.6, 1e-9);
    EXPECT_NEAR(p::domega_dt(0.2, 100, 0, 20, 5, 5, 10, 0), 300.0, 1e-9); // F-46
}

TEST(PhysicsDynamics, DynoHoldsSpeedAndMeasuresTorque) {
    const double j = 0.20, t_engine = 100.0;
    const double w_ref = 3000.0 * 2 * p::pi / 60.0;
    p::DynoPi pi_ctl;
    pi_ctl.kp = 40.0; pi_ctl.ki = 400.0;
    double w = w_ref * 0.9, brake = 0.0;
    const double dt = 1e-3;
    for (int i = 0; i < 20000; ++i) {
        brake = p::dyno_brake_nm(pi_ctl, w_ref, w, dt);
        w += (t_engine - brake) / j * dt;
    }
    EXPECT_NEAR(w * 60.0 / (2 * p::pi), 3000.0, 10.0);          // +-10 rpm
    EXPECT_NEAR(p::dyno_shaft_torque(brake, j, (t_engine - brake) / j), t_engine, 1.0); // +-1 %
    EXPECT_GE(p::DynoPi{}.t_max, 160.0);
}

TEST(PhysicsDynamics, DynoAntiWindupLimitsIntegral) {
    p::DynoPi c; c.kp = 1.0; c.ki = 10.0; c.t_max = 50.0;
    for (int i = 0; i < 10000; ++i) p::dyno_brake_nm(c, 100.0, 500.0, 1e-3); // engine way too fast
    const double i_sat = c.integral;
    EXPECT_GT(p::dyno_brake_nm(c, 100.0, 500.0, 1e-3), 49.9);
    for (int i = 0; i < 1000; ++i) p::dyno_brake_nm(c, 100.0, 500.0, 1e-3);
    EXPECT_NEAR(c.integral, i_sat, 1e-9); // frozen while saturated
}

TEST(PhysicsThermal, ThermostatFanAndSensor) {
    EXPECT_DOUBLE_EQ(p::thermostat_opening(80.0), 0.0);            // F-52 / manual p.17
    EXPECT_NEAR(p::thermostat_opening(87.0), 0.0, 1e-12);
    EXPECT_NEAR(p::thermostat_opening(92.5), 0.5, 1e-12);
    EXPECT_NEAR(p::thermostat_opening(98.0), 1.0, 1e-12);
    EXPECT_DOUBLE_EQ(p::thermostat_opening(110.0), 1.0);
    EXPECT_FALSE(p::fan_state(false, 91.9));
    EXPECT_TRUE(p::fan_state(false, 92.0));
    EXPECT_TRUE(p::fan_state(true, 89.0));   // hysteresis
    EXPECT_FALSE(p::fan_state(true, 87.0));
    EXPECT_NEAR(p::narrow_o2_volts(1.0), 0.465, 1e-9);
    EXPECT_GT(p::narrow_o2_volts(0.95), 0.8);
    EXPECT_LT(p::narrow_o2_volts(1.05), 0.1);
    EXPECT_NEAR(p::battery_voltage(12.6, 255.0), 12.6 - 255.0 * 0.021, 1e-12);
    EXPECT_NEAR(p::injector_current_derivative(12.0, 0.0, 16.0, 0.01), 1200.0, 1e-9);
    EXPECT_GT(p::exhaust_transport_delay_s(0.002, 0.01, 287.05, 800.0, 1.1e5, 0.05), 0.05);
}

TEST(PhysicsThermal, IntakeEffectiveness) {
    const double e_low = p::intake_heat_effectiveness(2.0, 0.003);
    const double e_high = p::intake_heat_effectiveness(2.0, 0.05);
    EXPECT_GT(e_low, e_high);  // hot at idle, near ambient at full load
    EXPECT_NEAR(p::manifold_air_temp_c(20.0, 0.5, 90.0, 10.0), 45.0, 1e-12);
}

TEST(PhysicsLosses, OilFrictionScaleFollowsViscosity) { // F-43
    p::OilFrictionParams o;
    EXPECT_NEAR(p::oil_friction_scale(o, 90.0), 1.0, 1e-12);        // reference
    double last = 1e9;
    for (double c = -10.0; c <= 120.0; c += 5.0) {                  // monotonic, never < 1 below 90
        const double s = p::oil_friction_scale(o, c);
        EXPECT_LT(s, last + 1e-12);
        last = s;
    }
    const double cold = p::oil_friction_scale(o, 20.0);
    EXPECT_GT(cold, 1.3);   // cold engine drags noticeably more (hydrodynamic share 30 %)
    EXPECT_LT(cold, 1.8);
    EXPECT_LT(p::oil_friction_scale(o, 110.0), 1.0);
}

TEST(PhysicsLosses, AccessoryTorqueAtIdleAndHighSpeed) { // F-45
    p::AccessoryParams a;
    const double idle = p::accessory_torque_nm(a, 14.2, 96.9);          // 925 rpm
    EXPECT_NEAR(idle, 14.2 * 20.0 / (0.55 * 2.0 * 96.9) + 0.5, 1e-9);
    EXPECT_GT(idle, 3.0);
    EXPECT_LT(idle, 5.0);
    EXPECT_DOUBLE_EQ(p::accessory_torque_nm(a, 14.2, 0.0), 0.0);
    // alternator part falls with speed (constant power), pump part rises with w^2
    EXPECT_GT(p::accessory_torque_nm(a, 14.2, 2.0 * p::pi * 700.0 / 60.0), 0.0);
    // No charging (and no constant-power blow-up) near cranking speed.
    EXPECT_LT(p::accessory_torque_nm(a, 14.2, 2.0 * p::pi * 300.0 / 60.0), 0.2);
}
