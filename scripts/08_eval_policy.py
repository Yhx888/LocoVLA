from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.rl.evaluate import evaluate_policy


def main() -> None:
    parser = argparse.ArgumentParser(description="评估零动作、经典控制、RL 或残差策略")
    parser.add_argument("--model", default=None)
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--mode", choices=["zero", "classic", "rl", "residual"], default="zero")
    parser.add_argument("--residual-scale", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--record", action="store_true", help="同时保存该模式录像")
    args = parser.parse_args()
    returns = evaluate_policy(
        args.model,
        episodes=args.episodes,
        mode=args.mode,
        residual_scale=args.residual_scale,
        seed=args.seed,
    )
    print(f"评估完成: mode={args.mode} seed={args.seed} returns={returns}")
    if args.record:
        from upkie_mujoco_course.rl.video import next_video_path, record_policy_video

        path = next_video_path(f"evaluation_{args.mode}.mp4")
        result = record_policy_video(
            path,
            mode=args.mode,
            model_path=args.model,
            residual_scale=args.residual_scale,
            seed=args.seed,
        )
        print(f"录像保存到: {result.path}，帧数={result.frame_count}，最大俯仰角={result.max_pitch_rad:.4f}rad")


if __name__ == "__main__":
    main()
