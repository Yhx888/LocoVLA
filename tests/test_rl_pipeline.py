"""测试 RL 训练 / 评估流水线。

覆盖场景：
- PPO 模型构建与回调配置
- 训练流水线短时运行可完成
- 评估流水线产出录像 / 指标
"""
import json
from pathlib import Path

import numpy as np
import pytest

from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.envs.standing_env import ResidualStandingEnv, StandingEnv
from upkie_mujoco_course.rl.evaluate import evaluate_policy
from upkie_mujoco_course.rl.train_sb3 import (
    train_ppo_residual_standing,
    train_ppo_standing,
    train_ppo_velocity,
)
from upkie_mujoco_course.rl.video import record_policy_video


def test_classic_evaluation_returns_finite_episode_score():
    returns = evaluate_policy(episodes=1, mode="classic")
    assert len(returns) == 1
    assert np.isfinite(returns[0])


def test_classic_evaluation_is_reproducible_for_fixed_seed():
    first = evaluate_policy(episodes=1, mode="classic", seed=11)
    second = evaluate_policy(episodes=1, mode="classic", seed=11)
    assert first == second


def test_rl_evaluation_requires_existing_checkpoint():
    with pytest.raises(FileNotFoundError):
        evaluate_policy("outputs/checkpoints/missing.zip", episodes=1, mode="rl")


def test_smoke_training_saves_loadable_checkpoint(tmp_path):
    reference_paths = [
        Path("outputs/checkpoints/ppo_standing_latest.zip"),
        Path("outputs/checkpoints/ppo_standing_latest.metadata.json"),
    ]
    before = {
        path: path.read_bytes() if path.exists() else None
        for path in reference_paths
    }
    repository_tensorboard = Path("outputs/tensorboard")
    tensorboard_before = {
        path.relative_to(repository_tensorboard): path.read_bytes()
        for path in repository_tensorboard.rglob("*")
        if path.is_file()
    }
    temporary_tensorboard = tmp_path / "tensorboard"

    path = train_ppo_standing(
        total_timesteps=16,
        seed=0,
        profile="smoke",
        output_dir=tmp_path,
        tensorboard_dir=temporary_tensorboard,
    )

    assert path.parent == tmp_path
    assert Path(path).exists()
    metadata = json.loads(path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    assert metadata["training_mode"] == "wheel_torque"
    returns = evaluate_policy(path, episodes=1, mode="rl")
    assert len(returns) == 1
    after = {
        reference: reference.read_bytes() if reference.exists() else None
        for reference in reference_paths
    }
    assert after == before
    assert any(temporary_tensorboard.rglob("events.out.tfevents.*"))
    tensorboard_after = {
        path.relative_to(repository_tensorboard): path.read_bytes()
        for path in repository_tensorboard.rglob("*")
        if path.is_file()
    }
    assert tensorboard_after == tensorboard_before


def test_zero_residual_matches_classic_controller_step_by_step():
    classic_env = StandingEnv(max_episode_steps=8)
    residual_env = ResidualStandingEnv(max_episode_steps=8, residual_scale=0.2)
    controller = WheelBalancerController()
    try:
        classic_obs, _ = classic_env.reset(seed=17)
        residual_obs, _ = residual_env.reset(seed=17)
        controller.reset()
        np.testing.assert_allclose(residual_obs, classic_obs)

        for _ in range(8):
            base = classic_env.to_normalized_action(
                controller.compute_action(classic_env.runner, classic_env.runner.time)
            )
            classic_step = classic_env.step(base)
            residual_step = residual_env.step(np.zeros(residual_env.action_space.shape))
            np.testing.assert_allclose(residual_step[0], classic_step[0])
            assert residual_step[1:4] == classic_step[1:4]
            np.testing.assert_allclose(residual_step[4]["base_action"], base)
            np.testing.assert_allclose(residual_step[4]["residual_action"], 0.0)
            np.testing.assert_allclose(residual_step[4]["applied_action"], base)
    finally:
        classic_env.close()
        residual_env.close()


def test_residual_environment_only_modifies_torque_actuators():
    env = ResidualStandingEnv(max_episode_steps=2, residual_scale=0.2)
    try:
        env.reset(seed=0)
        _, _, _, _, info = env.step(np.ones(env.action_space.shape))
        leg_ids = [env.runner.actuator_ids[item.name] for item in env.runner.spec.position_actuators]
        wheel_ids = [env.runner.actuator_ids[item.name] for item in env.runner.spec.torque_actuators]

        np.testing.assert_allclose(info["residual_action"][leg_ids], 0.0)
        np.testing.assert_allclose(info["residual_action"][wheel_ids], 1.0)
    finally:
        env.close()


def test_residual_training_uses_independent_checkpoint_and_metadata(tmp_path):
    path = train_ppo_residual_standing(
        total_timesteps=16,
        seed=3,
        profile="smoke",
        residual_scale=0.2,
        output_dir=tmp_path,
        tensorboard_dir=tmp_path / "tensorboard",
    )
    metadata_path = path.with_suffix(".metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert path.name == "ppo_residual_latest.zip"
    assert metadata["training_mode"] == "residual"
    assert metadata["residual_scale"] == pytest.approx(0.2)
    assert len(evaluate_policy(path, episodes=1, mode="residual", seed=3)) == 1

    records = evaluate_policy(
        path,
        episodes=1,
        mode="residual",
        seed=3,
        return_records=True,
    )
    assert {
        "success",
        "fell",
        "max_abs_pitch_rad",
        "max_abs_residual_action",
    } <= set(records[0])


def test_full_action_checkpoint_cannot_be_evaluated_as_residual(tmp_path):
    path = train_ppo_standing(
        total_timesteps=16,
        seed=4,
        profile="smoke",
        output_dir=tmp_path,
        tensorboard_dir=tmp_path / "tensorboard",
    )

    with pytest.raises(ValueError, match="residual"):
        evaluate_policy(path, episodes=1, mode="residual", seed=4)


def test_tampered_sidecar_cannot_turn_full_action_checkpoint_into_residual(tmp_path):
    path = train_ppo_standing(
        total_timesteps=16,
        seed=5,
        profile="smoke",
        output_dir=tmp_path,
        tensorboard_dir=tmp_path / "tensorboard",
    )
    metadata_path = path.with_suffix(".metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update({"training_mode": "residual", "residual_scale": 0.2, "residual_clip": 1.0})
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="checkpoint 内嵌"):
        evaluate_policy(path, episodes=1, mode="residual", seed=5)


def test_residual_checkpoint_rejects_incomplete_sidecar_metadata(tmp_path):
    path = train_ppo_residual_standing(
        total_timesteps=16,
        seed=7,
        profile="smoke",
        output_dir=tmp_path,
        tensorboard_dir=tmp_path / "tensorboard",
    )
    metadata_path = path.with_suffix(".metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.pop("residual_scale")
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="residual_scale"):
        evaluate_policy(path, episodes=1, mode="residual", seed=7)


def test_residual_video_rejects_full_action_checkpoint(tmp_path):
    path = train_ppo_standing(
        total_timesteps=16,
        seed=6,
        profile="smoke",
        output_dir=tmp_path,
        tensorboard_dir=tmp_path / "tensorboard",
    )

    with pytest.raises(ValueError, match="residual"):
        record_policy_video(
            tmp_path / "invalid-residual.mp4",
            duration=0.02,
            fps=10,
            mode="residual",
            model_path=path,
            width=160,
            height=120,
        )


def test_velocity_smoke_training_saves_checkpoint(tmp_path):
    path = train_ppo_velocity(
        total_timesteps=16,
        seed=0,
        profile="smoke",
        target_velocity=0.3,
        output_dir=tmp_path,
        tensorboard_dir=tmp_path / "tensorboard",
    )
    assert Path(path).exists()


def test_record_policy_video_writes_decodable_mp4(tmp_path):
    path = tmp_path / "baseline.mp4"
    result = record_policy_video(path, duration=0.05, fps=10, mode="classic", width=160, height=120)
    assert result.path == path
    assert result.frame_count >= 1
    assert path.stat().st_size > 1_000
