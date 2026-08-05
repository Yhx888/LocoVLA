# 08 残差强化学习

> ⚠️ 本文档对应 v1 课程结构。v2 正文请参见 `tutorials/v2/`。

> 📗 **难度**：★★★☆☆（进阶）— 需要理解经典控制和 RL 的融合思路
> 对应仓库 commit: d2c1f6f
> 最后验证日期: 2026-07-03
> 运行环境: Windows + Python 3.11 + MuJoCo

---

## 1. 本节学习目标

完成本节后，你应该能够：

- **理解** 残差 RL 的核心思想和优势
- **实现** 经典控制 + RL 融合的控制器
- **对比** 纯经典控制、纯 RL、残差 RL 的性能
- **分析** 残差 RL 的适用场景

---

## 2. 前置知识

开始本节前，建议你已经完成：

- Lesson 07: Robustness

你需要理解的概念：

- PD/LQR 控制
- 强化学习（PPO）
- 残差学习的思想

---

## 3. 本节涉及的文件

| 文件 | 作用 |
|------|------|
| `src/upkie_mujoco_course/controllers/residual.py` | 残差控制器 |
| `scripts/08_eval_policy.py` | 策略评估脚本 |
| `tests/test_controller_outputs.py` | 控制器输出测试 |

---

## 4. 核心概念：残差 RL

### 4.1 什么是残差 RL

**残差 RL**（Residual RL）是一种将经典控制与强化学习结合的方法：

$$u_{final} = u_{classic} + \alpha \cdot u_{rl}$$

其中：
- $u_{classic}$：经典控制器输出（PD/LQR）
- $u_{rl}$：RL 策略输出
- $\alpha$：残差缩放系数

**核心思想**：
1. **经典控制器**：提供基础的稳定控制
2. **RL 策略**：学习修正经典控制器的误差
3. **残差融合**：结合两者的优势

### 4.2 为什么用残差 RL

**纯经典控制的问题**：
- 需要精确的模型参数
- 无法处理非线性和不确定性
- 调参困难

**纯 RL 的问题**：
- 需要大量训练数据
- 训练不稳定
- 安全性难以保证

**残差 RL 的优势**：
1. **安全性**：经典控制器保证基础稳定性
2. **样本效率**：RL 只需要学习残差，任务更简单
3. **可解释性**：经典控制器提供可解释的基础行为
4. **鲁棒性**：RL 学习补偿模型不确定性

### 4.3 数学原理

**问题定义**：

假设真实系统动力学为：

$$\dot{x} = f(x, u)$$

经典控制器基于简化模型 $\hat{f}$ 设计：

$$u_{classic} = \pi_{classic}(x)$$

残差 RL 学习修正项：

$$u_{rl} = \pi_{rl}(x)$$

最终控制：

$$u_{final} = u_{classic} + \alpha \cdot u_{rl}$$

**优化目标**：

$$\pi_{rl}^* = \arg\max_{\pi_{rl}} \mathbb{E} \left[ \sum_t \gamma^t R(x_t, u_{classic} + \alpha \cdot u_{rl}) \right]$$

---

## 5. 代码详解

### 5.1 残差控制器

**文件**：`src/upkie_mujoco_course/controllers/residual.py`

```python
"""残差控制器。

将经典控制器与 RL 策略结合：
u_final = u_classic + alpha * u_rl
"""
from __future__ import annotations

import numpy as np


class ResidualController:
    """残差控制器。"""

    def __init__(
        self,
        classic_controller,
        rl_policy,
        residual_scale: float = 0.1,
    ):
        """
        Args:
            classic_controller: 经典控制器（PD/LQR）
            rl_policy: RL 策略
            residual_scale: 残差缩放系数 α
        """
        self.classic_controller = classic_controller
        self.rl_policy = rl_policy
        self.residual_scale = residual_scale

    def compute_action(self, state: np.ndarray) -> np.ndarray:
        """计算残差控制输出。

        Args:
            state: 当前状态

        Returns:
            控制输出
        """
        # 经典控制器输出
        u_classic = self.classic_controller.compute(state)

        # RL 策略输出
        u_rl = self.rl_policy.predict(state)[0]

        # 残差融合
        u_final = u_classic + self.residual_scale * u_rl

        return u_final
```

### 5.2 评估脚本

**文件**：`scripts/08_eval_policy.py`

```python
"""策略评估脚本。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.controllers.residual import ResidualController
from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.sim.runner import SimulationRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="评估策略")
    parser.add_argument("--episodes", type=int, default=1, help="评估轮数")
    parser.add_argument("--policy", type=str, default=None, help="RL 策略路径")
    parser.add_argument("--residual-scale", type=float, default=0.1, help="残差缩放系数")
    args = parser.parse_args()

    # 创建经典控制器
    classic_controller = WheelBalancerController()

    # 如果有 RL 策略，创建残差控制器
    if args.policy:
        from stable_baselines3 import PPO
        rl_policy = PPO.load(args.policy)
        controller = ResidualController(
            classic_controller,
            rl_policy,
            residual_scale=args.residual_scale,
        )
    else:
        controller = classic_controller

    # 评估
    runner = SimulationRunner()
    for episode in range(args.episodes):
        obs = runner.reset("crouch")
        total_reward = 0
        steps = 0

        while True:
            action = controller.compute_action(obs)
            obs, reward, terminated, truncated, info = runner.step(action)
            total_reward += reward
            steps += 1

            if terminated or truncated:
                break

        print(f"Episode {episode + 1}: reward={total_reward:.2f}, steps={steps}")

    runner.close()


if __name__ == "__main__":
    main()
```

---

## 6. 运行与验证

### 6.1 运行命令

```powershell
# 只用经典控制器
python scripts/08_eval_policy.py --episodes 1

# 使用残差 RL
python scripts/08_eval_policy.py --episodes 1 --policy outputs/checkpoints/ppo_standing_latest.zip --residual-scale 0.1

# 调整残差缩放
python scripts/08_eval_policy.py --episodes 1 --policy outputs/checkpoints/ppo_standing_latest.zip --residual-scale 0.5
```

### 6.2 预期输出

```
=== 策略评估 ===
Episode 1: reward=95.23, steps=500
Episode 2: reward=92.15, steps=480
Episode 3: reward=97.31, steps=520
平均奖励: 94.90
```

### 6.3 测试验证

```powershell
pytest tests/test_controller_outputs.py -v
```

---

## 7. 对比实验

### 7.1 三种策略对比

| 策略 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 纯经典控制 | 稳定、可解释 | 需要精确模型 | 模型已知、确定性环境 |
| 纯 RL | 适应性强 | 需要大量数据 | 复杂任务、模型未知 |
| 残差 RL | 结合两者优势 | 需要调 α | 模型部分已知、需要鲁棒性 |

### 7.2 实验设计

```python
# 实验 1：纯经典控制
controller_classic = WheelBalancerController()

# 实验 2：纯 RL
controller_rl = PPO.load("ppo_standing.zip")

# 实验 3：残差 RL
controller_residual = ResidualController(
    WheelBalancerController(),
    PPO.load("ppo_standing.zip"),
    residual_scale=0.1,
)
```

### 7.3 结果分析

**预期结果**：
- 纯经典控制：在理想条件下稳定，但对扰动敏感
- 纯 RL：需要大量训练，但适应性强
- 残差 RL：结合两者优势，鲁棒性最好

---

## 8. 参数调优指南

### 8.1 残差缩放系数 α

| α 值 | 效果 | 适用场景 |
|------|------|----------|
| 0.0 | 纯经典控制 | 模型精确、无扰动 |
| 0.1 | 小幅修正 | 轻微不确定性 |
| 0.5 | 中等修正 | 中等不确定性 |
| 1.0 | 完全融合 | 大不确定性 |

### 8.2 调优建议

1. **从小到大**：先用小 α，逐渐增大
2. **观察稳定性**：α 太大会导致不稳定
3. **验证鲁棒性**：在有扰动的环境中测试

---

## 9. 面试题精选

### 9.1 基础概念题

**Q1：残差 RL 的核心思想是什么？**

**A**：
- **核心思想**：将经典控制与 RL 结合，经典控制器提供基础稳定性，RL 学习修正误差
- **数学表达**：$u_{final} = u_{classic} + \alpha \cdot u_{rl}$
- **优势**：结合经典控制的稳定性和 RL 的适应性

**Q2：残差 RL 的公式中 α 代表什么？α=0 和 α=1 分别表示什么？**

**A**：
- α 是**残差缩放系数**（residual scale），控制 RL 修正的幅度
- α = 0：纯经典控制（RL 输出被完全忽略）
- α = 1：完全融合（经典控制 + RL 各贡献一份）

**Q3：为什么残差 RL 比纯 RL 更样本高效？**

**A**：
1. **任务简化**：RL 只需要学习残差，而不是完整的控制策略
2. **基础稳定**：经典控制器提供基础稳定性，减少探索难度
3. **安全探索**：经典控制器保证基础安全，RL 可以更激进地探索

### 9.2 应用分析题

**Q4：如何选择残差缩放系数 α？**

**A**：
1. **从小到大**：先用小 α（如 0.1），逐渐增大
2. **观察稳定性**：α 太大会导致不稳定
3. **验证鲁棒性**：在有扰动的环境中测试
4. **交叉验证**：在不同场景下验证性能

**Q5：残差 RL 的局限性是什么？**

**A**：
1. **调参复杂**：需要调 α 和 RL 超参数
2. **依赖经典控制器**：如果经典控制器太差，RL 难以补偿
3. **计算成本**：需要同时运行经典控制器和 RL 策略

---

## 10. 延伸学习

### 10.1 进阶主题

1. **自适应残差**：根据任务难度动态调整 α
2. **多任务残差**：在多个任务间共享经典控制器
3. **安全约束**：在残差 RL 中添加安全约束

### 10.2 推荐阅读

1. **Residual RL 论文**：Silver et al., "Residual Policy Learning" (2018)
2. **混合控制综述**：Survey on Learning-based Control

---

## 11. 下一节预告

下一节将学习：
- 如何替换机器人模型
- RobotSpec 接口设计
- 模型替换的最佳实践
