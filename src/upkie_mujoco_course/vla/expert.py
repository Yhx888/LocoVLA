"""应用型 VLA 的可解释脚本专家。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ExpertCommand:
    forward_velocity: float
    yaw_rate: float
    stop: bool


class ScriptedVLAExpert:
    """根据目标偏移和距离生成有界速度命令。"""

    def __init__(
        self,
        stop_distance: float = 0.6,
        max_velocity: float = 0.12,
        distance_gain: float = 0.5,
        yaw_gain: float = 1.2,
        yaw_deadband: float = 0.1,
    ):
        self.stop_distance = float(stop_distance)
        self.max_velocity = float(max_velocity)
        self.distance_gain = float(distance_gain)
        self.yaw_gain = float(yaw_gain)
        self.yaw_deadband = float(yaw_deadband)
        self.navigation_phase = "corridor"
        self.obstacle_was_near = False

    def reset(self) -> None:
        self.navigation_phase = "corridor"
        self.obstacle_was_near = False

    def should_defer_detection(self, target_color: str) -> bool:
        return target_color in {"blue", "green"} and self.navigation_phase == "corridor"

    def occluded_command(self, target_color: str, depth: np.ndarray | None = None) -> ExpertCommand:
        search_direction = {"blue": 0.3, "green": -0.3}.get(target_color, 0.0)
        if search_direction == 0.0:
            return ExpertCommand(0.0, 0.0, False)
        if depth is None:
            return ExpertCommand(0.04, search_direction, False)
        if self.navigation_phase == "corridor":
            image = np.asarray(depth, dtype=float)
            height, width = image.shape
            upper = image[int(0.04 * height) : int(0.63 * height), int(0.06 * width) : int(0.94 * width)]
            valid = upper[np.isfinite(upper) & (upper > 0.0)]
            clearance = float(np.percentile(valid, 5.0)) if valid.size else float("inf")
            self.obstacle_was_near = self.obstacle_was_near or clearance < 0.7
            if not (self.obstacle_was_near and clearance > 1.3):
                return ExpertCommand(0.1, 0.0, False)
            self.navigation_phase = "search"
        return ExpertCommand(0.0, 0.45 * np.sign(search_direction), False)

    def command(self, *, visible: bool, horizontal_offset: float, distance: float) -> ExpertCommand:
        if not visible or not np.isfinite(distance):
            return ExpertCommand(0.0, 0.0, True)
        self.navigation_phase = "approach"
        distance_error = float(distance) - self.stop_distance
        velocity = float(np.clip(self.distance_gain * distance_error, 0.0, self.max_velocity))
        if abs(horizontal_offset) <= self.yaw_deadband:
            yaw_rate = 0.0
        else:
            corrected_offset = horizontal_offset - np.sign(horizontal_offset) * self.yaw_deadband
            yaw_rate = float(np.clip(-self.yaw_gain * corrected_offset, -1.0, 1.0))
        return ExpertCommand(velocity, yaw_rate, velocity == 0.0)
