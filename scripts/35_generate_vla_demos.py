from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.vla.contracts import save_episode
from upkie_mujoco_course.vla.demonstrations import generate_scripted_demonstration


def main() -> None:
    parser = argparse.ArgumentParser(description="用可解释脚本专家生成真实 MuJoCo RGB-D 示范")
    parser.add_argument("--instruction", default=None)
    parser.add_argument("--episodes", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=5000)
    parser.add_argument("--record-stride", type=int, default=5)
    parser.add_argument("--output-dir", default="outputs/datasets/vla")
    args = parser.parse_args()
    output_dir = ROOT / args.output_dir
    instructions = [args.instruction] if args.instruction else [
        "前往红色目标并停车",
        "Navigate to the green target and stop",
        "Navigate to the blue target and stop",
    ]
    for task_index, instruction in enumerate(instructions):
        for split_seed in range(args.episodes):
            seed = task_index * 10 + split_seed
            episode = generate_scripted_demonstration(
                instruction,
                max_steps=args.max_steps,
                seed=seed,
                record_stride=args.record_stride,
            )
            color = str(episode.metadata["target_color"])
            path = save_episode(episode, output_dir / f"{color}_{seed:04d}.npz")
            print(f"示范已保存: {path}，步数={episode.timestamp.shape[0]}")


if __name__ == "__main__":
    main()
