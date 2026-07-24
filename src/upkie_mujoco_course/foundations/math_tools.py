"""基础关卡共用的可测试数学函数。"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np


def seeded_normal_trace(seed: int, size: int) -> np.ndarray:
    if size < 1:
        raise ValueError("采样数量必须为正数")
    return np.random.default_rng(int(seed)).normal(size=int(size))


def rotation_matrix_yaw(angle_rad: float) -> np.ndarray:
    cosine = np.cos(float(angle_rad))
    sine = np.sin(float(angle_rad))
    return np.array(
        [[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]],
        dtype=float,
    )


def _validate_transform(rotation: np.ndarray, translation: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rotation = np.asarray(rotation, dtype=float)
    translation = np.asarray(translation, dtype=float).reshape(-1)
    if rotation.shape != (3, 3) or translation.shape != (3,):
        raise ValueError("坐标变换必须使用 3x3 旋转矩阵和 3 维平移向量")
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-8):
        raise ValueError("旋转矩阵必须正交")
    return rotation, translation


def transform_point(
    body_point: np.ndarray,
    rotation_world_body: np.ndarray,
    translation_world_body: np.ndarray,
) -> np.ndarray:
    rotation, translation = _validate_transform(rotation_world_body, translation_world_body)
    point = np.asarray(body_point, dtype=float).reshape(-1)
    if point.shape != (3,):
        raise ValueError("点坐标必须是 3 维向量")
    return rotation @ point + translation


def inverse_transform_point(
    world_point: np.ndarray,
    rotation_world_body: np.ndarray,
    translation_world_body: np.ndarray,
) -> np.ndarray:
    rotation, translation = _validate_transform(rotation_world_body, translation_world_body)
    point = np.asarray(world_point, dtype=float).reshape(-1)
    if point.shape != (3,):
        raise ValueError("点坐标必须是 3 维向量")
    return rotation.T @ (point - translation)


def central_difference(function: Callable[[float], float], *, x: float, step: float) -> float:
    if step <= 0.0:
        raise ValueError("差分步长必须为正数")
    return float((function(x + step) - function(x - step)) / (2.0 * step))


def finite_difference_gradient(
    function: Callable[[np.ndarray], float],
    *,
    point: np.ndarray,
    step: float,
) -> np.ndarray:
    """逐维使用中心差分计算标量函数的梯度。"""

    if step <= 0.0:
        raise ValueError("差分步长必须为正数")
    point = np.asarray(point, dtype=float).reshape(-1)
    if point.size == 0 or not np.isfinite(point).all():
        raise ValueError("梯度计算点必须是非空有限向量")
    gradient = np.empty_like(point)
    for index in range(point.size):
        offset = np.zeros_like(point)
        offset[index] = step
        gradient[index] = (function(point + offset) - function(point - offset)) / (2.0 * step)
    return gradient


def singular_value_decomposition(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """返回经济型 SVD，使矩形矩阵可由 U @ diag(s) @ Vt 重构。"""

    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2 or 0 in matrix.shape or not np.isfinite(matrix).all():
        raise ValueError("SVD 输入必须是非空有限二维矩阵")
    return np.linalg.svd(matrix, full_matrices=False)


def symmetric_eigendecomposition(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """分解实对称矩阵，特征向量按列排列。"""

    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or matrix.size == 0:
        raise ValueError("特征值分解输入必须是非空方阵")
    if not np.isfinite(matrix).all() or not np.allclose(matrix, matrix.T, atol=1e-12):
        raise ValueError("本实验的特征值分解要求实对称矩阵")
    return np.linalg.eigh(matrix)


def quadratic_gradient(matrix: np.ndarray, point: np.ndarray) -> np.ndarray:
    """计算 f(x)=0.5*x^T*A*x 的梯度 0.5*(A+A^T)*x。"""

    matrix = np.asarray(matrix, dtype=float)
    point = np.asarray(point, dtype=float).reshape(-1)
    if matrix.shape != (point.size, point.size) or point.size == 0:
        raise ValueError("二次型矩阵维度必须与向量一致")
    if not np.isfinite(matrix).all() or not np.isfinite(point).all():
        raise ValueError("二次型输入必须为有限数值")
    return 0.5 * (matrix + matrix.T) @ point


def pendulum_acceleration(
    angle_rad: float | np.ndarray,
    *,
    gravity_m_s2: float = 9.81,
    length_m: float = 1.0,
) -> float | np.ndarray:
    if length_m <= 0.0:
        raise ValueError("摆长必须为正数")
    return -(float(gravity_m_s2) / float(length_m)) * np.sin(angle_rad)


def linearized_pendulum_acceleration(
    angle_rad: float | np.ndarray,
    *,
    gravity_m_s2: float = 9.81,
    length_m: float = 1.0,
) -> float | np.ndarray:
    if length_m <= 0.0:
        raise ValueError("摆长必须为正数")
    return -(float(gravity_m_s2) / float(length_m)) * np.asarray(angle_rad)


def low_pass_filter(values: np.ndarray, *, alpha: float) -> np.ndarray:
    if not 0.0 < alpha <= 1.0:
        raise ValueError("alpha 必须位于 (0, 1]")
    samples = np.asarray(values, dtype=float).reshape(-1)
    if samples.size == 0:
        return samples.copy()
    filtered = np.empty_like(samples)
    filtered[0] = samples[0]
    for index in range(1, samples.size):
        filtered[index] = alpha * samples[index] + (1.0 - alpha) * filtered[index - 1]
    return filtered


def rmse(actual: np.ndarray, expected: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    expected = np.asarray(expected, dtype=float)
    if actual.shape != expected.shape or actual.size == 0:
        raise ValueError("RMSE 输入必须形状一致且非空")
    return float(np.sqrt(np.mean(np.square(actual - expected))))
