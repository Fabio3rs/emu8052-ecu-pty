add_executable(emu8051-tty_tests test.cpp)
target_link_libraries(emu8051-tty_tests emu8051-tty_lib GTest::GTest GTest::Main)
gtest_discover_tests(emu8051-tty_tests)
