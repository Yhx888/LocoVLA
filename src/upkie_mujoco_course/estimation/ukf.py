"""离散无迹 Kalman 滤波器。"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np


StateFunction = Callable[[np.ndarray], np.ndarray]


class UnscentedKalmanFilter:
    """用 sigma 点传播非线性状态和观测，不依赖 Jacobian。"""

    def __init__(
        self,
        *,
        state: np.ndarray,
        covariance: np.ndarray,
        process_noise: np.ndarray,
        measurement_noise: np.ndarray,
        alpha: float = 0.3,
        beta: float = 2.0,
        kappa: float = 0.0,
    ):
        self.state = np.asarray(state, dtype=float).reshape(-1)
        self.covariance = np.asarray(covariance, dtype=float)
        self.process_noise = np.asarray(process_noise, dtype=float)
        self.measurement_noise = np.asarray(measurement_noise, dtype=float)
        expected = (self.state.size, self.state.size)
        if self.covariance.shape != expected or self.process_noise.shape != expected:
            raise ValueError("状态协方差维度与状态不一致")
        self._scale = alpha * alpha * (self.state.size + kappa)
        if self._scale <= 0.0:
            raise ValueError("UKF sigma 点缩放参数必须为正")
        self._mean_weights = np.full(2 * self.state.size + 1, 0.5 / self._scale)
        self._covariance_weights = self._mean_weights.copy()
        self._mean_weights[0] = 1.0 - self.state.size / self._scale
        self._covariance_weights[0] = self._mean_weights[0] + (1.0 - alpha * alpha + beta)
        self._predicted_sigma_points: np.ndarray | None = None

    def _sigma_points(self) -> np.ndarray:
        covariance = 0.5 * (self.covariance + self.covariance.T)
        root = np.linalg.cholesky(self._scale * covariance + np.eye(self.state.size) * 1e-12)
        points = [self.state]
        points.extend(self.state + root[:, index] for index in range(self.state.size))
        points.extend(self.state - root[:, index] for index in range(self.state.size))
        return np.asarray(points)

    def predict(self, *, transition: StateFunction) -> np.ndarray:
        propagated = np.asarray([transition(point) for point in self._sigma_points()], dtype=float)
        self.state = self._mean_weights @ propagated
        deviations = propagated - self.state
        self.covariance = (
            np.einsum("i,ij,ik->jk", self._covariance_weights, deviations, deviations)
            + self.process_noise
        )
        self._predicted_sigma_points = propagated
        return self.state.copy()

    def update(self, measurement_value: np.ndarray, *, measurement: StateFunction) -> np.ndarray:
        sigma_points = self._predicted_sigma_points
        if sigma_points is None:
            sigma_points = self._sigma_points()
        projected = np.asarray([measurement(point) for point in sigma_points], dtype=float)
        observed = np.asarray(measurement_value, dtype=float).reshape(-1)
        if projected.ndim != 2 or projected.shape[1:] != observed.shape:
            raise ValueError("测量维度不一致")
        predicted_measurement = self._mean_weights @ projected
        measurement_deviations = projected - predicted_measurement
        state_deviations = sigma_points - self.state
        innovation_covariance = (
            np.einsum(
                "i,ij,ik->jk",
                self._covariance_weights,
                measurement_deviations,
                measurement_deviations,
            )
            + self.measurement_noise
        )
        cross_covariance = np.einsum(
            "i,ij,ik->jk",
            self._covariance_weights,
            state_deviations,
            measurement_deviations,
        )
        gain = np.linalg.solve(innovation_covariance, cross_covariance.T).T
        self.state = self.state + gain @ (observed - predicted_measurement)
        self.covariance = self.covariance - gain @ innovation_covariance @ gain.T
        self.covariance = 0.5 * (self.covariance + self.covariance.T)
        self._predicted_sigma_points = None
        return self.state.copy()
