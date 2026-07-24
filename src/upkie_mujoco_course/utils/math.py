"""数学工具。"""

from __future__ import annotations

import numpy as np


def smoothstep(x: float) -> float:
    """三次 smoothstep，常用于站起插值。"""

    s = float(np.clip(x, 0.0, 1.0))
    return float(3.0 * s * s - 2.0 * s * s * s)

