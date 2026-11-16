add_executable(emu8051-tty_tests test.cpp adc_simulator_test.cpp cpu_hooks_test.cpp port_controller_test.cpp uart_scheduler_test.cpp xram_access_test.cpp crank_dynamics_test.cpp throttle_assembly_test.cpp thermal_sensor_test.cpp intake_fuel_test.cpp)
target_compile_definitions(emu8051-tty_tests PRIVATE
    MA17_ROM_PATH="${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin")
target_link_libraries(emu8051-tty_tests emu8051-tty_lib GTest::GTest GTest::Main)
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    # Keep legacy firmware fixtures buildable under the project's -Werror.
    set_source_files_properties(test.cpp PROPERTIES COMPILE_OPTIONS
        "-Wno-range-loop-construct;-Wno-conversion;-Wno-sign-conversion;-Wno-dangling-else")
endif()
gtest_discover_tests(emu8051-tty_tests)
add_test(NAME PhysicalCrank.FiatRomRpm
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_physical_crank.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalCrank.SensorOpenAndRestore
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_crank_sensor_open.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalTps.FiatRomTracks
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_physical_tps.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalThermal.FiatRomSensors
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_physical_thermal.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalIntake.ConditionalCc3Fuel
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_physical_intake.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalFuel.E25ClosedLoopResponse
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_fuel_blend_closed_loop.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalIdle.CandidateP15P16
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_physical_idle.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalIdle.ContactOpenElectricalFault
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_idle_contact_open.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalIdle.ContactClosedDuringPedal
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_idle_contact_closed.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalIdle.MotorOpenDuringPedal
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_idle_motor_open.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalLambda.ConditionalClosedLoop
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_sevel_closed_loop.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalLambda.StallCooldown
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_physical_lambda_cooldown.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalLambda.WarmCoilMisfireRecovery
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_physical_misfire_lambda.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalLambda.PumpRelayHeaterCandidate
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_pump_relay_heater.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalSupply.BatteryFeedsAdcInjectorAndHeater
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_battery_supply.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalDiagnostics.RawFaultBanks
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_physical_diagnostics.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalDiagnostics.KlineFaultHistory
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_physical_kline.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalLambda.TableThresholdAtFixedAdc
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_lambda_table_threshold.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalLambda.TableCrossingToCc3
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_lambda_table_to_cc3.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalLambda.ActiveCorrectionToCc3
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_lambda_active_path.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalIgnition.P5PhaseVsRam69
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_ignition_phase.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalEngine.SustainedSixtySeconds
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_sevel_long_run.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalTps.BenchProfileClosedLoop
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_tps_bench_profile.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalTps.PedalRiseAvoidsTransientFault
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_pedal_ramp.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalAdc7.StartupGateLatch
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_adc7_gate_latch.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalAdc4.ConditionalRomRatio
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_adc4_ratio.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME PhysicalPower.RetainedXramAcrossKeyAndProcess
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_power_retention.py
            $<TARGET_FILE:emu8051-tty>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
