"""正则 reward。"""

from __future__ import annotations

import numpy as np

from .common import finite_float


def energy_penalty(action: np.ndarray) -> float:
    return finite_float(-float(np.sum(np.square(np.asarray(action, dtype=float)))))


def action_smoothness_penalty(action: np.ndarray, previous_action: np.ndarray) -> float:
    delta = np.asarray(action, dtype=float) - np.asarray(previous_action, dtype=float)
    return finite_float(-float(np.sum(np.square(delta))))

