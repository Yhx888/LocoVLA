"""面向课程彩色目标的可解释 RGB-D 感知。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TargetDetection:
    visible: bool
    horizontal_offset: float
    distance: float
    pixel_count: int


def detect_colored_target(rgb: np.ndarray, depth: np.ndarray, color: str) -> TargetDetection:
    rgb = np.asarray(rgb, dtype=np.uint8)
    depth = np.asarray(depth, dtype=float)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or depth.shape != rgb.shape[:2]:
        raise ValueError("RGB 与深度图尺寸不匹配")
    channels = {"red": 0, "green": 1, "blue": 2}
    if color not in channels:
        return TargetDetection(False, 0.0, float("inf"), 0)
    primary = rgb[..., channels[color]].astype(int)
    others = np.delete(rgb.astype(int), channels[color], axis=2)
    secondary = np.max(others, axis=2)
    mask = (primary >= 160) & (secondary <= 85) & (primary >= secondary + 50)
    rows, cols = np.nonzero(mask)
    if cols.size == 0:
        return TargetDetection(False, 0.0, float("inf"), 0)
    offset = 2.0 * float(np.mean(cols)) / max(1, rgb.shape[1] - 1) - 1.0
    valid_depth = depth[mask]
    valid_depth = valid_depth[np.isfinite(valid_depth) & (valid_depth > 0.0)]
    distance = float(np.median(valid_depth)) if valid_depth.size else float("inf")
    return TargetDetection(True, offset, distance, int(cols.size))
