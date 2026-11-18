add_executable(emu8051-tty_tests test.cpp adc_simulator_test.cpp cpu_hooks_test.cpp port_controller_test.cpp uart_scheduler_test.cpp xram_access_test.cpp crank_dynamics_test.cpp sevel_geometry_test.cpp sevel_scene_test.cpp throttle_assembly_test.cpp thermal_sensor_test.cpp intake_fuel_test.cpp ma17_tachometer_test.cpp)
target_include_directories(emu8051-tty_tests SYSTEM PRIVATE
    ${PROJECT_SOURCE_DIR}/third_party/open-engine-sim/include)
target_compile_definitions(emu8051-tty_tests PRIVATE
    MA17_ROM_PATH="${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin")
target_link_libraries(emu8051-tty_tests emu8051-tty_lib GTest::GTest GTest::Main)
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    # Keep legacy firmware fixtures buildable under the project's -Werror.
    set_source_files_properties(test.cpp PROPERTIES COMPILE_OPTIONS
        "-Wno-range-loop-construct;-Wno-conversion;-Wno-sign-conversion;-Wno-dangling-else")
endif()
gtest_discover_tests(emu8051-tty_tests)
if(TARGET open-engine-sim-geometry)
    add_executable(lab_donor_scene_test lab_donor_scene_test.cpp
        ${PROJECT_SOURCE_DIR}/src/lab/DonorScene.cpp)
    target_include_directories(lab_donor_scene_test SYSTEM PRIVATE
        ${PROJECT_SOURCE_DIR}/third_party/open-engine-sim/include)
    target_link_libraries(lab_donor_scene_test PRIVATE open-engine-sim-geometry
        GTest::GTest GTest::Main)
    if(ENABLE_SEVEL_MA17_LAB_GUI)
        target_sources(lab_donor_scene_test PRIVATE
            ${PROJECT_SOURCE_DIR}/src/lab/MeshAsset.cpp)
        target_compile_definitions(lab_donor_scene_test PRIVATE
            SEVEL_LAB_MESH_ASSET=1
            LAB_MESH_ASSET_PATH="${PROJECT_BINARY_DIR}/assets/authored_meshes.obj.zlib.b64")
        target_link_libraries(lab_donor_scene_test PRIVATE ZLIB::ZLIB)
    endif()
    gtest_discover_tests(lab_donor_scene_test)
endif()
if(ENABLE_SEVEL_MA17_LAB_GUI AND ENABLE_SEVEL_MA17_LAB)
    add_executable(lab_mesh_asset_test lab_mesh_asset_test.cpp
        ${PROJECT_SOURCE_DIR}/src/lab/MeshAsset.cpp)
    target_include_directories(lab_mesh_asset_test SYSTEM PRIVATE
        ${PROJECT_SOURCE_DIR}/third_party/open-engine-sim/include)
    target_compile_definitions(lab_mesh_asset_test PRIVATE
        LAB_MESH_ASSET_PATH="${PROJECT_BINARY_DIR}/assets/authored_meshes.obj.zlib.b64"
        LAB_FONT_ASSET_PATH="${PROJECT_BINARY_DIR}/assets/slkscr.ttf.zlib.b64")
    target_link_libraries(lab_mesh_asset_test PRIVATE GTest::GTest
        GTest::Main open-engine-sim-geometry ZLIB::ZLIB SDL3::SDL3)
    gtest_discover_tests(lab_mesh_asset_test)
endif()
if(ENABLE_SEVEL_MA17_LAB_GUI AND ENABLE_SEVEL_MA17_LAB)
    add_executable(lab_font_test lab_font_test.cpp
        ${PROJECT_SOURCE_DIR}/src/lab/FontRenderer.cpp
        ${PROJECT_SOURCE_DIR}/src/lab/MeshAsset.cpp)
    target_include_directories(lab_font_test SYSTEM PRIVATE
        ${PROJECT_SOURCE_DIR}/third_party/open-engine-sim/include)
    target_compile_definitions(lab_font_test PRIVATE
        LAB_FONT_ASSET_PATH="${PROJECT_BINARY_DIR}/assets/slkscr.ttf.zlib.b64"
        LAB_FALLBACK_FONT_ASSET_PATH="${PROJECT_BINARY_DIR}/assets/DejaVuSansMono-Bold.ttf.zlib.b64")
    target_link_libraries(lab_font_test PRIVATE GTest::GTest GTest::Main
        open-engine-sim-geometry ZLIB::ZLIB SDL3::SDL3 Freetype::Freetype)
    gtest_discover_tests(lab_font_test)
endif()
add_executable(lab_trace_geometry_test lab_trace_geometry_test.cpp
    ${PROJECT_SOURCE_DIR}/src/lab/TraceGeometry.cpp)
target_link_libraries(lab_trace_geometry_test PRIVATE GTest::GTest GTest::Main)
gtest_discover_tests(lab_trace_geometry_test)
if(ENABLE_SEVEL_MA17_LAB_GUI AND ENABLE_SEVEL_MA17_LAB)
    add_executable(lab_scene_color_test lab_scene_color_test.cpp)
    target_link_libraries(lab_scene_color_test PRIVATE GTest::GTest
        GTest::Main SDL3::SDL3)
    gtest_discover_tests(lab_scene_color_test)
    add_executable(lab_profile_audit_test lab_profile_audit_test.cpp)
    target_link_libraries(lab_profile_audit_test PRIVATE GTest::GTest
        GTest::Main SDL3::SDL3)
    gtest_discover_tests(lab_profile_audit_test)
    add_executable(lab_ui_preferences_test lab_ui_preferences_test.cpp)
    target_link_libraries(lab_ui_preferences_test PRIVATE GTest::GTest
        GTest::Main SDL3::SDL3)
    gtest_discover_tests(lab_ui_preferences_test)
    add_executable(lab_layout_test lab_layout_test.cpp)
    target_link_libraries(lab_layout_test PRIVATE GTest::GTest
        GTest::Main SDL3::SDL3)
    gtest_discover_tests(lab_layout_test)
endif()
add_executable(lab_runner_smoke runner_snapshot_smoke.cpp)
target_link_libraries(lab_runner_smoke PRIVATE emu8051-tty_lib)
add_test(NAME LabRunner.OriginalRomSnapshot
    COMMAND lab_runner_smoke
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME LabRunner.TachometerMatchesLatchTrace
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/test_tachometer_trace.py
            $<TARGET_FILE:lab_runner_smoke>
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
add_test(NAME LabRunner.AdcFaultTelemetry
    COMMAND lab_runner_smoke
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin adc_fault)
add_test(NAME LabRunner.DrivetrainTelemetry
    COMMAND lab_runner_smoke
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin drivetrain)
add_test(NAME LabRunner.DrivetrainCli
    COMMAND lab_runner_smoke
            ${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin drivetrain_cli)
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
