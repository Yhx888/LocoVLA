from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.model.model_checks import write_model_audit
from upkie_mujoco_course.model.robot_spec import load_robot_spec
from upkie_mujoco_course.sim.loader import build_mujoco_model


def main() -> None:
    parser = argparse.ArgumentParser(description="审计 Upkie MuJoCo 模型")
    parser.add_argument("--config", default="configs/robot/upkie.json", help="机器人配置文件")
    args = parser.parse_args()
    spec = load_robot_spec(args.config)
    model = build_mujoco_model(spec)
    report = write_model_audit(model, spec)
    print(f"模型审计完成: nq={model.nq}, nv={model.nv}, nu={model.nu}")
    print(f"报告: {report}")


if __name__ == "__main__":
    main()

