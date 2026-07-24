"""偏航角速度到差动轮端力矩的受限控制器。"""

from __future__ import annotations


import numpy as np


class YawRateController:
    def __init__(self, gain: float = 0.025, torque_limit: float = 0.03):
        self.gain = float(gain)
        self.torque_limit = abs(float(torque_limit))

    def compute(
        self,
        target_yaw_rate: float,
        current_yaw_rate: float,
        *,
        gain: float | None = None,
        torque_limit: float | None = None,
    ) -> float:
        active_gain = self.gain if gain is None else float(gain)
        active_limit = self.torque_limit if torque_limit is None else abs(float(torque_limit))
        raw = active_gain * (float(target_yaw_rate) - float(current_yaw_rate))
        return float(np.clip(raw, -active_limit, active_limit))


def yaw_rate_command(
    target_yaw_rate: float,
    current_yaw_rate: float,
    gain: float = 1.0,
    torque_limit: float = float("inf"),
) -> float:
    return YawRateController(gain=gain, torque_limit=torque_limit).compute(
        target_yaw_rate,
        current_yaw_rate,
    )
