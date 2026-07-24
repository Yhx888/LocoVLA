"""残差控制器接口。

残差 RL 的核心思想：不从零开始学控制，而是在已有控制器的基础上做微调。

公式：u_final = u_classic + scale * u_rl

- u_classic：传统控制器（如 PD/LQR）的输出，提供基本的稳定性
- u_rl：强化学习策略的输出，负责补偿传统控制器的不足
- scale：残差缩放因子（0~1），限制 RL 的修正幅度，防止破坏稳定性

这种架构的好处：
1. 不需要 RL 从零学起，训练更快
2. 传统控制器保证基本安全，RL 负责优化
3. scale 控制 RL 的影响范围，便于调试
"""

from __future__ import annotations

import numpy as np


class ResidualController:
    """叠加、缩放并限幅经典控制与学习残差。"""

    def __init__(self, scale: float, low: np.ndarray, high: np.ndarray):
        self.scale = float(scale)
        self.low = np.asarray(low, dtype=float)
        self.high = np.asarray(high, dtype=float)

    def compute(self, base_action: np.ndarray, residual_action: np.ndarray) -> np.ndarray:
        combined = add_residual_action(base_action, residual_action, self.scale)
        return np.clip(combined, self.low, self.high)


def add_residual_action(base_action: np.ndarray, residual_action: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """将 RL 残差叠加到传统控制器输出上。

    Args:
        base_action: 传统控制器输出（如 PD/LQR 的力矩命令）
        residual_action: RL 策略输出的修正量
        scale: 残差缩放因子，越小 RL 影响越小（推荐 0.01~0.5）

    Returns:
        最终控制输出 = base_action + scale * residual_action
    """
    return np.asarray(base_action, dtype=float) + float(scale) * np.asarray(residual_action, dtype=float)
