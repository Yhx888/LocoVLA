from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.controllers.wheel_balancer import WheelBalancerController
from upkie_mujoco_course.sim.runner import SimulationRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="运行传统轮端力矩平衡控制 demo")
    parser.add_argument("--duration", type=float, default=10.0, help="仿真时长（秒）")
    parser.add_argument("--no-viewer", action="store_true", help="不打开可视化窗口")
    args = parser.parse_args()
    runner = SimulationRunner()
    controller = WheelBalancerController()
    if not args.no_viewer:
        runner.open_viewer()
    runner.reset("crouch")
    while runner.time < args.duration:
        action = controller.compute_action(runner, runner.time)
        runner.step(action)
    state = runner.posture_state()
    print(f"传统平衡 demo 完成: sim_time={runner.time:.3f}s pitch={state['pitch']:+.4f} contact={state['both_wheels_contact']}")
    runner.close()


if __name__ == "__main__":
    main()
