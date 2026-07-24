# Upkie 具身智能运动控制课程

这是一套以 Upkie 双腿轮足机器人和 MuJoCo 为主线的工程课程。目标不是承诺“看完即可入职”，而是帮助学习者从高中数学与零编程基础出发，逐关建立建模、控制、估计、强化学习、VLA、部署、诊断和技术答辩能力，并用可审查证据判断是否达到岗位门槛。

## 当前建设状态

- 课程清单覆盖 `00-47` 与 `H01-H10`，共 58 关；规划中关卡不会被标记完成。
- 数学与工具 `00-05` 已形成可执行基线：固定 seed 实验会生成统一结果、原始日志、专属图表和作品集索引。
- Upkie v2 为自由基座模型：`nq=13, nv=12, nu=6`，轮端动作语义为 `±1 N*m` 力矩。
- 站立平衡点由质心/轮轴几何审计得到 `0.142420 rad`，观测和奖励使用平衡点误差。
- 最近一次固定实验记录显示：受约束 MPC 的 100 步 MuJoCo 闭环求解率为 100%，预测与实际约束均通过。
- 最近一次训练记录显示：50000 步轮矩 PPO 在 10 个固定回合中 10/10 存活；10000 步残差 PPO 在 `10 N` 配对扰动下比经典基线平均回报高 `4.257`。
- 最近一次第 21 关记录显示：EKF/UKF 相对原始俯仰测量分别改善约 `3.05×/3.19×`，估计闭环 301 步存活。
- 最近一次 BC-VLA 固定三色记录为成功率 100%、碰撞率 0，且停止命令同一步进入安全控制层。以上量化值均须由最终统一源码摘要的 fresh 证据重新确认，不能把旧 JSON 当作当前源码证明。
- C++/Eigen 与 ROS2 工程代码已有 Windows CMake/CTest 和 WSL2/colcon 测试链；本地结果只证明课程工程状态，不代表真人已经完成答辩。
- H01-H10 只链接外部硬件仓库；授权未明确的 CAD、PCB 不复制到课程。

学习者毕业需要仓库外部人工答辩。本仓库只能判定课程工程是否具备可复现实验、测试和作品集入口，不能用自动代码评审替代真人答辩。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
python scripts/01_check_model.py
pytest
```

启动本地工程任务台：

```powershell
streamlit run dashboard/app.py
```

浏览器打开 `http://localhost:8501`。仪表盘读取统一课程清单与 `outputs/` 证据，不以“打开过页面”计算进度。

## 真实实验入口

```powershell
# 经典平衡与速度控制
python scripts/02_run_pd_balancer.py --duration 5 --no-viewer
python scripts/03_run_lqr_balancer.py --duration 5 --no-viewer
python scripts/04_run_velocity_controller.py --target-velocity 0.1 --duration 30 --no-viewer

# PPO 快速链路与评估
python scripts/06_train_ppo_standing.py --total-timesteps 256 --profile smoke --seed 0
python scripts/08_eval_policy.py --mode classic --episodes 1 --seed 0 --record

# VLA 示范、行为克隆和固定测试集
python scripts/35_generate_vla_demos.py --episodes 1 --max-steps 50
python scripts/36_train_behavior_cloning.py
python scripts/37_eval_vla.py --max-steps 5000 --seed 0

# 关卡三重验收；规划中关卡会拒绝完成
python scripts/run_foundation_lab.py --chapter 05 --seed 0
python scripts/course_checkpoint.py --chapter 19
```

## 课程入口

- [课程地图](docs/SYLLABUS.md)
- [v2 课程正文](tutorials/v2/00/README.md)
- [教程写作规范](docs/guides/tutorial-writing-spec.md)
- [WSL2 与 ROS2 环境](docs/guides/WSL2_ROS2_SETUP.md)
- [模型替换指南](docs/guides/MODEL_SWAP_GUIDE.md)

课程正文统一进入 `tutorials/v2/`。

## 证据原则

所有实验结果至少包含配置、Git commit、seed、指标、通过条件、日志和可视化路径。视觉说明发生了什么，日志给出时间与数值，测试负责重复判定。课程不隐藏失败、不夸大算法效果，也不允许通过放宽阈值把未完成章节包装成完成。

公开契约入口：机器人物理配置见 `configs/robot/upkie.json`，课程清单见 `configs/course/manifest.json`，实验结果见 `src/upkie_mujoco_course/course/results.py`，VLA 数据集见 `src/upkie_mujoco_course/vla/contracts.py`，硬件遥测见 `src/upkie_mujoco_course/hardware/telemetry.py`。
