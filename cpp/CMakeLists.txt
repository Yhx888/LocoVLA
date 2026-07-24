cmake_minimum_required(VERSION 3.20)
project(upkie_course_control LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Eigen3 3.4 CONFIG QUIET NO_MODULE)

if(NOT TARGET Eigen3::Eigen)
  include(FetchContent)
  set(BUILD_TESTING OFF CACHE BOOL "不构建 Eigen 的第三方测试" FORCE)
  FetchContent_Declare(
    eigen
    URL https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.gz
    URL_HASH SHA256=8586084F71F9BDE545EE7FA6D00288B264A2B7AC3607B974E54D13E7162C1C72
    DOWNLOAD_EXTRACT_TIMESTAMP FALSE
  )
  FetchContent_MakeAvailable(eigen)
endif()

add_library(upkie_course_control src/control.cpp)
option(UPKIE_COURSE_EXPOSE_PUBLIC_HEADERS "向调用方导出控制器公共头文件" ON)
if(UPKIE_COURSE_EXPOSE_PUBLIC_HEADERS)
  target_include_directories(upkie_course_control PUBLIC include)
else()
  target_include_directories(upkie_course_control PRIVATE include)
endif()
target_link_libraries(upkie_course_control PUBLIC Eigen3::Eigen)

add_executable(control_probe tools/control_probe.cpp)
target_link_libraries(control_probe PRIVATE upkie_course_control)

add_executable(realtime_probe tools/realtime_probe.cpp)
target_link_libraries(realtime_probe PRIVATE upkie_course_control)
if(WIN32)
  target_link_libraries(realtime_probe PRIVATE winmm)
endif()

enable_testing()
add_executable(control_test tests/control_test.cpp)
target_link_libraries(control_test PRIVATE upkie_course_control)
add_test(NAME control_test COMMAND control_test)
add_test(NAME realtime_probe_smoke COMMAND realtime_probe --ticks 3 --period-ms 1)
