"""带输出限幅和条件积分抗饱和的 PID 控制器。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PIDDebug:
    proportional: float
    integral: float
    derivative: float
    raw_output: float
    output: float
    saturated: bool


class PIDController:
    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        *,
        limit: float | None = None,
        anti_windup: bool = True,
    ):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.limit = None if limit is None else abs(float(limit))
        self.anti_windup = bool(anti_windup)
        self.integral = 0.0
        self.previous_error: float | None = None
        self.last_debug = PIDDebug(0.0, 0.0, 0.0, 0.0, 0.0, False)

    def reset(self) -> None:
        self.integral = 0.0
        self.previous_error = None

    def step(self, error: float, dt: float) -> float:
        if dt <= 0.0:
            raise ValueError("PID 采样周期必须大于 0")
        error = float(error)
        derivative = 0.0 if self.previous_error is None else (error - self.previous_error) / dt
        candidate_integral = self.integral + error * dt
        raw = self.kp * error + self.ki * candidate_integral + self.kd * derivative
        output = raw if self.limit is None else float(np.clip(raw, -self.limit, self.limit))
        saturated = not np.isclose(output, raw)
        pushes_further_into_saturation = saturated and error * raw > 0.0
        if not self.anti_windup or not pushes_further_into_saturation:
            self.integral = candidate_integral
        raw = self.kp * error + self.ki * self.integral + self.kd * derivative
        output = raw if self.limit is None else float(np.clip(raw, -self.limit, self.limit))
        self.previous_error = error
        self.last_debug = PIDDebug(
            proportional=self.kp * error,
            integral=self.ki * self.integral,
            derivative=self.kd * derivative,
            raw_output=raw,
            output=output,
            saturated=not np.isclose(output, raw),
        )
        return float(output)
