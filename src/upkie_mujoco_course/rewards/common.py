"""Reward 公共工具。"""

from __future__ import annotations

import math


def finite_float(value: float, fallback: float = 0.0) -> float:
    value = float(value)
    return value if math.isfinite(value) else float(fallback)


def combine_rewards(values: dict[str, float], scales: dict[str, float]) -> float:
    return finite_float(sum(float(scales.get(name, 0.0)) * float(value) for name, value in values.items()))

