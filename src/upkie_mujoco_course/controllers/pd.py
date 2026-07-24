"""PD 控制器。

PD 控制是最基础的反馈控制算法，公式：
    u = Kp * (x_target - x) + Kd * (v_target - v)

- Kp（比例增益）：纠正当前位置偏差，越大响应越快，但过大会振荡
- Kd（微分增益）：抑制振荡，相当于"阻尼"，越大越平稳，但过大会反应迟钝
- limit：输出限幅，防止执行器饱和（电机有最大力矩限制）
"""

from __future__ import annotations

import numpy as np


class PDController:
    """最小 PD 控制器，用于教程解释比例和微分反馈。

    典型用法::

        ctrl = PDController(kp=4.0, kd=0.3, limit=10.0)
        output = ctrl.compute(target_pos, current_pos, target_vel, current_vel)
    """

    def __init__(self, kp: float | np.ndarray, kd: float | np.ndarray, limit: float | np.ndarray | None = None):
        self.kp = np.asarray(kp, dtype=float)
        self.kd = np.asarray(kd, dtype=float)
        self.limit = None if limit is None else np.asarray(limit, dtype=float)

    def compute(
        self,
        target_position: np.ndarray,
        current_position: np.ndarray,
        target_velocity: np.ndarray,
        current_velocity: np.ndarray,
    ) -> np.ndarray:
        """计算 PD 输出：u = Kp*(x_target - x) + Kd*(v_target - v)。

        Args:
            target_position: 目标位置
            current_position: 当前位置
            target_velocity: 目标速度（通常为 0）
            current_velocity: 当前速度

        Returns:
            控制输出（力矩或速度目标）
        """
        # 比例项：纠正位置偏差（偏差越大，输出越大）
        output = self.kp * (np.asarray(target_position) - np.asarray(current_position))
        # 微分项：抑制速度（类似阻尼，防止振荡）
        output += self.kd * (np.asarray(target_velocity) - np.asarray(current_velocity))
        # 限幅：防止输出超出执行器能力范围
        if self.limit is not None:
            output = np.clip(output, -self.limit, self.limit)
        return np.asarray(output, dtype=float)

