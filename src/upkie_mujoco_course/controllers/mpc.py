"""有限时域线性模型预测控制器。

支持两种维度：
- 一维标量 MPC（保留 24 关早期测试兼容）
- 四状态 Upkie 平衡 MPC（pitch, pitch_rate, position, velocity → wheel torque）

QP 用 scipy L-BFGS-B（无约束）或 SLSQP（含线性/边界约束）求解，
求解统计通过 ``last_solve_stats`` 暴露给闭环脚本。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.optimize import minimize


@dataclass
class MPCSolveStats:
    """记录一次 MPC 求解的求解器输出，用于闭环脚本聚合。"""

    success: bool
    iterations: int
    solve_time_ms: float
    objective: float
    constraint_hit: bool
    message: str
    prediction_max_violation: float
    constraints_satisfied: bool


class MPCSolveError(RuntimeError):
    """MPC 求解器失败或返回违反硬约束的轨迹。"""


class LinearMPC:
    """在线求解带输入上下界的线性 MPC。

    支持标量或多维状态；``control_limit`` 为对每维控制的绝对值上界；可选
    ``state_lower`` / ``state_upper`` 为预测状态的软/硬约束（默认无）。
    """

    def __init__(
        self,
        system_matrix: np.ndarray,
        input_matrix: np.ndarray,
        state_cost: np.ndarray,
        input_cost: np.ndarray,
        horizon: int,
        control_limit: float,
        *,
        terminal_cost: np.ndarray | None = None,
        state_lower: np.ndarray | None = None,
        state_upper: np.ndarray | None = None,
    ):
        self.a = np.asarray(system_matrix, dtype=float)
        self.b = np.asarray(input_matrix, dtype=float)
        self.q = np.asarray(state_cost, dtype=float)
        self.r = np.asarray(input_cost, dtype=float)
        self.qf = np.asarray(terminal_cost if terminal_cost is not None else state_cost, dtype=float)
        self.horizon = int(horizon)
        self.control_limit = float(control_limit)
        if self.horizon < 1 or self.control_limit <= 0.0:
            raise ValueError("预测步数和控制限幅必须为正数")
        self.state_lower = None if state_lower is None else np.asarray(state_lower, dtype=float).reshape(-1)
        self.state_upper = None if state_upper is None else np.asarray(state_upper, dtype=float).reshape(-1)
        self.last_solve_stats: MPCSolveStats | None = None
        self._warm_start = np.zeros(self.horizon * self.b.shape[1], dtype=float)
        self._prediction_state_matrix, self._prediction_control_matrix = (
            self._build_prediction_matrices()
        )

    def _build_prediction_matrices(self) -> tuple[np.ndarray, np.ndarray]:
        """构造 X = F x0 + G U 的有限时域预测矩阵。"""

        state_size = self.a.shape[0]
        input_size = self.b.shape[1]
        state_matrix = np.zeros((self.horizon * state_size, state_size), dtype=float)
        control_matrix = np.zeros(
            (self.horizon * state_size, self.horizon * input_size),
            dtype=float,
        )
        for step in range(self.horizon):
            row = slice(step * state_size, (step + 1) * state_size)
            state_matrix[row] = np.linalg.matrix_power(self.a, step + 1)
            for control_step in range(step + 1):
                column = slice(
                    control_step * input_size,
                    (control_step + 1) * input_size,
                )
                control_matrix[row, column] = (
                    np.linalg.matrix_power(self.a, step - control_step) @ self.b
                )
        return state_matrix, control_matrix

    @property
    def has_state_constraints(self) -> bool:
        return bool(
            (self.state_lower is not None and np.any(np.isfinite(self.state_lower)))
            or (self.state_upper is not None and np.any(np.isfinite(self.state_upper)))
        )

    def _predict_states(self, state: np.ndarray, controls: np.ndarray) -> np.ndarray:
        """滚动展开 horizon 步预测状态，返回 shape=(horizon+1, n)。"""

        trajectory = np.empty((controls.shape[0] + 1, state.size), dtype=float)
        trajectory[0] = state
        current = state
        for index, control in enumerate(controls):
            current = self.a @ current + self.b @ control
            trajectory[index + 1] = current
        return trajectory

    def _compute_objective_and_gradient(
        self, state: np.ndarray, reference: np.ndarray, flat_controls: np.ndarray
    ) -> tuple[float, np.ndarray]:
        """同时计算目标函数值和解析梯度（伴随法/costate method）。

        前向：展开轨迹 x_0, ..., x_N
        后向：递推代价梯度 lambda_N = 2 Qf e_N, lambda_k = 2 Q e_k + A' lambda_{k+1}
        梯度：dJ/du_j = 2 R u_j + B' lambda_{j+1}

        比 scipy 数值差分精度高 ~8 个数量级，是 MPC 与 LQR 数值对齐的关键。
        """
        input_size = self.b.shape[1]
        controls = flat_controls.reshape(self.horizon, input_size)
        trajectory = self._predict_states(state, controls)

        # 目标函数
        total = 0.0
        for step_index in range(self.horizon):
            error = trajectory[step_index] - reference
            control = controls[step_index]
            total += float(error @ self.q @ error + control @ self.r @ control)
        terminal_error = trajectory[-1] - reference
        total += float(terminal_error @ self.qf @ terminal_error)

        # 伴随法梯度（反向递推）
        grad = np.empty_like(flat_controls)
        lam = 2.0 * self.qf @ terminal_error  # lambda_N
        for j in range(self.horizon - 1, -1, -1):
            # dJ/du_j = 2 R u_j + B' lambda_{j+1}
            grad[j * input_size : (j + 1) * input_size] = (
                2.0 * self.r @ controls[j] + (self.b.T @ lam).reshape(-1)
            )
            # lambda_j = 2 Q e_j + A' lambda_{j+1}
            error_j = trajectory[j] - reference
            lam = 2.0 * self.q @ error_j + self.a.T @ lam

        return total, grad

    def _max_state_constraint_violation(self, trajectory: np.ndarray) -> float:
        violation = 0.0
        predicted = trajectory[1:]
        if self.state_upper is not None:
            finite = np.isfinite(self.state_upper)
            if np.any(finite):
                violation = max(
                    violation,
                    float(np.max(predicted[:, finite] - self.state_upper[finite])),
                )
        if self.state_lower is not None:
            finite = np.isfinite(self.state_lower)
            if np.any(finite):
                violation = max(
                    violation,
                    float(np.max(self.state_lower[finite] - predicted[:, finite])),
                )
        return max(0.0, violation)

    def _record_failure(
        self,
        result: Any,
        elapsed_ms: float,
        message: str,
        prediction_max_violation: float,
    ) -> None:
        self.last_solve_stats = MPCSolveStats(
            success=False,
            iterations=int(getattr(result, "nit", 0)),
            solve_time_ms=float(elapsed_ms),
            objective=float(getattr(result, "fun", float("nan"))),
            constraint_hit=bool(self.has_state_constraints),
            message=message,
            prediction_max_violation=float(prediction_max_violation),
            constraints_satisfied=False,
        )

    def compute(self, state: np.ndarray, reference: np.ndarray | None = None) -> np.ndarray:
        state = np.asarray(state, dtype=float).reshape(-1)
        reference = np.zeros_like(state) if reference is None else np.asarray(reference, dtype=float).reshape(-1)
        if reference.shape != state.shape:
            raise ValueError("参考轨迹维度必须与状态维度一致")
        input_size = self.b.shape[1]

        def objective(flat_controls: np.ndarray) -> float:
            controls = flat_controls.reshape(self.horizon, input_size)
            trajectory = self._predict_states(state, controls)
            total = 0.0
            for step_index in range(self.horizon):
                error = trajectory[step_index] - reference
                control = controls[step_index]
                total += float(error @ self.q @ error + control @ self.r @ control)
            terminal_error = trajectory[-1] - reference
            total += float(terminal_error @ self.qf @ terminal_error)
            return total

        def objective_and_gradient(flat_controls: np.ndarray) -> tuple[float, np.ndarray]:
            return self._compute_objective_and_gradient(state, reference, flat_controls)

        initial = self._warm_start.copy()
        bounds = [(-self.control_limit, self.control_limit)] * initial.size

        start = time.perf_counter()
        constraint_hit = False
        if self.has_state_constraints:
            constraints: list[dict[str, Any]] = []
            upper_mask = (
                np.isfinite(self.state_upper)
                if self.state_upper is not None
                else np.zeros(state.size, dtype=bool)
            )
            lower_mask = (
                np.isfinite(self.state_lower)
                if self.state_lower is not None
                else np.zeros(state.size, dtype=bool)
            )
            predicted_without_control = self._prediction_state_matrix @ state
            values: list[np.ndarray] = []
            jacobians: list[np.ndarray] = []
            if np.any(upper_mask):
                upper_rows = np.tile(upper_mask, self.horizon)
                upper_bounds = np.tile(self.state_upper[upper_mask], self.horizon)
                values.append(upper_bounds - predicted_without_control[upper_rows])
                jacobians.append(-self._prediction_control_matrix[upper_rows])
            if np.any(lower_mask):
                lower_rows = np.tile(lower_mask, self.horizon)
                lower_bounds = np.tile(self.state_lower[lower_mask], self.horizon)
                values.append(predicted_without_control[lower_rows] - lower_bounds)
                jacobians.append(self._prediction_control_matrix[lower_rows])
            constraint_offset = np.concatenate(values)
            constraint_jacobian = np.vstack(jacobians)

            def state_constraint(flat_controls: np.ndarray) -> np.ndarray:
                return constraint_offset + constraint_jacobian @ flat_controls

            constraints.append(
                {
                    "type": "ineq",
                    "fun": state_constraint,
                    "jac": lambda _controls: constraint_jacobian,
                }
            )
            result = minimize(
                objective_and_gradient,
                initial,
                method="SLSQP",
                jac=True,
                bounds=bounds,
                constraints=constraints,
                options={"ftol": 1e-12, "maxiter": 150},
            )
            controls = result.x.reshape(self.horizon, input_size)
            trajectory = self._predict_states(state, controls)
            if self.state_upper is not None and np.any(trajectory[1:] - self.state_upper > -1e-6):
                constraint_hit = True
            if self.state_lower is not None and np.any(self.state_lower - trajectory[1:] > -1e-6):
                constraint_hit = True
        else:
            result = minimize(
                objective_and_gradient, initial, method="L-BFGS-B", jac=True, bounds=bounds,
                options={"ftol": 1e-15, "maxiter": 500},
            )
        elapsed_ms = (time.perf_counter() - start) * 1_000.0
        prediction_max_violation = (
            self._max_state_constraint_violation(trajectory)
            if self.has_state_constraints
            else 0.0
        )
        if not result.success:
            message = str(getattr(result, "message", "未知求解器错误"))
            self._record_failure(
                result,
                elapsed_ms,
                message,
                prediction_max_violation,
            )
            raise MPCSolveError(f"MPC 求解失败: {message}")
        if self.has_state_constraints:
            if prediction_max_violation > 1e-6:
                message = f"预测状态约束违反 {prediction_max_violation:.3e}"
                self._record_failure(
                    result,
                    elapsed_ms,
                    message,
                    prediction_max_violation,
                )
                raise MPCSolveError(message)
        control = np.clip(result.x[:input_size], -self.control_limit, self.control_limit)
        solved_controls = result.x.reshape(self.horizon, input_size)
        shifted_controls = np.empty_like(solved_controls)
        if self.horizon > 1:
            shifted_controls[:-1] = solved_controls[1:]
        shifted_controls[-1] = solved_controls[-1]
        self._warm_start = np.clip(
            shifted_controls.reshape(-1),
            -self.control_limit,
            self.control_limit,
        )
        self.last_solve_stats = MPCSolveStats(
            success=bool(result.success),
            iterations=int(getattr(result, "nit", 0)),
            solve_time_ms=float(elapsed_ms),
            objective=float(result.fun),
            constraint_hit=bool(constraint_hit),
            message=str(getattr(result, "message", "")),
            prediction_max_violation=float(prediction_max_violation),
            constraints_satisfied=bool(prediction_max_violation <= 1e-6),
        )
        return np.asarray(control, dtype=float)


def upkie_balance_ss_matrices(
    *,
    dt: float = 0.02,
    gravity: float = 9.81,
    pendulum_length: float = 0.28,
    mass: float = 5.4,
    wheel_radius: float = 0.06,
) -> tuple[np.ndarray, np.ndarray]:
    """构造 4 状态离散化线性倒立摆 + 轮子模型 (pitch, pitch_rate, x, x_dot)。

    连续动力学：
      x_ddot ≈ - g * pitch + tau / (m * r)
      theta_ddot ≈ (g / L) * pitch - tau / (m * L * r)

    使用一阶欧拉离散化。这里没有直接采用 MuJoCo 全阶动力学（那需要辨识），
    但足以支撑 LQR/MPC 对照演示和 24 关教学。

    与 classical_control/math_tools.py 的 wheel_pendulum_state_space() 不兼容：
      - 状态顺序：本函数为 [pitch, pitch_rate, x, x_dot]，
        wheel_pendulum_state_space() 为 [x, x_dot, pitch, pitch_dot]。
        调用方若同时使用两者，需自行做状态置换（前两维与后两维互换）。
      - 物理参数：本函数默认 m=5.4 kg、l=0.28 m（接近 Upkie 实际参数），
        wheel_pendulum_state_space() 默认 m=10 kg、l=0.5 m（教学示例值）。
      - 阻尼：本函数在 A 矩阵对角加入 -0.05 阻尼，
        wheel_pendulum_state_space() 无阻尼。
      - 输入语义：本函数 B 矩阵输入是"轮端力矩"（N*m），
        wheel_pendulum_state_space() 是"作用于基座的力"（N）。
    """

    # 加入极小的角速度/线速度阻尼，避免离散 A 出现恰好位于单位圆上的
    # 极点，从而使 (A, B) 在 DARE 求解时数值稳定。物理上这对应仿真
    # 中的等效摩擦项；对教学模型足够小以不影响俯仰失稳趋势。
    a_c = np.array(
        [
            [0.0, 1.0, 0.0, 0.0],
            [gravity / pendulum_length, -0.05, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [-gravity, 0.0, 0.0, -0.05],
        ],
        dtype=float,
    )
    b_c = np.array(
        [
            [0.0],
            [-1.0 / (mass * pendulum_length * wheel_radius)],
            [0.0],
            [1.0 / (mass * wheel_radius)],
        ],
        dtype=float,
    )
    a_d = np.eye(4) + dt * a_c
    b_d = dt * b_c
    return a_d, b_d


def run_mujoco_mpc_closed_loop(
    *,
    steps: int = 200,
    controller: LinearMPC | None = None,
    pitch_limit_rad: float = 0.35,
) -> dict[str, float | int | bool | str]:
    """在真实 MuJoCo runner 中执行 MPC 并返回闭环指标。"""

    from upkie_mujoco_course.sim.runner import SimulationRunner

    if steps < 1:
        raise ValueError("闭环步数必须为正数")
    if controller is not None and not controller.has_state_constraints:
        raise ValueError("MuJoCo MPC 闭环证据要求有限的预测状态约束")
    runner = SimulationRunner()
    dt = float(runner.model.opt.timestep * runner.spec.frame_skip)
    if controller is None:
        a, b = upkie_balance_ss_matrices(dt=dt)
        controller = LinearMPC(
            a,
            b,
            np.diag([200.0, 1.0, 0.2, 0.2]),
            np.array([[50.0]]),
            horizon=10,
            control_limit=1.0,
            state_lower=np.array([-pitch_limit_rad, -np.inf, -np.inf, -np.inf]),
            state_upper=np.array([pitch_limit_rad, np.inf, np.inf, np.inf]),
        )

    pitch_errors: list[float] = []
    solve_times_ms: list[float] = []
    torques: list[float] = []
    constraint_hits = 0
    max_state_constraint_violation = 0.0
    prediction_max_state_constraint_violation = 0.0
    prediction_constraints_satisfied = True
    solve_success = True
    successful_solves = 0
    runner.reset("stand")
    try:
        for _ in range(steps):
            state = runner.posture_state()
            mpc_state = np.array(
                [
                    state["pitch_error"],
                    state["pitch_rate"],
                    state["x_position"],
                    state["forward_velocity"],
                ],
                dtype=float,
            )
            try:
                common_torque = float(controller.compute(mpc_state)[0])
            except MPCSolveError:
                solve_success = False
                break
            successful_solves += 1

            action = np.zeros(runner.model.nu, dtype=float)
            stand = runner.spec.default_pose["stand"]
            for actuator in runner.spec.position_actuators:
                action[runner.actuator_ids[actuator.name]] = stand[actuator.joint]
            for actuator, direction in zip(
                runner.spec.torque_actuators,
                runner.spec.wheel_directions,
            ):
                action[runner.actuator_ids[actuator.name]] = direction * common_torque
            runner.step(action)

            state = runner.posture_state()
            pitch_error = float(state["pitch_error"])
            pitch_errors.append(pitch_error)
            torques.append(abs(common_torque))
            max_state_constraint_violation = max(
                max_state_constraint_violation,
                max(0.0, abs(pitch_error) - pitch_limit_rad),
            )
            stats = controller.last_solve_stats
            if stats is not None:
                solve_times_ms.append(stats.solve_time_ms)
                constraint_hits += int(stats.constraint_hit)
                prediction_max_state_constraint_violation = max(
                    prediction_max_state_constraint_violation,
                    stats.prediction_max_violation,
                )
                prediction_constraints_satisfied &= stats.constraints_satisfied
            if not bool(state["both_wheels_contact"]) or abs(pitch_error) > pitch_limit_rad:
                break
    finally:
        runner.close()

    executed = len(pitch_errors)
    survived = executed == steps and solve_success
    actual_constraints_satisfied = max_state_constraint_violation <= 1e-6
    return {
        "backend": "mujoco",
        "steps_requested": int(steps),
        "steps_executed": int(executed),
        "pitch_rmse_rad": float(np.sqrt(np.mean(np.square(pitch_errors)))) if pitch_errors else float("inf"),
        "survival_rate": float(executed / steps),
        "survived": bool(survived),
        "max_wheel_torque_nm": float(max(torques, default=0.0)),
        "constraint_hit_rate": float(constraint_hits / executed) if executed else 0.0,
        "max_state_constraint_violation": float(max_state_constraint_violation),
        "actual_max_state_constraint_violation": float(max_state_constraint_violation),
        "prediction_max_state_constraint_violation": float(
            prediction_max_state_constraint_violation
        ),
        "actual_constraints_satisfied": bool(actual_constraints_satisfied),
        "prediction_constraints_satisfied": bool(prediction_constraints_satisfied),
        "constraints_satisfied": bool(
            actual_constraints_satisfied and prediction_constraints_satisfied
        ),
        "solve_time_ms_mean": float(np.mean(solve_times_ms)) if solve_times_ms else 0.0,
        "solve_success_ratio": float(successful_solves / steps),
        "solve_success": bool(solve_success),
    }
