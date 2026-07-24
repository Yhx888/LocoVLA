"""速度跟踪任务环境。"""

from __future__ import annotations

import numpy as np
from gymnasium import spaces

from upkie_mujoco_course.envs.observation import build_observation, observation_bounds
from upkie_mujoco_course.rewards.velocity import velocity_tracking_reward

from .base_env import BaseUpkieEnv


class VelocityEnv(BaseUpkieEnv):
    """带目标前向速度的环境。"""

    def __init__(
        self,
        target_velocity: float = 0.0,
        max_episode_steps: int | None = None,
        randomization: dict | None = None,
    ):
        self.target_velocity = float(target_velocity)
        super().__init__(
            max_episode_steps=max_episode_steps,
            randomization=randomization,
            env_config_path="configs/env/velocity.json",
        )
        low, high = observation_bounds(self.runner)
        self.observation_space = spaces.Box(
            np.concatenate([low, [-2.0]]),
            np.concatenate([high, [2.0]]),
            dtype=np.float64,
        )

    def _observation(self) -> np.ndarray:
        obs = build_observation(self.runner)
        noise_std = float(self.last_randomization.get("sensor_noise_std", 0.0))
        if noise_std > 0.0:
            obs = obs + self.np_random.normal(0.0, noise_std, size=obs.shape)
        values = np.concatenate([obs, [self.target_velocity]])
        return np.clip(values, self.observation_space.low, self.observation_space.high).astype(np.float64)

    def compute_reward_terms(self, state: dict[str, float | bool], action: np.ndarray) -> dict[str, float]:
        terms = super().compute_reward_terms(state, action)
        terms["velocity_tracking"] = velocity_tracking_reward(state, self.target_velocity)
        return terms
