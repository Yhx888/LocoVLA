from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.rl.train_sb3 import train_ppo_velocity


def main() -> None:
    parser = argparse.ArgumentParser(description="速度跟踪 PPO 训练")
    parser.add_argument("--total-timesteps", type=int, default=None)
    parser.add_argument("--target-velocity", type=float, default=0.3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--profile", choices=["smoke", "reference"], default="smoke")
    args = parser.parse_args()
    path = train_ppo_velocity(
        total_timesteps=args.total_timesteps,
        target_velocity=args.target_velocity,
        seed=args.seed,
        profile=args.profile,
    )
    print(f"速度策略训练完成，模型保存到: {path}")


if __name__ == "__main__":
    main()
