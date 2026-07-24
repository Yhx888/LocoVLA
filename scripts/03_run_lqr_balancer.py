from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.controllers.lqr import LQRBalanceController
from upkie_mujoco_course.sim.runner import SimulationRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 LQR 轮端力矩平衡控制")
    parser.add_argument("--duration", type=float, default=10.0, help="仿真时长（秒）")
    parser.add_argument("--no-viewer", action="store_true", help="不打开可视化窗口")
    args = parser.parse_args()
    runner = SimulationRunner()
    controller = LQRBalanceController()
    if not args.no_viewer:
        runner.open_viewer()
    try:
        runner.reset("stand")
        while runner.time < args.duration:
            runner.step(controller.compute_action(runner))
        state = runner.posture_state()
        print(
            f"LQR 平衡完成: sim_time={runner.time:.3f}s "
            f"pitch={state['pitch']:+.4f} x={state['x_position']:+.4f}m"
        )
    finally:
        runner.close()


if __name__ == "__main__":
    main()
