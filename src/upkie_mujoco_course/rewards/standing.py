"""站立奖励。"""

from __future__ import annotations

import math

from .common import finite_float


def standing_reward(
    state: dict[str, float | bool],
    *,
    target_height: float | None = None,
) -> float:
    alive = 1.0 if bool(state.get("both_wheels_contact", True)) else -1.0
    upright = 1.0 - abs(float(state.get("pitch", 0.0)))
    current_height = float(state.get("base_height", 0.0))
    desired_height = current_height if target_height is None else float(target_height)
    height_error = current_height - desired_height
    height = math.exp(-10.0 * height_error * height_error)
    return finite_float(alive + upright + height)
