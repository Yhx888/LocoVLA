"""键盘命令占位。"""

from __future__ import annotations

from .command_types import MotionCommand


def key_to_command(key: str) -> MotionCommand:
    if key.lower() == "w":
        return MotionCommand(forward_velocity=0.2, source="keyboard:w")
    if key.lower() == "s":
        return MotionCommand(forward_velocity=-0.2, source="keyboard:s")
    return MotionCommand(source=f"keyboard:{key}")

