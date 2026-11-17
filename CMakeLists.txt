cmake_minimum_required(VERSION 3.12)
project(emu8051-tty C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_C_EXTENSIONS ON)

option(ENABLE_TESTS "Enable tests" ON)
option(ENABLE_SANITIZERS "Enable sanitizers" OFF)
option(ENABLE_SAB80C517 "Enable SAB80C517 interrupt support" ON)
option(ENABLE_SEVEL_MA17_LAB "Build the SEVEL MA1.7 Lab" OFF)
option(ENABLE_SEVEL_MA17_LAB_GUI "Build the SDL3 Lab window" ON)

# Enable 8052 mode by default (Timer 2, 6 interrupt sources, 256B IRAM)
# This is required for Bosch Monomotronic MA1.7 firmware which uses Timer 2
add_compile_definitions(__8052__)

# SAB80C517 support (conditional compilation)
if(ENABLE_SAB80C517)
    add_definitions(-D__SAB80C517__)
    message(STATUS "SAB80C517 support: ENABLED")
else()
    message(STATUS "SAB80C517 support: DISABLED (8051/8052 mode)")
endif()

include_directories(SYSTEM ${CMAKE_CURRENT_SOURCE_DIR}/emu8051)

if (${CMAKE_CXX_COMPILER_ID} STREQUAL "GNU")
    message(STATUS "Setting G++ flags")
    add_compile_options(-Wall -Werror -Wextra -Wformat-security -Wconversion -Wsign-conversion)
elseif (${CMAKE_CXX_COMPILER_ID} STREQUAL "MSVC")
    message(STATUS "Setting MSVC flags")
    add_compile_options(/W4 /WX)
elseif (${CMAKE_CXX_COMPILER_ID} STREQUAL "Clang")
    message(STATUS "Setting Clang flags")
    # Keep all Clang diagnostics enabled, except the explicitly reviewed categories below.
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Werror>
                        $<$<COMPILE_LANGUAGE:CXX>:-Weverything>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-c++98-compat>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-c++98-compat-pedantic>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-padded>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-global-constructors>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-exit-time-destructors>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-weak-vtables>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-documentation>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-documentation-unknown-command>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-unsafe-buffer-usage>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-unsafe-buffer-usage-in-libc-call>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-unused-macros>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-c99-designator>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-covered-switch-default>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-switch-default>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-ctad-maybe-unsupported>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-float-equal>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-old-style-cast>
                        $<$<COMPILE_LANGUAGE:CXX>:-Wno-reserved-macro-identifier>)
endif()

if(ENABLE_TESTS)
    include(CTest)
    enable_testing()
    find_package(GTest QUIET)
    if(GTest_FOUND)
        message(STATUS "GTest found, enabling tests")
        include(GoogleTest)
    else()
        message(WARNING "GTest not found, tests will be disabled. Install GTest to enable testing.")
        set(ENABLE_TESTS OFF)
    endif()
endif()

if(ENABLE_SANITIZERS)
    # Common sanitizer flags for better security and debugging
    set(SANITIZER_FLAGS
        -fno-omit-frame-pointer
        -fsanitize=address
        -fsanitize=alignment
        -fsanitize=bool
        -fsanitize=bounds
        -fsanitize=enum
        -fsanitize=float-cast-overflow
        -fsanitize=float-divide-by-zero
        -fsanitize=integer-divide-by-zero
        -fsanitize=leak
        -fsanitize=nonnull-attribute
        -fsanitize=pointer-compare
        -fsanitize=pointer-overflow
        -fsanitize=pointer-subtract
        -fsanitize=return
        -fsanitize=returns-nonnull-attribute
        -fsanitize=shift
        -fsanitize=signed-integer-overflow
        -fsanitize=undefined
        -fsanitize=unreachable
        -fsanitize=vla-bound
        -fsanitize=vptr
        -g
    )

    add_compile_options(${SANITIZER_FLAGS})
    add_link_options(${SANITIZER_FLAGS})

    if (${CMAKE_CXX_COMPILER_ID} STREQUAL "Clang")
        message(STATUS "Setting Clang-specific sanitizer flags")
        add_compile_options(-fsanitize=implicit-conversion -fsanitize=unsigned-integer-overflow)
        add_link_options(-fsanitize=implicit-conversion -fsanitize=unsigned-integer-overflow)
    endif()
endif()

# Add the include directory.
include_directories(include)

# Enable precompiled headers if supported
if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.16")
    # Modern CMake precompiled header support
    set(PCH_HEADER "include/stdafx.hpp")
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${PCH_HEADER}")
        message(STATUS "Using precompiled header: ${PCH_HEADER}")
        # We'll set this after creating the targets
    endif()
endif()

# Explicit sources keep component ownership and build changes reviewable.
set(SOURCES
    src/lib.cpp
    src/main.cpp
    src/ecu_hw/Ma17TpsCircuit.cpp
    src/ecu_hw/Ma17SensorCircuit.cpp
    src/ecu_hw/Ma17InjectorStage.cpp
    src/engine/CrankDynamics.cpp
    src/engine/IntakeFuel.cpp
    src/engine/ThrottleAssembly.cpp
    src/engine/ThermalState.cpp
    src/ma17/AdcSimulator.cpp
    src/ma17/CrankInput.cpp
    src/ma17/CpuHooks.cpp
    src/ma17/EmulatorConfig.cpp
    src/ma17/EmulatorLoop.cpp
    src/ma17/ExecutionTracer.cpp
    src/ma17/FiveBaudInjector.cpp
    src/ma17/FirmwareLoader.cpp
    src/ma17/FirmwareProbes.cpp
    src/ma17/InterruptTracer.cpp
    src/ma17/PortController.cpp
    src/ma17/PtyBridge.cpp
    src/ma17/UartScheduler.cpp
    src/ma17/XramAccess.cpp
)

# Add emu8051 core C files
set(EMU8051_SOURCES
    "${CMAKE_CURRENT_SOURCE_DIR}/emu8051/core.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/emu8051/opcodes.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/emu8051/disasm.c"
)

message(STATUS "Sources: ${SOURCES}")
message(STATUS "EMU8051 Sources: ${EMU8051_SOURCES}")

add_library(emu8051-tty_lib STATIC ${SOURCES} ${EMU8051_SOURCES})

# The emu8051 C code is third-party and doesn't compile with strict warnings
# Apply more lenient flags to C files
if(CMAKE_C_COMPILER_ID STREQUAL "GNU")
    set_source_files_properties(${EMU8051_SOURCES} PROPERTIES
        COMPILE_FLAGS "-Wno-conversion -Wno-sign-conversion -Wno-unused-parameter")
elseif(CMAKE_C_COMPILER_ID MATCHES "Clang")
    set_source_files_properties(${EMU8051_SOURCES} PROPERTIES
        COMPILE_FLAGS "-Wno-everything")
endif()

add_executable(emu8051-tty "src/cli_main.cpp")
target_link_libraries(emu8051-tty emu8051-tty_lib)

if(ENABLE_SEVEL_MA17_LAB)
    find_package(Threads REQUIRED)
    if(ENABLE_SEVEL_MA17_LAB_GUI)
        find_package(SDL3 3.2 CONFIG QUIET)
        if(NOT TARGET SDL3::SDL3)
            if(CMAKE_VERSION VERSION_LESS 3.14)
                message(FATAL_ERROR
                    "SDL3 was not found; install SDL3 or use CMake 3.14+ to fetch it")
            endif()
            include(FetchContent)
            FetchContent_Declare(SDL3
                GIT_REPOSITORY https://github.com/libsdl-org/SDL.git
                GIT_TAG release-3.2.8
                GIT_SHALLOW TRUE)
            FetchContent_MakeAvailable(SDL3)
        endif()
    endif()
    add_library(open-engine-sim-geometry STATIC
        third_party/open-engine-sim/src/gaussian_filter.cpp
        third_party/open-engine-sim/src/function.cpp
        third_party/open-engine-sim/src/ui_math.cpp
        third_party/open-engine-sim/src/shaders.cpp
        third_party/open-engine-sim/src/gauge.cpp
        third_party/open-engine-sim/src/oscilloscope.cpp
        third_party/open-engine-sim/src/geometry_generator.cpp
        third_party/open-engine-sim/src/authored_mesh_library.cpp)
    target_include_directories(open-engine-sim-geometry SYSTEM PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party/open-engine-sim/include)
    target_compile_definitions(open-engine-sim-geometry PUBLIC __forceinline=inline)
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(open-engine-sim-geometry PRIVATE -Wno-error)
    endif()
    add_library(open-engine-sim-audio STATIC
        third_party/open-engine-sim/src/filter.cpp
        third_party/open-engine-sim/src/low_pass_filter.cpp
        third_party/open-engine-sim/src/convolution_filter.cpp
        third_party/open-engine-sim/src/derivative_filter.cpp
        third_party/open-engine-sim/src/leveling_filter.cpp
        third_party/open-engine-sim/src/jitter_filter.cpp
        third_party/open-engine-sim/src/synthesizer.cpp)
    target_include_directories(open-engine-sim-audio SYSTEM PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party/open-engine-sim/include)
    target_compile_definitions(open-engine-sim-audio PUBLIC __forceinline=inline)
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(open-engine-sim-audio PRIVATE -Wno-error)
    endif()
    target_link_libraries(open-engine-sim-audio PUBLIC Threads::Threads)
    add_executable(sevel-ma17-lab
        apps/sevel-ma17-lab/main.cpp
        src/lab/AcousticAdapter.cpp
        src/lab/SimSession.cpp
        src/lab/StreamingAudio.cpp
        src/lab/WavWriter.cpp)
    target_include_directories(sevel-ma17-lab SYSTEM PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party/open-engine-sim/include)
    target_link_libraries(sevel-ma17-lab PRIVATE emu8051-tty_lib
        open-engine-sim-audio open-engine-sim-geometry)
    if(ENABLE_SEVEL_MA17_LAB_GUI)
        find_package(ZLIB REQUIRED)
        find_package(Freetype REQUIRED)
        file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/assets)
        configure_file(
            third_party/open-engine-sim/assets/authored_meshes.obj.zlib.b64
            ${CMAKE_CURRENT_BINARY_DIR}/assets/authored_meshes.obj.zlib.b64
            COPYONLY)
        configure_file(
            third_party/open-engine-sim/assets/fonts/slkscr.ttf.zlib.b64
            ${CMAKE_CURRENT_BINARY_DIR}/assets/slkscr.ttf.zlib.b64
            COPYONLY)
        configure_file(
            "third_party/open-engine-sim/assets/fonts/Kottke Silkscreen License.txt"
            "${CMAKE_CURRENT_BINARY_DIR}/assets/Kottke Silkscreen License.txt"
            COPYONLY)
        configure_file(third_party/SDL3_LICENSE.txt
            ${CMAKE_CURRENT_BINARY_DIR}/assets/SDL3_LICENSE.txt COPYONLY)
        find_package(Python3 COMPONENTS Interpreter REQUIRED)
        file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/assets/shaders)
        foreach(shader IN ITEMS engine_sim.hlsl engine_sim.vertex.msl
                engine_sim.fragment.msl)
            configure_file(
                third_party/open-engine-sim/assets/shaders/${shader}
                ${CMAKE_CURRENT_BINARY_DIR}/assets/shaders/${shader}
                COPYONLY)
        endforeach()
        function(sevel_restore_shader shader hash)
            set(source ${CMAKE_CURRENT_SOURCE_DIR}/third_party/open-engine-sim/assets/shaders/${shader}.zlib.b64)
            set(output ${CMAKE_CURRENT_BINARY_DIR}/assets/shaders/${shader})
            add_custom_command(OUTPUT ${output}
                COMMAND ${Python3_EXECUTABLE}
                    ${CMAKE_CURRENT_SOURCE_DIR}/tools/decode_lab_shader.py
                    ${source} ${output} ${hash}
                DEPENDS ${source} ${CMAKE_CURRENT_SOURCE_DIR}/tools/decode_lab_shader.py
                VERBATIM)
            set(SEVEL_SHADER_OUTPUTS ${SEVEL_SHADER_OUTPUTS} ${output} PARENT_SCOPE)
        endfunction()
        sevel_restore_shader(engine_sim.vertex.spv 9d61d719d3366b118158fb14c2325ca0ef4b1c38e57f7306b0f1c590e7d09c8b)
        sevel_restore_shader(engine_sim.fragment.spv 4215c56147a961db40eaf6919bbe0179832710760f4f296c4ba509ebcfc05416)
        sevel_restore_shader(engine_sim.vertex.dxil ce436be92359fbd138f83e6bcac54cabdcbf3cb7c160137966faa585f46bb856)
        sevel_restore_shader(engine_sim.fragment.dxil 98d403c25debde264e1d813eaed13c52b077a445cced82ba29cb0f770b5fe0bc)
        add_custom_target(sevel-lab-shaders DEPENDS ${SEVEL_SHADER_OUTPUTS})
        add_dependencies(sevel-ma17-lab sevel-lab-shaders)
        add_library(open-engine-sim-gpu STATIC
            third_party/open-engine-sim/src/sdl_gpu_renderer.cpp)
        target_include_directories(open-engine-sim-gpu SYSTEM PUBLIC
            ${CMAKE_CURRENT_SOURCE_DIR}/third_party/open-engine-sim/include)
        target_link_libraries(open-engine-sim-gpu PUBLIC SDL3::SDL3)
        if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
            target_compile_options(open-engine-sim-gpu PRIVATE -Wno-error)
        endif()
        target_sources(sevel-ma17-lab PRIVATE
            apps/sevel-ma17-lab/SdlDisplay.cpp
            src/lab/DonorScene.cpp
            src/lab/FontRenderer.cpp
            src/lab/LabInstruments.cpp
            src/lab/LiveAudio.cpp
            src/lab/MeshAsset.cpp)
        target_link_libraries(sevel-ma17-lab PRIVATE open-engine-sim-gpu
            SDL3::SDL3 ZLIB::ZLIB
            Freetype::Freetype)
        if(UNIX AND NOT APPLE)
            get_target_property(SEVEL_SDL3_TYPE SDL3::SDL3 TYPE)
            if(SEVEL_SDL3_TYPE STREQUAL "SHARED_LIBRARY")
                set_property(TARGET sevel-ma17-lab APPEND PROPERTY
                    BUILD_RPATH "$ORIGIN")
                add_custom_command(TARGET sevel-ma17-lab POST_BUILD
                    COMMAND ${CMAKE_COMMAND} -E copy_if_different
                        $<TARGET_FILE:SDL3::SDL3>
                        $<TARGET_FILE_DIR:sevel-ma17-lab>/$<TARGET_SONAME_FILE_NAME:SDL3::SDL3>
                    VERBATIM)
            endif()
        endif()
        target_compile_definitions(sevel-ma17-lab PRIVATE SEVEL_LAB_SDL3=1)
        find_package(PNG QUIET)
        if(PNG_FOUND)
            target_link_libraries(sevel-ma17-lab PRIVATE PNG::PNG)
            target_compile_definitions(sevel-ma17-lab PRIVATE SEVEL_LAB_PNG=1)
            if(ENABLE_TESTS)
                find_program(SEVEL_XVFB_RUN xvfb-run)
                if(SEVEL_XVFB_RUN)
                    add_test(NAME LabSession.GuiAudioFrameDeterminism
                        COMMAND python3
                            ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_mode_determinism.py
                            $<TARGET_FILE:sevel-ma17-lab>
                            ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                            ${CMAKE_CURRENT_SOURCE_DIR}/tests/data/lab_control_replay.txt
                            ${SEVEL_XVFB_RUN}
                            ${CMAKE_CURRENT_BINARY_DIR})
                    add_test(NAME LabCapture.SdlSoftwarePng
                        COMMAND ${SEVEL_XVFB_RUN} -a
                            $<TARGET_FILE:sevel-ma17-lab>
                            ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                            --capture-tick 1485000 --window-frames 2
                            --screenshot ${CMAKE_CURRENT_BINARY_DIR}/sevel-window.png)
                    add_test(NAME LabSession.BenchPreset
                        COMMAND ${Python3_EXECUTABLE}
                            ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_bench_preset.py
                            $<TARGET_FILE:sevel-ma17-lab>
                            ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                            ${SEVEL_XVFB_RUN} ${CMAKE_CURRENT_BINARY_DIR})
                    set_tests_properties(LabSession.BenchPreset PROPERTIES TIMEOUT 120)
                    add_test(NAME LabAudio.LiveDummyStream
                        COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_live_audio.py
                            ${SEVEL_XVFB_RUN} $<TARGET_FILE:sevel-ma17-lab>
                            ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                            ${CMAKE_CURRENT_BINARY_DIR}/sevel-live-audio.png)
                    add_test(NAME LabCapture.GpuPreviewFallback
                        COMMAND ${Python3_EXECUTABLE}
                            ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_gpu_preview.py
                            ${SEVEL_XVFB_RUN} $<TARGET_FILE:sevel-ma17-lab>
                            ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                            ${CMAKE_CURRENT_BINARY_DIR}/sevel-gpu-preview.png)
                    add_test(NAME LabCapture.GpuOffscreen
                        COMMAND ${Python3_EXECUTABLE}
                            ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_gpu_offscreen.py
                            $<TARGET_FILE:sevel-ma17-lab>
                            ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
                    set_tests_properties(LabCapture.GpuOffscreen
                        PROPERTIES SKIP_RETURN_CODE 77 TIMEOUT 30)
                    add_test(NAME LabKline.LivePtyFaultQuery
                        COMMAND ${Python3_EXECUTABLE}
                            ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_kline_live.py
                            ${SEVEL_XVFB_RUN} $<TARGET_FILE:sevel-ma17-lab>
                            ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
                    set_tests_properties(LabKline.LivePtyFaultQuery
                        PROPERTIES TIMEOUT 60)
                    find_program(SEVEL_XDOTOOL xdotool)
                    if(SEVEL_XDOTOOL)
                        add_test(NAME LabCapture.F12Live
                            COMMAND ${SEVEL_XVFB_RUN} -a python3
                                ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_f12_capture.py
                                $<TARGET_FILE:sevel-ma17-lab>
                                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
                        set_tests_properties(LabCapture.F12Live PROPERTIES TIMEOUT 30)
                        add_test(NAME LabControls.ManualBenchStart
                            COMMAND ${SEVEL_XVFB_RUN} -a python3
                                ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_manual_bench_start.py
                                $<TARGET_FILE:sevel-ma17-lab>
                                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                                ${CMAKE_CURRENT_BINARY_DIR})
                        set_tests_properties(LabControls.ManualBenchStart
                            PROPERTIES TIMEOUT 60)
                        add_test(NAME LabControls.MouseButtonBar
                            COMMAND ${SEVEL_XVFB_RUN} -a python3
                                ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_mouse_controls.py
                                $<TARGET_FILE:sevel-ma17-lab>
                                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                                ${CMAKE_CURRENT_BINARY_DIR}/sevel-mouse-controls.txt)
                        set_tests_properties(LabControls.MouseButtonBar
                            PROPERTIES TIMEOUT 30)
                        add_test(NAME LabControls.ReplayLocksMouse
                            COMMAND ${SEVEL_XVFB_RUN} -a python3
                                ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_replay_mouse_lock.py
                                $<TARGET_FILE:sevel-ma17-lab>
                                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                                ${CMAKE_CURRENT_SOURCE_DIR}/tests/data/lab_control_replay.txt
                                ${CMAKE_CURRENT_BINARY_DIR}/sevel-replay-mouse-controls.txt)
                        set_tests_properties(LabControls.ReplayLocksMouse
                            PROPERTIES TIMEOUT 30)
                        add_test(NAME LabCapture.ResizedButtonBar
                            COMMAND ${SEVEL_XVFB_RUN} -a python3
                                ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_resized_capture.py
                                $<TARGET_FILE:sevel-ma17-lab>
                                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                                ${CMAKE_CURRENT_BINARY_DIR}/sevel-resized-window.png)
                        set_tests_properties(LabCapture.ResizedButtonBar
                            PROPERTIES TIMEOUT 30)
                        foreach(SEVEL_LAYOUT_SIZE IN ITEMS "1920;1080" "3440;1440")
                            list(GET SEVEL_LAYOUT_SIZE 0 SEVEL_LAYOUT_WIDTH)
                            list(GET SEVEL_LAYOUT_SIZE 1 SEVEL_LAYOUT_HEIGHT)
                            add_test(NAME LabCapture.Layout${SEVEL_LAYOUT_WIDTH}x${SEVEL_LAYOUT_HEIGHT}
                                COMMAND ${SEVEL_XVFB_RUN} -a -s "-screen 0 3600x1600x24"
                                    python3 ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_resized_capture.py
                                    $<TARGET_FILE:sevel-ma17-lab>
                                    ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                                    ${CMAKE_CURRENT_BINARY_DIR}/sevel-${SEVEL_LAYOUT_WIDTH}x${SEVEL_LAYOUT_HEIGHT}.png
                                    ${SEVEL_LAYOUT_WIDTH} ${SEVEL_LAYOUT_HEIGHT})
                            set_tests_properties(LabCapture.Layout${SEVEL_LAYOUT_WIDTH}x${SEVEL_LAYOUT_HEIGHT}
                                PROPERTIES TIMEOUT 90)
                        endforeach()
                        add_test(NAME LabCapture.Radial1920x1080
                            COMMAND ${SEVEL_XVFB_RUN} -a -s "-screen 0 1920x1080x24"
                                python3 ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_resized_capture.py
                                $<TARGET_FILE:sevel-ma17-lab>
                                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                                ${CMAKE_CURRENT_BINARY_DIR}/sevel-radial-1920x1080.png
                                1920 1080 radial)
                        set_tests_properties(LabCapture.Radial1920x1080
                            PROPERTIES TIMEOUT 90)
                        add_test(NAME LabCapture.Radial3440x1440
                            COMMAND ${SEVEL_XVFB_RUN} -a -s "-screen 0 3600x1600x24"
                                python3 ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_resized_capture.py
                                $<TARGET_FILE:sevel-ma17-lab>
                                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                                ${CMAKE_CURRENT_BINARY_DIR}/sevel-radial-3440x1440.png
                                3440 1440 radial)
                        set_tests_properties(LabCapture.Radial3440x1440
                            PROPERTIES TIMEOUT 90)
                        add_test(NAME LabCapture.PhysicalMotion
                            COMMAND ${SEVEL_XVFB_RUN} -a
                                python3 ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_physical_motion.py
                                $<TARGET_FILE:sevel-ma17-lab>
                                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
                        set_tests_properties(LabCapture.PhysicalMotion
                            PROPERTIES TIMEOUT 90)
                        foreach(SEVEL_AXIAL_PAIR IN ITEMS "14;1920;1080" "23;3440;1440")
                            list(GET SEVEL_AXIAL_PAIR 0 SEVEL_PAIR_LABEL)
                            list(GET SEVEL_AXIAL_PAIR 1 SEVEL_AXIAL_WIDTH)
                            list(GET SEVEL_AXIAL_PAIR 2 SEVEL_AXIAL_HEIGHT)
                            add_test(NAME LabCapture.Axial${SEVEL_PAIR_LABEL}
                                COMMAND ${SEVEL_XVFB_RUN} -a -s "-screen 0 3600x1600x24"
                                    python3 ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_resized_capture.py
                                    $<TARGET_FILE:sevel-ma17-lab>
                                    ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                                    ${CMAKE_CURRENT_BINARY_DIR}/sevel-axial-${SEVEL_PAIR_LABEL}.png
                                    ${SEVEL_AXIAL_WIDTH} ${SEVEL_AXIAL_HEIGHT}
                                    axial-${SEVEL_PAIR_LABEL})
                            set_tests_properties(LabCapture.Axial${SEVEL_PAIR_LABEL}
                                PROPERTIES TIMEOUT 90)
                        endforeach()
                        add_test(NAME LabControls.RadialViewMouse
                            COMMAND ${SEVEL_XVFB_RUN} -a -s "-screen 0 1920x1080x24"
                                python3 ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_resized_capture.py
                                $<TARGET_FILE:sevel-ma17-lab>
                                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                                ${CMAKE_CURRENT_BINARY_DIR}/sevel-radial-mouse.png
                                1920 1080 radial-click)
                        set_tests_properties(LabControls.RadialViewMouse
                            PROPERTIES TIMEOUT 90)
                        add_test(NAME LabControls.RadialViewMouseDefault
                            COMMAND ${SEVEL_XVFB_RUN} -a -s "-screen 0 1280x720x24"
                                python3 ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_resized_capture.py
                                $<TARGET_FILE:sevel-ma17-lab>
                                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                                ${CMAKE_CURRENT_BINARY_DIR}/sevel-radial-1280x720.png
                                1280 720 radial-click)
                        set_tests_properties(LabControls.RadialViewMouseDefault
                            PROPERTIES TIMEOUT 90)
                        add_test(NAME LabControls.RadialViewMouseCompact
                            COMMAND ${SEVEL_XVFB_RUN} -a -s "-screen 0 1024x768x24"
                                python3 ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_resized_capture.py
                                $<TARGET_FILE:sevel-ma17-lab>
                                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                                ${CMAKE_CURRENT_BINARY_DIR}/sevel-radial-mouse-compact.png
                                900 620 radial-click)
                        set_tests_properties(LabControls.RadialViewMouseCompact
                            PROPERTIES TIMEOUT 90)
                    endif()
                endif()
            endif()
        endif()
        if(ENABLE_TESTS)
            add_executable(lab_live_audio_smoke
                tests/lab_live_audio_smoke.cpp src/lab/LiveAudio.cpp
                src/lab/StreamingAudio.cpp src/lab/SimSession.cpp)
            target_include_directories(lab_live_audio_smoke SYSTEM PRIVATE
                ${CMAKE_CURRENT_SOURCE_DIR}/third_party/open-engine-sim/include)
            target_link_libraries(lab_live_audio_smoke PRIVATE
                emu8051-tty_lib open-engine-sim-audio SDL3::SDL3)
            add_test(NAME LabAudio.PauseSpeedAndKey
                COMMAND lab_live_audio_smoke
                    ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
            set_tests_properties(LabAudio.PauseSpeedAndKey PROPERTIES
                ENVIRONMENT "SDL_AUDIODRIVER=dummy")
        endif()
    endif()
    if(ENABLE_TESTS)
        add_executable(lab_session_smoke tests/lab_session_smoke.cpp
            src/lab/SimSession.cpp)
        target_link_libraries(lab_session_smoke PRIVATE emu8051-tty_lib)
        add_test(NAME LabSession.PauseAndControls
            COMMAND lab_session_smoke
                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
        add_executable(lab_live_determinism
            tests/lab_live_determinism.cpp src/lab/SimSession.cpp)
        target_link_libraries(lab_live_determinism PRIVATE emu8051-tty_lib)
        add_test(NAME LabSession.WarmScenarioDeterminism
            COMMAND lab_live_determinism
                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
        add_executable(lab_control_replay
            tests/lab_control_replay.cpp src/lab/SimSession.cpp)
        target_link_libraries(lab_control_replay PRIVATE emu8051-tty_lib)
        add_test(NAME LabSession.ControlReplay
            COMMAND lab_control_replay
                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin)
        add_executable(lab_audio_smoke tests/lab_audio_smoke.cpp
            src/lab/AcousticAdapter.cpp src/lab/StreamingAudio.cpp
            src/lab/WavWriter.cpp)
        target_link_libraries(lab_audio_smoke PRIVATE open-engine-sim-audio)
        add_test(NAME LabAudio.EventDrivenWav
            COMMAND lab_audio_smoke
                ${CMAKE_CURRENT_BINARY_DIR}/sevel-audio-smoke.wav)
        add_test(NAME LabAudio.OriginalRomScenarios
            COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_audio_scenarios.py
                $<TARGET_FILE:sevel-ma17-lab>
                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                ${CMAKE_CURRENT_SOURCE_DIR}/tests/data/lab_key_off_controls.txt
                ${CMAKE_CURRENT_BINARY_DIR})
        add_test(NAME LabCapture.OriginalRomSvg
            COMMAND sevel-ma17-lab
                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                --headless --capture-tick 1485000
                --capture-svg ${CMAKE_CURRENT_BINARY_DIR}/sevel-capture.svg)
        add_test(NAME LabSession.HeadlessControlReplay
            COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lab_control_trace.py
                $<TARGET_FILE:sevel-ma17-lab>
                ${CMAKE_CURRENT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin
                ${CMAKE_CURRENT_SOURCE_DIR}/tests/data/lab_control_replay.txt
                ${CMAKE_CURRENT_BINARY_DIR})
    endif()
endif()

# Precompiled headers disabled for now due to complexity with mixed C/C++ code
# if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.16" AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/include/stdafx.hpp")
#     target_precompile_headers(emu8051-tty_lib PRIVATE "$<$<COMPILE_LANGUAGE:CXX>:include/stdafx.hpp>")
#     target_precompile_headers(emu8051-tty REUSE_FROM emu8051-tty_lib)
#     message(STATUS "Precompiled headers enabled for C++ files")
# endif()

if(ENABLE_TESTS AND GTest_FOUND)
    add_subdirectory(tests)
endif()
