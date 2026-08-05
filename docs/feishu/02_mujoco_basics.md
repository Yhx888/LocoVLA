# 02 MuJoCo 仿真基础

> ⚠️ 本文档对应 v1 课程结构。v2 正文请参见 `tutorials/v2/`。本文档所有 `nq/nv` 数值均为 v1 旧值（`nq=6, nv=6`）；v2 实际为 `nq=13, nv=12`（自由基座 7 + 6 关节），请勿用于 v2 验证。

> 📗 **难度**：★★★☆☆（进阶）— 需要理解 MuJoCo 数据结构和仿真流程
> 对应仓库 commit: d2c1f6f
> 最后验证日期: 2026-07-03
> 运行环境: Windows + Python 3.11 + MuJoCo

---

## 1. 本节学习目标

完成本节后，你应该能够：

- **理解** MuJoCo 的核心数据结构（MjModel、MjData）
- **掌握** 状态向量（qpos、qvel、ctrl）的含义
- **运行** 仿真步进并读取传感器数据
- **理解** 接触力和约束的概念

---

## 2. 前置知识

开始本节前，建议你已经完成：

- Lesson 01: Robot Model Audit

你需要理解的概念：

- MuJoCo 模型结构
- 基本的物理学知识（位置、速度、力）

---

## 3. 本节涉及的文件

| 文件 | 作用 |
|------|------|
| `scripts/02_mujoco_step_demo.py` | 仿真步进演示脚本 |
| `scripts/00_view_model.py` | 模型可视化脚本 |
| `src/upkie_mujoco_course/sim/` | 仿真模块 |

---

## 4. 核心概念：MuJoCo 数据结构

### 4.1 MjModel vs MjData

MuJoCo 的核心是两个数据结构：

| 结构 | 说明 | 特点 |
|------|------|------|
| `MjModel` | 模型的只读定义 | 包含质量、惯量、关节定义等 |
| `MjData` | 仿真运行时的可变状态 | 包含位置、速度、力等 |

**关系**：
- `MjModel` 定义了"机器人长什么样"
- `MjData` 记录了"机器人现在什么状态"

### 4.2 状态向量

MuJoCo 使用广义坐标描述机器人状态：

**qpos（关节位置）**：
- 维度：nq（本例中 nq=6）
- 含义：每个关节的角度或位置
- 示例：`[left_hip, left_knee, left_wheel, right_hip, right_knee, right_wheel]`

**qvel（关节速度）**：
- 维度：nv（本例中 nv=6）
- 含义：每个关节的角速度或线速度
- 示例：`[left_hip_vel, left_knee_vel, left_wheel_vel, ...]`

**ctrl（控制输入）**：
- 维度：nu（本例中 nu=6）
- 含义：发送给执行器的指令
- 示例：`[left_hip_servo, left_knee_servo, left_wheel_motor, ...]`

### 4.3 状态转移方程

MuJoCo 的仿真步进可以表示为：

$$\mathbf{x}_{t+1} = f(\mathbf{x}_t, \mathbf{u}_t)$$

其中：
- $\mathbf{x}_t = [\mathbf{qpos}_t, \mathbf{qvel}_t]$：当前状态
- $\mathbf{u}_t = \mathbf{ctrl}_t$：控制输入
- $f$：MuJoCo 物理引擎计算的状态转移函数

---

## 5. 代码详解

### 5.1 仿真步进演示

**文件**：`scripts/02_mujoco_step_demo.py`

```python
"""MuJoCo 仿真步进演示。

演示如何加载模型、运行仿真、读取状态。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import mujoco
import numpy as np

from upkie_mujoco_course.sim.loader import load_upkie_model
from upkie_mujoco_course.sim.runner import SimulationRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="MuJoCo 仿真步进演示")
    parser.add_argument("--duration", type=float, default=1.0, help="仿真时长（秒）")
    parser.add_argument("--no-viewer", action="store_true", help="不打开可视化窗口")
    args = parser.parse_args()

    # 创建仿真运行器
    runner = SimulationRunner()

    # 可选：打开可视化
    if not args.no_viewer:
        runner.open_viewer()

    # 重置到蹲姿
    obs = runner.reset("crouch")
    print(f"初始观测 shape: {obs.shape}")
    print(f"初始 qpos: {runner.data.qpos}")
    print(f"初始 qvel: {runner.data.qvel}")

    # 运行仿真
    step_count = 0
    while runner.time < args.duration:
        # 零控制输入（让机器人自由落体）
        action = np.zeros(runner.model.nu)

        # 执行一步仿真
        obs = runner.step(action)
        step_count += 1

        # 每 100 步打印一次状态
        if step_count % 100 == 0:
            print(f"Step {step_count}:")
            print(f"  time={runner.time:.3f}s")
            print(f"  qpos={runner.data.qpos}")
            print(f"  qvel={runner.data.qvel}")

    print(f"\n仿真完成: {step_count} steps, {runner.time:.3f}s")
    runner.close()


if __name__ == "__main__":
    main()
```

### 5.2 SimulationRunner 详解

**文件**：`src/upkie_mujoco_course/sim/runner.py`

```python
"""仿真运行器。"""
from __future__ import annotations

from typing import Any

import mujoco
import numpy as np


class SimulationRunner:
    """MuJoCo 仿真运行器。

    封装 MuJoCo 仿真循环，提供 reset/step/close 接口。
    """

    def __init__(self, config_path: str = "configs/robot/upkie.json"):
        # 加载模型
        self.model = load_upkie_model(config_path)
        self.data = mujoco.MjData(self.model)

        # 创建渲染器（可选）
        self.viewer = None

        # 关节映射
        self.joint_map = build_joint_map(self.model)
        self.actuator_ids = build_actuator_map(self.model)

        # 控制限制
        self.ctrl_low = self.model.actuator_ctrlrange[:, 0]
        self.ctrl_high = self.model.actuator_ctrlrange[:, 1]

    def reset(self, pose: str = "crouch") -> np.ndarray:
        """重置仿真到指定姿态。

        Args:
            pose: 姿态名称（"stand" 或 "crouch"）

        Returns:
            初始观测向量
        """
        # 重置状态
        mujoco.mj_resetData(self.model, self.data)

        # 设置初始姿态
        set_pose(self.model, self.data, pose)

        # 前向运动学，更新位置
        mujoco.mj_forward(self.model, self.data)

        # 返回观测
        return self._get_obs()

    def step(self, action: np.ndarray) -> np.ndarray:
        """执行一步仿真。

        Args:
            action: 控制输入向量

        Returns:
            下一步的观测向量
        """
        # 设置控制输入
        self.data.ctrl[:] = action

        # 执行仿真步进
        mujoco.mj_step(self.model, self.data)

        # 更新渲染器
        if self.viewer is not None:
            self.viewer.sync()

        # 返回观测
        return self._get_obs()

    def _get_obs(self) -> np.ndarray:
        """获取观测向量。

        Returns:
            观测向量（包含 qpos 和 qvel）
        """
        return np.concatenate([self.data.qpos, self.data.qvel])

    def posture_state(self) -> dict[str, float]:
        """获取姿态状态（用于奖励计算）。"""
        # 提取躯干偏角
        pitch = self.data.qpos[1]  # 假设 qpos[1] 是 pitch

        # 计算角速度
        pitch_rate = self.data.qvel[1]

        # 计算前进速度
        forward_velocity = self.data.qvel[0]

        # 检查轮子是否接触地面
        both_wheels_contact = check_wheel_contact(self.model, self.data)

        return {
            "pitch": pitch,
            "pitch_rate": pitch_rate,
            "forward_velocity": forward_velocity,
            "both_wheels_contact": both_wheels_contact,
            "base_height": self.data.qpos[2],
        }

    def close(self):
        """关闭仿真器。"""
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None
```

---

## 6. 运行与验证

### 6.1 运行命令

```powershell
# 基础运行（带可视化）
python scripts/02_mujoco_step_demo.py --duration 1

# 无可视化（快速测试）
python scripts/02_mujoco_step_demo.py --duration 1 --no-viewer

# 长时间仿真
python scripts/02_mujoco_step_demo.py --duration 5 --no-viewer
```

### 6.2 预期输出

```
初始观测 shape: (12,)
初始 qpos: [-0.3 -0.8  0.3  0.3 -0.8  0.3]
初始 qvel: [0. 0. 0. 0. 0. 0.]

Step 100:
  time=0.100s
  qpos=[-0.31 -0.81  0.31  0.31 -0.81  0.31]
  qvel=[-0.01 -0.02  0.01 -0.01 -0.02  0.01]

Step 200:
  time=0.200s
  qpos=[-0.32 -0.82  0.32  0.32 -0.82  0.32]
  qvel=[-0.02 -0.03  0.02 -0.02 -0.03  0.02]

仿真完成: 1000 steps, 1.000s
```

### 6.3 输出文件

- `outputs/` 目录下生成仿真日志

---

## 7. 核心 API 详解

### 7.1 mujoco.mj_step

```python
mujoco.mj_step(model, data)
```

**功能**：执行一步仿真

**内部流程**：
1. 计算外力（重力、接触力）
2. 求解约束（关节限制、接触约束）
3. 积分更新状态（qpos、qvel）

### 7.2 mujoco.mj_forward

```python
mujoco.mj_forward(model, data)
```

**功能**：更新运动学和动力学计算

**用途**：
- 设置初始姿态后调用
- 更新位置、速度、加速度

### 7.3 状态访问

```python
# 读取关节位置
qpos = data.qpos  # shape: (nq,)

# 读取关节速度
qvel = data.qvel  # shape: (nv,)

# 设置控制输入
data.ctrl[:] = action  # shape: (nu,)

# 读取时间
time = data.time
```

---

## 8. 常见问题

| 现象 | 可能原因 | 解决方法 |
|------|----------|----------|
| `mujoco 未安装` | Python 环境问题 | 运行 `pip install -r requirements.txt` |
| `模型加载失败` | MJCF 文件缺失 | 检查 `assets/upkie/` 目录 |
| `仿真结果 NaN` | 数值不稳定 | 检查 timestep 和控制输入 |
| `viewer 打不开` | 渲染问题 | 使用 `--no-viewer` 参数 |

---

## 9. 面试题精选

### Q1：MjModel 和 MjData 的区别是什么？

**A**：
- **MjModel**：模型的只读定义，包含质量、惯量、关节定义等
- **MjData**：仿真运行时的可变状态，包含位置、速度、力等
- **关系**：MjModel 定义"机器人长什么样"，MjData 记录"机器人现在什么状态"

### Q2：qpos、qvel、ctrl 分别代表什么？

**A**：
- **qpos**：关节位置（广义坐标），维度 nq
- **qvel**：关节速度（广义速度），维度 nv
- **ctrl**：控制输入（执行器指令），维度 nu
- **关系**：qpos 和 qvel 描述状态，ctrl 是控制输入

### Q3：MuJoCo 的仿真步进内部做了什么？

**A**：
1. **前向运动学**：计算各 body 的位置和速度
2. **力计算**：重力、接触力、执行器力
3. **约束求解**：关节限制、接触约束
4. **数值积分**：更新 qpos 和 qvel

---

## 10. 延伸学习

### 10.1 进阶主题

1. **接触动力学**：MuJoCo 如何处理接触和碰撞
2. **传感器仿真**：如何读取 IMU、编码器等传感器数据
3. **渲染和可视化**：如何自定义渲染效果

### 10.2 推荐阅读

1. **MuJoCo 文档**：https://mujoco.org/documentation
2. **MuJoCo Python 绑定**：https://mujoco.readthedocs.io

---

## 11. 下一节预告

下一节将学习：
- PD 控制的数学原理
- 轮式倒立摆动力学
- 实现第一个平衡控制器
