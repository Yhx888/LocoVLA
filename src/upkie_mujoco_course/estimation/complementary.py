"""俯仰角互补滤波器。"""

from __future__ import annotations


class ComplementaryPitchEstimator:
    """融合陀螺仪短期变化与加速度计长期参考。"""

    def __init__(self, alpha: float = 0.98, dt: float = 0.01):
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("alpha 必须位于 [0, 1]")
        if dt <= 0.0:
            raise ValueError("dt 必须为正数")
        self.alpha = float(alpha)
        self.dt = float(dt)
        self.pitch = 0.0

    def reset(self, pitch: float = 0.0) -> None:
        self.pitch = float(pitch)

    def update(self, gyro_rate: float, accelerometer_pitch: float) -> float:
        prediction = self.pitch + float(gyro_rate) * self.dt
        self.pitch = self.alpha * prediction + (1.0 - self.alpha) * float(accelerometer_pitch)
        return self.pitch

