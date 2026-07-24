from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gymnasium.utils.env_checker import check_env

from upkie_mujoco_course.envs.standing_env import StandingEnv


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 Gymnasium 环境")
    parser.add_argument("--max-episode-steps", type=int, default=5)
    args = parser.parse_args()
    env = StandingEnv(max_episode_steps=args.max_episode_steps)
    check_env(env, skip_render_check=True)
    env.close()
    print("Gymnasium 环境检查通过")


if __name__ == "__main__":
    main()

