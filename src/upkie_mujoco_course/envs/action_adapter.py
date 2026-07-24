"""动作适配。"""

from __future__ import annotations

import numpy as np


def adapt_action(
    action: np.ndarray,
    neutral: np.ndarray,
    scale: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
) -> np.ndarray:
    """把 [-1, 1] 策略动作映射为物理执行器命令。"""

    normalized = np.clip(np.asarray(action, dtype=float).reshape(low.shape), -1.0, 1.0)
    return np.clip(np.asarray(neutral, dtype=float) + normalized * np.asarray(scale, dtype=float), low, high)
