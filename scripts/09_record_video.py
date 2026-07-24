from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.rl.video import next_video_path, record_policy_video


def main() -> None:
    parser = argparse.ArgumentParser(description="离屏运行控制策略并生成 MP4")
    parser.add_argument("--name", default="upkie_demo.mp4")
    parser.add_argument("--mode", choices=["zero", "classic", "lqr", "rl", "residual"], default="classic")
    parser.add_argument("--model", default=None)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    result = record_policy_video(
        next_video_path(args.name),
        duration=args.duration,
        fps=args.fps,
        mode=args.mode,
        model_path=args.model,
        seed=args.seed,
    )
    print(
        f"录像完成: path={result.path} frames={result.frame_count} "
        f"duration={result.duration:.3f}s max_pitch={result.max_pitch_rad:.4f}rad"
    )


if __name__ == "__main__":
    main()
