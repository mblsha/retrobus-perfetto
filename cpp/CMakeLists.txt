cmake_minimum_required(VERSION 3.14)
project(retrobus_perfetto_cpp VERSION 0.1.0 LANGUAGES CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Options
option(BUILD_TESTS "Build unit tests" ON)
option(BUILD_EXAMPLES "Build example programs" ON)

# Find protobuf and its dependencies
find_package(Protobuf REQUIRED)
find_package(absl REQUIRED)

# Header-only library
add_library(retrobus_perfetto INTERFACE)
target_include_directories(retrobus_perfetto INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_link_libraries(retrobus_perfetto INTERFACE
    protobuf::libprotobuf
)
target_compile_features(retrobus_perfetto INTERFACE cxx_std_17)

# Generate protobuf files
set(PROTO_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../proto")
set(PROTO_FILE "${PROTO_PATH}/perfetto.proto")
set(PROTO_OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/proto")

file(MAKE_DIRECTORY ${PROTO_OUT_DIR})

add_custom_command(
    OUTPUT "${PROTO_OUT_DIR}/perfetto.pb.h" "${PROTO_OUT_DIR}/perfetto.pb.cc"
    COMMAND ${PROTOBUF_PROTOC_EXECUTABLE}
    ARGS --cpp_out=${PROTO_OUT_DIR}
         --proto_path=${PROTO_PATH}
         ${PROTO_FILE}
    DEPENDS ${PROTO_FILE}
    COMMENT "Generating protobuf files"
)

# Create a library for the generated protobuf files
add_library(perfetto_proto STATIC
    "${PROTO_OUT_DIR}/perfetto.pb.cc"
    "${PROTO_OUT_DIR}/perfetto.pb.h"
)
target_include_directories(perfetto_proto PUBLIC
    $<BUILD_INTERFACE:${PROTO_OUT_DIR}>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/retrobus/proto>
)
target_link_libraries(perfetto_proto PUBLIC
    protobuf::libprotobuf
    absl::log
    absl::log_internal_check_op
    absl::log_internal_message
    absl::strings
)
set_target_properties(perfetto_proto PROPERTIES
    POSITION_INDEPENDENT_CODE ON
)

# Link protobuf to main library
target_link_libraries(retrobus_perfetto INTERFACE perfetto_proto)

# Examples
if(BUILD_EXAMPLES)
    add_subdirectory(examples)
endif()

# Tests
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Installation
include(GNUInstallDirs)

# Install the generated protobuf library
install(TARGETS perfetto_proto
    EXPORT retrobus_perfetto-targets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(TARGETS retrobus_perfetto
    EXPORT retrobus_perfetto-targets
)

install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

# Also install generated protobuf header
install(FILES "${PROTO_OUT_DIR}/perfetto.pb.h"
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/retrobus/proto
)

install(EXPORT retrobus_perfetto-targets
    FILE retrobus_perfetto-targets.cmake
    NAMESPACE retrobus::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/retrobus_perfetto
)

# Create config file
include(CMakePackageConfigHelpers)
configure_package_config_file(
    "${CMAKE_CURRENT_LIST_DIR}/cmake/retrobus_perfetto-config.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/retrobus_perfetto-config.cmake"
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/retrobus_perfetto
)

write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/retrobus_perfetto-config-version.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/retrobus_perfetto-config.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/retrobus_perfetto-config-version.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/retrobus_perfetto
)