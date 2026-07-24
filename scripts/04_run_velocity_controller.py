from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.sim.runner import SimulationRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="运行带目标速度的经典平衡控制器")
    parser.add_argument("--target-velocity", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--no-viewer", action="store_true")
    args = parser.parse_args()
    runner = SimulationRunner()
    controller = WheelBalancerController(target_velocity=args.target_velocity)
    if not args.no_viewer:
        runner.open_viewer()
    try:
        runner.reset("stand")
        while runner.time < args.duration:
            runner.step(controller.compute_action(runner, runner.time))
        state = runner.posture_state()
        error = float(state["forward_velocity"]) - args.target_velocity
        print(
            f"速度控制完成: target={args.target_velocity:+.3f}m/s "
            f"actual={state['forward_velocity']:+.3f}m/s error={error:+.3f}m/s"
        )
    finally:
        runner.close()


if __name__ == "__main__":
    main()
