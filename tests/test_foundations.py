"""测试基础模块（foundation_01 ~ foundation_05）。

覆盖场景：
- 基础数学工具与单位换算
- 配置加载与项目路径解析
- 基础数据结构契约
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pytest

from upkie_mujoco_course.foundations.labs import run_foundation_lab
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


def test_foundation_labs_use_noninteractive_plot_backend():
    assert matplotlib.get_backend().lower() == "agg"


def test_seeded_trace_is_reproducible_and_seed_sensitive():
    first = seeded_normal_trace(seed=7, size=64)
    second = seeded_normal_trace(seed=7, size=64)
    different = seeded_normal_trace(seed=8, size=64)

    assert np.array_equal(first, second)
    assert not np.array_equal(first, different)


def test_coordinate_transform_round_trip_recovers_body_point():
    rotation = rotation_matrix_yaw(np.deg2rad(30.0))
    translation = np.array([1.0, -0.4, 0.2])
    body_point = np.array([0.3, 0.1, -0.2])

    world_point = transform_point(body_point, rotation, translation)
    restored = inverse_transform_point(world_point, rotation, translation)

    assert np.allclose(restored, body_point, atol=1e-12)
    assert np.isclose(np.linalg.det(rotation), 1.0, atol=1e-12)


def test_svd_reconstructs_rectangular_robot_observation_matrix():
    matrix = np.array([[1.0, 0.2], [0.1, 0.9], [0.5, 0.4]])
    left_vectors, singular_values, right_vectors_t = singular_value_decomposition(matrix)
    reconstructed = left_vectors @ np.diag(singular_values) @ right_vectors_t

    assert left_vectors.shape == (3, 2)
    assert singular_values.shape == (2,)
    assert right_vectors_t.shape == (2, 2)
    assert np.all(singular_values[:-1] >= singular_values[1:])
    assert np.allclose(reconstructed, matrix, atol=1e-12)


def test_symmetric_eigendecomposition_recovers_stiffness_matrix():
    matrix = np.array([[4.0, 1.0], [1.0, 2.0]])
    eigenvalues, eigenvectors = symmetric_eigendecomposition(matrix)
    reconstructed = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T

    assert np.allclose(eigenvectors.T @ eigenvectors, np.eye(2), atol=1e-12)
    assert np.allclose(reconstructed, matrix, atol=1e-12)
    assert np.allclose(matrix @ eigenvectors, eigenvectors * eigenvalues, atol=1e-12)


def test_central_difference_matches_sine_derivative():
    derivative = central_difference(np.sin, x=0.4, step=1e-5)
    assert np.isclose(derivative, np.cos(0.4), atol=1e-8)


def test_matrix_quadratic_gradient_matches_finite_difference():
    matrix = np.array([[4.0, 1.0], [1.0, 3.0]])
    point = np.array([0.4, -0.2])
    objective = lambda value: float(0.5 * value @ matrix @ value)
    analytic = quadratic_gradient(matrix, point)
    numerical = finite_difference_gradient(objective, point=point, step=1e-6)

    assert np.allclose(analytic, [1.4, -0.2], atol=1e-12)
    assert np.allclose(analytic, numerical, atol=1e-8)


def test_small_angle_linearization_is_accurate_only_near_equilibrium():
    small = np.deg2rad(5.0)
    large = np.deg2rad(60.0)
    small_error = abs(
        pendulum_acceleration(small) - linearized_pendulum_acceleration(small)
    )
    large_error = abs(
        pendulum_acceleration(large) - linearized_pendulum_acceleration(large)
    )

    assert small_error < 0.002
    assert large_error > 0.5


def test_low_pass_filter_reduces_fixed_seed_pitch_rmse():
    time = np.arange(0.0, 4.0, 0.01)
    clean = 0.1 * np.sin(2.0 * np.pi * 0.7 * time)
    noisy = clean + 0.08 * seeded_normal_trace(seed=5, size=time.size)
    filtered = low_pass_filter(noisy, alpha=0.2)

    assert rmse(filtered[20:], clean[20:]) < rmse(noisy[20:], clean[20:])


@pytest.mark.parametrize("chapter_id", ["01", "02", "03", "04", "05"])
def test_foundation_lab_writes_real_result_log_and_plot(tmp_path, chapter_id):
    result_path = run_foundation_lab(
        chapter_id,
        output_root=tmp_path,
        seed=0,
        source_root=tmp_path,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["chapter_id"] == chapter_id
    assert result["passed"] is True
    assert result["metrics"]
    assert result["plots"] and (tmp_path / result["plots"][0]).is_file()
    assert result["logs"] and (tmp_path / result["logs"][0]).is_file()
    portfolio_path = tmp_path / "portfolio" / chapter_id / "evidence.json"
    assert portfolio_path.is_file()
    portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
    assert portfolio["chapter_id"] == chapter_id
    assert Path(portfolio["result_path"]) == result_path


@pytest.mark.parametrize(
    ("chapter_id", "required_metrics", "required_log_sections"),
    [
        (
            "03",
            {"svd_reconstruction_error", "eigen_reconstruction_error"},
            {"svd", "eigendecomposition"},
        ),
        (
            "04",
            {"matrix_gradient_max_error"},
            {"matrix_derivative"},
        ),
    ],
)
def test_foundation_03_04_save_linear_algebra_evidence(
    tmp_path,
    chapter_id,
    required_metrics,
    required_log_sections,
):
    result_path = run_foundation_lab(
        chapter_id,
        output_root=tmp_path,
        seed=0,
        source_root=tmp_path,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    log = json.loads((tmp_path / result["logs"][0]).read_text(encoding="utf-8"))

    assert required_metrics <= set(result["metrics"])
    assert required_log_sections <= set(log)
    assert result["passed"] is True
