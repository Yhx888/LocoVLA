"""把基座高度误差映射为镜像腿部位置目标。"""

from __future__ import annotations

import numpy as np


def height_error(target_height: float, current_height: float) -> float:
    return float(target_height - current_height)


class HeightController:
    def __init__(self, gain: float = 4.0, max_joint_offset_rad: float = 0.1):
        self.gain = float(gain)
        self.max_joint_offset_rad = abs(float(max_joint_offset_rad))

    def compute_targets(
        self,
        nominal_pose: dict[str, float],
        *,
        target_height: float,
        current_height: float,
    ) -> dict[str, float]:
        correction = float(
            np.clip(
                self.gain * height_error(target_height, current_height),
                -self.max_joint_offset_rad,
                self.max_joint_offset_rad,
            )
        )
        return {
            "left_hip": float(nominal_pose["left_hip"] + correction),
            "left_knee": float(nominal_pose["left_knee"] - correction),
            "right_hip": float(nominal_pose["right_hip"] - correction),
            "right_knee": float(nominal_pose["right_knee"] + correction),
        }
