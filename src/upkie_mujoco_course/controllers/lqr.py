"""LQR 控制器。

LQR（Linear Quadratic Regulator，线性二次调节器）是最优控制的经典方法。
核心思想：给定状态 x 和参考状态 x_ref，计算最优控制量使代价函数最小。

公式：u = -K * (x - x_ref)

其中 K 是通过求解 Riccati 方程得到的最优增益矩阵。
本模块使用预计算的固定增益 K，不包含在线求解过程。

与 PD 的区别：
- PD 只看单个关节的误差和速度
- LQR 看整个状态向量，考虑多变量之间的耦合关系
"""

from __future__ import annotations

import numpy as np

from upkie_mujoco_course.utils.config import load_json_config


class LQRController:
    """用固定增益表示的最小 LQR 接口。

    典型用法::

        # gain 是预计算的 K 矩阵（行=输出维度，列=状态维度）
        controller = LQRController(gain=K_matrix)
        output = controller.compute(state_vector)
    """

    def __init__(self, gain: np.ndarray):
        """初始化。

        Args:
            gain: 状态反馈增益矩阵 K，形状为 (输出维度, 状态维度)
        """
        self.gain = np.asarray(gain, dtype=float)

    def compute(self, state: np.ndarray, reference: np.ndarray | None = None) -> np.ndarray:
        """计算 LQR 输出：u = -K * (x - x_ref)。

        Args:
            state: 当前状态向量（如 [x_position, forward_velocity, pitch_error, pitch_rate]，顺序需与 gain 矩阵列顺序一致）
            reference: 参考状态（默认为零向量，即"保持静止"）

        Returns:
            控制输出向量
        """
        state = np.asarray(state, dtype=float).reshape(-1)
        reference = np.zeros_like(state) if reference is None else np.asarray(reference, dtype=float).reshape(-1)
        # 矩阵乘法：K @ (x - x_ref) 得到最优控制量，取负号因为是调节器（使状态回到零）
        return -self.gain @ (state - reference)


class LQRBalanceController:
    """把四状态 LQR 输出映射为左右轮力矩。"""

    def __init__(self):
        config = load_json_config("configs/control/lqr.json")["lqr"]
        self.controller = LQRController(np.asarray(config["gain"], dtype=float))
        self.filter_alpha = float(config["torque_filter_alpha"])
        self.filtered_torque = 0.0

    def reset(self) -> None:
        self.filtered_torque = 0.0

    def compute_action(self, runner) -> np.ndarray:
        state = runner.posture_state()
        vector = np.array(
            [state["x_position"], state["forward_velocity"], state["pitch_error"], state["pitch_rate"]],
            dtype=float,
        )
        raw_torque = float(self.controller.compute(vector)[0])
        self.filtered_torque = (
            self.filter_alpha * raw_torque + (1.0 - self.filter_alpha) * self.filtered_torque
        )
        action = np.zeros(runner.model.nu, dtype=float)
        stand = runner.spec.default_pose["stand"]
        for actuator in runner.spec.position_actuators:
            action[runner.actuator_ids[actuator.name]] = stand[actuator.joint]
        for actuator, direction in zip(runner.spec.torque_actuators, runner.spec.wheel_directions):
            action[runner.actuator_ids[actuator.name]] = direction * self.filtered_torque
        return np.clip(action, runner.ctrl_low, runner.ctrl_high)
