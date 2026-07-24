"""测试地形随机化与动作滤波器整合。

覆盖场景：
- terrain.py 的 flat_terrain_config / validate_terrain_config / sample_terrain_config / apply_terrain
- dynamics.py 接受 terrain_slope_deg/terrain_roughness 字段不报错
- BaseUpkieEnv 默认配置（无 terrain 字段）保持平地行为，向后兼容
- BaseUpkieEnv 配置 terrain_slope_deg 后 reset/step 正常运行
- action_adapter.json 的 action_filter 字段默认 alpha=0/max_delta=0 时直通
- 配置非零 alpha/max_delta 后物理动作被低通滤波和增量限制
"""
import numpy as np
import pytest

from upkie_mujoco_course.randomization.dynamics import (
    sample_episode_randomization,
    validate_randomization_config,
)
from upkie_mujoco_course.randomization.terrain import (
    apply_terrain,
    flat_terrain_config,
    sample_terrain_config,
    validate_terrain_config,
)


def test_flat_terrain_config_returns_zero():
    """平地配置应返回 slope=0/roughness=0。"""
    cfg = flat_terrain_config()
    assert cfg == {"slope_deg": 0.0, "roughness": 0.0}


def test_validate_terrain_config_accepts_empty():
    """空配置（无 terrain 字段）应通过校验。"""
    validate_terrain_config({})


def test_validate_terrain_config_accepts_scalar():
    """标量 terrain 字段应通过校验。"""
    validate_terrain_config({"terrain_slope_deg": 5.0, "terrain_roughness": 0.2})


def test_validate_terrain_config_accepts_interval():
    """区间 terrain 字段应通过校验。"""
    validate_terrain_config({"terrain_slope_deg": [-5.0, 5.0], "terrain_roughness": [0.0, 0.5]})


def test_validate_terrain_config_rejects_out_of_range():
    """超出 [-45, 45] 度的斜坡应被拒绝。"""
    with pytest.raises(ValueError, match="terrain_slope_deg"):
        validate_terrain_config({"terrain_slope_deg": 60.0})
    with pytest.raises(ValueError, match="terrain_slope_deg"):
        validate_terrain_config({"terrain_slope_deg": -50.0})


def test_validate_terrain_config_rejects_negative_roughness():
    """负粗糙度应被拒绝。"""
    with pytest.raises(ValueError, match="terrain_roughness"):
        validate_terrain_config({"terrain_roughness": -0.1})


def test_validate_randomization_config_accepts_terrain_fields():
    """dynamics.validate_randomization_config 应接受 terrain 字段为已知字段。"""
    validate_randomization_config(
        {"mass_scale": 1.0, "terrain_slope_deg": 5.0, "terrain_roughness": 0.1}
    )


def test_sample_terrain_config_default_zero():
    """无 terrain 字段时返回平地配置。"""
    rng = np.random.default_rng(42)
    terrain = sample_terrain_config({}, rng)
    assert terrain == {"slope_deg": 0.0, "roughness": 0.0}


def test_sample_terrain_config_scalar_passthrough():
    """标量 terrain 字段应原样返回。"""
    rng = np.random.default_rng(42)
    terrain = sample_terrain_config({"terrain_slope_deg": 10.0, "terrain_roughness": 0.3}, rng)
    assert terrain["slope_deg"] == pytest.approx(10.0)
    assert terrain["roughness"] == pytest.approx(0.3)


def test_sample_terrain_config_interval_samples_in_range():
    """区间 terrain 字段应在区间内采样。"""
    rng = np.random.default_rng(42)
    for _ in range(20):
        terrain = sample_terrain_config({"terrain_slope_deg": [-5.0, 5.0]}, rng)
        assert -5.0 <= terrain["slope_deg"] <= 5.0


def test_sample_episode_randomization_skips_terrain_fields():
    """sample_episode_randomization 应跳过 terrain 字段（由 terrain 模块独立采样）。"""
    rng = np.random.default_rng(42)
    config = {"mass_scale": 1.0, "terrain_slope_deg": [-5.0, 5.0]}
    sampled = sample_episode_randomization(config, rng)
    # mass_scale 应被采样
    assert "mass_scale" in sampled
    # terrain_slope_deg 不应被 sample_episode_randomization 采样
    assert "terrain_slope_deg" not in sampled


def test_apply_terrain_zero_slope_keeps_gravity():
    """slope=0 时重力应保持不变（平地）。"""
    from upkie_mujoco_course.sim.runner import SimulationRunner

    runner = SimulationRunner()
    original_gravity = runner.model.opt.gravity.copy()
    apply_terrain(runner.model, {"slope_deg": 0.0, "roughness": 0.0})
    np.testing.assert_allclose(runner.model.opt.gravity, original_gravity, atol=1e-12)
    runner.close()


def test_apply_terrain_nonzero_slope_tilts_gravity():
    """非零 slope 应沿 +x 方向倾斜重力向量。"""
    from upkie_mujoco_course.sim.runner import SimulationRunner

    runner = SimulationRunner()
    original_g_z = float(runner.model.opt.gravity[2])
    slope_deg = 10.0
    apply_terrain(runner.model, {"slope_deg": slope_deg, "roughness": 0.0})
    expected_g_x = -original_g_z * np.sin(np.radians(slope_deg))
    expected_g_z = original_g_z * np.cos(np.radians(slope_deg))
    np.testing.assert_allclose(runner.model.opt.gravity[0], expected_g_x, atol=1e-9)
    np.testing.assert_allclose(runner.model.opt.gravity[2], expected_g_z, atol=1e-9)
    runner.close()


def test_apply_terrain_negative_slope_tilts_negative_x():
    """负 slope（上坡）应沿 -x 方向倾斜重力。"""
    from upkie_mujoco_course.sim.runner import SimulationRunner

    runner = SimulationRunner()
    apply_terrain(runner.model, {"slope_deg": -10.0, "roughness": 0.0})
    # 负 slope 时 g_x 应为负
    assert runner.model.opt.gravity[0] < 0
    runner.close()


def test_base_env_default_config_no_terrain_runs_normally():
    """BaseUpkieEnv 默认 randomization 配置（无 terrain 字段）应正常运行。"""
    from upkie_mujoco_course.envs.standing_env import StandingEnv

    env = StandingEnv()
    obs, info = env.reset(seed=42)
    assert "terrain" in info
    assert info["terrain"]["slope_deg"] == pytest.approx(0.0)
    action = np.zeros(env.action_space.shape, dtype=np.float64)
    obs, reward, terminated, truncated, step_info = env.step(action)
    assert "terrain" in step_info
    assert isinstance(reward, float)
    env.close()


def test_base_env_with_terrain_slope_runs_normally():
    """BaseUpkieEnv 配置 terrain_slope_deg 后应正常运行并应用斜坡。"""
    from upkie_mujoco_course.envs.standing_env import StandingEnv

    env = StandingEnv(randomization={"terrain_slope_deg": 5.0})
    obs, info = env.reset(seed=42)
    assert info["terrain"]["slope_deg"] == pytest.approx(5.0)
    # 验证重力被倾斜（g_x 应非零）
    assert abs(env.runner.model.opt.gravity[0]) > 1e-6
    action = np.zeros(env.action_space.shape, dtype=np.float64)
    obs, reward, terminated, truncated, step_info = env.step(action)
    assert step_info["terrain"]["slope_deg"] == pytest.approx(5.0)
    env.close()


def test_base_env_reset_restores_gravity():
    """连续 reset 应恢复默认重力再应用新地形，避免重力累积。"""
    from upkie_mujoco_course.envs.standing_env import StandingEnv

    env = StandingEnv(randomization={"terrain_slope_deg": 10.0})
    env.reset(seed=1)
    g_x_first = float(env.runner.model.opt.gravity[0])
    env.reset(seed=2)
    g_x_second = float(env.runner.model.opt.gravity[0])
    # 两次 reset 后 g_x 应一致（都应用 10 度斜坡）
    assert g_x_first == pytest.approx(g_x_second, abs=1e-9)
    env.close()


def test_action_filter_default_passthrough():
    """默认 alpha=0/max_delta=0 时动作滤波应直通，不改变物理动作。"""
    from upkie_mujoco_course.envs.standing_env import StandingEnv

    env = StandingEnv()
    env.reset(seed=42)
    # 默认配置 alpha=0/max_delta=0，物理动作应等于 adapt_action 输出
    action = np.array([0.1, -0.1, 0.2, -0.2, 0.0, 0.0], dtype=np.float64)
    physical = env.to_physical_action(action)
    # previous_physical_action 应更新为 physical
    np.testing.assert_allclose(env._previous_physical_action, physical)
    env.close()


def test_action_filter_low_pass_smoothing():
    """alpha>0 时低通滤波应平滑动作（第一步输出是 raw 的一半，因为 previous=0）。"""
    from upkie_mujoco_course.envs.standing_env import StandingEnv

    env = StandingEnv()
    # 注入 alpha=0.5 的低通滤波
    env._action_filter_alpha = 0.5
    from upkie_mujoco_course.controllers.action_filter import LowPassActionFilter

    env._action_filter = LowPassActionFilter(alpha=0.5, size=env.runner.model.nu)
    env.reset(seed=42)
    # reset 后 _action_filter.previous = 0（由 LowPassActionFilter.reset 实现）
    # 先计算无滤波的 raw physical 作为基准
    action = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float64)
    from upkie_mujoco_course.envs.action_adapter import adapt_action

    raw_physical = adapt_action(
        action,
        env.neutral_action,
        env.action_scale,
        env.runner.ctrl_low,
        env.runner.ctrl_high,
    )
    physical = env.to_physical_action(action)
    # alpha=0.5, previous=0: filtered = 0.5 * raw + 0.5 * 0 = 0.5 * raw
    expected_filtered = 0.5 * raw_physical
    np.testing.assert_allclose(physical, expected_filtered, atol=1e-9)
    env.close()


def test_action_filter_max_delta_limit():
    """max_delta>0 时增量应被限制在 [-max_delta, max_delta]。"""
    from upkie_mujoco_course.envs.standing_env import StandingEnv

    env = StandingEnv()
    env._action_filter_max_delta = 0.05
    env.reset(seed=42)
    # 第一步 previous=neutral，当前动作让 physical 与 neutral 差距超过 0.05
    action = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float64)
    physical = env.to_physical_action(action)
    delta = physical - env.neutral_action
    # 增量应被限制在 ±0.05
    assert np.all(np.abs(delta) <= 0.05 + 1e-9)
    env.close()
