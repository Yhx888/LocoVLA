#!/usr/bin/env bash
# 在 WSL2 中构建并测试 ROS2 工作空间，导出正式日志。
set -o pipefail

ROOT=/mnt/c/HOME/Project/Bipedal-Wheel-robot-learning
LOG="$ROOT/outputs/logs/ros2_build_test_20260723_wsl2.log"
mkdir -p "$ROOT/outputs/logs"

source /opt/ros/jazzy/setup.bash
cd "$ROOT/ros2_ws"

{
  echo "== ROS_DISTRO=$ROS_DISTRO =="
  echo "== src packages =="
  ls src
  echo "== COLCON BUILD =="
  colcon build --symlink-install
  echo "BUILD_EXIT=$?"
  echo "== COLCON TEST =="
  source install/setup.bash
  colcon test --event-handlers console_direct+
  echo "TEST_EXIT=$?"
  echo "== COLCON TEST-RESULT =="
  colcon test-result --all --verbose
  echo "RESULT_EXIT=$?"
} 2>&1 | tee "$LOG"
