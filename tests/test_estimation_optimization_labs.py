"""测试状态估计与优化实验室（estimation_20 ~ estimation_24）。

覆盖场景：
- 卡尔曼 / 互补 / EKF 滤波器实验室入口可执行
- 实验结果 JSON 产物字段契约
- 优化器收敛性与参数敏感性
"""
import json
import inspect
from pathlib import Path

import numpy as np
import pytest

from upkie_mujoco_course.estimation.labs import ESTIMATION_CHAPTERS
from upkie_mujoco_course.estimation import labs as estimation_labs
from upkie_mujoco_course.estimation.labs import run_estimation_optimization_lab
from upkie_mujoco_course.estimation.labs import run_trajectory_optimization_lab
from upkie_mujoco_course.estimation.labs import compute_kkt_diagnostics
from upkie_mujoco_course.estimation.labs import solve_quadratic_program
from upkie_mujoco_course.estimation.ukf import UnscentedKalmanFilter
from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.controllers.trajectory_optimization import solve_direct_collocation
from upkie_mujoco_course.controllers.trajectory_optimization import solve_single_shooting


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_quadratic_program_respects_box_and_coupled_constraints():
    result = solve_quadratic_program(
        hessian=np.diag([2.0, 2.0]),
        linear_term=np.array([-2.0, -2.0]),
        inequality=np.array([[1.0, 1.0]]),
        upper_bound=np.array([0.9]),
        lower=np.array([-0.6, -0.6]),
        upper=np.array([0.6, 0.6]),
    )

    assert result.success
    assert np.all(result.solution <= 0.6 + 1e-9)
    assert np.all(result.solution >= -0.6 - 1e-9)
    assert float(np.sum(result.solution)) <= 0.9 + 1e-9


def test_kkt_diagnostics_verify_stationarity_feasibility_and_duality():
    hessian = np.diag([2.0, 2.0])
    linear_term = np.array([-2.0, -2.0])
    inequality = np.array([[1.0, 1.0]])
    upper_bound = np.array([0.9])
    lower = np.array([-0.6, -0.6])
    upper = np.array([0.6, 0.6])
    result = solve_quadratic_program(
        hessian=hessian,
        linear_term=linear_term,
        inequality=inequality,
        upper_bound=upper_bound,
        lower=lower,
        upper=upper,
    )
    diagnostics = compute_kkt_diagnostics(
        solution=result.solution,
        hessian=hessian,
        linear_term=linear_term,
        inequality=inequality,
        upper_bound=upper_bound,
        lower=lower,
        upper=upper,
    )

    assert diagnostics.stationarity_residual <= 1e-8
    assert diagnostics.primal_feasibility_residual <= 1e-8
    assert diagnostics.dual_feasibility_residual <= 1e-10
    assert diagnostics.complementarity_residual <= 1e-8
    assert diagnostics.duality_gap <= 1e-8
    assert diagnostics.inequality_multipliers[0] == pytest.approx(1.1, abs=1e-7)


def test_direct_collocation_and_shooting_solve_the_same_trajectory_problem():
    direct = solve_direct_collocation(intervals=20, horizon=1.0, target_position=1.0)
    shooting = solve_single_shooting(intervals=20, horizon=1.0, target_position=1.0)

    assert direct.success
    assert shooting.success
    assert direct.terminal_error <= 1e-7
    assert shooting.terminal_error <= 1e-7
    assert direct.maximum_dynamic_defect <= 1e-8
    assert shooting.maximum_dynamic_defect <= 1e-12
    assert abs(direct.cost - shooting.cost) <= 1e-5


def test_direct_collocation_enforces_trapezoidal_collocation_equations():
    result = solve_direct_collocation(intervals=20, horizon=1.0, target_position=1.0)
    dt = result.time[1] - result.time[0]
    position_defect = (
        result.state[1:, 0]
        - result.state[:-1, 0]
        - 0.5 * dt * (result.state[:-1, 1] + result.state[1:, 1])
    )
    velocity_defect = (
        result.state[1:, 1]
        - result.state[:-1, 1]
        - 0.5 * dt * (result.control[:-1] + result.control[1:])
    )

    assert result.control.size == result.time.size
    assert np.max(np.abs(position_defect)) <= 1e-8
    assert np.max(np.abs(velocity_defect)) <= 1e-8


@pytest.mark.parametrize("chapter_id", ESTIMATION_CHAPTERS)
def test_estimation_optimization_labs_write_real_result_log_plot_and_portfolio(tmp_path, chapter_id):
    result_path = run_estimation_optimization_lab(chapter_id, output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["chapter_id"] == chapter_id
    assert result["seed"] == 0
    assert result["passed"] is True
    assert (tmp_path / result["plots"][0]).is_file()
    assert (tmp_path / result["logs"][0]).is_file()
    assert (tmp_path / "portfolio" / chapter_id / "evidence.json").is_file()


def test_chapter_21_uses_mujoco_sensors_and_compares_ekf_with_ukf(tmp_path, monkeypatch):
    original_read_sensors = estimation_labs.read_sensors
    original_compute_action = WheelBalancerController.compute_action
    original_update_estimator = estimation_labs._update_pitch_estimator
    sensor_call_count = 0
    controller_observations = []
    ukf_states = []

    def spy_read_sensors(data, sensor_map):
        nonlocal sensor_call_count
        sensor_call_count += 1
        return original_read_sensors(data, sensor_map)

    def spy_compute_action(controller, runner, sim_time, estimated_state=None):
        controller_observations.append(
            (
                None if estimated_state is None else dict(estimated_state),
                dict(runner.posture_state()),
                runner.spec.equilibrium_pitch_rad,
            )
        )
        return original_compute_action(
            controller,
            runner,
            sim_time,
            estimated_state=estimated_state,
        )

    def spy_update_estimator(filter_, measurement_value, dt):
        state = original_update_estimator(filter_, measurement_value, dt)
        if isinstance(filter_, UnscentedKalmanFilter):
            ukf_states.append(state.copy())
        return state

    monkeypatch.setattr(estimation_labs, "read_sensors", spy_read_sensors)
    monkeypatch.setattr(WheelBalancerController, "compute_action", spy_compute_action)
    monkeypatch.setattr(estimation_labs, "_update_pitch_estimator", spy_update_estimator)
    result_path = run_estimation_optimization_lab("21", output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    log = json.loads((tmp_path / result["logs"][0]).read_text(encoding="utf-8"))

    assert log["sensor_backend"] == "mujoco_sensordata"
    assert log["seed"] == 0
    assert result["seed"] == 0
    assert log["sample_count"] >= 100
    assert set(log["sensor_names"]) >= {
        "imu_accelerometer",
        "imu_gyroscope",
        "left_wheel_velocity",
        "right_wheel_velocity",
    }
    assert set(result["metrics"]) >= {
        "raw_pitch_rmse_rad",
        "ekf_pitch_rmse_rad",
        "ukf_pitch_rmse_rad",
        "closed_loop_survived",
        "closed_loop_max_abs_pitch_rad",
    }
    assert result["metrics"]["closed_loop_survived"] == 1.0
    assert sensor_call_count == int(result["metrics"]["closed_loop_sample_count"])
    assert len(controller_observations) == sensor_call_count
    assert all(estimated is not None for estimated, _, _ in controller_observations)
    assert any(
        not np.isclose(estimated["pitch_error"], truth["pitch_error"], atol=1e-6)
        for estimated, truth, _ in controller_observations
    )
    assert len(ukf_states) == sensor_call_count
    for (estimated, _, equilibrium_pitch), previous_ukf in zip(
        controller_observations[1:],
        ukf_states[:-1],
        strict=True,
    ):
        np.testing.assert_allclose(
            [
                estimated["pitch_error"],
                estimated["pitch_rate"],
                estimated["forward_velocity"],
                estimated["x_position"],
            ],
            [
                previous_ukf[0] - equilibrium_pitch,
                previous_ukf[1],
                previous_ukf[2],
                previous_ukf[3],
            ],
        )
    assert result["metrics"]["ekf_rmse_improvement_ratio"] >= 1.2
    assert result["metrics"]["ukf_rmse_improvement_ratio"] >= 1.2
    assert result["metrics"]["ukf_to_ekf_rmse_ratio"] <= 1.1
    assert log["truth_usage"] == "metrics_only"
    assert log["closed_loop_controller_observation"] == "ukf_estimate"


@pytest.mark.parametrize(
    ("chapter_function", "expected_seed"),
    [
        (estimation_labs._chapter_20, 0),
        (estimation_labs._chapter_21, 0),
        (estimation_labs._chapter_22, 0),
    ],
)
def test_estimation_chapter_rng_and_result_metadata_share_one_seed_variable(
    chapter_function,
    expected_seed,
):
    source = inspect.getsource(chapter_function)

    assert f"seed: int = {expected_seed}" in source
    assert "np.random.default_rng(seed)" in source
    assert '"seed": seed' in source


def test_estimation_cli_entrypoints_accept_fixed_seed_argument():
    scripts = [
        "run_estimation_optimization_lab.py",
        "run_mpc_balance_compare.py",
        "run_trajectory_optimization_lab.py",
    ]

    for filename in scripts:
        source = (PROJECT_ROOT / "scripts" / filename).read_text(encoding="utf-8")
        assert 'add_argument("--seed", type=int, default=0' in source


def test_chapter_19_tutorial_uses_deterministic_standing_loop_and_stops_on_fall():
    tutorial = (PROJECT_ROOT / "tutorials" / "v2" / "19" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "seed = 19" in tutorial
    assert "np.random.default_rng(seed)" in tutorial
    assert "runner.step(controller.compute_action(runner, runner.time))" in tutorial
    assert "survived = True" in tutorial
    assert "survived = False" in tutorial
    assert "break" in tutorial
    assert '"survived": survived' in tutorial


@pytest.mark.parametrize(
    ("chapter_id", "result_name", "obsolete_snapshot"),
    [
        ("20", "estimation_20.json", "0.07976595983432411"),
        ("21", "estimation_21.json", "3.054648"),
        ("22", "estimation_22.json", "0.0004619528907167319"),
        ("24", "trajectory_24.json", "12.11662249"),
    ],
)
def test_estimation_tutorial_metrics_come_from_result_with_six_digit_format(
    chapter_id,
    result_name,
    obsolete_snapshot,
):
    tutorial = (
        PROJECT_ROOT / "tutorials" / "v2" / chapter_id / "README.md"
    ).read_text(encoding="utf-8")

    assert result_name in tutorial
    assert 'result["metrics"]' in tutorial
    assert ".6f" in tutorial
    assert obsolete_snapshot not in tutorial


def test_chapter_23_records_all_kkt_conditions_and_duality_gap(tmp_path):
    result_path = run_estimation_optimization_lab("23", output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    log = json.loads((tmp_path / result["logs"][0]).read_text(encoding="utf-8"))

    for metric in (
        "kkt_stationarity_residual",
        "kkt_primal_feasibility_residual",
        "kkt_dual_feasibility_residual",
        "kkt_complementarity_residual",
        "duality_gap",
    ):
        assert result["checks"][metric] is True
    assert log["kkt"]["inequality_multipliers"][0] == pytest.approx(1.1, abs=1e-7)


def test_chapter_24_trajectory_lab_writes_comparable_method_evidence(tmp_path):
    result_path = run_trajectory_optimization_lab(output_root=tmp_path, source_root=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    log = json.loads((tmp_path / result["logs"][0]).read_text(encoding="utf-8"))

    assert result["chapter_id"] == "24"
    assert result["seed"] == 0
    assert log["seed"] == 0
    assert result["passed"] is True
    assert set(log["methods"]) == {"direct_collocation", "single_shooting"}
    assert log["shared_problem"]["target_position"] == 1.0
    for metric in (
        "direct_collocation_terminal_error",
        "shooting_terminal_error",
        "direct_collocation_dynamic_defect",
        "shooting_dynamic_defect",
        "trajectory_cost_gap",
    ):
        assert result["checks"][metric] is True
    assert (tmp_path / result["plots"][0]).is_file()
    assert (tmp_path / result["logs"][0]).is_file()
    assert (tmp_path / "portfolio" / "24" / "trajectory_optimization.json").is_file()
