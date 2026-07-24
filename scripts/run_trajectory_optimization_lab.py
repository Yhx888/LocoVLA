from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.estimation.labs import run_trajectory_optimization_lab


def main() -> None:
    parser = argparse.ArgumentParser(description="运行第 24 关直接配点与单次打靶轨迹优化实验")
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--source-root", default=None)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    result_path = run_trajectory_optimization_lab(
        output_root=args.output_root,
        source_root=args.source_root,
        seed=args.seed,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(f"轨迹优化实验未通过，证据见: {result_path}")
    print(f"轨迹优化实验通过，证据见: {result_path}")


if __name__ == "__main__":
    main()
