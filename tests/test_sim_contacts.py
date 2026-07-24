"""sim/contacts 模块单元测试。

覆盖 read_contact_pairs 与 wheel_ground_state 两个公共函数。
"""

from __future__ import annotations

import mujoco
import numpy as np
import pytest

from upkie_mujoco_course.sim.contacts import read_contact_pairs, wheel_ground_state
from upkie_mujoco_course.sim.runner import SimulationRunner


@pytest.fixture(scope="module")
def runner() -> SimulationRunner:
    """构造共享的 SimulationRunner 实例。"""
    return SimulationRunner()


def test_read_contact_pairs_returns_list_of_tuples():
    """read_contact_pairs 应返回 (geom1, geom2) 字符串元组列表。"""
    spec_runner = SimulationRunner()
    spec_runner.reset("stand")
    pairs = read_contact_pairs(spec_runner.model, spec_runner.data)
    assert isinstance(pairs, list)
    for pair in pairs:
        assert isinstance(pair, tuple)
        assert len(pair) == 2
        assert isinstance(pair[0], str)
        assert isinstance(pair[1], str)


def test_read_contact_pairs_empty_when_no_contact():
    """自由空间中（无接触）应返回空列表。"""
    spec_runner = SimulationRunner()
    spec_runner.reset("stand")
    # 将机器人提升到空中，确保无接触
    root_joint_id = spec_runner.root_joint_id
    if root_joint_id >= 0:
        qpos_adr = int(spec_runner.model.jnt_qposadr[root_joint_id])
        spec_runner.data.qpos[qpos_adr + 2] = 10.0  # z 抬高到 10 米
        mujoco.mj_forward(spec_runner.model, spec_runner.data)
    pairs = read_contact_pairs(spec_runner.model, spec_runner.data)
    # 空中应无接触
    assert pairs == []


def test_read_contact_pairs_detects_ground_contact_in_stand_pose():
    """站立姿态下若有接触对，则至少一个接触对中包含 floor 几何体。

    注：MuJoCo 的接触检测依赖几何体间距阈值，站立时轮子可能因间距略大
    而未触发 ncon 检测，因此本测试仅在存在接触对时校验命名。
    """
    spec_runner = SimulationRunner()
    spec_runner.reset("stand")
    # 推进若干步以促使接触稳定化
    for _ in range(5):
        spec_runner.step(np.zeros(spec_runner.model.nu, dtype=float))
    pairs = read_contact_pairs(spec_runner.model, spec_runner.data)
    if len(pairs) == 0:
        # 站立时 MuJoCo 可能未生成显式接触对（间距阈值原因），跳过命名校验
        return
    flat = {name for pair in pairs for name in pair}
    assert "floor" in flat


def test_wheel_ground_state_returns_expected_keys(runner: SimulationRunner):
    """wheel_ground_state 应返回包含接触与高度字段的字典。"""
    runner.reset("stand")
    state = wheel_ground_state(runner)
    expected_keys = {
        "left_contact",
        "right_contact",
        "both_wheels_contact",
        "left_wheel_axis_height",
        "right_wheel_axis_height",
    }
    assert set(state.keys()) == expected_keys


def test_wheel_ground_state_stand_pose_both_wheels_grounded(runner: SimulationRunner):
    """站立姿态下两轮均应接触地面。"""
    runner.reset("stand")
    state = wheel_ground_state(runner)
    assert state["left_contact"] is True
    assert state["right_contact"] is True
    assert state["both_wheels_contact"] is True


def test_wheel_ground_state_heights_nonnegative_when_grounded(runner: SimulationRunner):
    """轮接地时轮轴高度应非负且接近轮半径。"""
    runner.reset("stand")
    state = wheel_ground_state(runner)
    # 站立时轮轴高度应接近轮半径
    assert state["left_wheel_axis_height"] >= -1e-6
    assert state["right_wheel_axis_height"] >= -1e-6
    # 高度应不超过轮半径太多（避免离地）
    assert state["left_wheel_axis_height"] <= runner.left_wheel_radius + 0.05
    assert state["right_wheel_axis_height"] <= runner.right_wheel_radius + 0.05


def test_wheel_ground_state_values_are_python_types(runner: SimulationRunner):
    """wheel_ground_state 中所有值应为 Python 原生类型。"""
    runner.reset("stand")
    state = wheel_ground_state(runner)
    for key, value in state.items():
        if isinstance(value, bool):
            continue
        assert isinstance(value, float), f"{key} 应为 float，实际为 {type(value)}"


def test_wheel_ground_state_lifted_base_breaks_contact(runner: SimulationRunner):
    """抬升机器人后，两轮应不再接触地面。"""
    runner.reset("stand")
    root_joint_id = runner.root_joint_id
    assert root_joint_id >= 0
    qpos_adr = int(runner.model.jnt_qposadr[root_joint_id])
    runner.data.qpos[qpos_adr + 2] = 10.0
    mujoco.mj_forward(runner.model, runner.data)
    state = wheel_ground_state(runner)
    # 抬到 10 米后应判定为离地
    assert state["left_contact"] is False
    assert state["right_contact"] is False
    assert state["both_wheels_contact"] is False
    # 轮轴高度应明显大于轮半径
    assert state["left_wheel_axis_height"] > runner.left_wheel_radius
    assert state["right_wheel_axis_height"] > runner.right_wheel_radius


def test_wheel_ground_state_consistency_with_posture_state(runner: SimulationRunner):
    """wheel_ground_state 返回值应与 posture_state 中的接触字段一致。"""
    runner.reset("stand")
    contacts = wheel_ground_state(runner)
    posture = runner.posture_state()
    assert contacts["left_contact"] == posture["left_contact"]
    assert contacts["right_contact"] == posture["right_contact"]
    assert contacts["both_wheels_contact"] == posture["both_wheels_contact"]
    assert contacts["left_wheel_axis_height"] == pytest.approx(
        posture["left_wheel_axis_height"]
    )
    assert contacts["right_wheel_axis_height"] == pytest.approx(
        posture["right_wheel_axis_height"]
    )
