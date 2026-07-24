"""速度、偏航和高度命令的受限低层控制接口。"""

from __future__ import annotations

import numpy as np

from upkie_mujoco_course.commands.command_types import MotionCommand
from upkie_mujoco_course.controllers.height_controller import HeightController
from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.controllers.yaw_controller import YawRateController


class MotionController:
    def __init__(
        self,
        *,
        yaw_torque_gain: float = 0.025,
        acceleration_limit: float = 0.1,
        soft_pitch_limit: float = 0.18,
    ):
        self.balance = WheelBalancerController()
        self.yaw = YawRateController(gain=yaw_torque_gain, torque_limit=0.03)
        self.height = HeightController()
        self.yaw_torque_gain = float(yaw_torque_gain)
        self.acceleration_limit = float(acceleration_limit)
        self.soft_pitch_limit = float(soft_pitch_limit)
        self.command_velocity = 0.0
        self.safety_interventions = 0
        self.last_yaw_torque = 0.0

    def reset(self) -> None:
        self.balance.reset()
        self.command_velocity = 0.0
        self.safety_interventions = 0
        self.last_yaw_torque = 0.0

    def compute_action(self, runner, command: MotionCommand) -> np.ndarray:
        state = runner.posture_state()
        safety_active = abs(float(state["pitch_error"])) > self.soft_pitch_limit
        requested_velocity = 0.0 if safety_active else float(command.forward_velocity)
        requested_yaw = 0.0 if safety_active else float(command.yaw_rate)
        target_height = 0.0 if safety_active else float(command.height)
        if safety_active:
            self.safety_interventions += 1
            self.command_velocity = 0.0
            self.balance.target_position = float(state["x_position"])
            self.balance.last_time = runner.time

        control_dt = float(runner.model.opt.timestep * runner.spec.frame_skip)
        max_delta = self.acceleration_limit * control_dt
        velocity_error = requested_velocity - self.command_velocity
        self.command_velocity += float(np.clip(velocity_error, -max_delta, max_delta))
        self.balance.target_velocity = float(np.clip(self.command_velocity, -0.12, 0.12))
        action = self.balance.compute_action(runner, runner.time)

        measured_yaw_rate = float(state["yaw_rate"])
        opposing_motion = requested_yaw * measured_yaw_rate < 0.0
        yaw_gain = 0.05 if opposing_motion else self.yaw_torque_gain
        yaw_limit = 0.03 if opposing_motion else 0.015
        self.last_yaw_torque = self.yaw.compute(
            requested_yaw,
            measured_yaw_rate,
            gain=yaw_gain,
            torque_limit=yaw_limit,
        )
        for actuator, direction, turn_sign in zip(
            runner.spec.torque_actuators,
            runner.spec.wheel_directions,
            (-1.0, 1.0),
        ):
            actuator_id = runner.actuator_ids[actuator.name]
            physical_torque = direction * float(action[actuator_id])
            physical_torque += turn_sign * self.last_yaw_torque
            action[actuator_id] = direction * physical_torque

        nominal_pose = runner.spec.default_pose["stand"]
        leg_targets = (
            self.height.compute_targets(
                nominal_pose,
                target_height=target_height,
                current_height=float(state["base_height"]),
            )
            if abs(target_height) > 1e-9
            else nominal_pose
        )
        for actuator in runner.spec.position_actuators:
            action[runner.actuator_ids[actuator.name]] = leg_targets[actuator.joint]
        return np.clip(action, runner.ctrl_low, runner.ctrl_high)
