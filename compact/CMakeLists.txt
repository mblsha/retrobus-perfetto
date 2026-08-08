cmake_minimum_required(VERSION 3.14)
project(retrobus_compact_trace VERSION 0.4.0 LANGUAGES C CXX)

option(RBCT_BUILD_TESTS "Build compact trace tests" ON)

add_library(retrobus_compact_trace STATIC src/compact_trace.c)
add_library(retrobus::compact_trace ALIAS retrobus_compact_trace)
set_target_properties(retrobus_compact_trace PROPERTIES EXPORT_NAME compact_trace)
target_include_directories(retrobus_compact_trace PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_compile_features(retrobus_compact_trace PUBLIC c_std_99)

add_library(retrobus_compact_trace_cpp INTERFACE)
add_library(retrobus::compact_trace_cpp ALIAS retrobus_compact_trace_cpp)
set_target_properties(retrobus_compact_trace_cpp PROPERTIES EXPORT_NAME compact_trace_cpp)
target_include_directories(retrobus_compact_trace_cpp INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_compile_features(retrobus_compact_trace_cpp INTERFACE cxx_std_17)
target_link_libraries(retrobus_compact_trace_cpp INTERFACE retrobus_compact_trace)

if(RBCT_BUILD_TESTS)
    enable_testing()
    add_executable(test_compact_trace_c tests/test_compact_trace.c)
    target_link_libraries(test_compact_trace_c PRIVATE retrobus_compact_trace)
    add_test(NAME compact_trace_c COMMAND test_compact_trace_c)

    add_executable(test_compact_trace_cpp tests/test_compact_trace_cpp.cpp)
    target_link_libraries(test_compact_trace_cpp PRIVATE retrobus_compact_trace_cpp)
    add_test(NAME compact_trace_cpp COMMAND test_compact_trace_cpp)
endif()

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
install(TARGETS retrobus_compact_trace retrobus_compact_trace_cpp
        EXPORT retrobus_compact_trace-targets)
install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(EXPORT retrobus_compact_trace-targets
        FILE retrobus_compact_trace-targets.cmake
        NAMESPACE retrobus::
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/retrobus_compact_trace)
configure_package_config_file(
    cmake/retrobus_compact_trace-config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/retrobus_compact_trace-config.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/retrobus_compact_trace
)
write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/retrobus_compact_trace-config-version.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)
install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/retrobus_compact_trace-config.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/retrobus_compact_trace-config-version.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/retrobus_compact_trace
)
