"""20-23 状态估计与优化关卡的可执行实验。"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import lsq_linear, minimize

from upkie_mujoco_course.controllers.trajectory_optimization import solve_direct_collocation
from upkie_mujoco_course.controllers.trajectory_optimization import solve_single_shooting
from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.course.results import write_experiment_result
from upkie_mujoco_course.estimation.ekf import ExtendedKalmanFilter
from upkie_mujoco_course.estimation.kalman import LinearKalmanFilter
from upkie_mujoco_course.estimation.ukf import UnscentedKalmanFilter
from upkie_mujoco_course.sim.runner import SimulationRunner
from upkie_mujoco_course.sim.sensors import read_sensors
from upkie_mujoco_course.utils.paths import project_root


ESTIMATION_CHAPTERS = ("20", "21", "22", "23")


@dataclass(frozen=True)
class QuadraticProgramResult:
    solution: np.ndarray
    success: bool
    objective: float
    maximum_violation: float
    message: str


@dataclass(frozen=True)
class KKTDiagnostics:
    stationarity_residual: float
    primal_feasibility_residual: float
    dual_feasibility_residual: float
    complementarity_residual: float
    duality_gap: float
    primal_objective: float
    dual_objective: float
    inequality_multipliers: np.ndarray
    upper_bound_multipliers: np.ndarray
    lower_bound_multipliers: np.ndarray


def compute_kkt_diagnostics(
    *,
    solution: np.ndarray,
    hessian: np.ndarray,
    linear_term: np.ndarray,
    inequality: np.ndarray,
    upper_bound: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    active_tolerance: float = 1e-7,
) -> KKTDiagnostics:
    """计算凸 QP 的 KKT 五项残差与对偶间隙。"""

    solution = np.asarray(solution, dtype=float).reshape(-1)
    hessian = np.asarray(hessian, dtype=float)
    linear_term = np.asarray(linear_term, dtype=float).reshape(-1)
    inequality = np.asarray(inequality, dtype=float)
    upper_bound = np.asarray(upper_bound, dtype=float).reshape(-1)
    lower = np.asarray(lower, dtype=float).reshape(-1)
    upper = np.asarray(upper, dtype=float).reshape(-1)
    size = solution.size
    identity = np.eye(size)
    constraint_matrix = np.vstack([inequality, identity, -identity])
    constraint_bound = np.concatenate([upper_bound, upper, -lower])
    slack = constraint_bound - constraint_matrix @ solution
    active = slack <= active_tolerance
    multipliers = np.zeros(constraint_bound.size, dtype=float)
    gradient = hessian @ solution + linear_term
    if np.any(active):
        fit = lsq_linear(
            constraint_matrix[active].T,
            -gradient,
            bounds=(0.0, np.inf),
            tol=1e-14,
            lsmr_tol=1e-14,
        )
        multipliers[active] = fit.x
    stationarity = gradient + constraint_matrix.T @ multipliers
    primal_objective = float(0.5 * solution @ hessian @ solution + linear_term @ solution)
    dual_linear = linear_term + constraint_matrix.T @ multipliers
    dual_objective = float(
        -0.5 * dual_linear @ np.linalg.pinv(hessian) @ dual_linear
        - constraint_bound @ multipliers
    )
    coupled_count = inequality.shape[0]
    return KKTDiagnostics(
        stationarity_residual=float(np.max(np.abs(stationarity))),
        primal_feasibility_residual=float(max(0.0, np.max(-slack))),
        dual_feasibility_residual=float(max(0.0, np.max(-multipliers))),
        complementarity_residual=float(np.max(np.abs(multipliers * slack))),
        duality_gap=abs(primal_objective - dual_objective),
        primal_objective=primal_objective,
        dual_objective=dual_objective,
        inequality_multipliers=multipliers[:coupled_count],
        upper_bound_multipliers=multipliers[coupled_count : coupled_count + size],
        lower_bound_multipliers=multipliers[coupled_count + size :],
    )


def solve_quadratic_program(
    *,
    hessian: np.ndarray,
    linear_term: np.ndarray,
    inequality: np.ndarray,
    upper_bound: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> QuadraticProgramResult:
    """求解 min 0.5*x^T H*x + f^T*x, s.t. A*x<=b 与逐元素边界。"""

    hessian = np.asarray(hessian, dtype=float)
    linear_term = np.asarray(linear_term, dtype=float).reshape(-1)
    inequality = np.asarray(inequality, dtype=float)
    upper_bound = np.asarray(upper_bound, dtype=float).reshape(-1)
    lower = np.asarray(lower, dtype=float).reshape(-1)
    upper = np.asarray(upper, dtype=float).reshape(-1)
    size = linear_term.size
    if hessian.shape != (size, size) or inequality.shape[1:] != (size,):
        raise ValueError("QP 矩阵维度不一致")
    if upper_bound.size != inequality.shape[0] or lower.size != size or upper.size != size:
        raise ValueError("QP 约束维度不一致")
    if not np.allclose(hessian, hessian.T, atol=1e-10):
        raise ValueError("QP Hessian 必须对称")
    if np.min(np.linalg.eigvalsh(hessian)) < -1e-10:
        raise ValueError("QP Hessian 必须半正定")

    def objective(value: np.ndarray) -> float:
        return float(0.5 * value @ hessian @ value + linear_term @ value)

    def gradient(value: np.ndarray) -> np.ndarray:
        return hessian @ value + linear_term

    constraints = {
        "type": "ineq",
        "fun": lambda value: upper_bound - inequality @ value,
        "jac": lambda value: -inequality,
    }
    initial = np.clip(np.zeros(size), lower, upper)
    result = minimize(
        objective,
        initial,
        jac=gradient,
        method="SLSQP",
        bounds=list(zip(lower, upper, strict=True)),
        constraints=constraints,
        options={"ftol": 1e-12, "maxiter": 200},
    )
    solution = np.asarray(result.x, dtype=float)
    violation = np.concatenate(
        [
            inequality @ solution - upper_bound,
            lower - solution,
            solution - upper,
        ]
    )
    return QuadraticProgramResult(
        solution=solution,
        success=bool(result.success),
        objective=objective(solution),
        maximum_violation=float(max(0.0, np.max(violation))),
        message=str(result.message),
    )


def _resolve_output_root(output_root: str | Path) -> Path:
    root = Path(output_root)
    return root if root.is_absolute() else project_root() / root


def _save_figure(figure: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _rmse(estimate: np.ndarray, truth: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(estimate) - np.asarray(truth)) ** 2)))


def _chapter_20(plot_path: Path, seed: int = 0) -> tuple[dict, dict, dict]:
    rng = np.random.default_rng(seed)
    dt = 0.01
    time = np.arange(0.0, 6.0, dt)
    true_angle = 0.25 * np.sin(0.8 * time)
    measurements = true_angle + rng.normal(0.0, 0.08, size=time.size)
    filter_ = LinearKalmanFilter(
        state=np.zeros(2),
        covariance=np.diag([0.2, 0.5]),
        transition=np.array([[1.0, dt], [0.0, 1.0]]),
        observation=np.array([[1.0, 0.0]]),
        process_noise=np.diag([2e-5, 1e-3]),
        measurement_noise=np.array([[0.08**2]]),
    )
    estimate = np.empty_like(true_angle)
    covariance_trace = np.empty_like(true_angle)
    for index, measurement in enumerate(measurements):
        filter_.predict()
        estimate[index] = filter_.update(np.array([measurement]))[0]
        covariance_trace[index] = float(np.trace(filter_.covariance))
    raw_rmse = _rmse(measurements, true_angle)
    estimate_rmse = _rmse(estimate, true_angle)
    metrics = {
        "raw_measurement_rmse_rad": raw_rmse,
        "kalman_rmse_rad": estimate_rmse,
        "rmse_improvement_ratio": float(raw_rmse / estimate_rmse),
        "final_covariance_trace": float(covariance_trace[-1]),
    }
    conditions = {
        "kalman_rmse_rad": {"operator": "<=", "value": 0.05},
        "rmse_improvement_ratio": {"operator": ">=", "value": 1.5},
        "final_covariance_trace": {"operator": "<=", "value": 0.03},
    }
    figure, axes = plt.subplots(2, 1, figsize=(8.5, 6.0), sharex=True)
    axes[0].plot(time, true_angle, color="#17201d", label="true pitch")
    axes[0].plot(time, measurements, color="#aeb7b3", alpha=0.5, label="measurement")
    axes[0].plot(time, estimate, color="#17745a", label="Kalman estimate")
    axes[0].set(ylabel="pitch [rad]", title="Chapter 20: linear Kalman filtering")
    axes[1].plot(time, covariance_trace, color="#2978b5", label="trace(P)")
    axes[1].set(xlabel="time [s]", ylabel="uncertainty", yscale="log")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend()
    _save_figure(figure, plot_path)
    return metrics, conditions, {"seed": seed, "sample_period_s": dt, "metrics": metrics}


def _estimator_models(dt: float):
    transition = lambda state: np.array(
        [state[0] + dt * state[1], state[1], state[2], state[3] + dt * state[2]]
    )
    transition_jacobian = lambda state: np.array(
        [
            [1.0, dt, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, dt, 1.0],
        ]
    )
    measurement = lambda state: np.array(
        [
            np.sin(state[0]),
            np.cos(state[0]),
            state[1],
            state[2],
            np.sin(state[0]),
            np.cos(state[0]),
        ]
    )
    measurement_jacobian = lambda state: np.array(
        [
            [np.cos(state[0]), 0.0, 0.0, 0.0],
            [-np.sin(state[0]), 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [np.cos(state[0]), 0.0, 0.0, 0.0],
            [-np.sin(state[0]), 0.0, 0.0, 0.0],
        ]
    )
    return transition, transition_jacobian, measurement, measurement_jacobian


def _new_pitch_estimators(initial_pitch: float):
    arguments = {
        "state": np.array([initial_pitch, 0.0, 0.0, 0.0]),
        "covariance": np.diag([0.03, 0.2, 0.2, 0.02]),
        "process_noise": np.diag([2e-5, 2e-3, 1e-5, 1e-6]),
        "measurement_noise": np.diag(
            [0.035**2, 0.035**2, 0.03**2, 0.03**2, 0.25**2, 0.25**2]
        ),
    }
    return ExtendedKalmanFilter(**arguments), UnscentedKalmanFilter(**arguments)


def _sensor_measurement(
    readings: dict[str, np.ndarray],
    runner: SimulationRunner,
    rng: np.random.Generator,
) -> tuple[np.ndarray, float]:
    qw, qx, qy, qz = readings["imu_orientation"]
    orientation_pitch = float(
        np.arcsin(np.clip(2.0 * (qw * qy - qz * qx), -1.0, 1.0))
    )
    accelerometer = readings["imu_accelerometer"]
    accelerometer_pitch = float(
        np.arctan2(
            -accelerometer[0],
            np.hypot(accelerometer[1], accelerometer[2]),
        )
    )
    raw_pitch = float(orientation_pitch + rng.normal(0.0, 0.035))
    left_velocity = float(readings["left_wheel_velocity"][0])
    right_velocity = float(readings["right_wheel_velocity"][0])
    directions = runner.spec.wheel_directions
    wheel_velocity = 0.5 * (
        directions[0] * left_velocity * runner.left_wheel_radius
        + directions[1] * right_velocity * runner.right_wheel_radius
    ) + rng.normal(0.0, 0.03)
    measurement = np.array(
        [
            np.sin(raw_pitch),
            np.cos(raw_pitch),
            readings["imu_gyroscope"][1] + rng.normal(0.0, 0.03),
            wheel_velocity,
            np.sin(accelerometer_pitch),
            np.cos(accelerometer_pitch),
        ]
    )
    return measurement, raw_pitch


def _update_pitch_estimator(filter_, measurement_value: np.ndarray, dt: float) -> np.ndarray:
    transition, transition_jacobian, measurement, measurement_jacobian = _estimator_models(dt)
    if isinstance(filter_, ExtendedKalmanFilter):
        filter_.predict(transition=transition, transition_jacobian=transition_jacobian)
        return filter_.update(
            measurement_value,
            measurement=measurement,
            measurement_jacobian=measurement_jacobian,
        )
    filter_.predict(transition=transition)
    return filter_.update(measurement_value, measurement=measurement)


def _chapter_21(plot_path: Path, seed: int = 0) -> tuple[dict, dict, dict]:
    runner = SimulationRunner()
    runner.reset("stand")
    rng = np.random.default_rng(seed)
    controller = WheelBalancerController(
        standup_duration=0.2,
        position_gain=0.2,
        forward_velocity_gain=0.1,
    )
    dt = runner.model.opt.timestep * runner.spec.frame_skip
    ekf, ukf = _new_pitch_estimators(runner.spec.equilibrium_pitch_rad)
    control_estimate = ukf.state.copy()
    time_values: list[float] = []
    truth_values: list[float] = []
    raw_values: list[float] = []
    ekf_values: list[float] = []
    ukf_values: list[float] = []
    max_pitch = 0.0
    survived = True
    while runner.time < 3.0:
        estimated_state = {
            "pitch_error": float(control_estimate[0] - runner.spec.equilibrium_pitch_rad),
            "pitch_rate": float(control_estimate[1]),
            "forward_velocity": float(control_estimate[2]),
            "x_position": float(control_estimate[3]),
        }
        runner.step(
            controller.compute_action(
                runner,
                runner.time,
                estimated_state=estimated_state,
            )
        )
        readings = read_sensors(runner.data, runner.sensor_map)
        measurement_value, raw_pitch = _sensor_measurement(readings, runner, rng)
        ekf_state = _update_pitch_estimator(ekf, measurement_value, dt)
        ukf_state = _update_pitch_estimator(ukf, measurement_value, dt)
        control_estimate = ukf_state
        truth_state = runner.posture_state()
        time_values.append(runner.time)
        truth_values.append(float(truth_state["pitch"]))
        raw_values.append(raw_pitch)
        ekf_values.append(float(ekf_state[0]))
        ukf_values.append(float(ukf_state[0]))
        max_pitch = max(max_pitch, abs(float(truth_state["pitch"])))
        if float(truth_state["base_height"]) <= -0.35 or max_pitch >= 0.5:
            survived = False
            break
    sensor_names = list(runner.spec.sensor_names)
    runner.close()

    truth = np.asarray(truth_values)
    raw = np.asarray(raw_values)
    ekf_pitch = np.asarray(ekf_values)
    ukf_pitch = np.asarray(ukf_values)
    raw_rmse = _rmse(raw, truth)
    ekf_rmse = _rmse(ekf_pitch, truth)
    ukf_rmse = _rmse(ukf_pitch, truth)
    metrics = {
        "raw_pitch_rmse_rad": raw_rmse,
        "ekf_pitch_rmse_rad": ekf_rmse,
        "ukf_pitch_rmse_rad": ukf_rmse,
        "ekf_rmse_improvement_ratio": float(raw_rmse / max(ekf_rmse, 1e-12)),
        "ukf_rmse_improvement_ratio": float(raw_rmse / max(ukf_rmse, 1e-12)),
        "ukf_to_ekf_rmse_ratio": float(ukf_rmse / max(ekf_rmse, 1e-12)),
        "closed_loop_survived": float(survived),
        "closed_loop_max_abs_pitch_rad": max_pitch,
        "closed_loop_sample_count": float(len(time_values)),
    }
    conditions = {
        "ekf_pitch_rmse_rad": {"operator": "<=", "value": 0.15},
        "ukf_pitch_rmse_rad": {"operator": "<=", "value": 0.15},
        "ekf_rmse_improvement_ratio": {"operator": ">=", "value": 1.2},
        "ukf_rmse_improvement_ratio": {"operator": ">=", "value": 1.2},
        "ukf_to_ekf_rmse_ratio": {"operator": "<=", "value": 1.1},
        "closed_loop_survived": {"operator": "==", "value": 1.0},
        "closed_loop_max_abs_pitch_rad": {"operator": "<=", "value": 0.5},
    }
    figure, axis = plt.subplots(figsize=(8.5, 4.6))
    axis.plot(time_values, truth, color="#17201d", label="truth (scoring only)")
    axis.plot(time_values, raw, color="#aeb7b3", alpha=0.55, label="raw IMU tilt")
    axis.plot(time_values, ekf_pitch, color="#8b5fbf", label="EKF")
    axis.plot(time_values, ukf_pitch, color="#17745a", label="UKF")
    axis.set(xlabel="time [s]", ylabel="pitch [rad]", title="Chapter 21: MuJoCo IMU and encoder fusion")
    axis.grid(alpha=0.25)
    axis.legend()
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "sensor_backend": "mujoco_sensordata",
        "sensor_names": sensor_names,
        "sample_count": len(time_values),
        "sample_period_s": dt,
        "simulated_sensor_noise_std": {
            "orientation_rad": 0.035,
            "gyroscope_rad_s": 0.03,
            "wheel_velocity_m_s": 0.03,
        },
        "truth_usage": "metrics_only",
        "closed_loop_controller_observation": "ukf_estimate",
        "closed_loop_position_gain": 0.2,
        "closed_loop_forward_velocity_gain": 0.1,
        "metrics": metrics,
    }


def _chapter_22(plot_path: Path, seed: int = 0) -> tuple[dict, dict, dict]:
    rng = np.random.default_rng(seed)
    alpha_true = 19.62
    beta_true = -0.4
    train_angle = rng.uniform(-0.25, 0.25, 500)
    train_torque = rng.uniform(-1.0, 1.0, 500)
    train_acceleration = alpha_true * train_angle + beta_true * train_torque + rng.normal(0.0, 0.03, 500)
    design = np.column_stack([train_angle, train_torque])
    parameters, _, _, _ = np.linalg.lstsq(design, train_acceleration, rcond=None)
    test_angle = rng.uniform(-0.25, 0.25, 200)
    test_torque = rng.uniform(-1.0, 1.0, 200)
    test_truth = alpha_true * test_angle + beta_true * test_torque
    prediction = np.column_stack([test_angle, test_torque]) @ parameters
    metrics = {
        "alpha_relative_error": float(abs(parameters[0] - alpha_true) / alpha_true),
        "beta_relative_error": float(abs(parameters[1] - beta_true) / abs(beta_true)),
        "test_prediction_rmse_rad_s2": _rmse(prediction, test_truth),
        "design_condition_number": float(np.linalg.cond(design)),
    }
    conditions = {
        "alpha_relative_error": {"operator": "<=", "value": 0.01},
        "beta_relative_error": {"operator": "<=", "value": 0.05},
        "test_prediction_rmse_rad_s2": {"operator": "<=", "value": 0.03},
        "design_condition_number": {"operator": "<=", "value": 5.0},
    }
    figure, axes = plt.subplots(1, 2, figsize=(10.0, 4.3))
    axes[0].scatter(test_truth, prediction, s=12, alpha=0.65, color="#17745a", label="held-out samples")
    limit = float(max(np.max(np.abs(test_truth)), np.max(np.abs(prediction))))
    axes[0].plot([-limit, limit], [-limit, limit], "--", color="#17201d", label="ideal")
    axes[0].set(xlabel="true acceleration [rad/s^2]", ylabel="predicted", title="Held-out model validation")
    axes[1].bar(["alpha", "beta"], parameters, color=["#2978b5", "#d36b27"])
    axes[1].axhline(alpha_true, color="#2978b5", linestyle="--", label="alpha true")
    axes[1].axhline(beta_true, color="#d36b27", linestyle="--", label="beta true")
    axes[1].set(ylabel="identified coefficient", title="Known-parameter recovery")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend()
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "true_parameters": {"alpha": alpha_true, "beta": beta_true},
        "identified_parameters": {"alpha": float(parameters[0]), "beta": float(parameters[1])},
        "metrics": metrics,
    }


def _chapter_23(plot_path: Path, seed: int = 0) -> tuple[dict, dict, dict]:
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
    unconstrained = -np.linalg.solve(hessian, linear_term)
    unconstrained_violation = float(max(0.0, np.max(inequality @ unconstrained - upper_bound)))
    kkt = compute_kkt_diagnostics(
        solution=result.solution,
        hessian=hessian,
        linear_term=linear_term,
        inequality=inequality,
        upper_bound=upper_bound,
        lower=lower,
        upper=upper,
    )
    metrics = {
        "solver_success": float(result.success),
        "maximum_constraint_violation": result.maximum_violation,
        "unconstrained_constraint_violation": unconstrained_violation,
        "constrained_objective": result.objective,
        "solution_sum": float(np.sum(result.solution)),
        "kkt_stationarity_residual": kkt.stationarity_residual,
        "kkt_primal_feasibility_residual": kkt.primal_feasibility_residual,
        "kkt_dual_feasibility_residual": kkt.dual_feasibility_residual,
        "kkt_complementarity_residual": kkt.complementarity_residual,
        "duality_gap": kkt.duality_gap,
    }
    conditions = {
        "solver_success": {"operator": "==", "value": 1.0},
        "maximum_constraint_violation": {"operator": "<=", "value": 1e-8},
        "unconstrained_constraint_violation": {"operator": ">=", "value": 1.0},
        "solution_sum": {"operator": "<=", "value": 0.9 + 1e-8},
        "kkt_stationarity_residual": {"operator": "<=", "value": 1e-8},
        "kkt_primal_feasibility_residual": {"operator": "<=", "value": 1e-8},
        "kkt_dual_feasibility_residual": {"operator": "<=", "value": 1e-10},
        "kkt_complementarity_residual": {"operator": "<=", "value": 1e-8},
        "duality_gap": {"operator": "<=", "value": 1e-8},
    }
    values = np.linspace(-0.7, 1.1, 240)
    left, right = np.meshgrid(values, values)
    objective = 0.5 * (2.0 * left**2 + 2.0 * right**2) - 2.0 * left - 2.0 * right
    feasible = (left >= -0.6) & (left <= 0.6) & (right >= -0.6) & (right <= 0.6) & (left + right <= 0.9)
    figure, axes = plt.subplots(1, 2, figsize=(11.5, 5.3))
    axes[0].contour(left, right, objective, levels=16, colors="#9aa5a1", linewidths=0.8)
    axes[0].contourf(left, right, feasible.astype(float), levels=[0.5, 1.5], colors=["#d9eee4"], alpha=0.65)
    axes[0].scatter(*unconstrained, color="#d36b27", s=70, label="unconstrained")
    axes[0].scatter(*result.solution, color="#17745a", s=70, label="QP solution")
    axes[0].plot([-0.6, 0.6], [1.5, 0.3], "--", color="#17201d", label="u_left+u_right=0.9")
    axes[0].set(xlabel="u_left [N*m]", ylabel="u_right [N*m]", xlim=(-0.7, 1.1), ylim=(-0.7, 1.1), aspect="equal", title="Constrained torque allocation")
    axes[0].grid(alpha=0.25)
    axes[0].legend(loc="upper left")
    kkt_names = ["stationarity", "primal", "dual", "complementarity", "duality gap"]
    kkt_values = [
        kkt.stationarity_residual,
        kkt.primal_feasibility_residual,
        kkt.dual_feasibility_residual,
        kkt.complementarity_residual,
        kkt.duality_gap,
    ]
    axes[1].bar(kkt_names, np.maximum(kkt_values, 1e-18), color="#17745a")
    axes[1].axhline(1e-8, color="#d36b27", linestyle="--", label="acceptance limit")
    axes[1].set_yscale("log")
    axes[1].tick_params(axis="x", rotation=25)
    axes[1].set(ylabel="absolute residual", title="KKT and strong-duality checks")
    axes[1].grid(alpha=0.25)
    axes[1].legend()
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "solution": result.solution.tolist(),
        "solver_message": result.message,
        "kkt": {
            "stationarity_residual": kkt.stationarity_residual,
            "primal_feasibility_residual": kkt.primal_feasibility_residual,
            "dual_feasibility_residual": kkt.dual_feasibility_residual,
            "complementarity_residual": kkt.complementarity_residual,
            "primal_objective": kkt.primal_objective,
            "dual_objective": kkt.dual_objective,
            "duality_gap": kkt.duality_gap,
            "inequality_multipliers": kkt.inequality_multipliers.tolist(),
            "upper_bound_multipliers": kkt.upper_bound_multipliers.tolist(),
            "lower_bound_multipliers": kkt.lower_bound_multipliers.tolist(),
        },
        "metrics": metrics,
    }


LABS = {"20": _chapter_20, "21": _chapter_21, "22": _chapter_22, "23": _chapter_23}


def run_trajectory_optimization_lab(
    *,
    output_root: str | Path = "outputs",
    source_root: str | Path | None = None,
    seed: int = 0,
) -> Path:
    """运行第 24 关直接配点与单次打靶的同题对照实验。"""

    root = _resolve_output_root(output_root)
    plot_path = root / "plots" / "trajectory_24.png"
    log_path = root / "logs" / "trajectory_24.json"
    result_path = root / "results" / "trajectory_24.json"
    intervals = 20
    horizon = 1.0
    target_position = 1.0
    control_limit = 10.0
    direct = solve_direct_collocation(
        intervals=intervals,
        horizon=horizon,
        target_position=target_position,
        control_limit=control_limit,
    )
    shooting = solve_single_shooting(
        intervals=intervals,
        horizon=horizon,
        target_position=target_position,
        control_limit=control_limit,
    )
    cost_gap = abs(direct.cost - shooting.cost)
    metrics = {
        "direct_collocation_success": float(direct.success),
        "shooting_success": float(shooting.success),
        "direct_collocation_terminal_error": direct.terminal_error,
        "shooting_terminal_error": shooting.terminal_error,
        "direct_collocation_dynamic_defect": direct.maximum_dynamic_defect,
        "shooting_dynamic_defect": shooting.maximum_dynamic_defect,
        "direct_collocation_cost": direct.cost,
        "shooting_cost": shooting.cost,
        "trajectory_cost_gap": cost_gap,
        "direct_collocation_peak_control": float(np.max(np.abs(direct.control))),
        "shooting_peak_control": float(np.max(np.abs(shooting.control))),
    }
    conditions = {
        "direct_collocation_success": {"operator": "==", "value": 1.0},
        "shooting_success": {"operator": "==", "value": 1.0},
        "direct_collocation_terminal_error": {"operator": "<=", "value": 1e-7},
        "shooting_terminal_error": {"operator": "<=", "value": 1e-7},
        "direct_collocation_dynamic_defect": {"operator": "<=", "value": 1e-8},
        "shooting_dynamic_defect": {"operator": "<=", "value": 1e-12},
        "trajectory_cost_gap": {"operator": "<=", "value": 1e-5},
        "direct_collocation_peak_control": {"operator": "<=", "value": control_limit + 1e-9},
        "shooting_peak_control": {"operator": "<=", "value": control_limit + 1e-9},
    }
    figure, axes = plt.subplots(2, 2, figsize=(10.5, 7.0))
    axes[0, 0].plot(direct.time, direct.state[:, 0], color="#17745a", label="direct collocation")
    axes[0, 0].plot(shooting.time, shooting.state[:, 0], "--", color="#d36b27", label="single shooting")
    axes[0, 0].axhline(target_position, color="#17201d", linestyle=":", label="target")
    axes[0, 0].set(xlabel="time [s]", ylabel="position [m]", title="Position trajectory")
    axes[0, 1].plot(direct.time, direct.state[:, 1], color="#17745a", label="direct collocation")
    axes[0, 1].plot(shooting.time, shooting.state[:, 1], "--", color="#d36b27", label="single shooting")
    axes[0, 1].set(xlabel="time [s]", ylabel="velocity [m/s]", title="Velocity trajectory")
    control_time = direct.time
    axes[1, 0].step(control_time, direct.control, where="post", color="#17745a", label="direct collocation")
    axes[1, 0].step(control_time, shooting.control, where="post", linestyle="--", color="#d36b27", label="single shooting")
    axes[1, 0].axhline(control_limit, color="#17201d", linestyle=":")
    axes[1, 0].axhline(-control_limit, color="#17201d", linestyle=":")
    axes[1, 0].set(xlabel="time [s]", ylabel="acceleration [m/s^2]", title="Optimized control")
    axes[1, 1].bar(
        ["terminal\nerror", "dynamic\ndefect", "cost gap"],
        [max(direct.terminal_error, shooting.terminal_error), max(direct.maximum_dynamic_defect, shooting.maximum_dynamic_defect), cost_gap],
        color=["#2978b5", "#8b5fbf", "#d36b27"],
    )
    axes[1, 1].set_yscale("log")
    axes[1, 1].set(ylabel="absolute residual", title="Method agreement and feasibility")
    for axis in axes.flat:
        axis.grid(alpha=0.25)
        if axis is not axes[1, 1]:
            axis.legend()
    _save_figure(figure, plot_path)
    log = {
        "seed": seed,
        "shared_problem": {
            "dynamics": "position_dot=velocity, velocity_dot=control",
            "initial_state": [0.0, 0.0],
            "target_position": target_position,
            "target_velocity": 0.0,
            "horizon_s": horizon,
            "intervals": intervals,
            "control_limit": control_limit,
            "objective": "integral(control^2 dt)",
        },
        "methods": {
            "direct_collocation": {
                "success": direct.success,
                "iterations": direct.iterations,
                "message": direct.message,
                "state": direct.state.tolist(),
                "control": direct.control.tolist(),
            },
            "single_shooting": {
                "success": shooting.success,
                "iterations": shooting.iterations,
                "message": shooting.message,
                "state": shooting.state.tolist(),
                "control": shooting.control.tolist(),
            },
        },
        "metrics": metrics,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    written_result = write_experiment_result(
        result_path,
        chapter_id="24",
        seed=seed,
        config={"lab": "trajectory_24", **log["shared_problem"]},
        metrics=metrics,
        pass_conditions=conditions,
        plots=[str(plot_path)],
        logs=[str(log_path)],
        root=source_root,
    )
    result_payload = json.loads(written_result.read_text(encoding="utf-8"))
    portfolio_path = root / "portfolio" / "24" / "trajectory_optimization.json"
    portfolio_path.parent.mkdir(parents=True, exist_ok=True)
    portfolio_path.write_text(
        json.dumps(
            {
                "chapter_id": "24",
                "passed": result_payload["passed"],
                "result_path": str(written_result),
                "plots": result_payload["plots"],
                "logs": result_payload["logs"],
                "metrics": result_payload["metrics"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return written_result


def run_estimation_optimization_lab(
    chapter_id: str,
    *,
    output_root: str | Path = "outputs",
    source_root: str | Path | None = None,
    seed: int = 0,
) -> Path:
    if chapter_id not in LABS:
        raise ValueError(f"估计与优化实验只支持 {ESTIMATION_CHAPTERS}，收到: {chapter_id}")
    root = _resolve_output_root(output_root)
    plot_path = root / "plots" / f"estimation_{chapter_id}.png"
    log_path = root / "logs" / f"estimation_{chapter_id}.json"
    result_path = root / "results" / f"estimation_{chapter_id}.json"
    metrics, conditions, log = LABS[chapter_id](plot_path, seed=seed)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    written_result = write_experiment_result(
        result_path,
        chapter_id=chapter_id,
        seed=int(log.get("seed", 0)),
        config={"lab": f"estimation_{chapter_id}"},
        metrics=metrics,
        pass_conditions=conditions,
        plots=[str(plot_path)],
        logs=[str(log_path)],
        root=source_root,
    )
    result = json.loads(written_result.read_text(encoding="utf-8"))
    portfolio_path = root / "portfolio" / chapter_id / "evidence.json"
    portfolio_path.parent.mkdir(parents=True, exist_ok=True)
    portfolio_path.write_text(
        json.dumps(
            {
                "chapter_id": chapter_id,
                "passed": result["passed"],
                "result_path": str(written_result),
                "plots": result["plots"],
                "logs": result["logs"],
                "metrics": result["metrics"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return written_result
