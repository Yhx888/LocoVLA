"""测试教程目录结构（tutorials/v2/）一致性。

覆盖场景：
- 教程章节目录与课程清单一致
- 每章 README 与配置文件存在
- 章节编号与先修关系符合 manifest
"""
import json
from pathlib import Path

from upkie_mujoco_course.course.manifest import load_course_manifest


REQUIRED_SECTIONS = [
    "## 岗位任务",
    "## 学习目标",
    "## 前置关卡",
    "## 先观察现象",
    "## 直觉与概念",
    "## 教科书级展开",
    "## 动手检查点",
    "## 可视化证据",
    "## 故障诊断挑战",
    "## 三档任务",
    "## 复盘与面试",
    "## 下一关",
]


def test_every_manifest_chapter_has_unique_structured_v2_tutorial():
    manifest = load_course_manifest()
    paths = [chapter["tutorial"] for chapter in manifest["chapters"]]
    assert len(paths) == len(set(paths)) == 58
    for chapter in manifest["chapters"]:
        path = Path(chapter["tutorial"])
        assert path.is_file(), path
        text = path.read_text(encoding="utf-8")
        for section in REQUIRED_SECTIONS:
            assert section in text, f"{path}: {section}"
        expected_status = "建设状态：可执行" if chapter["status"] == "ready" else "建设状态：规划中"
        assert expected_status in text


def test_foundation_tutorials_are_curated_and_evidence_grounded():
    metric_markers = {
        "01": "0.0041333542482888674",
        "02": "1.0563434493906498",
        "03": "1.1857187100668868e-16",
        "04": "1.7772987661132813",
        "05": "2.6353178251800995",
    }
    for chapter_id, marker in metric_markers.items():
        text = Path(f"tutorials/v2/{chapter_id}/README.md").read_text(encoding="utf-8")
        assert len(text) > 3_500
        assert len(text.splitlines()) > 180
        assert f"python scripts/run_foundation_lab.py --chapter {chapter_id}" in text
        assert marker in text
        assert "假设" in text and "失效条件" in text
        assert f"outputs/portfolio/{chapter_id}" in text
        assert "明确拒绝验收" not in text

    generator = Path("scripts/tools/generate_v2_tutorials.py").read_text(encoding="utf-8")
    for chapter_id in ["00", "01", "02", "03", "04", "05"]:
        assert f'"{chapter_id}"' in generator.split("CURATED_CHAPTERS", 1)[1].split("}", 1)[0]


def test_classical_control_tutorials_are_curated_and_evidence_grounded():
    metric_markers = {
        "13": "12.635333503310314",
        "14": "3.5545975322265626",
        "15": "4.845606967001785",
        "16": "0.09987027976806588",
        "18": "0.5301153714449112",
    }
    generator = Path("scripts/tools/generate_v2_tutorials.py").read_text(encoding="utf-8")
    curated = generator.split("CURATED_CHAPTERS", 1)[1].split("}", 1)[0]
    for chapter_id, marker in metric_markers.items():
        text = Path(f"tutorials/v2/{chapter_id}/README.md").read_text(encoding="utf-8")
        assert len(text) > 3_500
        assert f"python scripts/run_classical_control_lab.py --chapter {chapter_id}" in text
        assert marker in text
        assert "假设" in text and "失效" in text
        assert f"outputs/portfolio/{chapter_id}" in text
        assert "明确拒绝验收" not in text
        assert f'"{chapter_id}"' in curated


def test_chapter_21_describes_real_mujoco_sensor_fusion_evidence():
    text = Path("tutorials/v2/21/README.md").read_text(encoding="utf-8")

    for marker in [
        "mujoco_sensordata",
        "imu_orientation",
        "imu_accelerometer",
        "imu_gyroscope",
        "left_wheel_velocity",
        "right_wheel_velocity",
        'result["metrics"]',
        "value:.6f",
        'metrics["ekf_rmse_improvement_ratio"] >= 1.2',
        'metrics["ukf_rmse_improvement_ratio"] >= 1.2',
        'metrics["closed_loop_max_abs_pitch_rad"] <= 0.5',
        "301",
        "truth_usage",
        "metrics_only",
        "UKF",
        "outputs/plots/estimation_21.png",
        "outputs/logs/estimation_21.json",
        "outputs/results/estimation_21.json",
        "outputs/portfolio/21/evidence.json",
    ]:
        assert marker in text
    for stale_snapshot in ["0.034259", "0.011215", "0.010753", "3.054648", "3.186002"]:
        assert stale_snapshot not in text

    assert "raw_nonlinear_measurement_rmse_rad" not in text
    assert "minimum_measurement_jacobian_magnitude" not in text
    assert "arcsin" not in text.lower()
    for full_precision in [
        "0.034259354196021274",
        "0.011215481717751571",
        "0.010753085947258743",
    ]:
        assert full_precision not in text
    assert "四类产物证据" in text
    assert "## 验证命令" in text


def test_chapter_19_example_uses_seeded_balancing_closed_loop():
    text = Path("tutorials/v2/19/README.md").read_text(encoding="utf-8")

    for marker in [
        "WheelBalancerController",
        "controller.compute_action(runner, runner.time)",
        "seed = 19",
        "rng = np.random.default_rng(seed)",
        '"seed": seed',
        'state["base_height"] <= -0.35',
    ]:
        assert marker in text
    assert "runner.step(np.zeros(runner.model.nu))" not in text
    assert "np.random.normal" not in text


def test_chapters_23_24_lock_optimization_and_mpc_acceptance_facts():
    chapter_23 = Path("tutorials/v2/23/README.md").read_text(encoding="utf-8")
    chapter_24 = Path("tutorials/v2/24/README.md").read_text(encoding="utf-8")

    for marker in [
        "KKT",
        "对偶",
        "kkt_stationarity_residual",
        "kkt_complementarity_residual",
        "duality_gap",
    ]:
        assert marker in chapter_23

    for marker in [
        "MuJoCo 闭环",
        "MPCSolveError",
        "test_mpc_rejects_infeasible_state_constraint_without_unconstrained_fallback",
        "禁止静默",
        "直接配点",
        "单次打靶",
    ]:
        assert marker in chapter_24


def test_every_required_tutorial_contains_all_manifest_commands():
    manifest = load_course_manifest()
    for chapter in manifest["chapters"]:
        if chapter["id"].startswith("H"):
            continue
        text = Path(chapter["tutorial"]).read_text(encoding="utf-8")
        for command in chapter["commands"]:
            assert command in text, f"{chapter['tutorial']}: 缺少命令 {command}"


def test_chapter_42_manifest_command_supplies_required_log_path():
    manifest = load_course_manifest()
    chapter = next(item for item in manifest["chapters"] if item["id"] == "42")
    command = (
        "python scripts/run_engineering_lab_42.py "
        "--log-path outputs/logs/engineering_42_log.jsonl"
    )

    assert command in chapter["commands"]
    tutorial = Path(chapter["tutorial"]).read_text(encoding="utf-8")
    assert command in tutorial


def test_vla_architecture_chapter_contains_renderable_data_flow_diagram():
    text = Path("tutorials/v2/32/README.md").read_text(encoding="utf-8")

    assert "```mermaid" in text or "<svg" in text
    assert "10 Hz" in text
    assert "100 Hz" in text
    assert "RGB-D" in text
    assert "6 维" in text
    assert "安全" in text


def test_learning_control_tutorials_match_current_rl_implementation_and_evidence():
    chapter_25 = Path("tutorials/v2/25/README.md").read_text(encoding="utf-8")
    for marker in [
        "observation_dim=15",
        "action_dim=6",
        "reset_reproducibility_max_abs=0.0",
        "outputs/plots/rl_25.png",
        "outputs/logs/rl_25.json",
        "outputs/results/rl_25.json",
    ]:
        assert marker in chapter_25
    assert "outputs/plots/checkpoint_25.png" not in chapter_25

    chapter_26 = Path("tutorials/v2/26/README.md").read_text(encoding="utf-8")
    for marker in [
        "target_standing_height",
        "height_error",
        "reward_mean=1.8772752006406745",
        "height_mean=0.9843925478023553",
        "outputs/plots/rl_26.png",
    ]:
        assert marker in chapter_26
    assert "当前实现鼓励基座高度接近 0" not in chapter_26

    chapter_27 = Path("tutorials/v2/27/README.md").read_text(encoding="utf-8")
    for marker in [
        "320",
        "128",
        "1.654573298518158",
        "outputs/plots/rl_27.png",
        "python scripts/run_rl_lab.py --chapter 27",
        "python scripts/course_checkpoint.py --chapter 27",
    ]:
        assert marker in chapter_27

    chapter_28 = Path("tutorials/v2/28/README.md").read_text(encoding="utf-8")
    for marker in [
        "WheelTorqueStandingEnv",
        "training_mode=wheel_torque",
        "50000",
        "ppo_standing_latest.metadata.json",
        "ppo_return_mean=358.25532205584386",
        "ppo_success_rate=1.0",
        "ppo_fall_rate=0.0",
        "ppo_max_abs_pitch_rad=0.3074230982798487",
        "outputs/plots/rl_28.png",
    ]:
        assert marker in chapter_28
    assert "outputs/plots/checkpoint_28.png" not in chapter_28

    chapter_29 = Path("tutorials/v2/29/README.md").read_text(encoding="utf-8")
    for marker in [
        "200",
        "field_count=8.0",
        "runtime_verified_field_count=8.0",
        "coverage_ratio=1.0",
        "reset_step_consistency_max_abs=0.0",
        "seed_reproducibility_max_abs=0.0",
        "mean_range_utilization=0.987921790987458",
        "audit_source=mujoco_model_and_environment_state",
        "第 29 关运行时审计",
        "第 31 关 Sim2Real",
        "inertia_scale",
        "com_offset_m",
        "joint_damping",
        "actuator_strength_scale",
        "evaluate_policy(",
        "return_records=True",
        "outputs/plots/rl_29.png",
    ]:
        assert marker in chapter_29
    assert 'PPO.load("outputs/checkpoints/ppo_standing_latest.zip", env=env_heavy)' not in chapter_29
    assert '"success_rate": sum(1 for r in rewards if r > -50)' not in chapter_29
    assert "standing_env_reset_and_step" not in chapter_29
    assert "第 29/31 关固定" not in chapter_29

    chapter_30 = Path("tutorials/v2/30/README.md").read_text(encoding="utf-8")
    for marker in [
        "ResidualStandingEnv",
        "ppo_residual_latest.zip",
        "ppo_residual_latest.metadata.json",
        "training_mode=residual",
        "--mode residual",
        "--residual-scale 0.05",
        "10000",
        "10 N",
        "residual_return_gap=4.256819603667282",
        "residual_max_abs_pitch_rad=0.15424480121590495",
        "outputs/plots/rl_30.png",
    ]:
        assert marker in chapter_30
    assert "--mode residual --model outputs/checkpoints/ppo_standing_latest.zip" not in chapter_30
    assert 'PPO.load("outputs/checkpoints/ppo_standing_latest.zip", env=env)' not in chapter_30

    chapter_31 = Path("tutorials/v2/31/README.md").read_text(encoding="utf-8")
    for marker in [
        "0.4433033573851295",
        "0.8 rad",
        "-0.35 m",
        "seed `29`",
        "不等于安全认证",
        "randomized_failure_episodes",
        "bootstrap_ci_low",
        "bootstrap_ci_high",
        "outputs/plots/rl_31.png",
    ]:
        assert marker in chapter_31


def test_vla_tutorials_match_real_demonstration_and_closed_loop_evidence():
    chapter_35 = Path("tutorials/v2/35/README.md").read_text(encoding="utf-8")
    chapter_36 = Path("tutorials/v2/36/README.md").read_text(encoding="utf-8")
    chapter_37 = Path("tutorials/v2/37/README.md").read_text(encoding="utf-8")

    for marker in ["6 个", "真实 MuJoCo RGB-D", "[forward_velocity, yaw_rate, stop]"]:
        assert marker in chapter_35
    assert "至少 50 个 episode" not in chapter_35
    assert "收集 50 个 episode" not in chapter_35

    assert "outputs/checkpoints/vla_bc_policy.npz" in chapter_36
    assert "episodes=6" in chapter_36
    assert "samples=3" not in chapter_36

    for marker in [
        "真实 MuJoCo 闭环",
        "policy_path=\"outputs/checkpoints/vla_bc_policy.npz\"",
        "9260",
        "100%",
        "0.180189 m",
        "0 步",
    ]:
        assert marker in chapter_37
    assert "合成场景" not in chapter_37


def test_chapter_35_scenario_matrix_matches_three_colors_and_two_seeds():
    text = Path("tutorials/v2/35/README.md").read_text(encoding="utf-8")

    for marker in [
        '("前往红色目标并停车", "red", 0)',
        '("前往红色目标并停车", "red", 1)',
        '("Navigate to the green target and stop", "green", 10)',
        '("Navigate to the green target and stop", "green", 11)',
        '("Navigate to the blue target and stop", "blue", 20)',
        '("Navigate to the blue target and stop", "blue", 21)',
    ]:
        assert marker in text
    assert "red_en" not in text
    assert "blue_en" not in text


def test_chapter_35_describes_scripted_expert_as_limited_rule_baseline():
    text = Path("tutorials/v2/35/README.md").read_text(encoding="utf-8")

    assert "确定性规则基线" in text
    assert "仅在已验证场景" in text
    assert "不会犯错" not in text
    assert "表现完美" not in text


def test_chapter_32_distinguishes_physics_integration_from_action_updates():
    text = Path("tutorials/v2/32/README.md").read_text(encoding="utf-8")

    for marker in [
        "physics timestep = 0.002 s（500 Hz）",
        "frame_skip = 5",
        "action/control update = 0.01 s（100 Hz）",
        "500 Hz 只负责 MuJoCo 物理积分",
        "100 Hz 才更新一次动作和安全控制输出",
    ]:
        assert marker in text
    assert "控制层 (500 Hz)" not in text
    assert "| 控制层 | 500 Hz |" not in text
    assert "控制 2 ms" not in text


def test_chapter_36_matches_current_local_1nn_checkpoint_behavior():
    text = Path("tutorials/v2/36/README.md").read_text(encoding="utf-8")

    for marker in ["22 维", "22 x 6", "局部 1-NN 动作检索", "兼容线性权重路径"]:
        assert marker in text
    for stale in ["10 x 6", "每步 10 维", "特征 10 维", "proprioception[:3]"]:
        assert stale not in text


def test_chapter_37_reports_all_fixed_closed_loop_safety_metrics():
    text = Path("tutorials/v2/37/README.md").read_text(encoding="utf-8")
    result = json.loads(Path("outputs/results/vla_37.json").read_text(encoding="utf-8"))

    assert "run_vla_lab(\"37\"" in text
    assert '"立即停止"' in text
    assert "9 个专属指标" in text
    for name, value in result["metrics"].items():
        assert f"{name}={float(value):.6f}" in text
    assert "unseen_combination_success_rate" not in text
    assert "mean_inference_latency_ms" not in text


def test_engineering_tutorials_separate_course_readiness_from_learner_graduation():
    chapters = {
        chapter_id: Path(f"tutorials/v2/{chapter_id}/README.md").read_text(encoding="utf-8")
        for chapter_id in range(38, 48)
    }
    combined = "\n".join(chapters.values())

    for forbidden in ["尚未建设完成", "明确拒绝验收", "自动变为 1.0"]:
        assert forbidden not in combined
    for marker in ["课程工程就绪不等于学习者毕业", "仓库外部人工答辩"]:
        assert marker in chapters[45]
        assert marker in chapters[47]

    for marker in [
        "arXiv:2308.13205",
        "arXiv:2109.11978",
        "arXiv:2307.15818",
        "M1 滑动统计",
        "M2 先修关系图",
        "M3 受限网格规划",
        "M4 实验调度",
    ]:
        assert marker in chapters[47]
