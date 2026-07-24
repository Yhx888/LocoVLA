"""Gymnasium 基础环境。

Gymnasium 是强化学习的标准环境接口，核心流程：
1. env.reset() -> 获取初始观测
2. env.step(action) -> 执行动作，返回 (观测, 奖励, 是否结束, 是否截断, 信息)
3. 重复步骤 2 直到 episode 结束

本模块将 MuJoCo 仿真封装为 Gymnasium 环境，供 RL 算法（如 PPO）训练。
"""

from __future__ import annotations

from collections import deque
from typing import Any

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces

from upkie_mujoco_course.controllers.action_filter import LowPassActionFilter, limit_action_delta
from upkie_mujoco_course.envs.action_adapter import adapt_action
from upkie_mujoco_course.envs.observation import build_observation, observation_bounds
from upkie_mujoco_course.envs.termination import is_fallen
from upkie_mujoco_course.randomization.dynamics import sample_episode_randomization
from upkie_mujoco_course.randomization.dynamics import validate_randomization_config
from upkie_mujoco_course.randomization.pushes import push_is_active
from upkie_mujoco_course.randomization.terrain import apply_terrain, sample_terrain_config, validate_terrain_config
from upkie_mujoco_course.sim.runner import SimulationRunner
from upkie_mujoco_course.utils.config import load_json_config


class BaseUpkieEnv(gym.Env):
    """Upkie Gymnasium 环境基类。

    将 MuJoCo Upkie 仿真封装为标准 Gymnasium 环境，支持：
    - reset()：重置到初始姿态
    - step(action)：执行动作，返回五元组
    - 自动终止：机器人摔倒时 terminated=True
    - 自动截断：超过最大步数时 truncated=True
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        max_episode_steps: int | None = None,
        initial_pose: str = "stand",
        randomization: dict[str, Any] | None = None,
        env_config_path: str = "configs/env/standing.json",
    ):
        super().__init__()
        self.env_config = load_json_config(env_config_path)
        self.action_config = load_json_config("configs/control/action_adapter.json")
        self.randomization = load_json_config("configs/randomization/default.json")
        if randomization:
            self.randomization.update(randomization)
        validate_randomization_config(self.randomization)
        validate_terrain_config(self.randomization)
        self.runner = SimulationRunner()
        configured_steps = int(self.env_config["max_episode_steps"])
        self.max_episode_steps = configured_steps if max_episode_steps is None else int(max_episode_steps)
        self.initial_pose = initial_pose
        self.elapsed_steps = 0
        self.previous_action = np.zeros(self.runner.model.nu, dtype=np.float64)
        self.neutral_action = self._neutral_action()
        leg_scale = float(self.action_config["leg_position_scale"])
        wheel_scale = float(self.action_config["wheel_torque_scale"])
        self.action_scale = np.array([leg_scale] * 4 + [wheel_scale] * 2, dtype=np.float64)
        # 动作滤波器配置：默认 alpha=0/max_delta=0 表示直通（关闭滤波），保持与历史行为一致
        filter_cfg = self.action_config.get("action_filter", {})
        self._action_filter_alpha = float(filter_cfg.get("low_pass_alpha", 0.0))
        self._action_filter_max_delta = float(filter_cfg.get("max_delta", 0.0))
        self._action_filter = LowPassActionFilter(alpha=self._action_filter_alpha, size=self.runner.model.nu)
        self._previous_physical_action = self.neutral_action.copy()
        self._base_mass = self.runner.model.body_mass.copy()
        self._base_inertia = self.runner.model.body_inertia.copy()
        self._base_ipos = self.runner.model.body_ipos.copy()
        self._base_friction = self.runner.model.geom_friction.copy()
        self._base_damping = self.runner.model.dof_damping.copy()
        self._base_actuator_gain = self.runner.model.actuator_gainprm.copy()
        self._base_actuator_bias = self.runner.model.actuator_biasprm.copy()
        self._base_gravity = self.runner.model.opt.gravity.copy()
        self.last_randomization = dict(self.randomization)
        self.last_runtime_randomization: dict[str, float | int] = {}
        self._sensor_noise_std = 0.0
        self._action_delay_steps = 0
        self.last_terrain: dict[str, float] = {"slope_deg": 0.0, "roughness": 0.0}
        self._delayed_actions: deque[np.ndarray] = deque()
        self.runner.reset("stand")
        self.target_standing_height = float(
            self.env_config.get(
                "target_standing_height",
                self.runner.posture_state()["base_height"],
            )
        )
        if initial_pose != "stand":
            self.runner.reset(initial_pose)
        low, high = observation_bounds(self.runner)
        self.observation_space = spaces.Box(low, high, dtype=np.float64)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(self.runner.model.nu,), dtype=np.float64)

    def _neutral_action(self) -> np.ndarray:
        neutral = np.zeros(self.runner.model.nu, dtype=np.float64)
        stand = self.runner.spec.default_pose["stand"]
        for actuator in self.runner.spec.position_actuators:
            neutral[self.runner.actuator_ids[actuator.name]] = stand[actuator.joint]
        return neutral

    def _sample_scale(self, value: Any) -> float:
        if isinstance(value, list):
            return float(self.np_random.uniform(float(value[0]), float(value[1])))
        return float(value)

    def to_physical_action(self, action: np.ndarray) -> np.ndarray:
        physical = adapt_action(
            action,
            self.neutral_action,
            self.action_scale,
            self.runner.ctrl_low,
            self.runner.ctrl_high,
        )
        # 动作滤波：低通 + 增量限制。alpha=0/max_delta=0 时为直通，保持历史行为
        if self._action_filter_alpha > 0.0:
            physical = self._action_filter.filter(physical)
        if self._action_filter_max_delta > 0.0:
            physical = limit_action_delta(physical, self._previous_physical_action, self._action_filter_max_delta)
        self._previous_physical_action = physical.copy()
        return physical

    def to_normalized_action(self, action: np.ndarray) -> np.ndarray:
        physical = np.asarray(action, dtype=float).reshape(self.action_space.shape)
        return np.clip((physical - self.neutral_action) / self.action_scale, -1.0, 1.0)

    def _apply_reset_randomization(self) -> None:
        self.last_randomization = sample_episode_randomization(self.randomization, self.np_random)
        self.runner.model.body_mass[:] = self._base_mass
        self.runner.model.body_inertia[:] = self._base_inertia
        self.runner.model.body_ipos[:] = self._base_ipos
        self.runner.model.geom_friction[:] = self._base_friction
        self.runner.model.dof_damping[:] = self._base_damping
        self.runner.model.actuator_gainprm[:] = self._base_actuator_gain
        self.runner.model.actuator_biasprm[:] = self._base_actuator_bias
        # 地形随机化：恢复默认重力后按采样 slope 倾斜重力向量模拟斜坡
        self.runner.model.opt.gravity[:] = self._base_gravity
        self.last_terrain = sample_terrain_config(self.randomization, self.np_random)
        apply_terrain(self.runner.model, self.last_terrain)
        mass_scale = float(self.last_randomization.get("mass_scale", 1.0))
        inertia_scale = float(self.last_randomization.get("inertia_scale", 1.0))
        com_offset_m = float(self.last_randomization.get("com_offset_m", 0.0))
        friction_scale = float(self.last_randomization.get("friction_scale", 1.0))
        joint_damping = self.last_randomization.get("joint_damping")
        actuator_scale = float(self.last_randomization.get("actuator_strength_scale", 1.0))
        self.runner.model.body_mass[:] *= mass_scale
        self.runner.model.body_inertia[:] *= inertia_scale
        base_id = self.runner.frame_map.body_ids[self.runner.spec.base_body]
        self.runner.model.body_ipos[base_id, 0] += com_offset_m
        self.runner.model.geom_friction[:, 0] *= friction_scale
        if joint_damping is not None:
            controlled_dofs = [
                self.runner.joint_map.dofadr[name]
                for name in self.runner.spec.controlled_joints
            ]
            self.runner.model.dof_damping[controlled_dofs] = float(joint_damping)
        self.runner.model.actuator_gainprm[:, 0] *= actuator_scale
        self.runner.model.actuator_biasprm[:, 1] *= actuator_scale
        self._sensor_noise_std = float(self.last_randomization.get("sensor_noise_std", 0.0))
        state_std = float(self.last_randomization.get("initial_state_std", 0.0))
        if state_std > 0.0:
            for name in self.runner.spec.controlled_joints:
                self.runner.data.qpos[self.runner.joint_map.qposadr[name]] += self.np_random.normal(0.0, state_std)
            self.runner.data.qvel[:] += self.np_random.normal(0.0, state_std, size=self.runner.model.nv)
        mujoco.mj_forward(self.runner.model, self.runner.data)

    @staticmethod
    def _applied_scale(current: np.ndarray, baseline: np.ndarray) -> float:
        mask = np.abs(baseline) > 1e-12
        if not np.any(mask):
            return 1.0
        return float(np.median(current[mask] / baseline[mask]))

    def _runtime_randomization(self) -> dict[str, float | int]:
        base_id = self.runner.frame_map.body_ids[self.runner.spec.base_body]
        return {
            "mass_scale": self._applied_scale(self.runner.model.body_mass, self._base_mass),
            "inertia_scale": self._applied_scale(self.runner.model.body_inertia, self._base_inertia),
            "com_offset_m": float(self.runner.model.body_ipos[base_id, 0] - self._base_ipos[base_id, 0]),
            "friction_scale": self._applied_scale(
                self.runner.model.geom_friction[:, 0], self._base_friction[:, 0]
            ),
            "joint_damping": float(np.mean([
                self.runner.model.dof_damping[self.runner.joint_map.dofadr[name]]
                for name in self.runner.spec.controlled_joints
            ])),
            "actuator_strength_scale": self._applied_scale(
                self.runner.model.actuator_gainprm[:, 0], self._base_actuator_gain[:, 0]
            ),
            "sensor_noise_std": float(self._sensor_noise_std),
            "action_delay_steps": int(self._action_delay_steps),
        }

    def _observation(self) -> np.ndarray:
        obs = build_observation(self.runner)
        noise_std = self._sensor_noise_std
        if noise_std > 0.0:
            obs = obs + self.np_random.normal(0.0, noise_std, size=obs.shape)
        return np.clip(obs, self.observation_space.low, self.observation_space.high).astype(np.float64)

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        """重置环境到初始姿态，返回初始观测。"""
        super().reset(seed=seed)
        initial_pose = self.initial_pose if options is None else options.get("initial_pose", self.initial_pose)
        self.elapsed_steps = 0
        self.previous_action[:] = 0.0
        # 重置动作滤波器与上一物理动作状态，避免跨 episode 状态泄漏
        self._action_filter.reset()
        self._previous_physical_action = self.neutral_action.copy()
        self.runner.reset(str(initial_pose))
        self._apply_reset_randomization()
        delay = max(0, int(self.last_randomization.get("action_delay_steps", 0)))
        self._action_delay_steps = delay
        self._delayed_actions = deque([self.neutral_action.copy() for _ in range(delay)])
        self.last_runtime_randomization = self._runtime_randomization()
        obs = self._observation()
        return obs.astype(np.float64), {
            "time": self.runner.time,
            "initial_pose": initial_pose,
            "randomization": dict(self.last_randomization),
            "runtime_randomization": dict(self.last_runtime_randomization),
            "terrain": dict(self.last_terrain),
        }

    def step(self, action, *, emergency_stop: bool = False):
        """执行一步仿真，返回 (obs, reward, terminated, truncated, info)。

        - terminated: 机器人摔倒时为 True
        - truncated: 达到最大步数时为 True
        """
        normalized_action = np.clip(
            np.asarray(action, dtype=float).reshape(self.runner.model.nu),
            -1.0,
            1.0,
        )
        if emergency_stop:
            normalized_action = np.zeros(self.action_space.shape, dtype=np.float64)
            physical_action = self.neutral_action.copy()
            self._delayed_actions.clear()
            self._action_filter.reset()
            self._previous_physical_action = physical_action.copy()
        else:
            physical_action = self.to_physical_action(normalized_action)
        if self._delayed_actions and not emergency_stop:
            self._delayed_actions.append(physical_action)
            applied_action = self._delayed_actions.popleft()
        else:
            applied_action = physical_action
        self.runner.data.xfrc_applied[:] = 0.0
        push_step = int(self.last_randomization.get("push_step", -1))
        push_duration = max(0, int(self.last_randomization.get("push_duration_steps", 0)))
        push_applied = push_is_active(self.elapsed_steps, push_step, push_duration)
        if push_applied:
            base_id = self.runner.frame_map.body_ids[self.runner.spec.base_body]
            self.runner.data.xfrc_applied[base_id, 0] = float(self.last_randomization.get("push_force", 0.0))
        self.runner.step(applied_action)
        self.runner.data.xfrc_applied[:] = 0.0
        self.elapsed_steps += 1
        state = self.runner.posture_state()
        reward_terms = self.compute_reward_terms(state, normalized_action)
        scales = self.env_config["reward_scales"]
        reward = sum(float(scales.get(name, 0.0)) * value for name, value in reward_terms.items())
        termination = self.env_config["termination"]
        terminated = bool(is_fallen(state, termination["max_pitch_rad"], termination["min_height"]))
        truncated = bool(not terminated and self.elapsed_steps >= self.max_episode_steps)
        obs = self._observation()
        info = {
            "time": self.runner.time,
            **state,
            "reward_terms": reward_terms,
            "physical_action": applied_action.copy(),
            "emergency_stop": bool(emergency_stop),
            "push_applied": bool(push_applied),
            "terrain": dict(self.last_terrain),
            "runtime_randomization": dict(self.last_runtime_randomization),
        }
        self.previous_action = normalized_action.copy()
        return obs.astype(np.float64), float(reward), terminated, truncated, info

    def compute_reward_terms(self, state: dict[str, float | bool], action: np.ndarray) -> dict[str, float]:
        pitch = float(state["pitch_error"])
        height_error = float(state["base_height"]) - self.target_standing_height
        x_position = float(state["x_position"])
        return {
            "alive": 1.0 if bool(state["both_wheels_contact"]) else 0.0,
            "upright": float(np.exp(-4.0 * pitch * pitch)),
            "height": float(np.exp(-10.0 * height_error * height_error)),
            "position": -x_position * x_position,
            "effort": -float(np.mean(np.square(action))),
            "smoothness": -float(np.mean(np.square(action - self.previous_action))),
        }

    def close(self):
        """关闭仿真器，释放资源。"""
        self.runner.close()
