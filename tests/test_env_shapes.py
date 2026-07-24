"""测试环境观测 / 动作空间形状。

覆盖场景：
- StandingEnv 观测与动作形状符合配置
- VelocityEnv 观测与动作形状符合配置
- 命令维度与控制频率设置正确
"""
import numpy as np

from upkie_mujoco_course.envs.standing_env import StandingEnv
from upkie_mujoco_course.envs.velocity_env import VelocityEnv


def test_standing_env_reset_and_step_shapes():
    env = StandingEnv(max_episode_steps=3)
    obs, info = env.reset(seed=0)
    assert env.observation_space.shape == (15,)
    assert np.isfinite(env.observation_space.low).all()
    assert np.isfinite(env.observation_space.high).all()
    assert np.allclose(env.action_space.low, -1.0)
    assert np.allclose(env.action_space.high, 1.0)
    assert obs.shape == env.observation_space.shape
    assert isinstance(info, dict)
    action = np.zeros(env.action_space.shape, dtype=env.action_space.dtype)
    obs, reward, terminated, truncated, info = env.step(action)
    assert obs.shape == env.observation_space.shape
    assert np.isfinite(reward)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)
    assert set(info["reward_terms"]) == {"alive", "upright", "height", "position", "effort", "smoothness"}
    env.close()


def test_free_base_moves_under_gravity_without_supporting_control():
    env = StandingEnv(max_episode_steps=200)
    env.reset(seed=0)
    start_position = env.runner._base_position().copy()
    action = np.zeros(env.action_space.shape, dtype=env.action_space.dtype)
    for _ in range(50):
        env.step(action)
    end_position = env.runner._base_position().copy()
    env.close()
    assert np.linalg.norm(end_position - start_position) > 0.01


def test_zero_normalized_action_maps_to_standing_pose_and_zero_wheel_torque():
    env = StandingEnv(max_episode_steps=2)
    env.reset(seed=0)
    env.step(np.zeros(6, dtype=np.float32))
    expected = env.runner.spec.default_pose["stand"]
    assert np.isclose(env.runner.data.ctrl[env.runner.actuator_ids["left_hip_servo"]], expected["left_hip"])
    assert np.isclose(env.runner.data.ctrl[env.runner.actuator_ids["left_knee_servo"]], expected["left_knee"])
    assert np.isclose(env.runner.data.ctrl[env.runner.actuator_ids["left_wheel_motor"]], 0.0)
    assert np.isclose(env.runner.data.ctrl[env.runner.actuator_ids["right_wheel_motor"]], 0.0)
    env.close()


def test_physical_and_normalized_actions_round_trip():
    env = StandingEnv(max_episode_steps=2)
    normalized = np.array([0.2, -0.2, 0.1, -0.1, 0.5, -0.5])
    physical = env.to_physical_action(normalized)
    restored = env.to_normalized_action(physical)
    env.close()
    assert np.allclose(restored, normalized)


def test_randomized_reset_is_reproducible_from_seed():
    randomization = {"initial_state_std": 0.01, "sensor_noise_std": 0.01}
    env = StandingEnv(max_episode_steps=2, randomization=randomization)
    obs_a, _ = env.reset(seed=42)
    obs_b, _ = env.reset(seed=42)
    obs_c, _ = env.reset(seed=43)
    env.close()
    assert np.allclose(obs_a, obs_b)
    assert not np.allclose(obs_a, obs_c)


def test_velocity_observation_includes_target_command():
    env = VelocityEnv(target_velocity=0.4, max_episode_steps=2)
    obs, _ = env.reset(seed=0)
    env.close()
    assert env.observation_space.shape == (16,)
    assert np.isclose(obs[-1], 0.4)


def test_action_delay_applies_previous_physical_action():
    env = StandingEnv(max_episode_steps=3, randomization={"action_delay_steps": 1})
    env.reset(seed=0)
    action = np.zeros(6)
    action[-2:] = 1.0
    _, _, _, _, first_info = env.step(action)
    _, _, _, _, second_info = env.step(np.zeros(6))
    env.close()
    assert np.allclose(first_info["physical_action"][-2:], 0.0)
    assert np.allclose(second_info["physical_action"][-2:], 1.0)


def test_dynamics_randomization_and_push_are_reported():
    randomization = {
        "mass_scale": [0.9, 1.1],
        "friction_scale": [0.8, 1.2],
        "push_force": 20.0,
        "push_step": 0,
        "push_duration_steps": 1,
    }
    env = StandingEnv(max_episode_steps=2, randomization=randomization)
    _, reset_info = env.reset(seed=7)
    _, _, _, _, step_info = env.step(np.zeros(6))
    env.close()
    assert 0.9 <= reset_info["randomization"]["mass_scale"] <= 1.1
    assert 0.8 <= reset_info["randomization"]["friction_scale"] <= 1.2
    assert step_info["push_applied"] is True


def test_height_reward_uses_neutral_standing_height_as_target():
    env = StandingEnv(max_episode_steps=2)
    env.reset(seed=0)
    standing_state = env.runner.posture_state()
    on_floor_state = {**standing_state, "base_height": env.runner.spec.floor_z}

    standing_reward_value = env.compute_reward_terms(standing_state, np.zeros(6))["height"]
    floor_reward_value = env.compute_reward_terms(on_floor_state, np.zeros(6))["height"]
    target_height = env.target_standing_height
    env.close()

    assert target_height == np.float64(standing_state["base_height"])
    assert standing_reward_value > floor_reward_value
