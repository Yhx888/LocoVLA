"""课程关卡自动验收。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt

from upkie_mujoco_course.course.manifest import load_course_manifest
from upkie_mujoco_course.course.results import assess_experiment_result
from upkie_mujoco_course.course.results import write_experiment_result
from upkie_mujoco_course.utils.paths import project_root


TEST_TARGETS = {
    "00": "tests/test_config_loads.py",
    "01": "tests/test_foundations.py::test_central_difference_matches_sine_derivative tests/test_foundations.py::test_foundation_lab_writes_real_result_log_and_plot[01]",
    "02": "tests/test_foundations.py::test_seeded_trace_is_reproducible_and_seed_sensitive tests/test_foundations.py::test_foundation_lab_writes_real_result_log_and_plot[02]",
    "03": "tests/test_foundations.py::test_coordinate_transform_round_trip_recovers_body_point tests/test_foundations.py::test_foundation_lab_writes_real_result_log_and_plot[03]",
    "04": "tests/test_foundations.py::test_small_angle_linearization_is_accurate_only_near_equilibrium tests/test_foundations.py::test_foundation_lab_writes_real_result_log_and_plot[04]",
    "05": "tests/test_foundations.py::test_low_pass_filter_reduces_fixed_seed_pitch_rmse tests/test_foundations.py::test_foundation_lab_writes_real_result_log_and_plot[05]",
    "06": "tests/test_model_loads.py",
    "07": "tests/test_model_loads.py",
    "08": "tests/test_model_loads.py::test_upkie_model_loads_with_actuators",
    "09": "tests/test_actuator_mapping.py tests/test_sensor_mapping.py",
    "10": "tests/test_model_loads.py::test_onboard_camera_renders_visible_red_target",
    "11": "tests/test_model_contract.py",
    "12": "tests/test_controller_outputs.py::test_wheel_balancer_keeps_floating_robot_upright_for_five_seconds",
    "13": "tests/test_classical_control_labs.py::test_pid_anti_windup_stops_integral_growth_during_saturation tests/test_classical_control_labs.py::test_classical_control_lab_writes_real_result_log_plot_and_portfolio[13]",
    "14": "tests/test_classical_control_labs.py::test_pendulum_linearization_is_local_and_torque_has_physical_unit_effect tests/test_classical_control_labs.py::test_classical_control_lab_writes_real_result_log_plot_and_portfolio[14]",
    "15": "tests/test_classical_control_labs.py::test_second_order_poles_distinguish_stable_and_unstable_damping tests/test_classical_control_labs.py::test_classical_control_lab_writes_real_result_log_plot_and_portfolio[15]",
    "16": "tests/test_classical_control_labs.py::test_four_state_wheel_pendulum_model_is_controllable tests/test_classical_control_labs.py::test_classical_control_lab_writes_real_result_log_plot_and_portfolio[16]",
    "17": "tests/test_controller_outputs.py::test_lqr_balancer_keeps_floating_robot_upright_for_five_seconds",
    "18": "tests/test_classical_control_labs.py::test_yaw_and_height_controllers_apply_limits_and_mirror_leg_targets tests/test_classical_control_labs.py::test_classical_control_lab_writes_real_result_log_plot_and_portfolio[18]",
    "19": "tests/test_estimation.py",
    "20": "tests/test_estimation_optimization_labs.py::test_estimation_optimization_labs_write_real_result_log_plot_and_portfolio[20]",
    "21": "tests/test_estimation_optimization_labs.py::test_chapter_21_uses_mujoco_sensors_and_compares_ekf_with_ukf",
    "22": "tests/test_estimation_optimization_labs.py::test_estimation_optimization_labs_write_real_result_log_plot_and_portfolio[22]",
    "23": "tests/test_estimation_optimization_labs.py::test_quadratic_program_respects_box_and_coupled_constraints tests/test_estimation_optimization_labs.py::test_estimation_optimization_labs_write_real_result_log_plot_and_portfolio[23]",
    "24": "tests/test_mpc.py",
    "25": "tests/test_env_check.py tests/test_env_shapes.py",
    "26": "tests/test_rewards.py",
    "27": "tests/test_rl_labs.py::test_policy_gradient_baseline_keeps_mean_near_analytic_gradient_and_reduces_variance tests/test_rl_labs.py::test_rl_labs_write_real_result_log_plot_and_portfolio[27]",
    "28": "tests/test_rl_labs.py::test_chapter_28_trains_and_reloads_real_mujoco_ppo",
    "29": "tests/test_env_check.py",
    "30": "tests/test_rl_pipeline.py::test_zero_residual_matches_classic_controller_step_by_step tests/test_rl_pipeline.py::test_residual_environment_only_modifies_torque_actuators tests/test_rl_labs.py::test_residual_lab_trains_real_policy_and_rejects_performance_regression",
    "31": "tests/test_rl_labs.py::test_randomization_sampler_is_seeded_and_covers_every_runtime_field tests/test_rl_labs.py::test_rl_labs_write_real_result_log_plot_and_portfolio[31] tests/test_rl_labs.py::test_sim2real_lab_reports_a_non_degenerate_bootstrap_interval",
    "32": "tests/test_vla.py",
    "33": "tests/test_vla.py::test_rgbd_detector_finds_red_target_centroid_and_depth",
    "34": "tests/test_vla.py::test_language_instruction_maps_to_structured_target",
    "35": "tests/test_vla.py::test_chapter_35_generates_real_three_color_mujoco_dataset",
    "36": "tests/test_vla.py::test_behavior_cloning_policy_fits_visual_language_examples tests/test_vla.py::test_behavior_cloning_policy_round_trips_checkpoint",
    "37": "tests/test_vla.py::test_vla_35_to_37_pipeline_evaluates_bc_in_real_mujoco tests/test_vla.py::test_emergency_stop_bypasses_bc_inference",
    "38": "tests/test_engineering_parity.py tests/test_course_assets.py::test_cpp_dependency_configuration_does_not_register_eigen_test_suite",
    "39": "tests/test_engineering_parity.py tests/test_course_assets.py::test_cpp_dependency_configuration_does_not_register_eigen_test_suite",
    # 第 40 关为 ROS2 控制节点，相关 C++ 测试在 ros2_ws/src/upkie_control/test/ 下，
    # 属 WSL2 环境的 colcon 测试，Windows 侧 pytest 无法直接运行；
    # 测试目标指向已有的工程关测试文件（会校验 ros2_ws 结构），与 41 关保持一致。
    "40": "tests/test_course_assets.py",
    "41": "tests/test_course_assets.py",
    "42": "tests/test_engineering_42.py",
    "43": "tests/test_safety.py",
    "44": "tests/test_design_docs.py",
    "45": "tests/test_capstone.py",
    "46": "tests/test_fault_drill.py",
    "47": "tests/test_code_review.py",
    "H01": "tests/test_hardware_audit.py",
}

REQUIRED_EXPERIMENT_RESULTS = {
    **{chapter: f"foundation_{chapter}.json" for chapter in ("01", "02", "03", "04", "05")},
    "11": "model_contract_11.json",
    **{chapter: f"classical_{chapter}.json" for chapter in ("13", "14", "15", "16", "18")},
    **{chapter: f"estimation_{chapter}.json" for chapter in ("20", "21", "22", "23")},
    "24": ("estimation_24.json", "trajectory_24.json"),
    "25": "rl_25.json",
    "26": "rl_26.json",
    "27": "rl_27.json",
    "28": "rl_28.json",
    "29": "rl_29.json",
    "30": "rl_30.json",
    "31": "rl_31.json",
    "32": "vla_32.json",
    "33": "vla_33.json",
    "34": "vla_34.json",
    "35": "vla_35.json",
    "36": "vla_36.json",
    "37": "vla_37.json",
    "38": "engineering_38.json",
    "39": "engineering_39.json",
    "40": "engineering_40.json",
    "41": "engineering_41.json",
    "42": "engineering_42.json",
    "43": "engineering_43.json",
    "44": "engineering_44.json",
    "45": "engineering_45.json",
    "46": "engineering_46.json",
    "47": "engineering_47.json",
    "H01": "hardware_H01.json",
}

REQUIRED_PORTFOLIO_REPORTS = {
    **{chapter: "evidence.json" for chapter in ("01", "02", "03", "04", "05")},
    "11": "evidence.json",
    **{chapter: "evidence.json" for chapter in ("13", "14", "15", "16", "18")},
    **{chapter: "evidence.json" for chapter in ("20", "21", "22", "23")},
    "24": "mpc_vs_lqr_report.md",
    "25": "evidence.json",
    "26": "evidence.json",
    "27": "evidence.json",
    "28": "evidence.json",
    "29": "evidence.json",
    "30": "evidence.json",
    "31": "evidence.json",
    "32": "evidence.json",
    "33": "evidence.json",
    "34": "evidence.json",
    "35": "evidence.json",
    "36": "evidence.json",
    "37": "evidence.json",
    "38": "numerical_parity_report.md",
    "39": "build_reproducibility_report.md",
    "40": "evidence.json",
    "41": "realtime_latency_report.md",
    "42": "engineering_42_report.md",
    "43": "engineering_43_report.md",
    "44": "engineering_44_report.md",
    "45": "engineering_45_report.md",
    "46": "engineering_46_report.md",
    "47": "engineering_47_report.md",
    "H01": "evidence.json",
}

EXPERIMENT_PORTFOLIO_OVERRIDES = {
    ("24", "trajectory_24.json"): "trajectory_optimization.json",
}

# 状态图中文字体候选：Windows 优先 SimHei，Linux/CI 回退到开源 CJK 字体，
# 避免在无 SimHei 的环境里回退到默认拉丁字体导致中文变成豆腐块（并触发 Glyph 缺字告警）。
_STATUS_FONT_CANDIDATES = (
    "SimHei",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "Noto Sans CJK KR",
    "WenQuanYi Zen Hei",
    "WenQuanYi Micro Hei",
    "Droid Sans Fallback",
)


def _resolve_status_font_family() -> str:
    """选取当前平台实际安装的中文字体族名。"""
    available = {font.name for font in font_manager.fontManager.ttflist}
    for name in _STATUS_FONT_CANDIDATES:
        if name in available:
            return name
    return _STATUS_FONT_CANDIDATES[0]


STATUS_FONT_FAMILY = _resolve_status_font_family()


def _plot_has_content(path: Path) -> bool:
    try:
        payload = path.read_bytes()
    except OSError:
        return False
    suffix = path.suffix.lower()
    if suffix == ".png":
        return len(payload) >= 32 and payload.startswith(b"\x89PNG\r\n\x1a\n") and payload[12:16] == b"IHDR"
    if suffix in {".jpg", ".jpeg"}:
        return len(payload) >= 32 and payload.startswith(b"\xff\xd8") and payload.endswith(b"\xff\xd9")
    if suffix == ".svg":
        return len(payload) >= 32 and b"<svg" in payload[:512]
    return len(payload) >= 32


def _log_has_content(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return False
    if not text.strip():
        return False
    try:
        if path.suffix.lower() == ".jsonl":
            records = [json.loads(line) for line in text.splitlines() if line.strip()]
            return bool(records) and all(isinstance(record, dict) and record for record in records)
        if path.suffix.lower() == ".json":
            payload = json.loads(text)
            return isinstance(payload, (dict, list)) and bool(payload)
    except json.JSONDecodeError:
        return False
    return True


def _has_summary(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list)):
        return bool(value)
    return False


def _json_portfolio_is_substantive(data: object, chapter_id: str) -> bool:
    if not isinstance(data, dict):
        return False
    metrics = data.get("metrics")
    explicit_summary = _has_summary(data.get("evidence"))
    referenced_summary = _has_summary(data.get("plots")) and _has_summary(data.get("logs"))
    return (
        data.get("chapter_id") == chapter_id
        and data.get("passed") is True
        and isinstance(metrics, dict)
        and bool(metrics)
        and (explicit_summary or referenced_summary)
    )


def _markdown_portfolio_is_substantive(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    has_title = any(line.startswith("# ") for line in lines)
    has_metrics = any(
        "指标" in line or "metric" in line.lower()
        for line in lines
        if line.startswith("#") or line.startswith("|")
    )
    return len(lines) >= 3 and has_title and has_metrics


def _write_status_plot(path: Path, passed: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"font.sans-serif": [STATUS_FONT_FAMILY], "axes.unicode_minus": False}):
        figure, axis = plt.subplots(figsize=(5.2, 2.2))
        axis.barh(["自动测试"], [1.0 if passed else 0.0], color="#17745a" if passed else "#d36b27")
        axis.set_xlim(0.0, 1.0)
        axis.set_xlabel("通过比例")
        axis.set_title("课程关卡自动验收证据")
        figure.tight_layout()
        figure.savefig(path, dpi=140)
        plt.close(figure)


def _require_experiment_result_file(
    root: Path,
    chapter_id: str,
    filename: str,
    *,
    source_root: Path | None = None,
) -> None:
    path = root / "results" / filename
    if not path.is_file():
        raise RuntimeError(f"关卡 {chapter_id} 缺少专属实验结果：{path}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("chapter_id") != chapter_id or not result.get("passed"):
        raise RuntimeError(f"关卡 {chapter_id} 的专属实验结果未通过")
    if result.get("seed") != 0:
        raise RuntimeError(
            f"关卡 {chapter_id} 的专属实验结果必须使用固定 seed=0，"
            f"当前为 {result.get('seed')!r}"
        )
    evidence_root = source_root.resolve() if source_root is not None else project_root().resolve()
    assessment = assess_experiment_result(result, root=evidence_root)
    if not assessment["valid"]:
        raise RuntimeError(
            f"关卡 {chapter_id} 的专属实验结果无效或源码证据过期: "
            + "; ".join(assessment["errors"])
        )

    # 三重证据 AND 校验：plots、logs、portfolio 三者必须同时满足，缺一即抛 RuntimeError。
    plots = result.get("plots", []) or []
    logs = result.get("logs", []) or []
    missing_categories: list[str] = []
    missing_details: list[str] = []

    # 1) plots 数组非空且所有引用文件真实存在
    if not plots:
        missing_categories.append("plots")
        missing_details.append(f"  - 缺 plots: plots 数组为空（关卡 {chapter_id}）")
    else:
        absent_plots = [
            item
            for item in plots
            if not (evidence_root / item).is_file()
            or not _plot_has_content(evidence_root / item)
        ]
        if absent_plots:
            missing_categories.append("plots")
            for item in absent_plots:
                missing_details.append(f"  - 缺 plots: 引用文件不存在 -> {item}")

    # 2) logs 数组非空且所有引用文件真实存在
    if not logs:
        missing_categories.append("logs")
        missing_details.append(f"  - 缺 logs: logs 数组为空（关卡 {chapter_id}）")
    else:
        absent_logs = [
            item
            for item in logs
            if not (evidence_root / item).is_file()
            or not _log_has_content(evidence_root / item)
        ]
        if absent_logs:
            missing_categories.append("logs")
            for item in absent_logs:
                missing_details.append(f"  - 缺 logs: 引用文件不存在 -> {item}")

    # 3) portfolio 文件存在
    portfolio_name = EXPERIMENT_PORTFOLIO_OVERRIDES.get(
        (chapter_id, filename),
        REQUIRED_PORTFOLIO_REPORTS.get(chapter_id),
    )
    if portfolio_name is None:
        missing_categories.append("portfolio")
        missing_details.append(f"  - 缺 portfolio: 关卡 {chapter_id} 未配置作品集报告文件名")
    else:
        portfolio = root / "portfolio" / chapter_id / portfolio_name
        if not portfolio.is_file():
            missing_categories.append("portfolio")
            missing_details.append(f"  - 缺 portfolio: {portfolio}")
        elif not portfolio.read_text(encoding="utf-8").strip():
            missing_categories.append("portfolio")
            missing_details.append(f"  - portfolio 内容为空: {portfolio}")
        elif portfolio.suffix.lower() == ".json":
            try:
                portfolio_data = json.loads(portfolio.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                missing_categories.append("portfolio")
                missing_details.append(f"  - portfolio 不是有效 JSON: {portfolio}")
            else:
                if not _json_portfolio_is_substantive(portfolio_data, chapter_id):
                    missing_categories.append("portfolio")
                    missing_details.append(f"  - portfolio 内容为空或缺少关卡、通过状态、指标、证据摘要: {portfolio}")
        elif portfolio.suffix.lower() in {".md", ".markdown"}:
            if not _markdown_portfolio_is_substantive(portfolio.read_text(encoding="utf-8")):
                missing_categories.append("portfolio")
                missing_details.append(f"  - portfolio Markdown 缺少标题或指标: {portfolio}")

    if missing_categories:
        detail = "\n".join(missing_details)
        raise RuntimeError(
            f"关卡 {chapter_id} 的专属实验证据不完整，缺失类别: "
            f"{', '.join(missing_categories)}\n{detail}"
        )


def _require_experiment_evidence(
    root: Path,
    chapter_id: str,
    *,
    source_root: Path | None = None,
) -> None:
    configured = REQUIRED_EXPERIMENT_RESULTS.get(chapter_id)
    if configured is None:
        return
    filenames = (configured,) if isinstance(configured, str) else tuple(configured)
    for filename in filenames:
        _require_experiment_result_file(
            root,
            chapter_id,
            filename,
            source_root=source_root,
        )


def run_chapter_checkpoint(
    chapter_id: str,
    output_root: str | Path = "outputs",
    *,
    learner_completion: bool = True,
    completed_chapters: set[str] | None = None,
    source_root: str | Path | None = None,
) -> Path:
    """运行关卡绑定的真实测试，并同时保存日志、图表和结果契约。"""

    manifest = load_course_manifest()
    chapter = next((item for item in manifest["chapters"] if item["id"] == chapter_id), None)
    if chapter is None:
        raise KeyError(f"未知关卡: {chapter_id}")
    if chapter["status"] != "ready" or chapter_id not in TEST_TARGETS:
        raise RuntimeError(f"关卡 {chapter_id} 尚未建设完成，不能标记为完成")
    if learner_completion:
        missing = set(chapter["prerequisites"]) - set(completed_chapters or set())
        if missing:
            raise RuntimeError(f"关卡 {chapter_id} 的学习者先修未完成: {', '.join(sorted(missing))}")

    root = Path(output_root)
    if not root.is_absolute():
        root = project_root() / root
    evidence_root = Path(source_root).resolve() if source_root is not None else project_root().resolve()
    _require_experiment_evidence(root, chapter_id, source_root=evidence_root)
    log_path = root / "logs" / f"checkpoint_{chapter_id}.log"
    plot_path = root / "plots" / f"checkpoint_{chapter_id}.png"
    result_path = root / "results" / f"checkpoint_{chapter_id}.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    targets = TEST_TARGETS[chapter_id].split()
    command = [sys.executable, "-m", "pytest", "-q", *targets]
    completed = subprocess.run(command, cwd=project_root(), capture_output=True, text=True, check=False)
    log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    passed = completed.returncode == 0
    _write_status_plot(plot_path, passed)
    return write_experiment_result(
        result_path,
        chapter_id=chapter_id,
        seed=0,
        config={"test_targets": targets, "command": command},
        metrics={"test_exit_code": float(completed.returncode)},
        pass_conditions={"test_exit_code": {"operator": "==", "value": 0}},
        plots=[str(plot_path)],
        logs=[str(log_path)],
        root=evidence_root,
    )
