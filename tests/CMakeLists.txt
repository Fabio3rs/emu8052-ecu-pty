add_executable(emu8051-tty_tests test.cpp)
target_compile_definitions(emu8051-tty_tests PRIVATE
    MA17_ROM_PATH="${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin")
target_link_libraries(emu8051-tty_tests emu8051-tty_lib GTest::GTest GTest::Main)
gtest_discover_tests(emu8051-tty_tests)
