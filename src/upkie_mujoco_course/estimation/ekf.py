"""离散扩展 Kalman 滤波器。"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np


StateFunction = Callable[[np.ndarray], np.ndarray]
JacobianFunction = Callable[[np.ndarray], np.ndarray]


class ExtendedKalmanFilter:
    """通过局部 Jacobian 线性化非线性状态与观测模型。"""

    def __init__(
        self,
        *,
        state: np.ndarray,
        covariance: np.ndarray,
        process_noise: np.ndarray,
        measurement_noise: np.ndarray,
    ):
        self.state = np.asarray(state, dtype=float).reshape(-1)
        self.covariance = np.asarray(covariance, dtype=float)
        self.process_noise = np.asarray(process_noise, dtype=float)
        self.measurement_noise = np.asarray(measurement_noise, dtype=float)
        expected = (self.state.size, self.state.size)
        if self.covariance.shape != expected or self.process_noise.shape != expected:
            raise ValueError("状态协方差维度与状态不一致")

    def predict(
        self,
        *,
        transition: StateFunction,
        transition_jacobian: JacobianFunction,
    ) -> np.ndarray:
        prior_state = self.state.copy()
        jacobian = np.asarray(transition_jacobian(prior_state), dtype=float)
        if jacobian.shape != self.covariance.shape:
            raise ValueError("状态 Jacobian 维度与状态不一致")
        self.state = np.asarray(transition(prior_state), dtype=float).reshape(-1)
        self.covariance = jacobian @ self.covariance @ jacobian.T + self.process_noise
        return self.state.copy()

    def update(
        self,
        measurement_value: np.ndarray,
        *,
        measurement: StateFunction,
        measurement_jacobian: JacobianFunction,
    ) -> np.ndarray:
        predicted_measurement = np.asarray(measurement(self.state), dtype=float).reshape(-1)
        observed = np.asarray(measurement_value, dtype=float).reshape(-1)
        jacobian = np.asarray(measurement_jacobian(self.state), dtype=float)
        if observed.shape != predicted_measurement.shape or jacobian.shape != (observed.size, self.state.size):
            raise ValueError("测量或测量 Jacobian 维度不一致")
        innovation_covariance = jacobian @ self.covariance @ jacobian.T + self.measurement_noise
        gain = np.linalg.solve(innovation_covariance, jacobian @ self.covariance).T
        self.state = self.state + gain @ (observed - predicted_measurement)
        identity = np.eye(self.state.size)
        residual = identity - gain @ jacobian
        self.covariance = (
            residual @ self.covariance @ residual.T
            + gain @ self.measurement_noise @ gain.T
        )
        return self.state.copy()
