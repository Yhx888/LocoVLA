from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.rl.train_sb3 import train_ppo_residual_standing, train_ppo_standing


def main() -> None:
    parser = argparse.ArgumentParser(description="短 PPO 站立训练")
    parser.add_argument("--total-timesteps", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=None, help="随机种子（默认从配置文件读取）")
    parser.add_argument("--profile", choices=["smoke", "reference"], default="smoke")
    parser.add_argument("--mode", choices=["full_action", "residual"], default="full_action")
    parser.add_argument("--residual-scale", type=float, default=0.2)
    args = parser.parse_args()
    if args.mode == "residual":
        path = train_ppo_residual_standing(
            total_timesteps=args.total_timesteps,
            seed=args.seed,
            profile=args.profile,
            residual_scale=args.residual_scale,
        )
    else:
        path = train_ppo_standing(
            total_timesteps=args.total_timesteps,
            seed=args.seed,
            profile=args.profile,
        )
    print(f"训练完成，模型保存到: {path}")


if __name__ == "__main__":
    main()
