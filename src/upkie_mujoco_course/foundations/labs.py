"""01-05 基础关卡的真实实验与证据生成。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from upkie_mujoco_course.course.results import write_experiment_result
from upkie_mujoco_course.foundations.math_tools import central_difference
from upkie_mujoco_course.foundations.math_tools import finite_difference_gradient
from upkie_mujoco_course.foundations.math_tools import inverse_transform_point
from upkie_mujoco_course.foundations.math_tools import linearized_pendulum_acceleration
from upkie_mujoco_course.foundations.math_tools import low_pass_filter
from upkie_mujoco_course.foundations.math_tools import pendulum_acceleration
from upkie_mujoco_course.foundations.math_tools import rmse
from upkie_mujoco_course.foundations.math_tools import rotation_matrix_yaw
from upkie_mujoco_course.foundations.math_tools import seeded_normal_trace
from upkie_mujoco_course.foundations.math_tools import singular_value_decomposition
from upkie_mujoco_course.foundations.math_tools import symmetric_eigendecomposition
from upkie_mujoco_course.foundations.math_tools import quadratic_gradient
from upkie_mujoco_course.foundations.math_tools import transform_point
from upkie_mujoco_course.utils.paths import project_root


FOUNDATION_CHAPTERS = ("01", "02", "03", "04", "05")


def _resolve_output_root(output_root: str | Path) -> Path:
    root = Path(output_root)
    return root if root.is_absolute() else project_root() / root


def _save_figure(figure: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _chapter_01(seed: int, plot_path: Path) -> tuple[dict, dict, dict]:
    time = np.linspace(0.0, 2.0, 201)
    angle = np.sin(2.0 * np.pi * time)
    analytic_rate = 2.0 * np.pi * np.cos(2.0 * np.pi * time)
    numerical_rate = np.gradient(angle, time)
    table = np.column_stack((time, angle, numerical_rate))
    derivative_error = float(np.max(np.abs(numerical_rate[1:-1] - analytic_rate[1:-1])))
    metrics = {
        "sample_count": float(table.shape[0]),
        "feature_count": float(table.shape[1]),
        "finite_ratio": float(np.isfinite(table).mean()),
        "derivative_max_error_rad_s": derivative_error,
    }
    conditions = {
        "sample_count": {"operator": "==", "value": 201},
        "feature_count": {"operator": "==", "value": 3},
        "finite_ratio": {"operator": "==", "value": 1.0},
        "derivative_max_error_rad_s": {"operator": "<=", "value": 0.005},
    }
    figure, axis = plt.subplots(figsize=(8.0, 4.2))
    axis.plot(time, angle, label="pitch angle [rad]")
    axis.plot(time, numerical_rate, label="numerical pitch rate [rad/s]")
    axis.set(xlabel="time [s]", title="Chapter 01: NumPy array and numerical derivative")
    axis.grid(alpha=0.25)
    axis.legend()
    _save_figure(figure, plot_path)
    log = {
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "array_shape": list(table.shape),
        "array_dtype": str(table.dtype),
        "seed": seed,
        "metrics": metrics,
    }
    return metrics, conditions, log


def _chapter_02(seed: int, plot_path: Path) -> tuple[dict, dict, dict]:
    first = seeded_normal_trace(seed, 128)
    repeated = seeded_normal_trace(seed, 128)
    different = seeded_normal_trace(seed + 1, 128)
    same_seed_difference = float(np.max(np.abs(first - repeated)))
    different_seed_difference = float(np.mean(np.abs(first - different)))
    digest = hashlib.sha256(first.tobytes()).hexdigest()
    metrics = {
        "same_seed_max_difference": same_seed_difference,
        "different_seed_mean_difference": different_seed_difference,
        "trace_sha256_length": float(len(digest)),
    }
    conditions = {
        "same_seed_max_difference": {"operator": "==", "value": 0.0},
        "different_seed_mean_difference": {"operator": ">=", "value": 0.2},
        "trace_sha256_length": {"operator": "==", "value": 64},
    }
    figure, axis = plt.subplots(figsize=(8.0, 4.2))
    axis.plot(first[:48], label=f"seed={seed}")
    axis.plot(repeated[:48], "--", label=f"seed={seed} repeated")
    axis.plot(different[:48], alpha=0.7, label=f"seed={seed + 1}")
    axis.set(xlabel="sample", ylabel="noise", title="Chapter 02: Reproducible random trace")
    axis.grid(alpha=0.25)
    axis.legend()
    _save_figure(figure, plot_path)
    log = {"seed": seed, "repeated_trace_sha256": digest, "metrics": metrics}
    return metrics, conditions, log


def _chapter_03(seed: int, plot_path: Path) -> tuple[dict, dict, dict]:
    angle = np.deg2rad(30.0)
    rotation = rotation_matrix_yaw(angle)
    translation = np.array([1.0, -0.4, 0.2])
    body_point = np.array([0.3, 0.1, -0.2])
    world_point = transform_point(body_point, rotation, translation)
    restored = inverse_transform_point(world_point, rotation, translation)
    observation_matrix = np.array([[1.0, 0.2], [0.1, 0.9], [0.5, 0.4]])
    left_vectors, singular_values, right_vectors_t = singular_value_decomposition(observation_matrix)
    svd_reconstructed = left_vectors @ np.diag(singular_values) @ right_vectors_t
    stiffness_matrix = np.array([[4.0, 1.0], [1.0, 2.0]])
    eigenvalues, eigenvectors = symmetric_eigendecomposition(stiffness_matrix)
    eigen_reconstructed = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T
    metrics = {
        "round_trip_error_m": float(np.linalg.norm(restored - body_point)),
        "rotation_determinant_error": float(abs(np.linalg.det(rotation) - 1.0)),
        "orthogonality_error": float(np.linalg.norm(rotation.T @ rotation - np.eye(3))),
        "svd_reconstruction_error": float(np.linalg.norm(svd_reconstructed - observation_matrix)),
        "svd_condition_number": float(singular_values[0] / singular_values[-1]),
        "eigen_reconstruction_error": float(np.linalg.norm(eigen_reconstructed - stiffness_matrix)),
        "eigenpair_residual": float(
            np.linalg.norm(stiffness_matrix @ eigenvectors - eigenvectors * eigenvalues)
        ),
    }
    conditions = {
        "round_trip_error_m": {"operator": "<=", "value": 1e-12},
        "rotation_determinant_error": {"operator": "<=", "value": 1e-12},
        "orthogonality_error": {"operator": "<=", "value": 1e-12},
        "svd_reconstruction_error": {"operator": "<=", "value": 1e-12},
        "svd_condition_number": {"operator": "<=", "value": 10.0},
        "eigen_reconstruction_error": {"operator": "<=", "value": 1e-12},
        "eigenpair_residual": {"operator": "<=", "value": 1e-12},
    }
    figure, axes = plt.subplots(1, 2, figsize=(11.0, 5.2))
    axis = axes[0]
    axis.quiver(0.0, 0.0, 1.0, 0.0, angles="xy", scale_units="xy", scale=1, color="#17745a", label="world x")
    axis.quiver(0.0, 0.0, 0.0, 1.0, angles="xy", scale_units="xy", scale=1, color="#d36b27", label="world y")
    axis.quiver(translation[0], translation[1], rotation[0, 0], rotation[1, 0], angles="xy", scale_units="xy", scale=1, color="#2978b5", label="body x")
    axis.quiver(translation[0], translation[1], rotation[0, 1], rotation[1, 1], angles="xy", scale_units="xy", scale=1, color="#8b5fbf", label="body y")
    axis.scatter(*world_point[:2], color="#111111", s=55, label="transformed point")
    axis.set(xlim=(-0.3, 2.2), ylim=(-1.0, 1.4), aspect="equal", xlabel="world x [m]", ylabel="world y [m]", title="Chapter 03: Body-to-world transform")
    axis.grid(alpha=0.25)
    axis.legend(loc="upper left")
    axes[1].bar(
        ["sigma 1", "sigma 2", "lambda 1", "lambda 2"],
        [*singular_values, *eigenvalues],
        color=["#17745a", "#65a58d", "#d36b27", "#e1a36f"],
    )
    axes[1].set(ylabel="value", title="SVD singular values and symmetric eigenvalues")
    axes[1].grid(axis="y", alpha=0.25)
    _save_figure(figure, plot_path)
    log = {
        "seed": seed,
        "yaw_rad": angle,
        "translation_m": translation.tolist(),
        "body_point_m": body_point.tolist(),
        "world_point_m": world_point.tolist(),
        "svd": {
            "observation_matrix": observation_matrix.tolist(),
            "left_singular_vectors": left_vectors.tolist(),
            "singular_values": singular_values.tolist(),
            "right_singular_vectors_t": right_vectors_t.tolist(),
        },
        "eigendecomposition": {
            "stiffness_matrix": stiffness_matrix.tolist(),
            "eigenvalues": eigenvalues.tolist(),
            "eigenvectors_by_column": eigenvectors.tolist(),
        },
        "metrics": metrics,
    }
    return metrics, conditions, log


def _chapter_04(seed: int, plot_path: Path) -> tuple[dict, dict, dict]:
    angles = np.linspace(-1.2, 1.2, 401)
    exact = np.asarray(pendulum_acceleration(angles))
    linear = np.asarray(linearized_pendulum_acceleration(angles))
    small_mask = np.abs(angles) <= np.deg2rad(10.0)
    small_error = float(np.max(np.abs(exact[small_mask] - linear[small_mask])))
    large_angle = np.deg2rad(60.0)
    large_error = float(abs(pendulum_acceleration(large_angle) - linearized_pendulum_acceleration(large_angle)))
    derivative_error = float(abs(central_difference(np.sin, x=0.4, step=1e-5) - np.cos(0.4)))
    quadratic_matrix = np.array([[4.0, 1.0], [1.0, 3.0]])
    evaluation_point = np.array([0.4, -0.2])
    objective = lambda value: float(0.5 * value @ quadratic_matrix @ value)
    analytic_gradient = quadratic_gradient(quadratic_matrix, evaluation_point)
    numerical_gradient = finite_difference_gradient(objective, point=evaluation_point, step=1e-6)
    metrics = {
        "small_angle_max_error_rad_s2": small_error,
        "large_angle_error_rad_s2": large_error,
        "central_difference_error": derivative_error,
        "matrix_gradient_max_error": float(np.max(np.abs(analytic_gradient - numerical_gradient))),
    }
    conditions = {
        "small_angle_max_error_rad_s2": {"operator": "<=", "value": 0.01},
        "large_angle_error_rad_s2": {"operator": ">=", "value": 0.5},
        "central_difference_error": {"operator": "<=", "value": 1e-8},
        "matrix_gradient_max_error": {"operator": "<=", "value": 1e-8},
    }
    figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
    axis = axes[0]
    axis.plot(angles, exact, label="nonlinear: -g sin(theta) / l")
    axis.plot(angles, linear, "--", label="linearized: -g theta / l")
    axis.axvspan(-np.deg2rad(10.0), np.deg2rad(10.0), color="#17745a", alpha=0.12, label="small-angle region")
    axis.set(xlabel="angle [rad]", ylabel="angular acceleration [rad/s^2]", title="Chapter 04: Linearization has a valid region")
    axis.grid(alpha=0.25)
    axis.legend()
    indices = np.arange(evaluation_point.size)
    axes[1].bar(indices - 0.18, analytic_gradient, width=0.36, label="analytic", color="#17745a")
    axes[1].bar(indices + 0.18, numerical_gradient, width=0.36, label="finite difference", color="#d36b27")
    axes[1].set(
        xticks=indices,
        xticklabels=["dJ/dx1", "dJ/dx2"],
        ylabel="gradient",
        title="Matrix derivative check",
    )
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].legend()
    _save_figure(figure, plot_path)
    log = {
        "seed": seed,
        "gravity_m_s2": 9.81,
        "pendulum_length_m": 1.0,
        "matrix_derivative": {
            "objective": "0.5 * x.T @ A @ x",
            "matrix": quadratic_matrix.tolist(),
            "point": evaluation_point.tolist(),
            "analytic_gradient": analytic_gradient.tolist(),
            "finite_difference_gradient": numerical_gradient.tolist(),
            "finite_difference_step": 1e-6,
        },
        "metrics": metrics,
    }
    return metrics, conditions, log


def _chapter_05(seed: int, plot_path: Path) -> tuple[dict, dict, dict]:
    sample_period_s = 0.01
    time = np.arange(0.0, 4.0, sample_period_s)
    clean = 0.1 * np.sin(2.0 * np.pi * 0.7 * time)
    noisy = clean + 0.08 * seeded_normal_trace(seed, time.size)
    alpha = 0.2
    filtered = low_pass_filter(noisy, alpha=alpha)
    noisy_rmse = rmse(noisy[20:], clean[20:])
    filtered_rmse = rmse(filtered[20:], clean[20:])
    improvement = noisy_rmse / filtered_rmse
    metrics = {
        "noisy_rmse_rad": noisy_rmse,
        "filtered_rmse_rad": filtered_rmse,
        "rmse_improvement_ratio": improvement,
        "sample_rate_hz": 1.0 / sample_period_s,
    }
    conditions = {
        "filtered_rmse_rad": {"operator": "<=", "value": 0.05},
        "rmse_improvement_ratio": {"operator": ">=", "value": 1.5},
        "sample_rate_hz": {"operator": "==", "value": 100.0},
    }
    figure, axis = plt.subplots(figsize=(8.0, 4.4))
    axis.plot(time, noisy, color="#9aa5a1", linewidth=0.9, label="noisy measurement")
    axis.plot(time, clean, color="#17201d", linewidth=1.6, label="true pitch")
    axis.plot(time, filtered, color="#17745a", linewidth=1.4, label="low-pass estimate")
    axis.set(xlabel="time [s]", ylabel="pitch [rad]", title="Chapter 05: Noise filtering and lag")
    axis.grid(alpha=0.25)
    axis.legend()
    _save_figure(figure, plot_path)
    log = {
        "seed": seed,
        "sample_period_s": sample_period_s,
        "noise_standard_deviation_rad": 0.08,
        "low_pass_alpha": alpha,
        "metrics": metrics,
    }
    return metrics, conditions, log


LABS = {
    "01": _chapter_01,
    "02": _chapter_02,
    "03": _chapter_03,
    "04": _chapter_04,
    "05": _chapter_05,
}


def run_foundation_lab(
    chapter_id: str,
    *,
    output_root: str | Path = "outputs",
    seed: int = 0,
    source_root: str | Path | None = None,
) -> Path:
    if chapter_id not in LABS:
        raise ValueError(f"基础实验只支持 01-05，收到: {chapter_id}")
    root = _resolve_output_root(output_root)
    plot_path = root / "plots" / f"foundation_{chapter_id}.png"
    log_path = root / "logs" / f"foundation_{chapter_id}.json"
    result_path = root / "results" / f"foundation_{chapter_id}.json"
    metrics, conditions, log = LABS[chapter_id](int(seed), plot_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    written_result = write_experiment_result(
        result_path,
        chapter_id=chapter_id,
        seed=int(seed),
        config={"lab": f"foundation_{chapter_id}", **{key: value for key, value in log.items() if key not in {"metrics"}}},
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
