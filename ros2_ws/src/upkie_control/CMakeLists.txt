cmake_minimum_required(VERSION 3.8)
project(upkie_control)

# 第 42 关：读取 git 短 hash，注入为编译宏 GIT_COMMIT_HASH，供日志记录使用
# 读取失败（如非 git 仓库）时兜底为 "unknown"，源码侧亦有 #ifndef 兜底
execute_process(
  COMMAND git rev-parse --short HEAD
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  OUTPUT_VARIABLE GIT_COMMIT_HASH
  OUTPUT_STRIP_TRAILING_WHITESPACE
  ERROR_QUIET
)
if(NOT GIT_COMMIT_HASH)
  set(GIT_COMMIT_HASH "unknown")
endif()
add_definitions(-DGIT_COMMIT_HASH="${GIT_COMMIT_HASH}")

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)

# 核心数学库（无 ROS 依赖，可独立单元测试）
# 第 42 关新增 log_contract.cpp（统一日志序列化/校验）
# 第 43 关新增 safety_state_machine.cpp（安全状态机纯函数）
add_library(${PROJECT_NAME}_lib
  src/control_math.cpp
  src/control_node.cpp
  src/log_contract.cpp
  src/safety_state_machine.cpp
)
target_include_directories(${PROJECT_NAME}_lib PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
ament_target_dependencies(${PROJECT_NAME}_lib rclcpp sensor_msgs std_msgs std_srvs)

# 控制节点可执行文件
# 第 43 关：新增 std_srvs（/estop、/arm 服务）依赖
add_executable(control_node src/control_node_main.cpp)
target_link_libraries(control_node ${PROJECT_NAME}_lib)
ament_target_dependencies(control_node rclcpp sensor_msgs std_msgs std_srvs)

install(TARGETS control_node ${PROJECT_NAME}_lib
  DESTINATION lib/${PROJECT_NAME}
)
install(DIRECTORY include/ DESTINATION include)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_control_node test/test_control_node.cpp)
  target_include_directories(test_control_node PRIVATE include)
  target_link_libraries(test_control_node ${PROJECT_NAME}_lib)
  ament_target_dependencies(test_control_node rclcpp sensor_msgs std_msgs std_srvs)

  # 第 42 关：统一日志契约测试
  ament_add_gtest(test_log_contract test/test_log_contract.cpp)
  target_include_directories(test_log_contract PRIVATE include)
  target_link_libraries(test_log_contract ${PROJECT_NAME}_lib)

  # 第 43 关：安全状态机纯函数测试
  ament_add_gtest(test_safety_state_machine test/test_safety_state_machine.cpp)
  target_include_directories(test_safety_state_machine PRIVATE include)
  target_link_libraries(test_safety_state_machine ${PROJECT_NAME}_lib)
endif()

ament_package()
