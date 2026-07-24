"""Gymnasium 环境注册。"""

from __future__ import annotations

from gymnasium.envs.registration import register


def register_envs() -> None:
    """注册课程环境，重复注册时由调用方忽略。"""

    try:
        register(id="UpkieStanding-v0", entry_point="upkie_mujoco_course.envs.standing_env:StandingEnv")
        register(id="UpkieVelocity-v0", entry_point="upkie_mujoco_course.envs.velocity_env:VelocityEnv")
    except Exception:
        return

