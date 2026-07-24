"""C++ 轮端控制器的 Python 参考实现。"""

from __future__ import annotations

import numpy as np


DEFAULT_GAINS = np.array([2.0, 0.8, 3.0, 0.8], dtype=float)


def reference_control(
    state_error: np.ndarray,
    yaw: np.ndarray,
    limit: np.ndarray,
) -> np.ndarray:
    """按 C++ 的增益、轮轴符号和限幅规则计算三列参考输出。"""

    states = np.asarray(state_error, dtype=float)
    yaws = np.asarray(yaw, dtype=float).reshape(-1)
    limits = np.asarray(limit, dtype=float).reshape(-1)
    if states.ndim != 2 or states.shape[1] != 4:
        raise ValueError("状态误差必须是形状为 (N, 4) 的数组")
    if len(states) != len(yaws) or len(states) != len(limits):
        raise ValueError("状态、偏航和限幅的样本数量必须一致")
    if np.any(limits <= 0.0):
        raise ValueError("轮端力矩限幅必须为正数")
    balance = states @ DEFAULT_GAINS
    left = np.clip(balance - yaws, -limits, limits)
    right = np.clip(-balance - yaws, -limits, limits)
    return np.column_stack((balance, left, right))


def parse_probe_output(output: str, expected_rows: int) -> np.ndarray:
    """解析 control_probe 的三列浮点输出，并拒绝缺行或多行。"""

    rows = [line.split() for line in output.splitlines() if line.strip()]
    if len(rows) != expected_rows or any(len(row) != 3 for row in rows):
        raise ValueError("control_probe 输出的行数或列数与输入不一致")
    try:
        values = np.asarray(rows, dtype=float)
    except ValueError as error:
        raise ValueError("control_probe 输出包含非数值内容") from error
    if not np.isfinite(values).all():
        raise ValueError("control_probe 输出包含非有限数值")
    return values
