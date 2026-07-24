"""脚本命令源。"""

from __future__ import annotations

from .command_types import MotionCommand


def stand_command() -> MotionCommand:
    return MotionCommand(source="script:stand")


def forward_command(speed: float = 0.2) -> MotionCommand:
    return MotionCommand(forward_velocity=float(speed), source="script:forward")

