"""SB3 训练入口。"""

from __future__ import annotations

import json
from pathlib import Path

from stable_baselines3 import PPO

from upkie_mujoco_course.envs.standing_env import ResidualStandingEnv, WheelTorqueStandingEnv
from upkie_mujoco_course.envs.velocity_env import VelocityEnv
from upkie_mujoco_course.utils.config import load_json_config
from upkie_mujoco_course.utils.paths import ensure_output_dir


def _train_ppo(
    env,
    config_path: str,
    checkpoint_name: str,
    total_timesteps: int | None,
    seed: int | None,
    profile: str,
    output_dir: str | Path | None = None,
    tensorboard_dir: str | Path | None = None,
    training_mode: str = "full_action",
    metadata: dict[str, object] | None = None,
) -> Path:
    config = load_json_config(config_path)
    profiles = config["profiles"]
    if profile not in profiles:
        raise ValueError(f"未知训练档位: {profile}")
    settings = profiles[profile]
    total_timesteps = int(settings["total_timesteps"] if total_timesteps is None else total_timesteps)
    # 若调用方未指定 seed，则使用配置文件中的 seed（可复现性默认值）
    seed = int(config.get("seed", 0)) if seed is None else int(seed)
    n_steps = max(2, min(int(settings["n_steps"]), max(2, total_timesteps)))
    batch_size = max(2, min(int(settings["batch_size"]), n_steps))
    checkpoint_metadata = {
        "schema_version": "1.0",
        "algorithm": "PPO",
        "training_mode": training_mode,
        "total_timesteps": total_timesteps,
        "seed": seed,
        "profile": profile,
        **(metadata or {}),
    }
    try:
        model = PPO(
            "MlpPolicy",
            env,
            verbose=0,
            seed=int(seed),
            n_steps=n_steps,
            batch_size=batch_size,
            learning_rate=float(settings["learning_rate"]),
            gamma=float(settings["gamma"]),
            tensorboard_log=str(
                Path(tensorboard_dir)
                if tensorboard_dir is not None
                else ensure_output_dir("tensorboard")
            ),
        )
        model.training_mode = training_mode
        model.training_metadata = checkpoint_metadata
        model.learn(total_timesteps=total_timesteps)
        checkpoint_dir = Path(output_dir) if output_dir is not None else ensure_output_dir("checkpoints")
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        output = checkpoint_dir / checkpoint_name
        model.save(output)
        metadata_path = output.with_suffix(".metadata.json")
        metadata_path.write_text(
            json.dumps(
                checkpoint_metadata,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return output
    finally:
        env.close()


def train_ppo_standing(
    total_timesteps: int | None = None,
    seed: int | None = None,
    profile: str = "smoke",
    output_dir: str | Path | None = None,
    tensorboard_dir: str | Path | None = None,
) -> Path:
    """训练站立策略并保存可重新加载的模型。"""

    return _train_ppo(
        WheelTorqueStandingEnv(max_episode_steps=200),
        "configs/rl/ppo_standing.json",
        "ppo_standing_latest.zip",
        total_timesteps,
        seed,
        profile,
        output_dir,
        tensorboard_dir,
        training_mode="wheel_torque",
    )


def train_ppo_velocity(
    total_timesteps: int | None = None,
    seed: int | None = None,
    profile: str = "smoke",
    target_velocity: float = 0.3,
    output_dir: str | Path | None = None,
    tensorboard_dir: str | Path | None = None,
) -> Path:
    """训练带目标速度观测的速度跟踪策略。"""

    return _train_ppo(
        VelocityEnv(target_velocity=target_velocity, max_episode_steps=200),
        "configs/rl/ppo_velocity.json",
        "ppo_velocity_latest.zip",
        total_timesteps,
        seed,
        profile,
        output_dir,
        tensorboard_dir,
        training_mode="velocity_full_action",
    )


def train_ppo_residual_standing(
    total_timesteps: int | None = None,
    seed: int | None = None,
    profile: str = "smoke",
    residual_scale: float = 0.2,
    residual_clip: float = 1.0,
    output_dir: str | Path | None = None,
    tensorboard_dir: str | Path | None = None,
) -> Path:
    """训练始终输出残差动作的 PPO 策略。"""

    return _train_ppo(
        ResidualStandingEnv(
            max_episode_steps=200,
            residual_scale=residual_scale,
            residual_clip=residual_clip,
        ),
        "configs/rl/ppo_standing.json",
        "ppo_residual_latest.zip",
        total_timesteps,
        seed,
        profile,
        output_dir,
        tensorboard_dir,
        training_mode="residual",
        metadata={
            "residual_scale": float(residual_scale),
            "residual_clip": float(residual_clip),
        },
    )
