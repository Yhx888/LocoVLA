"""测试 VLA（Vision-Language-Action）模型接口。

覆盖场景：
- 演示回合（DemonstrationEpisode）保存与加载
- 行为克隆策略（BehaviorCloningPolicy）前向推理
- 脚本化 VLA 专家（ScriptedVLAExpert）输出契约
"""
import json

import numpy as np
import pytest

from upkie_mujoco_course.vla.contracts import DemonstrationEpisode, load_episode, save_episode
from upkie_mujoco_course.vla.behavior_cloning import BehaviorCloningPolicy
from upkie_mujoco_course.vla.expert import ScriptedVLAExpert
from upkie_mujoco_course.vla.demonstrations import generate_scripted_demonstration
from upkie_mujoco_course.vla.demonstrations import expert_command_for_task
from upkie_mujoco_course.vla.evaluation import evaluate_vla_tasks
from upkie_mujoco_course.envs.standing_env import StandingEnv
from upkie_mujoco_course.vla.perception import TargetDetection
from upkie_mujoco_course.vla.control import VLASafetyController
from upkie_mujoco_course.vla.expert import ExpertCommand
from upkie_mujoco_course.sim.runner import SimulationRunner
from upkie_mujoco_course.vla.language import parse_task_instruction
from upkie_mujoco_course.vla.perception import detect_colored_target
from upkie_mujoco_course.vla.labs import run_vla_lab


def test_language_instruction_maps_to_structured_target():
    task = parse_task_instruction("前往红色目标并停车")
    assert task.verb == "navigate"
    assert task.target_color == "red"
    assert task.stop_at_target is True


def test_rgbd_detector_finds_red_target_centroid_and_depth():
    rgb = np.zeros((20, 40, 3), dtype=np.uint8)
    depth = np.full((20, 40), 5.0, dtype=np.float32)
    rgb[5:15, 25:35, 0] = 255
    depth[5:15, 25:35] = 2.0
    detection = detect_colored_target(rgb, depth, "red")
    assert detection.visible is True
    assert 0.45 < detection.horizontal_offset < 0.6
    assert np.isclose(detection.distance, 2.0)


def test_rgbd_detector_does_not_confuse_safety_orange_with_red_target():
    rgb = np.zeros((10, 10, 3), dtype=np.uint8)
    depth = np.ones((10, 10), dtype=np.float32)
    rgb[2:8, 2:8] = [230, 92, 20]
    detection = detect_colored_target(rgb, depth, "red")
    assert detection.visible is False


def test_demonstration_episode_round_trips_without_losing_contract_fields(tmp_path):
    episode = DemonstrationEpisode(
        rgb=np.zeros((2, 8, 8, 3), dtype=np.uint8),
        depth=np.ones((2, 8, 8), dtype=np.float32),
        proprioception=np.zeros((2, 15), dtype=np.float32),
        action=np.zeros((2, 6), dtype=np.float32),
        instruction="前往红色目标并停车",
        timestamp=np.array([0.0, 0.01], dtype=np.float64),
    )
    path = save_episode(episode, tmp_path / "episode_0001.npz")
    with np.load(path, allow_pickle=False) as raw:
        assert raw["schema_version"].item() == "1.0"
    restored = load_episode(path)
    assert restored.instruction == episode.instruction
    assert restored.rgb.shape == (2, 8, 8, 3)
    assert np.allclose(restored.timestamp, episode.timestamp)


def test_demonstration_episode_preserves_episode_metadata(tmp_path):
    episode = DemonstrationEpisode(
        rgb=np.zeros((1, 4, 4, 3), dtype=np.uint8),
        depth=np.ones((1, 4, 4), dtype=np.float32),
        proprioception=np.zeros((1, 15), dtype=np.float32),
        action=np.zeros((1, 6), dtype=np.float32),
        instruction="前往蓝色目标并停车",
        timestamp=np.array([0.0]),
        metadata={"episode_id": "blue_001", "seed": 3, "target_color": "blue"},
    )
    restored = load_episode(save_episode(episode, tmp_path / "episode.npz"))
    assert restored.metadata == episode.metadata


def test_scripted_expert_slows_down_and_stops_at_target():
    expert = ScriptedVLAExpert(stop_distance=0.6, max_velocity=0.4)
    far = expert.command(visible=True, horizontal_offset=0.2, distance=2.0)
    near = expert.command(visible=True, horizontal_offset=0.0, distance=0.55)
    assert 0.0 < far.forward_velocity <= 0.4
    assert far.yaw_rate < 0.0
    assert near.forward_velocity == 0.0
    assert near.stop is True


def test_scripted_expert_ignores_calibrated_camera_center_offset():
    expert = ScriptedVLAExpert()
    command = expert.command(visible=True, horizontal_offset=0.06, distance=2.0)
    assert command.yaw_rate == 0.0


def test_scripted_expert_uses_arc_search_when_colored_target_is_occluded():
    task = parse_task_instruction("Navigate to the blue target and stop")
    command = expert_command_for_task(
        ScriptedVLAExpert(),
        task,
        TargetDetection(False, 0.0, float("inf"), 0),
    )
    assert command.forward_velocity > 0.0
    assert command.yaw_rate > 0.0


def test_scripted_expert_crosses_corridor_before_searching_for_occluded_target():
    task = parse_task_instruction("Navigate to the blue target and stop")
    hidden = TargetDetection(False, 0.0, float("inf"), 0)
    clear = np.full((20, 20), 2.0, dtype=np.float32)
    near_obstacle = np.full((20, 20), 0.5, dtype=np.float32)
    expert = ScriptedVLAExpert()
    first = expert_command_for_task(expert, task, hidden, clear)
    near = expert_command_for_task(expert, task, hidden, near_obstacle)
    passed = expert_command_for_task(expert, task, hidden, clear)
    assert first.forward_velocity > 0.0 and first.yaw_rate == 0.0
    assert near.forward_velocity > 0.0 and near.yaw_rate == 0.0
    assert passed.forward_velocity == 0.0 and passed.yaw_rate > 0.0


def test_yaw_rate_controller_turns_in_commanded_direction_without_falling():
    runner = SimulationRunner()
    runner.reset("stand")
    controller = VLASafetyController()
    max_pitch_error = 0.0
    while runner.time < 10.0:
        runner.step(controller.compute_action(runner, ExpertCommand(0.0, 0.45, False)))
        max_pitch_error = max(max_pitch_error, abs(float(runner.posture_state()["pitch_error"])))
    qpos_address = int(runner.model.jnt_qposadr[runner.root_joint_id])
    qw, qx, qy, qz = runner.data.qpos[qpos_address + 3 : qpos_address + 7]
    yaw = np.arctan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz))
    assert abs(yaw) > 1.0
    assert max_pitch_error < 0.3
    assert runner.posture_state()["both_wheels_contact"] is True
    runner.close()


def test_behavior_cloning_policy_fits_visual_language_examples():
    rgb = np.zeros((3, 8, 8, 3), dtype=np.uint8)
    depth = np.ones((3, 8, 8), dtype=np.float32)
    for index, channel in enumerate((0, 1, 2)):
        rgb[index, 2:6, 2:6, channel] = 255
    action = np.array(
        [[0.0, 0.0, 0.0, 0.0, -0.3, 0.3], [0.0, 0.0, 0.0, 0.0, 0.1, -0.1], [0.0] * 6],
        dtype=np.float32,
    )
    episodes = [
        DemonstrationEpisode(
            rgb=rgb[index : index + 1],
            depth=depth[index : index + 1],
            proprioception=np.zeros((1, 15), dtype=np.float32),
            action=action[index : index + 1],
            instruction=f"前往{color}目标并停车",
            timestamp=np.array([0.0]),
        )
        for index, color in enumerate(("红色", "绿色", "蓝色"))
    ]
    policy = BehaviorCloningPolicy.fit(episodes, ridge=1e-6)
    predicted = policy.predict(rgb[0], depth[0], np.zeros(15), "前往红色目标并停车")
    assert predicted.shape == (6,)
    assert np.allclose(predicted, action[0], atol=1e-3)


def test_behavior_cloning_policy_round_trips_checkpoint(tmp_path):
    episode = DemonstrationEpisode(
        rgb=np.zeros((1, 4, 4, 3), dtype=np.uint8),
        depth=np.ones((1, 4, 4), dtype=np.float32),
        proprioception=np.zeros((1, 15), dtype=np.float32),
        action=np.full((1, 6), 0.1, dtype=np.float32),
        instruction="前往红色目标并停车",
        timestamp=np.array([0.0]),
    )
    policy = BehaviorCloningPolicy.fit([episode])
    path = policy.save(tmp_path / "bc_policy.npz")
    restored = BehaviorCloningPolicy.load(path)
    assert np.allclose(
        restored.predict(episode.rgb[0], episode.depth[0], episode.proprioception[0], episode.instruction),
        policy.predict(episode.rgb[0], episode.depth[0], episode.proprioception[0], episode.instruction),
    )


def test_behavior_cloning_checkpoint_with_samples_uses_local_one_nearest_neighbor(tmp_path):
    episode = DemonstrationEpisode(
        rgb=np.zeros((1, 4, 4, 3), dtype=np.uint8),
        depth=np.ones((1, 4, 4), dtype=np.float32),
        proprioception=np.zeros((1, 15), dtype=np.float32),
        action=np.array([[0.25, -0.5, 1.0, 0.0, 0.0, 0.0]], dtype=np.float32),
        instruction="前往红色目标并停车",
        timestamp=np.array([0.0]),
    )
    fitted = BehaviorCloningPolicy.fit([episode])
    policy = BehaviorCloningPolicy(
        weights=np.zeros_like(fitted.weights),
        training_features=fitted.training_features,
        training_actions=fitted.training_actions,
        feature_mean=fitted.feature_mean,
        feature_scale=fitted.feature_scale,
    )
    restored = BehaviorCloningPolicy.load(policy.save(tmp_path / "local_1nn.npz"))

    predicted = restored.predict(
        episode.rgb[0], episode.depth[0], episode.proprioception[0], episode.instruction,
    )

    assert restored.weights.shape == (22, 6)
    assert np.allclose(predicted, episode.action[0])
    assert not np.allclose(predicted, 0.0)


def test_behavior_cloning_weight_only_checkpoint_keeps_linear_compatibility():
    weights = np.zeros((22, 6), dtype=np.float64)
    weights[-1] = np.array([0.1, -0.2, 0.3, 0.0, 0.0, 0.0])
    policy = BehaviorCloningPolicy(weights=weights)

    predicted = policy.predict(
        np.zeros((4, 4, 3), dtype=np.uint8),
        np.ones((4, 4), dtype=np.float32),
        np.zeros(15, dtype=np.float32),
        "前往红色目标并停车",
    )

    assert np.allclose(predicted, weights[-1])


def test_scripted_demonstration_uses_real_rgbd_and_action_contract():
    episode = generate_scripted_demonstration(
        "前往红色目标并停车",
        max_steps=3,
        width=80,
        height=60,
        seed=2,
    )
    assert episode.rgb.shape == (3, 60, 80, 3)
    assert episode.depth.shape == (3, 60, 80)
    assert episode.action.shape == (3, 6)
    assert episode.metadata["policy"] == "scripted_expert"


def test_vla_evaluation_reports_required_safety_metrics():
    report = evaluate_vla_tasks(["前往红色目标并停车"], max_steps=3, width=80, height=60)
    assert {
        "success_rate",
        "collision_rate",
        "mean_stopping_error_m",
        "max_pitch_rad",
        "mean_inference_latency_ms",
        "unseen_combination_success_rate",
        "episodes",
    } <= set(report)
    assert 0.0 <= report["success_rate"] <= 1.0


def test_vla_red_task_respects_low_level_pitch_safety_envelope():
    report = evaluate_vla_tasks(["前往红色目标并停车"], max_steps=3000, width=160, height=120)
    assert report["max_pitch_rad"] < 0.5


def test_vla_fixed_three_color_set_reaches_acceptance_success_rate():
    report = evaluate_vla_tasks(
        [
            "前往红色目标并停车",
            "Navigate to the blue target and stop",
            "Navigate to the green target and stop",
        ],
        max_steps=5000,
        width=160,
        height=120,
    )
    assert report["success_rate"] >= 0.8


def test_plain_stop_instruction_is_an_emergency_stop():
    task = parse_task_instruction("立即停止")

    assert task.verb == "stop"
    assert task.emergency_stop is True
    assert task.stop_at_target is False


def test_emergency_stop_overrides_policy_and_action_delay_same_step():
    env = StandingEnv(
        max_episode_steps=4,
        randomization={"action_delay_steps": [2, 2]},
    )
    controller = VLASafetyController()
    try:
        env.reset(seed=0)
        malicious_action = np.ones(env.action_space.shape, dtype=np.float64)
        safe_action = controller.compute_policy_action(
            env,
            malicious_action,
            emergency_stop=True,
        )
        _, _, _, _, info = env.step(safe_action, emergency_stop=True)

        wheel_ids = [env.runner.actuator_ids[name] for name in ("left_wheel_motor", "right_wheel_motor")]
        assert np.allclose(info["physical_action"][wheel_ids], 0.0)
        assert info["emergency_stop"] is True
        assert len(env._delayed_actions) == 0
    finally:
        env.close()


def test_bc_policy_is_called_inside_mujoco_evaluation_loop():
    class SpyPolicy:
        def __init__(self):
            self.calls = 0

        def predict(self, rgb, depth, proprioception, instruction):
            self.calls += 1
            return np.zeros(6, dtype=np.float64)

    policy = SpyPolicy()
    report = evaluate_vla_tasks(
        ["前往红色目标并停车"],
        policy=policy,
        max_steps=2,
        width=80,
        height=60,
    )

    assert policy.calls > 0
    assert report["backend"] == "mujoco"
    assert report["policy_type"] == "behavior_cloning"
    assert report["bc_policy_evaluated"] is True
    assert report["policy_inference_count"] == policy.calls


def test_emergency_stop_bypasses_bc_inference():
    class FailingPolicy:
        def predict(self, *args, **kwargs):
            raise AssertionError("紧急停止不应调用 BC 策略")

    report = evaluate_vla_tasks(
        ["立即停止"],
        policy=FailingPolicy(),
        max_steps=2,
        width=80,
        height=60,
    )

    assert report["emergency_stop_latency_steps"] == 0
    assert report["post_stop_wheel_torque_max"] <= 1e-9


def test_chapter_35_generates_real_three_color_mujoco_dataset(tmp_path):
    result_path = run_vla_lab("35", output_root=tmp_path, source_root=tmp_path, max_steps=12)
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["passed"] is True
    assert result["seed"] == 0
    assert result["metrics"]["mujoco_rgbd_episode_count"] >= 3
    for color in ("red", "green", "blue"):
        assert list((tmp_path / "datasets" / "vla").glob(f"{color}_*.npz"))


def test_chapter_35_preserves_each_episode_seed_in_filename_and_metadata(tmp_path):
    run_vla_lab("35", output_root=tmp_path, source_root=tmp_path, max_steps=12)

    dataset_paths = sorted((tmp_path / "datasets" / "vla").glob("*.npz"))
    episodes = [load_episode(path) for path in dataset_paths]

    assert len(dataset_paths) == 6
    assert sorted(episode.metadata["seed"] for episode in episodes) == [0, 1, 10, 11, 20, 21]
    for color in ("red", "green", "blue"):
        assert len(list((tmp_path / "datasets" / "vla").glob(f"{color}_*.npz"))) == 2


def test_chapter_36_requires_real_demonstration_dataset(tmp_path):
    with pytest.raises(FileNotFoundError, match="第 35 关"):
        run_vla_lab("36", output_root=tmp_path, source_root=tmp_path)


def test_chapter_37_requires_behavior_cloning_checkpoint(tmp_path):
    with pytest.raises(FileNotFoundError, match="第 36 关"):
        run_vla_lab("37", output_root=tmp_path, source_root=tmp_path)


def test_vla_35_to_37_pipeline_evaluates_bc_in_real_mujoco(tmp_path):
    run_vla_lab("35", output_root=tmp_path, source_root=tmp_path, max_steps=12)
    run_vla_lab("36", output_root=tmp_path, source_root=tmp_path)
    result_path = run_vla_lab(
        "37",
        output_root=tmp_path,
        source_root=tmp_path,
        max_steps=2,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    log = json.loads((tmp_path / "logs" / "vla_37.json").read_text(encoding="utf-8"))

    assert result["metrics"]["bc_policy_evaluated"] == 1.0
    assert result["seed"] == 0
    assert result["metrics"]["policy_inference_count"] > 0
    assert log["backend"] == "mujoco"
    assert log["policy_type"] == "behavior_cloning"
