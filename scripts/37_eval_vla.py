from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.vla.evaluation import evaluate_vla_tasks


DEFAULT_TASKS = [
    "前往红色目标并停车",
    "找到蓝色目标，避开障碍并停下",
    "Navigate to the green target and stop",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 VLA 固定测试集并保留全部失败案例")
    parser.add_argument("--max-steps", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--policy", default="outputs/checkpoints/vla_bc_policy.npz")
    parser.add_argument("--output", default="outputs/logs/vla_evaluation.json")
    args = parser.parse_args()
    report = evaluate_vla_tasks(
        DEFAULT_TASKS,
        policy_path=ROOT / args.policy,
        max_steps=args.max_steps,
        seed=args.seed,
    )
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "episodes"}, ensure_ascii=False, indent=2))
    print(f"逐任务结果已保存: {output}")


if __name__ == "__main__":
    main()
