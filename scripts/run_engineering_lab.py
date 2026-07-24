from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.engineering.lab import EngineeringLabError
from upkie_mujoco_course.engineering.lab import run_engineering_lab
from upkie_mujoco_course.engineering.lab import run_engineering_project_lab


def main() -> None:
    parser = argparse.ArgumentParser(description="运行第 38 关 C++ 数值一致性实验")
    parser.add_argument("--chapter", choices=("38", "39"), default="38")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--sample-count", type=int, default=1000)
    parser.add_argument("--build-dir")
    parser.add_argument("--output-root", default="outputs")
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else int(args.chapter)
    try:
        if args.chapter == "38":
            result_path = run_engineering_lab(
                output_root=args.output_root,
                build_dir=args.build_dir or "build/cpp",
                seed=seed,
                sample_count=args.sample_count,
            )
        else:
            result_path = run_engineering_project_lab(
                output_root=args.output_root,
                build_dir=args.build_dir or "build/engineering-39",
                seed=seed,
            )
    except EngineeringLabError as error:
        raise SystemExit(f"第 {args.chapter} 关未通过：{error}") from error
    result = json.loads(result_path.read_text(encoding="utf-8"))
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    print(f"第 {args.chapter} 关通过，证据见: {result_path}")


if __name__ == "__main__":
    main()
