"""绘图工具占位。"""

from __future__ import annotations

from pathlib import Path

from upkie_mujoco_course.utils.paths import ensure_output_dir


def plot_output_path(name: str) -> Path:
    return ensure_output_dir("plots") / name

