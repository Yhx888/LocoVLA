#!/bin/bash
# 频率测试：验证 upkie_control 100Hz 控制周期
set -e

source ~/upkie-ros2-build/install/setup.bash

# 后台启动控制节点
ros2 run upkie_control control_node &
NODE_PID=$!
sleep 1

# 发布 1000 条 IMU 消息（约 10 秒）
for i in $(seq 1 1000); do
  ros2 topic pub --once /imu sensor_msgs/msg/Imu \
    "{header: {stamp: {sec: 0, nanosec: 0}}, orientation: {x: 0.0, y: 0.05, z: 0.0, w: 0.9987}, orientation_covariance: [0.01,0,0,0,0,0,0,0,0], angular_velocity: {x: 0.0, y: 0.1, z: 0.0}, angular_velocity_covariance: [0,0,0,0,0,0,0,0,0], linear_acceleration: {x: 0.0, y: 0.0, z: 9.81}, linear_acceleration_covariance: [0,0,0,0,0,0,0,0,0]}" 2>/dev/null
done

# 频率统计（100 窗口）
ros2 topic hz /wheel_torque --window 100 &
HZ_PID=$!
sleep 12
kill $HZ_PID 2>/dev/null || true

kill $NODE_PID 2>/dev/null || true
wait $NODE_PID 2>/dev/null || true
echo "FREQ_TEST_DONE"
