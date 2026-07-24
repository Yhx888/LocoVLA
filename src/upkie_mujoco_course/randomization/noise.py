"""传感器噪声。"""

from __future__ import annotations

import numpy as np


def add_gaussian_noise(values: np.ndarray, std: float, rng: np.random.Generator | None = None) -> np.ndarray:
    rng = rng or np.random.default_rng()
    return np.asarray(values, dtype=float) + rng.normal(0.0, float(std), size=np.asarray(values).shape)

