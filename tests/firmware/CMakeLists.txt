# Host build for the SmartCoaster pure-logic layers (no ESP-IDF required).
#
#   cmake -S tests/firmware -B /tmp/scoaster-host
#   cmake --build /tmp/scoaster-host -j
#   ctest --test-dir /tmp/scoaster-host --output-on-failure
#
# The ESP-IDF Linux target is intentionally not used: the pure layers are
# plain C11 and build with the system compiler, which keeps the loop fast and
# lets the same sources be diffed against the Python reference model.
cmake_minimum_required(VERSION 3.16)
project(smartcoaster_host_tests C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

get_filename_component(FW_MAIN "${CMAKE_CURRENT_SOURCE_DIR}/../../firmware/esp32/main" ABSOLUTE)

set(CORE_SOURCES
    ${FW_MAIN}/core_types.c
    ${FW_MAIN}/weight_process.c
    ${FW_MAIN}/intake.c
    ${FW_MAIN}/reminder.c
    ${FW_MAIN}/hydration.c
    ${FW_MAIN}/ui.c
    ${FW_MAIN}/weight_sensor.c
    ${FW_MAIN}/hx711_mock.c
)

add_library(coaster_core STATIC ${CORE_SOURCES})
target_include_directories(coaster_core PUBLIC ${FW_MAIN})
if(NOT MSVC)
    target_compile_options(coaster_core PRIVATE -Wall -Wextra -Werror)
endif()

function(add_host_test name source)
    add_executable(${name} ${source})
    target_link_libraries(${name} PRIVATE coaster_core m)
    if(NOT MSVC)
        target_compile_options(${name} PRIVATE -Wall -Wextra -Werror)
    endif()
    add_test(NAME ${name} COMMAND ${name})
endfunction()

# The 11 firmware/model scenarios, ported to C asserts.
add_host_test(host_core_test host_core_test.c)
# HX711 mock: noise / drift / saturation / quantisation / lifecycle.
add_host_test(host_mock_test host_mock_test.c)
# stdin/stdout driver used by differential.py.
add_executable(host_core_cli host_core_cli.c)
target_link_libraries(host_core_cli PRIVATE coaster_core m)
target_compile_options(host_core_cli PRIVATE -Wall -Wextra -Werror)

enable_testing()
