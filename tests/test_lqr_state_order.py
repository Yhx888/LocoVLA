"""LQR 状态顺序与增益矩阵维度一致性测试。

验证 lqr.json 中声明的 state_order 与 LQRBalanceController.compute_action
实际使用的状态顺序一致，且增益矩阵 K 的维度与状态向量匹配。
"""

from __future__ import annotations


import numpy as np
import pytest

from upkie_mujoco_course.controllers.lqr import LQRBalanceController, LQRController
from upkie_mujoco_course.sim.runner import SimulationRunner
from upkie_mujoco_course.utils.config import load_json_config


# state_order 字段名 -> posture_state 实际键名的映射
# 注：lqr.json 中 "x_rate" 在 posture_state 中对应 "forward_velocity"，
# 语义一致（x 方向前进速度），仅命名风格不同。
STATE_ORDER_TO_POSTURE_KEY = {
    "x": "x_position",
    "x_rate": "forward_velocity",
    "pitch": "pitch_error",
    "pitch_rate": "pitch_rate",
}


@pytest.fixture(scope="module")
def lqr_config() -> dict:
    """加载 lqr.json 配置。"""
    return load_json_config("configs/control/lqr.json")["lqr"]


@pytest.fixture(scope="module")
def runner() -> SimulationRunner:
    """共享 SimulationRunner 实例。"""
    return SimulationRunner()


@pytest.fixture(scope="module")
def controller() -> LQRBalanceController:
    """共享 LQRBalanceController 实例。"""
    return LQRBalanceController()


def test_state_order_has_four_entries(lqr_config: dict):
    """state_order 应包含 4 个状态变量（与倒立摆模型一致）。"""
    state_order = lqr_config["state_order"]
    assert isinstance(state_order, list)
    assert len(state_order) == 4


def test_gain_matrix_dimension_matches_state_order(lqr_config: dict):
    """增益矩阵 K 的形状应为 [1, 4]，即 1 个输出 × 4 个状态。"""
    gain = np.asarray(lqr_config["gain"], dtype=float)
    state_order = lqr_config["state_order"]
    # 输出维度（行数）：LQR 输出单一力矩，应为 1
    assert gain.shape[0] == 1, f"增益矩阵行数应为 1，实际为 {gain.shape[0]}"
    # 状态维度（列数）：应与 state_order 长度一致
    assert gain.shape[1] == len(state_order), (
        f"增益矩阵列数 {gain.shape[1]} 与 state_order 长度 {len(state_order)} 不一致"
    )


def test_state_order_matches_compute_action_usage(
    lqr_config: dict, runner: SimulationRunner, controller: LQRBalanceController
):
    """LQRBalanceController.compute_action 使用的状态顺序应与 state_order 一致。

    通过 monkeypatch 替换 controller.controller.compute，捕获实际传入的状态向量，
    再与 posture_state 中按 state_order 顺序取出的向量比较。
    """
    runner.reset("stand")
    posture = runner.posture_state()

    # 按 state_order 顺序构造期望向量（使用映射后的 posture_state 键名）
    expected_vector = np.array(
        [posture[STATE_ORDER_TO_POSTURE_KEY[name]] for name in lqr_config["state_order"]],
        dtype=float,
    )

    # 捕获实际传入 LQRController.compute 的状态向量
    captured: dict[str, np.ndarray] = {}

    original_compute = controller.controller.compute

    def capture_compute(state, reference=None):
        captured["state"] = np.asarray(state, dtype=float).reshape(-1)
        return original_compute(state, reference)

    controller.controller.compute = capture_compute
    try:
        controller.compute_action(runner)
    finally:
        controller.controller.compute = original_compute

    assert "state" in captured, "compute_action 应调用 controller.controller.compute"
    actual_vector = captured["state"]
    assert actual_vector.shape == (4,), f"状态向量维度应为 (4,)，实际为 {actual_vector.shape}"
    np.testing.assert_allclose(actual_vector, expected_vector, atol=1e-12)


def test_matrix_multiplication_executes(lqr_config: dict):
    """矩阵乘法 u = -K @ x 应能正确执行，输出为标量（1 维输出）。"""
    gain = np.asarray(lqr_config["gain"], dtype=float)
    lqr = LQRController(gain)
    # 构造一个任意非零状态向量
    state = np.array([0.1, 0.05, -0.02, 0.01], dtype=float)
    output = lqr.compute(state)
    # 输出维度应与 gain 行数一致
    assert output.shape == (1,)
    # 验证手算结果：u = -K @ x
    expected = -gain @ state
    np.testing.assert_allclose(output, expected, atol=1e-12)


def test_zero_state_produces_zero_output(lqr_config: dict):
    """零状态应产生零输出（调节器特性：u = -K @ 0 = 0）。"""
    gain = np.asarray(lqr_config["gain"], dtype=float)
    lqr = LQRController(gain)
    state = np.zeros(4, dtype=float)
    output = lqr.compute(state)
    np.testing.assert_allclose(output, np.zeros(1), atol=1e-12)


def test_compute_action_returns_clipped_action(
    runner: SimulationRunner, controller: LQRBalanceController
):
    """compute_action 应返回裁剪到 ctrl_range 内的动作向量。"""
    runner.reset("stand")
    action = controller.compute_action(runner)
    assert action.shape == (runner.model.nu,)
    assert np.all(action >= runner.ctrl_low - 1e-9)
    assert np.all(action <= runner.ctrl_high + 1e-9)


def test_state_order_fields_are_known(lqr_config: dict):
    """state_order 中每个字段都应在 STATE_ORDER_TO_POSTURE_KEY 映射中存在。

    若 lqr.json 新增了未知状态字段，本测试会失败，提醒开发者同步映射。
    """
    for field in lqr_config["state_order"]:
        assert field in STATE_ORDER_TO_POSTURE_KEY, (
            f"state_order 中的字段 '{field}' 未在测试映射中定义，"
            f"请在 STATE_ORDER_TO_POSTURE_KEY 中补充对应 posture_state 键名"
        )


def test_posture_state_has_required_keys_for_lqr(runner: SimulationRunner):
    """posture_state 应包含 LQR 所需的所有键。"""
    runner.reset("stand")
    posture = runner.posture_state()
    for key in STATE_ORDER_TO_POSTURE_KEY.values():
        assert key in posture, f"posture_state 缺少 LQR 所需的键 '{key}'"
