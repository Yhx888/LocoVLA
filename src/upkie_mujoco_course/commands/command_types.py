"""高层命令类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MotionCommand:
    forward_velocity: float = 0.0
    yaw_rate: float = 0.0
    height: float = 0.0
    source: str = "script"

