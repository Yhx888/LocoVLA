"""SimulationRunner 单元测试。

覆盖构造、reset、step、observation、posture_state、动作维度校验等公共接口。
"""

from __future__ import annotations

import numpy as np
import pytest

from upkie_mujoco_course.sim.runner import SimulationRunner


@pytest.fixture(scope="module")
def runner() -> SimulationRunner:
    """构造一个共享的 SimulationRunner 实例。"""
    return SimulationRunner()


def test_init_loads_model_and_maps(runner: SimulationRunner):
    """构造函数应加载 MjModel/MjData 并建立关节/执行器/传感器映射。"""
    assert runner.model is not None
    assert runner.data is not None
    # 关节映射应包含配置中所有受控关节
    for name in runner.spec.controlled_joints:
        assert name in runner.joint_map.ids
    # 执行器 id 顺序应与 spec 中 actuator_names 一致
    assert list(runner.actuator_map.ids) == runner.spec.actuator_names
    # 控制范围形状与执行器数量一致
    assert runner.ctrl_low.shape == (runner.model.nu,)
    assert runner.ctrl_high.shape == (runner.model.nu,)
    # 默认 qpos/qvel 已记录
    assert runner.default_qpos.shape == (runner.model.nq,)
    assert runner.default_qvel.shape == (runner.model.nv,)
    # 轮半径估计为正数
    assert runner.left_wheel_radius > 0
    assert runner.right_wheel_radius > 0


def test_time_property_returns_float(runner: SimulationRunner):
    """time 属性应返回浮点数。"""
    t = runner.time
    assert isinstance(t, float)
    assert t >= 0.0


def test_reset_returns_observation(runner: SimulationRunner):
    """reset 应返回 observation 向量。"""
    obs = runner.reset("stand")
    assert isinstance(obs, np.ndarray)
    assert obs.shape == (runner.model.nq + runner.model.nv,)
    # reset 后时间应为 0
    assert runner.time == pytest.approx(0.0, abs=1e-9)


def test_reset_unknown_pose_raises(runner: SimulationRunner):
    """reset 传入未知姿态名应抛出 ValueError。"""
    with pytest.raises(ValueError, match="未知初始姿态"):
        runner.reset("nonexistent_pose")


def test_reset_updates_last_reset_pose(runner: SimulationRunner):
    """reset 应更新 last_reset_pose 属性。"""
    runner.reset("stand")
    assert runner.last_reset_pose == "stand"


def test_step_returns_observation_with_correct_shape(runner: SimulationRunner):
    """step 应返回形状正确的 observation。"""
    runner.reset("stand")
    action = np.zeros(runner.model.nu, dtype=float)
    obs = runner.step(action)
    assert obs.shape == (runner.model.nq + runner.model.nv,)
    # step 后时间应前进
    expected_dt = runner.model.opt.timestep * runner.spec.frame_skip
    assert runner.time == pytest.approx(expected_dt, abs=1e-6)


def test_step_action_dimension_mismatch_raises(runner: SimulationRunner):
    """step 传入错误维度的动作应抛出 ValueError。"""
    runner.reset("stand")
    wrong_action = np.zeros(runner.model.nu + 1, dtype=float)
    with pytest.raises(ValueError, match="动作维度错误"):
        runner.step(wrong_action)


def test_step_clips_action_to_ctrl_range(runner: SimulationRunner):
    """step 应将动作裁剪到 actuator_ctrlrange 范围内。"""
    runner.reset("stand")
    # 传入一个明显超出范围的极大动作
    huge_action = np.full(runner.model.nu, 1e6, dtype=float)
    runner.step(huge_action)
    # 验证 ctrl 已被裁剪
    clipped = runner.data.ctrl
    assert np.all(clipped >= runner.ctrl_low - 1e-9)
    assert np.all(clipped <= runner.ctrl_high + 1e-9)


def test_observation_concatenates_qpos_qvel(runner: SimulationRunner):
    """observation 应等于 qpos 与 qvel 的拼接。"""
    runner.reset("stand")
    obs = runner.observation()
    expected = np.concatenate([runner.data.qpos, runner.data.qvel])
    np.testing.assert_allclose(obs, expected)


def test_posture_state_returns_expected_keys(runner: SimulationRunner):
    """posture_state 应返回包含姿态、速度、接触状态的字典。"""
    runner.reset("stand")
    state = runner.posture_state()
    expected_keys = {
        "time",
        "x_position",
        "base_height",
        "pitch",
        "pitch_error",
        "pitch_rate",
        "forward_velocity",
        "yaw_rate",
        "left_contact",
        "right_contact",
        "both_wheels_contact",
        "left_wheel_axis_height",
        "right_wheel_axis_height",
    }
    assert set(state.keys()) == expected_keys
    # pitch_error 应等于 pitch - equilibrium_pitch_rad
    assert state["pitch_error"] == pytest.approx(
        state["pitch"] - runner.spec.equilibrium_pitch_rad
    )
    # both_wheels_contact 应为左右接触的逻辑与
    assert state["both_wheels_contact"] == (
        state["left_contact"] and state["right_contact"]
    )


def test_posture_state_values_are_python_types(runner: SimulationRunner):
    """posture_state 中所有值应为 Python 原生 float/bool，而非 numpy 标量。"""
    runner.reset("stand")
    state = runner.posture_state()
    for key, value in state.items():
        if isinstance(value, bool):
            continue
        assert isinstance(value, float), f"{key} 应为 float，实际为 {type(value)}"


def test_close_without_viewer_is_noop(runner: SimulationRunner):
    """未打开 viewer 时调用 close 应为无操作，不抛异常。"""
    # 确保没有打开 viewer
    assert runner._viewer is None
    runner.close()
    assert runner._viewer is None
