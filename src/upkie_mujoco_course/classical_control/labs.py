"""12-18 经典控制关卡的真实实验与证据生成。"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from upkie_mujoco_course.classical_control.math_tools import controllability_matrix
from upkie_mujoco_course.classical_control.math_tools import inverted_pendulum_acceleration
from upkie_mujoco_course.classical_control.math_tools import linearized_inverted_pendulum_acceleration
from upkie_mujoco_course.classical_control.math_tools import observability_matrix
from upkie_mujoco_course.classical_control.math_tools import second_order_frequency_magnitude
from upkie_mujoco_course.classical_control.math_tools import second_order_poles
from upkie_mujoco_course.classical_control.math_tools import simulate_second_order
from upkie_mujoco_course.classical_control.math_tools import solve_scalar_euler_lagrange
from upkie_mujoco_course.classical_control.math_tools import solve_scalar_hjb
from upkie_mujoco_course.classical_control.math_tools import solve_scalar_pontryagin
from upkie_mujoco_course.classical_control.math_tools import wheel_pendulum_state_space
from upkie_mujoco_course.commands.command_types import MotionCommand
from upkie_mujoco_course.controllers.lqr import LQRBalanceController
from upkie_mujoco_course.controllers.motion import MotionController
from upkie_mujoco_course.controllers.pid import PIDController
from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.course.results import write_experiment_result
from upkie_mujoco_course.sim.runner import SimulationRunner
from upkie_mujoco_course.utils.paths import project_root


CLASSICAL_CHAPTERS = ("12", "13", "14", "15", "16", "17", "18")


def _resolve_output_root(output_root: str | Path) -> Path:
    root = Path(output_root)
    return root if root.is_absolute() else project_root() / root


def _save_figure(figure: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _simulate_pid(anti_windup: bool) -> dict[str, np.ndarray | float]:
    dt = 0.01
    time = np.arange(0.0, 6.0, dt)
    target = np.where(time < 2.0, 2.0, 0.0)
    controller = PIDController(2.0, 3.0, 0.05, limit=1.0, anti_windup=anti_windup)
    position = np.zeros_like(time)
    action = np.zeros_like(time)
    integral = np.zeros_like(time)
    for index in range(1, time.size):
        action[index] = controller.step(target[index] - position[index - 1], dt)
        position[index] = position[index - 1] + dt * ((-position[index - 1] + action[index]) / 0.35)
        integral[index] = controller.integral
    post_release = time >= 2.0
    return {
        "time": time,
        "target": target,
        "position": position,
        "action": action,
        "integral": integral,
        "integral_peak": float(np.max(np.abs(integral))),
        "integral_at_release": float(integral[np.searchsorted(time, 2.0) - 1]),
        "post_release_iae": float(np.sum(np.abs(position[post_release])) * dt),
    }


def _run_pd_balance(duration: float = 10.0) -> dict[str, np.ndarray | float]:
    """运行 PD 轮端平衡控制器并返回轨迹数据。"""
    runner = SimulationRunner()
    controller = WheelBalancerController()
    runner.reset("crouch")
    time_list: list[float] = []
    pitch_error: list[float] = []
    pitch_rate: list[float] = []
    height: list[float] = []
    torque_left: list[float] = []
    x_pos: list[float] = []
    contact: list[float] = []
    try:
        while runner.time < duration:
            action = controller.compute_action(runner, runner.time)
            runner.step(action)
            state = runner.posture_state()
            time_list.append(runner.time)
            pitch_error.append(float(state["pitch_error"]))
            pitch_rate.append(float(state["pitch_rate"]))
            height.append(float(state["base_height"]))
            x_pos.append(float(state["x_position"]))
            contact.append(float(bool(state["both_wheels_contact"])))
            left_id = runner.actuator_ids["left_wheel_motor"]
            torque_left.append(float(action[left_id]))
    finally:
        runner.close()
    return {
        "time": np.asarray(time_list),
        "pitch_error": np.asarray(pitch_error),
        "pitch_rate": np.asarray(pitch_rate),
        "height": np.asarray(height),
        "torque_left": np.asarray(torque_left),
        "x_position": np.asarray(x_pos),
        "contact": np.asarray(contact),
    }


def _compute_settle_time(time: np.ndarray, signal: np.ndarray, threshold: float) -> float:
    """计算信号最后一次超出 ±threshold 的时刻。"""
    exceed = np.abs(signal) > threshold
    if not np.any(exceed):
        return 0.0
    indices = np.where(exceed)[0]
    return float(time[indices[-1]])


def _chapter_12(plot_path: Path) -> tuple[dict, dict, dict]:
    """第 12 章实验：比例控制基线（PD 轮端平衡器）。"""
    trace = _run_pd_balance(duration=10.0)
    time_arr = trace["time"]
    pe = trace["pitch_error"]
    torque = trace["torque_left"]
    height = trace["height"]

    # 稳定阶段取最后 3 秒
    stable_mask = time_arr >= (float(time_arr[-1]) - 3.0)
    peak_pitch_error = float(np.max(np.abs(pe)))
    rms_pitch_error = float(np.sqrt(np.mean(pe[stable_mask] ** 2)))
    settle_time = _compute_settle_time(time_arr, pe, np.deg2rad(5.0))
    torque_rms = float(np.sqrt(np.mean(torque[stable_mask] ** 2)))
    torque_peak = float(np.max(np.abs(torque)))
    height_mean = float(np.mean(height[stable_mask]))
    contact_ratio = float(np.mean(trace["contact"]))

    metrics = {
        "peak_pitch_error_rad": peak_pitch_error,
        "rms_pitch_error_rad": rms_pitch_error,
        "settle_time_5deg_s": settle_time,
        "torque_rms_nm": torque_rms,
        "torque_peak_nm": torque_peak,
        "stable_height_m": height_mean,
        "wheel_contact_ratio": contact_ratio,
    }
    conditions = {
        "peak_pitch_error_rad": {"operator": "<=", "value": np.deg2rad(30.0)},
        "rms_pitch_error_rad": {"operator": "<=", "value": np.deg2rad(10.0)},
        "torque_peak_nm": {"operator": "<=", "value": 1.0},
        "wheel_contact_ratio": {"operator": ">=", "value": 0.9},
    }

    figure, axes = plt.subplots(3, 1, figsize=(9.0, 7.5), sharex=True)
    axes[0].plot(time_arr, np.rad2deg(pe), color="#17745a", label="pitch error")
    axes[0].axhline(0.0, color="#17201d", linewidth=0.6)
    axes[0].axhspan(-5.0, 5.0, color="#17745a", alpha=0.10, label="±5° band")
    axes[0].set(ylabel="pitch error [deg]", title="Chapter 12: PD wheel-balance baseline")
    axes[1].plot(time_arr, torque, color="#2978b5", label="left-wheel torque")
    axes[1].axhline(0.0, color="#17201d", linewidth=0.6)
    axes[1].set(ylabel="torque [N·m]")
    axes[2].plot(time_arr, height, color="#d36b27", label="base height")
    axes[2].set(xlabel="time [s]", ylabel="height [m]")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend(loc="upper right")
    _save_figure(figure, plot_path)

    stride = max(1, time_arr.size // 200)
    return metrics, conditions, {
        "controller": "WheelBalancerController (PD)",
        "duration_s": 10.0,
        "sample_period_s": float(np.mean(np.diff(time_arr))) if time_arr.size > 1 else 0.0,
        "trace": {
            "time_s": time_arr[::stride].tolist(),
            "pitch_error_deg": np.rad2deg(pe)[::stride].tolist(),
            "torque_nm": torque[::stride].tolist(),
        },
        "metrics": metrics,
    }


def _chapter_13(plot_path: Path) -> tuple[dict, dict, dict]:
    protected = _simulate_pid(True)
    naive = _simulate_pid(False)
    improvement = float(naive["post_release_iae"] / protected["post_release_iae"])
    metrics = {
        "protected_integral_peak": float(protected["integral_peak"]),
        "naive_integral_peak": float(naive["integral_peak"]),
        "protected_integral_at_release": float(abs(protected["integral_at_release"])),
        "naive_integral_at_release": float(abs(naive["integral_at_release"])),
        "recovery_iae_improvement_ratio": improvement,
        "protected_output_peak": float(np.max(np.abs(protected["action"]))),
    }
    conditions = {
        "protected_integral_at_release": {"operator": "<=", "value": 0.02},
        "naive_integral_at_release": {"operator": ">=", "value": 1.0},
        "recovery_iae_improvement_ratio": {"operator": ">=", "value": 1.5},
        "protected_output_peak": {"operator": "<=", "value": 1.0},
    }
    figure, axes = plt.subplots(2, 1, figsize=(8.4, 6.2), sharex=True)
    axes[0].plot(protected["time"], protected["target"], "--", color="#17201d", label="target")
    axes[0].plot(protected["time"], protected["position"], color="#17745a", label="anti-windup")
    axes[0].plot(naive["time"], naive["position"], color="#d36b27", label="naive integral")
    axes[0].set(ylabel="plant state", title="Chapter 13: saturation and integral windup")
    axes[1].plot(protected["time"], protected["integral"], color="#17745a", label="protected integral")
    axes[1].plot(naive["time"], naive["integral"], color="#d36b27", label="naive integral")
    axes[1].set(xlabel="time [s]", ylabel="integral [state*s]")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend()
    _save_figure(figure, plot_path)
    return metrics, conditions, {"plant_time_constant_s": 0.35, "sample_period_s": 0.01, "metrics": metrics}


def _chapter_14(plot_path: Path) -> tuple[dict, dict, dict]:
    angles = np.linspace(-1.2, 1.2, 401)
    torque = 0.2
    nonlinear = np.asarray(inverted_pendulum_acceleration(angles, torque))
    linear = np.asarray(linearized_inverted_pendulum_acceleration(angles, torque))
    small_mask = np.abs(angles) <= np.deg2rad(10.0)
    large_angle = np.deg2rad(60.0)
    torque_gain = abs(
        float(inverted_pendulum_acceleration(0.0, 0.5))
        - float(inverted_pendulum_acceleration(0.0, 0.0))
    ) / 0.5
    metrics = {
        "small_angle_max_error_rad_s2": float(np.max(np.abs(nonlinear[small_mask] - linear[small_mask]))),
        "large_angle_error_rad_s2": float(
            abs(
                inverted_pendulum_acceleration(large_angle, torque)
                - linearized_inverted_pendulum_acceleration(large_angle, torque)
            )
        ),
        "torque_acceleration_gain_rad_s2_per_nm": float(torque_gain),
    }
    conditions = {
        "small_angle_max_error_rad_s2": {"operator": "<=", "value": 0.02},
        "large_angle_error_rad_s2": {"operator": ">=", "value": 1.0},
        "torque_acceleration_gain_rad_s2_per_nm": {"operator": ">=", "value": 0.39},
    }
    figure, axis = plt.subplots(figsize=(8.2, 4.8))
    axis.plot(angles, nonlinear, label="nonlinear")
    axis.plot(angles, linear, "--", label="linearized")
    axis.axvspan(-np.deg2rad(10.0), np.deg2rad(10.0), color="#17745a", alpha=0.12, label="local valid region")
    axis.set(xlabel="pitch error [rad]", ylabel="pitch acceleration [rad/s^2]", title="Chapter 14: wheel inverted-pendulum dynamics")
    axis.grid(alpha=0.25)
    axis.legend()
    _save_figure(figure, plot_path)
    return metrics, conditions, {"mass_kg": 10.0, "com_length_m": 0.5, "wheel_torque_nm": torque, "metrics": metrics}


def _chapter_15(plot_path: Path) -> tuple[dict, dict, dict]:
    natural_frequency = 4.0
    stable_damping = 0.7
    unstable_damping = -0.1
    stable_poles = second_order_poles(natural_frequency, stable_damping)
    unstable_poles = second_order_poles(natural_frequency, unstable_damping)
    time, stable_response = simulate_second_order(natural_frequency, stable_damping)
    _, unstable_response = simulate_second_order(natural_frequency, unstable_damping)
    frequencies = np.logspace(-1.0, 1.5, 300)
    magnitude = second_order_frequency_magnitude(frequencies, natural_frequency, stable_damping)
    metrics = {
        "stable_max_real_pole": float(np.max(np.real(stable_poles))),
        "unstable_max_real_pole": float(np.max(np.real(unstable_poles))),
        "stable_final_abs_state": float(abs(stable_response[-1])),
        "unstable_peak_abs_state": float(np.max(np.abs(unstable_response))),
        "frequency_peak_gain": float(np.max(magnitude)),
    }
    conditions = {
        "stable_max_real_pole": {"operator": "<", "value": 0.0},
        "unstable_max_real_pole": {"operator": ">", "value": 0.0},
        "stable_final_abs_state": {"operator": "<=", "value": 0.01},
        "unstable_peak_abs_state": {"operator": ">=", "value": 2.0},
    }
    figure, axes = plt.subplots(1, 2, figsize=(10.0, 4.4))
    axes[0].plot(time, stable_response, color="#17745a", label="zeta=0.7")
    axes[0].plot(time, unstable_response, color="#d36b27", label="zeta=-0.1")
    axes[0].set(xlabel="time [s]", ylabel="state", title="Pole sign predicts time response")
    axes[0].grid(alpha=0.25)
    axes[0].legend()
    axes[1].semilogx(frequencies, magnitude, color="#2978b5")
    axes[1].axvline(natural_frequency, color="#17201d", linestyle="--", label="natural frequency")
    axes[1].set(xlabel="frequency [rad/s]", ylabel="gain", title="Stable frequency response")
    axes[1].grid(alpha=0.25)
    axes[1].legend()
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "natural_frequency_rad_s": natural_frequency,
        "stable_poles": [[float(value.real), float(value.imag)] for value in stable_poles],
        "unstable_poles": [[float(value.real), float(value.imag)] for value in unstable_poles],
        "metrics": metrics,
    }


def _chapter_16(plot_path: Path) -> tuple[dict, dict, dict]:
    a, b = wheel_pendulum_state_space()
    controllability = controllability_matrix(a, b)
    c = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]])
    observability = observability_matrix(a, c)
    faulty_b = b.copy()
    faulty_b[3, 0] = 0.0
    faulty_controllability = controllability_matrix(a, faulty_b)
    singular_values = np.linalg.svd(controllability, compute_uv=False)
    faulty_singular_values = np.linalg.svd(faulty_controllability, compute_uv=False)
    metrics = {
        "controllability_rank": float(np.linalg.matrix_rank(controllability)),
        "observability_rank": float(np.linalg.matrix_rank(observability)),
        "minimum_controllability_singular_value": float(np.min(singular_values)),
        "faulty_input_controllability_rank": float(np.linalg.matrix_rank(faulty_controllability)),
    }
    conditions = {
        "controllability_rank": {"operator": "==", "value": 4.0},
        "observability_rank": {"operator": "==", "value": 4.0},
        "minimum_controllability_singular_value": {"operator": ">", "value": 0.0},
        "faulty_input_controllability_rank": {"operator": "<=", "value": 2.0},
    }
    figure, axis = plt.subplots(figsize=(7.8, 4.6))
    indices = np.arange(1, singular_values.size + 1)
    axis.semilogy(indices, singular_values, "o-", color="#17745a", label="physical input mapping")
    axis.semilogy(indices, np.maximum(faulty_singular_values, 1e-16), "o--", color="#d36b27", label="pitch coupling removed")
    axis.set(xticks=indices, xlabel="singular-value index", ylabel="magnitude", title="Chapter 16: controllability is a graded property")
    axis.grid(alpha=0.25)
    axis.legend()
    _save_figure(figure, plot_path)
    return metrics, conditions, {"state_order": ["x", "x_rate", "pitch", "pitch_rate"], "A": a.tolist(), "B": b.tolist(), "metrics": metrics}


def _run_lqr_balance(duration: float = 10.0) -> dict[str, np.ndarray | float]:
    """运行 LQR 平衡控制器并返回轨迹数据。"""
    runner = SimulationRunner()
    controller = LQRBalanceController()
    runner.reset("stand")
    time_list: list[float] = []
    pitch_error: list[float] = []
    pitch_rate: list[float] = []
    height: list[float] = []
    torque_left: list[float] = []
    x_pos: list[float] = []
    contact: list[float] = []
    try:
        while runner.time < duration:
            action = controller.compute_action(runner)
            runner.step(action)
            state = runner.posture_state()
            time_list.append(runner.time)
            pitch_error.append(float(state["pitch_error"]))
            pitch_rate.append(float(state["pitch_rate"]))
            height.append(float(state["base_height"]))
            x_pos.append(float(state["x_position"]))
            contact.append(float(bool(state["both_wheels_contact"])))
            left_id = runner.actuator_ids["left_wheel_motor"]
            torque_left.append(float(action[left_id]))
    finally:
        runner.close()
    return {
        "time": np.asarray(time_list),
        "pitch_error": np.asarray(pitch_error),
        "pitch_rate": np.asarray(pitch_rate),
        "height": np.asarray(height),
        "torque_left": np.asarray(torque_left),
        "x_position": np.asarray(x_pos),
        "contact": np.asarray(contact),
    }


def _chapter_17(plot_path: Path) -> tuple[dict, dict, dict]:
    """第 17 章实验：LQR 对比 PD 平衡控制器。"""
    pd_trace = _run_pd_balance(duration=10.0)
    lqr_trace = _run_lqr_balance(duration=10.0)

    def _summarize(trace: dict) -> dict[str, float]:
        t = trace["time"]
        pe = trace["pitch_error"]
        tq = trace["torque_left"]
        stable = t >= (float(t[-1]) - 3.0)
        return {
            "peak_pitch_error_rad": float(np.max(np.abs(pe))),
            "rms_pitch_error_rad": float(np.sqrt(np.mean(pe[stable] ** 2))),
            "settle_time_5deg_s": _compute_settle_time(t, pe, np.deg2rad(5.0)),
            "torque_rms_nm": float(np.sqrt(np.mean(tq[stable] ** 2))),
            "torque_peak_nm": float(np.max(np.abs(tq))),
            "contact_ratio": float(np.mean(trace["contact"])),
        }

    pd_stats = _summarize(pd_trace)
    lqr_stats = _summarize(lqr_trace)
    optimal_solutions = {
        "euler_lagrange": solve_scalar_euler_lagrange(
            initial_state=1.0,
            horizon=2.0,
            terminal_weight=4.0,
        ),
        "hjb": solve_scalar_hjb(
            initial_state=1.0,
            horizon=2.0,
            terminal_weight=4.0,
        ),
        "pontryagin": solve_scalar_pontryagin(
            initial_state=1.0,
            horizon=2.0,
            terminal_weight=4.0,
        ),
    }
    euler = optimal_solutions["euler_lagrange"]
    hjb = optimal_solutions["hjb"]
    pontryagin = optimal_solutions["pontryagin"]
    state_agreement = float(
        max(
            np.max(np.abs(euler.state - hjb.state)),
            np.max(np.abs(euler.state - pontryagin.state)),
        )
    )
    control_agreement = float(
        max(
            np.max(np.abs(euler.control - hjb.control)),
            np.max(np.abs(euler.control - pontryagin.control)),
        )
    )
    cost_values = np.asarray([solution.cost for solution in optimal_solutions.values()])

    # 计算 LQR 相对 PD 的改善比
    pitch_improvement = float(pd_stats["rms_pitch_error_rad"] / max(lqr_stats["rms_pitch_error_rad"], 1e-9))
    torque_ratio = float(lqr_stats["torque_rms_nm"] / max(pd_stats["torque_rms_nm"], 1e-9))

    metrics = {
        "pd_peak_pitch_error_rad": pd_stats["peak_pitch_error_rad"],
        "pd_rms_pitch_error_rad": pd_stats["rms_pitch_error_rad"],
        "pd_settle_time_5deg_s": pd_stats["settle_time_5deg_s"],
        "pd_torque_rms_nm": pd_stats["torque_rms_nm"],
        "pd_torque_peak_nm": pd_stats["torque_peak_nm"],
        "pd_contact_ratio": pd_stats["contact_ratio"],
        "lqr_peak_pitch_error_rad": lqr_stats["peak_pitch_error_rad"],
        "lqr_rms_pitch_error_rad": lqr_stats["rms_pitch_error_rad"],
        "lqr_settle_time_5deg_s": lqr_stats["settle_time_5deg_s"],
        "lqr_torque_rms_nm": lqr_stats["torque_rms_nm"],
        "lqr_torque_peak_nm": lqr_stats["torque_peak_nm"],
        "lqr_contact_ratio": lqr_stats["contact_ratio"],
        "pitch_rms_improvement_ratio": pitch_improvement,
        "torque_consumption_ratio": torque_ratio,
        "euler_lagrange_equation_residual": euler.equation_residual,
        "hjb_equation_residual": hjb.equation_residual,
        "pontryagin_costate_residual": pontryagin.costate_residual,
        "pontryagin_stationarity_residual": pontryagin.stationarity_residual,
        "pontryagin_transversality_residual": pontryagin.transversality_residual,
        "optimal_control_state_agreement": state_agreement,
        "optimal_control_control_agreement": control_agreement,
        "optimal_control_cost_agreement": float(np.max(cost_values) - np.min(cost_values)),
    }
    conditions = {
        "lqr_peak_pitch_error_rad": {"operator": "<=", "value": np.deg2rad(30.0)},
        "lqr_rms_pitch_error_rad": {"operator": "<=", "value": np.deg2rad(10.0)},
        "lqr_torque_peak_nm": {"operator": "<=", "value": 1.0},
        "lqr_contact_ratio": {"operator": ">=", "value": 0.9},
        "euler_lagrange_equation_residual": {"operator": "<=", "value": 1e-10},
        "hjb_equation_residual": {"operator": "<=", "value": 1e-10},
        "pontryagin_costate_residual": {"operator": "<=", "value": 1e-10},
        "pontryagin_stationarity_residual": {"operator": "<=", "value": 1e-10},
        "pontryagin_transversality_residual": {"operator": "<=", "value": 1e-10},
        "optimal_control_state_agreement": {"operator": "<=", "value": 1e-10},
        "optimal_control_control_agreement": {"operator": "<=", "value": 1e-10},
        "optimal_control_cost_agreement": {"operator": "<=", "value": 1e-10},
    }

    figure, axes = plt.subplots(3, 2, figsize=(13.0, 8.0))
    axes[0, 0].plot(pd_trace["time"], np.rad2deg(pd_trace["pitch_error"]),
                    color="#d36b27", alpha=0.85, label="PD")
    axes[0, 0].plot(lqr_trace["time"], np.rad2deg(lqr_trace["pitch_error"]),
                    color="#17745a", alpha=0.85, label="LQR")
    axes[0, 0].axhline(0.0, color="#17201d", linewidth=0.6)
    axes[0, 0].axhspan(-5.0, 5.0, color="#8b5fbf", alpha=0.08, label="±5° band")
    axes[0, 0].set(ylabel="pitch error [deg]", title="MuJoCo: LQR vs PD")
    axes[1, 0].plot(pd_trace["time"], pd_trace["torque_left"],
                    color="#d36b27", alpha=0.7, label="PD torque")
    axes[1, 0].plot(lqr_trace["time"], lqr_trace["torque_left"],
                    color="#17745a", alpha=0.7, label="LQR torque")
    axes[1, 0].axhline(0.0, color="#17201d", linewidth=0.6)
    axes[1, 0].set(ylabel="torque [N·m]")
    axes[2, 0].plot(pd_trace["time"], pd_trace["height"],
                    color="#d36b27", alpha=0.85, label="PD height")
    axes[2, 0].plot(lqr_trace["time"], lqr_trace["height"],
                    color="#17745a", alpha=0.85, label="LQR height")
    axes[2, 0].set(xlabel="time [s]", ylabel="height [m]")
    method_colors = {"euler_lagrange": "#2978b5", "hjb": "#8b5fbf", "pontryagin": "#d36b27"}
    for name, solution in optimal_solutions.items():
        axes[0, 1].plot(solution.time, solution.state, color=method_colors[name], label=name)
        axes[1, 1].plot(solution.time, solution.control, color=method_colors[name], label=name)
    axes[0, 1].set(ylabel="state x", title="Scalar optimal-control agreement")
    axes[1, 1].set(ylabel="control u")
    residual_names = ["Euler-Lagrange", "HJB", "PMP costate", "PMP stationarity", "PMP terminal"]
    residual_values = [
        euler.equation_residual,
        hjb.equation_residual,
        pontryagin.costate_residual,
        pontryagin.stationarity_residual,
        pontryagin.transversality_residual,
    ]
    axes[2, 1].bar(residual_names, np.maximum(residual_values, 1e-18), color="#17745a")
    axes[2, 1].set_yscale("log")
    axes[2, 1].tick_params(axis="x", rotation=20)
    axes[2, 1].set(xlabel="equation", ylabel="absolute residual")
    for axis in axes.flat:
        axis.grid(alpha=0.25)
        if axis is not axes[2, 1]:
            axis.legend(loc="upper right")
    _save_figure(figure, plot_path)

    stride = max(1, pd_trace["time"].size // 200)
    return metrics, conditions, {
        "seed": 17,
        "pd_controller": "WheelBalancerController (PD)",
        "lqr_controller": "LQRBalanceController",
        "duration_s": 10.0,
        "pd_trace": {
            "time_s": pd_trace["time"][::stride].tolist(),
            "pitch_error_deg": np.rad2deg(pd_trace["pitch_error"])[::stride].tolist(),
            "torque_nm": pd_trace["torque_left"][::stride].tolist(),
        },
        "lqr_trace": {
            "time_s": lqr_trace["time"][::stride].tolist(),
            "pitch_error_deg": np.rad2deg(lqr_trace["pitch_error"])[::stride].tolist(),
            "torque_nm": lqr_trace["torque_left"][::stride].tolist(),
        },
        "optimal_control": {
            "problem": {
                "dynamics": "x_dot=u",
                "initial_state": 1.0,
                "horizon_s": 2.0,
                "running_cost": "0.5*u^2",
                "terminal_cost": "0.5*4*x(T)^2",
            },
            "methods": {
                name: {
                    "time_s": solution.time.tolist(),
                    "state": solution.state.tolist(),
                    "control": solution.control.tolist(),
                    "cost": solution.cost,
                    "equation_residual": solution.equation_residual,
                    "stationarity_residual": solution.stationarity_residual,
                    "costate_residual": solution.costate_residual,
                    "transversality_residual": solution.transversality_residual,
                }
                for name, solution in optimal_solutions.items()
            },
        },
        "metrics": metrics,
    }


def _yaw_from_runner(runner: SimulationRunner) -> float:
    qpos_address = int(runner.model.jnt_qposadr[runner.root_joint_id])
    qw, qx, qy, qz = [float(value) for value in runner.data.qpos[qpos_address + 3 : qpos_address + 7]]
    return float(np.arctan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz)))


def _chapter_18(plot_path: Path) -> tuple[dict, dict, dict]:
    runner = SimulationRunner()
    runner.reset("stand")
    controller = MotionController(acceleration_limit=0.2)
    time: list[float] = []
    velocity: list[float] = []
    velocity_target: list[float] = []
    yaw: list[float] = []
    height: list[float] = []
    height_target: list[float] = []
    pitch_error: list[float] = []
    wheel_torque_peak = 0.0
    contact_samples: list[float] = []
    yaw_mode_started = False
    height_mode_started = False
    try:
        while runner.time < 17.0:
            if runner.time < 8.0:
                command = MotionCommand(forward_velocity=0.1, height=0.0, source="chapter18:velocity")
            elif runner.time < 14.0:
                if not yaw_mode_started:
                    controller.reset()
                    yaw_mode_started = True
                command = MotionCommand(yaw_rate=0.45, height=0.0, source="chapter18:yaw")
            else:
                if not height_mode_started:
                    controller.reset()
                    height_mode_started = True
                command = MotionCommand(height=-0.02, source="chapter18:height")
            action = controller.compute_action(runner, command)
            wheel_ids = [runner.actuator_ids[item.name] for item in runner.spec.torque_actuators]
            wheel_torque_peak = max(wheel_torque_peak, float(np.max(np.abs(action[wheel_ids]))))
            runner.step(action)
            state = runner.posture_state()
            time.append(runner.time)
            velocity.append(float(state["forward_velocity"]))
            velocity_target.append(float(command.forward_velocity))
            yaw.append(_yaw_from_runner(runner))
            height.append(float(state["base_height"]))
            height_target.append(float(command.height))
            pitch_error.append(float(state["pitch_error"]))
            contact_samples.append(float(bool(state["both_wheels_contact"])))
    finally:
        runner.close()

    time_array = np.asarray(time)
    velocity_array = np.asarray(velocity)
    yaw_array = np.unwrap(np.asarray(yaw))
    height_array = np.asarray(height)
    velocity_window = (time_array >= 7.0) & (time_array < 8.0)
    final_window = time_array >= 16.0
    yaw_start = float(yaw_array[np.searchsorted(time_array, 8.0)])
    yaw_end = float(yaw_array[np.searchsorted(time_array, 14.0)])
    height_error_m = float(abs(np.mean(height_array[final_window]) - (-0.02)))
    metrics = {
        "velocity_error_m_s": float(abs(np.mean(velocity_array[velocity_window]) - 0.1)),
        "yaw_change_rad": float(abs(yaw_end - yaw_start)),
        "height_error_m": height_error_m,
        "height_improvement_ratio": float(0.02 / height_error_m),
        "max_pitch_error_rad": float(np.max(np.abs(pitch_error))),
        "wheel_torque_peak_nm": float(wheel_torque_peak),
        "wheel_contact_ratio": float(np.mean(contact_samples)),
    }
    conditions = {
        "velocity_error_m_s": {"operator": "<=", "value": 0.15},
        "yaw_change_rad": {"operator": ">=", "value": 0.5},
        "height_error_m": {"operator": "<=", "value": 0.018},
        "height_improvement_ratio": {"operator": ">=", "value": 1.2},
        "max_pitch_error_rad": {"operator": "<=", "value": 0.3},
        "wheel_torque_peak_nm": {"operator": "<=", "value": 1.0},
        "wheel_contact_ratio": {"operator": ">=", "value": 0.95},
    }
    figure, axes = plt.subplots(3, 1, figsize=(9.0, 8.0), sharex=True)
    axes[0].plot(time_array, velocity_target, "--", color="#17201d", label="target")
    axes[0].plot(time_array, velocity_array, color="#17745a", label="measured")
    axes[0].set(ylabel="velocity [m/s]")
    axes[1].plot(time_array, yaw_array, color="#2978b5", label="yaw")
    axes[1].set(ylabel="yaw [rad]")
    axes[2].plot(time_array, height_target, "--", color="#17201d", label="height target")
    axes[2].plot(time_array, height_array, color="#d36b27", label="base height")
    axes[2].plot(time_array, pitch_error, color="#8b5fbf", alpha=0.8, label="pitch error")
    axes[2].set(xlabel="time [s]", ylabel="height / pitch [m or rad]")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend(loc="upper right")
    axes[0].set_title("Chapter 18: velocity, yaw and height command interface")
    _save_figure(figure, plot_path)
    stride = 20
    return metrics, conditions, {
        "control_period_s": 0.01,
        "trace": {
            "time_s": time_array[::stride].tolist(),
            "velocity_m_s": velocity_array[::stride].tolist(),
            "yaw_rad": yaw_array[::stride].tolist(),
            "height_m": height_array[::stride].tolist(),
        },
        "metrics": metrics,
    }


LABS = {
    "12": _chapter_12,
    "13": _chapter_13,
    "14": _chapter_14,
    "15": _chapter_15,
    "16": _chapter_16,
    "17": _chapter_17,
    "18": _chapter_18,
}


def run_classical_control_lab(
    chapter_id: str,
    *,
    output_root: str | Path = "outputs",
    source_root: str | Path | None = None,
    seed: int = 0,
) -> Path:
    if chapter_id not in LABS:
        raise ValueError(f"经典控制实验只支持 {CLASSICAL_CHAPTERS}，收到: {chapter_id}")
    root = _resolve_output_root(output_root)
    plot_path = root / "plots" / f"classical_{chapter_id}.png"
    log_path = root / "logs" / f"classical_{chapter_id}.json"
    result_path = root / "results" / f"classical_{chapter_id}.json"
    metrics, conditions, log = LABS[chapter_id](plot_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    written_result = write_experiment_result(
        result_path,
        chapter_id=chapter_id,
        seed=seed,
        config={"lab": f"classical_{chapter_id}"},
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
