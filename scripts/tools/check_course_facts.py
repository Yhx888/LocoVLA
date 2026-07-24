from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.course.facts import check_course_facts


def main() -> None:
    errors = check_course_facts()
    if errors:
        for error in errors:
            print(f"[漂移] {error}")
        raise SystemExit(1)
    print("课程事实检查通过：模型、清单、命令和 v2 正文一致。")


if __name__ == "__main__":
    main()
