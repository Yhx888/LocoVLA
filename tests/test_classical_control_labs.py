"""测试经典控制实验室（classical_12 ~ classical_19）。

覆盖场景：
- PD / LQR / MPC 实验室入口可执行
- 实验结果 JSON 产物字段契约
- 与教程描述的边界行为一致
"""
import json
from pathlib import Path

import numpy as np
import pytest

from upkie_mujoco_course.classical_control.labs import CLASSICAL_CHAPTERS
from upkie_mujoco_course.classical_control.labs import run_classical_control_lab
from upkie_mujoco_course.classical_control.math_tools import controllability_matrix
from upkie_mujoco_course.classical_control.math_tools import inverted_pendulum_acceleration
from upkie_mujoco_course.classical_control.math_tools import linearized_inverted_pendulum_acceleration
from upkie_mujoco_course.classical_control.math_tools import second_order_poles
from upkie_mujoco_course.classical_control.math_tools import solve_scalar_euler_lagrange
from upkie_mujoco_course.classical_control.math_tools import solve_scalar_hjb
from upkie_mujoco_course.classical_control.math_tools import solve_scalar_pontryagin
from upkie_mujoco_course.controllers.height_controller import HeightController
from upkie_mujoco_course.controllers.pid import PIDController
from upkie_mujoco_course.controllers.yaw_controller import YawRateController


def test_pid_anti_windup_stops_integral_growth_during_saturation():
    protected = PIDController(kp=2.0, ki=3.0, kd=0.0, limit=1.0, anti_windup=True)
    naive = PIDController(kp=2.0, ki=3.0, kd=0.0, limit=1.0, anti_windup=False)
    for _ in range(200):
        protected.step(error=2.0, dt=0.01)
        naive.step(error=2.0, dt=0.01)

    assert abs(protected.integral) < 0.02
    assert naive.integral == pytest.approx(4.0)


def test_pendulum_linearization_is_local_and_torque_has_physical_unit_effect():
    small = np.deg2rad(5.0)
    large = np.deg2rad(60.0)
    small_error = abs(
        inverted_pendulum_acceleration(small, 0.2)
        - linearized_inverted_pendulum_acceleration(small, 0.2)
    )
    large_error = abs(
        inverted_pendulum_acceleration(large, 0.2)
        - linearized_inverted_pendulum_acceleration(large, 0.2)
    )

    assert small_error < 0.01
    assert large_error > 1.0
    assert inverted_pendulum_acceleration(0.0, 0.5) < 0.0


def test_second_order_poles_distinguish_stable_and_unstable_damping():
    stable = second_order_poles(natural_frequency_rad_s=4.0, damping_ratio=0.7)
    unstable = second_order_poles(natural_frequency_rad_s=4.0, damping_ratio=-0.1)

    assert np.all(np.real(stable) < 0.0)
    assert np.any(np.real(unstable) > 0.0)


def test_four_state_wheel_pendulum_model_is_controllable():
    gravity = 9.81
    mass = 10.0
    length = 0.5
    a = np.array(
        [
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, gravity / length, 0.0],
        ]
    )
    b = np.array([[0.0], [1.0 / mass], [0.0], [-1.0 / (mass * length)]])

    assert np.linalg.matrix_rank(controllability_matrix(a, b)) == 4


def test_scalar_optimal_control_methods_agree_and_satisfy_their_equations():
    euler = solve_scalar_euler_lagrange(initial_state=1.0, horizon=2.0, terminal_weight=4.0)
    hjb = solve_scalar_hjb(initial_state=1.0, horizon=2.0, terminal_weight=4.0)
    pontryagin = solve_scalar_pontryagin(initial_state=1.0, horizon=2.0, terminal_weight=4.0)

    np.testing.assert_allclose(euler.state, hjb.state, atol=1e-10)
    np.testing.assert_allclose(euler.state, pontryagin.state, atol=1e-10)
    np.testing.assert_allclose(euler.control, hjb.control, atol=1e-10)
    np.testing.assert_allclose(euler.control, pontryagin.control, atol=1e-10)
    assert euler.equation_residual <= 1e-10
    assert hjb.equation_residual <= 1e-10
    assert pontryagin.equation_residual <= 1e-10
    assert pontryagin.stationarity_residual <= 1e-10
    assert pontryagin.costate_residual <= 1e-10
    assert pontryagin.transversality_residual <= 1e-10


def test_yaw_and_height_controllers_apply_limits_and_mirror_leg_targets():
    yaw = YawRateController(gain=0.2, torque_limit=0.03)
    assert yaw.compute(target_yaw_rate=1.0, current_yaw_rate=0.0) == pytest.approx(0.03)
    assert yaw.compute(target_yaw_rate=-1.0, current_yaw_rate=0.0) == pytest.approx(-0.03)

    height = HeightController(gain=2.0, max_joint_offset_rad=0.1)
    stand = {"left_hip": -0.2, "left_knee": 0.6, "right_hip": 0.2, "right_knee": -0.6}
    targets = height.compute_targets(stand, target_height=0.03, current_height=0.0)
    assert targets["left_hip"] == pytest.approx(-targets["right_hip"])
    assert targets["left_knee"] == pytest.approx(-targets["right_knee"])
    assert abs(targets["left_knee"] - stand["left_knee"]) <= 0.1


@pytest.mark.parametrize("chapter_id", CLASSICAL_CHAPTERS)
def test_classical_control_lab_writes_real_result_log_plot_and_portfolio(tmp_path, chapter_id):
    result_path = run_classical_control_lab(chapter_id, output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["chapter_id"] == chapter_id
    assert result["seed"] == 0
    assert result["passed"] is True
    assert (tmp_path / result["plots"][0]).is_file()
    assert (tmp_path / result["logs"][0]).is_file()
    assert (tmp_path / "portfolio" / chapter_id / "evidence.json").is_file()


def test_classical_control_entrypoint_accepts_fixed_seed_argument():
    source = (Path(__file__).resolve().parents[1] / "scripts" / "run_classical_control_lab.py").read_text(
        encoding="utf-8"
    )
    assert 'add_argument("--seed", type=int, default=0' in source


def test_chapter_17_records_euler_hjb_and_pontryagin_hard_checks(tmp_path):
    result_path = run_classical_control_lab("17", output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    log = json.loads((tmp_path / result["logs"][0]).read_text(encoding="utf-8"))

    assert set(log["optimal_control"]["methods"]) == {
        "euler_lagrange",
        "hjb",
        "pontryagin",
    }
    for metric in (
        "euler_lagrange_equation_residual",
        "hjb_equation_residual",
        "pontryagin_costate_residual",
        "pontryagin_stationarity_residual",
        "pontryagin_transversality_residual",
        "optimal_control_state_agreement",
        "optimal_control_cost_agreement",
    ):
        assert metric in result["checks"]
        assert result["checks"][metric] is True
