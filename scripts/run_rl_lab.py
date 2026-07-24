from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.rl.labs import RL_LAB_CHAPTERS
from upkie_mujoco_course.rl.labs import run_rl_lab


def main() -> None:
    parser = argparse.ArgumentParser(description="运行学习控制阶段专属实验")
    parser.add_argument("--chapter", choices=RL_LAB_CHAPTERS, required=True)
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    result_path = run_rl_lab(args.chapter, output_root=args.output_root, seed=args.seed)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(f"学习控制实验 {args.chapter} 未通过，证据见: {result_path}")
    print(f"学习控制实验 {args.chapter} 通过，证据见: {result_path}")
    print(f"下一步: python scripts/course_checkpoint.py --chapter {args.chapter}")


if __name__ == "__main__":
    main()
