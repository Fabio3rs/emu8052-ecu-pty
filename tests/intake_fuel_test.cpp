#include "ecu_hw/Ma17IgnitionStage.hpp"
#include "ecu_hw/Ma17InjectorStage.hpp"
#include "ecu_hw/Ma17LambdaHeater.hpp"
#include "engine/Combustion.hpp"
#include "engine/ExhaustLambda.hpp"
#include "engine/IntakeFuel.hpp"

#include <gtest/gtest.h>

#include <array>
#include <cmath>

namespace {

TEST(Ma17PumpRelay, ShortHighPulseDoesNotReleaseActiveLowRelay) {
    ecu_hw::Ma17PumpRelay relay;
    EXPECT_FALSE(relay.step(true, 0));
    EXPECT_TRUE(relay.step(false, 781));
    EXPECT_TRUE(relay.step(true, 347531));
    EXPECT_TRUE(relay.step(true, 347562));
    EXPECT_TRUE(relay.step(false, 347563));
    EXPECT_TRUE(relay.step(true, 1181883));
    EXPECT_TRUE(relay.step(true, 1191782));
    EXPECT_FALSE(relay.step(true, 1191783));
    EXPECT_THROW(relay.step(false, 1191782), std::invalid_argument);
}

TEST(Ma17LambdaHeater, PumpRelayControlsElectricalPower) {
    ecu_hw::Ma17LambdaHeater heater;
    EXPECT_DOUBLE_EQ(heater.power_w(12.0, false), 0.0);
    EXPECT_DOUBLE_EQ(heater.power_w(12.0, true), 24.0);
    EXPECT_DOUBLE_EQ(heater.power_w(0.0, true), 0.0);
    EXPECT_THROW(heater.power_w(-1.0, true), std::invalid_argument);
}

TEST(IntakeFuel, ConservesAirAndFuelAcrossThrottleAndFilm) {
    engine::IntakeFuel intake;
    for (int step = 0; step < 2000; ++step)
        intake.step(0.001, 1000.0, 0.25, 20.0, 70.0, step < 500 ? 1e-7 : 0.0);
    EXPECT_NEAR(intake.initial_air_mass_kg() + intake.air_in_total_kg() -
                    intake.air_delivered_total_kg(),
                intake.air_mass_kg(), 1e-12);
    EXPECT_NEAR(intake.injected_total_kg(),
                intake.fuel_film_kg() + intake.fuel_vapor_kg() +
                    intake.fuel_delivered_total_kg(),
                1e-12);
    EXPECT_GT(intake.fuel_delivered_total_kg(), 0.0);
    EXPECT_GT(intake.fuel_film_kg(), 0.0);
}

TEST(IntakeFuel, OpeningThrottleRaisesManifoldPressureAtSameRpm) {
    engine::IntakeFuel closed;
    engine::IntakeFuel open;
    for (int step = 0; step < 1000; ++step) {
        closed.step(0.001, 900.0, 0.07, 20.0, 20.0, 0.0);
        open.step(0.001, 900.0, 0.30, 20.0, 20.0, 0.0);
    }
    EXPECT_LT(closed.pressure_pa(), open.pressure_pa());
    EXPECT_LT(open.pressure_pa(), 100000.0);
}

TEST(IntakeFuel, WarmStoppedManifoldVentsExpansionWithoutCreatingAir) {
    engine::IntakeFuel intake;
    for (int step = 0; step < 2000; ++step)
        intake.step(0.001, 0.0, 0.30, 90.0, 90.0, 0.0);
    EXPECT_NEAR(intake.pressure_pa(), 100000.0, 100.0);
    EXPECT_LT(intake.air_in_total_kg(), 0.0);
    EXPECT_NEAR(intake.initial_air_mass_kg() + intake.air_in_total_kg(),
                intake.air_mass_kg(), 1e-12);
}

TEST(Ma17InjectorStage, EffectiveLowPulseHasDeadTimeAndSingleFlow) {
    ecu_hw::Ma17InjectorStage injector;
    constexpr double tick_s = 1.0 / 990000.0;
    EXPECT_DOUBLE_EQ(injector.step(true, tick_s, 12.5), 0.0);
    for (int tick = 0; tick < 9900; ++tick)
        injector.step(false, tick_s, 12.5);
    injector.step(true, tick_s, 12.5);
    const double expected_kg =
        (0.010 - 0.0008) * (900e-6 / 60.0) * 740.0 * std::sqrt(1.0 / 3.0);
    EXPECT_NEAR(injector.delivered_total_kg(), expected_kg, 1e-12);
    EXPECT_EQ(injector.pulse_count(), 1u);
    EXPECT_EQ(injector.energized_ticks(), 9900u);
}

TEST(Ma17InjectorStage, KeyCycleClearsCurrentWithoutRestoringOpenCircuit) {
    ecu_hw::Ma17InjectorStage injector;
    injector.step(false, 0.002, 12.5);
    ASSERT_TRUE(injector.energized());
    injector.set_connected(false);
    injector.reset_electrical_state();
    EXPECT_FALSE(injector.energized());
    EXPECT_DOUBLE_EQ(injector.coil_current_a(), 0.0);
    EXPECT_DOUBLE_EQ(injector.step(false, 0.002, 12.5), 0.0);
    EXPECT_EQ(injector.pulse_count(), 1u);
}

TEST(FuelBlend, E25KeepsVolumeMassAndStoichiometryConsistent) {
    const auto e0 = engine::FuelBlend::from_ethanol_percent(0);
    const auto e25 = engine::FuelBlend::from_ethanol_percent(25);
    EXPECT_DOUBLE_EQ(e0.density_kg_m3(), 740.0);
    EXPECT_DOUBLE_EQ(e0.stoichiometric_air_fuel_ratio(), 14.7);
    EXPECT_DOUBLE_EQ(e0.lower_heating_value_j_kg(), 44e6);
    EXPECT_NEAR(e25.density_kg_m3(), 752.25, 1e-9);
    EXPECT_NEAR(e25.stoichiometric_air_fuel_ratio(), 13.2055, 0.01);
    EXPECT_LT(e25.lower_heating_value_j_kg(), e0.lower_heating_value_j_kg());
    EXPECT_THROW(engine::FuelBlend::from_ethanol_percent(-1),
                 std::invalid_argument);
    EXPECT_THROW(engine::FuelBlend::from_ethanol_percent(101),
                 std::invalid_argument);
}

TEST(Ma17InjectorStage, BallastLimitsCurrentAndVoltageChangesOpening) {
    ecu_hw::Ma17InjectorStage low;
    ecu_hw::Ma17InjectorStage nominal;
    ecu_hw::Ma17InjectorStage high;
    constexpr double tick_s = 1.0 / 990000.0;
    for (int tick = 0; tick < 3000; ++tick) {
        low.step(false, tick_s, 10.0);
        nominal.step(false, tick_s, 12.5);
        high.step(false, tick_s, 14.5);
    }
    EXPECT_LT(low.delivered_total_kg(), nominal.delivered_total_kg());
    EXPECT_LT(nominal.delivered_total_kg(), high.delivered_total_kg());
    EXPECT_NEAR(nominal.coil_current_a(), 12.5 / 4.7, 0.7);
    EXPECT_LT(high.coil_current_a(), 14.5 / 4.7);
    EXPECT_GT(low.coil_current_a(), 0.0);
    low.step(true, tick_s, 10.0);
    EXPECT_DOUBLE_EQ(low.coil_current_a(), 0.0);

    ecu_hw::InjectorStageParameters no_ballast_parameters;
    no_ballast_parameters.ballast_resistance_ohm = 0.0;
    ecu_hw::Ma17InjectorStage no_ballast{no_ballast_parameters};
    for (int tick = 0; tick < 3000; ++tick)
        no_ballast.step(false, tick_s, 12.5);
    EXPECT_GT(no_ballast.coil_current_a(), nominal.coil_current_a());
}

TEST(Ma17InjectorStage, ShortLowVoltagePulseNeedsPullInCurrent) {
    ecu_hw::Ma17InjectorStage low;
    ecu_hw::Ma17InjectorStage nominal;
    constexpr double tick_s = 1.0 / 990000.0;
    for (int tick = 0; tick < 1782; ++tick) {
        low.step(false, tick_s, 6.0);
        nominal.step(false, tick_s, 12.5);
    }
    EXPECT_DOUBLE_EQ(low.delivered_total_kg(), 0.0);
    EXPECT_GT(low.coil_current_a(), 0.0);
    EXPECT_GT(nominal.delivered_total_kg(), 0.0);
    for (int tick = 0; tick < 500; ++tick)
        low.step(false, tick_s, 6.0);
    EXPECT_GT(low.delivered_total_kg(), 0.0);
    EXPECT_EQ(low.pulse_count(), 1u);
}

TEST(Combustion, RequiresChargeAndSparkAtCandidatePhase) {
    engine::Combustion combustion;
    constexpr double pi = 3.14159265358979323846;
    const double phase = 2.0 * pi / 3.0;
    const double firing = phase + 4.0 * pi;
    combustion.admit({0.0, 0.0001, 0.00001}, phase + 2.0 * pi + 0.1);
    EXPECT_DOUBLE_EQ(combustion.torque_nm(firing), 0.0);
    const auto event = combustion.spark(firing, 0);
    EXPECT_EQ(combustion.burns(), 1u);
    EXPECT_EQ(event.cylinder_index, 0u);
    EXPECT_GT(event.burned_fuel_kg, 0.0);
    EXPECT_LE(event.burned_fuel_kg, event.fuel_kg);
    EXPECT_GT(combustion.torque_nm(firing), 0.0);
    EXPECT_DOUBLE_EQ(combustion.torque_nm(firing + 2.01), 0.0);
    combustion.spark(firing + pi, 1);
    EXPECT_EQ(combustion.burns(), 1u);
    combustion.admit({0.0, 0.0001, 0.00001}, firing + 0.1);
    combustion.spark(firing + 2.0 * pi + 0.8, 0);
    EXPECT_EQ(combustion.burns(), 1u);
}

TEST(Combustion, TdcPhaseCanUseOneHundredTwentyDegreeReference) {
    constexpr double pi = 3.14159265358979323846;
    engine::Combustion combustion{{2.0 * pi / 3.0}};
    const double phase = 2.0 * pi / 3.0;
    combustion.admit({0.0, 0.0001, 0.00001}, phase + 2.0 * pi + 0.1);
    EXPECT_GT(combustion.spark(phase + 4.0 * pi - 0.15, 0).burned_fuel_kg, 0.0);
    EXPECT_EQ(combustion.burns(), 1u);
}

TEST(Combustion, FullCyclePhaseSwapsCompressionCylinderWithinCoilPair) {
    constexpr double pi = 3.14159265358979323846;
    const double first_tdc = 2.0 * pi / 3.0;
    const engine::IntakeStep charge{0.0, 0.0001, 0.00001};
    engine::Combustion first{{first_tdc}};
    engine::Combustion second{{first_tdc + 2.0 * pi}};
    const double intake_angle = first_tdc + 2.0 * pi + 0.1;
    const double firing_angle = first_tdc + 4.0 * pi;
    first.admit(charge, intake_angle);
    second.admit(charge, intake_angle);

    const auto first_event = first.spark(firing_angle, 0);
    const auto second_event = second.spark(firing_angle, 0);
    EXPECT_EQ(first_event.cylinder_index, 0u);
    EXPECT_EQ(second_event.cylinder_index, 3u);
    EXPECT_DOUBLE_EQ(first_event.burned_fuel_kg, second_event.burned_fuel_kg);
    EXPECT_DOUBLE_EQ(first.torque_nm(firing_angle),
                     second.torque_nm(firing_angle));
    EXPECT_THROW(engine::Combustion({4.0 * pi}), std::invalid_argument);
}

TEST(Combustion, SparkTimingChangesUsefulWorkWithSameCharge) {
    constexpr double pi = 3.14159265358979323846;
    const double tdc = 2.0 * pi / 3.0 + 4.0 * pi;
    const engine::IntakeStep charge{0.0, 0.0001, 0.00001};
    engine::Combustion near_optimum;
    engine::Combustion late;
    near_optimum.admit(charge, tdc - 2.0 * pi + 0.1);
    late.admit(charge, tdc - 2.0 * pi + 0.1);
    const auto early_event = near_optimum.spark(tdc - 0.20, 0);
    const auto late_event = late.spark(tdc + 0.20, 0);
    EXPECT_DOUBLE_EQ(early_event.burned_fuel_kg,
                     late_event.burned_fuel_kg);
    EXPECT_GT(near_optimum.torque_nm(tdc + 0.20),
              late.torque_nm(tdc + 0.20));
}

TEST(Combustion, WeakSparkLeavesFuelAndOxygenForExhaust) {
    constexpr double pi = 3.14159265358979323846;
    const double tdc = 2.0 * pi / 3.0 + 4.0 * pi;
    const engine::IntakeStep charge{0.0, 0.0001, 0.00001};
    engine::Combustion full;
    engine::Combustion weak;
    engine::Combustion normal;
    full.admit(charge, tdc - 2.0 * pi + 0.1);
    weak.admit(charge, tdc - 2.0 * pi + 0.1);
    normal.admit(charge, tdc - 2.0 * pi + 0.1);
    const auto full_event = full.spark(tdc - 0.20, 0, 1.0);
    const auto weak_event = weak.spark(tdc - 0.20, 0, 0.5);
    const auto normal_event = normal.spark(tdc - 0.20, 0, 0.9);

    EXPECT_DOUBLE_EQ(weak_event.fuel_kg, full_event.fuel_kg);
    EXPECT_GT(weak_event.burned_fuel_kg, 0.5 * full_event.burned_fuel_kg);
    EXPECT_LT(weak_event.burned_fuel_kg, full_event.burned_fuel_kg);
    EXPECT_NEAR(weak.torque_nm(tdc), 0.5 * full.torque_nm(tdc), 1e-12);
    EXPECT_DOUBLE_EQ(weak.burned_fuel_kg(), weak_event.burned_fuel_kg);
    EXPECT_DOUBLE_EQ(normal_event.burned_fuel_kg, full_event.burned_fuel_kg);
    EXPECT_LT(normal.torque_nm(tdc), full.torque_nm(tdc));

    engine::ExhaustLambda full_exhaust;
    engine::ExhaustLambda weak_exhaust;
    full_exhaust.admit(full_event, 0.002, 0);
    weak_exhaust.admit(weak_event, 0.002, 0);
    full_exhaust.step(0.2, 198000);
    weak_exhaust.step(0.2, 198000);
    EXPECT_DOUBLE_EQ(full_exhaust.charge_lambda(),
                     weak_exhaust.charge_lambda());
    EXPECT_LT(full_exhaust.lambda(), weak_exhaust.lambda());
    EXPECT_LT(weak_exhaust.lambda(), 5.0);
    EXPECT_LT(full_exhaust.temperature_c(), 650.0);
    EXPECT_LT(weak_exhaust.temperature_c(), full_exhaust.temperature_c());
}

TEST(Combustion, RoutesFourChargesToCompressionCylinderAndCoil) {
    constexpr double pi = 3.14159265358979323846;
    constexpr double phase = 2.0 * pi / 3.0;
    constexpr std::array<unsigned, 4> order{0, 2, 3, 1};
    engine::Combustion combustion;
    const engine::IntakeStep charge{0.0, 0.0001, 0.00001};
    combustion.admit(charge, phase + 2.0 * pi + 0.1);
    combustion.admit(charge, phase + 3.0 * pi + 0.1);
    double discharged_air_kg = 0.0;
    double discharged_fuel_kg = 0.0;
    for (unsigned slot = 0; slot < 4; ++slot) {
        const auto event = combustion.spark(phase + (4.0 + slot) * pi, slot % 2);
        EXPECT_EQ(event.cylinder_index, order[slot]);
        EXPECT_GT(event.burned_fuel_kg, 0.0);
        discharged_air_kg += event.air_kg;
        discharged_fuel_kg += event.fuel_kg;
        if (slot < 2)
            combustion.admit(charge, phase + (4.0 + slot) * pi + 0.1);
    }
    EXPECT_NEAR(discharged_air_kg, 4.0 * charge.air_to_cylinders_kg, 1e-12);
    EXPECT_NEAR(discharged_fuel_kg, 4.0 * charge.fuel_to_cylinders_kg, 1e-12);
    EXPECT_EQ(combustion.burns_by_cylinder(),
              (std::array<unsigned long long, 4>{1, 1, 1, 1}));
}

TEST(Combustion, WrongCoilDischargesOnlyItsCompressionCharge) {
    constexpr double pi = 3.14159265358979323846;
    engine::Combustion combustion;
    const engine::IntakeStep charge{0.0, 0.0001, 0.00001};
    const double phase = 2.0 * pi / 3.0;
    combustion.admit(charge, phase + 2.0 * pi + 0.1);
    combustion.admit(charge, phase + 3.0 * pi + 0.1);
    const auto missed = combustion.spark(phase + 4.0 * pi, 1);
    EXPECT_EQ(missed.burned_fuel_kg, 0.0);
    EXPECT_EQ(combustion.missed_sparks(), 1u);
    EXPECT_GT(combustion.spark(phase + 5.0 * pi, 1).burned_fuel_kg, 0.0);
    EXPECT_EQ(combustion.burns_by_cylinder()[2], 1u);
}

TEST(Combustion, CoilPairBindingCanBeReversed) {
    constexpr double pi = 3.14159265358979323846;
    engine::Combustion combustion{{1.96, true}};
    EXPECT_EQ(combustion.pair_for_channel(0), 1u);
    EXPECT_EQ(combustion.pair_for_channel(1), 0u);
    EXPECT_THROW(combustion.pair_for_channel(2), std::out_of_range);
    const engine::IntakeStep charge{0.0, 0.0001, 0.00001};
    combustion.admit(charge, 1.96 + 2.0 * pi + 0.1);
    combustion.admit(charge, 1.96 + 3.0 * pi + 0.1);
    EXPECT_GT(combustion.spark(1.96 + 4.0 * pi, 1).burned_fuel_kg, 0.0);
    EXPECT_GT(combustion.spark(1.96 + 5.0 * pi, 0).burned_fuel_kg, 0.0);
    EXPECT_EQ(combustion.burns(), 2u);
}

TEST(Ma17IgnitionStage, ReleasesChargeOnlyAfterLowDwell) {
    ecu_hw::Ma17IgnitionStage stage;
    stage.step(0x03, 0.001);
    EXPECT_DOUBLE_EQ(stage.step(0x02, 0.001)[0], 0.0);
    EXPECT_NEAR(stage.step(0x03, 0.001)[0], 0.5, 1e-12);
    EXPECT_DOUBLE_EQ(stage.step(0x03, 0.001)[0], 0.0);
    stage.step(0x01, 0.001);
    stage.step(0x01, 0.001);
    EXPECT_DOUBLE_EQ(stage.step(0x03, 0.001)[1], 1.0);
}

TEST(Ma17IgnitionStage, OpenCoilSuppressesOnlyItsSpark) {
    ecu_hw::Ma17IgnitionStage stage;
    stage.step(0x03, 0.001);
    stage.set_connected(0, false);
    stage.step(0x00, 0.001);
    stage.step(0x00, 0.001);
    const auto open = stage.step(0x03, 0.001);
    EXPECT_DOUBLE_EQ(open[0], 0.0);
    EXPECT_DOUBLE_EQ(open[1], 1.0);
    EXPECT_TRUE(stage.attempted(0));
    EXPECT_TRUE(stage.attempted(1));

    stage.set_connected(0, true);
    stage.step(0x00, 0.002);
    EXPECT_FALSE(stage.attempted(0));
    const auto restored = stage.step(0x03, 0.001);
    EXPECT_DOUBLE_EQ(restored[0], 1.0);
}

TEST(Ma17IgnitionStage, KeyCycleClearsDwellAndKeepsOpenCoil) {
    ecu_hw::Ma17IgnitionStage stage;
    stage.step(0x03, 0.001);
    stage.step(0x02, 0.002);
    stage.set_connected(0, false);
    stage.reset_charge();
    EXPECT_DOUBLE_EQ(stage.step(0x03, 0.001)[0], 0.0);
    EXPECT_FALSE(stage.attempted(0));
    stage.step(0x02, 0.002);
    EXPECT_DOUBLE_EQ(stage.step(0x03, 0.001)[0], 0.0);
    EXPECT_TRUE(stage.attempted(0));
}

TEST(ExhaustLambda, TransportAndWarmupPrecedeNarrowbandResponse) {
    engine::ExhaustLambda exhaust;
    exhaust.admit({0.0001, 0.00001, 0.00001}, 0.002, 0);
    exhaust.step(0.01, 9900);
    EXPECT_DOUBLE_EQ(exhaust.lambda(), 5.0);
    EXPECT_DOUBLE_EQ(exhaust.voltage_v(), 0.45);
    for (int step = 2; step <= 200; ++step) {
        if (step % 10 == 0)
            exhaust.admit({0.0001, 0.00001, 0.00001}, 0.002,
                          static_cast<int64_t>(step) * 9900);
        exhaust.step(0.01, static_cast<int64_t>(step) * 9900);
    }
    EXPECT_TRUE(exhaust.valid());
    EXPECT_LT(exhaust.lambda(), 1.0);
    EXPECT_GT(exhaust.voltage_v(), 0.8);
    exhaust.admit({0.0001, 0.00001, 0.0}, 0.002, 2000000);
    for (int step = 201; step <= 300; ++step)
        exhaust.step(0.01, static_cast<int64_t>(step) * 9900);
    EXPECT_GT(exhaust.lambda(), 1.0);
    EXPECT_LT(exhaust.voltage_v(), 0.2);
    for (int step = 301; step <= 4000; ++step)
        exhaust.step(0.01, static_cast<int64_t>(step) * 9900);
    EXPECT_FALSE(exhaust.valid());
    EXPECT_NEAR(exhaust.temperature_c(), 20.0, 10.0);
    EXPECT_NEAR(exhaust.voltage_v(), 0.45, 1e-9);
}

TEST(ExhaustLambda, BlendChangesStoichiometricAfrButNotLambdaSwitchPoint) {
    engine::ExhaustParameters e25_parameters;
    e25_parameters.fuel = engine::FuelBlend::from_ethanol_percent(25);
    engine::ExhaustLambda e0_at_stoich;
    engine::ExhaustLambda e25_at_stoich(e25_parameters);
    engine::ExhaustLambda e0_at_afr14;
    engine::ExhaustLambda e25_at_afr14(e25_parameters);
    constexpr double fuel_kg = 1e-5;
    const double e0_stoich =
        engine::FuelBlend{}.stoichiometric_air_fuel_ratio();
    const double e25_stoich =
        e25_parameters.fuel.stoichiometric_air_fuel_ratio();
    ASSERT_LT(e25_stoich, e0_stoich);

    for (int step = 1; step <= 30; ++step) {
        const int64_t tick = static_cast<int64_t>(step) * 99000;
        e0_at_stoich.admit({e0_stoich * fuel_kg, fuel_kg, fuel_kg}, 0.002,
                           tick);
        e25_at_stoich.admit({e25_stoich * fuel_kg, fuel_kg, fuel_kg}, 0.002,
                            tick);
        e0_at_afr14.admit({14.0 * fuel_kg, fuel_kg, 14.0 * fuel_kg / e0_stoich},
                          0.002, tick);
        e25_at_afr14.admit({14.0 * fuel_kg, fuel_kg, fuel_kg}, 0.002, tick);
        e0_at_stoich.step(0.1, tick, 24.0);
        e25_at_stoich.step(0.1, tick, 24.0);
        e0_at_afr14.step(0.1, tick, 24.0);
        e25_at_afr14.step(0.1, tick, 24.0);
    }

    ASSERT_TRUE(e0_at_stoich.valid());
    ASSERT_TRUE(e25_at_stoich.valid());
    EXPECT_NEAR(e0_at_stoich.lambda(), 1.0, 1e-3);
    EXPECT_NEAR(e25_at_stoich.lambda(), 1.0, 1e-3);
    EXPECT_NEAR(e0_at_stoich.voltage_v(), e25_at_stoich.voltage_v(), 1e-9);
    EXPECT_LT(e0_at_afr14.lambda(), 1.0);
    EXPECT_GT(e25_at_afr14.lambda(), 1.0);
    EXPECT_GT(e0_at_afr14.voltage_v(), e25_at_afr14.voltage_v());
}

TEST(ExhaustLambda, NarrowbandSwitchesAcrossOnePercentLambdaWindow) {
    engine::ExhaustParameters experimental;
    experimental.narrowband_slope = 600.0;
    engine::ExhaustLambda rich(experimental);
    engine::ExhaustLambda lean(experimental);
    constexpr double fuel_kg = 1e-5;
    const double stoich = engine::FuelBlend{}.stoichiometric_air_fuel_ratio();
    for (int step = 1; step <= 30; ++step) {
        const int64_t tick = static_cast<int64_t>(step) * 99000;
        rich.admit({0.995 * stoich * fuel_kg, fuel_kg, 0.995 * fuel_kg}, 0.002,
                   tick);
        lean.admit({1.005 * stoich * fuel_kg, fuel_kg, fuel_kg}, 0.002, tick);
        rich.step(0.1, tick, 24.0);
        lean.step(0.1, tick, 24.0);
    }
    ASSERT_TRUE(rich.valid());
    ASSERT_TRUE(lean.valid());
    EXPECT_NEAR(rich.lambda(), 0.995, 1e-3);
    EXPECT_NEAR(lean.lambda(), 1.005, 1e-3);
    EXPECT_GT(rich.voltage_v() / lean.voltage_v(), 6.0);
}

TEST(ExhaustLambda, DelayedGasDoesNotHeatSensorBeforeArrival) {
    engine::ExhaustLambda exhaust;
    exhaust.admit({0.0001, 0.00001, 0.00001}, 1e-5, 0);
    for (int step = 1; step <= 40; ++step)
        exhaust.step(0.1, static_cast<int64_t>(step) * 99000);
    EXPECT_DOUBLE_EQ(exhaust.temperature_c(), 20.0);
    EXPECT_FALSE(exhaust.valid());
    EXPECT_DOUBLE_EQ(exhaust.voltage_v(), 0.45);

    for (int step = 41; step <= 80; ++step)
        exhaust.step(0.1, static_cast<int64_t>(step) * 99000);
    EXPECT_FALSE(exhaust.valid());
    EXPECT_GT(exhaust.temperature_c(), 20.0);
    EXPECT_LT(exhaust.temperature_c(), 200.0);
    EXPECT_DOUBLE_EQ(exhaust.voltage_v(), 0.45);
}

TEST(ExhaustLambda, PoweredHeaterWarmsWithoutExhaustAndCoolsAfterRelayOpens) {
    engine::ExhaustLambda exhaust;
    for (int step = 1; step <= 200; ++step)
        exhaust.step(0.1, static_cast<int64_t>(step) * 99000, 24.0);
    EXPECT_TRUE(exhaust.valid());
    EXPECT_GT(exhaust.temperature_c(), 300.0);
    for (int step = 201; step <= 500; ++step)
        exhaust.step(0.1, static_cast<int64_t>(step) * 99000);
    EXPECT_FALSE(exhaust.valid());
    EXPECT_LT(exhaust.temperature_c(), 50.0);
    EXPECT_THROW(exhaust.step(0.1, 50000000, -1.0), std::invalid_argument);
}

TEST(ExhaustLambda, HeaterDoesNotDelayWarmupWithHotExhaust) {
    engine::ExhaustLambda unpowered;
    engine::ExhaustLambda powered;
    for (int step = 1; step <= 30; ++step) {
        const int64_t tick = static_cast<int64_t>(step) * 99000;
        const engine::CombustionEvent event{0.0001, 0.00001, 0.00001};
        unpowered.admit(event, 0.002, tick);
        powered.admit(event, 0.002, tick);
        unpowered.step(0.1, tick);
        powered.step(0.1, tick, 24.0);
        EXPECT_GE(powered.temperature_c(), unpowered.temperature_c());
        if (unpowered.valid()) {
            EXPECT_TRUE(powered.valid());
        }
    }
    EXPECT_GT(powered.temperature_c(), unpowered.temperature_c());
}

TEST(ExhaustLambda, MixesBurnedAndMisfiredGasArrivingTogether) {
    engine::ExhaustLambda exhaust;
    exhaust.admit({0.0001, 0.00001, 0.00001}, 0.1, 0);
    exhaust.admit({0.0001, 0.00001, 0.0}, 0.1, 0);
    for (int step = 1; step <= 100; ++step)
        exhaust.step(0.01, static_cast<int64_t>(step) * 9900);
    EXPECT_GT(exhaust.lambda(), 1.0);
    EXPECT_LT(exhaust.lambda(), 5.0);
    EXPECT_LT(exhaust.charge_lambda(), 1.0);
}

} // namespace
