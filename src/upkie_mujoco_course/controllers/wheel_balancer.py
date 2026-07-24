"""轮速平衡控制器。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from upkie_mujoco_course.utils.config import load_json_config


@dataclass
class BalanceDebug:
    phase: str
    blend: float
    target_joints: dict[str, float]
    pitch: float
    pitch_rate: float
    balance_torque: float
    damping_torque: float


class WheelBalancerController:
    """从 crouch 姿态平滑过渡到站立，并用轮速反馈保持平衡。"""

    def __init__(
        self,
        standup_duration: float | None = None,
        wheel_damping_gain: float | None = None,
        pitch_gain: float | None = None,
        pitch_rate_gain: float | None = None,
        forward_velocity_gain: float | None = None,
        position_gain: float | None = None,
        torque_filter_alpha: float | None = None,
        target_velocity: float = 0.0,
    ):
        config = load_json_config("configs/control/pd.json")["wheel_balancer"]
        self.standup_duration = max(0.2, float(config["standup_duration"] if standup_duration is None else standup_duration))
        self.wheel_damping_gain = float(config["wheel_damping_gain"] if wheel_damping_gain is None else wheel_damping_gain)
        self.pitch_gain = float(config["pitch_gain"] if pitch_gain is None else pitch_gain)
        self.pitch_rate_gain = float(config["pitch_rate_gain"] if pitch_rate_gain is None else pitch_rate_gain)
        self.forward_velocity_gain = float(
            config["forward_velocity_gain"] if forward_velocity_gain is None else forward_velocity_gain
        )
        self.position_gain = float(config["position_gain"] if position_gain is None else position_gain)
        self.torque_filter_alpha = float(
            config["torque_filter_alpha"] if torque_filter_alpha is None else torque_filter_alpha
        )
        self.target_velocity = float(target_velocity)
        self.target_position = 0.0
        self.last_time: float | None = None
        self.filtered_torque = 0.0
        self.last_debug = BalanceDebug("init", 0.0, {}, 0.0, 0.0, 0.0, 0.0)

    def reset(self) -> None:
        self.filtered_torque = 0.0
        self.target_position = 0.0
        self.last_time = None

    def compute_action(
        self,
        runner,
        sim_time: float,
        estimated_state: dict[str, float] | None = None,
    ) -> np.ndarray:
        target_joints = self._standup_joint_targets(runner, sim_time)
        state = runner.posture_state()
        if estimated_state is not None:
            state.update(
                {
                    name: float(estimated_state[name])
                    for name in ("pitch_error", "pitch_rate", "forward_velocity", "x_position")
                }
            )
        left_wheel, right_wheel = runner.spec.wheel_joints
        left_vel = float(runner.data.qvel[runner.joint_map.dofadr[left_wheel]])
        right_vel = float(runner.data.qvel[runner.joint_map.dofadr[right_wheel]])
        left_direction, right_direction = runner.spec.wheel_directions
        mean_wheel_vel = 0.5 * (left_direction * left_vel + right_direction * right_vel)
        pitch = float(state["pitch_error"])
        pitch_rate = float(state["pitch_rate"])
        forward_velocity = float(state["forward_velocity"])
        if self.last_time is None:
            self.target_position = float(state["x_position"])
        else:
            self.target_position += self.target_velocity * max(0.0, sim_time - self.last_time)
        self.last_time = float(sim_time)
        balance_torque = (
            self.pitch_gain * pitch
            + self.pitch_rate_gain * pitch_rate
            + self.position_gain * (float(state["x_position"]) - self.target_position)
            + self.forward_velocity_gain * (forward_velocity - self.target_velocity)
        )
        damping_torque = -self.wheel_damping_gain * mean_wheel_vel
        raw_torque = balance_torque + damping_torque
        alpha = float(np.clip(self.torque_filter_alpha, 0.0, 1.0))
        self.filtered_torque = alpha * raw_torque + (1.0 - alpha) * self.filtered_torque
        action = np.zeros(runner.model.nu, dtype=float)
        action[runner.actuator_ids["left_hip_servo"]] = target_joints["left_hip"]
        action[runner.actuator_ids["left_knee_servo"]] = target_joints["left_knee"]
        action[runner.actuator_ids["right_hip_servo"]] = target_joints["right_hip"]
        action[runner.actuator_ids["right_knee_servo"]] = target_joints["right_knee"]
        action[runner.actuator_ids["left_wheel_motor"]] = left_direction * self.filtered_torque
        action[runner.actuator_ids["right_wheel_motor"]] = right_direction * self.filtered_torque
        blend = self._standup_blend(sim_time)
        self.last_debug = BalanceDebug(
            phase="standup" if blend < 1.0 else "balance",
            blend=blend,
            target_joints=target_joints,
            pitch=pitch,
            pitch_rate=pitch_rate,
            balance_torque=float(balance_torque),
            damping_torque=float(damping_torque),
        )
        return np.clip(action, runner.ctrl_low, runner.ctrl_high)

    def _standup_blend(self, sim_time: float) -> float:
        s = float(np.clip(sim_time / self.standup_duration, 0.0, 1.0))
        return float(3.0 * s * s - 2.0 * s * s * s)

    def _standup_joint_targets(self, runner, sim_time: float) -> dict[str, float]:
        end = runner.spec.default_pose["stand"]
        if runner.last_reset_pose != "crouch":
            return {joint: float(value) for joint, value in end.items()}
        start = runner.spec.default_pose["crouch"]
        blend = self._standup_blend(sim_time)
        return {joint: float((1.0 - blend) * start[joint] + blend * end[joint]) for joint in end}
