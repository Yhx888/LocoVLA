"""VLA 策略的 MuJoCo 闭环任务评估。"""

from __future__ import annotations

import time
from pathlib import Path

import mujoco
import numpy as np

from upkie_mujoco_course.envs.standing_env import StandingEnv
from upkie_mujoco_course.vla.behavior_cloning import BehaviorCloningPolicy
from upkie_mujoco_course.vla.control import VLASafetyController
from upkie_mujoco_course.vla.demonstrations import expert_command_for_task, render_rgbd
from upkie_mujoco_course.vla.expert import ScriptedVLAExpert
from upkie_mujoco_course.vla.language import parse_task_instruction
from upkie_mujoco_course.vla.perception import detect_colored_target


def _has_obstacle_contact(runner) -> bool:
    for index in range(runner.data.ncon):
        contact = runner.data.contact[index]
        names = {
            mujoco.mj_id2name(runner.model, mujoco.mjtObj.mjOBJ_GEOM, int(contact.geom1)),
            mujoco.mj_id2name(runner.model, mujoco.mjtObj.mjOBJ_GEOM, int(contact.geom2)),
        }
        if any(name and name.startswith("obstacle_") for name in names):
            return True
    return False


def evaluate_vla_tasks(
    instructions: list[str],
    *,
    policy=None,
    policy_path: str | Path | None = None,
    max_steps: int = 5000,
    width: int = 160,
    height: int = 120,
    seed: int = 0,
    stopping_tolerance_m: float = 0.4,
) -> dict:
    if policy is not None and policy_path is not None:
        raise ValueError("policy 与 policy_path 只能指定一个")
    if policy_path is not None:
        policy = BehaviorCloningPolicy.load(policy_path)
    policy_type = "behavior_cloning" if policy is not None else "scripted_expert"
    episodes: list[dict] = []
    policy_inference_count = 0
    emergency_stop_latency_steps = 0
    post_stop_wheel_torque_max = 0.0
    for episode_index, instruction in enumerate(instructions):
        task = parse_task_instruction(instruction)
        env = StandingEnv(max_episode_steps=max_steps)
        renderer = mujoco.Renderer(env.runner.model, height=height, width=width)
        expert = ScriptedVLAExpert()
        controller = VLASafetyController()
        collision = False
        max_pitch = 0.0
        latencies: list[float] = []
        stopped = False
        target_stop_latched = False
        steps_executed = 0
        final_forward_velocity = 0.0
        try:
            observation, _ = env.reset(seed=seed + episode_index)
            if task.emergency_stop:
                action = controller.compute_policy_action(
                    env,
                    np.zeros(env.action_space.shape, dtype=np.float64),
                    emergency_stop=True,
                )
                _, _, _, _, info = env.step(action, emergency_stop=True)
                wheel_ids = [
                    env.runner.actuator_ids[name]
                    for name in ("left_wheel_motor", "right_wheel_motor")
                ]
                post_stop_wheel_torque_max = max(
                    post_stop_wheel_torque_max,
                    float(np.max(np.abs(info["physical_action"][wheel_ids]))),
                )
                episodes.append(
                    {
                        "instruction": instruction,
                        "target_color": task.target_color,
                        "success": True,
                        "collision": False,
                        "stopping_error_m": 0.0,
                        "max_pitch_rad": abs(float(info["pitch_error"])),
                        "mean_inference_latency_ms": 0.0,
                        "emergency_stop": True,
                    }
                )
                continue
            if task.verb != "navigate" or task.target_color == "unknown":
                raise ValueError(f"无法执行的任务指令: {instruction}")
            for step_index in range(max_steps):
                rgb, depth = render_rgbd(renderer, env.runner)
                start = time.perf_counter()
                detection = detect_colored_target(rgb, depth, task.target_color)
                if policy is None:
                    command = expert_command_for_task(expert, task, detection, depth)
                    target_stop_latched = bool(target_stop_latched or command.stop)
                    if target_stop_latched:
                        command = type(command)(0.0, 0.0, True)
                    action = env.to_normalized_action(controller.compute_action(env.runner, command))
                else:
                    predicted = policy.predict(rgb, depth, observation, instruction)
                    policy_inference_count += 1
                    target_stop_latched = bool(
                        target_stop_latched
                        or float(predicted[2]) > 0.5
                        or (
                        task.stop_at_target
                        and detection.visible
                        and detection.distance <= expert.stop_distance + 0.2
                        )
                    )
                    action = controller.compute_policy_action(
                        env,
                        predicted,
                        stop_requested=target_stop_latched,
                    )
                latencies.append((time.perf_counter() - start) * 1_000.0)
                if policy is None:
                    target_stop_latched = bool(target_stop_latched or command.stop)
                observation, _, terminated, truncated, info = env.step(
                    action,
                    emergency_stop=False,
                )
                collision = collision or _has_obstacle_contact(env.runner)
                max_pitch = max(max_pitch, abs(float(info["pitch_error"])))
                forward_velocity = float(info.get("forward_velocity", 0.0))
                final_forward_velocity = forward_velocity
                steps_executed = step_index + 1
                stopped = bool(
                    target_stop_latched
                    and abs(forward_velocity) < 0.1
                )
                if terminated or truncated or stopped:
                    break
            target_id = mujoco.mj_name2id(env.runner.model, mujoco.mjtObj.mjOBJ_GEOM, f"{task.target_color}_target")
            target_position = env.runner.data.geom_xpos[target_id]
            base_id = env.runner.frame_map.body_ids[env.runner.spec.base_body]
            base_position = env.runner.data.xpos[base_id]
            center_distance = float(np.linalg.norm(target_position[:2] - base_position[:2]))
            stopping_error = abs(center_distance - (expert.stop_distance + 0.2))
            stopped_at_goal = bool(
                stopped
                or (
                    abs(final_forward_velocity) < 0.1
                    and stopping_error <= stopping_tolerance_m
                )
            )
            success = bool(
                stopped_at_goal
                and not collision
                and max_pitch <= 0.5
                and stopping_error <= stopping_tolerance_m
            )
            episodes.append(
                {
                    "instruction": instruction,
                    "target_color": task.target_color,
                    "success": success,
                    "collision": collision,
                    "stopping_error_m": stopping_error,
                    "max_pitch_rad": max_pitch,
                    "mean_inference_latency_ms": float(np.mean(latencies)) if latencies else 0.0,
                    "emergency_stop": False,
                    "steps_executed": int(steps_executed),
                    "final_forward_velocity_m_s": float(final_forward_velocity),
                    "target_stop_latched": bool(target_stop_latched),
                    "stopped_at_goal": stopped_at_goal,
                }
            )
        finally:
            renderer.close()
            env.close()
    success_values = [float(item["success"]) for item in episodes]
    collision_values = [float(item["collision"]) for item in episodes]
    return {
        "success_rate": float(np.mean(success_values)) if success_values else 0.0,
        "collision_rate": float(np.mean(collision_values)) if collision_values else 0.0,
        "mean_stopping_error_m": float(np.mean([item["stopping_error_m"] for item in episodes])) if episodes else 0.0,
        "max_pitch_rad": max((item["max_pitch_rad"] for item in episodes), default=0.0),
        "mean_inference_latency_ms": float(np.mean([item["mean_inference_latency_ms"] for item in episodes])) if episodes else 0.0,
        "unseen_combination_success_rate": float(np.mean(success_values[1:])) if len(success_values) > 1 else (success_values[0] if success_values else 0.0),
        "stopping_tolerance_m": float(stopping_tolerance_m),
        "backend": "mujoco",
        "policy_type": policy_type,
        "policy_action_semantics": "normalized_high_level_command" if policy is not None else "expert_command",
        "bc_policy_evaluated": bool(policy is not None and policy_inference_count > 0),
        "policy_inference_count": int(policy_inference_count),
        "emergency_stop_latency_steps": int(emergency_stop_latency_steps),
        "post_stop_wheel_torque_max": float(post_stop_wheel_torque_max),
        "episodes": episodes,
    }
