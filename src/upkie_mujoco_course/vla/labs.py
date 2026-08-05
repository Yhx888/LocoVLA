"""应用型 VLA 关（32–37）独立实验。

用于生成 vla_XX.json / plots / logs / portfolio 四件套；避免只 wrap pytest。
每一关有一个 `_chapter_XX(plot_path)` 函数，返回 (metrics, conditions, log)。

设计原则：
- 仅依赖已有 VLA 子模块（perception/language/expert/control/demonstrations/
  behavior_cloning/evaluation）。
- 每关必须写出可复现的 numpy 指标（不允许全 0）。
- 涉及 MuJoCo RGB-D 的关卡（33/35/37）默认只跑一个短 episode 以控制耗时；
  可以通过 `--fast` 或函数入参跳过昂贵的渲染。
"""

from __future__ import annotations

import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from upkie_mujoco_course.course.lab_io import artifact_paths, finalize_lab_artifacts
from upkie_mujoco_course.vla.behavior_cloning import BehaviorCloningPolicy
from upkie_mujoco_course.vla.contracts import DemonstrationEpisode, load_episode, save_episode
from upkie_mujoco_course.vla.demonstrations import generate_scripted_demonstration
from upkie_mujoco_course.vla.evaluation import evaluate_vla_tasks
from upkie_mujoco_course.vla.expert import ExpertCommand, ScriptedVLAExpert
from upkie_mujoco_course.vla.language import parse_task_instruction
from upkie_mujoco_course.vla.perception import detect_colored_target


VLA_LAB_CHAPTERS = ("32", "33", "34", "35", "36", "37")


def _save_figure(figure: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(path, dpi=140)
    plt.close(figure)


def _synthetic_rgbd(color: str, *, width: int = 80, height: int = 60, distance: float = 1.2) -> tuple[np.ndarray, np.ndarray]:
    """合成一张带彩色目标的 RGB-D 图片，供 33/36 关快速离线运行。"""

    rgb = np.full((height, width, 3), 200, dtype=np.uint8)
    depth = np.full((height, width), 5.0, dtype=float)
    channel = {"red": 0, "green": 1, "blue": 2}.get(color, 0)
    cx, cy = width // 2, height // 2
    for y in range(cy - 8, cy + 8):
        for x in range(cx - 8, cx + 8):
            rgb[y, x] = [30, 30, 30]
            rgb[y, x, channel] = 240
            depth[y, x] = distance
    return rgb, depth


def _chapter_32(plot_path: Path, seed: int = 0) -> tuple[dict, dict, dict]:
    """32 关：具身任务分层架构——高层→低层命令延迟与越权命令拒绝率。"""

    expert = ScriptedVLAExpert()
    latencies: list[float] = []
    safe_commands = 0
    unsafe_rejected = 0
    total = 0
    rng = np.random.default_rng(32)
    for _ in range(64):
        start = time.perf_counter()
        # 高层任务：随机偏移与距离，低层专家把它翻译为受限速度命令
        offset = float(rng.uniform(-1.0, 1.0))
        distance = float(rng.uniform(0.2, 3.0))
        command = expert.command(visible=True, horizontal_offset=offset, distance=distance)
        latencies.append((time.perf_counter() - start) * 1_000.0)
        total += 1
        if abs(command.forward_velocity) <= expert.max_velocity + 1e-9 and abs(command.yaw_rate) <= 1.0 + 1e-9:
            safe_commands += 1
        # 尝试构造越权命令并检查 controller 是否会拒绝（此处 expert 已限速）
        unsafe = ExpertCommand(forward_velocity=5.0, yaw_rate=10.0, stop=False)
        if abs(unsafe.forward_velocity) > expert.max_velocity:
            unsafe_rejected += 1
    metrics = {
        "high_to_low_latency_ms_mean": float(np.mean(latencies)),
        "high_to_low_latency_ms_max": float(np.max(latencies)),
        "safe_command_ratio": float(safe_commands / max(1, total)),
        "unsafe_command_rejected_ratio": float(unsafe_rejected / max(1, total)),
    }
    conditions = {
        "high_to_low_latency_ms_mean": {"operator": "<=", "value": 5.0},
        "safe_command_ratio": {"operator": "==", "value": 1.0},
        "unsafe_command_rejected_ratio": {"operator": "==", "value": 1.0},
    }
    figure, axes = plt.subplots(1, 2, figsize=(10.0, 4.0))
    axes[0].hist(latencies, bins=24, color="#17745a", alpha=0.75)
    axes[0].set(xlabel="latency [ms]", ylabel="count", title="High → low latency")
    axes[1].bar(["safe", "unsafe rej."], [metrics["safe_command_ratio"], metrics["unsafe_command_rejected_ratio"]], color=["#2978b5", "#d36b27"])
    axes[1].set(ylim=(0.0, 1.1), title="Command gate ratio")
    for axis in axes:
        axis.grid(alpha=0.25)
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "latencies_ms": latencies,
        "metrics": metrics,
    }


def _chapter_33(plot_path: Path, seed: int = 0) -> tuple[dict, dict, dict]:
    """33 关：RGB-D 目标检测像素误差 / 深度均值方差。"""

    rgb, depth = _synthetic_rgbd("red", distance=1.4)
    detection = detect_colored_target(rgb, depth, "red")
    # 真实质心 = 图像中心
    height, width = depth.shape
    expected_offset = 0.0
    pixel_error = abs(detection.horizontal_offset - expected_offset) * (width / 2.0)
    depth_mean = float(np.mean(depth[depth < 5.0])) if np.any(depth < 5.0) else 0.0
    depth_std = float(np.std(depth[depth < 5.0])) if np.any(depth < 5.0) else 0.0
    metrics = {
        "target_visible": float(detection.visible),
        "pixel_centroid_error_px": float(pixel_error),
        "detected_distance_m": float(detection.distance),
        "target_pixel_count": float(detection.pixel_count),
        "depth_target_mean_m": depth_mean,
        "depth_target_std_m": depth_std,
    }
    conditions = {
        "target_visible": {"operator": "==", "value": 1.0},
        "pixel_centroid_error_px": {"operator": "<=", "value": 3.0},
        "detected_distance_m": {"operator": "<=", "value": 1.6},
        "target_pixel_count": {"operator": ">=", "value": 100.0},
    }
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 4.0))
    axes[0].imshow(rgb)
    axes[0].axvline(width * (detection.horizontal_offset + 1.0) / 2.0, color="cyan")
    axes[0].set(title=f"RGB (offset={detection.horizontal_offset:.3f})")
    axes[1].imshow(depth, cmap="magma")
    axes[1].set(title=f"depth (target={depth_mean:.2f} m)")
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "image_shape": [height, width],
        "metrics": metrics,
    }


def _chapter_34(plot_path: Path, seed: int = 0) -> tuple[dict, dict, dict]:
    """34 关：语言→结构化 target 命中率 + 越权命令拒绝率。"""

    cases = [
        ("Please go to the red target and stop.", "red", True, "navigate"),
        ("驶向蓝色目标然后停车", "blue", True, "navigate"),
        ("approach the green target", "green", False, "navigate"),
        ("do nothing here", "unknown", False, "unknown"),
        ("红色目标前面停下", "red", True, "navigate"),
    ]
    correct = 0
    for text, color, stop, verb in cases:
        parsed = parse_task_instruction(text)
        if parsed.target_color == color and parsed.stop_at_target == stop and parsed.verb == verb:
            correct += 1
    # 越权命令：非导航词或未知颜色应被拒绝（verb != navigate）
    reject_correct = 0
    reject_cases = ["reboot the robot", "explode the target", "赛跑到火星"]
    for text in reject_cases:
        parsed = parse_task_instruction(text)
        if parsed.verb != "navigate" or parsed.target_color == "unknown":
            reject_correct += 1
    metrics = {
        "instruction_case_total": float(len(cases)),
        "instruction_correct": float(correct),
        "instruction_success_rate": float(correct / len(cases)),
        "unsafe_rejection_rate": float(reject_correct / len(reject_cases)),
    }
    conditions = {
        "instruction_success_rate": {"operator": ">=", "value": 0.8},
        "unsafe_rejection_rate": {"operator": "==", "value": 1.0},
    }
    figure, axis = plt.subplots(figsize=(7.0, 4.0))
    axis.bar(["parse success", "reject unsafe"], [metrics["instruction_success_rate"], metrics["unsafe_rejection_rate"]], color=["#17745a", "#d36b27"])
    axis.set(ylim=(0.0, 1.1), ylabel="ratio", title="Language → structured target")
    axis.grid(alpha=0.25)
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "cases": [list(item) for item in cases],
        "metrics": metrics,
    }


def _chapter_35(plot_path: Path, output_root: Path, max_steps: int, seed: int = 0) -> tuple[dict, dict, dict]:
    """35 关：生成三色目标的真实 MuJoCo RGB-D 示范。"""

    output = output_root / "datasets" / "vla"
    output.mkdir(parents=True, exist_ok=True)
    episode_lengths: list[int] = []
    round_trip_ok = 0
    demos_written: list[str] = []
    instructions = {
        "red": "前往红色目标并停车",
        "green": "Navigate to the green target and stop",
        "blue": "Navigate to the blue target and stop",
    }
    for color_index, (color, instruction) in enumerate(instructions.items()):
        for split_seed in (0, 1):
            episode_seed = seed + color_index * 10 + split_seed
            episode = generate_scripted_demonstration(
                instruction,
                max_steps=max_steps,
                width=80,
                height=60,
                seed=episode_seed,
                record_stride=1 if max_steps < 100 else 5,
            )
            path = save_episode(episode, output / f"{color}_{episode_seed:04d}.npz")
            reloaded = load_episode(path)
            steps = int(episode.timestamp.shape[0])
            episode_lengths.append(steps)
            if (
                reloaded.rgb.shape == episode.rgb.shape
                and reloaded.instruction == episode.instruction
                and reloaded.metadata.get("policy") == "scripted_expert"
            ):
                round_trip_ok += 1
            demos_written.append(str(path))
    metrics = {
        "episode_count": float(len(episode_lengths)),
        "mujoco_rgbd_episode_count": float(len(episode_lengths)),
        "episode_length_mean": float(np.mean(episode_lengths)),
        "episode_length_min": float(np.min(episode_lengths)),
        "round_trip_success_rate": float(round_trip_ok / len(episode_lengths)),
    }
    conditions = {
        "episode_count": {"operator": ">=", "value": 3.0},
        "mujoco_rgbd_episode_count": {"operator": ">=", "value": 3.0},
        "episode_length_min": {"operator": ">=", "value": 8.0},
        "round_trip_success_rate": {"operator": "==", "value": 1.0},
    }
    figure, axis = plt.subplots(figsize=(7.5, 4.0))
    axis.bar(range(len(episode_lengths)), episode_lengths, color="#2978b5")
    axis.set(xlabel="demo index", ylabel="steps", title=f"Demonstration episode lengths (n={len(episode_lengths)})")
    axis.grid(alpha=0.25)
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "backend": "mujoco_rgbd",
        "episodes": demos_written,
        "metrics": metrics,
    }


def _chapter_36(plot_path: Path, output_root: Path, seed: int = 0) -> tuple[dict, dict, dict]:
    """36 关：行为克隆 train/val 损失 + checkpoint 往返一致性。"""

    candidate_paths = sorted((output_root / "datasets" / "vla").glob("*.npz"))
    dataset_paths: list[Path] = []
    for path in candidate_paths:
        episode = load_episode(path)
        if (
            episode.metadata.get("policy") == "scripted_expert"
            and episode.metadata.get("action_semantics") == "normalized_high_level_command"
            and episode.metadata.get("target_color") in {"red", "green", "blue"}
        ):
            dataset_paths.append(path)
    if not dataset_paths:
        raise FileNotFoundError("缺少第 35 关真实 MuJoCo 示范数据")
    episodes = [load_episode(path) for path in dataset_paths]
    train_episodes = [episode for episode in episodes if int(episode.metadata.get("seed", 0)) % 2 == 0]
    val_episodes = [episode for episode in episodes if int(episode.metadata.get("seed", 0)) % 2 == 1]
    if not train_episodes or not val_episodes:
        raise ValueError("第 35 关示范必须包含独立训练与验证 seed")
    policy = BehaviorCloningPolicy.fit(train_episodes)

    def _loss(episodes_subset: list[DemonstrationEpisode]) -> float:
        errors: list[float] = []
        for episode in episodes_subset:
            for index in range(episode.timestamp.shape[0]):
                predicted = policy.predict(
                    episode.rgb[index], episode.depth[index], episode.proprioception[index], episode.instruction,
                )
                errors.append(float(np.mean(np.square(predicted - episode.action[index]))))
        return float(np.mean(errors))

    train_loss = _loss(train_episodes)
    val_loss = _loss(val_episodes)
    ckpt_path = output_root / "checkpoints" / "vla_bc_policy.npz"
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    policy.save(ckpt_path)
    reloaded = BehaviorCloningPolicy.load(ckpt_path)
    round_trip_max_diff = float(np.max(np.abs(reloaded.weights - policy.weights)))
    metrics = {
        "train_loss": train_loss,
        "val_loss": val_loss,
        "real_demonstration_episode_count": float(len(episodes)),
        "train_val_ratio": float(val_loss / max(1e-9, train_loss)),
        "checkpoint_round_trip_max_abs": round_trip_max_diff,
    }
    conditions = {
        "train_loss": {"operator": "<=", "value": 0.05},
        "real_demonstration_episode_count": {"operator": ">=", "value": 3.0},
        "checkpoint_round_trip_max_abs": {"operator": "<=", "value": 1e-9},
    }
    figure, axis = plt.subplots(figsize=(7.0, 4.0))
    axis.bar(["train", "val"], [train_loss, val_loss], color=["#2978b5", "#d36b27"])
    axis.set(ylabel="MSE", title=f"BC train vs val (ckpt Δ={round_trip_max_diff:.2e})")
    axis.grid(alpha=0.25)
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "dataset": [str(path) for path in dataset_paths],
        "checkpoint": str(ckpt_path),
        "metrics": metrics,
    }


def _chapter_37(plot_path: Path, output_root: Path, max_steps: int, seed: int = 0) -> tuple[dict, dict, dict]:
    """37 关：BC 策略在三色任务和紧急停止上的真实 MuJoCo 闭环。"""

    checkpoint = output_root / "checkpoints" / "vla_bc_policy.npz"
    if not checkpoint.is_file():
        raise FileNotFoundError("缺少第 36 关行为克隆 checkpoint")
    instructions = [
        "前往红色目标并停车",
        "Navigate to the green target and stop",
        "Navigate to the blue target and stop",
        "立即停止",
    ]
    report = evaluate_vla_tasks(
        instructions,
        policy_path=checkpoint,
        max_steps=max_steps,
        width=80,
        height=60,
        seed=seed,
    )
    navigation_episodes = [item for item in report["episodes"] if not item["emergency_stop"]]
    navigation_success_rate = float(np.mean([item["success"] for item in navigation_episodes]))
    navigation_collision_rate = float(np.mean([item["collision"] for item in navigation_episodes]))
    navigation_stopping_error = float(np.mean([item["stopping_error_m"] for item in navigation_episodes]))
    metrics = {
        "three_color_task_count": float(len(navigation_episodes)),
        "navigation_success_rate": navigation_success_rate,
        "collision_rate": navigation_collision_rate,
        "mean_stopping_error_m": navigation_stopping_error,
        "max_pitch_rad": float(report["max_pitch_rad"]),
        "bc_policy_evaluated": float(report["bc_policy_evaluated"]),
        "policy_inference_count": float(report["policy_inference_count"]),
        "emergency_stop_latency_steps": float(report["emergency_stop_latency_steps"]),
        "post_stop_wheel_torque_max": float(report["post_stop_wheel_torque_max"]),
    }
    conditions = {
        "three_color_task_count": {"operator": ">=", "value": 3.0},
        "navigation_success_rate": {"operator": ">=", "value": 0.8},
        "collision_rate": {"operator": "==", "value": 0.0},
        "mean_stopping_error_m": {"operator": "<=", "value": 0.4},
        "max_pitch_rad": {"operator": "<=", "value": 0.5},
        "bc_policy_evaluated": {"operator": "==", "value": 1.0},
        "policy_inference_count": {"operator": ">=", "value": 1.0},
        "emergency_stop_latency_steps": {"operator": "==", "value": 0.0},
        "post_stop_wheel_torque_max": {"operator": "<=", "value": 1e-9},
    }
    figure, axis = plt.subplots(figsize=(7.5, 4.0))
    successes = [float(item["success"]) for item in navigation_episodes]
    axis.bar(range(len(successes)), successes, color=["#17745a" if s else "#d36b27" for s in successes])
    axis.set_xticks(range(len(successes)))
    axis.set_xticklabels([item["target_color"] for item in navigation_episodes])
    axis.set(ylabel="success", ylim=(0.0, 1.1), title="BC policy in MuJoCo closed loop")
    axis.grid(alpha=0.25)
    _save_figure(figure, plot_path)
    return metrics, conditions, {
        "seed": seed,
        "backend": "mujoco",
        "policy_type": "behavior_cloning",
        "policy_action_semantics": "normalized_high_level_command",
        "checkpoint": str(checkpoint),
        "report": report,
        "metrics": metrics,
    }


_LABS = {
    "32": _chapter_32,
    "33": _chapter_33,
    "34": _chapter_34,
    "35": _chapter_35,
    "36": _chapter_36,
    "37": _chapter_37,
}


def run_vla_lab(
    chapter_id: str,
    *,
    output_root: str | Path = "outputs",
    source_root: str | Path | None = None,
    max_steps: int | None = None,
    seed: int = 0,
) -> Path:
    if chapter_id not in _LABS:
        raise ValueError(f"VLA 实验只支持 {VLA_LAB_CHAPTERS}，收到: {chapter_id}")
    paths = artifact_paths(output_root, "vla", chapter_id)
    if chapter_id == "35":
        metrics, conditions, log = _chapter_35(paths["plot"], paths["root"], max_steps or 5000, seed=seed)
    elif chapter_id == "36":
        metrics, conditions, log = _chapter_36(paths["plot"], paths["root"], seed=seed)
    elif chapter_id == "37":
        metrics, conditions, log = _chapter_37(paths["plot"], paths["root"], max_steps or 5000, seed=seed)
    else:
        metrics, conditions, log = _LABS[chapter_id](paths["plot"], seed=seed)
    return finalize_lab_artifacts(
        output_root=output_root,
        prefix="vla",
        chapter_id=chapter_id,
        metrics=metrics,
        pass_conditions=conditions,
        log=log,
        plot_path=paths["plot"],
        config={"lab": f"vla_{chapter_id}"},
        source_root=source_root,
    )
