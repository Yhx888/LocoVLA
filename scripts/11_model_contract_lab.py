from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.model.contract import run_model_contract_lab


def main() -> None:
    parser = argparse.ArgumentParser(description="运行关卡 11 机器人模型替换契约审计")
    parser.add_argument(
        "--inject-fault",
        choices=["wheel_semantics", "wheel_direction"],
        help="注入可复现故障，用于练习契约诊断",
    )
    parser.add_argument("--output-root", default="outputs")
    args = parser.parse_args()
    result_path = run_model_contract_lab(
        output_root=args.output_root,
        inject_fault=args.inject_fault,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(f"模型契约审计未通过，证据见: {result_path}")
    print(f"模型契约审计通过，证据见: {result_path}")
    print("下一步: python scripts/course_checkpoint.py --chapter 11")


if __name__ == "__main__":
    main()
