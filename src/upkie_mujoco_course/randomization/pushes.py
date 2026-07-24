"""外力扰动占位。"""

from __future__ import annotations

import numpy as np


def push_vector(force: float, direction: tuple[float, float, float] = (1.0, 0.0, 0.0)) -> np.ndarray:
    direction_array = np.asarray(direction, dtype=float)
    norm = np.linalg.norm(direction_array)
    if norm <= 1e-12:
        return np.zeros(3)
    return float(force) * direction_array / norm


def push_is_active(step: int, push_step: int, duration_steps: int) -> bool:
    """判断第 step 个控制周期是否应施加外力。``push_step=-1`` 表示关闭。"""

    return bool(push_step >= 0 and duration_steps > 0 and push_step <= step < push_step + duration_steps)
