#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第 45 关综合毕业项目编排入口：编排仿真→控制→安全→日志→分析全链路。

调用 ``upkie_mujoco_course.capstone.runner.run_capstone`` 执行：
1. 6 步快速验证（保留以兼容 test_capstone_runner.py）
2. 5 步真实端到端链路（任务 4.2 要求）：
   - physics：1000 步 MuJoCo 仿真
   - code：PD 控制 1000 步
   - safety：安全状态机（pitch=0.5 触发 FAULT）
   - realtime：9 字段 JSON lines 日志
   - robustness：综合分析所有维度
3. 端到端验证失败时强制归零对应维度，system_score = min(所有维度)
4. 生成 3 张图：e2e_flow、dimension_scores、simulation_timeline
5. 生成 2 个日志文件：e2e_run.log、simulation_data.json

输出：
- 统一结果契约 ``outputs/results/engineering_45.json``
- 端到端运行日志 ``outputs/logs/engineering_45_e2e_run.log``
- 仿真数据 JSON ``outputs/logs/engineering_45_simulation_data.json``
- 端到端流程图 ``outputs/plots/engineering_45_e2e_flow.png``
- 8 维度评分雷达图 ``outputs/plots/engineering_45_dimension_scores.png``
- 仿真时间线图 ``outputs/plots/engineering_45_simulation_timeline.png``
- Markdown portfolio 报告 ``outputs/portfolio/45/engineering_45_report.md``

用法：
    python scripts/run_capstone_project.py [--output-root outputs]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.capstone import run_capstone  # noqa: E402
from upkie_mujoco_course.course.results import write_experiment_result  # noqa: E402

# 8 类毕业门槛 → 评分维度名称（用于 portfolio 报告展示）
GATE_TO_DIMENSION = {
    "code_tests": "code（代码测试）",
    "physical_metrics": "physics（物理指标）",
    "robustness": "robustness（鲁棒性）",
    "realtime": "realtime（实时性）",
    "safety": "safety（安全性）",
    "documentation": "docs（文档）",
    "design_review": "design_review（设计评审）",
    "oral_defense": "oral_defense（口头答辩）",
}

# 8 个评分维度键（与 DIMENSION_TO_GATE 一致）
DIMENSION_KEYS = [
    "code",
    "physics",
    "robustness",
    "realtime",
    "safety",
    "docs",
    "design_review",
    "oral_defense",
]

# 6 个快速验证步骤（顺序固定，用于时间线展示）
END_TO_END_STEPS = [
    ("simulation", "仿真加载（nq=13/nv=12/nu=6）"),
    ("control", "PD 控制（pitch=0.1 输入）"),
    ("environment", "Gymnasium 环境（reset+step）"),
    ("safety_ros2", "ROS2 安全（5 故障全安全）"),
    ("log_contract", "日志契约（9 字段 0 miss）"),
    ("doc_consistency", "文档一致性（7 项检查）"),
]

# 5 步真实端到端链路（任务 4.2 要求）
E2E_PIPELINE_STEPS = [
    ("physics", "仿真启动（1000 步 MuJoCo 仿真）"),
    ("code", "PD 控制（应用到仿真 1000 步）"),
    ("safety", "安全状态机（pitch=0.5 触发 FAULT）"),
    ("realtime", "日志记录（9 字段 JSON lines）"),
    ("robustness", "综合分析（8 维度全部通过）"),
]


def _resolve_output_root(value: str, source_root: Path) -> Path:
    """将输出根目录解析为绝对路径，相对路径相对于源码根。"""
    p = Path(value)
    return p.resolve() if p.is_absolute() else (source_root / p).resolve()


def _gate_to_dim_key(gate: str) -> str:
    """门槛名 → 评分维度键。"""
    if gate in ("design_review", "oral_defense"):
        return gate
    return {
        "code_tests": "code",
        "physical_metrics": "physics",
        "robustness": "robustness",
        "realtime": "realtime",
        "safety": "safety",
        "documentation": "docs",
    }.get(gate, gate)


def _build_metrics(report: dict) -> dict[str, float]:
    """从 capstone 报告构造统一契约 metrics。"""
    dim_scores = report["dimension_scores"]
    metrics: dict[str, float] = {
        "project_score": float(report["project_score"]),
        "system_score": float(report["system_score"]),
        "course_readiness_passed": float(report["course_readiness_passed"]),
    }
    for dim, score in dim_scores.items():
        metrics[dim] = float(score)
    # 通过的门槛数
    metrics["gate_passed_count"] = float(sum(1 for v in dim_scores.values() if v >= 1.0))
    metrics["gate_total_count"] = float(len(dim_scores))
    # 端到端验证步骤数（6 步快速验证）
    end_to_end = report.get("end_to_end_validation", {})
    metrics["end_to_end_steps_passed"] = float(sum(1 for v in end_to_end.values() if v.get("passed")))
    metrics["end_to_end_steps_total"] = float(len(END_TO_END_STEPS))
    # 5 步真实端到端链路
    e2e_pipeline = report.get("e2e_pipeline", {})
    metrics["e2e_pipeline_steps_passed"] = float(sum(1 for v in e2e_pipeline.values() if v.get("passed")))
    metrics["e2e_pipeline_steps_total"] = float(len(E2E_PIPELINE_STEPS))
    return metrics


def _build_config(report: dict) -> dict:
    """从 capstone 报告构造 config 摘要（门槛状态表 + 端到端验证标记）。"""
    evidence = report["evidence"]
    gate_summary = {}
    for gate, dim_label in GATE_TO_DIMENSION.items():
        ev = evidence.get(gate, {})
        gate_summary[gate] = {
            "dimension": dim_label,
            "chapter": ev.get("chapter", "?"),
            "passed": ev.get("passed", False),
        }
    return {
        "gates": gate_summary,
        "project_scoring_formula": "project_score = min(code, physics, robustness, realtime, safety, docs)",
        "scoring_formula": "system_score = min(code, physics, robustness, realtime, safety, docs, design_review, oral_defense)",
        "end_to_end_validation": True,
        "e2e_pipeline": True,
        "e2e_pipeline_steps": [step for step, _ in E2E_PIPELINE_STEPS],
    }


def _write_portfolio(
    portfolio: Path,
    report: dict,
    metrics: dict,
    result_path: Path,
    e2e_run_log: Path,
    sim_data_path: Path,
    e2e_flow_plot: Path,
    dim_score_plot: Path,
    sim_timeline_plot: Path,
) -> None:
    """写 portfolio Markdown 报告。"""
    portfolio.parent.mkdir(parents=True, exist_ok=True)
    dim_scores = report["dimension_scores"]
    evidence = report["evidence"]
    end_to_end = report.get("end_to_end_validation", {})
    overrides = report.get("end_to_end_overrides", {})
    e2e_pipeline = report.get("e2e_pipeline", {})
    e2e_overrides = report.get("e2e_overrides", {})

    # 各维度得分表
    dim_rows = []
    for gate, dim_label in GATE_TO_DIMENSION.items():
        dim_key = _gate_to_dim_key(gate)
        score = dim_scores.get(dim_key, 0.0)
        ev = evidence.get(gate, {})
        chapter = ev.get("chapter", "?")
        passed = ev.get("passed", False)
        status = "[OK] 通过" if passed else "[FAIL] 未通过"
        dim_rows.append(f"| {dim_label} | 第 {chapter} 关 | {score:.1f} | {status} |")

    # 6 步快速验证结果表
    e2e_rows = []
    for step, label in END_TO_END_STEPS:
        result = end_to_end.get(step, {})
        passed = bool(result.get("passed", False))
        details = result.get("details", {})
        elapsed_ms = details.get("elapsed_ms", 0.0)
        status = "[OK] 通过" if passed else "[FAIL] 失败"
        impacted = overrides.get(step, [])
        impact_str = ", ".join(impacted) if impacted else "---"
        detail_keys = [k for k in details.keys() if k not in ("elapsed_ms",)]
        summary_parts = []
        for k in detail_keys[:4]:
            v = details[k]
            if isinstance(v, (list, dict)):
                v_str = json.dumps(v, ensure_ascii=False)
                if len(v_str) > 60:
                    v_str = v_str[:57] + "..."
            else:
                v_str = str(v)
            summary_parts.append(f"{k}={v_str}")
        detail_str = "; ".join(summary_parts) if summary_parts else "---"
        e2e_rows.append(
            f"| {step} | {label} | {status} | {elapsed_ms:.3f} | {impact_str} | {detail_str} |"
        )

    # 5 步真实端到端链路结果表
    pipeline_rows = []
    for step, label in E2E_PIPELINE_STEPS:
        result = e2e_pipeline.get(step, {})
        passed = bool(result.get("passed", False))
        details = result.get("details", {})
        elapsed_ms = details.get("elapsed_ms", 0.0)
        status = "[OK] 通过" if passed else "[FAIL] 失败"
        impacted = e2e_overrides.get(step, [])
        impact_str = ", ".join(impacted) if impacted else "---"
        # 提取关键指标（去掉 error/elapsed_ms）
        key_metrics = []
        for k in ("steps_run", "expected_steps", "any_nan", "out_of_range",
                  "entered_fault", "stays_fault_without_reset", "resets_to_boot",
                  "field_count", "timestamp_monotonic", "first_four_passed",
                  "all_gates_passed", "sim_data_complete", "gate_passed_count",
                  "gate_total_count", "final_pitch_rad", "pitch_fault_rad",
                  "sample_count", "error"):
            if k in details:
                v = details[k]
                key_metrics.append(f"{k}={v}")
        detail_str = "; ".join(key_metrics[:5]) if key_metrics else "---"
        pipeline_rows.append(
            f"| {step} | {label} | {status} | {elapsed_ms:.3f} | {impact_str} | {detail_str} |"
        )

    # 计算端到端验证步骤通过数
    e2e_passed = sum(1 for v in end_to_end.values() if v.get("passed"))
    e2e_total = len(END_TO_END_STEPS)
    pipeline_passed = sum(1 for v in e2e_pipeline.values() if v.get("passed"))
    pipeline_total = len(E2E_PIPELINE_STEPS)

    lines = [
        "# 第 45 关综合毕业项目报告",
        "",
        "## 综合评分",
        "",
        "```text",
        "system_score = min(code, physics, robustness, realtime, safety, docs, design_review, oral_defense)",
        "```",
        "",
        f"- **project_score = {metrics['project_score']:.1f}**",
        f"- **system_score = {metrics['system_score']:.1f}**",
        f"- 通过门槛数：{int(metrics['gate_passed_count'])} / {int(metrics['gate_total_count'])}",
        f"- 第 45 关通过条件：`project_score >= 1.0`（六个既有工程维度全部通过）",
        f"- 6 步快速验证：{int(metrics.get('end_to_end_steps_passed', 0))} / {int(metrics.get('end_to_end_steps_total', 0))}",
        f"- 5 步真实端到端链路：{int(metrics.get('e2e_pipeline_steps_passed', 0))} / {int(metrics.get('e2e_pipeline_steps_total', 0))}",
        f"- 第 45 关状态：{'通过' if report['passed'] else '未通过（存在未闭环工程维度）'}",
        "",
        "## 综合评分公式说明",
        "",
        "综合评分取 8 个维度的**最小值**（木桶原理）：任何一个维度不通过，",
        "system_score 即为 0.0。每个维度的得分同时受三类因素影响：",
        "",
        "1. **门槛证据**：8 类毕业门槛（第 37/18/31/42/43/44/46/47 关）的 passed 字段",
        "2. **6 步快速验证**：仿真/控制/环境/安全/日志/文档的快速校验",
        "3. **5 步真实端到端链路**（任务 4.2 新增）：1000 步仿真、PD 控制、安全状态机、日志记录、综合分析",
        "",
        "当任一验证步骤失败时，对应维度的分数强制归零：",
        "",
        "### 6 步快速验证归零规则",
        "- simulation 失败 → code/physics 归零",
        "- control 失败 → code 归零",
        "- environment 失败 → code/physics 归零",
        "- safety_ros2 失败 → safety 归零",
        "- log_contract 失败 → realtime 归零",
        "- doc_consistency 失败 → docs 归零",
        "",
        "### 5 步真实端到端链路归零规则（任务 4.2）",
        "- physics 失败 → physics 归零（仿真启动失败）",
        "- code 失败 → code 归零（PD 控制失败）",
        "- safety 失败 → safety 归零（安全状态机失败）",
        "- realtime 失败 → realtime 归零（日志记录失败）",
        "- robustness 失败 → robustness 归零（综合分析失败）",
        "",
        "## 8 维度评分明细",
        "",
        "| 维度 | 关联关卡 | 得分 | 状态 |",
        "|---|---|---|---|",
        *dim_rows,
        "",
        "## 6 步快速验证结果",
        "",
        f"6 步快速验证通过数：**{e2e_passed} / {e2e_total}**",
        "",
        "| 步骤 | 说明 | 状态 | 耗时 (ms) | 失败时归零维度 | 详情摘要 |",
        "|---|---|---|---|---|---|",
        *e2e_rows,
        "",
        "## 5 步真实端到端链路（任务 4.2）",
        "",
        f"5 步真实端到端链路通过数：**{pipeline_passed} / {pipeline_total}**",
        "",
        "本链路真实运行 MuJoCo 仿真、PD 控制器、安全状态机和日志记录，",
        "采集 1000 步仿真数据并生成 9 字段 JSON lines 日志。",
        "任一步骤失败立即令对应维度归零，system_score = 0.0。",
        "",
        "| 步骤 | 说明 | 状态 | 耗时 (ms) | 失败时归零维度 | 关键指标 |",
        "|---|---|---|---|---|---|",
        *pipeline_rows,
        "",
        "## 端到端链路详细说明",
        "",
        "### 步骤 1：仿真启动（physics）",
        "",
        "- 真实加载 MuJoCo 模型（`configs/robot/upkie.json`）",
        "- 运行 1000 步仿真（0 控制输入，纯被动）",
        "- 记录 base pitch、6 个关节位置、6 个 ctrl 力矩",
        "- 失败条件：模型加载失败或仿真出现 NaN",
        "",
        "### 步骤 2：PD 控制（code）",
        "",
        "- 真实调用 PD 控制器（`configs/control/pd.json`）",
        "- 应用到仿真 1000 步，目标姿态为 stand",
        "- 失败条件：控制力矩 NaN 或超范围",
        "",
        "### 步骤 3：安全状态机（safety）",
        "",
        "- 真实调用 SafetyStateMachine（C++ safety_state_machine.cpp 的 Python 等价实现）",
        "- 推进 BOOT → SELF_CHECK → DISARMED → ARMED",
        "- 注入 pitch=0.5（超限 0.3），验证状态进入 FAULT",
        "- 验证 FAULT 状态下不自动恢复，仅显式 reset 才能离开",
        "- 失败条件：状态未进入 FAULT 或自动恢复",
        "",
        "### 步骤 4：日志记录（realtime）",
        "",
        "- 真实生成 200 条 JSON lines 日志",
        "- 9 字段：timestamp_ns / episode_id / git_commit / pitch_rad / pitch_rate_rad_s /",
        "  raw_torque_common_nm / clamped_torque_common_nm / safety_flag / loop_cycle_ms",
        "- 验证字段完整性和时间戳单调递增",
        "- 失败条件：字段缺失或时间戳回退",
        "",
        "### 步骤 5：综合分析（robustness）",
        "",
        "- 真实计算综合指标",
        "- 验证前 4 步端到端链路全部通过",
        "- 验证 8 类毕业门槛全部通过",
        "- 验证仿真数据完整性（physics/code 各 1000 步）",
        "- 失败条件：任一维度不通过",
        "",
        "## 评分逻辑说明",
        "",
        "综合评分取 8 个维度的**最小值**（木桶原理）：任何一个维度不通过，",
        "system_score 即为 0.0。这要求毕业项目「全链路无短板」——",
        "仿真、控制、鲁棒性、实时性、安全性、文档、设计评审、口头答辩全部闭环。",
        "",
        "**任务 4.2 新增 5 步真实端到端链路**：除门槛证据和 6 步快速验证外，",
        "第 45 关直接调用 `sim`/`controllers`/`safety_state_machine` 模块进行真实端到端运行，",
        "采集 1000 步仿真数据和 200 条日志记录。任一链路步骤失败会强制令对应维度归零，",
        "确保 system_score 反映的是「真实可运行」的全链路状态，而非仅 JSON 文件聚合。",
        "",
        "## 证据文件",
        "",
        f"- 结果契约：`{result_path}`",
        f"- 端到端运行日志：`{e2e_run_log}`",
        f"- 仿真数据 JSON：`{sim_data_path}`",
        f"- 端到端流程图：`{e2e_flow_plot}`",
        f"- 8 维度评分雷达图：`{dim_score_plot}`",
        f"- 仿真时间线图：`{sim_timeline_plot}`",
        f"- 毕业门槛汇总：`outputs/reports/graduation_gates.json`",
        "",
        "## 门槛证据来源",
        "",
        "- 第 37 关（code_tests）：`outputs/results/checkpoint_37.json`",
        "- 第 18 关（physical_metrics）：`outputs/results/checkpoint_18.json`",
        "- 第 31 关（robustness）：`outputs/results/checkpoint_31.json`",
        "- 第 42 关（realtime）：`outputs/results/engineering_42.json`",
        "- 第 43 关（safety）：`outputs/results/engineering_43.json`",
        "- 第 44 关（documentation）：`outputs/results/engineering_44.json`",
        "- 第 46 关（design_review）：`outputs/results/engineering_46.json`",
        "- 第 47 关（oral_defense）：`outputs/results/engineering_47.json`",
        "",
        "## 6 步快速验证证据来源",
        "",
        "- 仿真：真实调用 `upkie_mujoco_course.sim.loader.build_mujoco_model`",
        "- 控制：真实调用 `upkie_mujoco_course.controllers.pd.PDController`",
        "- 环境：真实调用 `upkie_mujoco_course.envs.standing_env.StandingEnv`",
        "- ROS2 安全：`outputs/results/engineering_43_ros2_fault_injection.json`",
        "- 日志契约：`outputs/results/engineering_42.json`",
        "- 文档一致性：`outputs/results/doc_code_consistency_44.json`",
        "",
        "## 5 步真实端到端链路证据来源（任务 4.2）",
        "",
        "- physics：真实运行 1000 步 MuJoCo 仿真，数据见 `outputs/logs/engineering_45_simulation_data.json`",
        "- code：真实运行 PD 控制 1000 步，数据见 `outputs/logs/engineering_45_simulation_data.json`",
        "- safety：真实调用 SafetyStateMachine Python 等价实现（与 C++ safety_state_machine.cpp 一致）",
        "- realtime：真实生成 200 条 9 字段 JSON lines 日志",
        "- robustness：综合分析所有维度，数据见 `outputs/logs/engineering_45_e2e_run.log`",
    ]
    portfolio.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="运行第 45 关综合毕业项目")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--source-root", default=str(ROOT))
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    output_root = _resolve_output_root(args.output_root, source_root)

    # 1. 运行综合毕业项目编排（包含 6 步快速验证 + 5 步真实端到端链路）
    #    runner.py 已经在内部生成 e2e_run.log 和 simulation_data.json
    report = run_capstone(output_root, seed=args.seed)
    metrics = _build_metrics(report)
    config = _build_config(report)

    # 2. 提取端到端运行日志和仿真数据路径
    e2e_run_log = Path(report.get("e2e_log_path", str(output_root / "logs" / "engineering_45_e2e_run.log")))
    sim_data_path = Path(report.get("e2e_sim_data_path", str(output_root / "logs" / "engineering_45_simulation_data.json")))

    # 3. 生成 3 张图表
    e2e_flow_plot = output_root / "plots" / "engineering_45_e2e_flow.png"
    dim_score_plot = output_root / "plots" / "engineering_45_dimension_scores.png"
    sim_timeline_plot = output_root / "plots" / "engineering_45_simulation_timeline.png"
    _generate_plots(report, e2e_flow_plot, dim_score_plot, sim_timeline_plot)

    # 4. 写统一结果契约（传入 plots 和 logs）
    #    write_experiment_result 会校验所有引用文件存在
    #    路径引用使用 try-relative-to-ROOT 兜底：在仓库 outputs/ 下用相对路径，
    #    在 tmp_path 等仓库外目录用绝对路径
    result_path = output_root / "results" / "engineering_45.json"

    def _ref(path: Path) -> str:
        """生成路径引用：仓库内用相对路径，仓库外用绝对路径。"""
        try:
            return str(path.resolve().relative_to(source_root))
        except ValueError:
            return str(path)

    plots_refs = [
        _ref(e2e_flow_plot),
        _ref(dim_score_plot),
        _ref(sim_timeline_plot),
    ]
    logs_refs = [
        _ref(e2e_run_log),
        _ref(sim_data_path),
    ]
    graduation_report = output_root / "reports" / "graduation_gates.json"
    if graduation_report.is_file():
        logs_refs.append(_ref(graduation_report))

    write_experiment_result(
        result_path,
        chapter_id="45",
        seed=args.seed,
        config=config,
        metrics=metrics,
        pass_conditions={
            "project_score": {"operator": ">=", "value": 1.0},
        },
        plots=plots_refs,
        logs=logs_refs,
        root=source_root,
    )

    # 5. 写 portfolio 报告
    portfolio = output_root / "portfolio" / "45" / "engineering_45_report.md"
    _write_portfolio(
        portfolio, report, metrics, result_path,
        e2e_run_log, sim_data_path,
        e2e_flow_plot, dim_score_plot, sim_timeline_plot,
    )

    # 6. 打印摘要
    print(f"[OK] 第 45 关结果契约：{result_path}")
    print(f"[OK] 端到端运行日志：{e2e_run_log}")
    print(f"[OK] 仿真数据 JSON：{sim_data_path}")
    print(f"[OK] 端到端流程图：{e2e_flow_plot}")
    print(f"[OK] 8 维度评分雷达图：{dim_score_plot}")
    print(f"[OK] 仿真时间线图：{sim_timeline_plot}")
    print(f"[OK] portfolio：{portfolio}")
    print(f"     system_score = {metrics['system_score']:.1f}")
    print(f"     project_score = {metrics['project_score']:.1f}")
    print(f"     通过门槛数：{int(metrics['gate_passed_count'])} / {int(metrics['gate_total_count'])}")
    print(f"     6 步快速验证：{int(metrics.get('end_to_end_steps_passed', 0))} / {int(metrics.get('end_to_end_steps_total', 0))}")
    print(f"     5 步真实端到端链路：{int(metrics.get('e2e_pipeline_steps_passed', 0))} / {int(metrics.get('e2e_pipeline_steps_total', 0))}")
    for gate, dim_label in GATE_TO_DIMENSION.items():
        dim_key = _gate_to_dim_key(gate)
        score = metrics[dim_key]
        print(f"     - {dim_label}: {score:.1f}")
    print("     6 步快速验证步骤：")
    for step, label in END_TO_END_STEPS:
        result = report["end_to_end_validation"].get(step, {})
        passed = bool(result.get("passed", False))
        elapsed_ms = result.get("details", {}).get("elapsed_ms", 0.0)
        status = "[OK]" if passed else "[FAIL]"
        print(f"       {status} {step} ({label}): {elapsed_ms:.3f} ms")
    print("     5 步真实端到端链路：")
    for step, label in E2E_PIPELINE_STEPS:
        result = report.get("e2e_pipeline", {}).get(step, {})
        passed = bool(result.get("passed", False))
        elapsed_ms = result.get("details", {}).get("elapsed_ms", 0.0)
        status = "[OK]" if passed else "[FAIL]"
        print(f"       {status} {step} ({label}): {elapsed_ms:.3f} ms")
    return 0


def _generate_plots(
    report: dict,
    e2e_flow_plot: Path,
    dim_score_plot: Path,
    sim_timeline_plot: Path,
) -> None:
    """调用 plot_engineering_45.py 生成 3 张图。"""
    import sys

    tools_dir = ROOT / "scripts" / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))

    import plot_engineering_45

    plot_engineering_45.plot_e2e_flow(report, e2e_flow_plot)
    plot_engineering_45.plot_dimension_scores(report, dim_score_plot)
    plot_engineering_45.plot_simulation_timeline(report, sim_timeline_plot)


if __name__ == "__main__":
    sys.exit(main())
