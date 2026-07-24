from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.course.dashboard_data import load_experiment_results
from upkie_mujoco_course.course.graduation import write_graduation_gate_report


def main() -> None:
    results = load_experiment_results(ROOT / "outputs")
    path = write_graduation_gate_report(ROOT / "outputs", results)
    report = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"毕业项目门槛报告：{path}")


if __name__ == "__main__":
    main()
