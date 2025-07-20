# Basic example
add_executable(basic_example basic_example.cpp)
target_link_libraries(basic_example PRIVATE retrobus_perfetto)

# CPU emulator example
add_executable(cpu_emulator_example cpu_emulator_example.cpp)
target_link_libraries(cpu_emulator_example PRIVATE retrobus_perfetto)