# 依赖说明

本文件按"核心运行时依赖 / 开发依赖 / 构建依赖 / C++ 依赖 / ROS2 依赖"五类组织，
覆盖 Python、构建工具、C++ 数学库与 ROS2 包，确保依赖清单可追溯、可复现。

权威来源：

- Python 运行时依赖：`requirements.txt`、`pyproject.toml`
- Python 开发依赖：`requirements-dev.txt`
- 构建工具：`pyproject.toml`、`cpp/CMakeLists.txt`、`ros2_ws/src/upkie_control/CMakeLists.txt`
- C++ 依赖：`cpp/CMakeLists.txt`
- ROS2 依赖：`ros2_ws/src/upkie_control/package.xml`

## 1. 核心运行时依赖（Python）

来源：`requirements.txt` 与 `pyproject.toml`（两者保持同步，共 12 项）。

| 依赖 | 最低版本 | 用途 |
|---|---|---|
| `mujoco` | `>=3.1.0` | 物理仿真引擎，加载 Upkie MJCF 模型并执行动力学积分 |
| `gymnasium` | `>=0.29.0` | 强化学习环境接口（`envs/` 模块基于其 API） |
| `numpy` | `>=1.24.0` | 数值计算（状态向量、增益矩阵、批量统计） |
| `scipy` | `>=1.10.0` | 科学计算（LQR 求解辅助、信号处理） |
| `matplotlib` | `>=3.6.0` | 绘图（训练曲线、时序图、性能直方图） |
| `stable-baselines3` | `>=2.0.0` | 强化学习算法（PPO 训练与评估） |
| `torch` | `>=2.0.0` | 深度学习框架（策略网络后端） |
| `tensorboard` | `>=2.13.0` | 训练日志可视化（`outputs/tensorboard/`） |
| `streamlit` | `>=1.40.0` | 交互式 dashboard（运行时监控与可视化） |
| `plotly` | `>=5.24.0` | 交互式图表（dashboard 中的 3D 轨迹与状态曲线） |
| `imageio` | `>=2.34.0` | 视频帧编码（评估录像 `outputs/videos/`） |
| `imageio-ffmpeg` | `>=0.5.0` | `imageio` 的 ffmpeg 后端，提供 mp4 编码能力 |

Python 版本要求：`>=3.11,<3.12`（`pyproject.toml` 中 `requires-python`）。Python 3.11 是课程唯一权威解释器版本；3.12 可用于临时开发诊断，但不能生成最终依赖锁或验收证据。

`requirements.lock` 由下面的命令在 CPython 3.11 解析，包含直接依赖和全部传递依赖：

```powershell
uv python install 3.11
uv pip compile pyproject.toml --all-extras --python-version 3.11 --python-platform windows --output-file requirements.lock
```

## 2. 开发依赖

来源：`requirements-dev.txt`。

| 依赖 | 最低版本 | 用途 |
|---|---|---|
| `pytest` | `>=8.0` | 单元测试框架（`tests/` 目录共 42+ 个测试文件） |

## 3. 构建依赖

来源：`pyproject.toml`、`cpp/CMakeLists.txt`。

| 依赖 | 版本 | 用途 |
|---|---|---|
| `setuptools` | `>=68` | Python 包构建后端（`pyproject.toml` 中 `build-system.requires`） |
| `wheel` | 任意 | Python wheel 包格式支持 |
| CMake | `>=3.20` | C++ 项目构建（`cpp/CMakeLists.txt`、ROS2 包） |

构建命令：

```powershell
# Python 包
pip install -e .

# C++ 独立项目（不依赖 ROS2）
cmake -S cpp -B cpp/build
cmake --build cpp/build
ctest --test-dir cpp/build
```

## 4. C++ 依赖

来源：`cpp/CMakeLists.txt`。

| 依赖 | 版本 | 用途 |
|---|---|---|
| C++17 | 标准 | `CMAKE_CXX_STANDARD 17`，`CMAKE_CXX_STANDARD_REQUIRED ON` |
| Eigen3 | `3.4` | 线性代数（矩阵运算，`find_package(Eigen3 3.4 CONFIG QUIET NO_MODULE)`） |
| `winmm` | 系统库 | Windows 高分辨率定时器（`if(WIN32) target_link_libraries(realtime_probe PRIVATE winmm)`） |

Eigen3 获取策略：优先使用系统安装版本（`find_package`），若未找到则通过 `FetchContent` 从
`https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.gz` 下载并校验 SHA256。

## 5. ROS2 依赖

来源：`ros2_ws/src/upkie_control/package.xml` 与 `ros2_ws/src/upkie_control/CMakeLists.txt`。

目标环境：WSL2 Ubuntu 24.04 + ROS2 Jazzy（详见 `outputs/portfolio/40/evidence.json`）。

| 依赖 | 类型 | 用途 |
|---|---|---|
| `ament_cmake` | buildtool | ROS2 包构建工具 |
| `rclcpp` | depend | ROS2 C++ 客户端库（节点、订阅者、发布者） |
| `sensor_msgs` | depend | 传感器消息类型（IMU、关节状态） |
| `std_msgs` | depend | 标准消息类型（Header、字符串等） |
| `std_srvs` | depend | 标准服务类型（`/estop`、`/arm` 服务） |
| `ament_cmake_gtest` | test_depend | ROS2 包级别的 gtest 集成（`BUILD_TESTING` 块） |

测试目标（`ros2_ws/src/upkie_control/CMakeLists.txt` 中 `ament_add_gtest`）：

- `test_control_node`：控制节点通信与安全门控测试（14 项 gtest）
- `test_log_contract`：日志契约与 CSV 导出测试（10 项 gtest）
- `test_safety_state_machine`：安全状态机纯函数测试（15 项 gtest）

## 非核心依赖（不引入）

本课程不强制引入以下重量级依赖，以保持本地零基础友好：

- Docker / 容器运行时
- 大模型训练框架（如 `transformers`、`accelerate`）
- 商业化仿真器（如 V-REP、Webots）
- 真实硬件 SDK（如 STM32 HAL、Serial 库）

VLA（Vision-Language-Action）相关接口仅以桩函数形式存在于 `src/upkie_mujoco_course/vla/`，
不引入大模型权重或在线推理依赖。

## 6. 版本锁定（可复现性）

为支持长期可复现性，项目提供 `requirements.lock` 文件，锁定当前已验证的依赖版本组合。

| 文件 | 用途 | 安装命令 |
|---|---|---|
| `requirements.txt` | 开发环境，使用 `>=` 兼容下限 | `pip install -r requirements.txt` |
| `requirements-dev.txt` | 开发工具依赖（pytest、pytest-cov、coverage） | `pip install -r requirements-dev.txt` |
| `requirements.lock` | 精确复现已验证环境，锁定全部直接依赖的精确版本 | `pip install -r requirements.lock` |

### 使用场景

- **开发新功能**：使用 `requirements.txt` + `requirements-dev.txt`，允许版本浮动
- **复现实验结果**：使用 `requirements.lock`，确保依赖版本完全一致
- **CI/CD**：使用 `requirements.lock`，保证构建环境可复现

### 当前已验证版本（2026-07-17）

| 依赖 | 锁定版本 |
|---|---|
| `mujoco` | `3.8.0` |
| `gymnasium` | `1.3.0` |
| `numpy` | `2.4.4` |
| `scipy` | `1.18.0` |
| `matplotlib` | `3.11.0` |
| `stable_baselines3` | `2.9.0` |
| `torch` | `2.13.0` |
| `tensorboard` | `2.21.0` |
| `imageio` | `2.37.3` |
| `imageio-ffmpeg` | `0.6.0` |
| `pytest` | `9.1.1` |
| `pytest-cov` | `7.1.0` |
| `coverage` | `7.15.1` |

> 注意：`streamlit` 和 `plotly` 在当前验证环境中未安装。如需使用 dashboard 功能，请单独安装。
