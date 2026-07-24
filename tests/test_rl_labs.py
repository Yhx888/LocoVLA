"""测试 RL 实验室（rl_25 ~ rl_31）。

覆盖场景：
- PPO 训练入口与配置加载
- 训练日志 / 检查点产物契约
- 评估脚本输出结构
"""
import json
from pathlib import Path

import numpy as np
import pytest

from upkie_mujoco_course.envs.observation import build_observation
from upkie_mujoco_course.envs.standing_env import StandingEnv
from upkie_mujoco_course.randomization.dynamics import sample_episode_randomization
from upkie_mujoco_course.randomization.dynamics import validate_randomization_config
from upkie_mujoco_course.rl.labs import RL_LAB_CHAPTERS
from upkie_mujoco_course.rl.labs import estimate_gaussian_policy_gradient
from upkie_mujoco_course.rl.labs import run_rl_lab


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_rl_and_vla_entrypoints_accept_fixed_seed_argument():
    for filename in ("run_rl_lab.py", "run_vla_lab.py"):
        source = (PROJECT_ROOT / "scripts" / filename).read_text(encoding="utf-8")
        assert 'add_argument("--seed", type=int, default=0' in source


def test_policy_gradient_baseline_keeps_mean_near_analytic_gradient_and_reduces_variance():
    result = estimate_gaussian_policy_gradient(seed=7, batches=160, samples_per_batch=128)

    assert abs(result.raw_mean - result.analytic_gradient) < 0.08
    assert abs(result.baseline_mean - result.analytic_gradient) < 0.08
    assert result.baseline_variance < result.raw_variance


def test_randomization_sampler_is_seeded_and_covers_every_runtime_field():
    config = {
        "mass_scale": [0.9, 1.1],
        "friction_scale": [0.8, 1.2],
        "sensor_noise_std": [0.001, 0.003],
        "initial_state_std": [0.01, 0.02],
        "action_delay_steps": [0, 2],
        "push_force": [1.0, 2.0],
        "push_step": [10, 20],
        "push_duration_steps": [2, 4],
    }
    first = sample_episode_randomization(config, np.random.default_rng(5))
    second = sample_episode_randomization(config, np.random.default_rng(5))

    assert first == second
    assert set(first) == set(config)
    assert 0 <= first["action_delay_steps"] <= 2
    assert 10 <= first["push_step"] <= 20


def test_randomization_config_rejects_negative_mass_scale():
    with pytest.raises(ValueError, match="mass_scale"):
        validate_randomization_config({"mass_scale": [-0.1, 1.0]})


def test_runtime_randomization_is_applied_to_mujoco_and_control_chain():
    config = {
        "mass_scale": [1.04, 1.04],
        "inertia_scale": [0.96, 0.96],
        "com_offset_m": [0.006, 0.006],
        "friction_scale": [1.08, 1.08],
        "joint_damping": [0.05, 0.05],
        "actuator_strength_scale": [0.93, 0.93],
        "sensor_noise_std": [0.002, 0.002],
        "action_delay_steps": [1, 1],
    }
    env = StandingEnv(max_episode_steps=2, randomization=config)
    try:
        base_mass = env.runner.model.body_mass.copy()
        base_inertia = env.runner.model.body_inertia.copy()
        base_ipos = env.runner.model.body_ipos.copy()
        base_friction = env.runner.model.geom_friction.copy()
        base_damping = env.runner.model.dof_damping.copy()
        base_gain = env.runner.model.actuator_gainprm[:, 0].copy()

        observation, reset_info = env.reset(seed=29)
        applied = reset_info["runtime_randomization"]

        assert set(applied) == set(config)
        np.testing.assert_allclose(env.runner.model.body_mass, base_mass * applied["mass_scale"])
        np.testing.assert_allclose(env.runner.model.body_inertia, base_inertia * applied["inertia_scale"])
        base_id = env.runner.frame_map.body_ids[env.runner.spec.base_body]
        assert env.runner.model.body_ipos[base_id, 0] == pytest.approx(
            base_ipos[base_id, 0] + applied["com_offset_m"]
        )
        np.testing.assert_allclose(
            env.runner.model.geom_friction[:, 0],
            base_friction[:, 0] * applied["friction_scale"],
        )
        controlled_dofs = [
            env.runner.joint_map.dofadr[name]
            for name in env.runner.spec.controlled_joints
        ]
        np.testing.assert_allclose(
            env.runner.model.dof_damping[controlled_dofs],
            applied["joint_damping"],
        )
        np.testing.assert_allclose(env.runner.model.dof_damping[:6], base_damping[:6])
        np.testing.assert_allclose(
            env.runner.model.actuator_gainprm[:, 0],
            base_gain * applied["actuator_strength_scale"],
        )
        raw_observation = np.clip(
            build_observation(env.runner),
            env.observation_space.low,
            env.observation_space.high,
        )
        assert np.max(np.abs(observation - raw_observation)) > 0.0

        action = np.zeros(env.action_space.shape)
        action[-2:] = 1.0
        _, _, _, _, step_info = env.step(action)
        assert step_info["runtime_randomization"] == applied
        np.testing.assert_allclose(step_info["physical_action"][-2:], 0.0)
    finally:
        env.close()


def test_chapter_29_audits_environment_runtime_values(tmp_path):
    result_path = run_rl_lab("29", output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    log = json.loads((tmp_path / result["logs"][0]).read_text(encoding="utf-8"))

    assert log["audit_source"] == "mujoco_model_and_environment_state"
    assert log["sample_count"] == 200
    assert set(log["per_field"]) == {
        "mass_scale",
        "inertia_scale",
        "com_offset_m",
        "friction_scale",
        "joint_damping",
        "actuator_strength_scale",
        "sensor_noise_std",
        "action_delay_steps",
    }
    assert result["metrics"]["runtime_verified_field_count"] == 8.0
    assert result["metrics"]["seed_reproducibility_max_abs"] == 0.0
    assert result["metrics"]["runtime_sample_count"] == 200.0
    assert result["metrics"]["boundary_violation_count"] == 0.0

    first_run = log["runtime_samples"]
    replay_run = log["seed_replay_runtime_samples"]
    assert len(first_run["reset"]) == len(first_run["step"]) == 200
    assert first_run == replay_run
    assert first_run["reset"] == first_run["step"]
    for sample in first_run["step"]:
        assert set(sample) == set(log["per_field"])
        for name, value in sample.items():
            stat = log["per_field"][name]
            assert stat["lower_bound"] <= value <= stat["upper_bound"]


def test_chapter_29_does_not_trust_runtime_values_reported_in_info(tmp_path, monkeypatch):
    original_reset = StandingEnv.reset
    original_step = StandingEnv.step

    def poisoned_reset(self, *args, **kwargs):
        observation, info = original_reset(self, *args, **kwargs)
        info["runtime_randomization"] = {
            name: -999.0 for name in info["runtime_randomization"]
        }
        return observation, info

    def poisoned_step(self, *args, **kwargs):
        transition = list(original_step(self, *args, **kwargs))
        transition[4]["runtime_randomization"] = {
            name: -999.0 for name in transition[4]["runtime_randomization"]
        }
        return tuple(transition)

    monkeypatch.setattr(StandingEnv, "reset", poisoned_reset)
    monkeypatch.setattr(StandingEnv, "step", poisoned_step)

    result_path = run_rl_lab("29", output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    log = json.loads((tmp_path / result["logs"][0]).read_text(encoding="utf-8"))

    assert result["passed"] is True
    assert log["audit_source"] == "mujoco_model_and_environment_state"
    assert all(
        stat["lower_bound"] <= stat["min"] <= stat["max"] <= stat["upper_bound"]
        for stat in log["per_field"].values()
    )


@pytest.mark.parametrize(
    "chapter_id",
    [
        # 第 28 关的严格收敛阈值只在参考平台可逐位复现，CI 上以 rl_reference 标记排除。
        pytest.param(chapter, marks=pytest.mark.rl_reference) if chapter == "28" else chapter
        for chapter in RL_LAB_CHAPTERS
    ],
)
def test_rl_labs_write_real_result_log_plot_and_portfolio(tmp_path, chapter_id):
    result_path = run_rl_lab(chapter_id, output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["chapter_id"] == chapter_id
    assert result["seed"] == 0
    assert result["passed"] is True
    assert (tmp_path / result["plots"][0]).is_file()
    assert (tmp_path / result["logs"][0]).is_file()
    assert (tmp_path / "portfolio" / chapter_id / "evidence.json").is_file()


def test_sim2real_lab_reports_a_non_degenerate_bootstrap_interval(tmp_path):
    result_path = run_rl_lab("31", output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    metrics = result["metrics"]

    assert metrics["configuration_coverage_ratio"] == 1.0
    assert metrics["bootstrap_ci_width"] > 0.0
    assert metrics["evaluation_episode_count"] == 12.0


def test_residual_lab_trains_real_policy_and_rejects_performance_regression(tmp_path):
    result_path = run_rl_lab("30", output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    log = json.loads((tmp_path / result["logs"][0]).read_text(encoding="utf-8"))

    assert log["training"]["training_mode"] == "residual"
    assert log["training"]["total_timesteps"] > 0
    assert result["seed"] == log["training"]["seed"]
    assert Path(log["training"]["checkpoint_path"]).is_file()
    assert log["evaluation"]["paired_seeds"] == log["evaluation"]["baseline_seeds"]
    assert result["checks"]["residual_return_gap"] is (
        result["metrics"]["residual_return_gap"] >= 0.0
    )


@pytest.mark.rl_reference
def test_chapter_28_trains_and_reloads_real_mujoco_ppo(tmp_path):
    # 严格 PPO 收敛阈值只在参考平台（本地）逐位复现；CI 用 -m 'not rl_reference' 排除。
    result_path = run_rl_lab("28", output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    log = json.loads((tmp_path / result["logs"][0]).read_text(encoding="utf-8"))

    assert result["passed"] is True
    assert log["backend"] == "mujoco"
    assert log["training"]["training_mode"] == "wheel_torque"
    assert result["seed"] == 0
    assert log["training"]["seed"] == 28
    assert result["metrics"]["training_timesteps"] >= 50_000
    assert result["metrics"]["ppo_success_rate"] == 1.0
    assert result["metrics"]["ppo_fall_rate"] == 0.0
