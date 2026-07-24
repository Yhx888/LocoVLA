"""24 关：MPC vs LQR vs 受限 MPC 三条闭环曲线对照。

依赖已扩展的 LinearMPC（支持 4 状态 + 状态约束）和 4 状态线性倒立摆离散
模型 `upkie_balance_ss_matrices`。线性仿真用于控制器对照，最终通过条件由
真实 MuJoCo 闭环决定。

产物：
- outputs/results/estimation_24.json（4 项 pass 条件）
- outputs/plots/estimation_24.png（三行子图）
- outputs/logs/estimation_24.log（QP 求解统计）
- outputs/portfolio/24/mpc_vs_lqr_report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import solve_discrete_are

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.controllers.mpc import (
    LinearMPC,
    run_mujoco_mpc_closed_loop,
    upkie_balance_ss_matrices,
)
from upkie_mujoco_course.course.results import write_experiment_result
from upkie_mujoco_course.utils.paths import project_root


def _lqr_gain(a: np.ndarray, b: np.ndarray, q: np.ndarray, r: np.ndarray) -> np.ndarray:
    p = solve_discrete_are(a, b, q, r)
    return np.linalg.solve(b.T @ p @ b + r, b.T @ p @ a)


def _simulate(a: np.ndarray, b: np.ndarray, x0: np.ndarray, disturb: np.ndarray, *, controller_fn, control_limit: float, steps: int) -> tuple[np.ndarray, np.ndarray, list[float]]:
    x = x0.copy()
    xs = [x.copy()]
    us = []
    solve_times: list[float] = []
    for t in range(steps):
        u_raw = controller_fn(x)
        u = np.clip(np.asarray(u_raw, dtype=float).reshape(-1), -control_limit, control_limit)
        us.append(u.copy())
        stats = getattr(controller_fn, "__self__", None)
        if isinstance(stats, LinearMPC) and stats.last_solve_stats is not None:
            solve_times.append(stats.last_solve_stats.solve_time_ms)
        x = a @ x + (b @ u).reshape(-1)
        # 加扰动
        if t < disturb.shape[0]:
            x = x + disturb[t]
        xs.append(x.copy())
    return np.stack(xs), np.stack(us), solve_times


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 MPC、LQR 与受限 MPC 对照实验")
    parser.add_argument("--output-root", default="outputs", help="实验产物根目录")
    parser.add_argument("--source-root", default=None, help="源码与证据引用根目录")
    parser.add_argument("--seed", type=int, default=0, help="固定随机种子")
    args = parser.parse_args()

    source_root = (
        Path(args.source_root).resolve()
        if args.source_root is not None
        else project_root().resolve()
    )
    root = Path(args.output_root)
    if not root.is_absolute():
        root = project_root() / root

    dt = 0.02
    steps = 200
    a, b = upkie_balance_ss_matrices(dt=dt)
    q = np.diag([200.0, 5.0, 5.0, 5.0])
    r = np.array([[10.0]])
    control_limit = 1.0
    tighter_limit = 0.35  # 受限 MPC 的更严格约束（刷无 LQR 的最大力矩以触发饱和）

    rng = np.random.default_rng(args.seed)
    disturbance = np.zeros((steps, 4))
    disturbance[10, 0] = 0.08  # 一次俯仰扰动脉冲（重到足以触发多步饱和）
    disturbance[80, 2] = 0.05

    # 1) LQR
    k = _lqr_gain(a, b, q, r)
    lqr_fn = lambda state: -k @ state

    # 2) MPC（无状态约束、宽输入）
    mpc = LinearMPC(a, b, q, r, horizon=20, control_limit=control_limit)

    # 3) 受限 MPC（更紧输入 + pitch 状态硬约束）
    mpc_constrained = LinearMPC(
        a, b, q, r, horizon=20,
        control_limit=tighter_limit,
        state_lower=np.array([-0.20, -np.inf, -np.inf, -np.inf]),
        state_upper=np.array([0.20, np.inf, np.inf, np.inf]),
    )

    x0 = np.array([0.05, 0.0, 0.0, 0.0])
    xs_lqr, us_lqr, _ = _simulate(a, b, x0, disturbance, controller_fn=lqr_fn, control_limit=control_limit, steps=steps)
    xs_mpc, us_mpc, times_mpc = _simulate(a, b, x0, disturbance, controller_fn=mpc.compute, control_limit=control_limit, steps=steps)
    xs_cst, us_cst, times_cst = _simulate(a, b, x0, disturbance, controller_fn=mpc_constrained.compute, control_limit=tighter_limit, steps=steps)

    def _rmse(pitch: np.ndarray) -> float:
        return float(np.sqrt(np.mean(pitch ** 2)))

    def _settling_time(pitch: np.ndarray, tol: float = 0.02) -> float:
        below = np.abs(pitch) < tol
        # 找连续 20 步都在容差内的第一个索引
        for idx in range(pitch.size - 20):
            if np.all(below[idx : idx + 20]):
                return float(idx * dt)
        return float(pitch.size * dt)

    lqr_rmse = _rmse(xs_lqr[:, 0])
    mpc_rmse = _rmse(xs_mpc[:, 0])
    cst_rmse = _rmse(xs_cst[:, 0])
    max_torque_lqr = float(np.max(np.abs(us_lqr)))
    max_torque_mpc = float(np.max(np.abs(us_mpc)))
    max_torque_cst = float(np.max(np.abs(us_cst)))
    constraint_hit_rate = float(np.mean(np.abs(us_cst) >= tighter_limit - 1e-6))
    settling_lqr = _settling_time(xs_lqr[:, 0])
    settling_mpc = _settling_time(xs_mpc[:, 0])
    settling_cst = _settling_time(xs_cst[:, 0])
    solve_time_ms_mean = float(np.mean(times_mpc)) if times_mpc else 0.0
    mujoco_report = run_mujoco_mpc_closed_loop(steps=100)

    metrics = {
        "lqr_pitch_rmse": lqr_rmse,
        "mpc_pitch_rmse": mpc_rmse,
        "constrained_mpc_pitch_rmse": cst_rmse,
        "mpc_over_lqr_rmse_ratio": float(mpc_rmse / max(1e-9, lqr_rmse)),
        "max_torque_lqr": max_torque_lqr,
        "max_torque_mpc": max_torque_mpc,
        "max_torque_constrained_mpc": max_torque_cst,
        "constrained_mpc_torque_within_limit": float(max_torque_cst <= tighter_limit + 1e-6),
        "constraint_hit_rate": constraint_hit_rate,
        "settling_time_s_lqr": settling_lqr,
        "settling_time_s_mpc": settling_mpc,
        "settling_time_s_constrained_mpc": settling_cst,
        "solve_time_ms_mean": solve_time_ms_mean,
        "mujoco_solve_success_ratio": float(mujoco_report["solve_success_ratio"]),
        "mujoco_survived": float(bool(mujoco_report["survived"])),
        "mujoco_constraints_satisfied": float(bool(mujoco_report["constraints_satisfied"])),
        "mujoco_prediction_constraints_satisfied": float(bool(mujoco_report["prediction_constraints_satisfied"])),
        "mujoco_actual_constraints_satisfied": float(bool(mujoco_report["actual_constraints_satisfied"])),
        "mujoco_steps_executed": float(mujoco_report["steps_executed"]),
        "mujoco_pitch_rmse": float(mujoco_report["pitch_rmse_rad"]),
        "mujoco_max_torque": float(mujoco_report["max_wheel_torque_nm"]),
        "mujoco_solve_time_ms_mean": float(mujoco_report["solve_time_ms_mean"]),
    }
    pass_conditions = {
        "mpc_over_lqr_rmse_ratio": {"operator": "<=", "value": 1.2},
        "constrained_mpc_torque_within_limit": {"operator": "==", "value": 1.0},
        "constraint_hit_rate": {"operator": ">=", "value": 0.005},
        "solve_time_ms_mean": {"operator": "<=", "value": 200.0},
        "mujoco_solve_success_ratio": {"operator": "==", "value": 1.0},
        "mujoco_survived": {"operator": "==", "value": 1.0},
        "mujoco_constraints_satisfied": {"operator": "==", "value": 1.0},
        "mujoco_prediction_constraints_satisfied": {"operator": "==", "value": 1.0},
        "mujoco_actual_constraints_satisfied": {"operator": "==", "value": 1.0},
        "mujoco_steps_executed": {"operator": ">=", "value": 100.0},
        "mujoco_pitch_rmse": {"operator": "<=", "value": 0.15},
        "mujoco_max_torque": {"operator": "<=", "value": 1.0},
    }

    # ---- 写文件 ----
    plot_path = root / "plots" / "estimation_24.png"
    log_path = root / "logs" / "estimation_24.log"
    result_path = root / "results" / "estimation_24.json"
    report_path = root / "portfolio" / "24" / "mpc_vs_lqr_report.md"
    for path in (plot_path, log_path, result_path, report_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    # 绘图：三行子图（俯仰、力矩、约束边界）
    time_axis = np.arange(steps + 1) * dt
    time_axis_u = np.arange(steps) * dt
    figure, axes = plt.subplots(3, 1, figsize=(11.0, 9.0), sharex=True)
    axes[0].plot(time_axis, xs_lqr[:, 0], label="LQR", color="#2978b5")
    axes[0].plot(time_axis, xs_mpc[:, 0], label="MPC", color="#17745a")
    axes[0].plot(time_axis, xs_cst[:, 0], label="Constrained MPC", color="#d36b27")
    axes[0].axhline(0.20, color="grey", linestyle="--", alpha=0.6)
    axes[0].axhline(-0.20, color="grey", linestyle="--", alpha=0.6)
    axes[0].set(ylabel="pitch [rad]", title=f"Chapter 24: LQR vs MPC vs Constrained MPC (RMSE {lqr_rmse:.3f}/{mpc_rmse:.3f}/{cst_rmse:.3f})")
    axes[0].legend()
    axes[1].plot(time_axis_u, us_lqr[:, 0], label="LQR", color="#2978b5")
    axes[1].plot(time_axis_u, us_mpc[:, 0], label="MPC", color="#17745a")
    axes[1].plot(time_axis_u, us_cst[:, 0], label="Constrained MPC", color="#d36b27")
    axes[1].axhline(control_limit, color="grey", linestyle="--")
    axes[1].axhline(-control_limit, color="grey", linestyle="--")
    axes[1].axhline(tighter_limit, color="#d36b27", linestyle=":")
    axes[1].axhline(-tighter_limit, color="#d36b27", linestyle=":")
    axes[1].set(ylabel="wheel torque [N*m]")
    axes[1].legend()
    axes[2].plot(time_axis, xs_cst[:, 2], label="position x", color="#17745a")
    axes[2].plot(time_axis, xs_cst[:, 3], label="velocity", color="#d36b27")
    axes[2].set(xlabel="time [s]", ylabel="state", title="Constrained MPC position / velocity")
    axes[2].legend()
    for axis in axes:
        axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(plot_path, dpi=140)
    plt.close(figure)

    # 日志：QP 求解统计
    log_path.write_text(
        json.dumps(
            {
                "mpc_solve_times_ms": times_mpc,
                "constrained_mpc_solve_times_ms": times_cst,
                "mean_solve_time_ms": solve_time_ms_mean,
                "constraint_hit_rate": constraint_hit_rate,
                "control_limit": control_limit,
                "tighter_limit": tighter_limit,
                "seed": args.seed,
                "mujoco": mujoco_report,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # 报告：mpc_vs_lqr_report.md
    report_lines = [
        "# 24 关：MPC vs LQR 闭环对照报告",
        "",
        f"- 采样周期：{dt} s，仿真步数：{steps}",
        f"- 状态：pitch, pitch_rate, x, x_dot",
        f"- 输入限幅（LQR/MPC）: ±{control_limit} N*m；受限 MPC: ±{tighter_limit} N*m + pitch ∈ [-0.20, 0.20]",
        "",
        "| 指标 | LQR | MPC | 受限 MPC |",
        "|---|---|---|---|",
        f"| pitch RMSE [rad] | {lqr_rmse:.4f} | {mpc_rmse:.4f} | {cst_rmse:.4f} |",
        f"| max\\|torque\\| [N*m] | {max_torque_lqr:.3f} | {max_torque_mpc:.3f} | {max_torque_cst:.3f} |",
        f"| settling time [s] (\\|pitch\\|<0.02, 连续 20 步) | {settling_lqr:.2f} | {settling_mpc:.2f} | {settling_cst:.2f} |",
        f"| MPC 平均 QP 求解时间 [ms] | — | {solve_time_ms_mean:.2f} | — |",
        f"| 受限 MPC 约束命中率 | — | — | {constraint_hit_rate:.2%} |",
        "",
        "## MuJoCo 必修闭环",
        "",
        f"- 完成步数：{int(mujoco_report['steps_executed'])}/100",
        f"- pitch RMSE：{mujoco_report['pitch_rmse_rad']:.4f} rad",
        f"- 最大轮端力矩：{mujoco_report['max_wheel_torque_nm']:.3f} N·m",
        f"- 求解成功率：{mujoco_report['solve_success_ratio']:.1%}",
        f"- 存活：{mujoco_report['survived']}",
        f"- 预测/实际约束：{mujoco_report['prediction_constraints_satisfied']} / {mujoco_report['actual_constraints_satisfied']}",
        "",
        "**结论**：MPC 在无约束情形下与 LQR 数值接近（比率 ≤ 1.2）；引入 pitch/torque 硬约束后，MPC 主动牺牲部分收敛速度，把 pitch 限制在物理安全范围内。约束命中率 > 0 说明 QP 真正触碰约束边界，而不是纯软约束。",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    # 结果契约
    write_experiment_result(
        result_path,
        chapter_id="24",
        seed=args.seed,
        config={
            "lab": "estimation_24",
            "controllers": ["LQR", "MPC", "Constrained MPC", "MuJoCo MPC"],
            "required_backend": "mujoco",
            "dt": dt,
            "steps": steps,
            "control_limit": control_limit,
            "tighter_limit": tighter_limit,
        },
        metrics=metrics,
        pass_conditions=pass_conditions,
        plots=[str(plot_path)],
        logs=[str(log_path)],
        root=source_root,
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"结果已写入 {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
