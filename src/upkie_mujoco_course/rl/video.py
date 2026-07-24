"""策略录像工具。"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

import imageio.v2 as imageio
import mujoco
import numpy as np
from stable_baselines3 import PPO

from upkie_mujoco_course.controllers.lqr import LQRBalanceController
from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.envs.standing_env import ResidualStandingEnv, StandingEnv, WheelTorqueStandingEnv
from upkie_mujoco_course.rl.evaluate import load_checkpoint_metadata, residual_checkpoint_metadata, validate_loaded_residual_policy
from upkie_mujoco_course.utils.paths import ensure_output_dir


def next_video_path(name: str = "upkie_demo.mp4") -> Path:
    return ensure_output_dir("videos") / name


@dataclass(frozen=True)
class VideoResult:
    path: Path
    frame_count: int
    duration: float
    max_pitch_rad: float


def record_policy_video(
    path: str | Path,
    duration: float = 5.0,
    fps: int = 30,
    mode: str = "classic",
    model_path: str | Path | None = None,
    residual_scale: float = 0.2,
    seed: int = 0,
    width: int = 640,
    height: int = 480,
) -> VideoResult:
    """离屏运行策略并写出 MP4，同时返回可用于验收的物理指标。"""

    if mode not in {"zero", "classic", "lqr", "rl", "residual"}:
        raise ValueError(f"未知录像模式: {mode}")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    max_episode_steps = max(2, int(duration / 0.01) + 1)
    residual_metadata = None
    if mode == "residual":
        if model_path is None or not Path(model_path).exists():
            raise FileNotFoundError(f"找不到策略模型: {model_path}")
        residual_metadata = residual_checkpoint_metadata(model_path, residual_scale)
        env = ResidualStandingEnv(
            max_episode_steps=max_episode_steps,
            residual_scale=float(residual_metadata["residual_scale"]),
            residual_clip=float(residual_metadata.get("residual_clip", 1.0)),
        )
    elif mode == "rl":
        if model_path is None or not Path(model_path).exists():
            raise FileNotFoundError(f"找不到策略模型: {model_path}")
        metadata = load_checkpoint_metadata(model_path)
        if metadata.get("training_mode") == "wheel_torque":
            env = WheelTorqueStandingEnv(max_episode_steps=max_episode_steps)
        elif metadata.get("training_mode") == "full_action":
            env = StandingEnv(max_episode_steps=max_episode_steps)
        else:
            raise ValueError(f"不支持的站立 PPO 训练模式: {metadata.get('training_mode')}")
    else:
        env = StandingEnv(max_episode_steps=max_episode_steps)
    model = None
    if mode in {"rl", "residual"}:
        if model_path is None or not Path(model_path).exists():
            env.close()
            raise FileNotFoundError(f"找不到策略模型: {model_path}")
        model = PPO.load(str(model_path))
        if mode == "residual":
            try:
                validate_loaded_residual_policy(model, residual_metadata)
            except ValueError:
                env.close()
                raise
        model.set_env(env)
    classic = WheelBalancerController()
    lqr = LQRBalanceController()
    renderer = mujoco.Renderer(env.runner.model, height=height, width=width)
    writer = imageio.get_writer(output, fps=fps, codec="libx264", quality=8, macro_block_size=None)
    frame_count = 0
    max_pitch = 0.0
    try:
        observation, _ = env.reset(seed=seed)
        next_frame_time = 0.0
        terminated = truncated = False
        while env.runner.time < duration and not (terminated or truncated):
            if env.runner.time + 1e-12 >= next_frame_time:
                renderer.update_scene(env.runner.data)
                writer.append_data(renderer.render())
                frame_count += 1
                next_frame_time += 1.0 / fps
            if mode == "zero":
                action = np.zeros(env.action_space.shape, dtype=env.action_space.dtype)
            elif mode == "classic":
                physical = classic.compute_action(env.runner, env.runner.time)
                action = env.to_normalized_action(physical)
            elif mode == "lqr":
                action = env.to_normalized_action(lqr.compute_action(env.runner))
            elif mode == "rl":
                action, _ = model.predict(observation, deterministic=True)
            else:
                action, _ = model.predict(observation, deterministic=True)
            observation, _, terminated, truncated, info = env.step(action)
            max_pitch = max(max_pitch, abs(float(info["pitch"])))
        return VideoResult(output, frame_count, env.runner.time, max_pitch)
    finally:
        writer.close()
        renderer.close()
        env.close()
