"""速度跟踪 reward。"""

from __future__ import annotations

from .common import finite_float


def velocity_tracking_reward(state: dict[str, float | bool], target_velocity: float) -> float:
    error = float(state.get("forward_velocity", 0.0)) - float(target_velocity)
    # P-CODE-012 修复：加 clip 下界，避免大误差时 reward 趋向 -inf 导致训练不稳定
    # 原始实现：1.0 - error * error（无下界，error=10 时 reward=-99）
    # 修复后：max(0.0, 1.0 - error * error），reward 范围 [0.0, 1.0]
    raw_reward = 1.0 - error * error
    clipped_reward = max(0.0, raw_reward)
    return finite_float(clipped_reward)

