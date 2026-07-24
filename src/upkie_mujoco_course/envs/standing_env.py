"""站立任务环境。"""

from __future__ import annotations

import numpy as np
from gymnasium import spaces

from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController

from .base_env import BaseUpkieEnv


class StandingEnv(BaseUpkieEnv):
    """从蹲姿站起并保持稳定的环境。"""

    pass


class WheelTorqueStandingEnv(StandingEnv):
    """保持腿部站姿，让纯 PPO 只从零学习两轮力矩。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wheel_action_ids = np.array(
            [self.runner.actuator_ids[item.name] for item in self.runner.spec.torque_actuators],
            dtype=int,
        )
        self.action_space = spaces.Box(-1.0, 1.0, shape=(len(self.wheel_action_ids),), dtype=np.float64)

    def step(self, action):
        wheel_action = np.clip(
            np.asarray(action, dtype=float).reshape(self.action_space.shape),
            self.action_space.low,
            self.action_space.high,
        )
        full_action = np.zeros(self.runner.model.nu, dtype=np.float64)
        full_action[self.wheel_action_ids] = wheel_action
        return BaseUpkieEnv.step(self, full_action)


class ResidualStandingEnv(BaseUpkieEnv):
    """让策略只学习经典控制器之上的归一化残差动作。"""

    def __init__(self, *args, residual_scale: float = 0.2, residual_clip: float = 1.0, **kwargs):
        if residual_scale < 0.0:
            raise ValueError("residual_scale 必须非负")
        if not 0.0 < residual_clip <= 1.0:
            raise ValueError("residual_clip 必须在 (0, 1] 内")
        super().__init__(*args, **kwargs)
        self.residual_scale = float(residual_scale)
        self.residual_clip = float(residual_clip)
        self.base_controller = WheelBalancerController()
        self.residual_mask = np.zeros(self.action_space.shape, dtype=np.float64)
        for actuator in self.runner.spec.torque_actuators:
            self.residual_mask[self.runner.actuator_ids[actuator.name]] = 1.0

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        self.base_controller.reset()
        return super().reset(seed=seed, options=options)

    def step(self, action):
        raw_residual = np.asarray(action, dtype=float).reshape(self.action_space.shape)
        residual_action = (
            np.clip(raw_residual, -self.residual_clip, self.residual_clip)
            * self.residual_mask
        )
        base_physical = self.base_controller.compute_action(self.runner, self.runner.time)
        base_action = self.to_normalized_action(base_physical)
        applied_action = np.clip(
            base_action + self.residual_scale * residual_action,
            self.action_space.low,
            self.action_space.high,
        )
        observation, reward, terminated, truncated, info = super().step(applied_action)
        info.update(
            {
                "base_action": base_action.copy(),
                "residual_action": residual_action.copy(),
                "applied_action": applied_action.copy(),
            }
        )
        return observation, reward, terminated, truncated, info
