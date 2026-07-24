"""VLA 关（32–37）专属实验入口。

用法：
    python scripts/run_vla_lab.py --chapter 32
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.vla.labs import VLA_LAB_CHAPTERS, run_vla_lab


def main() -> None:
    parser = argparse.ArgumentParser(description="运行应用型 VLA 阶段专属实验（32–37 关）")
    parser.add_argument("--chapter", choices=VLA_LAB_CHAPTERS, required=True)
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    result_path = run_vla_lab(args.chapter, output_root=args.output_root, seed=args.seed)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(f"VLA 实验 {args.chapter} 未通过，证据见: {result_path}")
    print(f"VLA 实验 {args.chapter} 通过，证据见: {result_path}")
    print(f"下一步: python scripts/course_checkpoint.py --chapter {args.chapter}")


if __name__ == "__main__":
    main()
