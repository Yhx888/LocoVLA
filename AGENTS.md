# Upkie MuJoCo 运动控制课程

## 语言规范
- 永远说中文，包括代码注释和提交信息也用中文。

## 项目概述
- 零基础入门运动控制与 VLA（Vision-Language-Action）的课程项目。
- 以 Upkie 双腿轮足机器人 + MuJoCo 仿真为核心教学载体。
- 默认环境：Windows + Python 3.11 + MuJoCo，本地仿真，不接真实硬件。
- `archive/v1-current-learning/` 是 v1 历史快照，仅用于参考，不在其中新增功能。

## 目录结构

```
├── assets/           # 机器人模型（MJCF/URDF）
├── cpp/              # C++ 控制库（Eigen + CMake + CTest）
├── dashboard/        # 课程前端
│   ├── app.py        # Streamlit 实验台仪表盘
│   └── web/          # React + Vite + TypeScript 前端（含 Three.js 3D 可视化、KaTeX、Mermaid）
├── diagrams/         # 课程 SVG/PNG 图表（按时间戳子目录组织）
├── configs/          # 配置文件
│   ├── control/      # 控制器配置（PD、LQR）
│   ├── course/       # 课程配置（manifest.json）
│   ├── env/          # 环境配置（standing、velocity）
│   ├── randomization/# 随机化配置
│   ├── rl/           # 强化学习配置（PPO）
│   └── robot/        # 机器人配置（upkie.json）
├── docs/             # 文档
│   ├── analysis/     # 项目分析（课程差距、问题、优化总结等）
│   └── guides/       # 操作指南（依赖安装、Git 操作等）
├── outputs/          # 输出（不提交 Git 的工作产物）
│   ├── checkpoints/  # 训练模型
│   ├── experiments/  # 实验证据（meta.json + 日志 + 结果）
│   ├── logs/         # 训练日志
│   ├── model_audit/  # 模型审计报告
│   ├── plots/        # 图表
│   ├── progress/     # 学习进度存档
│   ├── tensorboard/  # TensorBoard 日志
│   └── videos/       # 录像
├── ros2_ws/          # ROS2 工作空间（WSL2 环境）
├── scripts/          # 入口脚本
│   ├── git/          # Git 工作流辅助脚本
│   ├── tools/        # 工具脚本（飞书同步等）
│   └── *.py          # 课程章节入口（00-47 + 工程/毕业/VLA/HW）
├── src/              # 核心代码库
│   └── upkie_mujoco_course/
│       ├── sim/              # 仿真：加载、运行、可视化
│       ├── model/            # 模型：关节/执行器/传感器映射
│       ├── controllers/      # 控制器：PD、LQR、残差
│       ├── classical_control/# 经典控制器实现
│       ├── envs/             # 环境：Gymnasium 接口
│       ├── rewards/          # 奖励函数
│       ├── randomization/    # 域随机化
│       ├── rl/               # 强化学习训练/评估
│       ├── commands/         # 高层指令接口
│       ├── course/           # 课程清单与进度管理
│       ├── estimation/       # 状态估计
│       ├── engineering/      # 工程工具
│       ├── foundations/      # 基础模块
│       ├── hardware/         # 硬件接口
│       ├── vla/              # VLA 模型接口
│       ├── capstone/         # 综合项目
│       ├── web/              # 课程 Web 后端：FastAPI + 内容服务
│       └── utils/            # 工具函数
├── tests/            # 测试（55 个 .py 文件）
├── tutorials/        # 教程（v2/ 下 00-47 + H01-H10，共 58 关）
└── archive/          # 历史版本
```

## 课程章节（V2）

课程清单唯一权威来源：`configs/course/manifest.json`（版本 0.3.0）。以下为阶段摘要，先修关系、验收条件和完成状态以 manifest 为准。

| 阶段 | 编号 | 主题 | 毕业项目 |
|------|------|------|----------|
| 0 | 00-05 | 数学与工具 | 手算与代码验证倒立摆基础模型 |
| 1 | 06-11 | 机器人仿真 | 建立物理正确的 Upkie MuJoCo 数字样机 |
| 2 | 12-18 | 经典控制 | PD、LQR 与速度控制对比实验 |
| 3 | 19-24 | 状态估计与优化 | 带噪声状态估计与受约束 MPC |
| 4 | 25-31 | 学习控制 | 可复现的 PPO 与残差控制基准 |
| 5 | 32-37 | 应用型 VLA | 语言条件视觉导航与稳定停车 |
| 6 | 38-43 | 工程部署 | 将控制链路迁移到 C++ 与 ROS2 |
| 7 | 44-47 | 岗位毕业项目 | 完整具身控制系统与岗位级作品集 |
| H | H01-H10 | 硬件选修 | 复刻并改进桌面轮足平衡机器人 |

- 章节入口脚本：`scripts/run_foundation_lab.py`、`scripts/run_classical_control_lab.py`、`scripts/run_estimation_optimization_lab.py`、`scripts/run_rl_lab.py`、`scripts/run_vla_lab.py`、`scripts/run_trajectory_optimization_lab.py`、`scripts/run_engineering_lab.py` 等
- 课程 Web 入口：`scripts/run_course_web.py`（FastAPI 后端 + React 前端）
- 验收入口：`scripts/course_checkpoint.py --chapter <编号>`
- v1 历史脚本（`scripts/01_check_model.py` 等）仍可运行，仅作旧版参考

## 教程写作规范

教程内容写作必须遵循 `docs/guides/tutorial-writing-spec.md`，该规范定义了 8 种内容类型（公式推导、概念定义、架构描述、代码分析、操作验证、对比分析、参数调优、问答检测）各自的讲解框架和自检清单。

- **核心原则**：小白原则——只学过高中数学就能独立理解
- **公式类**：七层递进（直觉→拆解→物理→动机→推导→算例→类比）
- **概念类**：四步框架（大白话定义→拆解字母→Upkie实例→为什么有用）
- **架构类**：五要素 + **画板强制**
- **代码类**：三步分析法（整体流程→代码+注解→关键行讲解）
- 修改或新增教程内容前，先确定内容类型，再按对应框架组织内容，最后运行自检清单。

## 模型参数

当前 Upkie v2 模型（权威配置：`configs/robot/upkie.json`）：
- `nq=13, nv=12, nu=6`，根部为真实自由基座 `root`；无控制时允许位移和跌倒。
- 关节：left_hip、left_knee、left_wheel、right_hip、right_knee、right_wheel。
- 执行器：4 个腿部位置执行器（单位 `rad`）+ 2 个轮端力矩执行器（单位 `N*m`，范围 `[-1.0, 1.0]`）。轮端不再使用速度控制语义。
- 传感器和替换模型字段以 `sensor_contract` 为准；修改模型后先运行 `python scripts/11_model_contract_lab.py`，再同步教程和飞书事实。

## 开发规范

- 代码简洁，避免过度封装。
- 优先让教程可运行，再优化算法。
- 复杂逻辑放入 `src/`，`scripts/` 只做入口。
- 路径统一用 `pathlib.Path`，不要写死绝对路径。
- 修改模型后必须同步更新所有教程文档和飞书文档。

## 安全规则

- 禁止批量删除文件或目录。
- 不使用 `del /s`、`rd /s`、`rmdir /s`、`Remove-Item -Recurse`、`rm -rf`。
- 不确定模型字段时先运行模型审计，不要猜。
- 保持所有脚本可从本目录根路径运行。

## 实验约定

- 所有自动化实验必须指定 `--seed`（默认 0）和 `--no-viewer`（headless）
- 结果输出到 `outputs/experiments/`：配置、Git commit、seed、指标、日志、图表
- 固定 seed 实验必须可复现；不可复现的不计入课程证据
- 验收判定由 `pytest` 测试文件给出，不做人工放宽阈值
- 作业产物不得隐藏失败、夸大效果或绕过通过条件

## 注意事项

- 项目根有两个 Python 环境：`.venv`（主力，Windows）和 `.venv-wsl`（WSL2 专用），不要混用
- `ros2_ws/` 只在 WSL2 中构建和运行，Windows 侧无法直接使用
- C++ 构建产物在 `cpp/build/`
- `archive/v1-current-learning/` 仅作历史参考，不在其中新增功能
- 修改模型后必须运行 `python scripts/11_model_contract_lab.py` 并同步教程和飞书文档

## 常用命令

```powershell
# 环境激活
.\.venv\Scripts\Activate.ps1

# 运行测试
pytest

# 模型审计
python scripts/01_check_model.py

# 训练（示例）
python scripts/06_train_ppo_standing.py --total-timesteps 1000

# 评估
python scripts/08_eval_policy.py --episodes 1

# Dashboard 实验台
streamlit run dashboard/app.py

# 课程 Web（含 React 前端，自动打开浏览器）
.\start.ps1

# VLA 链路
python scripts/35_generate_vla_demos.py --episodes 1 --max-steps 50
python scripts/36_train_behavior_cloning.py
python scripts/37_eval_vla.py --max-steps 5000 --seed 0

# 工程 Lab（38-47）
python scripts/run_engineering_lab.py --chapter 38

# 关卡验收（生成证据 + 运行测试）
python scripts/course_checkpoint.py --chapter 19 --seed 0

# C++ 构建与测试
cd cpp; cmake -B build; cmake --build build; ctest --test-dir build

# Dashboard 前端构建
cd dashboard/web; npm install; npm run build
```
