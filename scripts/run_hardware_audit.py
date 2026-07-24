from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.hardware.audit import run_hardware_audit


def main() -> None:
    parser = argparse.ArgumentParser(description="运行硬件选修的许可证与 BOM 审计")
    parser.add_argument("--chapter", choices=("H01",), default="H01")
    parser.add_argument("--output-root", default="outputs")
    args = parser.parse_args()
    result_path = run_hardware_audit(args.chapter, output_root=args.output_root)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(f"硬件审计未通过，证据见: {result_path}")
    print(f"硬件审计完成，证据见: {result_path}")


if __name__ == "__main__":
    main()
