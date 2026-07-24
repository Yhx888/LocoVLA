"""把 VLA 速度命令接到受限低层平衡控制器。"""

from __future__ import annotations

import numpy as np

from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.vla.expert import ExpertCommand


class VLASafetyController:
    def __init__(
        self,
        yaw_torque_gain: float = 0.025,
        acceleration_limit: float = 0.1,
        soft_pitch_limit: float = 0.18,
    ):
        self.balance = WheelBalancerController()
        self.yaw_torque_gain = float(yaw_torque_gain)
        self.acceleration_limit = float(acceleration_limit)
        self.soft_pitch_limit = float(soft_pitch_limit)
        self.command_velocity = 0.0
        self.safety_interventions = 0

    def reset(self) -> None:
        self.balance.reset()
        self.command_velocity = 0.0
        self.safety_interventions = 0

    def compute_action(self, runner, command: ExpertCommand) -> np.ndarray:
        state = runner.posture_state()
        safety_active = abs(float(state["pitch_error"])) > self.soft_pitch_limit
        stop_requested = bool(command.stop)
        requested_velocity = 0.0 if safety_active or stop_requested else float(command.forward_velocity)
        requested_yaw = 0.0 if safety_active or stop_requested else float(command.yaw_rate)
        if safety_active or stop_requested:
            self.safety_interventions += 1
            self.command_velocity = 0.0
            self.balance.target_position = float(state["x_position"])
            self.balance.last_time = runner.time
        control_dt = runner.model.opt.timestep * runner.spec.frame_skip
        max_delta = self.acceleration_limit * control_dt
        velocity_error = requested_velocity - self.command_velocity
        self.command_velocity += float(np.clip(velocity_error, -max_delta, max_delta))
        self.balance.target_velocity = float(np.clip(self.command_velocity, -0.12, 0.12))
        action = self.balance.compute_action(runner, runner.time)
        root_dof = int(runner.model.jnt_dofadr[runner.root_joint_id])
        measured_yaw_rate = float(runner.data.qvel[root_dof + 5])
        yaw_torque = 0.0
        if abs(requested_yaw) > 1e-6:
            if abs(requested_velocity) < 1e-6:
                opposing_motion = requested_yaw * measured_yaw_rate < 0.0
                gain = 0.05 if opposing_motion else self.yaw_torque_gain
                limit = 0.03 if opposing_motion else 0.015
                yaw_torque = float(np.clip(gain * (requested_yaw - measured_yaw_rate), -limit, limit))
            else:
                yaw_torque = 0.02 * requested_yaw
        for name in ("left_wheel_motor", "right_wheel_motor"):
            action[runner.actuator_ids[name]] -= yaw_torque
        return np.clip(action, runner.ctrl_low, runner.ctrl_high)

    def compute_policy_action(
        self,
        env,
        policy_action: np.ndarray,
        *,
        emergency_stop: bool = False,
        stop_requested: bool = False,
    ) -> np.ndarray:
        """把 BC 的归一化动作送入可抢占的确定性安全层。"""

        state = env.runner.posture_state()
        if emergency_stop:
            self.command_velocity = 0.0
            self.balance.target_position = float(state["x_position"])
            self.balance.last_time = env.runner.time
            self.safety_interventions += 1
            return np.zeros(env.action_space.shape, dtype=np.float64)
        learned = np.clip(
            np.asarray(policy_action, dtype=np.float64).reshape(env.action_space.shape),
            -1.0,
            1.0,
        )
        command = ExpertCommand(
            forward_velocity=0.4 * float(learned[0]),
            yaw_rate=float(learned[1]),
            stop=bool(stop_requested or learned[2] > 0.5),
        )
        physical = self.compute_action(env.runner, command)
        return env.to_normalized_action(physical)
