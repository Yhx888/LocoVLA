"""观测构造。"""

from __future__ import annotations

import numpy as np


OBSERVATION_NAMES = (
    "pitch_error",
    "pitch_rate",
    "base_height",
    "x_position",
    "forward_velocity",
    "left_hip_position",
    "left_knee_position",
    "right_hip_position",
    "right_knee_position",
    "left_hip_velocity",
    "left_knee_velocity",
    "right_hip_velocity",
    "right_knee_velocity",
    "left_wheel_velocity",
    "right_wheel_velocity",
)


def observation_bounds(runner) -> tuple[np.ndarray, np.ndarray]:
    low = np.array([-np.pi, -50.0, -1.0, -20.0, -10.0] + [-np.pi] * 4 + [-50.0] * 4 + [-100.0] * 2)
    high = np.array([np.pi, 50.0, 2.0, 20.0, 10.0] + [np.pi] * 4 + [50.0] * 4 + [100.0] * 2)
    return low.astype(np.float64), high.astype(np.float64)


def build_observation(runner) -> np.ndarray:
    state = runner.posture_state()
    leg_positions = [runner.data.qpos[runner.joint_map.qposadr[name]] for name in runner.spec.leg_joints]
    leg_velocities = [runner.data.qvel[runner.joint_map.dofadr[name]] for name in runner.spec.leg_joints]
    wheel_velocities = [runner.data.qvel[runner.joint_map.dofadr[name]] for name in runner.spec.wheel_joints]
    values = [
        state["pitch_error"],
        state["pitch_rate"],
        state["base_height"],
        state["x_position"],
        state["forward_velocity"],
        *leg_positions,
        *leg_velocities,
        *wheel_velocities,
    ]
    low, high = observation_bounds(runner)
    return np.clip(np.asarray(values, dtype=np.float64), low, high)
