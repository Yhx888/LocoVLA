"""经典控制章节使用的最小数学工具。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ScalarOptimalControlSolution:
    method: str
    time: np.ndarray
    state: np.ndarray
    control: np.ndarray
    cost: float
    equation_residual: float
    stationarity_residual: float = 0.0
    costate_residual: float = 0.0
    transversality_residual: float = 0.0


def _validate_scalar_problem(initial_state: float, horizon: float, terminal_weight: float) -> None:
    if not np.isfinite(initial_state):
        raise ValueError("initial_state 必须有限")
    if not np.isfinite(horizon) or horizon <= 0.0:
        raise ValueError("horizon 必须为正数")
    if not np.isfinite(terminal_weight) or terminal_weight <= 0.0:
        raise ValueError("terminal_weight 必须为正数")


def _scalar_time_and_cost(
    horizon: float,
    terminal_weight: float,
    control: np.ndarray,
    state: np.ndarray,
) -> tuple[np.ndarray, float]:
    time = np.linspace(0.0, horizon, control.size)
    running_cost = float(np.trapezoid(0.5 * np.square(control), time))
    terminal_cost = 0.5 * terminal_weight * float(state[-1] ** 2)
    return time, running_cost + terminal_cost


def solve_scalar_euler_lagrange(
    *,
    initial_state: float,
    horizon: float,
    terminal_weight: float,
    samples: int = 201,
) -> ScalarOptimalControlSolution:
    """求解 x_dot=u、积分能量代价与软终端代价的变分法算例。"""

    _validate_scalar_problem(initial_state, horizon, terminal_weight)
    if samples < 3:
        raise ValueError("samples 至少为 3")
    time = np.linspace(0.0, horizon, samples)
    slope = -terminal_weight * initial_state / (1.0 + terminal_weight * horizon)
    state = initial_state + slope * time
    control = np.full_like(time, slope)
    _, cost = _scalar_time_and_cost(horizon, terminal_weight, control, state)
    equation_residual = float(np.max(np.abs(np.gradient(control, time))))
    transversality = abs(float(control[-1] + terminal_weight * state[-1]))
    return ScalarOptimalControlSolution(
        method="euler_lagrange",
        time=time,
        state=state,
        control=control,
        cost=cost,
        equation_residual=equation_residual,
        transversality_residual=transversality,
    )


def solve_scalar_hjb(
    *,
    initial_state: float,
    horizon: float,
    terminal_weight: float,
    samples: int = 201,
) -> ScalarOptimalControlSolution:
    """用二次值函数求解同一标量问题并验证 HJB PDE。"""

    _validate_scalar_problem(initial_state, horizon, terminal_weight)
    if samples < 3:
        raise ValueError("samples 至少为 3")
    time = np.linspace(0.0, horizon, samples)
    denominator = 1.0 + terminal_weight * (horizon - time)
    value_coefficient = terminal_weight / denominator
    state = initial_state * denominator / (1.0 + terminal_weight * horizon)
    control = -value_coefficient * state
    value_time_derivative = 0.5 * np.square(value_coefficient * state)
    minimized_hamiltonian = 0.5 * np.square(control) + value_coefficient * state * control
    pde_residual = float(np.max(np.abs(value_time_derivative + minimized_hamiltonian)))
    _, cost = _scalar_time_and_cost(horizon, terminal_weight, control, state)
    return ScalarOptimalControlSolution(
        method="hjb",
        time=time,
        state=state,
        control=control,
        cost=cost,
        equation_residual=pde_residual,
    )


def solve_scalar_pontryagin(
    *,
    initial_state: float,
    horizon: float,
    terminal_weight: float,
    samples: int = 201,
) -> ScalarOptimalControlSolution:
    """用协态与驻值条件求解同一标量问题。"""

    _validate_scalar_problem(initial_state, horizon, terminal_weight)
    if samples < 3:
        raise ValueError("samples 至少为 3")
    time = np.linspace(0.0, horizon, samples)
    costate = np.full_like(
        time,
        terminal_weight * initial_state / (1.0 + terminal_weight * horizon),
    )
    control = -costate
    state = initial_state + control * time
    stationarity = float(np.max(np.abs(control + costate)))
    costate_residual = float(np.max(np.abs(np.gradient(costate, time))))
    transversality = abs(float(costate[-1] - terminal_weight * state[-1]))
    _, cost = _scalar_time_and_cost(horizon, terminal_weight, control, state)
    return ScalarOptimalControlSolution(
        method="pontryagin",
        time=time,
        state=state,
        control=control,
        cost=cost,
        equation_residual=max(stationarity, costate_residual, transversality),
        stationarity_residual=stationarity,
        costate_residual=costate_residual,
        transversality_residual=transversality,
    )


def inverted_pendulum_acceleration(
    angle_rad: float | np.ndarray,
    wheel_torque_nm: float | np.ndarray,
    *,
    mass_kg: float = 10.0,
    com_length_m: float = 0.5,
    gravity_m_s2: float = 9.81,
) -> float | np.ndarray:
    inertia = mass_kg * com_length_m**2
    return (
        mass_kg * gravity_m_s2 * com_length_m * np.sin(angle_rad) - wheel_torque_nm
    ) / inertia


def linearized_inverted_pendulum_acceleration(
    angle_rad: float | np.ndarray,
    wheel_torque_nm: float | np.ndarray,
    *,
    mass_kg: float = 10.0,
    com_length_m: float = 0.5,
    gravity_m_s2: float = 9.81,
) -> float | np.ndarray:
    inertia = mass_kg * com_length_m**2
    return (
        mass_kg * gravity_m_s2 * com_length_m * np.asarray(angle_rad) - wheel_torque_nm
    ) / inertia


def second_order_poles(natural_frequency_rad_s: float, damping_ratio: float) -> np.ndarray:
    coefficients = [
        1.0,
        2.0 * float(damping_ratio) * float(natural_frequency_rad_s),
        float(natural_frequency_rad_s) ** 2,
    ]
    return np.roots(coefficients)


def simulate_second_order(
    natural_frequency_rad_s: float,
    damping_ratio: float,
    *,
    duration_s: float = 4.0,
    timestep_s: float = 0.002,
    initial_position: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    time = np.arange(0.0, duration_s + timestep_s, timestep_s)
    position = np.empty_like(time)
    velocity = 0.0
    position[0] = float(initial_position)
    for index in range(1, time.size):
        acceleration = (
            -2.0 * damping_ratio * natural_frequency_rad_s * velocity
            - natural_frequency_rad_s**2 * position[index - 1]
        )
        velocity += timestep_s * acceleration
        position[index] = position[index - 1] + timestep_s * velocity
    return time, position


def second_order_frequency_magnitude(
    frequency_rad_s: np.ndarray,
    natural_frequency_rad_s: float,
    damping_ratio: float,
) -> np.ndarray:
    omega = np.asarray(frequency_rad_s, dtype=float)
    numerator = natural_frequency_rad_s**2
    denominator = np.sqrt(
        (natural_frequency_rad_s**2 - omega**2) ** 2
        + (2.0 * damping_ratio * natural_frequency_rad_s * omega) ** 2
    )
    return numerator / denominator


def wheel_pendulum_state_space(
    *,
    mass_kg: float = 10.0,
    com_length_m: float = 0.5,
    gravity_m_s2: float = 9.81,
) -> tuple[np.ndarray, np.ndarray]:
    """构造"力作用于基座"简化轮摆模型的连续状态空间矩阵。

    本函数对应简化教学模型，与 controllers/mpc.py 的 upkie_balance_ss_matrices()
    在以下四个维度均不兼容，调用方需自行做状态置换：

    1. 状态顺序：本函数为 ``[x, x_dot, pitch, pitch_dot]``，
       mpc.py 为 ``[pitch, pitch_rate, x, x_dot]``（前两维与后两维互换）。
    2. 物理参数：本函数默认 m=10 kg、l=0.5 m（教学示例值），
       mpc.py 默认 m=5.4 kg、l=0.28 m（更接近 Upkie 实际参数）。
    3. 阻尼：本函数无阻尼（A 矩阵对角为 0），mpc.py 加入 -0.05 角速度/线速度阻尼。
    4. 输入语义：本函数 B 矩阵输入是"作用于基座的力"（N），
       mpc.py B 矩阵输入是"轮端力矩"（N*m，需除以轮半径 r 才得到力）。
    """
    a = np.array(
        [
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, gravity_m_s2 / com_length_m, 0.0],
        ],
        dtype=float,
    )
    b = np.array(
        [[0.0], [1.0 / mass_kg], [0.0], [-1.0 / (mass_kg * com_length_m)]],
        dtype=float,
    )
    return a, b


def controllability_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    blocks = [b]
    for power in range(1, a.shape[0]):
        blocks.append(np.linalg.matrix_power(a, power) @ b)
    return np.concatenate(blocks, axis=1)


def observability_matrix(a: np.ndarray, c: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    c = np.asarray(c, dtype=float)
    blocks = [c]
    for power in range(1, a.shape[0]):
        blocks.append(c @ np.linalg.matrix_power(a, power))
    return np.concatenate(blocks, axis=0)
