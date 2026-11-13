add_executable(emu8051-tty_tests test.cpp adc_simulator_test.cpp cpu_hooks_test.cpp port_controller_test.cpp uart_scheduler_test.cpp xram_access_test.cpp)
target_compile_definitions(emu8051-tty_tests PRIVATE
    MA17_ROM_PATH="${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin")
target_link_libraries(emu8051-tty_tests emu8051-tty_lib GTest::GTest GTest::Main)
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    # Keep legacy firmware fixtures buildable under the project's -Werror.
    set_source_files_properties(test.cpp PROPERTIES COMPILE_OPTIONS
        "-Wno-range-loop-construct;-Wno-conversion;-Wno-sign-conversion;-Wno-dangling-else")
endif()
gtest_discover_tests(emu8051-tty_tests)
