include(FetchContent)

# Fetch Catch2
FetchContent_Declare(
    Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG v3.4.0
)
FetchContent_MakeAvailable(Catch2)

# Test executable
add_executable(test_retrobus_perfetto
    test_main.cpp
    test_builder.cpp
)

target_link_libraries(test_retrobus_perfetto PRIVATE
    retrobus_perfetto
    Catch2::Catch2WithMain
)

# Register tests with CTest
include(Catch)
catch_discover_tests(test_retrobus_perfetto)