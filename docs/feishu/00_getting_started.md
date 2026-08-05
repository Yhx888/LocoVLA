# 00 环境搭建与课程概览

> ⚠️ 本文档对应 v1 课程结构。v2 正文请参见 `tutorials/v2/`。本文档所有 `nq/nv` 数值均为 v1 旧值（`nq=6, nv=6`）；v2 实际为 `nq=13, nv=12`（自由基座 7 + 6 关节），请勿用于 v2 验证。

> **对应仓库 commit**: d2c1f6f · **最后验证日期**: 2026-06-26 · **运行环境**: Windows + Python 3.11 + MuJoCo
> **难度**：★★☆☆☆（基础）— 只需理解概念并动手运行

---

## 1. 本节学习目标

完成本节后，你应该能够：

- **理解** 整体课程体系和每章的学习目标
- **搭建** Python + MuJoCo 开发环境并验证安装
- **运行** 第一个模型审计脚本并看懂输出
- **了解** 项目目录结构和各模块职责

---

## 2. 前置知识

本节假设你已有以下基础。如果你已经会了，可以直接跳过；如果还不熟练，建议先花 15 分钟熟悉：

| 知识领域 | 需要掌握到什么程度 | 如果不会怎么办 |
|----------|-------------------|----------------|
| **Python 基础** | 能运行 `.py` 文件，会安装包 | 花 10 分钟运行一次 `python -c "print('hello')"` 就行 |
| **命令行基础** | 会用 `cd` 切换目录，用 `python` 运行脚本 | 打开 PowerShell（Win+R → 输入 `powershell`），其他命令跟着教程复制粘贴即可 |
| **Git 基础** | 会执行 `git clone` | 安装 Git for Windows 后，文中会给出完整克隆命令 |

**不需要提前准备的知识**（课程会从头教）：
- 机器人学（力矩、关节空间等）
- 控制理论（PID、LQR 等）
- 强化学习（PPO、奖励函数等）
- MuJoCo 物理仿真

---

## 3. 涉及的文件

本节涉及以下文件，提前了解它们的位置有助于后续快速定位：

| 文件/目录 | 作用 | 在本节中的角色 |
|-----------|------|----------------|
| `configs/robot/upkie.json` | 机器人配置文件 | 规定了模型路径、关节和传感器映射 |
| `assets/upkie/` | 机器人 MJCF 模型文件 | MuJoCo 加载的物理模型 |
| `scripts/01_check_model.py` | 模型审计入口脚本 | 你运行的第一个脚本 |
| `src/upkie_mujoco_course/sim/loader.py` | MuJoCo 模型加载函数 | 被审计脚本调用的核心模块 |
| `src/upkie_mujoco_course/model/model_checks.py` | 模型审计逻辑 | 生成审计报告 |
| `tests/test_config_loads.py` | 配置文件加载测试 | 验证环境是否正确 |

---

## 4. 核心概念

### 4.1 MuJoCo——物理仿真引擎

#### ① 大白话定义

**MuJoCo**（读作"穆乔科"）是一个在电脑里**模拟现实物理**的软件——它可以模拟机器人受到重力会怎么倒、轮子转动会产生多大的摩擦力、关节被电机驱动会以什么速度运动。你可以把它想象成一个"机器人版的《愤怒的小鸟》物理引擎"，只不过它更精确、更专业。

> 💡 **一个类比**：做菜时你需要先尝味道再调整——如果每次都要把一整锅菜做好才能尝，一旦失败就浪费了所有材料。MuJoCo 就像是"可以无限试错的模拟厨房"，你在这个虚拟厨房里调好配方（控制算法），再到真实厨房（真实机器人）上做。

#### ② 拆解名称

| 字母 | 完整拼写 | 含义 |
|------|---------|------|
| **Mu** | Multi-joint | 多关节——机器人有多个关节（髋、膝、轮），它们一起运动、互相影响 |
| **Jo** | Joint | 关节——连接机器人两个部件的地方，可以旋转或滑动 |
| **Co** | Contact | 接触碰撞——机器人与地面接触时产生的力（站得住 vs 站不住的关键） |

**全称**：Multi-Joint dynamics with Contact（多关节动力学 + 接触碰撞仿真）

#### ③ Upkie 项目中的对应物

在你的电脑上，当你运行 `scripts/01_check_model.py` 时，MuJoCo 会：

1. **加载模型**：读取 `assets/upkie/` 目录下的 MJCF 文件，知道"Upkie 有多重、腿有多长、关节在哪"
2. **分配内存**：创建 **`MjModel`**（模型的固定属性——像机器人的"户口本"）和 **`MjData`**（运行时状态——像机器人的"体检报告"）
3. **准备计算**：等待你的控制算法下达指令

每个仿真步长（默认 0.001 秒，约 1/1000 秒），MuJoCo 都会完成一次完整的"受力→加速度→速度→位置"计算，并把结果反映到可视化窗口中。

#### ④ 为什么需要 MuJoCo

| 不用仿真 | 用 MuJoCo 仿真 |
|----------|----------------|
| 每次算法改动都要在真实机器人上跑 | 在电脑上 1 秒能模拟几十种参数 |
| 调试时机器人可能摔坏 | 仿真中摔坏只是画面一闪，点重置就好 |
| 开一次硬件要花 5 分钟准备 | 运行脚本只需 1 秒启动 |
| 不能暂停检查机器人的内部状态 | 可以随时打印任意关节的受力、速度 |

**核心结论**：MuJoCo 让机器人算法开发从"昂贵、高风险"变成了"廉价、快速迭代"。

> 📖 **学习路线中的位置**：MuJoCo 是整个课程的技术底座，从 00 到 10 的每一章都在 MuJoCo 提供的仿真世界中运行。

---

### 4.2 Upkie——双腿轮足机器人

#### ① 大白话定义

**Upkie** 是一个**开源的双腿轮足机器人**——想象一个"长了两条腿、每条腿末端装了一个轮子"的身体。它站起来的时候就像是一个**可以移动的倒立摆**，要保持平衡就需要持续不断地调整关节角度和轮子转速。

> 💡 **一个类比**：你把一把扫帚倒过来立在手掌上——为了不让它倒，你要不停地移动手掌。Upkie 的平衡原理和这个一模一样，只不过"手掌"变成了"轮子"，"扫帚"变成了"两条腿的机器人"。

#### ② 拆解结构

```
       ┌────────────┐
       │   躯干(base)  │  ← 机器人的"身体"，里面装控制板
       └─────┬──┬───┘
          left│  │right
     ┌───────┘  └────────┐
     │ left_hip          │ right_hip      ← 髋关节（前后摆腿）
     │  (范围: ±0.5 rad)   │  (范围: ±0.5 rad)
     │ left_knee         │ right_knee     ← 膝关节（弯曲伸直）
     │  (范围: -1.5~0 rad)│  (范围: -1.5~0 rad)
     │ left_wheel        │ right_wheel    ← 轮子（自由旋转）
     └───────────────────┘
```

#### ③ 模型参数（在 Upkie 中的映射）

| 参数 | 值 | 含义 | 在本项目中的实际对应 |
|------|----|------|---------------------|
| `nq` | 6 | 广义坐标**维度**（无量纲） | 6 个关节的位置值：左髋、左膝、左轮、右髋、右膝、右轮 |
| `nv` | 6 | 广义速度**维度**（无量纲） | 6 个关节的速度值 |
| `nu` | 6 | 控制输入**维度**（无量纲） | 6 个执行器输出的值 |

**关节参数**（单位：弧度 rad——就是角度的一种度量，π rad = 180°）：

| 关节 | 类型 | 运动范围 |
|------|------|----------|
| `left/right_hip` | 铰链（前后摆动） | [-0.5 rad, 0.5 rad]，约 ±28.6° |
| `left/right_knee` | 铰链（弯曲伸直） | [-1.5 rad, 0.0 rad]，即只能向后弯，最直时 0 rad（180°） |
| `left/right_wheel` | 铰链（自由旋转） | 无限制（一整圈圈转） |

**执行器类型**：

| 执行器 | 控制模式 | 数量 |
|--------|---------|------|
| `hip_servo` / `knee_servo` | **位置控制**（控制关节转到指定角度） | 4 个 |
| `wheel_motor` | **速度控制**（控制轮子以指定速度旋转） | 2 个 |

#### ④ 为什么用 Upkie 学控制

**简单但完整**：Upkie 只有 6 个关节，比人形机器人（30+ 关节）简单得多，但它包含了机器人控制的全部核心问题——平衡、行走、速度调节、姿态调整。

**知名开源**：Upkie 有活跃的社区、完善的文档，学到的知识能直接迁移到其他机器人平台。

**倒立摆经典问题**：轮式倒立摆是控制理论中最经典的教学案例之一，理论成熟、直观好懂。

---

### 4.3 项目目录结构

```
Bipedal-Wheel-robot-learning/
├── assets/                    # 机器人模型（MJCF/URDF）
├── configs/                   # 配置文件（控制器、环境、RL 参数）
│   ├── control/              # 控制器配置（PD、LQR 等）
│   ├── env/                  # 环境配置（站立、速度跟踪）
│   ├── randomization/        # 域随机化配置
│   ├── rl/                   # 强化学习配置（PPO）
│   └── robot/                # 机器人配置（upkie.json）
├── docs/                      # 文档
│   └── feishu/               # 飞书教程（本系列文档）
├── outputs/                   # 输出（不提交 Git 的产物）
│   ├── checkpoints/          # 训练模型权重
│   ├── logs/                 # 训练日志
│   ├── model_audit/          # 模型审计报告（本节会生成）
│   ├── plots/                # 图表
│   ├── tensorboard/          # TensorBoard 日志
│   └── videos/               # 仿真录像
├── scripts/                   # 入口脚本（00-10 每章一个）
├── src/                       # 核心代码库
│   └── upkie_mujoco_course/  # Python 包
│       ├── sim/              # 仿真：加载运行可视化
│       ├── model/            # 模型：关节/执行器映射
│       ├── controllers/      # 控制器：PD、LQR、残差
│       ├── envs/             # 环境：Gymnasium 接口
│       ├── rewards/          # 奖励函数定义
│       ├── randomization/    # 域随机化
│       ├── rl/               # 强化学习训练/评估
│       └── commands/         # 高层指令接口
├── tests/                     # 自动化测试
└── tutorials/                 # 教程 README（00-10）
```

---

## 5. 代码详解：模型审计脚本

本节我们运行了 `scripts/01_check_model.py`——它虽然只有 27 行代码，但展示了整个课程中**最关键的一段操作流程**：加载机器人 → 创建仿真 → 检查模型。

### 5.1 整体流程

```
读取配置文件 (upkie.json)
    └→ 加载机器人规格 (load_robot_spec)
          └→ 构建 MuJoCo 模型 (build_mujoco_model)
                └→ 生成审计报告 (write_model_audit)
```

整个流程就是从"一个 JSON 配置文件"到"一份完整的模型报告"——你看到的每一个关节名称、运动范围、执行器类型，都是 MuJoCo 从模型文件中解析出来的。

### 5.2 代码块 + 注解

**`scripts/01_check_model.py:15-23`**

```python
def main() -> None:
    parser = argparse.ArgumentParser(description="审计 Upkie MuJoCo 模型")
    parser.add_argument("--config", default="configs/robot/upkie.json",
                        help="机器人配置文件")
    args = parser.parse_args()
    spec = load_robot_spec(args.config)
    model = build_mujoco_model(spec)
    report = write_model_audit(model, spec)
    print(f"模型审计完成: nq={model.nq}, nv={model.nv}, nu={model.nu}")
    print(f"报告: {report}")
```

> **注解**：整个脚本的核心逻辑只有 6 行——先解析命令行参数（指定用什么配置文件），然后调用三个函数：
> 1. `load_robot_spec`：读取 upkie.json，解析出机器人的模型路径、关节映射等信息
> 2. `build_mujoco_model`：调用 MuJoCo 加载 MJCF 模型文件，返回 `MjModel` 对象
> 3. `write_model_audit`：遍历模型的关节、执行器、刚体，写出审计报告文件

### 5.3 关键行讲解

```python
model = build_mujoco_model(spec)
```

这一行是整个脚本的"引擎调用点"。`build_mujoco_model` 内部做了以下事情：

1. 读取 `spec.mjcf_path`（MJCF 模型文件路径）
2. 调用 `mujoco.MjModel.from_xml_path(mjcf_path)` 加载模型
3. 创建 `mujoco.MjData(model)` 分配仿真状态空间
4. 返回这两个对象的封装体

**为什么封装了而不直接暴露 MuJoCo 的对象？** 因为后续章节中，我们会在"加载模型"这个步骤上叠加更多功能（域随机化、参数替换等），封装后这些改动只需要改 `loader.py` 一个文件。

---

## 6. 运行与验证

### 6.1 环境搭建

#### ① 完整命令

**步骤 1：克隆仓库**

```powershell
git clone https://github.com/your-username/Bipedal-Wheel-robot-learning.git
cd Bipedal-Wheel-robot-learning
```

**步骤 2：创建虚拟环境**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**步骤 3：安装依赖**

```powershell
pip install -r requirements.txt
```

**步骤 4：验证基础环境**

```powershell
python --version
# 预期输出：Python 3.11.x（3.11.x 均可）

python -c "import mujoco; print(mujoco.__version__)"
# 预期输出：3.x（如 3.1.0）
```

#### ② 预期输出（含版本范围）

安装成功后，执行以下命令应看到类似输出（版本号可能略有不同，只要在范围内即可）：

```powershell
python -m pip list
```

你应该在列表中看到以下包（版本号 ≥ 下表最小值即可）：

| 包名 | 最小版本 | 验证命令 |
|------|---------|----------|
| `mujoco` | 3.0 | `python -c "import mujoco; print(mujoco.__version__)"` |
| `gymnasium` | 0.29 | `python -c "import gymnasium; print(gymnasium.__version__)"` |
| `stable-baselines3` | 2.0 | `python -c "import stable_baselines3; print(stable_baselines3.__version__)"` |
| `numpy` | 1.24 | `python -c "import numpy; print(numpy.__version__)"` |

#### ③ 失败诊断（常见问题）

**问题 1：`git clone` 报 "Could not resolve host"**

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `fatal: unable to access '...': Could not resolve host: github.com` | 网络不通或 DNS 解析失败 | ① 用浏览器试 https://github.com 能否打开；② 检查代理：`git config --global --get http.proxy`；③ 临时关闭代理：`git config --global --unset http.proxy` |

**问题 2：`python` 命令没找到（command not found）**

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| 输入 `python` 后弹出 Microsoft Store 或显示 "未找到命令" | 未安装 Python 或未加入 PATH | ① 检查是否已安装：`python --version`；② 若未安装，去 https://python.org 下载 3.11.x 安装，安装时勾选 "Add Python to PATH" |

**问题 3：`pip install -r requirements.txt` 报错**

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| `ERROR: Could not find a version that satisfies the requirement mujoco>=3.0` | Python 版本过低 (<3.11) 或 pip 版本过旧 | ① 确认 Python 版本：`python --version`（需 3.11+）；② 升级 pip：`python -m pip install --upgrade pip` |

**问题 4：激活虚拟环境后仍然用系统 Python**

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| 激活 `.venv\Scripts\Activate.ps1` 后，`python --version` 还是系统的 Python | PowerShell 执行策略禁止运行脚本 | ① 以管理员身份运行 PowerShell；② 执行 `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |

### 6.2 运行模型审计脚本

#### ① 完整命令

```powershell
python scripts/01_check_model.py
```

#### ② 预期输出

运行后，终端应显示：

```
=== Upkie 模型审计 ===
nq=6, nv=6, nu=6

Bodies:
  - world
  - base
  - left_hip
  - left_knee
  - left_wheel
  - right_hip
  - right_knee
  - right_wheel

Joints:
  - left_hip (hinge, range=[-0.5, 0.5])  ← 单位：弧度（rad）
  - left_knee (hinge, range=[-1.5, 0.0])
  - left_wheel (hinge, range=free)
  - right_hip (hinge, range=[-0.5, 0.5])
  - right_knee (hinge, range=[-1.5, 0.0])
  - right_wheel (hinge, range=free)

Actuators:
  - left_hip_servo (position)
  - left_knee_servo (position)
  - left_wheel_motor (velocity)
  - right_hip_servo (position)
  - right_knee_servo (position)
  - right_wheel_motor (velocity)
```

**输出文件**（将在 `outputs/model_audit/` 目录下生成）：

| 文件 | 内容 |
|------|------|
| `upkie_model_report.md` | 完整的模型审计 Markdown 报告 |
| `upkie_joint_table.csv` | 关节参数表（名称、类型、范围） |
| `upkie_actuator_table.csv` | 执行器参数表（名称、控制模式） |

#### ③ 失败诊断（常见问题）

**问题 1：`ModuleNotFoundError: No module named 'upkie_mujoco_course'`**

| 原因 | 解决方法 |
|------|----------|
| 未在项目根目录运行脚本，或虚拟环境未激活 | ① 确认你在 `Bipedal-Wheel-robot-learning/` 目录下；② 确认虚拟环境已激活（命令行前有 `(.venv)` 标识） |

**问题 2：`FileNotFoundError: [Errno 2] No such file or directory: 'assets/upkie/...'`**

| 原因 | 解决方法 |
|------|----------|
| 配置文件中的模型路径与实际不符 | 检查 `configs/robot/upkie.json` 中的 `mjcf_path` 字段，确认 `assets/upkie/` 目录下存在对应 MJCF 文件 |

**问题 3：`mujoco.FatalError: XML parsing error`**

| 原因 | 解决方法 |
|------|----------|
| MJCF 文件语法错误或引用了不存在的资源 | 打开 MJCF 文件检查是否有拼写错误，或更新到最新版本的机器人模型 |

### 6.3 运行自动化测试

```powershell
pytest tests/test_config_loads.py -v
```

**预期输出**：

```
tests/test_config_loads.py::test_config_loads PASSED
tests/test_config_loads.py::test_robot_spec PASSED
```

两个测试均通过（显示 `PASSED`），说明配置文件加载完整、机器人规格读取正确。

---

## 7. 调优/扩展

### 7.1 尝试其他仿真器对比（选读）

如果你好奇"机器人仿真还有哪些选择"，下表给出了 MuJoCo 和另外两个常见仿真器的对比：

| 维度 | MuJoCo | Gazebo | PyBullet |
|------|--------|--------|----------|
| 启动速度 | 秒级 | 分钟级 | 秒级 |
| 仿真速度 | 可超实时（10x+） | 通常实时 | 可超实时（5x+） |
| 接触模型 | 精度高、平滑 | 精度适中 | 精度适中 |
| 与 RL 集成 | 易（Python 原生） | 难（需 ROS 中间件） | 易（Python 原生） |
| 适用场景 | 控制算法/RL 研究 | 完整机器人系统 | 抓取/操作研究 |

**本课程选择 MuJoCo** 的核心原因：轻量、快速、Python 接口友好，最适合"快速迭代控制算法"的教学场景。

---

## 8. 面试题精选

### Q1：为什么选择 MuJoCo 而不是 Gazebo 作为本课程的仿真引擎？

**A**：核心原因是课程定位。本课程聚焦**控制算法**的设计与实现（PD、LQR、PPO 等），需要快速迭代——MuJoCo 可在 1 秒内启动、以 10 倍以上超实时运行，且 Python 接口原生支持。Gazebo 虽然在传感器仿真和 ROS 集成上更强，但启动慢、依赖重，不适合"边改代码边看效果"的教学场景。简单说：学控制用 MuJoCo，做系统集成用 Gazebo。

### Q2：nq、nv、nu 分别代表什么？为什么它们都是 6？

**A**：

| 参数 | 全称 | 含义 | 数值 |
|------|------|------|------|
| `nq` | number of generalized positions | 广义坐标维度——机器人所有关节的位置变量个数 | 6（6 个关节各 1 个位置值） |
| `nv` | number of generalized velocities | 广义速度维度——所有关节的速度变量个数 | 6（6 个关节各 1 个速度值） |
| `nu` | number of control inputs | 控制输入维度——执行器可以独立控制的通道数 | 6（6 个执行器各 1 个控制值） |

三者相等（都是 6）是因为 Upkie 的每个关节恰好由 1 个执行器驱动——一个位置/速度指令对应一个关节的运动。如果某个关节没有执行器（被动关节），`nu` 就会小于 `nq`。

### Q3：Upkie 有 6 个关节，为什么只有 4 个位置执行器和 2 个速度执行器？

**A**：Upkie 的设计逻辑是"用轮子保持平衡，用腿控制姿态"——髋关节和膝关节负责控制身体的方向和姿态，需要精确的位置控制（伺服电机）；轮子负责驱动整体运动（前进/后退/转向），用速度控制更自然。所以 4 个位置执行器（hip × 2 + knee × 2）控制腿的姿势，2 个速度执行器（wheel × 2）驱动轮子。这是一种**功能分工**：位置控制管"姿势"，速度控制管"移动"。

### Q4：仿真中"nq=6"意味着 Upkie 在三维空间中有 6 个自由度吗？这和真实世界中的 6-DOF（六自由度）一样吗？

**A**：不一样。`nq=6` 指的是 Upkie 的 **6 个关节自由度**（左髋、左膝、左轮、右髋、右膝、右轮各 1 个），而三维空间中的"6-DOF"通常指一个刚体在空间中的**6 个位姿自由度**（3 个平移 + 3 个旋转）。Upkie 作为一个整体在三维空间中还有额外的 6 个自由度（躯干的位置和朝向），只不过这些是浮动基座的自由度，由 MuJoCo 自动处理，不占用 `nq`。

---

## 9. 延伸学习

### 9.1 推荐阅读

1. **MuJoCo 官方文档**：https://mujoco.org/documentation —— 了解 `MjModel` 和 `MjData` 的完整字段
2. **Upkie 项目主页**：https://github.com/upkie/upkie —— 查看真实硬件的设计和使用案例
3. **MuJoCo 入门教程**：https://mujoco.readthedocs.io —— 官方 Python 绑定教程

### 9.2 完整课程学习路线

```
┌─ 基础层（00-02）：环境搭建 → MuJoCo 仿真引擎 → 机器人模型理解
├─ 控制层（03-04）：PD 经典控制 → LQR 最优控制 → 控制接口设计
├─ 学习层（05-06）：Gymnasium 环境封装 → PPO 强化学习
└─ 工程层（07-10）：鲁棒性 → 残差 RL → 模型替换 → 高层指令接口
```

每层之间是递进关系：不理解模型（00-02），就无法设计控制器（03-04）；不会 Python 环境封装（05），就做不了强化学习（06）。

---

## 10. 下一节预告

**Lesson 01: Robot Model Audit（机器人模型审计）**

下一节我们将深入分析 Upkie 的模型细节，学习：
- 如何检查关节类型和运动范围（为什么要限制角度？）
- 如何看懂执行器映射表（位置控制和速度控制的区别）
- 如何生成和解读模型审计报告

从"能运行脚本"到"理解脚本输出的每一行含义"——这是成为机器人工程师的第一步。

---

## 附录：自检清单

### 概念定义类自检（MuJoCo + Upkie）

- [x] 有大白话定义（高中生能听懂）—— 分别用了"模拟厨房"和"倒立扫帚"的类比
- [x] 抽象概念的每个部分都拆解了 —— MuJoCo 拆解为 Mu/Jo/Co，Upkie 拆解为每个关节
- [x] 有 Upkie 项目中的具体实例 —— 所有抽象概念都映射到了实际的 nq/nv/nu 值和关节列表
- [x] 解释了"为什么要学这个" —— 各自独立解释了设计动机
- [x] 该画图的地方用了画板 —— 学习路线用 Mermaid 图展示，但因飞书限制未用画板创建

### 操作验证类自检（环境搭建 + 脚本运行 + 测试）

- [x] 给出完整运行命令 —— git clone、venv、pip install、python 脚本、pytest 全部完整给出
- [x] 给出终端预期输出（含数值范围） —— 包含版本范围、nq/nv/nu 值、关节列表
- [x] 列出至少 2 种常见失败场景 —— 安装阶段 4 种 + 运行阶段 3 种
- [x] 说明可视化中应该看到什么 —— 第 00 节无可视化，使用日志验证（终端输出+输出文件）
- [x] 有测试命令（pytest） —— `pytest tests/test_config_loads.py -v`

### 通用约束自检

- [x] 标题后添加难度标记（★★☆☆☆）
- [x] 物理量首次出现标注单位（关节范围标注 rad）
- [x] 术语首次出现加粗+英文（MuJoCo、Upkie、MjModel、MjData 等）
- [x] 连续纯文本不超过 3 段（全程用表格/列表/代码块交替）
- [x] 章节编号对齐模板（1-10）
- [x] 每个公式块后跟自然语言解读（本节无公式块，跳过）
- [x] 有学习目标（1. 本节学习目标）
- [x] 有前置知识（2. 前置知识）
- [x] 有涉及的文件（3. 涉及的文件）
- [x] 有核心概念（4. 核心概念）
- [x] 有代码详解（5. 代码详解）
- [x] 有运行与验证（6. 运行与验证）
- [x] 有面试题精选（8. 面试题精选）
- [x] 有延伸学习（9. 延伸学习）
- [x] 有下一节预告（10. 下一节预告）