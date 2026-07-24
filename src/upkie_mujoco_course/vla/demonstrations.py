"""从真实 MuJoCo RGB-D 闭环生成可解释示范。"""

from __future__ import annotations

import mujoco
import numpy as np

from upkie_mujoco_course.envs.standing_env import StandingEnv
from upkie_mujoco_course.vla.contracts import DemonstrationEpisode
from upkie_mujoco_course.vla.control import VLASafetyController
from upkie_mujoco_course.vla.expert import ExpertCommand, ScriptedVLAExpert
from upkie_mujoco_course.vla.language import parse_task_instruction
from upkie_mujoco_course.vla.perception import detect_colored_target


def render_rgbd(renderer: mujoco.Renderer, runner) -> tuple[np.ndarray, np.ndarray]:
    renderer.disable_depth_rendering()
    renderer.update_scene(runner.data, camera="onboard_camera")
    rgb = renderer.render().copy()
    renderer.enable_depth_rendering()
    renderer.update_scene(runner.data, camera="onboard_camera")
    depth = renderer.render().copy()
    return rgb, depth


def expert_command_for_task(expert, task, detection, depth: np.ndarray | None = None) -> ExpertCommand:
    if detection.visible and not expert.should_defer_detection(task.target_color):
        return expert.command(
            visible=True,
            horizontal_offset=detection.horizontal_offset,
            distance=detection.distance,
        )
    return expert.occluded_command(task.target_color, depth)


def generate_scripted_demonstration(
    instruction: str,
    *,
    max_steps: int = 600,
    width: int = 160,
    height: int = 120,
    seed: int = 0,
    record_stride: int = 1,
) -> DemonstrationEpisode:
    task = parse_task_instruction(instruction)
    if task.verb != "navigate" or task.target_color == "unknown":
        raise ValueError(f"无法执行的任务指令: {instruction}")
    env = StandingEnv(max_episode_steps=max_steps)
    renderer = mujoco.Renderer(env.runner.model, height=height, width=width)
    expert = ScriptedVLAExpert()
    controller = VLASafetyController()
    if record_stride < 1:
        raise ValueError("record_stride 必须为正整数")
    rgb_frames: list[np.ndarray] = []
    depth_frames: list[np.ndarray] = []
    observations: list[np.ndarray] = []
    actions: list[np.ndarray] = []
    timestamps: list[float] = []
    try:
        observation, _ = env.reset(seed=seed)
        controller.reset()
        control_steps = 0
        for step_index in range(max_steps):
            rgb, depth = render_rgbd(renderer, env.runner)
            detection = detect_colored_target(rgb, depth, task.target_color)
            command = expert_command_for_task(expert, task, detection, depth)
            physical_action = controller.compute_action(env.runner, command)
            control_action = env.to_normalized_action(physical_action)
            policy_action = np.array(
                [command.forward_velocity / expert.max_velocity, command.yaw_rate, float(command.stop), 0.0, 0.0, 0.0],
                dtype=np.float32,
            )
            if step_index % record_stride == 0 or command.stop:
                rgb_frames.append(rgb)
                depth_frames.append(depth.astype(np.float32))
                observations.append(observation.astype(np.float32))
                actions.append(policy_action)
                timestamps.append(env.runner.time)
            observation, _, terminated, truncated, info = env.step(
                control_action,
                emergency_stop=bool(command.stop),
            )
            control_steps = step_index + 1
            stopped = bool(command.stop and abs(float(info["forward_velocity"])) < 0.1)
            if terminated or truncated or stopped:
                break
        return DemonstrationEpisode(
            rgb=np.stack(rgb_frames),
            depth=np.stack(depth_frames),
            proprioception=np.stack(observations),
            action=np.stack(actions),
            instruction=instruction,
            timestamp=np.asarray(timestamps, dtype=np.float64),
            metadata={
                "episode_id": f"{task.target_color}_{seed:04d}",
                "seed": int(seed),
                "target_color": task.target_color,
                "policy": "scripted_expert",
                "action_semantics": "normalized_high_level_command",
                "camera": "onboard_camera",
                "control_steps": int(control_steps),
                "record_stride": int(record_stride),
            },
        )
    finally:
        renderer.close()
        env.close()
