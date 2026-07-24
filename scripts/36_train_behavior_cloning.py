from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.vla.behavior_cloning import BehaviorCloningPolicy
from upkie_mujoco_course.vla.contracts import load_episode


def main() -> None:
    parser = argparse.ArgumentParser(description="训练轻量视觉语言条件行为克隆策略")
    parser.add_argument("--dataset-dir", default="outputs/datasets/vla")
    parser.add_argument("--output", default="outputs/checkpoints/vla_bc_policy.npz")
    parser.add_argument("--ridge", type=float, default=1e-4)
    args = parser.parse_args()
    paths = sorted((ROOT / args.dataset_dir).glob("*.npz"))
    if not paths:
        raise SystemExit(f"没有找到示范数据: {ROOT / args.dataset_dir}")
    episodes = [load_episode(path) for path in paths]
    episodes = [
        episode
        for episode in episodes
        if episode.metadata.get("policy") == "scripted_expert"
        and episode.metadata.get("action_semantics") == "normalized_high_level_command"
    ]
    if not episodes:
        raise SystemExit("没有找到第 35 关生成的高层命令示范")
    policy = BehaviorCloningPolicy.fit(episodes, ridge=args.ridge)
    output = policy.save(ROOT / args.output)
    print(f"行为克隆训练完成: episodes={len(episodes)} checkpoint={output}")


if __name__ == "__main__":
    main()
