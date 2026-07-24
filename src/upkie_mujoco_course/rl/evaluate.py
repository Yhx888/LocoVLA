"""策略评估。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO

from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.envs.standing_env import ResidualStandingEnv, StandingEnv, WheelTorqueStandingEnv


def load_checkpoint_metadata(model_path: str | Path) -> dict[str, object]:
    path = Path(model_path)
    metadata_path = path.with_suffix(".metadata.json")
    if not metadata_path.is_file():
        raise ValueError(f"checkpoint 缺少训练模式元数据: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("checkpoint 元数据必须是 JSON 对象")
    return metadata


def residual_checkpoint_metadata(model_path: str | Path, residual_scale: float) -> dict[str, object]:
    metadata = load_checkpoint_metadata(model_path)
    if metadata.get("training_mode") != "residual":
        raise ValueError("residual 模式只能加载 training_mode=residual 的 checkpoint")
    for field in ("residual_scale", "residual_clip"):
        if field not in metadata:
            raise ValueError(f"residual checkpoint 元数据缺少 {field}")
    try:
        trained_scale = float(metadata["residual_scale"])
        float(metadata["residual_clip"])
    except (TypeError, ValueError) as exc:
        raise ValueError("residual_scale 和 residual_clip 必须是数值") from exc
    if not np.isclose(trained_scale, residual_scale):
        raise ValueError(f"residual_scale 与训练元数据不一致: {residual_scale} != {trained_scale}")
    return metadata


def validate_loaded_residual_policy(model: PPO, metadata: dict[str, object]) -> None:
    embedded_mode = getattr(model, "training_mode", None)
    embedded_metadata = getattr(model, "training_metadata", {})
    if embedded_mode != "residual":
        raise ValueError("checkpoint 内嵌训练模式不是 residual")
    if not isinstance(embedded_metadata, dict) or embedded_metadata.get("training_mode") != "residual":
        raise ValueError("checkpoint 内嵌训练元数据无效")
    trained_scale = float(metadata["residual_scale"])
    if not np.isclose(float(embedded_metadata.get("residual_scale", -1.0)), trained_scale):
        raise ValueError("checkpoint 内嵌 residual_scale 与旁车元数据不一致")


def evaluate_policy(
    model_path: str | Path | None = None,
    episodes: int = 1,
    mode: str = "zero",
    residual_scale: float = 0.2,
    seed: int = 0,
    return_records: bool = False,
    randomization: dict | None = None,
) -> list[float] | list[dict[str, float | int | bool]]:
    """评估零动作、经典控制、RL 或残差策略。"""

    if mode not in {"zero", "classic", "rl", "residual"}:
        raise ValueError(f"未知评估模式: {mode}")
    if mode == "residual":
        if model_path is None or not Path(model_path).exists():
            raise FileNotFoundError(f"找不到策略模型: {model_path}")
        metadata = residual_checkpoint_metadata(model_path, residual_scale)
        env = ResidualStandingEnv(
            max_episode_steps=200,
            residual_scale=float(metadata["residual_scale"]),
            residual_clip=float(metadata.get("residual_clip", 1.0)),
            randomization=randomization,
        )
    elif mode == "rl":
        if model_path is None or not Path(model_path).exists():
            raise FileNotFoundError(f"找不到策略模型: {model_path}")
        metadata = load_checkpoint_metadata(model_path)
        training_mode = metadata.get("training_mode")
        if training_mode == "wheel_torque":
            env = WheelTorqueStandingEnv(max_episode_steps=200, randomization=randomization)
        elif training_mode == "full_action":
            env = StandingEnv(max_episode_steps=200, randomization=randomization)
        else:
            raise ValueError(f"不支持的站立 PPO 训练模式: {training_mode}")
    else:
        env = StandingEnv(max_episode_steps=200, randomization=randomization)
    model = None
    if mode in {"rl", "residual"}:
        if model_path is None or not Path(model_path).exists():
            env.close()
            raise FileNotFoundError(f"找不到策略模型: {model_path}")
        model = PPO.load(str(model_path))
        if mode == "residual":
            try:
                validate_loaded_residual_policy(model, metadata)
            except ValueError:
                env.close()
                raise
        elif mode == "rl":
            embedded_metadata = getattr(model, "training_metadata", {})
            if (
                not isinstance(embedded_metadata, dict)
                or embedded_metadata.get("training_mode") != metadata.get("training_mode")
            ):
                env.close()
                raise ValueError("checkpoint 内嵌训练模式与旁车元数据不一致")
        model.set_env(env)
    classic = WheelBalancerController()
    records: list[dict[str, float | int | bool]] = []
    try:
        for episode in range(int(episodes)):
            obs, _ = env.reset(seed=int(seed) + episode)
            classic.reset()
            total = 0.0
            max_abs_pitch = 0.0
            max_abs_residual = 0.0
            terminated = False
            truncated = False
            while not (terminated or truncated):
                if mode == "zero":
                    action = np.zeros(env.action_space.shape, dtype=env.action_space.dtype)
                elif mode == "classic":
                    action = env.to_normalized_action(classic.compute_action(env.runner, env.runner.time))
                elif mode == "rl":
                    action, _ = model.predict(obs, deterministic=True)
                else:
                    action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                total += float(reward)
                max_abs_pitch = max(max_abs_pitch, abs(float(info["pitch_error"])))
                if mode == "residual":
                    max_abs_residual = max(
                        max_abs_residual,
                        float(np.max(np.abs(info["residual_action"]))),
                    )
            records.append(
                {
                    "seed": int(seed) + episode,
                    "return": total,
                    "success": bool(not terminated and truncated),
                    "fell": bool(terminated),
                    "max_abs_pitch_rad": max_abs_pitch,
                    "max_abs_residual_action": max_abs_residual,
                }
            )
        if return_records:
            return records
        return [float(record["return"]) for record in records]
    finally:
        env.close()
