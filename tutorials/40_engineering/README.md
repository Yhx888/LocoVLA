# 40 ROS2 控制节点

## 岗位任务

把 IMU 输入和轮端力矩输出变成可观测的 ROS2 节点，而不是把整个控制系统塞进一个回调函数。

## 接口契约

输入 `/imu` 使用 `sensor_msgs/Imu`，输出 `/wheel_torque` 暂用 `Float64MultiArray`，顺序固定为左轮、右轮，单位固定为 N·m。教学版使用该消息便于观察，岗位挑战应换成带时间戳、单位和安全状态的自定义消息。

控制定时器为 10 ms，即 100 Hz。IMU 回调只更新最新状态；定时器消费快照并发布动作。这样传感器抖动不会直接改变控制频率。

## 验收

```bash
colcon build --symlink-install
source install/setup.bash
ros2 run upkie_control control_node
ros2 topic hz /wheel_torque
ros2 topic echo /wheel_torque --once
```

故意错误：用默认可靠 QoS 订阅高频传感器，再对比 `SensorDataQoS` 下的延迟与丢包。说明“可靠”不等于“实时控制更可靠”。

作品集：节点图、话题频率、消息契约评审。
