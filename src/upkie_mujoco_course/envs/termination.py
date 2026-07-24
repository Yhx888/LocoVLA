"""终止条件。"""

from __future__ import annotations


def is_fallen(state: dict[str, float | bool], max_pitch_rad: float = 0.8, min_height: float = -1.0) -> bool:
    if abs(float(state.get("pitch_error", state.get("pitch", 0.0)))) > float(max_pitch_rad):
        return True
    if float(state.get("base_height", 0.0)) < float(min_height):
        return True
    return False
