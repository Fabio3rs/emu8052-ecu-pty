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
    add_compile_options(-Wall -Werror -Wextra -Wformat-security -Wconversion -Wsign-conversion -Wno-gnu -Wno-gnu-statement-expression)
elseif (${CMAKE_CXX_COMPILER_ID} STREQUAL "MSVC")
    message(STATUS "Setting MSVC flags")
    add_compile_options(/W4 /WX)
elseif (${CMAKE_CXX_COMPILER_ID} STREQUAL "Clang")
    message(STATUS "Setting Clang flags")
    add_compile_options(-Werror -Weverything -Wno-c++98-compat -Wno-c++98-compat-pedantic -Wno-padded -Wno-global-constructors -Wno-exit-time-destructors -Wno-weak-vtables -Wno-documentation -Wno-documentation-unknown-command -Wno-unsafe-buffer-usage -Wno-unsafe-buffer-usage-in-libc-call -Wno-unused-macros -Wno-c99-designator -Wno-covered-switch-default)
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

# Function to filter out excluded files.
function(filter_out excluded output)
    set(result "")
    foreach(file ${${output}})
        if(NOT "${file}" IN_LIST ${excluded})
            list(APPEND result ${file})
        endif()
    endforeach()
    set(${output} "${result}" PARENT_SCOPE)
endfunction()

# Gather all source files.
file(GLOB_RECURSE SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp")
set(EXCLUDE_FILES "${CMAKE_CURRENT_SOURCE_DIR}/src/main.cpp")
filter_out(EXCLUDE_FILES SOURCES)

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
set_source_files_properties(${EMU8051_SOURCES} PROPERTIES
    COMPILE_FLAGS "-Wno-everything"
)

add_executable(emu8051-tty "src/main.cpp")
target_link_libraries(emu8051-tty emu8051-tty_lib)

# Precompiled headers disabled for now due to complexity with mixed C/C++ code
# if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.16" AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/include/stdafx.hpp")
#     target_precompile_headers(emu8051-tty_lib PRIVATE "$<$<COMPILE_LANGUAGE:CXX>:include/stdafx.hpp>")
#     target_precompile_headers(emu8051-tty REUSE_FROM emu8051-tty_lib)
#     message(STATUS "Precompiled headers enabled for C++ files")
# endif()

if(ENABLE_TESTS AND GTest_FOUND)
    add_subdirectory(tests)
endif()
