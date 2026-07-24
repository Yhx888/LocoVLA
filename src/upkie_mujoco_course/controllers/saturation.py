"""动作限幅。"""

from __future__ import annotations

import numpy as np


def clip_action(action: np.ndarray, low: np.ndarray, high: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(action, dtype=float), np.asarray(low, dtype=float), np.asarray(high, dtype=float))

