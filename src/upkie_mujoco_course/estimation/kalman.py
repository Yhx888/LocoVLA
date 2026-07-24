"""离散线性 Kalman 滤波器。"""

from __future__ import annotations

import numpy as np


class LinearKalmanFilter:
    """对线性状态转移和线性观测执行预测与校正。"""

    def __init__(
        self,
        *,
        state: np.ndarray,
        covariance: np.ndarray,
        transition: np.ndarray,
        observation: np.ndarray,
        process_noise: np.ndarray,
        measurement_noise: np.ndarray,
    ):
        self.state = np.asarray(state, dtype=float).reshape(-1)
        self.covariance = np.asarray(covariance, dtype=float)
        self.transition = np.asarray(transition, dtype=float)
        self.observation = np.asarray(observation, dtype=float)
        self.process_noise = np.asarray(process_noise, dtype=float)
        self.measurement_noise = np.asarray(measurement_noise, dtype=float)
        self._validate_shapes()

    def _validate_shapes(self) -> None:
        state_size = self.state.size
        measurement_size = self.observation.shape[0]
        expected_state_matrix = (state_size, state_size)
        if self.transition.shape != expected_state_matrix:
            raise ValueError("状态转移矩阵维度与状态不一致")
        if self.covariance.shape != expected_state_matrix or self.process_noise.shape != expected_state_matrix:
            raise ValueError("状态协方差维度与状态不一致")
        if self.observation.shape[1:] != (state_size,):
            raise ValueError("观测矩阵维度与状态不一致")
        if self.measurement_noise.shape != (measurement_size, measurement_size):
            raise ValueError("测量噪声矩阵维度与观测不一致")

    def predict(
        self,
        control: np.ndarray | None = None,
        control_matrix: np.ndarray | None = None,
    ) -> np.ndarray:
        self.state = self.transition @ self.state
        if control is not None:
            if control_matrix is None:
                raise ValueError("提供控制量时必须同时提供控制矩阵")
            self.state += np.asarray(control_matrix, dtype=float) @ np.asarray(control, dtype=float).reshape(-1)
        self.covariance = self.transition @ self.covariance @ self.transition.T + self.process_noise
        return self.state.copy()

    def update(self, measurement: np.ndarray) -> np.ndarray:
        measurement = np.asarray(measurement, dtype=float).reshape(-1)
        if measurement.size != self.observation.shape[0]:
            raise ValueError("测量维度与观测模型不一致")
        innovation = measurement - self.observation @ self.state
        innovation_covariance = (
            self.observation @ self.covariance @ self.observation.T + self.measurement_noise
        )
        gain = np.linalg.solve(
            innovation_covariance,
            self.observation @ self.covariance,
        ).T
        self.state = self.state + gain @ innovation
        identity = np.eye(self.state.size)
        residual = identity - gain @ self.observation
        self.covariance = (
            residual @ self.covariance @ residual.T
            + gain @ self.measurement_noise @ gain.T
        )
        return self.state.copy()
