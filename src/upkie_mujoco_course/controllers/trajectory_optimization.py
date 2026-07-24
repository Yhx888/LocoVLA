"""双积分器轨迹优化的直接配点与单次打靶算例。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize


@dataclass(frozen=True)
class TrajectoryOptimizationResult:
    method: str
    success: bool
    time: np.ndarray
    state: np.ndarray
    control: np.ndarray
    cost: float
    terminal_error: float
    maximum_dynamic_defect: float
    iterations: int
    message: str


def _problem_matrices(intervals: int, horizon: float) -> tuple[float, np.ndarray, np.ndarray]:
    if intervals < 4:
        raise ValueError("intervals 至少为 4")
    if not np.isfinite(horizon) or horizon <= 0.0:
        raise ValueError("horizon 必须为正数")
    dt = horizon / intervals
    continuous = np.array([[0.0, 1.0], [0.0, 0.0]])
    input_vector = np.array([0.0, 1.0])
    left = np.eye(2) - 0.5 * dt * continuous
    transition = np.linalg.solve(left, np.eye(2) + 0.5 * dt * continuous)
    control = np.linalg.solve(left, 0.5 * dt * input_vector)
    return dt, transition, control


def _initial_control(intervals: int, horizon: float, target_position: float) -> np.ndarray:
    nodes = np.arange(intervals + 1, dtype=float) / intervals
    return 6.0 * target_position / (horizon * horizon) * (1.0 - 2.0 * nodes)


def _rollout(controls: np.ndarray, transition: np.ndarray, control_matrix: np.ndarray) -> np.ndarray:
    state = np.zeros((controls.size, 2), dtype=float)
    for index in range(controls.size - 1):
        state[index + 1] = (
            transition @ state[index]
            + control_matrix * (controls[index] + controls[index + 1])
        )
    return state


def _summarize_trajectory(
    *,
    method: str,
    optimization_result,
    state: np.ndarray,
    control: np.ndarray,
    horizon: float,
    target_position: float,
    transition: np.ndarray,
    control_matrix: np.ndarray,
) -> TrajectoryOptimizationResult:
    dt = horizon / (control.size - 1)
    defects = state[1:] - (
        state[:-1] @ transition.T
        + (control[:-1] + control[1:])[:, None] * control_matrix
    )
    terminal_error = float(np.linalg.norm(state[-1] - np.array([target_position, 0.0])))
    return TrajectoryOptimizationResult(
        method=method,
        success=bool(optimization_result.success),
        time=np.linspace(0.0, horizon, control.size),
        state=state,
        control=control,
        cost=float(
            dt
            * (
                0.5 * control[0] ** 2
                + np.sum(np.square(control[1:-1]))
                + 0.5 * control[-1] ** 2
            )
        ),
        terminal_error=terminal_error,
        maximum_dynamic_defect=float(np.max(np.abs(defects))),
        iterations=int(optimization_result.nit),
        message=str(optimization_result.message),
    )


def solve_direct_collocation(
    *,
    intervals: int = 20,
    horizon: float = 1.0,
    target_position: float = 1.0,
    control_limit: float = 10.0,
) -> TrajectoryOptimizationResult:
    """同时优化节点状态和分段常值控制，并强制动力学缺陷为零。"""

    dt, transition, control_matrix = _problem_matrices(intervals, horizon)
    if control_limit <= 0.0:
        raise ValueError("control_limit 必须为正数")
    initial_control = _initial_control(intervals, horizon, target_position)
    initial_state = _rollout(initial_control, transition, control_matrix)
    initial = np.concatenate([initial_state.ravel(), initial_control])
    state_size = 2 * (intervals + 1)
    control_size = intervals + 1

    def unpack(decision: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return decision[:state_size].reshape(intervals + 1, 2), decision[state_size:]

    def objective(decision: np.ndarray) -> float:
        _, control = unpack(decision)
        return float(
            dt
            * (
                0.5 * control[0] ** 2
                + np.sum(np.square(control[1:-1]))
                + 0.5 * control[-1] ** 2
            )
        )

    def equality(decision: np.ndarray) -> np.ndarray:
        state, control = unpack(decision)
        defects = state[1:] - (
            state[:-1] @ transition.T
            + (control[:-1] + control[1:])[:, None] * control_matrix
        )
        return np.concatenate(
            [
                state[0],
                defects.ravel(),
                state[-1] - np.array([target_position, 0.0]),
            ]
        )

    bounds = [(None, None)] * state_size + [(-control_limit, control_limit)] * control_size
    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=bounds,
        constraints={"type": "eq", "fun": equality},
        options={"ftol": 1e-12, "maxiter": 500},
    )
    state, control = unpack(np.asarray(result.x, dtype=float))
    return _summarize_trajectory(
        method="direct_collocation",
        optimization_result=result,
        state=state,
        control=control,
        horizon=horizon,
        target_position=target_position,
        transition=transition,
        control_matrix=control_matrix,
    )


def solve_single_shooting(
    *,
    intervals: int = 20,
    horizon: float = 1.0,
    target_position: float = 1.0,
    control_limit: float = 10.0,
) -> TrajectoryOptimizationResult:
    """只优化控制序列，每次前向积分后用终端约束校正射击方向。"""

    dt, transition, control_matrix = _problem_matrices(intervals, horizon)
    if control_limit <= 0.0:
        raise ValueError("control_limit 必须为正数")
    initial = _initial_control(intervals, horizon, target_position)

    def objective(control: np.ndarray) -> float:
        return float(
            dt
            * (
                0.5 * control[0] ** 2
                + np.sum(np.square(control[1:-1]))
                + 0.5 * control[-1] ** 2
            )
        )

    def terminal_constraint(control: np.ndarray) -> np.ndarray:
        return _rollout(control, transition, control_matrix)[-1] - np.array([target_position, 0.0])

    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=[(-control_limit, control_limit)] * (intervals + 1),
        constraints={"type": "eq", "fun": terminal_constraint},
        options={"ftol": 1e-12, "maxiter": 500},
    )
    control = np.asarray(result.x, dtype=float)
    state = _rollout(control, transition, control_matrix)
    return _summarize_trajectory(
        method="single_shooting",
        optimization_result=result,
        state=state,
        control=control,
        horizon=horizon,
        target_position=target_position,
        transition=transition,
        control_matrix=control_matrix,
    )
