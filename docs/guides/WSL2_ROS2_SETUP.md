# WSL2 + Ubuntu + ROS2 工程环境

## 环境边界

Windows + Python 3.11 继续承担 MuJoCo 主线。ROS2 阶段使用 WSL2 的 Ubuntu 24.04 与 ROS2 Jazzy，避免把 Windows 原生 ROS2、WSL 网络和仿真依赖混成一个难以复现的环境。Python 3.12 只可用于临时诊断，不生成最终课程证据。

当前机器探测结果：Windows 侧的 CMake、MinGW C++ 编译器和第 38-39 关已完成真实验收。WSL2 的 Ubuntu 24.04.4 LTS 已安装并以版本 2 运行，ROS2 Jazzy 与 `colcon` 已可执行。

首次在 `/mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/ros2_ws` 直接运行 `colcon build --symlink-install` 的真实结果为失败：ament 在生成 stamp 文件时返回 `Operation not permitted`。这是 WSL 对 Windows 挂载盘的写入权限/元数据边界，不是 ROS2 依赖缺失；`ros2_ws/build`、`install` 和 `log` 是失败尝试的残留，不能作为第 40 关通过证据，也不能 `source install/setup.bash`。

## 安装与验收

以管理员 PowerShell 运行：

```powershell
wsl --install -d Ubuntu-24.04
```

重启后在 Ubuntu 中执行：

```bash
sudo apt update
sudo apt install -y build-essential cmake ninja-build libeigen3-dev
cmake -S /mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/cpp -B /tmp/upkie-build -G Ninja
cmake --build /tmp/upkie-build
ctest --test-dir /tmp/upkie-build --output-on-failure
```

安装 ROS2 Jazzy 后，优先把构建、安装与日志目录放到 Linux 家目录，源码仍可保留在 Windows 工作区：

```bash
source /opt/ros/jazzy/setup.bash
cd /mnt/c/HOME/Project/Bipedal-Wheel-robot-learning/ros2_ws
colcon build --symlink-install \
  --build-base ~/upkie-ros2-build/build \
  --install-base ~/upkie-ros2-build/install \
  --log-base ~/upkie-ros2-build/log
source ~/upkie-ros2-build/install/setup.bash
ros2 run upkie_control control_node
```

若该方式仍出现 Windows 挂载盘权限错误，再把仅 `src/` 复制到 Linux 家目录后构建；不要把 WSL 的 `build`、`install` 或 `log` 目录提交回 Windows 工作区。

## 三重验收

- 视觉：`rqt_graph` 能看到 `/imu -> /upkie_control -> /wheel_torque`。
- 日志：10 秒内控制周期平均频率接近 100 Hz，无连续 deadline miss。
- 测试：`ctest` 与 `colcon test` 均为零失败。

常见失败不是“ROS2 坏了”，而是忘记 `source`、WSL 路径包含 Windows 权限差异，或 QoS 与传感器发布端不一致。逐层检查环境、构建、节点、话题，不要跳过根因直接重装。
