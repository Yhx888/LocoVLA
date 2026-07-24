"""动作滤波。"""

from __future__ import annotations

import numpy as np


class LowPassActionFilter:
    """一阶低通动作滤波器。"""

    def __init__(self, alpha: float, size: int):
        self.alpha = float(np.clip(alpha, 0.0, 1.0))
        self.previous = np.zeros(int(size), dtype=float)

    def reset(self) -> None:
        self.previous[:] = 0.0

    def filter(self, action: np.ndarray) -> np.ndarray:
        action = np.asarray(action, dtype=float)
        self.previous = self.alpha * action + (1.0 - self.alpha) * self.previous
        return self.previous.copy()


def limit_action_delta(action: np.ndarray, previous: np.ndarray, max_delta: float) -> np.ndarray:
    delta = np.clip(np.asarray(action, dtype=float) - np.asarray(previous, dtype=float), -max_delta, max_delta)
    return np.asarray(previous, dtype=float) + delta

