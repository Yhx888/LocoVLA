"""测试 MPC 控制器实验室（classical_19 / mpc 章节）。

覆盖场景：
- MPC 脚本入口能正常执行
- 输出结果文件结构与契约
- 与 LQR 的对比报告生成
"""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.linalg import solve_discrete_are

import upkie_mujoco_course.controllers.mpc as mpc_module
from upkie_mujoco_course.controllers.mpc import LinearMPC, upkie_balance_ss_matrices


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _dare_lqr_gain(a: np.ndarray, b: np.ndarray, q: np.ndarray, r: np.ndarray) -> np.ndarray:
    """通过离散代数 Riccati 方程计算无限时域 LQR 最优增益 K。"""
    p = solve_discrete_are(a, b, q, r)
    return np.linalg.solve(b.T @ p @ b + r, b.T @ p @ a)


# ---------------------------------------------------------------------------
# 基础标量测试（保留兼容性）
# ---------------------------------------------------------------------------

def test_linear_mpc_drives_scalar_state_toward_zero_within_limits():
    controller = LinearMPC(
        system_matrix=np.array([[1.0]]),
        input_matrix=np.array([[1.0]]),
        state_cost=np.array([[1.0]]),
        input_cost=np.array([[0.1]]),
        horizon=5,
        control_limit=0.25,
    )
    action = controller.compute(np.array([1.0]))
    assert action.shape == (1,)
    assert -0.25 <= action[0] < 0.0


def test_trajectory_optimization_script_runs_both_methods(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_trajectory_optimization_lab.py",
            "--output-root",
            str(tmp_path),
            "--source-root",
            str(tmp_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads((tmp_path / "results" / "trajectory_24.json").read_text(encoding="utf-8"))
    assert result["passed"] is True


# ---------------------------------------------------------------------------
# 任务 3 新增测试
# ---------------------------------------------------------------------------

def test_mpc_matches_lqr_when_no_constraints():
    """无约束 + 长时域时 MPC 首步动作与 LQR 差 <= 1e-3。

    原理：当控制限幅足够大（不构成有效约束）、预测时域足够长、
    且终端代价取 DARE 的解 P 时，有限时域 MPC 的首步最优控制
    精确等价于无限时域 LQR 最优控制。

    使用完全可控的双积分器系统（而非 Upkie 线性化模型——其可控性秩亏
    导致 DARE 数值不稳定），验证 MPC 算法本身的正确性。
    """
    dt = 0.05
    # 双积分器：x = [position, velocity], u = force
    # 连续: x_dot = [v; u/m]，离散化后:
    a = np.array([[1.0, dt], [0.0, 1.0]])
    b = np.array([[0.5 * dt * dt], [dt]])
    q = np.diag([10.0, 1.0])
    r = np.array([[1.0]])

    # DARE 求解 + LQR 增益
    p = solve_discrete_are(a, b, q, r)
    k = np.linalg.solve(b.T @ p @ b + r, b.T @ p @ a)

    # 验证 DARE 残差极小（系统完全可控，DARE 应收敛到高精度）
    dare_residual = a.T @ p @ a - p - (a.T @ p @ b) @ np.linalg.solve(b.T @ p @ b + r, b.T @ p @ a) + q
    assert np.max(np.abs(dare_residual)) < 1e-8, "DARE 残差过大"

    # 长时域、宽限幅 MPC，终端代价取 P
    mpc = LinearMPC(
        a, b, q, r, horizon=50, control_limit=1000.0,
        terminal_cost=p,
    )

    # 多组随机初始状态测试
    rng = np.random.default_rng(42)
    for _ in range(10):
        state = rng.uniform(-1.0, 1.0, size=2)
        u_lqr = (-k @ state).reshape(-1)
        u_mpc = mpc.compute(state)
        np.testing.assert_allclose(
            u_mpc, u_lqr, atol=1e-3,
            err_msg=f"MPC 首步动作 {u_mpc} 与 LQR {u_lqr} 差超过 1e-3"
        )


def test_mpc_respects_wheel_torque_bounds():
    """即使误差极大，MPC 输出恒在 [-1, 1] N*m 范围内。"""
    a, b = upkie_balance_ss_matrices(dt=0.02)
    q = np.diag([200.0, 5.0, 5.0, 5.0])
    r = np.array([[10.0]])
    control_limit = 1.0

    mpc = LinearMPC(a, b, q, r, horizon=10, control_limit=control_limit)

    # 测试多组极端状态
    extreme_states = [
        np.array([1.0, 5.0, 2.0, 3.0]),      # 大俯仰 + 大角速度
        np.array([-0.5, -3.0, -1.0, -2.0]),   # 反向大误差
        np.array([0.3, 0.0, 0.0, 0.0]),        # 纯俯仰偏移
        np.array([0.0, 0.0, 5.0, 10.0]),       # 纯位置/速度偏移
    ]
    for state in extreme_states:
        action = mpc.compute(state)
        assert action.shape == (1,), f"动作形状应为 (1,)，实际为 {action.shape}"
        assert -control_limit - 1e-9 <= action[0] <= control_limit + 1e-9, (
            f"状态 {state} 下 MPC 输出 {action[0]} 超出 [-{control_limit}, {control_limit}]"
        )


def test_mpc_rejects_infeasible_state_constraint_without_unconstrained_fallback():
    controller = LinearMPC(
        system_matrix=np.array([[1.0]]),
        input_matrix=np.array([[1.0]]),
        state_cost=np.array([[1.0]]),
        input_cost=np.array([[0.1]]),
        horizon=2,
        control_limit=0.1,
        state_upper=np.array([0.0]),
    )

    with pytest.raises(RuntimeError, match="MPC 求解失败|状态约束"):
        controller.compute(np.array([1.0]))

    assert controller.last_solve_stats is not None
    assert controller.last_solve_stats.success is False


def test_mpc_ignores_infinite_components_of_state_bounds():
    controller = LinearMPC(
        system_matrix=np.eye(2),
        input_matrix=np.array([[1.0], [0.0]]),
        state_cost=np.eye(2),
        input_cost=np.array([[0.1]]),
        horizon=2,
        control_limit=0.5,
        state_lower=np.array([-0.5, -np.inf]),
        state_upper=np.array([0.5, np.inf]),
    )

    action = controller.compute(np.array([0.1, 0.0]))

    assert action.shape == (1,)
    assert controller.last_solve_stats is not None
    assert controller.last_solve_stats.success is True
    assert controller.last_solve_stats.prediction_max_violation <= 1e-6
    assert controller.last_solve_stats.constraints_satisfied is True


def test_constrained_mpc_reuses_shifted_previous_solution(monkeypatch):
    initial_guesses: list[np.ndarray] = []

    def fake_minimize(_fun, initial, **_kwargs):
        initial_guesses.append(np.asarray(initial, dtype=float).copy())
        solution = np.array([0.1, 0.2, 0.3])
        return SimpleNamespace(
            x=solution,
            success=True,
            nit=1,
            fun=0.0,
            message="ok",
        )

    monkeypatch.setattr(mpc_module, "minimize", fake_minimize)
    controller = LinearMPC(
        system_matrix=np.array([[1.0]]),
        input_matrix=np.array([[1.0]]),
        state_cost=np.array([[1.0]]),
        input_cost=np.array([[0.1]]),
        horizon=3,
        control_limit=1.0,
        state_lower=np.array([-10.0]),
        state_upper=np.array([10.0]),
    )

    controller.compute(np.array([0.0]))
    controller.compute(np.array([0.0]))

    assert np.allclose(initial_guesses[0], np.zeros(3))
    assert np.allclose(initial_guesses[1], np.array([0.2, 0.3, 0.3]))


def test_constrained_mpc_supplies_analytic_constraint_jacobian(monkeypatch):
    captured_constraints = None

    def fake_minimize(_fun, initial, **kwargs):
        nonlocal captured_constraints
        captured_constraints = kwargs["constraints"]
        return SimpleNamespace(
            x=np.zeros_like(initial),
            success=True,
            nit=1,
            fun=0.0,
            message="ok",
        )

    monkeypatch.setattr(mpc_module, "minimize", fake_minimize)
    controller = LinearMPC(
        system_matrix=np.array([[1.0]]),
        input_matrix=np.array([[1.0]]),
        state_cost=np.array([[1.0]]),
        input_cost=np.array([[0.1]]),
        horizon=3,
        control_limit=1.0,
        state_lower=np.array([-1.0]),
        state_upper=np.array([1.0]),
    )

    controller.compute(np.array([0.0]))

    assert isinstance(captured_constraints, list)
    assert len(captured_constraints) == 1
    assert callable(captured_constraints[0]["jac"])


def test_mujoco_mpc_closed_loop_steps_real_runner_and_reports_metrics():
    run_closed_loop = getattr(mpc_module, "run_mujoco_mpc_closed_loop", None)
    assert callable(run_closed_loop), "缺少真实 MuJoCo MPC 闭环接口"

    report = run_closed_loop(steps=10)

    assert report["backend"] == "mujoco"
    assert report["steps_executed"] == 10
    assert report["pitch_rmse_rad"] >= 0.0
    assert 0.0 <= report["survival_rate"] <= 1.0
    assert report["max_wheel_torque_nm"] <= 1.0 + 1e-9
    assert report["max_state_constraint_violation"] >= 0.0
    assert report["solve_time_ms_mean"] >= 0.0
    assert report["solve_success_ratio"] == 1.0
    assert report["survived"] is True
    assert report["constraints_satisfied"] is True
    assert report["prediction_constraints_satisfied"] is True
    assert report["actual_constraints_satisfied"] is True
    assert report["prediction_max_state_constraint_violation"] <= 1e-6


def test_mujoco_mpc_closed_loop_rejects_controller_without_state_constraints():
    a, b = upkie_balance_ss_matrices(dt=0.01)
    controller = LinearMPC(
        a,
        b,
        np.eye(4),
        np.array([[1.0]]),
        horizon=3,
        control_limit=1.0,
    )

    with pytest.raises(ValueError, match="预测状态约束"):
        mpc_module.run_mujoco_mpc_closed_loop(steps=1, controller=controller)


def test_fixed_mpc_result_script_uses_mujoco_as_required_backend():
    source = Path("scripts/run_mpc_balance_compare.py").read_text(encoding="utf-8")
    assert "run_mujoco_mpc_closed_loop(" in source
    for metric in (
        "mujoco_solve_success_ratio",
        "mujoco_survived",
        "mujoco_constraints_satisfied",
        "mujoco_prediction_constraints_satisfied",
        "mujoco_actual_constraints_satisfied",
        "mujoco_steps_executed",
        "mujoco_pitch_rmse",
        "mujoco_max_torque",
    ):
        assert metric in source


def test_mpc_balance_lab_writes_real_result_log_plot_and_portfolio(tmp_path):
    """跑 lab 入口，校验五件套齐全：JSON、PNG、LOG、报告 MD、passed=true。"""
    project_root = Path(__file__).resolve().parents[1]
    script = project_root / "scripts" / "run_mpc_balance_compare.py"
    assert script.is_file(), f"找不到对比脚本: {script}"

    source_root = tmp_path / "source"
    output_root = source_root / "fresh_outputs"
    source_root.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output-root",
            str(output_root),
            "--source-root",
            str(source_root),
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert result.returncode == 0, (
        f"脚本退出码 {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    outputs = output_root
    result_json = outputs / "results" / "estimation_24.json"
    plot_png = outputs / "plots" / "estimation_24.png"
    log_file = outputs / "logs" / "estimation_24.log"
    report_md = outputs / "portfolio" / "24" / "mpc_vs_lqr_report.md"

    # 五件套存在性校验
    for artifact in (result_json, plot_png, log_file, report_md):
        assert artifact.is_file(), f"产物缺失: {artifact}"

    # 结果契约校验
    data = json.loads(result_json.read_text(encoding="utf-8"))
    assert data.get("passed") is True, (
        f"实验未通过，checks={data.get('checks')}"
    )
    assert data["plots"] == ["fresh_outputs/plots/estimation_24.png"]
    assert data["logs"] == ["fresh_outputs/logs/estimation_24.log"]
    assert data["source_state"]["commit"] == "unknown"

    # 核心指标存在性
    metrics = data.get("metrics", {})
    required_keys = [
        "mpc_pitch_rmse",
        "max_torque_mpc",
        "settling_time_s_mpc",
        "constraint_hit_rate",
        "solve_time_ms_mean",
        "mujoco_solve_success_ratio",
        "mujoco_survived",
        "mujoco_constraints_satisfied",
        "mujoco_prediction_constraints_satisfied",
        "mujoco_actual_constraints_satisfied",
        "mujoco_steps_executed",
        "mujoco_pitch_rmse",
        "mujoco_max_torque",
    ]
    for key in required_keys:
        assert key in metrics, f"metrics 缺少字段: {key}"
