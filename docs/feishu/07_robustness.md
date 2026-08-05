# 07 鲁棒性与域随机化

> ⚠️ 本文档对应 v1 课程结构。v2 正文请参见 `tutorials/v2/`。

> 📗 **难度**：★★★☆☆（进阶）— 需要理解随机化概念和仿真与现实的差距
> 对应仓库 commit: d2c1f6f
> 最后验证日期: 2026-07-03
> 运行环境: Windows + Python 3.11 + MuJoCo

---

## 1. 本节学习目标

完成本节后，你应该能够：

- **理解** Sim-to-Real Gap 的概念和成因
- **实现** 域随机化技术（传感器噪声、动作延迟、动力学随机化）
- **分析** 随机化对策略鲁棒性的影响
- **设计** 合理的随机化参数

---

## 2. 前置知识

开始本节前，建议你已经完成：

- Lesson 06: Reinforcement Learning

你需要理解的概念：

- 仿真与真实世界的差距
- 随机化的基本思想

---

## 3. 本节涉及的文件

| 文件 | 作用 |
|------|------|
| `src/upkie_mujoco_course/randomization/` | 随机化模块 |
| `configs/randomization/default.json` | 随机化配置 |
| `tests/test_randomization.py` | 随机化测试 |

---

## 4. 核心概念：Sim-to-Real Gap

### 4.1 什么是 Sim-to-Real Gap

**Sim-to-Real Gap**（仿真到现实的差距）是指在仿真环境中训练的策略，直接部署到真实机器人时性能下降的现象。

**成因**：

| 类别 | 仿真 | 真实 |
|------|------|------|
| 动力学 | 理想化模型 | 摩擦、间隙、柔性 |
| 传感器 | 精确读数 | 噪声、延迟、漂移 |
| 执行器 | 理想响应 | 延迟、饱和、非线性 |
| 环境 | 确定性 | 随机扰动 |

### 4.2 域随机化的理论基础

**核心思想**：在仿真中随机化环境参数，使策略学会适应各种变化，从而泛化到真实世界。

**数学表述**：

假设真实环境参数为 $\theta_{real}$，仿真环境参数为 $\theta_{sim}$。

**传统方法**：在固定 $\theta_{sim}$ 上训练策略 $\pi_\theta$

$$\pi^* = \arg\max_\pi \mathbb{E}_{s \sim p_{\theta_{sim}}} \left[ \sum_t \gamma^t R(s_t, a_t) \right]$$

**域随机化**：在随机化的 $\theta_{sim}$ 上训练策略

$$\pi^* = \arg\max_\pi \mathbb{E}_{\theta \sim p(\theta)} \mathbb{E}_{s \sim p_\theta} \left[ \sum_t \gamma^t R(s_t, a_t) \right]$$

**理论保证**：如果随机化范围足够大，包含真实环境参数，策略在真实环境中也能工作。

### 4.3 域随机化类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 动力学随机化 | 物理参数随机化 | 质量、惯量、摩擦系数 |
| 传感器噪声 | 传感器读数添加噪声 | IMU 噪声、编码器噪声 |
| 动作延迟 | 控制指令延迟执行 | 通信延迟、计算延迟 |
| 外部扰动 | 施加随机外力 | 推力、地面不平 |

---

## 5. 代码详解

### 5.1 随机化模块结构

**目录**：`src/upkie_mujoco_course/randomization/`

```python
# randomization/__init__.py
from .dynamics import randomize_dynamics
from .sensors import add_sensor_noise
from .actions import add_action_delay
from .disturbances import apply_disturbance
```

### 5.2 传感器噪声

**文件**：`src/upkie_mujoco_course/randomization/sensors.py`

```python
"""传感器噪声随机化。"""
from __future__ import annotations

import numpy as np


def add_sensor_noise(obs: np.ndarray, noise_std: float = 0.01) -> np.ndarray:
    """给观测添加高斯噪声。

    Args:
        obs: 原始观测
        noise_std: 噪声标准差

    Returns:
        添加噪声后的观测
    """
    noise = np.random.normal(0, noise_std, size=obs.shape)
    return obs + noise
```

**数学表达**：

$$\tilde{o}_t = o_t + \epsilon, \quad \epsilon \sim \mathcal{N}(0, \sigma^2)$$

### 5.3 动作延迟

**文件**：`src/upkie_mujoco_course/randomization/actions.py`

```python
"""动作延迟随机化。"""
from __future__ import annotations

from collections import deque

import numpy as np


class ActionDelay:
    """动作延迟缓冲区。"""

    def __init__(self, max_delay: int = 5):
        self.buffer = deque(maxlen=max_delay)

    def add(self, action: np.ndarray) -> np.ndarray:
        """添加动作到缓冲区，返回延迟后的动作。"""
        self.buffer.append(action.copy())

        # 随机延迟 0 到 max_delay 步
        delay = np.random.randint(0, len(self.buffer))
        return self.buffer[-(delay + 1)]
```

**数学表达**：

$$u_t^{delayed} = u_{t-d}, \quad d \sim \text{Uniform}(0, d_{max})$$

### 5.4 动力学随机化

**文件**：`src/upkie_mujoco_course/randomization/dynamics.py`

```python
"""动力学参数随机化。"""
from __future__ import annotations

import mujoco
import numpy as np


def randomize_dynamics(model: mujoco.MjModel, config: dict) -> None:
    """随机化模型的动力学参数。

    Args:
        model: MuJoCo 模型
        config: 随机化配置
    """
    # 随机化质量
    if "mass_range" in config:
        low, high = config["mass_range"]
        scale = np.random.uniform(low, high)
        model.body_mass[:] *= scale

    # 随机化摩擦系数
    if "friction_range" in config:
        low, high = config["friction_range"]
        model.geom_friction[:, 0] = np.random.uniform(low, high, size=model.ngeom)

    # 随机化阻尼
    if "damping_range" in config:
        low, high = config["damping_range"]
        scale = np.random.uniform(low, high)
        model.dof_damping[:] *= scale
```

### 5.5 外部扰动

**文件**：`src/upkie_mujoco_course/randomization/disturbances.py`

```python
"""外部扰动随机化。"""
from __future__ import annotations

import mujoco
import numpy as np


def apply_disturbance(data: mujoco.MjData, config: dict) -> None:
    """施加随机外部扰动。

    Args:
        data: MuJoCo 数据
        config: 扰动配置
    """
    # 随机推力
    if "push_force_range" in config:
        low, high = config["push_force_range"]
        force = np.random.uniform(low, high, size=3)
        data.xfrc_applied[1, :3] = force  # 施加到 base body
```

---

## 6. 配置文件

**文件**：`configs/randomization/default.json`

```json
{
  "dynamics": {
    "mass_range": [0.8, 1.2],
    "friction_range": [0.5, 1.5],
    "damping_range": [0.8, 1.2]
  },
  "sensors": {
    "noise_std": 0.01
  },
  "actions": {
    "max_delay": 3
  },
  "disturbances": {
    "push_force_range": [-5.0, 5.0],
    "push_probability": 0.01
  }
}
```

**配置说明**：

| 参数 | 含义 | 推荐范围 |
|------|------|----------|
| `mass_range` | 质量缩放范围 | [0.8, 1.2] |
| `friction_range` | 摩擦系数范围 | [0.5, 1.5] |
| `damping_range` | 阻尼缩放范围 | [0.8, 1.2] |
| `noise_std` | 传感器噪声标准差 | 0.001-0.01 |
| `max_delay` | 最大动作延迟步数 | 1-5 |
| `push_force_range` | 推力范围 | [-10, 10] |

---

## 7. 运行与验证

### 7.1 运行测试

```powershell
# 运行随机化测试
pytest tests/test_randomization.py -v

# 运行全部测试
pytest
```

### 7.2 预期输出

```
tests/test_randomization.py::test_sensor_noise PASSED
tests/test_randomization.py::test_action_delay PASSED
tests/test_randomization.py::test_dynamics_randomization PASSED
```

### 7.3 常见失败诊断

| 现象 | 可能原因 | 解决方法 |
|------|----------|----------|
| `ModuleNotFoundError` | Python 找不到 src 目录 | 确认从项目根目录运行 |
| 随机化测试失败 | 随机化参数超出合理范围 | 检查 `configs/randomization/default.json` 中的参数值 |
| 所有测试跳过（skipped） | 缺少依赖 | 确认安装 `pip install -r requirements.txt` |

---

## 8. 随机化调优指南

### 8.1 调优原则

1. **从小到大**：先用小范围随机化，逐渐增大
2. **观察性能**：随机化太强会导致训练困难
3. **平衡鲁棒性和性能**：随机化会降低仿真中的性能，但提高真实世界的鲁棒性

### 8.2 常见问题

| 现象 | 可能原因 | 解决方法 |
|------|----------|----------|
| 训练不收敛 | 随机化太强 | 减小随机化范围 |
| 真实世界性能差 | 随机化不足 | 增大随机化范围 |
| 训练时间长 | 随机化增加复杂度 | 使用 Curriculum Learning |

### 8.3 Curriculum Learning

**思想**：从简单到复杂，逐步增加随机化强度。

**实现**：

```python
def get_randomization_config(epoch: int, total_epochs: int) -> dict:
    """根据训练进度调整随机化强度。"""
    progress = epoch / total_epochs

    return {
        "dynamics": {
            "mass_range": [1.0 - 0.2 * progress, 1.0 + 0.2 * progress],
            "friction_range": [1.0 - 0.5 * progress, 1.0 + 0.5 * progress],
        },
        "sensors": {
            "noise_std": 0.001 + 0.009 * progress,
        },
    }
```

---

## 9. 面试题精选

### 9.1 基础概念题

**Q1：什么是 Sim-to-Real Gap？**

**A**：
- **定义**：仿真环境中训练的策略，直接部署到真实机器人时性能下降的现象
- **成因**：动力学模型不准确、传感器噪声、执行器延迟、环境变化
- **解决方法**：
  1. **域随机化**：在仿真中随机化环境参数
  2. **系统辨识**：提高仿真模型的准确性
  3. **迁移学习**：在真实世界中微调策略

**Q2：域随机化的三个基本类型是什么？**

**A**：
1. **传感器随机化**：在观测值上添加噪声
2. **动作延迟随机化**：随机延迟动作执行
3. **动力学随机化**：改变质量、摩擦力等物理参数

**Q3：为什么随机化太强会导致训练不收敛？**

**A**：
- 随机化范围太大会让环境变化过于剧烈，策略无法找到稳定有效的动作序列
- agent 面对的环境"千变万化"，很难学到通用的应对策略

### 9.2 应用分析题

**Q4：什么是 Curriculum Learning？如何用于域随机化？**

**A**：
- **Curricular Learning**（课程学习）：从简单到复杂，逐步增加任务难度
- **用于域随机化**：在训练初期用小范围随机化（简单），后期用大范围随机化（复杂）
- **好处**：策略先学会基础控制，再逐步适应各种变化

### Q2：域随机化的理论依据是什么？

**A**：
- **核心思想**：如果随机化范围包含真实环境参数，策略在真实环境中也能工作
- **数学表述**：

$$\pi^* = \arg\max_\pi \mathbb{E}_{\theta \sim p(\theta)} \mathbb{E}_{s \sim p_\theta} \left[ \sum_t \gamma^t R(s_t, a_t) \right]$$

- **理论保证**：在足够大的随机化范围内训练，策略具有泛化能力

### Q3：如何选择随机化参数？

**A**：
1. **参考真实数据**：如果有真实机器人数据，根据数据范围设置
2. **从小到大**：先用小范围，逐渐增大
3. **观察性能**：随机化太强会导致训练困难
4. **Curriculum Learning**：从简单到复杂，逐步增加强度

### Q4：域随机化的局限性是什么？

**A**：
1. **计算成本**：随机化增加训练时间
2. **性能损失**：随机化会降低仿真中的最优性能
3. **范围选择**：范围太小无效，太大训练困难
4. **无法补偿**：无法补偿系统辨识的误差

---

## 10. 延伸学习

### 10.1 进阶主题

1. **System Identification**：如何提高仿真模型的准确性
2. **Domain Adaptation**：如何从仿真迁移到真实世界
3. **Sim-to-Real Transfer**：最新的迁移学习方法

### 10.2 推荐阅读

1. **Domain Randomization 论文**：Tobin et al., "Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World" (2017)
2. **Sim-to-Real 综述**：Zhao et al., "Sim-to-Real Transfer in Robotics" (2020)

---

## 11. 下一节预告

下一节将学习：
- 残差 RL（经典控制 + 强化学习融合）
- 如何结合传统控制和学习方法
